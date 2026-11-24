"""IZ-10: kirim pengingat batas waktu layanan. Jalankan harian lewat cron, misalnya:

    0 7 * * 1-5 cd /opt/sik && docker compose exec -T web python manage.py pengingat_sla
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from akun.models import Peran, User
from perizinan import notifikasi
from perizinan.models import Permohonan, StatusPermohonan

S = StatusPermohonan


def jatuh_tempo(sisa_hari=1):
    """Permohonan aktif yang sudah lewat batas atau tinggal `sisa_hari` lagi."""
    ambang = timezone.now() + timedelta(days=sisa_hari)
    hasil = []
    aktif = Permohonan.objects.filter(
        status__in=[S.DIAJUKAN, S.PENILAIAN_TEKNIS, S.DISETUJUI], diajukan_pada__isnull=False
    ).select_related("jenis_izin")
    for p in aktif:
        if p.batas_layanan <= ambang:
            hasil.append(p)
    return hasil


class Command(BaseCommand):
    help = "Mengirim email pengingat permohonan yang lewat atau mendekati batas waktu layanan."

    def add_arguments(self, parser):
        parser.add_argument("--sisa-hari", type=int, default=1)

    def handle(self, *args, sisa_hari, **options):
        daftar = jatuh_tempo(sisa_hari)
        petugas = [p for p in daftar if p.status in (S.DIAJUKAN, S.DISETUJUI)]
        per_instansi = {}
        for p in daftar:
            if p.status == S.PENILAIAN_TEKNIS and p.instansi_penilai_id:
                per_instansi.setdefault(p.instansi_penilai_id, []).append(p)

        dikirim = 0
        with transaction.atomic():
            if petugas:
                for email in User.objects.filter(peran=Peran.PETUGAS, is_active=True).values_list(
                    "email", flat=True
                ):
                    notifikasi.pengingat_sla(email, petugas)
                    dikirim += 1
            for instansi_id, isi in per_instansi.items():
                for email in User.objects.filter(
                    peran=Peran.INSTANSI, instansi_id=instansi_id, is_active=True
                ).values_list("email", flat=True):
                    notifikasi.pengingat_sla(email, isi)
                    dikirim += 1
        self.stdout.write(f"{len(daftar)} permohonan jatuh tempo, {dikirim} email pengingat.")
