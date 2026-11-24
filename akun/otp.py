"""Kode OTP registrasi (PRD IZ-01). Dikirim ke email; WhatsApp menyusul bila gateway tersedia."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from akun.models import KodeOTP
from core.surel import kirim_setelah_commit

BERLAKU = timedelta(minutes=15)
MAKS_PERCOBAAN = 5
JEDA_KIRIM_ULANG = timedelta(seconds=60)


class OTPGagal(Exception):
    """Pesannya aman ditampilkan ke pengguna."""


def _hash(kode):
    return hmac.new(settings.SECRET_KEY.encode(), kode.encode(), hashlib.sha256).hexdigest()


def kirim(pengguna):
    terakhir = pengguna.kode_otp.first()
    if terakhir and timezone.now() - terakhir.dibuat < JEDA_KIRIM_ULANG:
        raise OTPGagal("Tunggu satu menit sebelum meminta kode baru.")
    kode = f"{secrets.randbelow(10**6):06d}"
    pengguna.kode_otp.filter(dipakai=False).update(dipakai=True)  # kode lama tidak berlaku
    KodeOTP.objects.create(
        user=pengguna, kode_hash=_hash(kode), kedaluwarsa=timezone.now() + BERLAKU
    )
    isi = (
        f"Yth. {pengguna.nama},\n\nKode verifikasi akun PANDU LOTIM Anda: {kode}\n\n"
        f"Kode berlaku {int(BERLAKU.total_seconds() // 60)} menit. "
        "Jangan berikan kode ini kepada siapa pun, termasuk petugas.\n"
    )
    kirim_setelah_commit("Kode verifikasi PANDU LOTIM", isi, [pengguna.email], "kode OTP")


def periksa(pengguna, kode):
    """Kembalikan True bila kode benar; akun diaktifkan oleh pemanggil.

    Galat dilempar SETELAH transaksi selesai, agar hitungan percobaan yang gagal tetap
    tersimpan (exception di dalam atomic() akan membatalkannya).
    """
    galat = _periksa(pengguna, kode)
    if galat:
        raise OTPGagal(galat)
    return True


@transaction.atomic
def _periksa(pengguna, kode):
    otp = (
        KodeOTP.objects.select_for_update()
        .filter(user=pengguna, dipakai=False)
        .order_by("-dibuat")
        .first()
    )
    if otp is None or otp.kedaluwarsa < timezone.now():
        return "Kode sudah kedaluwarsa. Minta kode baru."
    if otp.percobaan >= MAKS_PERCOBAAN:
        return "Terlalu banyak percobaan. Minta kode baru."
    if not hmac.compare_digest(otp.kode_hash, _hash(kode.strip())):
        otp.percobaan += 1
        otp.save(update_fields=["percobaan"])
        return "Kode salah."
    otp.dipakai = True
    otp.save(update_fields=["dipakai"])
    return None
