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
