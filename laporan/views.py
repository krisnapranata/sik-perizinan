from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from core.audit import catat
from laporan import ekspor
from laporan.services import ringkasan
from perizinan.permissions import bisa_lihat_laporan


def _periode(request):
    if not bisa_lihat_laporan(request.user):
        raise PermissionDenied
    sekarang = timezone.localdate()
    try:
        tahun, bulan = (int(x) for x in request.GET.get("bulan", "").split("-"))
        if not (2000 <= tahun <= 2100 and 1 <= bulan <= 12):
            raise ValueError
    except ValueError:
        tahun, bulan = sekarang.year, sekarang.month
    return tahun, bulan


@login_required
def dasbor(request):
    tahun, bulan = _periode(request)
    return render(request, "laporan/dasbor.html", {"d": ringkasan(tahun, bulan)})


def _unduh(request, isi, jenis, ekstensi, tahun, bulan):
    catat(request.user, "laporan.ekspor", keterangan=f"{tahun}-{bulan:02d}.{ekstensi}")
    respons = HttpResponse(isi, content_type=jenis)
    nama = f"laporan-perizinan-{tahun}-{bulan:02d}.{ekstensi}"
    respons["Content-Disposition"] = f'attachment; filename="{nama}"'
    return respons


@login_required
def ekspor_excel(request):
    tahun, bulan = _periode(request)
    jenis = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return _unduh(request, ekspor.ke_excel(ringkasan(tahun, bulan)), jenis, "xlsx", tahun, bulan)


@login_required
def ekspor_pdf(request):
    tahun, bulan = _periode(request)
    return _unduh(
        request, ekspor.ke_pdf(ringkasan(tahun, bulan)), "application/pdf", "pdf", tahun, bulan
    )
