import secrets

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from akun import otp
from akun.models import Pemohon, Peran, User
from core.audit import catat
from core.surel import kirim_setelah_commit


def _tautan(nama_url, pengguna):
    uid = urlsafe_base64_encode(force_bytes(pengguna.pk))
    token = default_token_generator.make_token(pengguna)
    return settings.SITUS_URL + reverse(nama_url, kwargs={"uidb64": uid, "token": token})


def _kirim(pengguna, subjek, isi):
    kirim_setelah_commit(subjek, isi, [pengguna.email], subjek)


@transaction.atomic
def daftar_mandiri(email, password, data_pemohon):
    """IZ-01: akun nonaktif sampai kode OTP yang dikirim ke email dimasukkan."""
    pengguna = User.objects.create_user(
        email=email,
        password=password,
        nama=data_pemohon["nama"],
        peran=Peran.PEMOHON,
        is_active=False,
    )
    pemohon = Pemohon.objects.create(user=pengguna, **data_pemohon)
    catat(pengguna, "akun.daftar", pemohon)
    otp.kirim(pengguna)
    return pemohon


@transaction.atomic
def daftar_oleh_loket(petugas, email, data_pemohon):
    """F-02: petugas tidak pernah tahu password; pemohon membuatnya sendiri lewat email."""
    pengguna = User.objects.create_user(
        email=email,
        password=secrets.token_urlsafe(32),
        nama=data_pemohon["nama"],
        peran=Peran.PEMOHON,
    )
    pemohon = Pemohon.objects.create(user=pengguna, didaftarkan_oleh=petugas, **data_pemohon)
    catat(petugas, "akun.daftar_loket", pemohon)
    _kirim(
        pengguna,
        "Akun PANDU LOTIM Anda telah dibuat",
        f"Yth. {pengguna.nama},\n\nPetugas DPMPTSP telah membuatkan akun untuk Anda.\n"
        f"Buat password melalui tautan berikut:\n{_tautan('akun:reset_konfirmasi', pengguna)}\n",
    )
    return pemohon


def aktifkan(pengguna):
    pengguna.is_active = True
    pengguna.save(update_fields=["is_active", "is_staff"])
    catat(pengguna, "akun.aktivasi", pengguna)
