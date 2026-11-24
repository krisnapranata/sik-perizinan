from django.urls import path, re_path

from basisdata import views

app_name = "basisdata"

FORMAT = r"(?P<format>xlsx|pdf)"

urlpatterns = [
    path("database/oss/", views.oss_daftar, name="oss_daftar"),
    re_path(rf"^database/oss/ekspor\.{FORMAT}$", views.oss_ekspor, name="oss_ekspor"),
    path("database/oss/impor/", views.oss_impor, name="oss_impor"),
    path("database/oss/impor/<int:pk>/", views.oss_impor_hasil, name="oss_impor_hasil"),
    path("database/oss/<str:id_proyek>/", views.oss_detail, name="oss_detail"),
    path("database/usaha/<str:nib>/", views.usaha_detail, name="usaha_detail"),
    path("database/nonoss/", views.nonoss_daftar, name="nonoss_daftar"),
    re_path(rf"^database/nonoss/ekspor\.{FORMAT}$", views.nonoss_ekspor, name="nonoss_ekspor"),
    path("database/nonoss/tambah/", views.nonoss_form, name="nonoss_tambah"),
    path("database/nonoss/<int:pk>/", views.nonoss_detail, name="nonoss_detail"),
    path("database/nonoss/<int:pk>/ubah/", views.nonoss_form, name="nonoss_ubah"),
    path("database/nonoss/<int:pk>/dokumen/", views.nonoss_dokumen, name="nonoss_dokumen"),
    path("statistik/", views.statistik, name="statistik"),
    re_path(rf"^statistik/ekspor\.{FORMAT}$", views.statistik_ekspor, name="statistik_ekspor"),
]
