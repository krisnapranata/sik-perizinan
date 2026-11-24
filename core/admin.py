from django.contrib import admin

from akun.models import Peran
from core.audit import catat
from core.models import LogAudit


def admin_sistem(request):
    pengguna = request.user
    return pengguna.is_active and (pengguna.is_superuser or pengguna.peran == Peran.ADMIN)


class AdminSistemMixin:
    """F-19: hanya Admin Sistem yang masuk panel admin; setiap perubahan masuk log audit."""

    def has_module_permission(self, request):
        return admin_sistem(request)

    def has_view_permission(self, request, obj=None):
        return admin_sistem(request)

    def has_add_permission(self, request):
        return admin_sistem(request)

    def has_change_permission(self, request, obj=None):
        return admin_sistem(request)

    def has_delete_permission(self, request, obj=None):
        return False  # nonaktifkan, jangan hapus: data ini dirujuk permohonan

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        aksi = "ubah" if change else "tambah"
        catat(request.user, f"admin.{aksi}", obj, f"Kolom: {', '.join(form.changed_data)}")


@admin.register(LogAudit)
class LogAuditAdmin(admin.ModelAdmin):
    list_display = ["waktu", "pengguna", "aksi", "objek_tipe", "objek_id", "alamat_ip"]
    list_filter = ["aksi"]
    search_fields = ["objek_id", "aksi"]
    date_hierarchy = "waktu"
    list_select_related = ["pengguna"]

    def has_module_permission(self, request):
        return admin_sistem(request)

    def has_view_permission(self, request, obj=None):
        return admin_sistem(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
