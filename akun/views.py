from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from akun import otp, services
from akun.forms import (
    CariPemohonForm,
    DaftarForm,
    DaftarLoketForm,
    GantiPasswordForm,
    OTPForm,
    ProfilForm,
)
from akun.models import Pemohon, Peran, User
from akun.permissions import bisa_kelola_pemohon
from core.audit import catat


def daftar(request):
    form = DaftarForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        pemohon = services.daftar_mandiri(
            form.cleaned_data["email"], form.cleaned_data["password"], form.data_pemohon()
        )
        request.session["otp_user"] = pemohon.user_id
        return redirect("akun:verifikasi")
    return render(request, "akun/daftar.html", {"form": form})


def _akun_menunggu_otp(request):
    """Akun yang baru mendaftar di sesi ini. last_login kosong: akun yang pernah aktif lalu
    dinonaktifkan admin tidak bisa dihidupkan lagi lewat OTP."""
    pk = request.session.get("otp_user")
    pengguna = User.objects.filter(pk=pk, is_active=False, last_login=None).first() if pk else None
    if pengguna is None:
        request.session.pop("otp_user", None)
    return pengguna


def verifikasi(request):
    pengguna = _akun_menunggu_otp(request)
    if pengguna is None:
        messages.info(request, "Sesi verifikasi berakhir. Masuk atau daftar ulang.")
        return redirect("akun:masuk")
    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            otp.periksa(pengguna, form.cleaned_data["kode"])
        except otp.OTPGagal as galat:
            form.add_error("kode", str(galat))
        else:
            services.aktifkan(pengguna)
            request.session.pop("otp_user", None)
            messages.success(request, "Akun aktif. Silakan masuk.")
            return redirect("akun:masuk")
    return render(request, "akun/verifikasi.html", {"form": form, "email": pengguna.email})


@require_POST
def kirim_ulang_otp(request):
    pengguna = _akun_menunggu_otp(request)
    if pengguna is None:
        return redirect("akun:masuk")
    try:
        otp.kirim(pengguna)
        messages.success(request, "Kode baru sudah dikirim.")
    except otp.OTPGagal as galat:
        messages.error(request, str(galat))
    return redirect("akun:verifikasi")


def _simpan_profil(request, pemohon, tujuan):
    form = ProfilForm(request.POST or None, request.FILES or None, instance=pemohon)
    if request.method == "POST" and form.is_valid():
        form.save()
        catat(request.user, "pemohon.ubah", pemohon, f"Kolom: {', '.join(form.changed_data)}")
        messages.success(request, "Profil disimpan.")
        return redirect(*tujuan)
    return render(request, "akun/profil.html", {"form": form, "pemohon": pemohon})


@login_required
def profil(request):
    pemohon = Pemohon.objects.filter(user=request.user).first()
    if pemohon is None:
        # Akun pemohon yang dibuat lewat panel admin belum punya data pemohon.
        if request.user.peran != Peran.PEMOHON:
            raise PermissionDenied
        pemohon = Pemohon(user=request.user, nama=request.user.nama)
    return _simpan_profil(request, pemohon, ["akun:profil"])


def _hanya_loket(request):
    """Layanan berbantuan (front office) dijalankan Petugas DPMPTSP."""
    if request.user.peran != Peran.PETUGAS:
        raise PermissionDenied


@login_required
def loket(request):
    """Pencarian harus cocok persis: petugas tidak bisa menelusuri seluruh data pemohon."""
    _hanya_loket(request)
    form = CariPemohonForm(request.GET or None)
    hasil = None
    if form.is_valid():
        q = form.cleaned_data["q"].strip()
        hasil = Pemohon.objects.filter(Q(user__email=q) | Q(nik=q) | Q(nib=q)).select_related(
            "user"
        )[:10]
    return render(request, "akun/loket.html", {"form": form, "hasil": hasil})


@login_required
def loket_daftar(request):
    _hanya_loket(request)
    form = DaftarLoketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        pemohon = services.daftar_oleh_loket(
            request.user, form.cleaned_data["email"], form.data_pemohon()
        )
        messages.success(request, "Akun pemohon dibuat. Silakan buat permohonan.")
        return redirect("akun:loket_pemohon", pemohon.pk)
    return render(request, "akun/daftar.html", {"form": form, "loket": True})


@login_required
def loket_pemohon(request, pemohon_id):
    _hanya_loket(request)
    pemohon = get_object_or_404(Pemohon, pk=pemohon_id)
    if not bisa_kelola_pemohon(request.user, pemohon):
        raise PermissionDenied
    return _simpan_profil(request, pemohon, ["akun:loket_pemohon", pemohon.pk])


class ResetPassword(auth_views.PasswordResetView):
    template_name = "akun/form_sederhana.html"
    email_template_name = "akun/email_reset.txt"
    subject_template_name = "akun/email_reset_subjek.txt"
    success_url = reverse_lazy("akun:masuk")
    extra_context = {"judul": "Lupa password", "tombol": "Kirim tautan"}

    def form_valid(self, form):
        messages.info(self.request, "Bila email terdaftar, tautan reset telah dikirim.")
        return super().form_valid(form)


class ResetKonfirmasi(auth_views.PasswordResetConfirmView):
    template_name = "akun/form_sederhana.html"
    success_url = reverse_lazy("akun:masuk")
    extra_context = {"judul": "Buat password baru", "tombol": "Simpan"}

    def form_valid(self, form):
        form.user.wajib_ganti_password = False
        return super().form_valid(form)


@login_required
def ganti_password(request):
    wajib = request.user.wajib_ganti_password
    form = GantiPasswordForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        pengguna = form.save(commit=False)
        pengguna.wajib_ganti_password = False
        pengguna.save()
        update_session_auth_hash(request, pengguna)
        catat(pengguna, "akun.ganti_password", pengguna)
        messages.success(request, "Password berhasil diganti.")
        return redirect("beranda")
    if wajib and request.method == "GET":
        messages.warning(
            request, "Demi keamanan, ganti password awal Anda sebelum memakai aplikasi."
        )
    return render(
        request,
        "akun/form_sederhana.html",
        {"form": form, "judul": "Ganti password", "tombol": "Simpan password baru"},
    )
