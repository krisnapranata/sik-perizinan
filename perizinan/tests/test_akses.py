from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from core.models import LogAudit
from perizinan.models import StatusPermohonan
from perizinan.tests.dasar import DasarUji, berkas


class AksesBerkas(DasarUji):
    def url(self, p):
        return reverse("perizinan:unduh_dokumen", args=[p.nomor_registrasi, p.dokumen.first().pk])

    def status_untuk(self, pengguna, url):
        self.client.force_login(pengguna)
        return self.client.get(url).status_code

    def test_berkas_hanya_untuk_pemilik_petugas_dan_instansi_tujuan(self):
        p = self.terkirim()
        url = self.url(p)
        self.assertEqual(self.client.get(url).status_code, 302)  # anonim -> login
        self.assertEqual(self.status_untuk(self.pemohon.user, url), 200)
        self.assertEqual(self.status_untuk(self.petugas, url), 200)
        for pengguna in (self.pemohon_lain.user, self.penilai, self.pimpinan, self.admin_sistem):
            self.assertEqual(self.status_untuk(pengguna, url), 404)
        self.setujui_dokumen(p)
        from perizinan import services
        from perizinan.models import Aksi

        services.proses(p, Aksi.TERUSKAN, self.petugas)
        self.assertEqual(self.status_untuk(self.penilai, url), 200)
        self.assertEqual(self.status_untuk(self.penilai_lain, url), 404)

    def test_draf_tidak_terlihat_oleh_petugas_lain(self):
        p = self.draf()
        self.assertEqual(self.status_untuk(self.petugas, self.url(p)), 404)

    def test_respons_memakai_x_accel_dan_attachment(self):
        p = self.terkirim()
        self.client.force_login(self.pemohon.user)
        r = self.client.get(self.url(p))
        self.assertTrue(r["X-Accel-Redirect"].startswith("/_berkas/syarat/"))
        self.assertTrue(r["Content-Disposition"].startswith("attachment"))
        self.assertEqual(r.content, b"")
        self.assertTrue(LogAudit.objects.filter(aksi="berkas.unduh").exists())

    @override_settings(DEBUG=True)
    def test_mode_pengembangan_mengirim_isi_langsung(self):
        p = self.terkirim()
        self.client.force_login(self.pemohon.user)
        r = self.client.get(self.url(p))
        self.assertEqual(b"".join(r.streaming_content), b"%PDF-1.4 uji")

    def test_bukti_nib(self):
        self.pemohon.nib = "1234567890123"
        self.pemohon.bukti_nib = berkas()
        self.pemohon.save()
        url = reverse("perizinan:unduh_nib", args=[self.pemohon.pk])
        self.assertEqual(self.status_untuk(self.pemohon.user, url), 200)
        self.assertEqual(self.status_untuk(self.pemohon_lain.user, url), 404)
        self.assertEqual(self.status_untuk(self.petugas, url), 404)  # belum ada berkas masuk
        self.terkirim()
        self.assertEqual(self.status_untuk(self.petugas, url), 200)

    def test_dokumen_permohonan_lain_tidak_bisa_diakses_lewat_nomor_sendiri(self):
        milik_saya = self.terkirim()
        milik_lain = self.terkirim(pemohon=self.pemohon_lain)
        url = reverse(
            "perizinan:unduh_dokumen",
            args=[milik_saya.nomor_registrasi, milik_lain.dokumen.first().pk],
        )
        self.assertEqual(self.status_untuk(self.pemohon.user, url), 404)


class AksesHalaman(DasarUji):
    def test_daftar_hanya_milik_sendiri(self):
        milik_saya = self.terkirim()
        milik_lain = self.terkirim(pemohon=self.pemohon_lain)
        self.client.force_login(self.pemohon.user)
        isi = self.client.get(reverse("perizinan:daftar")).content.decode()
        self.assertIn(milik_saya.nomor_registrasi, isi)
        self.assertNotIn(milik_lain.nomor_registrasi, isi)

    def test_pemohon_tidak_bisa_memakai_aksi_verifikasi(self):
        p = self.terkirim()
        self.client.force_login(self.pemohon.user)
        self.client.post(reverse("perizinan:aksi", args=[p.nomor_registrasi]), {"aksi": "tolak", "catatan": "x"})
        p.refresh_from_db()
        self.assertEqual(p.status, StatusPermohonan.DIAJUKAN)

    def test_antrean_sesuai_peran(self):
        self.terkirim()
        url = reverse("perizinan:antrean")
        self.client.force_login(self.pemohon.user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.petugas)
        self.assertEqual(len(self.client.get(url).context["halaman"]), 1)
        self.client.force_login(self.penilai)
        self.assertEqual(len(self.client.get(url).context["halaman"]), 0)
        self.dinilai(pemohon=self.pemohon_lain)
        self.assertEqual(len(self.client.get(url).context["halaman"]), 1)
        self.client.force_login(self.penilai_lain)
        self.assertEqual(len(self.client.get(url).context["halaman"]), 0)

    def test_pemohon_tidak_bisa_membuat_permohonan_atas_nama_orang_lain(self):
        self.client.force_login(self.pemohon.user)
        url = reverse("perizinan:baru_loket", args=[self.pemohon_lain.pk])
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_halaman_detail_setiap_tahap_tampil(self):
        p = self.dinilai()
        self.client.force_login(self.penilai)
        r = self.client.get(reverse("perizinan:detail", args=[p.nomor_registrasi]))
        self.assertContains(r, "Simpan penilaian")
        self.client.force_login(self.petugas)
        self.assertNotContains(
            self.client.get(reverse("perizinan:detail", args=[p.nomor_registrasi])), "Simpan penilaian"
        )
        p = self.disetujui(pemohon=self.pemohon_lain)
        r = self.client.get(reverse("perizinan:detail", args=[p.nomor_registrasi]))
        self.assertContains(r, "Terbitkan izin")
        self.client.post(reverse("perizinan:terbit", args=[p.nomor_registrasi]))
        p.refresh_from_db()
        self.assertEqual(p.status, StatusPermohonan.TERBIT)
        self.client.force_login(self.pemohon_lain.user)
        r = self.client.get(reverse("perizinan:detail", args=[p.nomor_registrasi]))
        self.assertContains(r, p.izin_terbit.nomor_izin)
        r = self.client.get(reverse("perizinan:unduh_izin", args=[p.nomor_registrasi]))
        self.assertEqual(r.status_code, 200)

    def test_alur_pemohon_lewat_web(self):
        self.client.force_login(self.pemohon.user)
        r = self.client.post(reverse("perizinan:baru"), {"jenis_izin": self.kkpr.pk})
        nomor = r.url.rstrip("/").split("/")[-1]
        p = self.pemohon.permohonan.get(nomor_registrasi=nomor)
        self.client.post(
            reverse("perizinan:formulir", args=[nomor]),
            {"lokasi_alamat": "Dusun A", "kecamatan": self.selong.pk, "rencana_kegiatan": "Rumah"},
        )
        for syarat in p.syarat_berlaku():
            self.client.post(
                reverse("perizinan:unggah", args=[nomor, syarat.pk]), {"berkas": berkas()}
            )
        self.client.post(reverse("perizinan:kirim", args=[nomor]))
        p.refresh_from_db()
        self.assertEqual(p.status, StatusPermohonan.DIAJUKAN)
        self.assertEqual(p.kanal, "mandiri")

    def test_unggah_ditolak_bila_bukan_pdf_atau_jpg_asli(self):
        p = self.draf()
        self.client.force_login(self.pemohon.user)
        syarat = p.syarat_berlaku().first()
        lama = p.dokumen.get(syarat=syarat).berkas.name
        url = reverse("perizinan:unggah", args=[p.nomor_registrasi, syarat.pk])
        palsu = SimpleUploadedFile("uji.pdf", b"<script>alert(1)</script>")
        besar = SimpleUploadedFile("uji.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024))
        html = SimpleUploadedFile("uji.html", b"%PDF-")
        for berkas_buruk in (palsu, besar, html):
            self.client.post(url, {"berkas": berkas_buruk})
            self.assertEqual(p.dokumen.get(syarat=syarat).berkas.name, lama)


class CekStatusPublik(DasarUji):
    def test_tanpa_login_dan_tanpa_data_pribadi(self):
        p = self.terkirim()
        r = self.client.get(reverse("perizinan:cek_status"), {"nomor": p.nomor_registrasi})
        isi = r.content.decode()
        self.assertEqual(r.status_code, 200)
        self.assertIn("Diajukan", isi)
        for rahasia in (self.pemohon.nama, self.pemohon.nik, "a@uji.test", "petugas"):
            self.assertNotIn(rahasia, isi)

    def test_draf_tidak_tampil(self):
        p = self.draf()
        r = self.client.get(reverse("perizinan:cek_status"), {"nomor": p.nomor_registrasi})
        self.assertContains(r, "tidak ditemukan")

    def test_nomor_tidak_berurutan(self):
        self.assertNotEqual(self.draf().nomor_registrasi[-8:], self.draf().nomor_registrasi[-8:])


class Dasbor(DasarUji):
    url = reverse("perizinan:dasbor")

    def test_akses_per_peran(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.admin_sistem)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        for pengguna in (self.pemohon.user, self.petugas, self.penilai):
            self.client.force_login(pengguna)
            self.assertEqual(self.client.get(self.url).status_code, 200)
        self.client.force_login(self.pimpinan)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_beranda_mengarahkan_ke_dasbor(self):
        self.client.force_login(self.petugas)
        self.assertRedirects(self.client.get(reverse("beranda")), self.url)

    def test_pemohon_hanya_melihat_angka_miliknya(self):
        self.terkirim(pemohon=self.pemohon_lain)
        self.terkirim(pemohon=self.pemohon_lain)
        milik = self.terkirim()
        self.client.force_login(self.pemohon.user)
        r = self.client.get(self.url)
        d = r.context["d"]
        self.assertEqual(d["total"], 1)
        self.assertEqual(d["masuk_minggu_ini"], 1)
        self.assertEqual([m["p"] for m in d["milik"]], [milik])
        self.assertNotContains(r, self.pemohon_lain.nama)

    def test_petugas_melihat_antrean_dan_grafik(self):
        self.terkirim()
        self.terkirim(pemohon=self.pemohon_lain)
        self.client.force_login(self.petugas)
        d = self.client.get(self.url).context["d"]
        self.assertEqual(d["menunggu_saya"], 2)
        self.assertEqual(len(d["harian"]), 14)
        self.assertEqual(d["harian"][-1]["jumlah"], 2)
        self.assertEqual(d["harian"][-1]["tinggi"], 100)


class PratinjauBerkas(DasarUji):
    def url(self, p):
        return reverse("perizinan:unduh_dokumen", args=[p.nomor_registrasi, p.dokumen.first().pk])

    def test_lihat_tampil_langsung_dengan_header_aman(self):
        p = self.terkirim()
        self.client.force_login(self.pemohon.user)
        r = self.client.get(self.url(p) + "?lihat=1")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r["Content-Disposition"].startswith("inline"))
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("no-store", r["Cache-Control"])
        self.assertTrue(LogAudit.objects.filter(aksi="berkas.lihat").exists())

    def test_tanpa_lihat_tetap_diunduh(self):
        p = self.terkirim()
        self.client.force_login(self.pemohon.user)
        r = self.client.get(self.url(p))
        self.assertTrue(r["Content-Disposition"].startswith("attachment"))
        self.assertTrue(LogAudit.objects.filter(aksi="berkas.unduh").exists())

    def test_pratinjau_tetap_dibatasi_hak_akses(self):
        p = self.terkirim()
        for pengguna in (self.pemohon_lain.user, self.penilai, self.admin_sistem):
            self.client.force_login(pengguna)
            self.assertEqual(self.client.get(self.url(p) + "?lihat=1").status_code, 404)

    @override_settings(DEBUG=True)
    def test_mode_pengembangan_juga_tampil_langsung(self):
        p = self.terkirim()
        self.client.force_login(self.pemohon.user)
        r = self.client.get(self.url(p) + "?lihat=1")
        self.assertTrue(r["Content-Disposition"].startswith("inline"))
        self.assertEqual(b"".join(r.streaming_content), b"%PDF-1.4 uji")

    def test_halaman_detail_punya_tombol_lihat(self):
        p = self.terkirim()
        self.client.force_login(self.petugas)
        r = self.client.get(reverse("perizinan:detail", args=[p.nomor_registrasi]))
        self.assertContains(r, 'data-pratinjau="pdf"')
        self.assertContains(r, 'id="pratinjau"')


class KatalogPublik(DasarUji):
    def test_katalog_dan_syarat_terbuka_tanpa_login(self):
        r = self.client.get(reverse("perizinan:katalog"))
        self.assertContains(r, "KKPR Nonberusaha")
        r = self.client.get(reverse("perizinan:katalog_detail", args=[self.kkpr.pk]))
        self.assertContains(r, "Bukti penguasaan tanah")
        self.assertContains(r, "Penilaian teknis")
