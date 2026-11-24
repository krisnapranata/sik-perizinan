"""Modul 3 PRD PANDU LOTIM: potensi, peluang, dan proyek investasi siap tawar."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from basisdata.models import Kecamatan, Sektor


class Tingkat(models.TextChoices):
    """PRD 7.1: tiga tingkat kesiapan, dibedakan dengan label yang jelas."""

    POTENSI = "potensi", "Potensi"
    PELUANG = "peluang", "Peluang"
    SIAP_TAWAR = "siap_tawar", "Proyek siap tawar"


KONTAK_BAWAAN = "DPMPTSP Kabupaten Lombok Timur"


class PeluangInvestasi(models.Model):
    nama = models.CharField("nama", max_length=200)
    tingkat = models.CharField("tingkat kesiapan", max_length=12, choices=Tingkat.choices)
    sektor = models.CharField("sektor", max_length=20, choices=Sektor.choices)
    kecamatan = models.ForeignKey(
        Kecamatan, verbose_name="kecamatan", on_delete=models.PROTECT, related_name="peluang_investasi"
    )
    lokasi = models.CharField(
        "lokasi", max_length=200, blank=True, help_text="Desa/dusun atau nama kawasan"
    )
    deskripsi = models.TextField("deskripsi")
    luas_lahan_ha = models.DecimalField(
        "luas lahan (ha)", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal(0))],
    )
    estimasi_investasi = models.PositiveBigIntegerField("estimasi investasi (Rp)", null=True, blank=True)
    potensi_pasar = models.TextField("potensi pasar", blank=True)
    kontak = models.CharField(
        "kontak", max_length=200, blank=True,
        help_text=f"Kosongkan untuk memakai kontak {KONTAK_BAWAAN}",
    )
    # Batas kira-kira wilayah Indonesia, untuk menangkap lintang/bujur yang tertukar.
    lintang = models.DecimalField(
        "lintang", max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(Decimal(-11)), MaxValueValidator(Decimal(6))],
    )
    bujur = models.DecimalField(
        "bujur", max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(Decimal(95)), MaxValueValidator(Decimal(141))],
    )
    tampil = models.BooleanField("tampil di portal", default=True)
    diperbarui = models.DateTimeField("diperbarui", auto_now=True)

    class Meta:
        verbose_name = "potensi/peluang investasi"
        verbose_name_plural = "potensi dan peluang investasi"
        ordering = ["nama"]

    def __str__(self):
        return self.nama

    def clean(self):
        galat = {}
        if (self.lintang is None) != (self.bujur is None):
            galat["lintang"] = "Isi lintang dan bujur sekaligus, atau kosongkan keduanya."
        # PRD 7.1: data minimum bertambah sesuai tingkat kesiapan.
        if self.tingkat in (Tingkat.PELUANG, Tingkat.SIAP_TAWAR):
            if self.estimasi_investasi is None:
                galat["estimasi_investasi"] = "Wajib untuk peluang dan proyek siap tawar."
            if not self.potensi_pasar:
                galat["potensi_pasar"] = "Wajib untuk peluang dan proyek siap tawar."
        if self.tingkat == Tingkat.SIAP_TAWAR:
            if self.luas_lahan_ha is None:
                galat["luas_lahan_ha"] = "Proyek siap tawar wajib mencantumkan luas lahan terverifikasi."
            if not self.kontak:
                galat["kontak"] = "Proyek siap tawar wajib mencantumkan kontak."
        if galat:
            raise ValidationError(galat)

    @property
    def ada_koordinat(self):
        return self.lintang is not None and self.bujur is not None

    @property
    def koordinat(self):
        return f"{self.lintang},{self.bujur}" if self.ada_koordinat else ""

    @property
    def kontak_tampil(self):
        return self.kontak or KONTAK_BAWAAN
