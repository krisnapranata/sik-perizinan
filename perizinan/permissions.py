"""Semua aturan akses permohonan dan berkas. View tidak mengecek peran sendiri."""

from django.db.models import Q

from akun.models import Peran
from perizinan.models import Permohonan, StatusPermohonan

S = StatusPermohonan


def permohonan_terlihat(pengguna):
    """Queryset permohonan yang boleh dilihat.

    - Petugas DPMPTSP: semua yang sudah diajukan, plus draf yang ia buat untuk pemohon.
    - Instansi teknis: hanya yang pernah diteruskan ke instansinya (PRD 6.3).
    - Pemohon: miliknya sendiri.
    - Pimpinan dan Admin Sistem: tidak melihat data rinci; cukup laporan agregat.
    """
    semua = Permohonan.objects.select_related("pemohon", "jenis_izin", "kecamatan")
    if pengguna.peran == Peran.PETUGAS:
        return semua.filter(~Q(status=S.DRAF) | Q(dibuat_oleh=pengguna))
    if pengguna.peran == Peran.INSTANSI and pengguna.instansi_id:
        return semua.filter(
            Q(instansi_penilai_id=pengguna.instansi_id)
            | Q(penilaian__instansi_id=pengguna.instansi_id)
        ).distinct()
    if pengguna.peran == Peran.PEMOHON:
        return semua.filter(pemohon__user=pengguna)
    return semua.none()


def bisa_lihat(pengguna, permohonan):
    return permohonan_terlihat(pengguna).filter(pk=permohonan.pk).exists()


def bisa_perbaiki(pengguna, permohonan):
    if not permohonan.bisa_diperbaiki:
        return False
    if permohonan.pemohon.user_id == pengguna.pk:
        return True
    return pengguna.peran == Peran.PETUGAS and permohonan.dibuat_oleh_id == pengguna.pk


def bisa_verifikasi(pengguna, permohonan):
    """Petugas: verifikasi administrasi (Diajukan) dan penerbitan (Disetujui)."""
    return pengguna.peran == Peran.PETUGAS and permohonan.status in (S.DIAJUKAN, S.DISETUJUI)


def bisa_cek_dokumen(pengguna, permohonan):
    return pengguna.peran == Peran.PETUGAS and permohonan.status == S.DIAJUKAN


def bisa_nilai(pengguna, permohonan):
    """IZ-05: hanya instansi yang dituju, selama permohonan dalam penilaian teknis."""
    return (
        pengguna.peran == Peran.INSTANSI
        and pengguna.instansi_id is not None
        and permohonan.status == S.PENILAIAN_TEKNIS
        and permohonan.instansi_penilai_id == pengguna.instansi_id
    )


def bisa_lihat_laporan(pengguna):
    return pengguna.is_superuser or pengguna.peran in (Peran.PETUGAS, Peran.PIMPINAN, Peran.ADMIN)


def bisa_ganti_dokumen_izin(pengguna, permohonan):
    return pengguna.peran == Peran.PETUGAS and permohonan.status == S.TERBIT
