"""Kirim email setelah transaksi selesai. Galat SMTP dicatat di log, tidak menggagalkan request."""

import logging

from django.core.mail import send_mail
from django.db import transaction

logger = logging.getLogger("sik.email")


def kirim_setelah_commit(subjek, isi, tujuan, keterangan):
    def _kirim():
        try:
            send_mail(subjek, isi, None, tujuan)
        except Exception:
            # Muncul di `docker compose logs web`; lihat docs/PANDUAN_EMAIL.md bagian masalah umum.
            logger.exception("Email %s ke %s gagal dikirim.", keterangan, ", ".join(tujuan))

    if tujuan:
        transaction.on_commit(_kirim)
