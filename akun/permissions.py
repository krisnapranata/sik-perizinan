from akun.models import Peran


def bisa_kelola_pemohon(pengguna, pemohon):
    """Petugas DPMPTSP melayani pemohon yang datang ke kantor (layanan berbantuan)."""
    return pemohon.user_id == pengguna.pk or pengguna.peran == Peran.PETUGAS


def bisa_unduh_bukti_nib(pengguna, pemohon):
    if pemohon.user_id == pengguna.pk:
        return True
    if pengguna.peran == Peran.PETUGAS:
        if pemohon.didaftarkan_oleh_id == pengguna.pk:
            return True
        from perizinan.models import StatusPermohonan

        return pemohon.permohonan.exclude(status=StatusPermohonan.DRAF).exists()
    return False
