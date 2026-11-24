from django.test import TestCase


class Sehat(TestCase):
    def test_ok_tanpa_login(self):
        r = self.client.get("/sehat/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})


class EmailGagalTercatat(TestCase):
    """Galat SMTP saat kirim OTP tidak boleh hilang tanpa jejak."""

    def test_galat_smtp_masuk_log(self):
        from unittest import mock

        from core.surel import kirim_setelah_commit

        with mock.patch("core.surel.send_mail", side_effect=OSError("SMTP mati")), \
                self.assertLogs("sik.email", level="ERROR") as log, \
                self.captureOnCommitCallbacks(execute=True):
            kirim_setelah_commit("Subjek", "Isi", ["a@uji.test"], "kode OTP")
        self.assertIn("kode OTP ke a@uji.test gagal", log.output[0])


class PanduanKhususAdmin(TestCase):
    """Halaman panduan hanya untuk Admin Sistem; peran lain ditolak, tamu diminta masuk."""

    def setUp(self):
        from akun.models import Peran, User

        self.admin = User.objects.create_user(email="adm@uji.test", password="x", nama="A", peran=Peran.ADMIN)
        self.lain = {
            peran: User.objects.create_user(email=f"{peran}@uji.test", password="x", nama=peran, peran=peran)
            for peran in (Peran.PEMOHON, Peran.PETUGAS, Peran.INSTANSI, Peran.PIMPINAN)
        }

    def test_tamu_diarahkan_ke_halaman_masuk(self):
        r = self.client.get("/panduan/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/akun/masuk/", r["Location"])

    def test_peran_selain_admin_ditolak_dan_tidak_melihat_menu(self):
        for peran, pengguna in self.lain.items():
            self.client.force_login(pengguna)
            self.assertEqual(self.client.get("/panduan/").status_code, 403, peran)
            self.assertNotContains(self.client.get("/statistik/"), 'href="/panduan/"')

    def test_admin_bisa_membaca_dan_melihat_menu(self):
        self.client.force_login(self.admin)
        r = self.client.get("/panduan/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Panduan Fitur PANDU LOTIM")
        self.assertContains(r, 'href="/panduan/"')
