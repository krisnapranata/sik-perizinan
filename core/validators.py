from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

# F-03: PDF/JPG. Isi diperiksa juga agar ekstensi palsu tertolak.
TANDA_BERKAS = {
    ".pdf": b"%PDF-",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}


def validasi_berkas(berkas):
    if berkas.size > settings.UKURAN_MAKS_BERKAS:
        batas = settings.UKURAN_MAKS_BERKAS // (1024 * 1024)
        raise ValidationError(f"Ukuran berkas melebihi {batas} MB.")

    ekstensi = Path(berkas.name).suffix.lower()
    tanda = TANDA_BERKAS.get(ekstensi)
    if tanda is None:
        raise ValidationError("Format berkas harus PDF atau JPG.")

    berkas.seek(0)
    awal = berkas.read(len(tanda))
    berkas.seek(0)
    if awal != tanda:
        raise ValidationError("Isi berkas tidak sesuai dengan formatnya.")
