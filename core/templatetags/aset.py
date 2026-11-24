"""Alamat static dengan ?v=<hash isi berkas> agar browser langsung memakai CSS/JS baru setelah deploy.

Pemakaian di template: {% load aset %} <link rel="stylesheet" href="{% aset 'css/sik.css' %}">

Nilai v = 10 karakter pertama SHA-256 isi berkas, jadi hanya berganti bila isinya berubah.
Nginx boleh menyimpan URL ber-?v= selama setahun (immutable); lihat deploy/nginx.conf.
"""

import hashlib

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()

_cache = {}


def versi_berkas(jalur):
    """Hash isi berkas static, atau '' bila berkas tidak ditemukan."""
    if not settings.DEBUG and jalur in _cache:
        return _cache[jalur]
    lokasi = finders.find(jalur)
    if not lokasi:
        versi = ""
    else:
        h = hashlib.sha256()
        with open(lokasi, "rb") as f:
            for potongan in iter(lambda: f.read(65536), b""):
                h.update(potongan)
        versi = h.hexdigest()[:10]
    _cache[jalur] = versi
    return versi


@register.simple_tag
def aset(jalur):
    url = static(jalur)
    versi = versi_berkas(jalur)
    return f"{url}?v={versi}" if versi else url
