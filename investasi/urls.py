from django.urls import path

from investasi import views

app_name = "investasi"

urlpatterns = [
    path("", views.daftar, name="daftar"),
    path("<int:pk>/", views.detail, name="detail"),
]
