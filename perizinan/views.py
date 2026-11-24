from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from akun.models import Pemohon, Peran
from akun.permissions import bisa_kelola_pemohon, bisa_unduh_bukti_nib
from core.berkas import kirim_berkas, nama_aman
from perizinan import dasbor as dasbor_data
from perizinan import permissions as izin
from perizinan import services
from perizinan.forms import (
    CekStatusForm,
    FormulirForm,
    GantiDokumenIzinForm,
    PenilaianForm,
    PermohonanBaruForm,
    TerbitForm,
    TeruskanForm,
    UnggahDokumenForm,
)
from perizinan.models import (
    Aksi,
    IzinTerbit,
    JenisIzin,
    PenilaianTeknis,
    Permohonan,
    StatusCek,
    StatusPermohonan,
)

S = StatusPermohonan

HASIL_AKSI = {
    Aksi.KIRIM: ("sah", "Diajukan"),
    Aksi.TERUSKAN: ("sah", "Lengkap, diteruskan ke instansi teknis"),
    Aksi.SETUJUI: ("sah", "Lengkap, disetujui"),
    Aksi.MINTA_PERBAIKAN: ("coret", "Perlu perbaikan"),
    Aksi.TOLAK: ("coret", "Ditolak"),
    Aksi.MEMENUHI: ("sah", "Memenuhi"),
    Aksi.TIDAK_MEMENUHI: ("coret", "Tidak memenuhi"),
    Aksi.TERBIT: ("sah", "Izin terbit"),
}


def tahapan(permohonan, riwayat):
    """Langkah alur PRD 6.4 untuk putaran pengajuan terakhir."""
    kiriman = [i for i, r in enumerate(riwayat) if r.aksi == Aksi.KIRIM]
    putaran = riwayat[kiriman[-1]:] if kiriman else []

    def keputusan(*aksi):
        cocok = [r for r in putaran if r.aksi in aksi]
        return cocok[-1] if cocok else None

    def langkah(nama, entri, aktif, menunggu="Sedang diproses"):
        if entri is not None:
            kondisi, hasil = HASIL_AKSI[entri.aksi]
            return {"tahap": nama, "kondisi": kondisi, "hasil": hasil,
                    "petugas": entri.verifikator.nama, "waktu": entri.waktu}
        return {"tahap": nama, "kondisi": "aktif" if aktif else "", "petugas": "", "waktu": None,
                "hasil": menunggu if aktif else ""}

    if not putaran:
        return []
    baris = [
        langkah("Diajukan", putaran[0], False),
        langkah(
            "Verifikasi administrasi",
            keputusan(Aksi.TERUSKAN, Aksi.SETUJUI, Aksi.MINTA_PERBAIKAN, Aksi.TOLAK),
            permohonan.status == S.DIAJUKAN,
        ),
    ]
    if permohonan.jenis_izin.perlu_kajian_teknis or keputusan(Aksi.TERUSKAN):
        baris.append(
            langkah(
                "Penilaian teknis",
                keputusan(Aksi.MEMENUHI, Aksi.TIDAK_MEMENUHI),
                permohonan.status == S.PENILAIAN_TEKNIS,
                menunggu=f"Di {permohonan.instansi_penilai}" if permohonan.instansi_penilai else "",
            )
        )
    baris.append(
        langkah("Penerbitan izin", keputusan(Aksi.TERBIT), permohonan.status == S.DISETUJUI,
                menunggu="Disetujui, izin sedang diterbitkan")
    )
    return baris


def _ambil(request, nomor):
    """404, bukan 403: keberadaan nomor tidak dibocorkan ke pengguna yang tidak berhak."""
    return get_object_or_404(
        izin.permohonan_terlihat(request.user).select_related(
            "pemohon__user", "izin_terbit", "instansi_penilai"
        ),
        nomor_registrasi=nomor,
    )


def beranda(request):
    pengguna = request.user
    if pengguna.is_authenticated:
        if pengguna.pemeriksa or pengguna.peran == Peran.PEMOHON:
            return redirect("perizinan:dasbor")
        if izin.bisa_lihat_laporan(pengguna):
            return redirect("basisdata:statistik")
    from basisdata.kueri import rekap_oss
    from basisdata.models import ProyekOSS

    return render(
        request,
        "beranda.html",
        {"form": CekStatusForm(), "ringkasan": rekap_oss(ProyekOSS.objects.all())},
    )


@login_required
def dasbor(request):
    pengguna = request.user
    if not (pengguna.pemeriksa or pengguna.peran == Peran.PEMOHON):
        raise PermissionDenied
    return render(request, "perizinan/dasbor.html", {"d": dasbor_data.ringkasan(pengguna)})


def katalog(request):
    """IZ-02: jenis izin, persyaratan, dan alurnya; bisa dibaca sebelum mendaftar."""
    jenis = JenisIzin.objects.filter(aktif=True).prefetch_related("syarat")
    return render(request, "perizinan/katalog.html", {"daftar_jenis": jenis})


def katalog_detail(request, pk):
    jenis = get_object_or_404(JenisIzin.objects.select_related("instansi"), pk=pk, aktif=True)
    return render(
        request,
        "perizinan/katalog_detail.html",
        {"j": jenis, "syarat": jenis.syarat.filter(aktif=True)},
    )


def cek_status(request):
    """Hanya status, jenis izin, tahapan, dan tanggal. Tanpa data pribadi."""
    form = CekStatusForm(request.GET or None)
    hasil, dicari, langkah = None, False, []
    if form.is_valid():
        dicari = True
        nomor = form.cleaned_data["nomor"].strip().upper()
        hasil = (
            Permohonan.objects.filter(nomor_registrasi=nomor)
            .exclude(status=S.DRAF)
            .select_related("jenis_izin", "instansi_penilai")
            .first()
        )
        if hasil:
            langkah = tahapan(hasil, list(hasil.riwayat.select_related("verifikator")))
            for b in langkah:
                b["petugas"] = ""  # nama petugas tidak dibuka ke publik
    return render(
        request,
        "perizinan/cek_status.html",
        {"form": form, "hasil": hasil, "dicari": dicari, "tahapan": langkah},
    )


def verifikasi_izin(request, kode):
    """IZ-09: tujuan kode QR di dokumen izin. Nama pemohon disamarkan (UU PDP)."""
    izin_terbit = (
        IzinTerbit.objects.select_related("permohonan__jenis_izin", "permohonan__pemohon",
                                          "permohonan__kecamatan")
        .filter(kode_verifikasi=kode)
        .first()
    )
    nama = ""
    if izin_terbit:
        nama = " ".join(
            k[0] + "*" * (len(k) - 2) + k[-1] if len(k) > 2 else k
            for k in izin_terbit.permohonan.pemohon.nama.split()
        )
    return render(
        request, "perizinan/verifikasi_izin.html", {"izin": izin_terbit, "nama_samar": nama}
    )


@login_required
def daftar(request):
    permohonan = izin.permohonan_terlihat(request.user)
    halaman = Paginator(permohonan, 25).get_page(request.GET.get("halaman"))
    return render(request, "perizinan/daftar.html", {"halaman": halaman})


def _pemohon_dari(request, pemohon_id):
    """None berarti akun pemohon belum melengkapi data dirinya."""
    if pemohon_id is None:
        pemohon = Pemohon.objects.filter(user=request.user).first()
        if pemohon is None and request.user.peran != Peran.PEMOHON:
            raise PermissionDenied
        return pemohon
    pemohon = get_object_or_404(Pemohon, pk=pemohon_id)
    if not bisa_kelola_pemohon(request.user, pemohon):
        raise PermissionDenied
    return pemohon


@login_required
def baru(request, pemohon_id=None):
    pemohon = _pemohon_dari(request, pemohon_id)
    if pemohon is None:
        messages.info(request, "Lengkapi data diri Anda sebelum mengajukan izin.")
        return redirect("akun:profil")
    awal = {"jenis_izin": request.GET.get("jenis")} if request.GET.get("jenis") else None
    form = PermohonanBaruForm(request.POST or None, initial=awal)
    if request.method == "POST" and form.is_valid():
        try:
            permohonan = services.buat_permohonan(
                pemohon, form.cleaned_data["jenis_izin"], request.user
            )
        except services.TransisiTidakValid as galat:
            messages.error(request, str(galat))
        else:
            messages.info(request, "Isi formulir lokasi, unggah syarat, lalu kirim permohonan.")
            return redirect("perizinan:detail", permohonan.nomor_registrasi)
    return render(request, "perizinan/baru.html", {"form": form, "pemohon": pemohon})


@login_required
def detail(request, nomor):
    permohonan = _ambil(request, nomor)
    pengguna = request.user
    dokumen = {d.syarat_id: d for d in permohonan.dokumen.select_related("syarat")}
    baris_syarat = [(s, dokumen.get(s.pk)) for s in permohonan.syarat_berlaku()]
    bisa_perbaiki = izin.bisa_perbaiki(pengguna, permohonan)
    bisa_verifikasi = izin.bisa_verifikasi(pengguna, permohonan)
    riwayat = list(permohonan.riwayat.select_related("verifikator"))
    konteks = {
        "p": permohonan,
        "baris_syarat": baris_syarat,
        "riwayat": riwayat,
        "tahapan": tahapan(permohonan, riwayat),
        "penilaian": list(permohonan.penilaian.select_related("instansi", "penilai")),
        "bisa_perbaiki": bisa_perbaiki,
        "bisa_cek": izin.bisa_cek_dokumen(pengguna, permohonan),
        "bisa_nilai": izin.bisa_nilai(pengguna, permohonan),
        "bisa_ganti_izin": izin.bisa_ganti_dokumen_izin(pengguna, permohonan),
        "kekurangan": services.kekurangan(permohonan) if bisa_perbaiki else [],
        "aksi": services.aksi_tersedia(permohonan) if bisa_verifikasi else [],
        "bisa_terbit": bisa_verifikasi and permohonan.status == S.DISETUJUI,
        "form_formulir": FormulirForm(instance=permohonan) if bisa_perbaiki else None,
        "form_teruskan": TeruskanForm(initial={"instansi": permohonan.jenis_izin.instansi_id}),
        "form_nilai": PenilaianForm(),
        "form_terbit": TerbitForm(),
        "form_ganti_izin": GantiDokumenIzinForm(),
        "izin_terbit": getattr(permohonan, "izin_terbit", None),
        "Aksi": Aksi,
        "StatusCek": StatusCek,
    }
    return render(request, "perizinan/detail.html", konteks)


def _kembali(permohonan):
    return redirect("perizinan:detail", permohonan.nomor_registrasi)


def _pesan_form(request, form):
    for galat in form.errors.values():
        messages.error(request, " ".join(galat))


@login_required
@require_POST
def formulir(request, nomor):
    permohonan = _ambil(request, nomor)
    form = FormulirForm(request.POST, instance=permohonan)
    if form.is_valid():
        try:
            services.simpan_formulir(permohonan, form, request.user)
            messages.success(request, "Formulir disimpan.")
        except services.TransisiTidakValid as galat:
            messages.error(request, str(galat))
    else:
        _pesan_form(request, form)
    return _kembali(permohonan)


@login_required
@require_POST
def unggah(request, nomor, syarat_id):
    permohonan = _ambil(request, nomor)
    syarat = get_object_or_404(permohonan.syarat_berlaku(), pk=syarat_id)
    form = UnggahDokumenForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            services.unggah_dokumen(permohonan, syarat, form.cleaned_data["berkas"], request.user)
            messages.success(request, f"{syarat.nama} berhasil diunggah.")
        except services.TransisiTidakValid as galat:
            messages.error(request, str(galat))
    else:
        _pesan_form(request, form)
    return _kembali(permohonan)


@login_required
@require_POST
def kirim(request, nomor):
    permohonan = _ambil(request, nomor)
    try:
        services.kirim(permohonan, request.user)
        messages.success(request, "Permohonan terkirim dan masuk antrean verifikasi.")
    except services.TransisiTidakValid as galat:
        messages.error(request, str(galat))
    return _kembali(permohonan)


@login_required
def antrean(request):
    if not request.user.pemeriksa:
        raise PermissionDenied
    halaman = Paginator(services.antrean(request.user), 25).get_page(request.GET.get("halaman"))
    return render(request, "perizinan/antrean.html", {"halaman": halaman, "antrean": True})


@login_required
@require_POST
def aksi(request, nomor):
    permohonan = _ambil(request, nomor)
    form = TeruskanForm(request.POST)
    instansi = form.cleaned_data["instansi"] if form.is_valid() else None
    try:
        services.proses(
            permohonan,
            request.POST.get("aksi", ""),
            request.user,
            request.POST.get("catatan", ""),
            instansi=instansi,
        )
        messages.success(request, "Keputusan tersimpan.")
    except services.TransisiTidakValid as galat:
        messages.error(request, str(galat))
    return _kembali(permohonan)


@login_required
@require_POST
def cek(request, nomor, dokumen_id):
    permohonan = _ambil(request, nomor)
    dokumen = get_object_or_404(permohonan.dokumen, pk=dokumen_id)
    try:
        services.cek_dokumen(
            dokumen,
            request.POST.get("status_cek", ""),
            request.user,
            request.POST.get("catatan", ""),
        )
    except services.TransisiTidakValid as galat:
        messages.error(request, str(galat))
    return _kembali(permohonan)


@login_required
@require_POST
def nilai(request, nomor):
    permohonan = _ambil(request, nomor)
    form = PenilaianForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            services.nilai(
                permohonan,
                request.user,
                form.cleaned_data["hasil"],
                form.cleaned_data["rekomendasi"],
                form.cleaned_data["berkas"],
            )
            messages.success(request, "Hasil penilaian tersimpan.")
        except services.TransisiTidakValid as galat:
            messages.error(request, str(galat))
    else:
        _pesan_form(request, form)
    return _kembali(permohonan)


@login_required
@require_POST
def terbit(request, nomor):
    permohonan = _ambil(request, nomor)
    form = TerbitForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            services.terbitkan(permohonan, request.user, form.cleaned_data["berkas_ttd"])
            messages.success(request, "Izin terbit. Nomor izin dibuat otomatis.")
        except services.TransisiTidakValid as galat:
            messages.error(request, str(galat))
    else:
        _pesan_form(request, form)
    return _kembali(permohonan)


@login_required
@require_POST
def ganti_dokumen_izin(request, nomor):
    permohonan = _ambil(request, nomor)
    if not izin.bisa_ganti_dokumen_izin(request.user, permohonan):
        raise PermissionDenied
    form = GantiDokumenIzinForm(request.POST, request.FILES)
    if form.is_valid():
        services.ganti_dokumen_izin(permohonan, form.cleaned_data["berkas"], request.user)
        messages.success(request, "Dokumen bertanda tangan disimpan.")
    else:
        _pesan_form(request, form)
    return _kembali(permohonan)


def _tampil(request):
    """?lihat=1 menampilkan berkas di browser (pratinjau); tanpa itu berkas diunduh."""
    return request.GET.get("lihat") == "1"


@login_required
def unduh_dokumen(request, nomor, dokumen_id):
    permohonan = _ambil(request, nomor)
    dokumen = get_object_or_404(permohonan.dokumen.select_related("syarat"), pk=dokumen_id)
    nama = nama_aman(f"{permohonan.nomor_registrasi}-{dokumen.syarat.nama}", dokumen.berkas)
    return kirim_berkas(request.user, dokumen.berkas, nama, dokumen, tampil=_tampil(request))


@login_required
def unduh_izin(request, nomor):
    permohonan = _ambil(request, nomor)
    izin_terbit = get_object_or_404(IzinTerbit, permohonan=permohonan)
    berkas = izin_terbit.berkas_unduhan
    nama = nama_aman(f"izin-{permohonan.nomor_registrasi}", berkas)
    return kirim_berkas(request.user, berkas, nama, izin_terbit, tampil=_tampil(request))


@login_required
def unduh_rekomendasi(request, nomor, penilaian_id):
    permohonan = _ambil(request, nomor)
    penilaian = get_object_or_404(PenilaianTeknis, pk=penilaian_id, permohonan=permohonan)
    nama = nama_aman(f"rekomendasi-{permohonan.nomor_registrasi}", penilaian.berkas)
    return kirim_berkas(request.user, penilaian.berkas, nama, penilaian, tampil=_tampil(request))


@login_required
def unduh_nib(request, pemohon_id):
    pemohon = get_object_or_404(Pemohon, pk=pemohon_id)
    if not bisa_unduh_bukti_nib(request.user, pemohon):
        raise Http404
    return kirim_berkas(
        request.user,
        pemohon.bukti_nib,
        nama_aman("bukti-nib", pemohon.bukti_nib),
        pemohon,
        tampil=_tampil(request),
    )
