"""Penanda dan pembersih data demo (perintah `buat_akun_demo`).

Data demo boleh ada di server production untuk presentasi, jadi semua yang menyentuhnya harus bisa
membedakannya dari data asli:

- Akun demo = lima email di EMAIL_DEMO (bukan semua @sik.test).
- Permohonan demo = permohonan milik pemohon@sik.test. Izinnya memakai nomor `DEMO-...` dan tidak
  memakai urutan nomor izin resmi, sehingga reset tidak meninggalkan nomor resmi yang bolong.
- Contoh investasi = nama yang persis ada di NAMA_INVESTASI_CONTOH.

`hapus_data_demo()` hanya menghapus permohonan demo beserta turunannya dan contoh investasi. Akun demo
tidak dihapus (log audit merujuk ke akun itu dan tidak boleh diubah), hanya dinonaktifkan atau
diaktifkan ulang oleh perintahnya.
"""

from django.db import models, transaction

EMAIL_PEMOHON_DEMO = "pemohon@sik.test"
EMAIL_DEMO = (
    EMAIL_PEMOHON_DEMO,
    "petugas@sik.test",
    "pupr@sik.test",
    "pimpinan@sik.test",
    "admin@sik.test",
)
NAMA_INVESTASI_CONTOH = (
    "Kawasan agrowisata Sembalun (contoh)",
    "Pengolahan hasil perikanan Labuhan Haji (contoh)",
    "Wisata bahari Tanjung Ringgit (contoh)",
)


def adalah_permohonan_demo(permohonan):
    return permohonan.pemohon.user.email == EMAIL_PEMOHON_DEMO


def nomor_izin_demo(permohonan):
    return f"DEMO-{permohonan.nomor_registrasi}"


def _hapus_berkas(*berkas):
    for b in berkas:
        if b:
            b.delete(save=False)


def _hapus_catatan_tetap(qs):
    """Riwayat dan penilaian sengaja tidak bisa dihapus lewat aplikasi (CatatanTetap).
    Pengecualian ini HANYA untuk turunan permohonan demo."""
    _hapus_berkas(*(getattr(c, "berkas", None) for c in qs))
    models.QuerySet.delete(qs)


@transaction.atomic
def hapus_data_demo():
    """Hapus permohonan demo (dengan dokumen, riwayat, penilaian, izin, dan catatan Database NonOSS-nya)
    serta contoh investasi. Mengembalikan jumlah yang dihapus."""
    from basisdata.models import IzinNonOSS
    from investasi.models import PeluangInvestasi
    from perizinan.models import (
        Dokumen,
        IzinTerbit,
        PenilaianTeknis,
        Permohonan,
        RiwayatVerifikasi,
    )

    permohonan = list(Permohonan.objects.filter(pemohon__user__email=EMAIL_PEMOHON_DEMO))
    for p in permohonan:
        for catatan in IzinNonOSS.objects.filter(permohonan=p):
            _hapus_berkas(catatan.dokumen)
            catatan.delete()
        for izin in IzinTerbit.objects.filter(permohonan=p):
            _hapus_berkas(izin.berkas, izin.berkas_ttd)
            izin.delete()
        _hapus_catatan_tetap(PenilaianTeknis.objects.filter(permohonan=p))
        _hapus_catatan_tetap(RiwayatVerifikasi.objects.filter(permohonan=p))
        for dokumen in Dokumen.objects.filter(permohonan=p):
            _hapus_berkas(dokumen.berkas)
            dokumen.delete()
        p.delete()

    investasi, _ = PeluangInvestasi.objects.filter(nama__in=NAMA_INVESTASI_CONTOH).delete()
    return {"permohonan": len(permohonan), "investasi": investasi}
