"""Batas percobaan login: per akun dan per alamat IP dalam jendela waktu tertentu."""

from datetime import timedelta

from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from akun.models import PercobaanMasuk
from core.audit import alamat_ip

JENDELA = timedelta(minutes=15)
MAKS_PER_AKUN = 5
# Kantor bisa berbagi satu IP publik, jadi batas per IP lebih longgar.
MAKS_PER_IP = 30


def _email(teks):
    return (teks or "").strip().lower()[:254]


def terkunci(email):
    batas = timezone.now() - JENDELA
    baru = PercobaanMasuk.objects.filter(waktu__gte=batas)
    if baru.filter(email=_email(email)).count() >= MAKS_PER_AKUN:
        return True
    ip = alamat_ip.get()
    return bool(ip) and baru.filter(alamat_ip=ip).count() >= MAKS_PER_IP


def catat_gagal(email):
    PercobaanMasuk.objects.filter(waktu__lt=timezone.now() - JENDELA * 4).delete()
    PercobaanMasuk.objects.create(email=_email(email), alamat_ip=alamat_ip.get())


def bersihkan(email):
    PercobaanMasuk.objects.filter(email=_email(email)).delete()


PESAN_TERKUNCI = (
    "Terlalu banyak percobaan masuk yang gagal. Tunggu 15 menit lalu coba lagi, "
    "atau gunakan Lupa password."
)


class _BatasMixin:
    def clean(self):
        if terkunci(self.data.get("username")):
            raise forms.ValidationError(PESAN_TERKUNCI, code="terkunci")
        return super().clean()


class FormMasuk(_BatasMixin, AuthenticationForm):
    pass


class FormMasukAdmin(_BatasMixin, AdminAuthenticationForm):
    pass
