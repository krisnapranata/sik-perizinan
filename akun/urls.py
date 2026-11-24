from django.contrib.auth import views as auth_views
from django.urls import path

from akun import views
from akun.batas_masuk import FormMasuk

app_name = "akun"

urlpatterns = [
    path("daftar/", views.daftar, name="daftar"),
    path("verifikasi/", views.verifikasi, name="verifikasi"),
    path("verifikasi/kirim-ulang/", views.kirim_ulang_otp, name="kirim_ulang_otp"),
    path("masuk/", auth_views.LoginView.as_view(template_name="akun/masuk.html", authentication_form=FormMasuk), name="masuk"),
    path("keluar/", auth_views.LogoutView.as_view(), name="keluar"),
    path("lupa-password/", views.ResetPassword.as_view(), name="reset"),
    path("reset/<uidb64>/<token>/", views.ResetKonfirmasi.as_view(), name="reset_konfirmasi"),
    path("profil/", views.profil, name="profil"),
    path("ganti-password/", views.ganti_password, name="ganti_password"),
    path("loket/", views.loket, name="loket"),
    path("loket/daftar/", views.loket_daftar, name="loket_daftar"),
    path("loket/pemohon/<int:pemohon_id>/", views.loket_pemohon, name="loket_pemohon"),
]
