from django.contrib import admin

from core.admin import AdminSistemMixin
from perizinan.models import JenisIzin, SyaratIzin, TemplateEmail


class SyaratInline(admin.TabularInline):
    model = SyaratIzin
    extra = 1
    fields = ["nama", "keterangan", "wajib", "berlaku_untuk", "aktif", "urutan"]

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(JenisIzin)
class JenisIzinAdmin(AdminSistemMixin, admin.ModelAdmin):
    list_display = ["nama", "kode", "perlu_kajian_teknis", "instansi", "sla_hari", "aktif", "urutan"]
    list_filter = ["aktif", "perlu_kajian_teknis"]
    inlines = [SyaratInline]


@admin.register(TemplateEmail)
class TemplateEmailAdmin(AdminSistemMixin, admin.ModelAdmin):
    list_display = ["kode", "subjek"]
