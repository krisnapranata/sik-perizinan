"""Modul 1 PRD PANDU LOTIM: Database Perizinan Berusaha (OSS-RBA) dan Nonberusaha (NonOSS).

Usaha dan proyek dipisah karena satu NIB bisa punya banyak proyek (PRD bagian 9).
"""

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from core.validators import validasi_berkas


class Kecamatan(models.Model):
    nama = models.CharField("nama", max_length=60, unique=True)

    class Meta:
        verbose_name = "kecamatan"
        verbose_name_plural = "kecamatan"
        ordering = ["nama"]

    def __str__(self):
        return self.nama


class Kelurahan(models.Model):
    kecamatan = models.ForeignKey(
        Kecamatan, verbose_name="kecamatan", on_delete=models.PROTECT, related_name="kelurahan"
    )
    nama = models.CharField("nama kelurahan/desa", max_length=80)

    class Meta:
        verbose_name = "kelurahan/desa"
        verbose_name_plural = "kelurahan/desa"
        ordering = ["kecamatan__nama", "nama"]
        constraints = [
            models.UniqueConstraint(fields=["kecamatan", "nama"], name="kelurahan_unik_per_kecamatan")
        ]

    def __str__(self):
        return self.nama


class Sektor(models.TextChoices):
    """Sektor usaha versi KAK. Bawaannya dipetakan dari kode KBLI; admin bisa mengubahnya."""

    PERTANIAN = "pertanian", "Pertanian"
    PERIKANAN = "perikanan", "Perikanan"
    PERDAGANGAN = "perdagangan", "Perdagangan"
    PARIWISATA = "pariwisata", "Pariwisata"
    LAINNYA = "lainnya", "Lainnya"


class KBLI(models.Model):
    kode = models.CharField("kode", max_length=5, primary_key=True)
    judul = models.CharField("judul", max_length=255)
    kl_pembina = models.CharField("KL/sektor pembina", max_length=150, blank=True)
    sektor = models.CharField("sektor KAK", max_length=12, choices=Sektor, default=Sektor.LAINNYA)

    class Meta:
        verbose_name = "KBLI"
        verbose_name_plural = "KBLI"
        ordering = ["kode"]

    def __str__(self):
        return f"{self.kode} — {self.judul}"


class PelakuUsaha(models.Model):
    nib = models.CharField("NIB", max_length=13, primary_key=True)
    nama = models.CharField("nama perusahaan", max_length=255, db_index=True)
    jenis_perusahaan = models.CharField("jenis perusahaan", max_length=80, blank=True)
    status_pm = models.CharField("status penanaman modal", max_length=10, blank=True, db_index=True)

    class Meta:
        verbose_name = "pelaku usaha"
        verbose_name_plural = "pelaku usaha"
        ordering = ["nama"]

    def __str__(self):
        return f"{self.nama} ({self.nib})"


class StatusIzin(models.TextChoices):
    """Tidak ada di ekspor OSS (PRD 5.1): diisi petugas. Kosong = belum diketahui."""

    BELUM = "", "Belum diisi"
    AKTIF = "aktif", "Aktif"
    DICABUT = "dicabut", "Dicabut"


class ProyekOSS(models.Model):
    id_proyek = models.CharField("Id proyek", max_length=40, unique=True)
    pelaku = models.ForeignKey(
        PelakuUsaha, verbose_name="pelaku usaha", on_delete=models.PROTECT, related_name="proyek"
    )
    jenis_proyek = models.CharField("jenis proyek", max_length=30, blank=True)
    nama_proyek = models.CharField("nama proyek", max_length=255, blank=True)
    kbli = models.ForeignKey(
        KBLI, verbose_name="KBLI", null=True, blank=True, on_delete=models.PROTECT, related_name="proyek"
    )
    skala = models.CharField("skala usaha", max_length=30, blank=True, db_index=True)
    risiko = models.CharField("risiko proyek", max_length=30, blank=True, db_index=True)
    alamat = models.TextField("alamat usaha", blank=True)
    kab_kota = models.CharField("kab/kota", max_length=60, blank=True)
    kecamatan = models.ForeignKey(
        Kecamatan, verbose_name="kecamatan", on_delete=models.PROTECT, related_name="proyek"
    )
    kelurahan = models.ForeignKey(
        Kelurahan,
        verbose_name="kelurahan/desa",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="proyek",
    )
    tanggal_terbit = models.DateField("tanggal terbit OSS", null=True, blank=True)
    tanggal_pengajuan = models.DateField("tanggal pengajuan proyek", null=True, blank=True)
    tahun = models.PositiveSmallIntegerField("tahun", null=True, blank=True, db_index=True)
    luas_tanah = models.DecimalField("luas tanah", max_digits=16, decimal_places=2, null=True, blank=True)
    satuan_tanah = models.CharField("satuan tanah", max_length=10, blank=True)
    investasi = models.PositiveBigIntegerField("jumlah investasi (Rp)", default=0)
    tki = models.PositiveIntegerField("tenaga kerja Indonesia", default=0)
    status_izin = models.CharField(
        "status izin", max_length=10, choices=StatusIzin, default=StatusIzin.BELUM, blank=True
    )
    diimpor_pada = models.DateTimeField("terakhir diimpor", auto_now=True)

    class Meta:
        verbose_name = "proyek OSS"
        verbose_name_plural = "proyek OSS"
        ordering = ["-tanggal_terbit", "id_proyek"]

    def __str__(self):
        return self.id_proyek

    def save(self, *args, **kwargs):
        self.tahun = tahun_proyek(self)
        super().save(*args, **kwargs)


def tahun_proyek(proyek):
    """Satu-satunya tempat menentukan tahun rekap.

    PRD 5.1: tahun diambil dari tanggal terbit. Bila kolom itu kosong, pakai tanggal pengajuan.
    """
    tanggal = proyek.tanggal_terbit or proyek.tanggal_pengajuan
    return tanggal.year if tanggal else None


class ImporOSS(models.Model):
    """Catatan setiap unggahan ekspor OSS-RBA beserta hasilnya."""

    waktu = models.DateTimeField("waktu", auto_now_add=True)
    pengguna = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="pengguna", on_delete=models.PROTECT, related_name="+"
    )
    nama_berkas = models.CharField("nama berkas", max_length=255)
    jumlah_baris = models.PositiveIntegerField("jumlah baris", default=0)
    baru = models.PositiveIntegerField("proyek baru", default=0)
    diperbarui = models.PositiveIntegerField("proyek diperbarui", default=0)
    tetap = models.PositiveIntegerField("tidak berubah", default=0)
    gagal = models.PositiveIntegerField("baris gagal", default=0)
    laporan = models.JSONField("baris bermasalah", default=list, blank=True)

    class Meta:
        verbose_name = "impor OSS"
        verbose_name_plural = "impor OSS"
        ordering = ["-waktu"]

    def __str__(self):
        return f"{self.nama_berkas} ({self.waktu:%Y-%m-%d %H:%M})"


class JenisIzinNonOSS(models.Model):
    nama = models.CharField("nama", max_length=120, unique=True)
    aktif = models.BooleanField("aktif", default=True)

    class Meta:
        verbose_name = "jenis izin NonOSS"
        verbose_name_plural = "jenis izin NonOSS"
        ordering = ["nama"]

    def __str__(self):
        return self.nama


class StatusNonOSS(models.TextChoices):
    DIPROSES = "diproses", "Diproses"
    TERBIT = "terbit", "Terbit"
    DITOLAK = "ditolak", "Ditolak"
    DICABUT = "dicabut", "Dicabut"


def lokasi_dokumen_nonoss(izin, nama_berkas):
    return f"nonoss/{uuid.uuid4().hex}{Path(nama_berkas).suffix.lower()}"


class IzinNonOSS(models.Model):
    jenis = models.ForeignKey(
        JenisIzinNonOSS, verbose_name="jenis perizinan", on_delete=models.PROTECT, related_name="izin"
    )
    nomor_izin = models.CharField("nomor izin", max_length=80, null=True, blank=True, unique=True)
    nama_pemohon = models.CharField("nama pemohon", max_length=200, db_index=True)
    nik = models.CharField("NIK pemohon", max_length=16, blank=True)
    tanggal_permohonan = models.DateField("tanggal permohonan")
    tanggal_terbit = models.DateField("tanggal penerbitan", null=True, blank=True)
    tahun = models.PositiveSmallIntegerField("tahun", db_index=True)
    alamat_objek = models.TextField("lokasi objek perizinan", blank=True)
    kecamatan = models.ForeignKey(
        Kecamatan, verbose_name="kecamatan", on_delete=models.PROTECT, related_name="izin_nonoss"
    )
    kelurahan = models.ForeignKey(
        Kelurahan,
        verbose_name="kelurahan/desa",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="izin_nonoss",
    )
    status = models.CharField(
        "status", max_length=10, choices=StatusNonOSS, default=StatusNonOSS.DIPROSES, db_index=True
    )
    instansi_teknis = models.CharField("instansi teknis terkait", max_length=120, blank=True)
    dokumen = models.FileField(
        "dokumen perizinan",
        upload_to=lokasi_dokumen_nonoss,
        blank=True,
        validators=[validasi_berkas],
    )
    # Diisi otomatis saat permohonan KKPR online (Modul 2, Rilis 2) terbit.
    permohonan = models.OneToOneField(
        "perizinan.Permohonan",
        verbose_name="permohonan online",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="izin_nonoss",
    )
    dibuat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="dibuat oleh", on_delete=models.PROTECT, related_name="+"
    )
    dibuat_pada = models.DateTimeField("dibuat pada", auto_now_add=True)
    diperbarui_pada = models.DateTimeField("diperbarui pada", auto_now=True)

    class Meta:
        verbose_name = "izin NonOSS"
        verbose_name_plural = "izin NonOSS"
        ordering = ["-tanggal_permohonan", "-id"]

    def __str__(self):
        return self.nomor_izin or f"{self.jenis} — {self.nama_pemohon}"

    def save(self, *args, **kwargs):
        self.nomor_izin = self.nomor_izin or None  # kosong tidak boleh bentrok dengan unique
        self.tahun = (self.tanggal_terbit or self.tanggal_permohonan).year
        super().save(*args, **kwargs)
