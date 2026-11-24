from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path

from akun import impor
from akun.forms import ImporPenggunaForm, TambahPenggunaForm
from akun.models import Instansi, User
from core.admin import AdminSistemMixin, admin_sistem

admin.site.unregister(Group)
admin.site.site_header = "Admin PANDU LOTIM"
admin.site.site_title = "Admin PANDU LOTIM"
admin.site.index_title = "Pengelolaan sistem"


@admin.register(User)
class PenggunaAdmin(AdminSistemMixin, UserAdmin):
    """Tanpa kolom is_superuser/grup: Admin Sistem tidak bisa menaikkan hak aksesnya sendiri."""

    add_form = TambahPenggunaForm
    ordering = ["nama"]
    list_display = ["nama", "email", "peran", "instansi", "unit_kerja", "is_active"]
    list_filter = ["peran", "instansi", "is_active", "wajib_ganti_password"]
    search_fields = ["nama", "email", "nip"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Data pegawai", {"fields": ["nama", "nip", "unit_kerja", "peran", "instansi"]}),
        ("Status", {"fields": ["is_active", "wajib_ganti_password", "last_login"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "fields": [
                    "email", "nama", "nip", "unit_kerja", "peran", "instansi", "password1", "password2",
                ]
            },
        )
    ]
    readonly_fields = ["last_login"]
    filter_horizontal = []

    def get_urls(self):
        tambahan = [
            path("impor/", self.admin_site.admin_view(self.impor_view), name="akun_user_impor"),
            path(
                "impor/template.<str:format>",
                self.admin_site.admin_view(self.template_view),
                name="akun_user_impor_template",
            ),
        ]
        return tambahan + super().get_urls()

    def impor_view(self, request):
        if not admin_sistem(request):
            raise PermissionDenied
        form = ImporPenggunaForm(
            request.POST or None,
            request.FILES or None,
            initial={"password_default": settings.IMPOR_PASSWORD_DEFAULT},
        )
        hasil = None
        if request.method == "POST" and form.is_valid():
            try:
                hasil = impor.impor(
                    form.cleaned_data["berkas"], form.cleaned_data["password_default"], request.user
                )
            except impor.BerkasTidakValid as galat:
                form.add_error("berkas", str(galat))
        konteks = {
            **self.admin_site.each_context(request),
            "opts": self.opts,
            "title": "Impor pengguna dari CSV / Excel",
            "form": form,
            "hasil": hasil,
            "kolom": impor.KOLOM_TEMPLATE,
        }
        return TemplateResponse(request, "admin/akun/user/impor.html", konteks)

    def template_view(self, request, format):
        if not admin_sistem(request):
            raise PermissionDenied
        if format == "xlsx":
            isi = impor.template_xlsx()
            jenis = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format == "csv":
            isi, jenis = impor.template_csv(), "text/csv; charset=utf-8"
        else:
            raise PermissionDenied
        respons = HttpResponse(isi, content_type=jenis)
        respons["Content-Disposition"] = f'attachment; filename="template-impor-pengguna.{format}"'
        return respons


@admin.register(Instansi)
class InstansiAdmin(AdminSistemMixin, admin.ModelAdmin):
    list_display = ["nama", "singkatan", "aktif"]
    search_fields = ["nama", "singkatan"]
