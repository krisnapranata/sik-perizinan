from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from akun.impor import BerkasTidakValid
from basisdata import ekspor, kueri
from basisdata.forms import ImporForm, IzinNonOSSForm, StatusIzinForm
from basisdata.impor import impor
from basisdata.models import ImporOSS, IzinNonOSS, PelakuUsaha, ProyekOSS
from basisdata.permissions import bisa_kelola_database, bisa_lihat_database
from core.audit import catat
from core.berkas import jenis_pratinjau, kirim_berkas, nama_aman
from core.models import LogAudit

PER_HALAMAN = 50


def _wajib_lihat(request):
    if not bisa_lihat_database(request.user):
        raise PermissionDenied


def _wajib_kelola(request):
    if not bisa_kelola_database(request.user):
        raise PermissionDenied


def _halaman(request, qs):
    return Paginator(qs, PER_HALAMAN).get_page(request.GET.get("halaman"))


def _unduh(request, isi, jenis, nama, aksi, filter_aktif):
    catat(request.user, aksi, keterangan=f"{nama}; {filter_aktif or 'semua data'}")
    respons = HttpResponse(isi, content_type=jenis)
    respons["Content-Disposition"] = f'attachment; filename="{nama}"'
    return respons


def _riwayat(objek):
    return LogAudit.objects.filter(
        objek_tipe=objek._meta.label, objek_id=str(objek.pk)
    ).select_related("pengguna")


# ---------------------------------------------------------------- OSS-RBA


def _rekap_baris_oss(r):
    return [
        ("Jumlah usaha (NIB unik)", r["usaha"]),
        ("Jumlah proyek", r["proyek"]),
        ("Total nilai investasi (Rp)", r["investasi"]),
        ("Total tenaga kerja", r["tki"]),
    ]


@login_required
def oss_daftar(request):
    _wajib_lihat(request)
    qs, aktif = kueri.filter_oss(request.GET)
    return render(
        request,
        "basisdata/oss_daftar.html",
        {
            "halaman": _halaman(request, qs),
            "rekap": kueri.rekap_oss(qs),
            "aktif": aktif,
            "pilihan": kueri.pilihan_oss(),
            "kueri": urlencode(aktif),
            "bisa_kelola": bisa_kelola_database(request.user),
        },
    )


@login_required
def oss_ekspor(request, format):
    _wajib_lihat(request)
    qs, aktif = kueri.filter_oss(request.GET)
    rekap = _rekap_baris_oss(kueri.rekap_oss(qs))
    judul = "Database Perizinan Berusaha (OSS-RBA)"
    if format == "xlsx":
        isi = ekspor.daftar_excel(judul, ekspor.KOLOM_OSS, qs, aktif, rekap)
        return _unduh(request, isi, ekspor.XLSX, "perizinan-oss.xlsx", "database.ekspor_oss", aktif)
    isi = ekspor.daftar_pdf(judul, ekspor.KOLOM_OSS, ekspor.KOLOM_OSS_PDF, qs, aktif,
                            [(a, ekspor.rupiah(b) if "investasi" in a else b) for a, b in rekap])
    return _unduh(request, isi, "application/pdf", "perizinan-oss.pdf", "database.ekspor_oss", aktif)


@login_required
def oss_detail(request, id_proyek):
    _wajib_lihat(request)
    proyek = get_object_or_404(
        ProyekOSS.objects.select_related("pelaku", "kbli", "kecamatan", "kelurahan"),
        id_proyek=id_proyek,
    )
    form = StatusIzinForm(instance=proyek)
    if request.method == "POST":
        _wajib_kelola(request)
        lama = proyek.get_status_izin_display()
        form = StatusIzinForm(request.POST, instance=proyek)
        if form.is_valid():
            form.save()
            catat(request.user, "database.status_izin", proyek,
                  f"Status izin: {lama} → {proyek.get_status_izin_display()}")
            messages.success(request, "Status izin disimpan.")
            return redirect("basisdata:oss_detail", proyek.id_proyek)
    return render(
        request,
        "basisdata/oss_detail.html",
        {
            "p": proyek,
            "form": form,
            "proyek_lain": proyek.pelaku.proyek.exclude(pk=proyek.pk).select_related("kecamatan"),
            "riwayat": _riwayat(proyek),
            "bisa_kelola": bisa_kelola_database(request.user),
        },
    )


@login_required
def usaha_detail(request, nib):
    _wajib_lihat(request)
    pelaku = get_object_or_404(PelakuUsaha, nib=nib)
    proyek = pelaku.proyek.select_related("kbli", "kecamatan", "kelurahan")
    return render(
        request,
        "basisdata/usaha_detail.html",
        {"u": pelaku, "proyek": proyek, "rekap": kueri.rekap_oss(proyek)},
    )


@login_required
def oss_impor(request):
    _wajib_kelola(request)
    form = ImporForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            hasil, catatan = impor(form.cleaned_data["berkas"], request.user)
        except BerkasTidakValid as galat:
            form.add_error("berkas", str(galat))
        else:
            if hasil.galat:
                messages.warning(request, f"{len(hasil.galat)} baris tidak diimpor. Lihat rinciannya.")
            else:
                messages.success(request, "Semua baris berhasil diimpor.")
            return redirect("basisdata:oss_impor_hasil", catatan.pk)
    return render(
        request,
        "basisdata/oss_impor.html",
        {"form": form, "riwayat": ImporOSS.objects.select_related("pengguna")[:10]},
    )


@login_required
def oss_impor_hasil(request, pk):
    _wajib_kelola(request)
    return render(
        request, "basisdata/oss_impor_hasil.html", {"i": get_object_or_404(ImporOSS, pk=pk)}
    )


# ---------------------------------------------------------------- NonOSS


@login_required
def nonoss_daftar(request):
    _wajib_lihat(request)
    qs, aktif = kueri.filter_nonoss(request.GET)
    return render(
        request,
        "basisdata/nonoss_daftar.html",
        {
            "halaman": _halaman(request, qs),
            "rekap": kueri.rekap_nonoss(qs),
            "aktif": aktif,
            "pilihan": kueri.pilihan_nonoss(),
            "kueri": urlencode(aktif),
            "bisa_kelola": bisa_kelola_database(request.user),
        },
    )


@login_required
def nonoss_ekspor(request, format):
    _wajib_lihat(request)
    qs, aktif = kueri.filter_nonoss(request.GET)
    r = kueri.rekap_nonoss(qs)
    rekap = [("Jumlah izin", r["total"]), *r["per_status"]]
    judul = "Database Perizinan Nonberusaha (NonOSS)"
    if format == "xlsx":
        isi = ekspor.daftar_excel(judul, ekspor.KOLOM_NONOSS, qs, aktif, rekap)
        return _unduh(request, isi, ekspor.XLSX, "perizinan-nonoss.xlsx",
                      "database.ekspor_nonoss", aktif)
    isi = ekspor.daftar_pdf(judul, ekspor.KOLOM_NONOSS, ekspor.KOLOM_NONOSS_PDF, qs, aktif, rekap)
    return _unduh(request, isi, "application/pdf", "perizinan-nonoss.pdf",
                  "database.ekspor_nonoss", aktif)


@login_required
def nonoss_detail(request, pk):
    _wajib_lihat(request)
    izin = get_object_or_404(
        IzinNonOSS.objects.select_related("jenis", "kecamatan", "kelurahan", "dibuat_oleh"), pk=pk
    )
    return render(
        request,
        "basisdata/nonoss_detail.html",
        {
            "i": izin,
            "riwayat": _riwayat(izin),
            "pratinjau": jenis_pratinjau(izin.dokumen) if izin.dokumen else "",
            "bisa_kelola": bisa_kelola_database(request.user),
        },
    )


# Nilai kolom ini tidak ditulis ke log audit (UU PDP); cukup dicatat bahwa ia berubah.
KOLOM_PRIBADI = {"nama_pemohon", "nik", "dokumen"}


def _nilai_tampil(izin):
    """Nilai sebelum diubah, dalam bentuk yang dibaca manusia (nama, bukan ID)."""
    return {
        "jenis": izin.jenis.nama,
        "nomor_izin": izin.nomor_izin,
        "tanggal_permohonan": izin.tanggal_permohonan,
        "tanggal_terbit": izin.tanggal_terbit,
        "status": izin.get_status_display(),
        "alamat_objek": izin.alamat_objek,
        "kecamatan": izin.kecamatan.nama,
        "kelurahan_nama": izin.kelurahan.nama if izin.kelurahan else "",
        "instansi_teknis": izin.instansi_teknis,
    }


def _ringkas_perubahan(form, sebelum, sesudah):
    bagian = []
    for nama in form.changed_data:
        label = form.fields[nama].label
        if nama in KOLOM_PRIBADI:
            bagian.append(f"{label} diubah")
        elif str(sebelum.get(nama) or "").lower() != str(sesudah.get(nama) or "").lower():
            bagian.append(f"{label}: {sebelum.get(nama) or '-'} → {sesudah.get(nama) or '-'}")
    return "; ".join(bagian)


@login_required
def nonoss_form(request, pk=None):
    _wajib_kelola(request)
    izin = get_object_or_404(IzinNonOSS, pk=pk) if pk else None
    sebelum = _nilai_tampil(izin) if izin else {}  # sebelum form mengubah instance
    form = IzinNonOSSForm(request.POST or None, request.FILES or None, instance=izin)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            baru = form.save(commit=False)
            if izin is None:
                baru.dibuat_oleh = request.user
            baru.save()
            if izin is None:
                catat(request.user, "database.nonoss_tambah", baru)
            else:
                perubahan = _ringkas_perubahan(form, sebelum, _nilai_tampil(baru))
                if perubahan:
                    catat(request.user, "database.nonoss_ubah", baru, perubahan)
        messages.success(request, "Data izin disimpan.")
        return redirect("basisdata:nonoss_detail", baru.pk)
    return render(request, "basisdata/nonoss_form.html", {"form": form, "izin": izin})


@login_required
def nonoss_dokumen(request, pk):
    _wajib_lihat(request)
    izin = get_object_or_404(IzinNonOSS, pk=pk)
    return kirim_berkas(
        request.user,
        izin.dokumen,
        nama_aman(f"izin-nonoss-{izin.pk}", izin.dokumen),
        objek=izin,
        tampil=request.GET.get("tampil") == "1",
    )


# ---------------------------------------------------------------- statistik publik


def statistik(request):
    """Modul 4: terbuka untuk publik, hanya angka agregat."""
    data = kueri.statistik(kueri._int(request.GET.get("tahun")))
    return render(request, "basisdata/statistik.html", {"d": data})


def statistik_ekspor(request, format):
    data = kueri.statistik(kueri._int(request.GET.get("tahun")))
    akhiran = f"-{data['tahun']}" if data["tahun"] else ""
    if format == "xlsx":
        isi, jenis = ekspor.statistik_excel(data), ekspor.XLSX
    else:
        isi, jenis = ekspor.statistik_pdf(data), "application/pdf"
    respons = HttpResponse(isi, content_type=jenis)
    respons["Content-Disposition"] = f'attachment; filename="statistik-perizinan{akhiran}.{format}"'
    return respons
