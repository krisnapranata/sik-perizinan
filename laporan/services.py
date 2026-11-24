"""Laporan bulanan layanan izin (PRD AN-05). Hanya agregat: tanpa data pribadi pemohon."""

from collections import Counter, defaultdict
from datetime import date

from django.db.models import Count, Min
from django.utils import timezone

from perizinan.models import Aksi, Permohonan, RiwayatVerifikasi, StatusPermohonan

AKSI_PETUGAS = {
    Aksi.TERUSKAN, Aksi.SETUJUI, Aksi.MEMENUHI, Aksi.MINTA_PERBAIKAN, Aksi.TOLAK,
    Aksi.TIDAK_MEMENUHI, Aksi.TERBIT,
}


def rentang_bulan(tahun, bulan):
    zona = timezone.get_current_timezone()
    awal = timezone.make_aware(timezone.datetime(tahun, bulan, 1), zona)
    lanjut = (tahun + 1, 1) if bulan == 12 else (tahun, bulan + 1)
    return awal, timezone.make_aware(timezone.datetime(*lanjut, 1), zona)


def ringkasan(tahun, bulan):
    awal, akhir = rentang_bulan(tahun, bulan)
    masuk = Permohonan.objects.filter(dibuat_pada__gte=awal, dibuat_pada__lt=akhir)
    label_status = dict(StatusPermohonan.choices)

    per_status = [
        (label_status[b["status"]], b["n"])
        for b in masuk.values("status").annotate(n=Count("id")).order_by("status")
    ]
    per_jenis = [
        (b["jenis_izin__nama"], b["n"])
        for b in masuk.values("jenis_izin__nama").annotate(n=Count("id")).order_by("-n")
    ]

    riwayat = list(
        RiwayatVerifikasi.objects.filter(waktu__gte=awal, waktu__lt=akhir)
        .select_related("verifikator")
        .order_by("permohonan_id", "waktu", "id")
    )
    per_verifikator = defaultdict(Counter)
    for r in riwayat:
        if r.aksi in AKSI_PETUGAS:
            per_verifikator[r.verifikator.nama][r.aksi] += 1

    baris_verifikator = [
        {
            "nama": nama,
            "teruskan": n[Aksi.TERUSKAN] + n[Aksi.SETUJUI] + n[Aksi.MEMENUHI],
            "kembalikan": n[Aksi.MINTA_PERBAIKAN],
            "tolak": n[Aksi.TOLAK] + n[Aksi.TIDAK_MEMENUHI],
            "terbit": n[Aksi.TERBIT],
            "total": sum(n.values()),
        }
        for nama, n in sorted(per_verifikator.items())
    ]

    return {
        "tahun": tahun,
        "bulan": bulan,
        "judul_bulan": date(tahun, bulan, 1),
        "total": masuk.count(),
        "per_status": per_status,
        "per_jenis": per_jenis,
        "per_verifikator": baris_verifikator,
        "lama_tahap": _lama_tahap(riwayat, label_status),
        "lama_proses": lama_proses(awal, akhir),
    }


def lama_proses(awal=None, akhir=None):
    """Rata-rata hari dari pengajuan pertama sampai izin terbit, untuk izin yang terbit
    dalam rentang waktu (atau semua bila rentang kosong)."""
    terbit = RiwayatVerifikasi.objects.filter(aksi=Aksi.TERBIT)
    if awal is not None:
        terbit = terbit.filter(waktu__gte=awal, waktu__lt=akhir)
    waktu_terbit = dict(terbit.values_list("permohonan_id", "waktu"))
    if not waktu_terbit:
        return {"jumlah": 0, "rata_hari": None}
    pertama = (
        RiwayatVerifikasi.objects.filter(permohonan_id__in=waktu_terbit, aksi=Aksi.KIRIM)
        .values("permohonan_id")
        .annotate(awal=Min("waktu"))
    )
    hari = [(waktu_terbit[b["permohonan_id"]] - b["awal"]).total_seconds() / 86400 for b in pertama]
    return {"jumlah": len(hari), "rata_hari": round(sum(hari) / len(hari), 1) if hari else None}


def _lama_tahap(riwayat, label_status):
    """Lama satu tahap = selisih dari masuk tahap sampai tahap itu ditinggalkan."""
    durasi = defaultdict(list)
    sebelumnya = None
    for r in riwayat:
        if sebelumnya is not None and sebelumnya.permohonan_id == r.permohonan_id:
            durasi[r.dari_status].append((r.waktu - sebelumnya.waktu).total_seconds())
        sebelumnya = r
    urutan = [
        StatusPermohonan.DIAJUKAN,
        StatusPermohonan.PENILAIAN_TEKNIS,
        StatusPermohonan.DISETUJUI,
    ]
    return [
        (label_status[s], len(durasi[s]), round(sum(durasi[s]) / len(durasi[s]) / 3600, 1))
        for s in urutan
        if durasi[s]
    ]
