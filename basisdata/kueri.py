"""Pencarian, filter, dan rekap (PRD DB-01..DB-03, AN-01..AN-03, AN-05).

Semua angka rekap dihitung dari sini, sehingga daftar, dasbor, dan ekspor selalu sama.
"""

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from basisdata.models import (
    IzinNonOSS,
    JenisIzinNonOSS,
    Kecamatan,
    ProyekOSS,
    Sektor,
    StatusIzin,
    StatusNonOSS,
)

FILTER_OSS = ["tahun", "sektor", "kecamatan", "skala", "kbli", "risiko", "status_pm", "status_izin"]
# "belum" mewakili status kosong, karena nilai kosong di dropdown berarti "semua".
PILIHAN_STATUS_IZIN = {"aktif": "Aktif", "dicabut": "Dicabut", "belum": "Belum diisi"}
FILTER_NONOSS = ["tahun", "jenis", "kecamatan", "status"]


def _int(teks):
    try:
        return int(teks)
    except (TypeError, ValueError):
        return None


def filter_oss(params):
    """Kembalikan (queryset, dict filter yang aktif). `params` = request.GET."""
    qs = ProyekOSS.objects.select_related("pelaku", "kbli", "kecamatan", "kelurahan")
    aktif = {}
    q = (params.get("q") or "").strip()
    if q:
        aktif["q"] = q
        qs = qs.filter(
            Q(pelaku__nib__startswith=q)
            | Q(pelaku__nama__icontains=q)
            | Q(nama_proyek__icontains=q)
            | Q(id_proyek=q)
        )
    for kunci in FILTER_OSS:
        nilai = (params.get(kunci) or "").strip()
        if not nilai:
            continue
        if kunci == "tahun" and _int(nilai):
            qs = qs.filter(tahun=_int(nilai))
        elif kunci == "sektor" and nilai in Sektor.values:
            qs = qs.filter(kbli__sektor=nilai)
        elif kunci == "kecamatan" and _int(nilai):
            qs = qs.filter(kecamatan_id=_int(nilai))
        elif kunci == "skala":
            qs = qs.filter(skala=nilai)
        elif kunci == "kbli":
            qs = qs.filter(kbli_id__startswith=nilai)
        elif kunci == "risiko":
            qs = qs.filter(risiko=nilai)
        elif kunci == "status_pm":
            qs = qs.filter(pelaku__status_pm=nilai)
        elif kunci == "status_izin" and nilai in PILIHAN_STATUS_IZIN:
            qs = qs.filter(status_izin=StatusIzin.BELUM if nilai == "belum" else nilai)
        else:
            continue
        aktif[kunci] = nilai
    return qs, aktif


def rekap_oss(qs):
    """Jumlah usaha = NIB unik; jumlah proyek = baris; investasi dan TKI = jumlah kolom."""
    r = qs.order_by().aggregate(
        usaha=Count("pelaku", distinct=True),
        proyek=Count("id"),
        investasi=Coalesce(Sum("investasi"), 0),
        tki=Coalesce(Sum("tki"), 0),
    )
    return r


def pilihan_oss():
    """Isi dropdown filter, diambil dari data yang ada."""
    def beda(kolom):
        return [
            v
            for v in ProyekOSS.objects.order_by(kolom).values_list(kolom, flat=True).distinct()
            if v not in (None, "")
        ]

    return {
        "tahun": sorted(beda("tahun"), reverse=True),
        "sektor": Sektor.choices,
        "kecamatan": Kecamatan.objects.all(),
        "skala": beda("skala"),
        "risiko": beda("risiko"),
        "status_pm": beda("pelaku__status_pm"),
        "status_izin": list(PILIHAN_STATUS_IZIN.items()),
    }


def filter_nonoss(params):
    qs = IzinNonOSS.objects.select_related("jenis", "kecamatan", "kelurahan")
    aktif = {}
    q = (params.get("q") or "").strip()
    if q:
        aktif["q"] = q
        qs = qs.filter(Q(nomor_izin__icontains=q) | Q(nama_pemohon__icontains=q))
    for kunci in FILTER_NONOSS:
        nilai = (params.get(kunci) or "").strip()
        if not nilai:
            continue
        if kunci == "tahun" and _int(nilai):
            qs = qs.filter(tahun=_int(nilai))
        elif kunci == "jenis" and _int(nilai):
            qs = qs.filter(jenis_id=_int(nilai))
        elif kunci == "kecamatan" and _int(nilai):
            qs = qs.filter(kecamatan_id=_int(nilai))
        elif kunci == "status" and nilai in StatusNonOSS.values:
            qs = qs.filter(status=nilai)
        else:
            continue
        aktif[kunci] = nilai
    return qs, aktif


def rekap_nonoss(qs):
    per_status = dict(qs.order_by().values_list("status").annotate(n=Count("id")))
    return {
        "total": sum(per_status.values()),
        "per_status": [(label, per_status.get(kode, 0)) for kode, label in StatusNonOSS.choices],
    }


def pilihan_nonoss():
    return {
        "tahun": list(
            IzinNonOSS.objects.order_by("-tahun").values_list("tahun", flat=True).distinct()
        ),
        "jenis": JenisIzinNonOSS.objects.all(),
        "kecamatan": Kecamatan.objects.all(),
        "status": StatusNonOSS.choices,
    }


# ---------------------------------------------------------------- statistik (Modul 4)


def _sebaran(qs, kolom, label=None, kosong="Tidak diisi"):
    baris = (
        qs.order_by()
        .values(kolom)
        .annotate(
            proyek=Count("id"),
            usaha=Count("pelaku", distinct=True),
            investasi=Coalesce(Sum("investasi"), 0),
        )
        .order_by("-proyek")
    )
    return [
        {
            "nama": (label or {}).get(b[kolom], b[kolom]) or kosong,
            "proyek": b["proyek"],
            "usaha": b["usaha"],
            "investasi": b["investasi"],
        }
        for b in baris
    ]


def statistik(tahun=None):
    """Hanya angka agregat: aman untuk halaman publik (PRD AN-07, DB-08)."""
    semua = ProyekOSS.objects.all()
    qs = semua.filter(tahun=tahun) if tahun else semua

    tren = list(
        semua.order_by()
        .exclude(tahun=None)
        .values("tahun")
        .annotate(
            proyek=Count("id"),
            usaha=Count("pelaku", distinct=True),
            investasi=Coalesce(Sum("investasi"), 0),
        )
        .order_by("tahun")
    )
    nonoss = IzinNonOSS.objects.filter(tahun=tahun) if tahun else IzinNonOSS.objects.all()
    per_jenis = list(
        nonoss.order_by().values_list("jenis__nama").annotate(n=Count("id")).order_by("-n")
    )
    return {
        "tahun": tahun,
        "pilihan_tahun": [t["tahun"] for t in reversed(tren)],
        "ringkasan": rekap_oss(qs),
        "tren": tren,
        "maks_tren": max((t["proyek"] for t in tren), default=0),
        "per_kecamatan": _sebaran(qs, "kecamatan__nama"),
        "per_sektor": _sebaran(qs, "kbli__sektor", dict(Sektor.choices)),
        "per_skala": _sebaran(qs, "skala"),
        "per_risiko": _sebaran(qs, "risiko"),
        "nonoss": rekap_nonoss(nonoss) | {"per_jenis": per_jenis},
        "layanan": rekap_layanan(),
    }


def rekap_layanan():
    """AN-05: permohonan izin online per status dan rata-rata lama proses sampai terbit."""
    from laporan.services import lama_proses
    from perizinan.models import Permohonan, StatusPermohonan

    per_status = dict(
        Permohonan.objects.exclude(status=StatusPermohonan.DRAF)
        .order_by()
        .values_list("status")
        .annotate(n=Count("id"))
    )
    return {
        "total": sum(per_status.values()),
        "per_status": [
            (label, per_status.get(kode, 0))
            for kode, label in StatusPermohonan.choices
            if kode != StatusPermohonan.DRAF
        ],
        "lama": lama_proses(),
    }
