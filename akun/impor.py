"""Impor pengguna massal dari CSV atau Excel (.xlsx) lewat panel admin.

Alur: baca berkas -> validasi semua baris -> bila ada satu saja baris salah, tidak ada yang
disimpan (admin memperbaiki berkas lalu mengunggah ulang). Email yang sudah terdaftar dilewati,
jadi berkas yang sama aman diunggah berulang kali.
"""

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

from django.contrib.auth.hashers import identify_hasher
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from akun.models import Pemohon, Peran, TipePemohon, User
from core.audit import catat

MAKS_BARIS = 5000
EKSTENSI = {".csv", ".xlsx", ".xlsm"}

# Nama kolom di berkas -> nama kolom internal. Header dibandingkan setelah dinormalkan
# (huruf kecil, spasi/tanda hubung jadi garis bawah).
ALIAS = {
    "email": "email",
    "e_mail": "email",
    "surel": "email",
    "username": "email",
    "user": "email",
    "password": "password",
    "pass": "password",
    "kata_sandi": "password",
    "sandi": "password",
    "nama": "nama",
    "name": "nama",
    "nama_lengkap": "nama",
    "nip": "nip",
    "unit_kerja": "unit_kerja",
    "unit": "unit_kerja",
    "peran": "peran",
    "role": "peran",
    "aktif": "aktif",
    "tipe": "tipe",
    "tipe_pemohon": "tipe",
    "nama_pemohon": "nama_pemohon",
    "nama_badan_hukum": "nama_pemohon",
    "nama_usaha": "nama_pemohon",
    "nama_perusahaan": "nama_pemohon",
    "nik": "nik",
    "npwp": "npwp",
    "hp": "hp",
    "no_hp": "hp",
    "nomor_hp": "hp",
    "telepon": "hp",
    "no_telepon": "hp",
    "alamat": "alamat",
    "nib": "nib",
}

KOLOM_TEMPLATE = [
    "email", "password", "nama", "nip", "unit_kerja", "peran",
    "tipe", "nama_pemohon", "nik", "npwp", "hp", "alamat", "nib",
]
CONTOH_TEMPLATE = [
    ["kasi.baru@contoh.go.id", "", "Nama Pegawai", "198001012005011001",
     "Seksi Pelayanan Perizinan", "kasi", "", "", "", "", "", "", ""],
    ["pemohon@contoh.com", "PasswordLama-123", "Nama Pemohon", "", "", "pemohon",
     "perorangan", "", "5203010101900001", "", "081234567890", "Jl. Contoh No. 1, Selong", ""],
]

KOLOM_PROFIL = ("tipe", "nama_pemohon", "nik", "npwp", "hp", "alamat", "nib")


class BerkasTidakValid(Exception):
    pass


@dataclass
class HasilImpor:
    dibuat: list = field(default_factory=list)        # (email, pakai_password_default)
    dilewati: list = field(default_factory=list)      # (nomor_baris, email, alasan)
    galat: list = field(default_factory=list)         # (nomor_baris, pesan)

    @property
    def jumlah_password_default(self):
        return sum(1 for _, default in self.dibuat if default)


# ---------------------------------------------------------------- membaca berkas


def _normal_header(teks):
    teks = str(teks or "").strip().lower()
    for c in " -./":
        teks = teks.replace(c, "_")
    return ALIAS.get(teks.strip("_"), None)


def _teks(nilai):
    """Sel Excel bisa berupa angka: 81234567890.0 -> '81234567890'."""
    if nilai is None:
        return ""
    if isinstance(nilai, bool):
        return "1" if nilai else "0"
    if isinstance(nilai, float) and nilai.is_integer():
        nilai = int(nilai)
    return str(nilai).strip()


def _baca_csv(isi):
    try:
        teks = isi.decode("utf-8-sig")
    except UnicodeDecodeError:
        teks = isi.decode("latin-1")  # CSV dari Excel Windows lama
    try:
        dialek = csv.Sniffer().sniff(teks[:4096], delimiters=",;\t")
    except csv.Error:
        dialek = csv.excel
    return list(csv.reader(io.StringIO(teks), dialek))


def _baca_xlsx(isi):
    from openpyxl import load_workbook

    try:
        buku = load_workbook(io.BytesIO(isi), read_only=True, data_only=True)
    except Exception as galat:  # openpyxl melempar berbagai jenis galat untuk berkas rusak
        raise BerkasTidakValid("Berkas Excel tidak bisa dibaca. Simpan ulang sebagai .xlsx.") from galat
    try:
        lembar = buku.worksheets[0]
        return [list(baris) for baris in lembar.iter_rows(values_only=True)]
    finally:
        buku.close()


def baca_berkas(berkas):
    """Kembalikan list of (nomor_baris, dict kolom internal -> teks)."""
    ekstensi = Path(berkas.name).suffix.lower()
    if ekstensi == ".xls":
        raise BerkasTidakValid("Format .xls lama tidak didukung. Simpan ulang sebagai .xlsx atau .csv.")
    if ekstensi not in EKSTENSI:
        raise BerkasTidakValid("Berkas harus .csv atau .xlsx.")

    isi = berkas.read()
    baris = _baca_csv(isi) if ekstensi == ".csv" else _baca_xlsx(isi)

    # Header = baris pertama yang tidak kosong.
    while baris and not any(_teks(s) for s in baris[0]):
        baris.pop(0)
    if not baris:
        raise BerkasTidakValid("Berkas kosong.")

    header = [_normal_header(h) for h in baris[0]]
    if "email" not in header:
        raise BerkasTidakValid(
            "Kolom 'email' tidak ditemukan di baris pertama. Unduh template untuk contoh format."
        )

    data = []
    for nomor, sel in enumerate(baris[1:], start=2):
        nilai = {}
        for kolom, isi_sel in zip(header, sel):
            if kolom and kolom not in nilai:
                nilai[kolom] = _teks(isi_sel)
        if any(nilai.values()):
            data.append((nomor, nilai))
    if not data:
        raise BerkasTidakValid("Berkas tidak berisi data pengguna.")
    if len(data) > MAKS_BARIS:
        raise BerkasTidakValid(f"Maksimal {MAKS_BARIS} baris per unggahan.")
    return data


# ---------------------------------------------------------------- validasi baris


def _peran(teks):
    if not teks:
        return Peran.PEMOHON
    kunci = teks.strip().lower()
    for nilai, label in Peran.choices:
        if kunci in (nilai, label.lower()):
            return nilai
    # Nama peran dari aplikasi lama tetap diterima.
    if kunci in ("loket", "petugas loket", "front office", "kasi", "kabid", "petugas"):
        return Peran.PETUGAS
    if kunci in ("kadis", "kepala dinas"):
        return Peran.PIMPINAN
    raise ValidationError(f"peran '{teks}' tidak dikenal")


def _tipe(teks, nik, npwp):
    kunci = teks.strip().lower().replace(" ", "_")
    if kunci in ("perorangan", "pribadi", "individu"):
        return TipePemohon.PERORANGAN
    if kunci in ("badan_hukum", "badan", "perusahaan", "cv", "pt"):
        return TipePemohon.BADAN_HUKUM
    if kunci:
        raise ValidationError(f"tipe pemohon '{teks}' tidak dikenal (perorangan / badan hukum)")
    return TipePemohon.BADAN_HUKUM if npwp and not nik else TipePemohon.PERORANGAN


def _hp(teks):
    teks = teks.replace(" ", "").replace("-", "")
    # Excel membuang angka 0 di depan: 81234567890 -> 081234567890
    if teks.startswith("8"):
        teks = "0" + teks
    return teks


def _aktif(teks):
    return teks.strip().lower() not in ("0", "tidak", "no", "false", "nonaktif", "n")


def _siapkan(nilai, password_default):
    """Kembalikan (user, pemohon_atau_None, pakai_default) yang belum disimpan."""
    email = nilai.get("email", "").lower()
    validate_email(email)

    nama = nilai.get("nama") or nilai.get("nama_pemohon")
    if not nama:
        raise ValidationError("nama wajib diisi")
    peran = _peran(nilai.get("peran", ""))

    user = User(
        email=email,
        nama=nama[:150],
        nip=nilai.get("nip", ""),
        unit_kerja=nilai.get("unit_kerja", ""),
        peran=peran,
        is_active=_aktif(nilai.get("aktif", "")),
    )
    password = nilai.get("password", "")
    pakai_default = not password
    if pakai_default:
        user.set_password(password_default)
        user.wajib_ganti_password = True
    elif _sudah_hash(password):
        user.password = password  # hash Django dari sistem lama dipakai apa adanya
    else:
        user.set_password(password)
    user.full_clean(exclude=["password"], validate_unique=False)

    pemohon = None
    profil = {k: nilai.get(k, "") for k in KOLOM_PROFIL}
    if peran == Peran.PEMOHON and (profil["hp"] or profil["alamat"]):
        if not profil["hp"] or not profil["alamat"]:
            raise ValidationError("data pemohon perlu hp dan alamat sekaligus")
        pemohon = Pemohon(
            user=user,
            tipe=_tipe(profil["tipe"], profil["nik"], profil["npwp"]),
            nama=(profil["nama_pemohon"] or nama)[:200],
            nik=profil["nik"],
            npwp=profil["npwp"],
            hp=_hp(profil["hp"]),
            alamat=profil["alamat"],
            nib=profil["nib"],
        )
        if pemohon.tipe == TipePemohon.PERORANGAN and not pemohon.nik:
            raise ValidationError("NIK wajib untuk pemohon perorangan")
        if pemohon.tipe == TipePemohon.BADAN_HUKUM and not pemohon.npwp:
            raise ValidationError("NPWP wajib untuk badan hukum")
        pemohon.full_clean(exclude=["user", "bukti_nib", "didaftarkan_oleh"])
    return user, pemohon, pakai_default


def _sudah_hash(password):
    try:
        identify_hasher(password)
        return True
    except ValueError:
        return False


def _pesan(galat):
    if hasattr(galat, "message_dict"):
        return "; ".join(f"{k}: {' '.join(v)}" for k, v in galat.message_dict.items())
    return "; ".join(galat.messages)


# ---------------------------------------------------------------- impor


def impor(berkas, password_default, admin):
    """Validasi seluruh berkas; simpan hanya bila tidak ada baris yang salah."""
    hasil = HasilImpor()
    data = baca_berkas(berkas)

    terdaftar = set(
        User.objects.filter(
            email__in=[n.get("email", "").lower() for _, n in data]
        ).values_list("email", flat=True)
    )
    siap = []
    dilihat = {}
    for nomor, nilai in data:
        email = nilai.get("email", "").lower()
        if email in terdaftar:
            hasil.dilewati.append((nomor, email, "email sudah terdaftar"))
            continue
        if email and email in dilihat:
            hasil.galat.append((nomor, f"email {email} ganda (juga di baris {dilihat[email]})"))
            continue
        dilihat[email] = nomor
        try:
            siap.append(_siapkan(nilai, password_default))
        except ValidationError as galat:
            hasil.galat.append((nomor, _pesan(galat)))

    if hasil.galat:
        return hasil

    with transaction.atomic():
        for user, pemohon, pakai_default in siap:
            user.save()
            if pemohon is not None:
                pemohon.user = user
                pemohon.save()
            catat(admin, "admin.impor_pengguna", user)
            hasil.dibuat.append((user.email, pakai_default))
        catat(
            admin,
            "admin.impor_berkas",
            None,
            f"Dibuat {len(hasil.dibuat)}, dilewati {len(hasil.dilewati)}, "
            f"password default {hasil.jumlah_password_default}",
        )
    return hasil


def template_xlsx():
    from openpyxl import Workbook

    buku = Workbook()
    lembar = buku.active
    lembar.title = "pengguna"
    lembar.append(KOLOM_TEMPLATE)
    for baris in CONTOH_TEMPLATE:
        lembar.append(baris)
    # Kolom angka panjang disimpan sebagai teks agar tidak berubah jadi notasi ilmiah.
    for kolom in ("D", "I", "J", "K", "M"):
        for sel in lembar[kolom]:
            sel.number_format = "@"
    keluaran = io.BytesIO()
    buku.save(keluaran)
    return keluaran.getvalue()


def template_csv():
    keluaran = io.StringIO()
    penulis = csv.writer(keluaran)
    penulis.writerow(KOLOM_TEMPLATE)
    penulis.writerows(CONTOH_TEMPLATE)
    return keluaran.getvalue().encode("utf-8-sig")
