"""Data demo di production: nomor izin terpisah, reset, dan hapus tidak boleh menyentuh data asli."""

from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import override_settings

from akun import demo
from akun.management.commands.buat_akun_demo import INVESTASI_CONTOH
from akun.models import User
from basisdata.models import IzinNonOSS, Kecamatan
from investasi.models import PeluangInvestasi
from perizinan import services
from perizinan.models import (
    Aksi,
    HasilPenilaian,
    PenomoranIzin,
    Permohonan,
    RiwayatVerifikasi,
    StatusCek,
)
from perizinan.tests.dasar import DasarUji

SANDI = "Presentasi-Lotim-2026"


def demo_cmd(*args, **kw):
    call_command("buat_akun_demo", *args, password=SANDI, ya=True, stdout=StringIO(), **kw)


class DataDemo(DasarUji):
    def _permohonan_demo(self):
        return Permohonan.objects.get(pemohon__user__email=demo.EMAIL_PEMOHON_DEMO)

    def _terbitkan_demo(self):
        p = self._permohonan_demo()
        petugas = User.objects.get(email="petugas@sik.test")
        for d in p.dokumen.all():
            services.cek_dokumen(d, StatusCek.SESUAI, petugas)
        if p.jenis_izin.perlu_kajian_teknis:
            services.proses(p, Aksi.TERUSKAN, petugas)
            services.nilai(p, User.objects.get(email="pupr@sik.test"), HasilPenilaian.MEMENUHI, "Rekaan.")
        else:
            services.proses(p, Aksi.SETUJUI, petugas)
        p.refresh_from_db()
        services.terbitkan(p, petugas)
        p.refresh_from_db()
        return p

    def test_nama_contoh_investasi_sama_dengan_penanda(self):
        self.assertEqual(tuple(d["nama"] for d in INVESTASI_CONTOH), demo.NAMA_INVESTASI_CONTOH)

    def test_izin_demo_tidak_memakai_nomor_resmi(self):
        demo_cmd()
        sebelum = list(PenomoranIzin.objects.values_list("jenis_izin_id", "tahun", "terakhir"))
        p = self._terbitkan_demo()
        self.assertEqual(p.izin_terbit.nomor_izin, f"DEMO-{p.nomor_registrasi}")
        self.assertEqual(list(PenomoranIzin.objects.values_list("jenis_izin_id", "tahun", "terakhir")), sebelum)

    def test_reset_kembali_ke_awal_tanpa_menyentuh_data_asli(self):
        asli = self.terbit()  # permohonan pemohon sungguhan (rekaan uji) sampai terbit
        riwayat_asli = RiwayatVerifikasi.objects.filter(permohonan=asli).count()
        investasi_asli = PeluangInvestasi.objects.create(
            nama="Investasi asli", tingkat="potensi", sektor="pertanian",
            kecamatan=Kecamatan.objects.get(nama="Selong"), deskripsi="Bukan contoh",
        )
        demo_cmd()
        self._terbitkan_demo()

        demo_cmd("--reset")

        p = self._permohonan_demo()
        self.assertEqual(p.status, "diajukan")
        self.assertFalse(IzinNonOSS.objects.filter(permohonan__pemohon__user__email=demo.EMAIL_PEMOHON_DEMO).exists())
        self.assertEqual(PeluangInvestasi.objects.filter(nama__in=demo.NAMA_INVESTASI_CONTOH).count(), 3)
        # Data asli utuh.
        asli.refresh_from_db()
        self.assertEqual(asli.status, "terbit")
        self.assertEqual(RiwayatVerifikasi.objects.filter(permohonan=asli).count(), riwayat_asli)
        self.assertTrue(IzinNonOSS.objects.filter(permohonan=asli).exists())
        self.assertTrue(PeluangInvestasi.objects.filter(pk=investasi_asli.pk).exists())

    def test_hapus_membuang_data_demo_dan_menonaktifkan_akun(self):
        asli = self.terkirim()
        demo_cmd()
        call_command("buat_akun_demo", "--hapus", ya=True, stdout=StringIO())
        self.assertFalse(Permohonan.objects.filter(pemohon__user__email=demo.EMAIL_PEMOHON_DEMO).exists())
        self.assertFalse(PeluangInvestasi.objects.filter(nama__in=demo.NAMA_INVESTASI_CONTOH).exists())
        self.assertFalse(User.objects.filter(email__in=demo.EMAIL_DEMO, is_active=True).exists())
        self.assertTrue(Permohonan.objects.filter(pk=asli.pk).exists())
        # --reset mengaktifkan kembali.
        demo_cmd("--reset")
        self.assertEqual(User.objects.filter(email__in=demo.EMAIL_DEMO, is_active=True).count(), 5)

    def test_production_reset_tanpa_konfirmasi_ditolak(self):
        demo_cmd()
        with mock.patch("sys.stdin.isatty", return_value=False), self.assertRaises(CommandError):
            call_command("buat_akun_demo", "--reset", password=SANDI, stdout=StringIO())
        self.assertTrue(Permohonan.objects.filter(pemohon__user__email=demo.EMAIL_PEMOHON_DEMO).exists())

    @override_settings(DEBUG=True)
    def test_lokal_reset_tanpa_konfirmasi(self):
        call_command("buat_akun_demo", stdout=StringIO())
        call_command("buat_akun_demo", "--reset", stdout=StringIO())
        self.assertEqual(Permohonan.objects.filter(pemohon__user__email=demo.EMAIL_PEMOHON_DEMO).count(), 1)
