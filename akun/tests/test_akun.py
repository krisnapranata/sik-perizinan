import re
from datetime import timedelta

from django.core import mail
from django.urls import reverse
from django.utils import timezone

from akun.models import Peran, User
from perizinan.tests.dasar import SANDI, DasarUji

DATA = {
    "email": "Baru@Uji.Test",
    "tipe": "perorangan",
    "nama": "Pemohon Baru",
    "nik": "1234567890123456",
    "npwp": "",
    "hp": "081234567890",
    "alamat": "Alamat rekaan",
}


class Registrasi(DasarUji):
    def daftar(self):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                reverse("akun:daftar"),
                {**DATA, "password": SANDI, "ulangi_password": SANDI},
            )

    def kode(self, nomor=-1):
        return re.search(r"\b(\d{6})\b", mail.outbox[nomor].body).group(1)

    def test_akun_nonaktif_sampai_otp_dimasukkan(self):
        r = self.daftar()
        self.assertRedirects(r, reverse("akun:verifikasi"))
        pengguna = User.objects.get(email="baru@uji.test")
        self.assertFalse(pengguna.is_active)
        self.assertFalse(self.client.login(email="baru@uji.test", password=SANDI))
        self.assertNotIn(self.kode(), str(pengguna.kode_otp.get().kode_hash))  # hanya hash
        r = self.client.post(reverse("akun:verifikasi"), {"kode": self.kode()})
        self.assertRedirects(r, reverse("akun:masuk"))
        pengguna.refresh_from_db()
        self.assertTrue(pengguna.is_active)
        self.assertTrue(self.client.login(email="baru@uji.test", password=SANDI))

    def test_otp_salah_dibatasi_lima_kali(self):
        self.daftar()
        benar = self.kode()
        salah = "000000" if benar != "000000" else "111111"
        for _ in range(5):
            self.assertContains(self.client.post(reverse("akun:verifikasi"), {"kode": salah}),
                                "Kode salah")
        r = self.client.post(reverse("akun:verifikasi"), {"kode": benar})
        self.assertContains(r, "Terlalu banyak percobaan")
        self.assertFalse(User.objects.get(email="baru@uji.test").is_active)

    def test_otp_kedaluwarsa(self):
        self.daftar()
        User.objects.get(email="baru@uji.test").kode_otp.update(
            kedaluwarsa=timezone.now() - timedelta(minutes=1)
        )
        r = self.client.post(reverse("akun:verifikasi"), {"kode": self.kode()})
        self.assertContains(r, "kedaluwarsa")

    def test_kirim_ulang_membatalkan_kode_lama(self):
        self.daftar()
        lama = self.kode()
        User.objects.get(email="baru@uji.test").kode_otp.update(
            dibuat=timezone.now() - timedelta(minutes=2)
        )
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("akun:kirim_ulang_otp"))
        baru = self.kode()
        if lama != baru:
            self.assertContains(self.client.post(reverse("akun:verifikasi"), {"kode": lama}),
                                "Kode salah")
        self.client.post(reverse("akun:verifikasi"), {"kode": baru})
        self.assertTrue(User.objects.get(email="baru@uji.test").is_active)

    def test_akun_yang_dinonaktifkan_admin_tidak_bisa_dihidupkan_lewat_otp(self):
        self.daftar()
        pengguna = User.objects.get(email="baru@uji.test")
        pengguna.last_login = timezone.now()  # pernah aktif, lalu dinonaktifkan admin
        pengguna.save()
        r = self.client.post(reverse("akun:verifikasi"), {"kode": self.kode()})
        self.assertRedirects(r, reverse("akun:masuk"))
        pengguna.refresh_from_db()
        self.assertFalse(pengguna.is_active)

    def test_nik_wajib_untuk_perorangan(self):
        r = self.client.post(
            reverse("akun:daftar"),
            {**DATA, "nik": "", "password": SANDI, "ulangi_password": SANDI},
        )
        self.assertContains(r, "NIK wajib")


class LayananBerbantuan(DasarUji):
    def test_petugas_membuat_akun_dan_permohonan_berbantuan(self):
        self.client.force_login(self.petugas)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(reverse("akun:loket_daftar"), DATA)
        self.assertEqual(r.status_code, 302)
        pengguna = User.objects.get(email="baru@uji.test")
        self.assertTrue(pengguna.is_active)
        self.assertIn("/akun/reset/", mail.outbox[0].body)

        pemohon = pengguna.pemohon
        self.client.post(
            reverse("perizinan:baru_loket", args=[pemohon.pk]), {"jenis_izin": self.kkpr.pk}
        )
        p = pemohon.permohonan.get()
        self.assertEqual(p.kanal, "berbantuan")
        self.assertEqual(p.dibuat_oleh, self.petugas)
        r = self.client.get(reverse("perizinan:detail", args=[p.nomor_registrasi]))
        self.assertEqual(r.status_code, 200)

    def test_halaman_loket_tertutup_untuk_peran_lain(self):
        for pengguna in (self.pemohon.user, self.penilai, self.pimpinan):
            self.client.force_login(pengguna)
            self.assertEqual(self.client.get(reverse("akun:loket")).status_code, 403)

    def test_pencarian_harus_cocok_persis(self):
        self.client.force_login(self.petugas)
        r = self.client.get(reverse("akun:loket"), {"q": "uji"})
        self.assertEqual(len(r.context["hasil"]), 0)
        r = self.client.get(reverse("akun:loket"), {"q": "a@uji.test"})
        self.assertEqual(len(r.context["hasil"]), 1)


class PanelAdmin(DasarUji):
    def test_hanya_admin_sistem_yang_masuk(self):
        url = reverse("admin:perizinan_jenisizin_changelist")
        self.client.force_login(self.pimpinan)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.admin_sistem)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_tambah_petugas_dan_tidak_bisa_jadi_superuser(self):
        self.client.force_login(self.admin_sistem)
        self.client.post(
            reverse("admin:akun_user_add"),
            {
                "email": "kasi2@uji.test",
                "nama": "Kasi Dua",
                "peran": Peran.PETUGAS,
                "password1": "SandiUji-9x!",
                "password2": "SandiUji-9x!",
            },
        )
        self.assertEqual(User.objects.get(email="kasi2@uji.test").peran, Peran.PETUGAS)
        self.client.get(reverse("admin:akun_user_change", args=[self.petugas.pk]))
        self.client.post(
            reverse("admin:akun_user_change", args=[self.admin_sistem.pk]),
            {
                "email": self.admin_sistem.email,
                "nama": "x",
                "peran": Peran.ADMIN,
                "is_active": "on",
                "is_superuser": "on",
            },
        )
        self.admin_sistem.refresh_from_db()
        self.assertFalse(self.admin_sistem.is_superuser)

    def test_log_audit_baca_saja(self):
        self.client.force_login(self.admin_sistem)
        self.assertEqual(
            self.client.get(reverse("admin:core_logaudit_changelist")).status_code, 200
        )
        self.assertEqual(self.client.get(reverse("admin:core_logaudit_add")).status_code, 403)


class PemohonTanpaData(DasarUji):
    """Akun pemohon yang dibuat Admin Sistem lewat panel admin belum punya data pemohon."""

    def setUp(self):
        self.akun = User.objects.create_user(
            email="baru-admin@uji.test", password="SandiUji-9x!", nama="Dibuat Admin"
        )
        self.client.force_login(self.akun)

    def test_ajukan_izin_diarahkan_ke_profil(self):
        r = self.client.get(reverse("perizinan:baru"))
        self.assertRedirects(r, reverse("akun:profil"))

    def test_bisa_melengkapi_data_lalu_mengajukan(self):
        self.assertEqual(self.client.get(reverse("akun:profil")).status_code, 200)
        r = self.client.post(
            reverse("akun:profil"),
            {**{k: v for k, v in DATA.items() if k != "email"}, "nib": ""},
        )
        self.assertEqual(r.status_code, 302)
        self.akun.refresh_from_db()
        self.assertEqual(self.akun.pemohon.nama, "Pemohon Baru")
        self.assertEqual(self.client.get(reverse("perizinan:baru")).status_code, 200)

    def test_peran_lain_tetap_ditolak(self):
        self.client.force_login(self.petugas)
        self.assertEqual(self.client.get(reverse("akun:profil")).status_code, 403)
        self.assertEqual(self.client.get(reverse("perizinan:baru")).status_code, 403)


class PerintahAkunDemo(DasarUji):
    def test_production_tanpa_password_ditolak_bila_tidak_interaktif(self):
        from io import StringIO
        from unittest import mock

        from django.core.management import CommandError, call_command

        with mock.patch("sys.stdin.isatty", return_value=False), self.assertRaises(CommandError):
            call_command("buat_akun_demo", stdout=StringIO())
        self.assertFalse(User.objects.filter(email="admin@sik.test").exists())

    def test_production_menolak_demo123_dan_password_lemah(self):
        from io import StringIO

        from django.core.management import CommandError, call_command

        for lemah in ("demo123", "12345678"):
            with self.assertRaises(CommandError):
                call_command("buat_akun_demo", password=lemah, stdout=StringIO())
        self.assertFalse(User.objects.filter(email="admin@sik.test").exists())

    def test_production_dengan_password_sendiri(self):
        from io import StringIO

        from django.core.management import call_command

        call_command("buat_akun_demo", password="Presentasi-Lotim-2026", stdout=StringIO())
        admin = User.objects.get(email="admin@sik.test")
        self.assertTrue(admin.check_password("Presentasi-Lotim-2026"))
        self.assertFalse(admin.check_password("demo123"))

    def test_membuat_akun_dan_bisa_dijalankan_ulang(self):
        from io import StringIO

        from django.core.management import call_command
        from django.test import override_settings

        with override_settings(DEBUG=True):
            call_command("buat_akun_demo", stdout=StringIO())
            call_command("buat_akun_demo", stdout=StringIO())
        self.assertTrue(User.objects.filter(email="pimpinan@sik.test", peran="pimpinan").exists())
        self.assertTrue(User.objects.filter(email="pupr@sik.test", instansi__singkatan="PUPR").exists())
        pemohon = User.objects.get(email="pemohon@sik.test").pemohon
        self.assertEqual(pemohon.permohonan.count(), 1)
        self.assertEqual(pemohon.permohonan.get().status, "diajukan")


class InstansiWajib(DasarUji):
    def test_akun_instansi_teknis_wajib_punya_instansi(self):
        self.client.force_login(self.admin_sistem)
        r = self.client.post(
            reverse("admin:akun_user_add"),
            {"email": "dinas@uji.test", "nama": "Dinas", "peran": Peran.INSTANSI,
             "password1": SANDI, "password2": SANDI},
        )
        self.assertContains(r, "Pilih instansi")
        self.assertFalse(User.objects.filter(email="dinas@uji.test").exists())
