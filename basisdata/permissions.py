"""Akses Database Perizinan. Data rinci hanya untuk petugas DPMPTSP (PRD DB-08)."""

from akun.models import Peran


def bisa_lihat_database(pengguna):
    """PRD DB-08 dan bagian 3: data rinci dan dokumen hanya untuk Petugas DPMPTSP."""
    return pengguna.is_authenticated and (pengguna.is_superuser or pengguna.peran == Peran.PETUGAS)


def bisa_kelola_database(pengguna):
    """Impor OSS, input/edit NonOSS, ubah status izin."""
    return bisa_lihat_database(pengguna)
