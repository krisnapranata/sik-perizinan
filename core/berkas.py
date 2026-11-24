"""Pengiriman berkas privat. Selalu panggil setelah izin diperiksa."""

import mimetypes
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse

from core.audit import catat

# Hanya jenis ini yang boleh tampil langsung di browser. Isinya sudah dicek saat unggah
# (core.validators.validasi_berkas), dan Content-Type dikunci di sini plus nosniff,
# sehingga browser tidak bisa memperlakukannya sebagai halaman HTML.
JENIS_PRATINJAU = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def jenis_pratinjau(berkas):
    """'pdf', 'gambar', atau '' bila berkas tidak boleh ditampilkan langsung."""
    jenis = JENIS_PRATINJAU.get(Path(berkas.name).suffix.lower(), "")
    return {"application/pdf": "pdf", "image/jpeg": "gambar"}.get(jenis, "")


def kirim_berkas(pengguna, berkas, nama_unduhan, objek=None, tampil=False):
    if not berkas or not berkas.storage.exists(berkas.name):
        raise Http404("Berkas tidak ditemukan.")

    ekstensi = Path(berkas.name).suffix.lower()
    tampil = tampil and ekstensi in JENIS_PRATINJAU
    jenis = JENIS_PRATINJAU.get(ekstensi) or (
        mimetypes.guess_type(berkas.name)[0] or "application/octet-stream"
    )
    catat(pengguna, "berkas.lihat" if tampil else "berkas.unduh", objek)

    if settings.DEBUG:  # runserver tanpa Nginx
        respons = FileResponse(
            berkas.open("rb"),
            as_attachment=not tampil,
            filename=nama_unduhan,
            content_type=jenis,
        )
    else:
        respons = HttpResponse(content_type=jenis)
        respons["X-Accel-Redirect"] = settings.X_ACCEL_PREFIX + quote(berkas.name)
        disposisi = "inline" if tampil else "attachment"
        respons["Content-Disposition"] = f"{disposisi}; filename*=UTF-8''{quote(nama_unduhan)}"

    respons["X-Content-Type-Options"] = "nosniff"
    respons["Cache-Control"] = "private, no-store"
    if tampil:
        # Boleh disematkan di jendela pratinjau aplikasi sendiri, tidak di situs lain.
        respons["X-Frame-Options"] = "SAMEORIGIN"
    return respons


def nama_aman(nama_dasar, berkas):
    return f"{nama_dasar}{Path(berkas.name).suffix.lower()}"
