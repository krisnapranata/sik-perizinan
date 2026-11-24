from django.conf import settings
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from basisdata.models import Kecamatan, Sektor
from investasi.models import PeluangInvestasi, Tingkat

# Pusat peta bila belum ada titik: Selong, ibu kota Kabupaten Lombok Timur.
PUSAT_LOTIM = {"lat": -8.65, "lng": 116.53}

_URUTAN_TINGKAT = Case(
    When(tingkat=Tingkat.SIAP_TAWAR, then=Value(0)),
    When(tingkat=Tingkat.PELUANG, then=Value(1)),
    default=Value(2),
    output_field=IntegerField(),
)


def _terbit():
    return PeluangInvestasi.objects.filter(tampil=True).select_related("kecamatan")


def daftar(request):
    """IN-01 dan IN-03: daftar dengan filter sektor, kecamatan, tingkat, dan peta titik proyek."""
    qs = _terbit()
    aktif = {}
    sektor = request.GET.get("sektor", "")
    if sektor in Sektor.values:
        qs, aktif["sektor"] = qs.filter(sektor=sektor), sektor
    tingkat = request.GET.get("tingkat", "")
    if tingkat in Tingkat.values:
        qs, aktif["tingkat"] = qs.filter(tingkat=tingkat), tingkat
    kecamatan = request.GET.get("kecamatan", "")
    if kecamatan.isdigit():
        qs, aktif["kecamatan"] = qs.filter(kecamatan_id=kecamatan), kecamatan
    daftar_peluang = list(qs.annotate(urutan=_URUTAN_TINGKAT).order_by("urutan", "nama"))

    titik = [
        {
            "id": p.pk,
            "nama": p.nama,
            "lat": float(p.lintang),
            "lng": float(p.bujur),
            "tingkat": p.get_tingkat_display(),
            "sektor": p.get_sektor_display(),
            "kecamatan": p.kecamatan.nama,
            "url": reverse("investasi:detail", args=[p.pk]),
        }
        for p in daftar_peluang
        if p.ada_koordinat
    ]
    pilihan_kec = Kecamatan.objects.filter(peluang_investasi__tampil=True).distinct()
    return render(request, "investasi/daftar.html", {
        "daftar_peluang": daftar_peluang,
        "titik": titik,
        "pusat": titik[0] if titik else PUSAT_LOTIM,
        "aktif": aktif,
        "pilihan": {"sektor": Sektor.choices, "tingkat": Tingkat.choices, "kecamatan": pilihan_kec},
        "kunci_peta": settings.GOOGLE_MAPS_API_KEY,
    })


def detail(request, pk):
    """IN-02: profil proyek dengan lokasi di Google Maps dan kontak DPMPTSP."""
    p = get_object_or_404(_terbit(), pk=pk)
    return render(request, "investasi/detail.html", {
        "p": p,
        "kunci_peta": settings.GOOGLE_MAPS_API_KEY,
    })
