from django.urls import reverse

from akun.batas_masuk import MAKS_PER_AKUN
from perizinan.tests.dasar import DasarUji


class BatasMasuk(DasarUji):
    def masuk(self, password):
        return self.client.post(
            reverse("akun:masuk"), {"username": "petugas@uji.test", "password": password}
        )

    def test_terkunci_setelah_terlalu_banyak_gagal(self):
        for _ in range(MAKS_PER_AKUN):
            self.masuk("salah")
        r = self.masuk("SandiUji-9x!")
        self.assertContains(r, "Terlalu banyak percobaan")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_berhasil_menghapus_hitungan(self):
        for _ in range(MAKS_PER_AKUN - 1):
            self.masuk("salah")
        self.assertEqual(self.masuk("SandiUji-9x!").status_code, 302)
        self.client.logout()
        for _ in range(MAKS_PER_AKUN - 1):
            self.masuk("salah")
        self.assertEqual(self.masuk("SandiUji-9x!").status_code, 302)
