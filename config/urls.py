from django.contrib import admin
from django.urls import include, path

from akun.batas_masuk import FormMasukAdmin
from core.views import sehat
from perizinan.views import beranda

admin.site.login_form = FormMasukAdmin

urlpatterns = [
    path("", beranda, name="beranda"),
    path("sehat/", sehat, name="sehat"),
    path("admin/", admin.site.urls),
    path("akun/", include("akun.urls")),
    path("laporan/", include("laporan.urls")),
    path("investasi/", include("investasi.urls")),
    path("", include("basisdata.urls")),
    path("", include("perizinan.urls")),
]
