from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from akun.batas_masuk import bersihkan, catat_gagal
from core.audit import catat


@receiver(user_logged_in)
def _masuk(sender, request, user, **kwargs):
    bersihkan(user.email)
    catat(user, "akun.masuk", user)


@receiver(user_login_failed)
def _gagal(sender, credentials, **kwargs):
    catat_gagal(credentials.get("username"))
    catat(None, "akun.masuk_gagal")
