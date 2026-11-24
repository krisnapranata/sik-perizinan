"""Impor file ekspor OSS-RBA (PRD DB-05).

Aturan:
- Satu baris = satu proyek. Id Proyek adalah kunci: bila sudah ada, barisnya diperbarui,
  sehingga ekspor yang sama atau yang lebih baru aman diunggah berulang kali.
- Pelaku usaha disimpan per NIB (teks, agar digit tidak terpotong).
- Baris yang valid disimpan; baris bermasalah dilewati dan dilaporkan dengan nomor barisnya.
- Status izin (aktif/dicabut) tidak ada di ekspor OSS, jadi isian petugas tidak ditimpa.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from akun.impor import BerkasTidakValid, _baca_csv, _baca_xlsx, _teks
from basisdata.models import (
    KBLI,
    ImporOSS,
    Kecamatan,
    Kelurahan,
    PelakuUsaha,
    ProyekOSS,
    Sektor,
    tahun_proyek,
)
from core.audit import catat

MAKS_BARIS = 200_000
EKSTENSI = {".csv", ".xlsx", ".xlsm"}
UKURAN_BATCH = 1000

# Header dinormalkan (huruf kecil, selain huruf/angka jadi "_"), lalu dicocokkan ke sini.
# Bila OSS mengganti nama kolom, cukup tambahkan alias baru.
ALIAS = {
    "id_proyek": "id_proyek",
    "uraian_jenis_proyek": "jenis_proyek",
    "jenis_proyek": "jenis_proyek",
    "nib": "nib",
    "nama_perusahaan": "nama_perusahaan",
    "tanggal_terbit_oss": "tanggal_terbit",
    "tanggal_terbit_proyek": "tanggal_terbit",
    "tanggal_terbit": "tanggal_terbit",
    "uraian_status_penanaman_modal": "status_pm",
    "status_penanaman_modal": "status_pm",
    "uraian_jenis_perusahaan": "jenis_perusahaan",
    "jenis_perusahaan": "jenis_perusahaan",
    "uraian_risiko_proyek": "risiko",
    "risiko_proyek": "risiko",
    "nama_proyek": "nama_proyek",
    "uraian_skala_usaha": "skala",
    "skala_usaha": "skala",
    "alamat_usaha": "alamat",
    "kab_kota_usaha": "kab_kota",
    "kab_kota": "kab_kota",
    "kecamatan_usaha": "kecamatan",
    "kecamatan": "kecamatan",
    "kelurahan_usaha": "kelurahan",
    "kelurahan": "kelurahan",
    "day_of_tanggal_pengajuan_proyek": "tanggal_pengajuan",
    "tanggal_pengajuan_proyek": "tanggal_pengajuan",
    "kbli": "kbli",
    "judul_kbli": "judul_kbli",
    "kl_sektor_pembina": "kl_pembina",
    "luas_tanah": "luas_tanah",
    "satuan_tanah": "satuan_tanah",
    "jumlah_investasi": "investasi",
    "tki": "tki",
}
WAJIB = {"id_proyek": "Id Proyek", "nib": "NIB", "nama_perusahaan": "Nama Perusahaan",
         "kecamatan": "Kecamatan"}

BULAN = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7,
    "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
    "january": 1, "february": 2, "march": 3, "may": 5, "june": 6, "july": 7, "august": 8,
    "october": 10, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "agu": 8, "agt": 8,
    "aug": 8, "sep": 9, "okt": 10, "oct": 10, "nov": 11, "des": 12, "dec": 12,
}


@dataclass
class HasilImpor:
    jumlah_baris: int = 0
    baru: int = 0
    diperbarui: int = 0
    tetap: int = 0
    galat: list = field(default_factory=list)  # (nomor_baris, pesan)


class BarisSalah(ValueError):
    pass


# ---------------------------------------------------------------- konversi nilai


def _kunci(teks):
    return re.sub(r"[^a-z0-9]+", "_", str(teks or "").strip().lower()).strip("_")


def _nama_wilayah(teks):
    """'KEC. SAKRA  TIMUR' -> 'sakra timur' untuk dicocokkan."""
    teks = re.sub(r"^(kecamatan|kec\.?|kelurahan|kel\.?|desa)\s+", "", teks.strip(), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", teks).lower()


def tanggal(nilai, kolom):
    """Menyeragamkan format campuran di ekspor OSS: 04/10/2018, 2018-10-04, 6 Juni 2022."""
    if nilai in (None, ""):
        return None
    if isinstance(nilai, datetime):
        return nilai.date()
    if isinstance(nilai, date):
        return nilai
    if isinstance(nilai, (int, float)) and not isinstance(nilai, bool):
        if 20000 < nilai < 80000:  # nomor seri tanggal Excel
            return date(1899, 12, 30) + timedelta(days=int(nilai))
        raise BarisSalah(f"{kolom} tidak dikenali: {nilai}")
    teks = str(nilai).strip()
    try:
        m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?:\s.*)?", teks)
        if m:  # hari/bulan/tahun, urutan yang dipakai OSS
            return date(int(m[3]), int(m[2]), int(m[1]))
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T].*)?", teks)
        if m:
            return date(int(m[1]), int(m[2]), int(m[3]))
        m = re.fullmatch(r"(\d{1,2})[\s-]+([A-Za-z]+)\.?[\s-]+(\d{4})", teks)
        if m and m[2].lower() in BULAN:
            return date(int(m[3]), BULAN[m[2].lower()], int(m[1]))
    except ValueError:
        pass  # mis. 31/02/2020
    raise BarisSalah(f"{kolom} tidak dikenali: {teks}")


def _angka_bulat(nilai, kolom):
    if nilai in (None, ""):
        return 0
    if isinstance(nilai, (int, float)) and not isinstance(nilai, bool):
        if nilai < 0:
            raise BarisSalah(f"{kolom} tidak boleh negatif.")
        return int(nilai)
    teks = re.sub(r"(?i)^rp\.?\s*", "", str(nilai).strip())
    teks = re.sub(r"[,.]00$", "", teks)  # 150.000.000,00
    teks = teks.replace(".", "").replace(",", "").replace(" ", "")
    if not teks.isdigit():
        raise BarisSalah(f"{kolom} bukan angka: {nilai}")
    return int(teks)


def _desimal(nilai, kolom):
    if nilai in (None, ""):
        return None
    if isinstance(nilai, (int, float)) and not isinstance(nilai, bool):
        return Decimal(str(nilai)).quantize(Decimal("0.01"))
    teks = str(nilai).strip().replace(" ", "")
    if "," in teks:  # format Indonesia: 1.234,5
        teks = teks.replace(".", "").replace(",", ".")
    try:
        hasil = Decimal(teks)
    except InvalidOperation:
        raise BarisSalah(f"{kolom} bukan angka: {nilai}") from None
    if hasil < 0:
        raise BarisSalah(f"{kolom} tidak boleh negatif.")
    return hasil.quantize(Decimal("0.01"))


def _digit(nilai, kolom, panjang):
    teks = _teks(nilai).replace(" ", "")
    teks = teks.removeprefix("'")  # Excel kadang menyimpan tanda kutip teks
    if not teks.isdigit():
        raise BarisSalah(f"{kolom} harus berupa angka: {teks or '(kosong)'}")
    if len(teks) == panjang - 1:  # satu nol di depan hilang saat sel dibaca sebagai angka
        teks = "0" + teks
    if len(teks) != panjang:
        raise BarisSalah(f"{kolom} harus {panjang} digit: {teks}")
    return teks


def sektor_dari_kbli(kode):
    """Pemetaan awal KBLI -> sektor KAK berdasarkan golongan pokok (2 digit pertama)."""
    golongan = int(kode[:2])
    if golongan in (1, 2):
        return Sektor.PERTANIAN
    if golongan == 3:
        return Sektor.PERIKANAN
    if 45 <= golongan <= 47:
        return Sektor.PERDAGANGAN
    if golongan in (55, 56, 79, 93):
        return Sektor.PARIWISATA
    return Sektor.LAINNYA


# ---------------------------------------------------------------- membaca berkas


def baca_berkas(berkas):
    """Kembalikan list (nomor_baris, dict kolom internal -> nilai mentah)."""
    ekstensi = Path(berkas.name).suffix.lower()
    if ekstensi == ".xls":
        raise BerkasTidakValid("Format .xls lama tidak didukung. Simpan ulang sebagai .xlsx atau .csv.")
    if ekstensi not in EKSTENSI:
        raise BerkasTidakValid("Berkas harus .xlsx atau .csv.")
    isi = berkas.read()
    baris = _baca_csv(isi) if ekstensi == ".csv" else _baca_xlsx(isi)

    while baris and not any(_teks(s) for s in baris[0]):
        baris.pop(0)
    if not baris:
        raise BerkasTidakValid("Berkas kosong.")
    header = [ALIAS.get(_kunci(h)) for h in baris[0]]
    kurang = [label for kolom, label in WAJIB.items() if kolom not in header]
    if kurang:
        raise BerkasTidakValid(
            "Kolom wajib tidak ditemukan di baris judul: " + ", ".join(kurang) + "."
        )

    data = []
    for nomor, sel in enumerate(baris[1:], start=2):
        nilai = {}
        for kolom, isi_sel in zip(header, sel):
            if kolom and kolom not in nilai:
                nilai[kolom] = isi_sel.strip() if isinstance(isi_sel, str) else isi_sel
        if any(_teks(v) for v in nilai.values()):
            data.append((nomor, nilai))
    if not data:
        raise BerkasTidakValid("Berkas tidak berisi data proyek.")
    if len(data) > MAKS_BARIS:
        raise BerkasTidakValid(f"Maksimal {MAKS_BARIS:,} baris per unggahan; pecah berkasnya.")
    return data


# ---------------------------------------------------------------- impor


class _Wilayah:
    def __init__(self):
        self.kecamatan = {_nama_wilayah(k.nama): k for k in Kecamatan.objects.all()}
        self.kelurahan = {(k.kecamatan_id, _nama_wilayah(k.nama)): k for k in Kelurahan.objects.all()}

    def cari_kecamatan(self, teks):
        kec = self.kecamatan.get(_nama_wilayah(_teks(teks)))
        if kec is None:
            raise BarisSalah(f"Kecamatan tidak dikenal di Lombok Timur: {_teks(teks) or '(kosong)'}")
        return kec

    def kelurahan_untuk(self, kecamatan, teks):
        nama = re.sub(r"\s+", " ", _teks(teks))
        if not nama:
            return None
        kunci = (kecamatan.pk, _nama_wilayah(nama))
        if kunci not in self.kelurahan:
            self.kelurahan[kunci] = Kelurahan.objects.create(kecamatan=kecamatan, nama=nama.title())
        return self.kelurahan[kunci]


def _siapkan(nilai, wilayah):
    """Validasi satu baris. Kembalikan (data_pelaku, data_kbli, data_proyek)."""
    id_proyek = _teks(nilai.get("id_proyek"))
    if not id_proyek:
        raise BarisSalah("Id Proyek kosong.")
    if len(id_proyek) > 40:
        raise BarisSalah("Id Proyek terlalu panjang.")
    nib = _digit(nilai.get("nib"), "NIB", 13)
    nama = _teks(nilai.get("nama_perusahaan"))
    if not nama:
        raise BarisSalah("Nama Perusahaan kosong.")

    kecamatan = wilayah.cari_kecamatan(nilai.get("kecamatan"))
    kbli = None
    if _teks(nilai.get("kbli")):
        kbli = {
            "kode": _digit(nilai.get("kbli"), "KBLI", 5),
            "judul": _teks(nilai.get("judul_kbli"))[:255],
            "kl_pembina": _teks(nilai.get("kl_pembina"))[:150],
        }

    proyek = {
        "id_proyek": id_proyek,
        "pelaku_id": nib,
        "jenis_proyek": _teks(nilai.get("jenis_proyek"))[:30],
        "nama_proyek": _teks(nilai.get("nama_proyek"))[:255],
        "kbli_id": kbli["kode"] if kbli else None,
        "skala": _teks(nilai.get("skala"))[:30],
        "risiko": _teks(nilai.get("risiko"))[:30],
        "alamat": _teks(nilai.get("alamat")),
        "kab_kota": _teks(nilai.get("kab_kota"))[:60],
        "kecamatan": kecamatan,
        "kelurahan_nama": nilai.get("kelurahan"),
        "tanggal_terbit": tanggal(nilai.get("tanggal_terbit"), "Tanggal terbit"),
        "tanggal_pengajuan": tanggal(nilai.get("tanggal_pengajuan"), "Tanggal pengajuan"),
        "luas_tanah": _desimal(nilai.get("luas_tanah"), "Luas tanah"),
        "satuan_tanah": _teks(nilai.get("satuan_tanah"))[:10],
        "investasi": _angka_bulat(nilai.get("investasi"), "Jumlah investasi"),
        "tki": _angka_bulat(nilai.get("tki"), "TKI"),
    }
    pelaku = {
        "nib": nib,
        "nama": nama[:255],
        "jenis_perusahaan": _teks(nilai.get("jenis_perusahaan"))[:80],
        "status_pm": _teks(nilai.get("status_pm")).upper()[:10],
    }
    return pelaku, kbli, proyek


KOLOM_PROYEK = [
    "pelaku_id", "jenis_proyek", "nama_proyek", "kbli_id", "skala", "risiko", "alamat",
    "kab_kota", "kecamatan_id", "kelurahan_id", "tanggal_terbit", "tanggal_pengajuan", "tahun",
    "luas_tanah", "satuan_tanah", "investasi", "tki",
]


def impor(berkas, pengguna):
    data = baca_berkas(berkas)
    hasil = HasilImpor(jumlah_baris=len(data))
    wilayah = _Wilayah()

    siap, terlihat = [], {}
    for nomor, nilai in data:
        try:
            pelaku, kbli, proyek = _siapkan(nilai, wilayah)
        except BarisSalah as galat:
            hasil.galat.append((nomor, str(galat)))
            continue
        if proyek["id_proyek"] in terlihat:
            hasil.galat.append(
                (nomor, f"Id Proyek {proyek['id_proyek']} ganda; sama dengan baris {terlihat[proyek['id_proyek']]}.")
            )
            continue
        terlihat[proyek["id_proyek"]] = nomor
        siap.append((pelaku, kbli, proyek))

    with transaction.atomic():
        _simpan(siap, wilayah, hasil)
        catatan = ImporOSS.objects.create(
            pengguna=pengguna,
            nama_berkas=Path(berkas.name).name[:255],
            jumlah_baris=hasil.jumlah_baris,
            baru=hasil.baru,
            diperbarui=hasil.diperbarui,
            tetap=hasil.tetap,
            gagal=len(hasil.galat),
            laporan=[[n, p] for n, p in hasil.galat[:1000]],
        )
        catat(
            pengguna,
            "database.impor_oss",
            catatan,
            f"{hasil.jumlah_baris} baris: {hasil.baru} baru, {hasil.diperbarui} diperbarui, "
            f"{hasil.tetap} tetap, {len(hasil.galat)} gagal",
        )
    return hasil, catatan


def _simpan(siap, wilayah, hasil):
    # Pelaku usaha: data dari baris terakhir untuk NIB yang sama dianggap terbaru.
    pelaku_baru = {p["nib"]: p for p, _, _ in siap}
    ada = PelakuUsaha.objects.in_bulk(list(pelaku_baru))
    buat, ubah = [], []
    for nib, p in pelaku_baru.items():
        if nib not in ada:
            buat.append(PelakuUsaha(**p))
        else:
            lama = ada[nib]
            if any(getattr(lama, k) != v for k, v in p.items() if v):
                for k, v in p.items():
                    if v:
                        setattr(lama, k, v)
                ubah.append(lama)
    PelakuUsaha.objects.bulk_create(buat, batch_size=UKURAN_BATCH)
    PelakuUsaha.objects.bulk_update(
        ubah, ["nama", "jenis_perusahaan", "status_pm"], batch_size=UKURAN_BATCH
    )

    kbli_baru = {k["kode"]: k for _, k, _ in siap if k}
    ada = KBLI.objects.in_bulk(list(kbli_baru))
    KBLI.objects.bulk_create(
        [KBLI(sektor=sektor_dari_kbli(kode), **k) for kode, k in kbli_baru.items() if kode not in ada],
        batch_size=UKURAN_BATCH,
    )
    # Judul/KL yang dulu kosong dilengkapi; sektor yang sudah diatur admin tidak disentuh.
    lengkapi = []
    for kode, k in kbli_baru.items():
        lama = ada.get(kode)
        if lama and ((k["judul"] and not lama.judul) or (k["kl_pembina"] and not lama.kl_pembina)):
            lama.judul = lama.judul or k["judul"]
            lama.kl_pembina = lama.kl_pembina or k["kl_pembina"]
            lengkapi.append(lama)
    KBLI.objects.bulk_update(lengkapi, ["judul", "kl_pembina"], batch_size=UKURAN_BATCH)

    ada = {
        p.id_proyek: p
        for p in ProyekOSS.objects.filter(id_proyek__in=[pr["id_proyek"] for _, _, pr in siap])
    }
    buat, ubah, sekarang = [], [], timezone.now()
    for _, _, pr in siap:
        pr = dict(pr)
        kecamatan = pr.pop("kecamatan")
        kelurahan = wilayah.kelurahan_untuk(kecamatan, pr.pop("kelurahan_nama"))
        baru = ProyekOSS(kecamatan=kecamatan, kelurahan=kelurahan, **pr)
        baru.tahun = tahun_proyek(baru)
        lama = ada.get(pr["id_proyek"])
        if lama is None:
            buat.append(baru)
        elif any(getattr(lama, k) != getattr(baru, k) for k in KOLOM_PROYEK):
            for k in KOLOM_PROYEK:
                setattr(lama, k, getattr(baru, k))
            lama.diimpor_pada = sekarang
            ubah.append(lama)
        else:
            hasil.tetap += 1
    ProyekOSS.objects.bulk_create(buat, batch_size=UKURAN_BATCH)
    ProyekOSS.objects.bulk_update(ubah, [*KOLOM_PROYEK, "diimpor_pada"], batch_size=UKURAN_BATCH)
    hasil.baru, hasil.diperbarui = len(buat), len(ubah)
