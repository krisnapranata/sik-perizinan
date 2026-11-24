from django.urls import reverse
from django.utils import timezone

from laporan import ekspor
from laporan.services import ringkasan
from perizinan.tests.dasar import DasarUji


class Laporan(DasarUji):
    def data(self):
        hari_ini = timezone.localdate()
        return ringkasan(hari_ini.year, hari_ini.month)

    def test_ringkasan(self):
        self.terbit()
        d = self.data()
        self.assertEqual(d["total"], 1)
        self.assertEqual(d["per_status"], [("Terbit", 1)])
        self.assertEqual(d["per_jenis"], [("KKPR Nonberusaha", 1)])
        self.assertEqual(
            {v["nama"]: v["total"] for v in d["per_verifikator"]},
            {"petugas": 2, "pupr": 1},  # teruskan + terbit; penilaian
        )
        self.assertEqual(
            [t[0] for t in d["lama_tahap"]], ["Diajukan", "Penilaian teknis", "Disetujui"]
        )
        self.assertEqual(d["lama_proses"]["jumlah"], 1)
        self.assertIsNotNone(d["lama_proses"]["rata_hari"])

    def test_ekspor(self):
        self.terbit()
        self.assertTrue(ekspor.ke_pdf(self.data()).startswith(b"%PDF"))
        self.assertTrue(ekspor.ke_excel(self.data()).startswith(b"PK"))

    def test_akses(self):
        for nama in ("dasbor", "ekspor_excel", "ekspor_pdf"):
            url = reverse(f"laporan:{nama}")
            self.client.force_login(self.pemohon.user)
            self.assertEqual(self.client.get(url).status_code, 403)
            self.client.force_login(self.penilai)
            self.assertEqual(self.client.get(url).status_code, 403)
            for boleh in (self.pimpinan, self.petugas, self.admin_sistem):
                self.client.force_login(boleh)
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_bulan_tidak_valid_memakai_bulan_ini(self):
        self.client.force_login(self.pimpinan)
        r = self.client.get(reverse("laporan:dasbor"), {"bulan": "abc"})
        self.assertEqual(r.status_code, 200)

    def test_tidak_ada_data_pribadi(self):
        self.terbit()
        self.client.force_login(self.pimpinan)
        r = self.client.get(reverse("laporan:dasbor"))
        self.assertNotContains(r, self.pemohon.nama)
        self.assertNotContains(r, self.pemohon.nik)
