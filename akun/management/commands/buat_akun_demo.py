"""Akun demo untuk mencoba alur lengkap di komputer pengembang. Ditolak bila DEBUG mati."""

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from akun.models import Instansi, Pemohon, Peran, User
from basisdata.models import Kecamatan
from perizinan import services
from perizinan.forms import FormulirForm
from perizinan.models import JenisIzin

PASSWORD = "demo123"

PETUGAS = [
    ("petugas@sik.test", "Baiq Nurul Aini", Peran.PETUGAS, "Front Office dan Verifikasi"),
    ("pimpinan@sik.test", "H. Muhammad Zaini", Peran.PIMPINAN, "Kepala Dinas"),
    ("admin@sik.test", "Admin Sistem", Peran.ADMIN, "Pengelola Sistem"),
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
