"""Alur PRD PANDU LOTIM 6.1 dan 6.4."""

from django.core import mail
from django.urls import reverse
from django.utils import timezone

from basisdata.models import IzinNonOSS
from core.models import LogAudit, TidakBisaDihapus
from perizinan import services
from perizinan.models import (
    Aksi,
    HasilPenilaian,
    PenilaianTeknis,
    RiwayatVerifikasi,
    StatusCek,
    StatusPermohonan,
)
from perizinan.tests.dasar import DasarUji, berkas

S = StatusPermohonan
T = services.TransisiTidakValid


class AlurDenganPenilaianTeknis(DasarUji):
    def test_alur_penuh_sampai_terbit(self):
        p = self.terkirim()
        self.assertEqual(p.status, S.DIAJUKAN)
        self.assertIsNotNone(p.diajukan_pada)
        self.setujui_dokumen(p)
        services.proses(p, Aksi.TERUSKAN, self.petugas)
        p.refresh_from_db()
        self.assertEqual((p.status, p.instansi_penilai), (S.PENILAIAN_TEKNIS, self.pupr))
        services.nilai(p, self.penilai, HasilPenilaian.MEMENUHI, "Sesuai RTRW.")
        p.refresh_from_db()
        self.assertEqual(p.status, S.DISETUJUI)
        services.terbitkan(p, self.petugas)
        p.refresh_from_db()
        self.assertEqual(p.status, S.TERBIT)
        tahun = timezone.localdate().year
        self.assertEqual(p.izin_terbit.nomor_izin, f"0001/KKPR-NB/DPMPTSP/{tahun}")
        self.assertTrue(p.izin_terbit.berkas.read().startswith(b"%PDF"))
        self.assertEqual(
            list(p.riwayat.values_list("aksi", flat=True)),
            [Aksi.KIRIM, Aksi.TERUSKAN, Aksi.MEMENUHI, Aksi.TERBIT],
        )

    def test_nomor_izin_berurutan_per_jenis(self):
        satu = self.terbit()
        dua = self.terbit(pemohon=self.pemohon_lain)
        self.assertTrue(satu.izin_terbit.nomor_izin.startswith("0001/"))
        self.assertTrue(dua.izin_terbit.nomor_izin.startswith("0002/"))

    def test_jenis_yang_perlu_kajian_tidak_bisa_langsung_disetujui(self):
        p = self.terkirim()
        self.setujui_dokumen(p)
        self.assertNotIn(Aksi.SETUJUI, services.aksi_tersedia(p))
        with self.assertRaises(T):
            services.proses(p, Aksi.SETUJUI, self.petugas)

    def test_tidak_memenuhi_ditolak_dengan_alasan(self):
        p = self.dinilai()
        services.nilai(p, self.penilai, HasilPenilaian.TIDAK_MEMENUHI, "Zona lindung.")
        p.refresh_from_db()
        self.assertEqual((p.status, p.catatan_terakhir), (S.DITOLAK, "Zona lindung."))
        self.assertEqual(IzinNonOSS.objects.get(permohonan=p).status, "ditolak")

    def test_hanya_instansi_tujuan_yang_bisa_menilai(self):
        p = self.dinilai()
        for bukan in (self.penilai_lain, self.petugas, self.pemohon.user):
            with self.assertRaises(T):
                services.nilai(p, bukan, HasilPenilaian.MEMENUHI, "x")
        with self.assertRaises(T):
            services.nilai(p, self.penilai, HasilPenilaian.MEMENUHI, "  ")  # rekomendasi wajib

    def test_teruskan_ke_instansi_lain(self):
        p = self.terkirim()
        self.setujui_dokumen(p)
        services.proses(p, Aksi.TERUSKAN, self.petugas, instansi=self.bappeda)
        p.refresh_from_db()
        self.assertEqual(p.instansi_penilai, self.bappeda)
        with self.assertRaises(T):
            services.nilai(p, self.penilai, HasilPenilaian.MEMENUHI, "x")

    def test_penilaian_tidak_bisa_diubah(self):
        p = self.disetujui()
        penilaian = PenilaianTeknis.objects.get(permohonan=p)
        with self.assertRaises(TidakBisaDihapus):
            penilaian.save()


class AlurTanpaPenilaianTeknis(DasarUji):
    def test_petugas_menyetujui_langsung(self):
        p = self.terkirim(jenis=self.sederhana)
        self.assertNotIn(Aksi.TERUSKAN, services.aksi_tersedia(p))
        self.setujui_dokumen(p)
        services.proses(p, Aksi.SETUJUI, self.petugas)
        services.terbitkan(p, self.petugas)
        p.refresh_from_db()
        self.assertEqual(p.status, S.TERBIT)
        self.assertIn("/UJI/", p.izin_terbit.nomor_izin)


class VerifikasiAdministrasi(DasarUji):
    def test_minta_perbaikan_wajib_catatan_lalu_kirim_ulang(self):
        p = self.terkirim()
        with self.assertRaises(T):
            services.proses(p, Aksi.MINTA_PERBAIKAN, self.petugas, "")
        services.proses(p, Aksi.MINTA_PERBAIKAN, self.petugas, "KTP buram")
        p.refresh_from_db()
        self.assertEqual(p.status, S.PERLU_PERBAIKAN)
        services.unggah_dokumen(p, p.syarat_berlaku().first(), berkas(), self.pemohon.user)
        services.kirim(p, self.pemohon.user)
        p.refresh_from_db()
        self.assertEqual(p.status, S.DIAJUKAN)

    def test_dokumen_tidak_sesuai_wajib_catatan_per_dokumen(self):
        p = self.terkirim()
        d = p.dokumen.first()
        with self.assertRaises(T):
            services.cek_dokumen(d, StatusCek.TIDAK_SESUAI, self.petugas, "")
        services.cek_dokumen(d, StatusCek.TIDAK_SESUAI, self.petugas, "Halaman 2 hilang")
        d.refresh_from_db()
        self.assertEqual(d.catatan_cek, "Halaman 2 hilang")

    def test_teruskan_ditolak_bila_dokumen_belum_sesuai(self):
        p = self.terkirim()
        with self.assertRaises(T):
            services.proses(p, Aksi.TERUSKAN, self.petugas)

    def test_petugas_bisa_menolak_dengan_alasan(self):
        p = self.terkirim()
        with self.assertRaises(T):
            services.proses(p, Aksi.TOLAK, self.petugas)
        services.proses(p, Aksi.TOLAK, self.petugas, "Bukan kewenangan daerah")
        p.refresh_from_db()
        self.assertEqual(p.status, S.DITOLAK)

    def test_unggah_ulang_mereset_status_cek(self):
        p = self.terkirim()
        services.proses(p, Aksi.MINTA_PERBAIKAN, self.petugas, "Perbaiki")
        d = p.dokumen.first()
        d.status_cek = StatusCek.SESUAI
        d.save()
        services.unggah_dokumen(p, d.syarat, berkas(), self.pemohon.user)
        d.refresh_from_db()
        self.assertEqual(d.status_cek, StatusCek.BELUM)

    def test_berkas_terkunci_setelah_dikirim(self):
        p = self.terkirim()
        with self.assertRaises(T):
            services.unggah_dokumen(p, p.syarat_berlaku().first(), berkas(), self.pemohon.user)

    def test_kirim_ditolak_bila_syarat_atau_formulir_kurang(self):
        p = services.buat_permohonan(self.pemohon, self.kkpr, self.pemohon.user)
        alasan = services.kekurangan(p)
        self.assertTrue(any("Formulir" in a for a in alasan))
        self.assertTrue(any("KTP pemohon" in a for a in alasan))
        with self.assertRaises(T):
            services.kirim(p, self.pemohon.user)

    def test_syarat_akta_hanya_untuk_badan_hukum(self):
        p = self.draf()
        self.assertNotIn("Akta pendirian badan hukum", [s.nama for s in p.syarat_berlaku()])

    def test_tidak_perlu_nib(self):
        self.assertFalse(self.pemohon.nib)
        self.assertEqual(self.terkirim().status, S.DIAJUKAN)

    def test_hanya_petugas_yang_memverifikasi(self):
        p = self.terkirim()
        self.setujui_dokumen(p)
        for bukan in (self.pemohon.user, self.penilai, self.pimpinan, self.admin_sistem):
            with self.assertRaises(T):
                services.proses(p, Aksi.TERUSKAN, bukan)


class Notifikasi(DasarUji):
    def test_email_setiap_perubahan_status(self):
        with self.captureOnCommitCallbacks(execute=True):
            p = self.terkirim()
            self.setujui_dokumen(p)
            services.proses(p, Aksi.TERUSKAN, self.petugas)
            p.refresh_from_db()
            services.nilai(p, self.penilai, HasilPenilaian.MEMENUHI, "OK")
            p.refresh_from_db()
            services.terbitkan(p, self.petugas)
        subjek = [m.subject for m in mail.outbox]
        self.assertEqual(len([s for s in subjek if p.nomor_registrasi in s]), 5)
        self.assertIn(["pupr@uji.test"], [m.to for m in mail.outbox])  # instansi dikabari


class DatabaseNonOSS(DasarUji):
    def test_izin_terbit_masuk_database_nonoss(self):
        p = self.terbit()
        izin = IzinNonOSS.objects.get(permohonan=p)
        self.assertEqual(izin.nomor_izin, p.izin_terbit.nomor_izin)
        self.assertEqual((izin.status, izin.kecamatan, izin.kelurahan.nama), ("terbit", self.selong, "Desa Uji"))
        self.assertEqual(izin.jenis.nama, "KKPR Nonberusaha")
        self.assertEqual(izin.instansi_teknis, self.pupr.nama)


class VerifikasiKeaslian(DasarUji):
    def test_halaman_qr_menyamarkan_nama(self):
        p = self.terbit()
        r = self.client.get(reverse("perizinan:verifikasi_izin", args=[p.izin_terbit.kode_verifikasi]))
        self.assertContains(r, p.izin_terbit.nomor_izin)
        self.assertNotContains(r, self.pemohon.nama)
        self.assertNotContains(r, self.pemohon.nik)
        r = self.client.get(reverse("perizinan:verifikasi_izin", args=["palsu"]))
        self.assertContains(r, "tidak ditemukan")

    def test_petugas_bisa_mengganti_dengan_dokumen_bertanda_tangan(self):
        p = self.terbit()
        self.client.force_login(self.petugas)
        self.client.post(reverse("perizinan:ganti_dokumen_izin", args=[p.nomor_registrasi]),
                         {"berkas": berkas("ttd.pdf", b"%PDF-1.4 ttd")})
        self.client.force_login(self.pemohon.user)
        r = self.client.get(reverse("perizinan:unduh_izin", args=[p.nomor_registrasi]))
        self.assertIn("/_berkas/izin/", r["X-Accel-Redirect"])
        p.izin_terbit.refresh_from_db()
        self.assertTrue(p.izin_terbit.berkas_ttd)


class JejakAudit(DasarUji):
    def test_riwayat_dan_log_audit_tidak_bisa_diubah(self):
        p = self.terkirim()
        riwayat = RiwayatVerifikasi.objects.filter(permohonan=p).first()
        with self.assertRaises(TidakBisaDihapus):
            riwayat.delete()
        with self.assertRaises(TidakBisaDihapus):
            riwayat.save()
        with self.assertRaises(TidakBisaDihapus):
            RiwayatVerifikasi.objects.all().delete()
        with self.assertRaises(TidakBisaDihapus):
            LogAudit.objects.all().update(aksi="x")
        self.assertTrue(LogAudit.objects.filter(aksi="permohonan.kirim").exists())
