"""Akun dan data demo untuk mencoba alur lengkap.

Komputer pengembang (DJANGO_DEBUG=1): password semua akun demo `demo123`.
Server production (DEBUG mati): password WAJIB ditentukan sendiri, karena `demo123` tertulis di README
publik dan akun admin@sik.test berperan Admin Sistem:

    docker compose exec web python manage.py buat_akun_demo          # ditanya password (tidak tampil)
"""

import getpass
import sys

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from akun.models import Instansi, Pemohon, Peran, User
from basisdata.models import Kecamatan
from investasi.models import PeluangInvestasi, Tingkat
from perizinan import services
from perizinan.forms import FormulirForm
from perizinan.models import JenisIzin

PASSWORD_PENGEMBANGAN = "demo123"

PETUGAS = [
    ("petugas@sik.test", "Baiq Nurul Aini", Peran.PETUGAS, "Front Office dan Verifikasi"),
    ("pimpinan@sik.test", "H. Muhammad Zaini", Peran.PIMPINAN, "Kepala Dinas"),
    ("admin@sik.test", "Admin Sistem", Peran.ADMIN, "Pengelola Sistem"),
]

# Contoh Pusat Informasi Investasi (data rekaan, ditandai "(contoh)") agar peta bisa dicoba.
INVESTASI_CONTOH = [
    {
        "nama": "Kawasan agrowisata Sembalun (contoh)", "tingkat": Tingkat.SIAP_TAWAR,
        "sektor": "pariwisata", "kecamatan": "Sembalun", "lokasi": "Desa Sembalun Lawang",
        "deskripsi": "Data contoh. Kebun stroberi dan sayur dataran tinggi di kaki Rinjani untuk wisata petik.",
        "luas_lahan_ha": 12, "estimasi_investasi": 15_000_000_000,
        "potensi_pasar": "Data contoh. Pendaki Rinjani dan wisatawan domestik.",
        "kontak": "Bidang Promosi Penanaman Modal DPMPTSP", "lintang": "-8.357700", "bujur": "116.529700",
    },
    {
        "nama": "Pengolahan hasil perikanan Labuhan Haji (contoh)", "tingkat": Tingkat.PELUANG,
        "sektor": "perikanan", "kecamatan": "Labuhan Haji", "lokasi": "Pelabuhan perikanan",
        "deskripsi": "Data contoh. Cold storage dan pengolahan ikan tangkap nelayan setempat.",
        "estimasi_investasi": 8_500_000_000, "potensi_pasar": "Data contoh. Pasar Lombok dan Bali.",
        "lintang": "-8.673600", "bujur": "116.567900",
    },
    {
        "nama": "Wisata bahari Tanjung Ringgit (contoh)", "tingkat": Tingkat.POTENSI,
        "sektor": "pariwisata", "kecamatan": "Jerowaru", "lokasi": "Desa Sekaroh",
        "deskripsi": "Data contoh. Tebing dan pantai di ujung tenggara Lombok yang belum dikaji.",
        "lintang": "-8.866000", "bujur": "116.583000",
    },
]

# PDF minimal yang valid, hanya untuk bukti contoh.
PDF_CONTOH = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def _pdf(nama):
    return ContentFile(PDF_CONTOH, name=nama)


class Command(BaseCommand):
    help = (
        "Membuat akun demo semua peran, satu permohonan KKPR contoh, dan contoh potensi investasi. "
        "Di production password wajib ditentukan sendiri."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            help="Password semua akun demo. Di production lebih aman dikosongkan agar ditanya "
                 "tanpa tampil di layar dan riwayat shell.",
        )

    def handle(self, *args, **options):
        self.password = self._tentukan_password(options.get("password"))

        with transaction.atomic():
            for email, nama, peran, unit in PETUGAS:
                self._akun(email, nama, peran=peran, unit_kerja=unit)
            jenis = JenisIzin.objects.get(kode="KKPR-NB")
            self._akun("pupr@sik.test", "Lalu Ahmad Fauzi", peran=Peran.INSTANSI,
                       instansi=jenis.instansi or Instansi.objects.first())

            user = self._akun("pemohon@sik.test", "Baiq Rinjani", peran=Peran.PEMOHON)
            pemohon, _ = Pemohon.objects.get_or_create(
                user=user,
                defaults={
                    "tipe": "perorangan",
                    "nama": "Baiq Rinjani",
                    "nik": "5203010101900001",
                    "hp": "081234567890",
                    "alamat": "Jl. Contoh No. 1, Selong, Lombok Timur",
                },
            )
            if not pemohon.permohonan.exists():
                p = services.buat_permohonan(pemohon, jenis, user)
                form = FormulirForm(
                    {
                        "lokasi_alamat": "Dusun Contoh",
                        "kecamatan": Kecamatan.objects.get(nama="Selong").pk,
                        "kelurahan_nama": "Pancor",
                        "luas_tanah": "250",
                        "rencana_kegiatan": "Rumah tinggal",
                    },
                    instance=p,
                )
                form.is_valid()
                services.simpan_formulir(p, form, user)
                for syarat in p.syarat_berlaku():
                    services.unggah_dokumen(p, syarat, _pdf(f"{syarat.nama}.pdf"), user)
                services.kirim(p, user)
                self.stdout.write(f"Permohonan contoh {p.nomor_registrasi} sudah diajukan.")

            for data in INVESTASI_CONTOH:
                data = dict(data, kecamatan=Kecamatan.objects.get(nama=data["kecamatan"]))
                _, baru = PeluangInvestasi.objects.get_or_create(nama=data["nama"], defaults=data)
                if baru:
                    self.stdout.write(f"Contoh investasi dibuat: {data['nama']}")

        if settings.DEBUG:
            self.stdout.write(self.style.SUCCESS(f"Akun demo siap. Password semua akun: {self.password}"))
        else:
            self.stdout.write(self.style.SUCCESS(
                "Akun demo siap dengan password yang Anda tentukan. Nonaktifkan akun @sik.test di "
                "Pengaturan sistem → Pengguna bila demo sudah selesai."
            ))

    def _tentukan_password(self, password):
        if settings.DEBUG:
            return password or PASSWORD_PENGEMBANGAN
        if not password:
            if not sys.stdin.isatty():
                raise CommandError(
                    "Di production password akun demo wajib ditentukan. Jalankan dengan terminal "
                    "interaktif (docker compose exec web python manage.py buat_akun_demo) atau --password."
                )
            password = getpass.getpass("Password untuk semua akun demo: ")
            if password != getpass.getpass("Ulangi password: "):
                raise CommandError("Password tidak sama.")
        if password == PASSWORD_PENGEMBANGAN:
            raise CommandError("Ditolak: 'demo123' tertulis di README publik. Pakai password lain.")
        try:
            validate_password(password)
        except ValidationError as e:
            raise CommandError("Password terlalu lemah: " + " ".join(e.messages)) from None
        return password

    def _akun(self, email, nama, **kolom):
        user, baru = User.objects.get_or_create(email=email, defaults={"nama": nama, **kolom})
        # Selalu disetel ulang agar akun demo lama ikut memakai password yang sama.
        user.set_password(self.password)
        user.save()
        self.stdout.write(
            f"{'Dibuat ' if baru else 'Sudah ada'}: {email} ({user.get_peran_display()})"
        )
        return user
