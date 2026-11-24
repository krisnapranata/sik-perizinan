"""Pengaturan SIK Perizinan DPMPTSP Lombok Timur. Semua nilai rahasia dari environment."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _muat_env(berkas):
    """Membaca .env untuk manage.py lokal. Variabel yang sudah ada (mis. dari Docker) menang."""
    if not berkas.is_file():
        return
    for baris in berkas.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#") or "=" not in baris:
            continue
        kunci, nilai = baris.split("=", 1)
        os.environ.setdefault(kunci.strip(), nilai.strip())


_muat_env(BASE_DIR / ".env")


def _daftar(nama, bawaan=""):
    return [x.strip() for x in os.environ.get(nama, bawaan).split(",") if x.strip()]


# Bawaan aman: DEBUG mati kecuali diminta (DJANGO_DEBUG=1 untuk pengembangan lokal).
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if DEBUG and not SECRET_KEY:
    SECRET_KEY = "dev-only-insecure-key"
if not SECRET_KEY or SECRET_KEY.startswith("ganti-"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY wajib diisi nilai acak (atau DJANGO_DEBUG=1 untuk pengembangan)."
    )

ALLOWED_HOSTS = _daftar("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = _daftar("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
    "akun",
    "perizinan",
    "laporan",
    "basisdata",
    "investasi",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.AlamatIPMiddleware",
    "core.middleware.WajibGantiPasswordMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "perizinan.context_processors.navigasi",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",  # dipakai juga untuk MariaDB
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "NAME": os.environ.get("DB_NAME", "sik"),
        "USER": os.environ.get("DB_USER", "sik"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "sik"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "TEST": {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_unicode_ci"},
    }
}

AUTH_USER_MODEL = "akun.User"
LOGIN_URL = "akun:masuk"
LOGIN_REDIRECT_URL = "beranda"
LOGOUT_REDIRECT_URL = "beranda"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Makassar"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Berkas pemohon adalah data pribadi: tidak ada MEDIA_URL publik. Unduhan selalu lewat
# view yang mengecek izin, lalu Nginx mengirim isinya via X-Accel-Redirect (lihat core/berkas.py).
MEDIA_ROOT = BASE_DIR / "media"
X_ACCEL_PREFIX = "/_berkas/"

# Django di belakang Nginx HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# F-03: batas sebenarnya ditegakkan core.validators.validasi_berkas.
# Dua setelan Django di bawah hanya mengatur memori, bukan batas ukuran berkas.
UKURAN_MAKS_BERKAS = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Email (F-01, F-15). Tanpa EMAIL_HOST, email hanya tampil di log.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.environ.get("EMAIL_FROM", "SIK Perizinan <noreply@localhost>")
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)

# Alamat dasar untuk tautan di email.
SITUS_URL = os.environ.get("SITUS_URL", "http://localhost:8000").rstrip("/")

# Impor pengguna (panel admin): password untuk baris yang kolom password-nya kosong.
IMPOR_PASSWORD_DEFAULT = os.environ.get("IMPOR_PASSWORD_DEFAULT", "Sik-Lotim-2026!")

# Bawaan Django hanya mencetak log saat DEBUG=True; tanpa ini error 500 di produksi tidak terlihat.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"baku": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"konsol": {"class": "logging.StreamHandler", "formatter": "baku"}},
    "root": {"handlers": ["konsol"], "level": "INFO"},
}

# Kop surat untuk ekspor Excel/PDF (PRD AN-06).
KOP_INSTANSI = os.environ.get("KOP_INSTANSI", "PEMERINTAH KABUPATEN LOMBOK TIMUR")
KOP_DINAS = os.environ.get(
    "KOP_DINAS", "DINAS PENANAMAN MODAL DAN PELAYANAN TERPADU SATU PINTU"
)
KOP_ALAMAT = os.environ.get("KOP_ALAMAT", "Selong, Lombok Timur, Nusa Tenggara Barat")

# Nomor izin otomatis (PRD IZ-06). Penanda: {urut}, {kode}, {tahun}, {bulan}.
FORMAT_NOMOR_IZIN = os.environ.get("FORMAT_NOMOR_IZIN", "{urut:04d}/{kode}/DPMPTSP/{tahun}")
# Pejabat yang tercantum di dokumen izin (tanda tangan tetap sesuai prosedur dinas).
# Peta Pusat Informasi Investasi. Tanpa kunci, peta tetap tampil lewat embed Google Maps
# (satu titik sekali tampil). Dengan kunci (Maps JavaScript API + Maps Embed API, dibatasi
# HTTP referrer ke domain portal), semua titik tampil sekaligus di satu peta.
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()

PEJABAT_IZIN = os.environ.get("PEJABAT_IZIN", "Kepala DPMPTSP Kabupaten Lombok Timur")
