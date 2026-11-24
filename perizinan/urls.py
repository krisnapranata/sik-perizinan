from django.urls import path

from perizinan import views

app_name = "perizinan"

urlpatterns = [
    path("dasbor/", views.dasbor, name="dasbor"),
    path("layanan/", views.katalog, name="katalog"),
    path("layanan/<int:pk>/", views.katalog_detail, name="katalog_detail"),
    path("cek-status/", views.cek_status, name="cek_status"),
    path("verifikasi/<str:kode>/", views.verifikasi_izin, name="verifikasi_izin"),
    path("permohonan/", views.daftar, name="daftar"),
    path("permohonan/baru/", views.baru, name="baru"),
    path("permohonan/baru/<int:pemohon_id>/", views.baru, name="baru_loket"),
    path("permohonan/<str:nomor>/", views.detail, name="detail"),
    path("permohonan/<str:nomor>/formulir/", views.formulir, name="formulir"),
    path("permohonan/<str:nomor>/syarat/<int:syarat_id>/", views.unggah, name="unggah"),
    path("permohonan/<str:nomor>/kirim/", views.kirim, name="kirim"),
    path("permohonan/<str:nomor>/aksi/", views.aksi, name="aksi"),
    path("permohonan/<str:nomor>/nilai/", views.nilai, name="nilai"),
    path("permohonan/<str:nomor>/terbit/", views.terbit, name="terbit"),
    path("permohonan/<str:nomor>/izin-ttd/", views.ganti_dokumen_izin, name="ganti_dokumen_izin"),
    path("permohonan/<str:nomor>/dokumen/<int:dokumen_id>/cek/", views.cek, name="cek"),
    path("antrean/", views.antrean, name="antrean"),
    path("berkas/<str:nomor>/dokumen/<int:dokumen_id>/", views.unduh_dokumen, name="unduh_dokumen"),
    path("berkas/<str:nomor>/izin/", views.unduh_izin, name="unduh_izin"),
    path(
        "berkas/<str:nomor>/rekomendasi/<int:penilaian_id>/",
        views.unduh_rekomendasi,
        name="unduh_rekomendasi",
    ),
    path("berkas/nib/<int:pemohon_id>/", views.unduh_nib, name="unduh_nib"),
]
