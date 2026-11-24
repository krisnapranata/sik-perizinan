"""Pencatatan log audit (F-20). Jangan menaruh isi data pribadi di keterangan."""

from contextvars import ContextVar

alamat_ip = ContextVar("alamat_ip", default=None)


def catat(pengguna, aksi, objek=None, keterangan=""):
    from core.models import LogAudit

    terautentikasi = pengguna is not None and pengguna.is_authenticated
    return LogAudit.objects.create(
        pengguna=pengguna if terautentikasi else None,
        aksi=aksi,
        objek_tipe=objek._meta.label if objek is not None else "",
        objek_id=str(objek.pk) if objek is not None else "",
        keterangan=keterangan,
        alamat_ip=alamat_ip.get(),
    )
