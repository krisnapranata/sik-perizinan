import uuid
from pathlib import Path

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models

from core.validators import validasi_berkas


class Peran(models.TextChoices):
    """Peran sesuai PRD PANDU LOTIM bagian 3."""

    PEMOHON = "pemohon", "Pemohon"
    PETUGAS = "petugas", "Petugas DPMPTSP"
    INSTANSI = "instansi", "Instansi Teknis"
    PIMPINAN = "pimpinan", "Pimpinan"
    ADMIN = "admin", "Admin Sistem"


class Instansi(models.Model):
    """Instansi teknis (mis. Dinas PUPR, Bappeda) yang memberi penilaian dan rekomendasi."""

    nama = models.CharField("nama", max_length=150, unique=True)
    singkatan = models.CharField("singkatan", max_length=30, blank=True)
    aktif = models.BooleanField("aktif", default=True)

    class Meta:
        verbose_name = "instansi teknis"
        verbose_name_plural = "instansi teknis"
        ordering = ["nama"]

    def __str__(self):
        return self.singkatan or self.nama


class PenggunaManager(BaseUserManager):
    use_in_migrations = True

    def _buat(self, email, password, **kolom):
        if not email:
            raise ValueError("Email wajib diisi.")
        pengguna = self.model(email=self.normalize_email(email).lower(), **kolom)
        pengguna.set_password(password)
        pengguna.save(using=self._db)
        return pengguna

    def create_user(self, email, password=None, **kolom):
        kolom.setdefault("is_superuser", False)
        return self._buat(email, password, **kolom)

    def create_superuser(self, email, password=None, **kolom):
        kolom.update(is_superuser=True, peran=Peran.ADMIN)
        return self._buat(email, password, **kolom)


class User(AbstractUser):
    username = None
    first_name = None
    last_name = None
    email = models.EmailField("email", unique=True)
    nama = models.CharField("nama", max_length=150)
    nip = models.CharField("NIP", max_length=30, blank=True)
    unit_kerja = models.CharField("unit kerja", max_length=120, blank=True)
    peran = models.CharField("peran", max_length=12, choices=Peran, default=Peran.PEMOHON)
    instansi = models.ForeignKey(
        Instansi,
        verbose_name="instansi",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pengguna",
        help_text="Wajib untuk peran Instansi Teknis.",
    )
    wajib_ganti_password = models.BooleanField(
        "wajib ganti password",
        default=False,
        help_text="Pengguna harus mengganti password sebelum bisa memakai aplikasi.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nama"]
    objects = PenggunaManager()

    class Meta:
        verbose_name = "pengguna"
        verbose_name_plural = "pengguna"

    def __str__(self):
        return self.nama or self.email

    def save(self, *args, **kwargs):
        # Panel admin hanya untuk Admin Sistem; is_staff mengikuti peran.
        self.is_staff = self.is_superuser or self.peran == Peran.ADMIN
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.nama

    def get_short_name(self):
        return self.nama

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        if self.peran == Peran.INSTANSI and not self.instansi_id:
            raise ValidationError({"instansi": "Pilih instansi untuk akun Instansi Teknis."})

    @property
    def petugas(self):
        """Petugas DPMPTSP: front office dan verifikator (PRD bagian 3)."""
        return self.peran == Peran.PETUGAS

    @property
    def pemeriksa(self):
        """Pengguna yang punya antrean permohonan: petugas dan instansi teknis."""
        return self.peran in (Peran.PETUGAS, Peran.INSTANSI)


class TipePemohon(models.TextChoices):
    PERORANGAN = "perorangan", "Perorangan"
    BADAN_HUKUM = "badan_hukum", "Badan Hukum"


def lokasi_bukti_nib(pemohon, nama_berkas):
    return f"nib/{uuid.uuid4().hex}{Path(nama_berkas).suffix.lower()}"


class Pemohon(models.Model):
    user = models.OneToOneField(
        User, verbose_name="akun", on_delete=models.PROTECT, related_name="pemohon"
    )
    tipe = models.CharField("tipe pemohon", max_length=12, choices=TipePemohon)
    nama = models.CharField("nama pemohon / badan hukum", max_length=200)
    nik = models.CharField(
        "NIK",
        max_length=16,
        blank=True,
        validators=[RegexValidator(r"^\d{16}$", "NIK harus 16 digit angka.")],
    )
    npwp = models.CharField("NPWP", max_length=20, blank=True)
    hp = models.CharField(
        "nomor HP",
        max_length=20,
        validators=[RegexValidator(r"^\+?\d{8,15}$", "Nomor HP tidak valid.")],
    )
    alamat = models.TextField("alamat")
    nib = models.CharField(
        "NIB",
        max_length=13,
        blank=True,
        validators=[RegexValidator(r"^\d{13}$", "NIB harus 13 digit angka.")],
    )
    bukti_nib = models.FileField(
        "bukti NIB",
        upload_to=lokasi_bukti_nib,
        blank=True,
        validators=[validasi_berkas],
    )
    didaftarkan_oleh = models.ForeignKey(
        User,
        verbose_name="didaftarkan oleh petugas",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    dibuat_pada = models.DateTimeField("dibuat pada", auto_now_add=True)

    class Meta:
        verbose_name = "pemohon"
        verbose_name_plural = "pemohon"
        ordering = ["nama"]

    def __str__(self):
        return self.nama

    @property
    def nib_lengkap(self):
        return bool(self.nib and self.bukti_nib)


class PercobaanMasuk(models.Model):
    """Login gagal, untuk membatasi tebakan password (PRD bagian 10: Keamanan).

    Baris untuk email dihapus saat login berhasil; baris lama dibersihkan otomatis.
    """

    email = models.CharField("email", max_length=254, db_index=True)
    alamat_ip = models.GenericIPAddressField("alamat IP", null=True, blank=True, db_index=True)
    waktu = models.DateTimeField("waktu", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "percobaan masuk gagal"
        verbose_name_plural = "percobaan masuk gagal"


class KodeOTP(models.Model):
    """Kode verifikasi 6 digit saat registrasi (PRD IZ-01). Hanya hash yang disimpan."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="kode_otp")
    kode_hash = models.CharField(max_length=64)
    dibuat = models.DateTimeField(auto_now_add=True)
    kedaluwarsa = models.DateTimeField()
    percobaan = models.PositiveSmallIntegerField(default=0)
    dipakai = models.BooleanField(default=False)

    class Meta:
        verbose_name = "kode OTP"
        verbose_name_plural = "kode OTP"
        ordering = ["-dibuat"]
