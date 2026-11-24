"""Data uji rekaan."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from akun.models import Peran, User
from basisdata.models import Kecamatan
from investasi.forms import PeluangInvestasiAdminForm
from investasi.models import PeluangInvestasi, Tingkat


def buat(nama="Agrowisata uji", **kolom):
    data = {
        "tingkat": Tingkat.POTENSI, "sektor": "pariwisata",
        "kecamatan": Kecamatan.objects.get_or_create(nama="Kecamatan Uji")[0],
        "deskripsi": "Deskripsi rekaan", "lintang": Decimal("-8.65"), "bujur": Decimal("116.53"),
    }
    data.update(kolom)
    return PeluangInvestasi.objects.create(nama=nama, **data)


class DataMinimum(TestCase):
    def test_peluang_wajib_estimasi_dan_potensi_pasar(self):
        p = buat(tingkat=Tingkat.PELUANG)
        with self.assertRaises(ValidationError) as c:
            p.full_clean()
        self.assertIn("estimasi_investasi", c.exception.message_dict)
        self.assertIn("potensi_pasar", c.exception.message_dict)

    def test_siap_tawar_wajib_luas_dan_kontak(self):
        p = buat(tingkat=Tingkat.SIAP_TAWAR, estimasi_investasi=1, potensi_pasar="ada")
        with self.assertRaises(ValidationError) as c:
            p.full_clean()
        self.assertEqual(set(c.exception.message_dict), {"luas_lahan_ha", "kontak"})

    def test_koordinat_harus_berpasangan(self):
        with self.assertRaises(ValidationError):
            buat(bujur=None).full_clean()


class FormAdmin(TestCase):
    def setUp(self):
        self.kec = Kecamatan.objects.create(nama="Kecamatan Form")

    def _form(self, koordinat):
        return PeluangInvestasiAdminForm({
            "nama": "Uji", "tingkat": "potensi", "sektor": "pertanian", "kecamatan": self.kec.pk,
            "deskripsi": "x", "tampil": "on", "koordinat": koordinat,
        })

    def test_koordinat_tempelan_google_maps_dipecah(self):
        form = self._form("-8.6512345, 116.5321")
        self.assertTrue(form.is_valid(), form.errors)
        p = form.save()
        self.assertEqual((p.lintang, p.bujur), (Decimal("-8.651235"), Decimal("116.532100")))

    def test_koordinat_tertukar_ditolak(self):
        form = self._form("116.53, -8.65")
        self.assertFalse(form.is_valid())
        self.assertIn("koordinat", form.errors)

    def test_koordinat_boleh_kosong(self):
        form = self._form("")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.save().ada_koordinat)


class HalamanPublik(TestCase):
    def setUp(self):
        self.siap = buat("Proyek siap uji", tingkat=Tingkat.SIAP_TAWAR, sektor="perikanan",
                         estimasi_investasi=2_000_000_000, potensi_pasar="ada",
                         luas_lahan_ha=Decimal(3), kontak="Kontak uji")
        self.potensi = buat("Potensi uji")
        self.tersembunyi = buat("Draf tersembunyi", tampil=False)

    def test_daftar_terbuka_tanpa_login_dan_menyembunyikan_draf(self):
        r = self.client.get(reverse("investasi:daftar"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Proyek siap uji")
        self.assertNotContains(r, "Draf tersembunyi")
        nama = [p.nama for p in r.context["daftar_peluang"]]
        self.assertEqual(nama, ["Proyek siap uji", "Potensi uji"])  # siap tawar lebih dulu

    def test_filter_sektor_dan_tingkat(self):
        r = self.client.get(reverse("investasi:daftar"), {"sektor": "perikanan"})
        self.assertEqual([p.nama for p in r.context["daftar_peluang"]], ["Proyek siap uji"])
        r = self.client.get(reverse("investasi:daftar"), {"tingkat": "potensi", "sektor": "ngawur"})
        self.assertEqual([p.nama for p in r.context["daftar_peluang"]], ["Potensi uji"])

    @override_settings(GOOGLE_MAPS_API_KEY="")
    def test_tanpa_kunci_peta_memakai_embed(self):
        r = self.client.get(reverse("investasi:daftar"))
        self.assertContains(r, "maps.google.com/maps?q=")
        self.assertNotContains(r, "maps.googleapis.com/maps/api/js")
        r = self.client.get(reverse("investasi:detail", args=[self.siap.pk]))
        self.assertContains(r, "maps.google.com/maps?q=-8.650000,116.530000")
        self.assertContains(r, "Kontak uji")

    @override_settings(GOOGLE_MAPS_API_KEY="kunci-uji")
    def test_dengan_kunci_semua_titik_di_satu_peta(self):
        r = self.client.get(reverse("investasi:daftar"))
        self.assertContains(r, "maps.googleapis.com/maps/api/js?key=kunci-uji")
        self.assertEqual(len(r.context["titik"]), 2)
        r = self.client.get(reverse("investasi:detail", args=[self.siap.pk]))
        self.assertContains(r, "maps/embed/v1/place?key=kunci-uji")

    def test_detail_draf_404(self):
        r = self.client.get(reverse("investasi:detail", args=[self.tersembunyi.pk]))
        self.assertEqual(r.status_code, 404)

    def test_nama_dari_admin_tidak_dieksekusi_di_data_peta(self):
        buat("<script>alert(1)</script>")
        r = self.client.get(reverse("investasi:daftar"))
        self.assertNotContains(r, "<script>alert(1)</script>")


class AdminHanyaAdminSistem(TestCase):
    def test_petugas_tidak_bisa_mengelola(self):
        petugas = User.objects.create_user(email="p@uji.test", password="x", nama="P", peran=Peran.PETUGAS)
        admin = User.objects.create_user(email="a@uji.test", password="x", nama="A", peran=Peran.ADMIN)
        url = reverse("admin:investasi_peluanginvestasi_add")
        self.client.force_login(petugas)
        self.assertNotEqual(self.client.get(url).status_code, 200)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(url).status_code, 200)
