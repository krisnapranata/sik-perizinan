"""Notifikasi perubahan status (PRD IZ-08). Email; WhatsApp menyusul bila gateway tersedia."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse

from perizinan.models import TemplateEmail

logger = logging.getLogger(__name__)


def _isi(teks, nilai):
    # replace, bukan str.format: template ditulis admin dan tidak boleh mengakses atribut objek.
    for kunci, isi in nilai.items():
        teks = teks.replace("{" + kunci + "}", isi)
    return teks


def _tautan(permohonan):
    return settings.SITUS_URL + reverse("perizinan:detail", args=[permohonan.nomor_registrasi])


def _kirim_setelah_commit(subjek, isi, tujuan, keterangan):
    def _kirim():
        try:
            send_mail(subjek, isi, None, tujuan)
        except Exception:
            logger.exception("Email %s gagal.", keterangan)

    if tujuan:
        transaction.on_commit(_kirim)


def kirim_email(permohonan, kode):
    """Dijalankan setelah commit; kegagalan SMTP tidak membatalkan proses."""
    template = TemplateEmail.objects.filter(kode=kode).first()
    if template is None:
        logger.warning("Template email %s belum ada.", kode)
        return
    nilai = {
        "nama": permohonan.pemohon.nama,
        "nomor": permohonan.nomor_registrasi,
        "jenis_izin": permohonan.jenis_izin.nama,
        "catatan": permohonan.catatan_terakhir,
        "tautan": _tautan(permohonan),
    }
    _kirim_setelah_commit(
        _isi(template.subjek, nilai),
        _isi(template.isi, nilai),
        [permohonan.pemohon.user.email],
        f"{kode} permohonan {permohonan.pk}",
    )


def _email_peran(**filter_pengguna):
    from akun.models import User

    return list(
        User.objects.filter(is_active=True, **filter_pengguna).values_list("email", flat=True)
    )


def kabari_instansi(permohonan):
    """Instansi teknis diberi tahu ada permohonan yang menunggu penilaiannya."""
    from akun.models import Peran

    _kirim_setelah_commit(
        f"Permohonan {permohonan.nomor_registrasi} menunggu penilaian teknis",
        f"Permohonan {permohonan.jenis_izin.nama} nomor {permohonan.nomor_registrasi} "
        f"diteruskan ke instansi Anda untuk penilaian teknis.\n\nBuka: {_tautan(permohonan)}\n",
        _email_peran(peran=Peran.INSTANSI, instansi=permohonan.instansi_penilai),
        f"instansi permohonan {permohonan.pk}",
    )


def pengingat_sla(penerima, daftar_permohonan):
    """IZ-10: satu email berisi semua permohonan yang lewat atau mendekati batas layanan."""
    baris = "\n".join(
        f"- {p.nomor_registrasi} ({p.jenis_izin.nama}, {p.get_status_display()}), "
        f"batas {p.batas_layanan:%d-%m-%Y}: {_tautan(p)}"
        for p in daftar_permohonan
    )
    _kirim_setelah_commit(
        f"Pengingat batas waktu layanan: {len(daftar_permohonan)} permohonan",
        "Permohonan berikut sudah lewat atau mendekati batas waktu layanan:\n\n" + baris + "\n",
        [penerima],
        f"pengingat SLA ke {penerima}",
    )
