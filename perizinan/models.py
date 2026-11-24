"""Modul 2 PRD PANDU LOTIM: pengajuan izin nonberusaha (KKPR) online."""

import secrets
import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from akun.models import Instansi, Pemohon, TipePemohon
from core.models import CatatanTetap
from core.validators import validasi_berkas


class Kanal(models.TextChoices):
    MANDIRI = "mandiri", "Mandiri"
    BERBANTUAN = "berbantuan", "Berbantuan"


class StatusPermohonan(models.TextChoices):
    """PRD 6.1."""

    DRAF = "draf", "Draf"
    DIAJUKAN = "diajukan", "Diajukan"
    PERLU_PERBAIKAN = "perlu_perbaikan", "Perlu perbaikan"
    PENILAIAN_TEKNIS = "penilaian_teknis", "Penilaian teknis"
    DISETUJUI = "disetujui", "Disetujui"
    DITOLAK = "ditolak", "Ditolak"
    TERBIT = "terbit", "Terbit"


class Aksi(models.TextChoices):
    KIRIM = "kirim", "Kirim"
    MINTA_PERBAIKAN = "minta_perbaikan", "Minta perbaikan"
    TERUSKAN = "teruskan", "Teruskan ke instansi teknis"
    SETUJUI = "setujui", "Setujui"
    TOLAK = "tolak", "Tolak"
    MEMENUHI = "memenuhi", "Rekomendasi: memenuhi"
    TIDAK_MEMENUHI = "tidak_memenuhi", "Rekomendasi: tidak memenuhi"
    TERBIT = "terbit", "Terbitkan izin"


# Riwayat tidak pernah diubah (jejak audit). Nilai dari alur lama (sebelum PRD PANDU LOTIM)
# tetap disimpan apa adanya; label ini hanya agar riwayat lama tetap terbaca.
_STATUS_LAMA = [
    ("verifikasi_kasi", "Verifikasi Kasi"),
    ("verifikasi_kabid", "Verifikasi Kabid"),
    ("verifikasi_kadis", "Verifikasi Kadis"),
    ("dikembalikan", "Dikembalikan"),
    ("komitmen_ditolak", "Komitmen Ditolak"),
]
_AKSI_LAMA = [
    ("mulai", "Mulai verifikasi"),
    ("kembalikan", "Kembalikan"),
    ("komitmen_ditolak", "Komitmen Ditolak"),
]
STATUS_RIWAYAT = StatusPermohonan.choices + _STATUS_LAMA
AKSI_RIWAYAT = Aksi.choices + _AKSI_LAMA


class StatusCek(models.TextChoices):
    BELUM = "belum", "Belum dicek"
    SESUAI = "sesuai", "Sesuai"
    TIDAK_SESUAI = "tidak_sesuai", "Tidak Sesuai"


class BerlakuUntuk(models.TextChoices):
    SEMUA = "semua", "Semua pemohon"
    PERORANGAN = TipePemohon.PERORANGAN.value, "Perorangan"
    BADAN_HUKUM = TipePemohon.BADAN_HUKUM.value, "Badan Hukum"


class JenisIzin(models.Model):
    """Katalog jenis izin nonberusaha (PRD IZ-02). Dikelola Admin Sistem."""

    nama = models.CharField("nama", max_length=120, unique=True)
    kode = models.CharField(
        "kode nomor izin",
        max_length=20,
        blank=True,
        help_text="Dipakai di nomor izin otomatis, mis. KKPR-NB.",
    )
    keterangan = models.TextField(
        "keterangan", blank=True, help_text="Penjelasan singkat untuk pemohon di katalog izin."
    )
    perlu_kajian_teknis = models.BooleanField(
        "perlu penilaian instansi teknis",
        default=False,
        help_text="Bila dicentang, petugas wajib meneruskan permohonan ke instansi teknis.",
    )
    instansi = models.ForeignKey(
        Instansi,
        verbose_name="instansi teknis bawaan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="jenis_izin",
    )
    sla_hari = models.PositiveSmallIntegerField(
        "batas waktu layanan (hari)",
        default=14,
        help_text="Dihitung sejak permohonan terakhir diajukan. Dipakai untuk pengingat SLA.",
    )
    aktif = models.BooleanField("aktif", default=True)
    urutan = models.PositiveSmallIntegerField("urutan", default=0)

    class Meta:
        verbose_name = "jenis izin"
        verbose_name_plural = "jenis izin"
        ordering = ["urutan", "nama"]

    def __str__(self):
        return self.nama


class SyaratIzin(models.Model):
    jenis_izin = models.ForeignKey(
        JenisIzin, verbose_name="jenis izin", on_delete=models.PROTECT, related_name="syarat"
    )
    nama = models.CharField("nama syarat", max_length=150)
    keterangan = models.CharField("keterangan", max_length=255, blank=True)
    wajib = models.BooleanField("wajib", default=True)
    berlaku_untuk = models.CharField(
        "berlaku untuk", max_length=12, choices=BerlakuUntuk, default=BerlakuUntuk.SEMUA
    )
    aktif = models.BooleanField("aktif", default=True)
    urutan = models.PositiveSmallIntegerField("urutan", default=0)

    class Meta:
        verbose_name = "syarat izin"
        verbose_name_plural = "syarat izin"
        ordering = ["urutan", "id"]
        constraints = [
            models.UniqueConstraint(fields=["jenis_izin", "nama"], name="syarat_unik_per_izin")
        ]

    def __str__(self):
        return self.nama


# Tanpa huruf/angka yang mirip (0/O, 1/I/L) agar mudah dibacakan di loket.
ABJAD_NOMOR = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def nomor_registrasi_baru(tanggal):
    """Akhiran acak: cek status publik tidak bisa ditelusuri dengan menebak nomor urut."""
    acak = "".join(secrets.choice(ABJAD_NOMOR) for _ in range(8))
    return f"SIK-{tanggal:%Y%m%d}-{acak}"


def lokasi_komitmen(permohonan, nama_berkas):
    """Tidak dipakai lagi; tetap ada karena dirujuk migrasi lama."""
    return f"komitmen/{uuid.uuid4().hex}{Path(nama_berkas).suffix.lower()}"


class Permohonan(models.Model):
    nomor_registrasi = models.CharField("nomor registrasi", max_length=24, unique=True)
    pemohon = models.ForeignKey(
        Pemohon, verbose_name="pemohon", on_delete=models.PROTECT, related_name="permohonan"
    )
    jenis_izin = models.ForeignKey(
        JenisIzin, verbose_name="jenis izin", on_delete=models.PROTECT, related_name="permohonan"
    )
    kanal = models.CharField("kanal", max_length=12, choices=Kanal, default=Kanal.MANDIRI)
    status = models.CharField(
        "status",
        max_length=20,
        choices=StatusPermohonan,
        default=StatusPermohonan.DRAF,
        db_index=True,
    )

    # Data formulir: lokasi objek perizinan (dipakai juga di Database NonOSS).
    lokasi_alamat = models.TextField("alamat lokasi objek", blank=True)
    kecamatan = models.ForeignKey(
        "basisdata.Kecamatan",
        verbose_name="kecamatan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="permohonan",
    )
    kelurahan_nama = models.CharField("kelurahan/desa", max_length=80, blank=True)
    luas_tanah = models.DecimalField(
        "luas tanah (m²)", max_digits=14, decimal_places=2, null=True, blank=True
    )
    rencana_kegiatan = models.TextField("rencana kegiatan / pemanfaatan ruang", blank=True)
    koordinat = models.CharField(
        "titik koordinat", max_length=60, blank=True, help_text="Contoh: -8.6512, 116.5321"
    )

    instansi_penilai = models.ForeignKey(
        Instansi,
        verbose_name="instansi teknis penilai",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="permohonan",
    )
    dibuat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="dibuat oleh",
        on_delete=models.PROTECT,
        related_name="+",
    )
    dibuat_pada = models.DateTimeField("dibuat pada", auto_now_add=True, db_index=True)
    diajukan_pada = models.DateTimeField("terakhir diajukan", null=True, blank=True)
    diperbarui_pada = models.DateTimeField("diperbarui pada", auto_now=True)
    catatan_terakhir = models.TextField("catatan terakhir", blank=True)

    class Meta:
        verbose_name = "permohonan"
        verbose_name_plural = "permohonan"
        ordering = ["-dibuat_pada"]

    def __str__(self):
        return self.nomor_registrasi

    @property
    def bisa_diperbaiki(self):
        return self.status in (StatusPermohonan.DRAF, StatusPermohonan.PERLU_PERBAIKAN)

    @property
    def batas_layanan(self):
        """IZ-10: batas waktu layanan, dihitung sejak pengajuan terakhir."""
        if self.diajukan_pada is None:
            return None
        from datetime import timedelta

        return self.diajukan_pada + timedelta(days=self.jenis_izin.sla_hari)

    def syarat_berlaku(self):
        return self.jenis_izin.syarat.filter(
            aktif=True, berlaku_untuk__in=[BerlakuUntuk.SEMUA, self.pemohon.tipe]
        )


def lokasi_dokumen(dokumen, nama_berkas):
    return f"syarat/{uuid.uuid4().hex}{Path(nama_berkas).suffix.lower()}"


class Dokumen(models.Model):
    permohonan = models.ForeignKey(
        Permohonan, verbose_name="permohonan", on_delete=models.PROTECT, related_name="dokumen"
    )
    syarat = models.ForeignKey(
        SyaratIzin, verbose_name="syarat", on_delete=models.PROTECT, related_name="+"
    )
    berkas = models.FileField("berkas", upload_to=lokasi_dokumen, validators=[validasi_berkas])
    status_cek = models.CharField(
        "status cek", max_length=14, choices=StatusCek, default=StatusCek.BELUM
    )
    catatan_cek = models.CharField("catatan cek", max_length=255, blank=True)
    diunggah_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="diunggah oleh",
        on_delete=models.PROTECT,
        related_name="+",
    )
    diunggah_pada = models.DateTimeField("diunggah pada", auto_now=True)

    class Meta:
        verbose_name = "dokumen"
        verbose_name_plural = "dokumen"
        constraints = [
            models.UniqueConstraint(fields=["permohonan", "syarat"], name="dokumen_unik_per_syarat")
        ]

    def __str__(self):
        return f"{self.permohonan} - {self.syarat}"


class RiwayatVerifikasi(CatatanTetap):
    permohonan = models.ForeignKey(
        Permohonan, verbose_name="permohonan", on_delete=models.PROTECT, related_name="riwayat"
    )
    dari_status = models.CharField("tahap", max_length=20, choices=STATUS_RIWAYAT)
    ke_status = models.CharField("status baru", max_length=20, choices=STATUS_RIWAYAT)
    aksi = models.CharField("aksi", max_length=20, choices=AKSI_RIWAYAT)
    verifikator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="pengguna",
        on_delete=models.PROTECT,
        related_name="+",
    )
    catatan = models.TextField("catatan", blank=True)
    waktu = models.DateTimeField("waktu", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "riwayat verifikasi"
        verbose_name_plural = "riwayat verifikasi"
        ordering = ["waktu", "id"]

    def __str__(self):
        return f"{self.permohonan_id}: {self.dari_status} -> {self.ke_status}"


class HasilPenilaian(models.TextChoices):
    MEMENUHI = "memenuhi", "Memenuhi"
    TIDAK_MEMENUHI = "tidak_memenuhi", "Tidak memenuhi"


def lokasi_rekomendasi(penilaian, nama_berkas):
    return f"rekomendasi/{uuid.uuid4().hex}{Path(nama_berkas).suffix.lower()}"


class PenilaianTeknis(CatatanTetap):
    """IZ-05: hasil penilaian dan rekomendasi instansi teknis. Tidak bisa diubah."""

    permohonan = models.ForeignKey(
        Permohonan, verbose_name="permohonan", on_delete=models.PROTECT, related_name="penilaian"
    )
    instansi = models.ForeignKey(
        Instansi, verbose_name="instansi", on_delete=models.PROTECT, related_name="penilaian"
    )
    penilai = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="penilai", on_delete=models.PROTECT, related_name="+"
    )
    hasil = models.CharField("hasil", max_length=16, choices=HasilPenilaian)
    rekomendasi = models.TextField("rekomendasi / alasan")
    berkas = models.FileField(
        "berkas rekomendasi",
        upload_to=lokasi_rekomendasi,
        blank=True,
        validators=[validasi_berkas],
    )
    waktu = models.DateTimeField("waktu", auto_now_add=True)

    class Meta:
        verbose_name = "penilaian teknis"
        verbose_name_plural = "penilaian teknis"
        ordering = ["waktu", "id"]

    def __str__(self):
        return f"{self.permohonan} — {self.instansi}: {self.get_hasil_display()}"


def lokasi_izin(izin, nama_berkas):
    return f"izin/{uuid.uuid4().hex}{Path(nama_berkas).suffix.lower()}"


def kode_verifikasi_baru():
    return secrets.token_urlsafe(18)


class IzinTerbit(models.Model):
    permohonan = models.OneToOneField(
        Permohonan, verbose_name="permohonan", on_delete=models.PROTECT, related_name="izin_terbit"
    )
    nomor_izin = models.CharField("nomor izin", max_length=80, unique=True)
    tanggal_terbit = models.DateField("tanggal terbit")
    # IZ-09: dokumen dibuat sistem (dengan QR); petugas boleh mengganti dengan pindaian bertanda tangan.
    berkas = models.FileField("dokumen izin", upload_to=lokasi_izin, validators=[validasi_berkas])
    berkas_ttd = models.FileField(
        "dokumen bertanda tangan",
        upload_to=lokasi_izin,
        blank=True,
        validators=[validasi_berkas],
    )
    kode_verifikasi = models.CharField(
        "kode verifikasi", max_length=40, unique=True, default=kode_verifikasi_baru, editable=False
    )

    class Meta:
        verbose_name = "izin terbit"
        verbose_name_plural = "izin terbit"

    def __str__(self):
        return self.nomor_izin

    @property
    def berkas_unduhan(self):
        return self.berkas_ttd or self.berkas


class PenomoranIzin(models.Model):
    """Nomor urut izin per jenis per tahun (IZ-06). Dikunci saat dipakai agar tidak ganda."""

    jenis_izin = models.ForeignKey(JenisIzin, on_delete=models.PROTECT, related_name="+")
    tahun = models.PositiveSmallIntegerField()
    terakhir = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["jenis_izin", "tahun"], name="nomor_unik_per_tahun")
        ]


class KodeEmail(models.TextChoices):
    DITERIMA = "diterima", "Permohonan diterima"
    PERLU_PERBAIKAN = "perlu_perbaikan", "Perlu perbaikan"
    PENILAIAN_TEKNIS = "penilaian_teknis", "Diteruskan ke instansi teknis"
    DISETUJUI = "disetujui", "Permohonan disetujui"
    DITOLAK = "ditolak", "Permohonan ditolak"
    TERBIT = "terbit", "Izin terbit"


class TemplateEmail(models.Model):
    kode = models.CharField("peristiwa", max_length=20, choices=KodeEmail, unique=True)
    subjek = models.CharField("subjek", max_length=200)
    isi = models.TextField(
        "isi",
        help_text="Penanda yang tersedia: {nama}, {nomor}, {jenis_izin}, {catatan}, {tautan}",
    )

    class Meta:
        verbose_name = "template email"
        verbose_name_plural = "template email"

    def __str__(self):
        return self.get_kode_display()
