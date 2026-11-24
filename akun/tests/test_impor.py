import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from akun.models import Pemohon, Peran, User
from core.models import LogAudit
from perizinan.tests.dasar import DasarUji

URL = "admin:akun_user_impor"
DEFAULT = "Default-Uji-2026!"


def csv_berkas(teks, nama="pengguna.csv"):
    return SimpleUploadedFile(nama, teks.encode("utf-8-sig"), content_type="text/csv")


def xlsx_berkas(baris):
    buku = Workbook()
    for b in baris:
        buku.active.append(b)
    keluaran = io.BytesIO()
    buku.save(keluaran)
    return SimpleUploadedFile("pengguna.xlsx", keluaran.getvalue())


class ImporPengguna(DasarUji):
    def setUp(self):
        self.client.force_login(self.admin_sistem)

    def unggah(self, berkas, password=DEFAULT):
        return self.client.post(
            reverse(URL), {"berkas": berkas, "password_default": password}
        )

    def test_csv_password_kosong_memakai_default(self):
        r = self.unggah(
            csv_berkas(
                "email;password;nama;peran;unit_kerja\n"
                "Kasi2@Uji.Test;;Kasi Dua;Kasi;Seksi\n"
                "loket2@uji.test;SandiLama-77;Loket Dua;Petugas Loket;\n"
                "kadis2@uji.test;;Kadis Dua;Kadis;\n"
            )
        )
        self.assertContains(r, "3 pengguna dibuat")
        kasi = User.objects.get(email="kasi2@uji.test")
        self.assertEqual(kasi.peran, Peran.PETUGAS)  # nama peran lama tetap diterima
        self.assertEqual(User.objects.get(email="kadis2@uji.test").peran, Peran.PIMPINAN)
        self.assertTrue(kasi.check_password(DEFAULT))
        loket = User.objects.get(email="loket2@uji.test")
        self.assertEqual(loket.peran, Peran.PETUGAS)
        self.assertTrue(loket.check_password("SandiLama-77"))
        self.assertTrue(LogAudit.objects.filter(aksi="admin.impor_berkas").exists())

    def test_excel_dengan_profil_pemohon(self):
        r = self.unggah(
            xlsx_berkas(
                [
                    ["Email", "Pass", "Nama", "Tipe", "NIK", "No HP", "Alamat", "NIB"],
                    ["p1@uji.test", None, "Pemohon Satu", "perorangan", "1234567890123456",
                     81234567890, "Alamat rekaan", "1234567890123"],
                    ["p2@uji.test", "Sandi-Lama-1", "Pemohon Dua", None, None, None, None, None],
                ]
            )
        )
        self.assertContains(r, "2 pengguna dibuat")
        p1 = Pemohon.objects.get(user__email="p1@uji.test")
        self.assertEqual(p1.hp, "081234567890")
        self.assertEqual(p1.nik, "1234567890123456")
        self.assertTrue(p1.user.check_password(DEFAULT))
        # Tanpa hp/alamat: hanya akun, profil dilengkapi saat mengajukan izin.
        self.assertFalse(Pemohon.objects.filter(user__email="p2@uji.test").exists())

    def test_satu_baris_salah_tidak_ada_yang_disimpan(self):
        r = self.unggah(
            csv_berkas(
                "email,nama,peran\nbaik@uji.test,Baik,kasi\nbukan-email,Salah,kasi\n"
                "baik3@uji.test,Baik,raja\n"
            )
        )
        self.assertContains(r, "Tidak ada pengguna yang disimpan")
        self.assertContains(r, "tidak dikenal")
        self.assertFalse(User.objects.filter(email="baik@uji.test").exists())

    def test_email_terdaftar_dilewati(self):
        r = self.unggah(csv_berkas("email,nama\npetugas@uji.test,Ganti Nama\nbaru@uji.test,Baru\n"))
        self.assertContains(r, "1 pengguna dibuat")
        self.assertContains(r, "email sudah terdaftar")
        self.assertEqual(User.objects.get(email="petugas@uji.test").nama, "petugas")

    def test_password_default_lemah_ditolak(self):
        self.unggah(csv_berkas("email,nama\nx@uji.test,X\n"), password="123")
        self.assertFalse(User.objects.filter(email="x@uji.test").exists())

    def test_xls_lama_dan_tanpa_kolom_email_ditolak(self):
        r = self.unggah(SimpleUploadedFile("lama.xls", b"\xd0\xcf\x11\xe0"))
        self.assertContains(r, "tidak didukung")
        r = self.unggah(csv_berkas("nama\nX\n"))
        self.assertContains(r, "Kolom &#x27;email&#x27; tidak ditemukan")

    def test_template_bisa_diunduh_dan_diimpor_ulang(self):
        r = self.client.get(reverse("admin:akun_user_impor_template", args=["xlsx"]))
        self.assertEqual(r.status_code, 200)
        load_workbook(io.BytesIO(r.content))
        r = self.client.get(reverse("admin:akun_user_impor_template", args=["csv"]))
        r = self.unggah(SimpleUploadedFile("t.csv", r.content))
        self.assertContains(r, "2 pengguna dibuat")

    def test_hanya_admin_sistem(self):
        self.client.force_login(self.petugas)
        r = self.client.get(reverse(URL))
        self.assertNotEqual(r.status_code, 200)


class WajibGantiPassword(DasarUji):
    def setUp(self):
        self.client.force_login(self.admin_sistem)
        self.client.post(
            reverse(URL),
            {
                "berkas": csv_berkas(
                    "email,password,nama,peran\nbaru@uji.test,,Baru,kasi\n"
                    "lama@uji.test,SandiLama-77,Lama,kasi\n"
                ),
                "password_default": DEFAULT,
            },
        )
        self.client.logout()

    def test_hanya_password_default_yang_wajib_diganti(self):
        self.assertTrue(User.objects.get(email="baru@uji.test").wajib_ganti_password)
        self.assertFalse(User.objects.get(email="lama@uji.test").wajib_ganti_password)

    def test_diarahkan_ke_ganti_password_sampai_diganti(self):
        self.client.login(email="baru@uji.test", password=DEFAULT)
        tujuan = reverse("akun:ganti_password")
        self.assertRedirects(self.client.get(reverse("perizinan:antrean")), tujuan)
        self.assertRedirects(self.client.get("/admin/"), tujuan, fetch_redirect_response=False)

        # Password baru sama dengan yang lama ditolak.
        r = self.client.post(
            tujuan,
            {"old_password": DEFAULT, "new_password1": DEFAULT, "new_password2": DEFAULT},
        )
        self.assertContains(r, "harus berbeda")

        r = self.client.post(
            tujuan,
            {
                "old_password": DEFAULT,
                "new_password1": "SandiBaru-Kuat-91",
                "new_password2": "SandiBaru-Kuat-91",
            },
        )
        self.assertRedirects(r, reverse("beranda"), fetch_redirect_response=False)
        pengguna = User.objects.get(email="baru@uji.test")
        self.assertFalse(pengguna.wajib_ganti_password)
        self.assertTrue(pengguna.check_password("SandiBaru-Kuat-91"))
        # Sesi tetap login dan halaman lain bisa dibuka.
        self.assertEqual(self.client.get(reverse("perizinan:antrean")).status_code, 200)

    def test_pengguna_lama_tidak_terganggu(self):
        self.client.login(email="lama@uji.test", password="SandiLama-77")
        self.assertEqual(self.client.get(reverse("perizinan:antrean")).status_code, 200)
