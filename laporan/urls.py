from django.urls import path

from laporan import views

app_name = "laporan"

urlpatterns = [
    path("", views.dasbor, name="dasbor"),
    path("ekspor.xlsx", views.ekspor_excel, name="ekspor_excel"),
    path("ekspor.pdf", views.ekspor_pdf, name="ekspor_pdf"),
]
