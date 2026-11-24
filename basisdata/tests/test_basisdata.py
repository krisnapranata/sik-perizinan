"""Data uji rekaan dengan format seperti ekspor OSS-RBA. Jangan memakai data usaha sungguhan."""

import io
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook

from basisdata import kueri
from basisdata.impor import BarisSalah, impor, tanggal
from basisdata.models import (
    IzinNonOSS,
    JenisIzinNonOSS,
    Kecamatan,
    ProyekOSS,
    StatusIzin,
)
from core.models import LogAudit
from perizinan.tests.dasar import DasarUji

JUDUL = [
    "No.", "Id Proyek", "Uraian_Jenis_Proyek", "Nib", "Nama Perusahaan", "Tanggal Terbit Oss",
    "Uraian Status Penanaman Modal", "Uraian Jenis Perusahaan", "Uraian Risiko Proyek",
    "nama_proyek", "Uraian Skala Usaha", "Alamat Usaha", "Kab Kota Usaha", "kecamatan_usaha",
    "kelurahan_usaha", "Day of Tanggal Pengajuan Proyek", "Kbli", "Judul Kbli",
    "KL/Sektor Pembina", "luas_tanah", "satuan_tanah", "Jumlah Investasi", "TKI",
]


def baris(no, id_proyek, nib, nama, kec, kbli="03112", terbit="04/10/2021",
          pengajuan="6 Juni 2022", investasi=100_000_000, tki=3):
    return [str(no), id_proyek, "Utama", nib, nama, terbit, "PMDN", "Perorangan", "Rendah",
            f"Proyek {nama}", "Usaha Mikro", "Jl. Rekaan", "Kab. Lombok Timur", kec, "Desa Uji",
            pengajuan, kbli, "Judul rekaan", "Kementerian Rekaan", "200", "m2", investasi, tki]


def xlsx(*isi):
    buku = Workbook()
    lembar = buku.active
    lembar.append(JUDUL)
    for b in isi:
        lembar.append(b)
    keluaran = io.BytesIO()
    buku.save(keluaran)
    return SimpleUploadedFile("ekspor-oss.xlsx", keluaran.getvalue())


DATA = [
    baris(1, "R-UJI-1", "9120000000001", "UD. Satu", "Masbagik"),
    baris(2, "R-UJI-2", "9120000000002", "UD. Dua", "Sakra Timur", kbli=47215, terbit="2022-03-05"),
    baris(3, "R-UJI-3", "9120000000002", "UD. Dua", "KEC. SAKRA TIMUR", kbli="55110",
          terbit=None, pengajuan="21 Oktober 2023"),
]


class Tanggal(DasarUji):
    def test_format_campuran(self):
        self.assertEqual(tanggal("04/10/2018", "x"), date(2018, 10, 4))
        self.assertEqual(tanggal("6 Juni 2022", "x"), date(2022, 6, 6))
        self.assertEqual(tanggal("2022-06-06", "x"), date(2022, 6, 6))
        self.assertEqual(tanggal(44718, "x"), date(2022, 6, 6))
        self.assertIsNone(tanggal("", "x"))
        with self.assertRaises(BarisSalah):
            tanggal("31/02/2020", "x")


class Impor(DasarUji):
    def test_impor_dan_rekap(self):
        hasil, catatan = impor(xlsx(*DATA), self.petugas)
        self.assertEqual((hasil.baru, hasil.galat), (3, []))
        p2 = ProyekOSS.objects.get(id_proyek="R-UJI-2")
        self.assertEqual(p2.kbli_id, "47215")
        self.assertEqual(p2.kbli.sektor, "perdagangan")
        self.assertEqual(p2.tahun, 2022)
        p3 = ProyekOSS.objects.get(id_proyek="R-UJI-3")
        self.assertEqual(p3.tahun, 2023)  # tanggal terbit kosong -> tanggal pengajuan
        self.assertEqual(p3.kecamatan.nama, "Sakra Timur")
        self.assertEqual(p3.kbli.sektor, "pariwisata")
        r = kueri.rekap_oss(ProyekOSS.objects.all())
        self.assertEqual((r["usaha"], r["proyek"], r["investasi"], r["tki"]), (2, 3, 300_000_000, 9))
        self.assertEqual(catatan.baru, 3)

    def test_nol_di_depan_kbli_dilengkapi(self):
        impor(xlsx(baris(1, "R-UJI-9", "9120000000009", "UD. Sembilan", "Aikmel", kbli=3112)),
              self.petugas)
        self.assertEqual(ProyekOSS.objects.get().kbli_id, "03112")

    def test_impor_ulang_tidak_menggandakan_dan_status_izin_tetap(self):
        impor(xlsx(*DATA), self.petugas)
        p = ProyekOSS.objects.get(id_proyek="R-UJI-1")
        p.status_izin = StatusIzin.DICABUT
        p.save()
        ubah = list(DATA)
        ubah[0] = baris(1, "R-UJI-1", "9120000000001", "UD. Satu", "Masbagik", investasi=5)
        hasil, _ = impor(xlsx(*ubah), self.petugas)
        self.assertEqual((hasil.baru, hasil.diperbarui, hasil.tetap), (0, 1, 2))
        p.refresh_from_db()
        self.assertEqual((p.investasi, p.status_izin), (5, StatusIzin.DICABUT))
        self.assertEqual(ProyekOSS.objects.count(), 3)

    def test_baris_salah_dilaporkan_baris_lain_tetap_masuk(self):
        hasil, _ = impor(xlsx(
            DATA[0],
            baris(2, "R-UJI-X", "123", "UD. NIB Salah", "Masbagik"),
            baris(3, "R-UJI-Y", "9120000000005", "UD. Luar", "Mataram"),
            baris(4, "R-UJI-1", "9120000000001", "UD. Satu", "Masbagik"),
            baris(5, "R-UJI-Z", "9120000000006", "UD. Tanggal", "Masbagik", terbit="kemarin"),
        ), self.petugas)
        self.assertEqual(hasil.baru, 1)
        self.assertEqual([n for n, _ in hasil.galat], [3, 4, 5, 6])
        self.assertIn("NIB", hasil.galat[0][1])
        self.assertIn("Kecamatan", hasil.galat[1][1])
        self.assertIn("ganda", hasil.galat[2][1])

    def test_kolom_wajib_hilang_ditolak(self):
        buku = Workbook()
        buku.active.append(["Nama Perusahaan", "Kecamatan"])
        keluaran = io.BytesIO()
        buku.save(keluaran)
        self.client.force_login(self.petugas)
        r = self.client.post(reverse("basisdata:oss_impor"),
                             {"berkas": SimpleUploadedFile("x.xlsx", keluaran.getvalue())})
        self.assertContains(r, "Id Proyek")
        self.assertEqual(ProyekOSS.objects.count(), 0)


class Akses(DasarUji):
    def setUp(self):
        impor(xlsx(*DATA), self.petugas)

    def test_data_rinci_hanya_untuk_petugas(self):
        url = reverse("basisdata:oss_daftar")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.pemohon.user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.get(reverse("basisdata:oss_impor")).status_code, 403)
        for bukan in (self.penilai, self.pimpinan, self.admin_sistem):
            self.client.force_login(bukan)
            self.assertEqual(self.client.get(url).status_code, 403)
        for petugas in (self.petugas, self.petugas_lain):
            self.client.force_login(petugas)
            self.assertContains(self.client.get(url), "UD. Satu")

    def test_statistik_publik_hanya_agregat(self):
        r = self.client.get(reverse("basisdata:statistik"))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "UD. Satu")
        self.assertNotContains(r, "9120000000001")
        self.assertContains(r, "Sakra Timur")
        r = self.client.get(reverse("beranda"))
        self.assertNotContains(r, "UD. Satu")

    def test_filter_dan_pencarian(self):
        self.client.force_login(self.petugas)
        url = reverse("basisdata:oss_daftar")
        r = self.client.get(url, {"q": "9120000000002"})
        self.assertEqual(r.context["rekap"]["proyek"], 2)
        sakra = Kecamatan.objects.get(nama="Sakra Timur").pk
        r = self.client.get(url, {"kecamatan": sakra, "tahun": 2022})
        self.assertEqual(r.context["rekap"]["proyek"], 1)
        r = self.client.get(url, {"sektor": "perikanan"})
        self.assertEqual(r.context["rekap"]["usaha"], 1)
        r = self.client.get(url, {"status_izin": "belum"})
        self.assertEqual(r.context["rekap"]["proyek"], 3)

    def test_ekspor(self):
        self.client.force_login(self.petugas)
        for nama in ("oss_ekspor", "nonoss_ekspor"):
            r = self.client.get(reverse(f"basisdata:{nama}", args=["xlsx"]), {"tahun": 2022})
            self.assertEqual(r["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            r = self.client.get(reverse(f"basisdata:{nama}", args=["pdf"]))
            self.assertTrue(r.content.startswith(b"%PDF"))
        r = self.client.get(reverse("basisdata:statistik_ekspor", args=["pdf"]))
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_ubah_status_izin_tercatat(self):
        self.client.force_login(self.petugas)
        url = reverse("basisdata:oss_detail", args=["R-UJI-1"])
        self.client.post(url, {"status_izin": "aktif"})
        self.assertEqual(ProyekOSS.objects.get(id_proyek="R-UJI-1").status_izin, "aktif")
        self.assertContains(self.client.get(url), "Belum diisi → Aktif")


class NonOSS(DasarUji):
    def test_tambah_ubah_dan_riwayat_tanpa_nik(self):
        self.client.force_login(self.petugas)
        data = {
            "jenis": JenisIzinNonOSS.objects.get(nama="KKPR Nonberusaha").pk,
            "nomor_izin": "",
            "nama_pemohon": "Pemohon Rekaan",
            "nik": "5203000000000001",
            "tanggal_permohonan": "2024-02-01",
            "status": "diproses",
            "kecamatan": Kecamatan.objects.get(nama="Selong").pk,
            "kelurahan_nama": "pancor",
        }
        self.client.post(reverse("basisdata:nonoss_tambah"), data)
        izin = IzinNonOSS.objects.get()
        self.assertEqual((izin.tahun, izin.kelurahan.nama, izin.nomor_izin), (2024, "Pancor", None))

        r = self.client.post(reverse("basisdata:nonoss_ubah", args=[izin.pk]),
                             data | {"status": "terbit"})
        self.assertContains(r, "Wajib diisi untuk izin yang terbit")
        self.client.post(reverse("basisdata:nonoss_ubah", args=[izin.pk]), data | {
            "status": "terbit", "nomor_izin": "KKPR/001/2025", "tanggal_terbit": "2025-01-10",
            "nik": "5203000000000002"})
        izin.refresh_from_db()
        self.assertEqual((izin.status, izin.tahun), ("terbit", 2025))
        log = LogAudit.objects.get(aksi="database.nonoss_ubah")
        self.assertIn("NIK pemohon diubah", log.keterangan)
        self.assertNotIn("5203000000000002", log.keterangan)
        self.assertIn("Status: Diproses → Terbit", log.keterangan)
        self.assertNotIn("Kelurahan", log.keterangan)  # hanya beda huruf besar/kecil

    def test_pemohon_tidak_bisa_menambah(self):
        self.client.force_login(self.pemohon.user)
        self.assertEqual(self.client.get(reverse("basisdata:nonoss_tambah")).status_code, 403)
