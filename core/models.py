from django.conf import settings
from django.db import models


class TidakBisaDihapus(Exception):
    pass


class QuerySetTetap(models.QuerySet):
    def delete(self):
        raise TidakBisaDihapus("Catatan audit tidak bisa dihapus.")

    def update(self, **kwargs):
        raise TidakBisaDihapus("Catatan audit tidak bisa diubah.")


class CatatanTetap(models.Model):
    """Dasar model jejak audit: hanya bisa ditambah, tidak bisa diubah atau dihapus."""

    objects = QuerySetTetap.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise TidakBisaDihapus("Catatan audit tidak bisa diubah.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TidakBisaDihapus("Catatan audit tidak bisa dihapus.")


class LogAudit(CatatanTetap):
    waktu = models.DateTimeField("waktu", auto_now_add=True, db_index=True)
    pengguna = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="pengguna",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    aksi = models.CharField("aksi", max_length=60, db_index=True)
    objek_tipe = models.CharField("tipe objek", max_length=60, blank=True)
    objek_id = models.CharField("ID objek", max_length=40, blank=True)
    keterangan = models.TextField("keterangan", blank=True)
    alamat_ip = models.GenericIPAddressField("alamat IP", null=True, blank=True)

    class Meta:
        verbose_name = "log audit"
        verbose_name_plural = "log audit"
        ordering = ["-waktu"]

    def __str__(self):
        return f"{self.waktu:%Y-%m-%d %H:%M} {self.aksi}"
