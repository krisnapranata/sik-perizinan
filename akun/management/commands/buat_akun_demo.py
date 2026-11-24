"""Akun demo untuk mencoba alur lengkap di komputer pengembang. Ditolak bila DEBUG mati."""

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from akun.models import Instansi, Pemohon, Peran, User
from basisdata.models import Kecamatan
from investasi.models import PeluangInvestasi, Tingkat
from perizinan import services
from perizinan.forms import FormulirForm
from perizinan.models import JenisIzin

PASSWORD = "demo123"

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
    help = "Membuat akun demo semua peran dan satu permohonan KKPR contoh (hanya saat DEBUG=1)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Ditolak: akun demo hanya untuk pengembangan (DJANGO_DEBUG=1).")

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

        self.stdout.write(self.style.SUCCESS(f"Akun demo siap. Password semua akun: {PASSWORD}"))

    def _akun(self, email, nama, **kolom):
        user, baru = User.objects.get_or_create(email=email, defaults={"nama": nama, **kolom})
        # Selalu disetel ulang agar akun demo lama ikut memakai password yang sama.
        user.set_password(PASSWORD)
        user.save()
        self.stdout.write(
            f"{'Dibuat ' if baru else 'Sudah ada'}: {email} ({user.get_peran_display()})"
        )
        return user
