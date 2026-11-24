"""Angka dashboard per peran. Selalu dihitung dari permohonan_terlihat(): tidak ada kebocoran."""

from collections import Counter
from datetime import timedelta

from django.utils import timezone

from akun.models import Peran
from perizinan import services
from perizinan.models import Aksi, RiwayatVerifikasi, StatusPermohonan
from perizinan.permissions import permohonan_terlihat

S = StatusPermohonan
SEDANG_DIPROSES = [S.DIAJUKAN, S.PENILAIAN_TEKNIS, S.DISETUJUI]
LANGKAH = {
    S.DRAF: 0,
    S.PERLU_PERBAIKAN: 0,
    S.DIAJUKAN: 1,
    S.PENILAIAN_TEKNIS: 2,
    S.DISETUJUI: 3,
    S.TERBIT: 4,
    S.DITOLAK: 3,
}


def kemajuan(permohonan):
    """Persentase posisi berkas pada alur 4 langkah, untuk bilah kemajuan."""
    return LANGKAH.get(permohonan.status, 0) * 25


def _harian(riwayat_kirim, hari=14):
    hari_ini = timezone.localdate()
    hitung = Counter(timezone.localtime(w).date() for w in riwayat_kirim)
    deret = []
    for i in range(hari - 1, -1, -1):
        tanggal = hari_ini - timedelta(days=i)
        deret.append({"tanggal": tanggal, "jumlah": hitung.get(tanggal, 0)})
    puncak = max((d["jumlah"] for d in deret), default=0) or 1
    for d in deret:
        d["tinggi"] = round(d["jumlah"] / puncak * 100)
    return deret, puncak


def ringkasan(pengguna):
    terlihat = permohonan_terlihat(pengguna)
    sekarang = timezone.now()
    awal_bulan = timezone.localtime(sekarang).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    riwayat = RiwayatVerifikasi.objects.filter(permohonan__in=terlihat.values("pk"))

    kirim_14 = list(
        riwayat.filter(aksi=Aksi.KIRIM, waktu__gte=sekarang - timedelta(days=14)).values_list(
            "waktu", flat=True
        )
    )
    harian, puncak = _harian(kirim_14)
    minggu_ini = sum(d["jumlah"] for d in harian[7:])
    minggu_lalu = sum(d["jumlah"] for d in harian[:7])

    per_status = Counter(terlihat.values_list("status", flat=True))
    label = dict(S.choices)
    total = sum(per_status.values()) or 1
    distribusi = [
        {
            "kode": s,
            "label": label[s],
            "jumlah": per_status[s],
            "persen": round(per_status[s] / total * 100),
        }
        for s in S
        if per_status.get(s)
    ]

    bulan_ini = riwayat.filter(waktu__gte=awal_bulan)
    data = {
        "harian": harian,
        "puncak": puncak,
        "masuk_minggu_ini": minggu_ini,
        "selisih_minggu": minggu_ini - minggu_lalu,
        "distribusi": distribusi,
        "diproses": sum(per_status.get(s, 0) for s in SEDANG_DIPROSES),
        "terbit_bulan_ini": bulan_ini.filter(aksi=Aksi.TERBIT).count(),
        "dikembalikan_bulan_ini": bulan_ini.filter(aksi=Aksi.MINTA_PERBAIKAN).count(),
        "perlu_diperbaiki": per_status.get(S.PERLU_PERBAIKAN, 0) + per_status.get(S.DRAF, 0),
        "terbit": per_status.get(S.TERBIT, 0),
        "total": sum(per_status.values()),
        "terbaru": list(terlihat.order_by("-diperbarui_pada")[:6]),
    }
    if pengguna.pemeriksa:
        antrean = list(services.antrean(pengguna))
        sekarang = timezone.now()
        data["menunggu_saya"] = len(antrean)
        data["lewat_batas"] = sum(
            1 for p in antrean if p.batas_layanan and p.batas_layanan < sekarang
        )
    if pengguna.peran == Peran.PEMOHON:
        data["milik"] = [
            {"p": p, "kemajuan": kemajuan(p)} for p in terlihat.order_by("-diperbarui_pada")[:12]
        ]
    return data
