from django.contrib import admin

from basisdata.models import KBLI, ImporOSS, JenisIzinNonOSS, Kecamatan, Kelurahan
from core.admin import AdminSistemMixin, admin_sistem


@admin.register(Kecamatan)
class KecamatanAdmin(AdminSistemMixin, admin.ModelAdmin):
    search_fields = ["nama"]


@admin.register(Kelurahan)
class KelurahanAdmin(AdminSistemMixin, admin.ModelAdmin):
    list_display = ["nama", "kecamatan"]
    list_filter = ["kecamatan"]
    search_fields = ["nama"]


@admin.register(KBLI)
class KBLIAdmin(AdminSistemMixin, admin.ModelAdmin):
    """Sektor KAK diisi otomatis saat impor; ubah di sini bila pemetaannya kurang tepat."""

    list_display = ["kode", "judul", "kl_pembina", "sektor"]
    list_editable = ["sektor"]
    list_filter = ["sektor", "kl_pembina"]
    search_fields = ["kode", "judul"]


@admin.register(JenisIzinNonOSS)
class JenisIzinNonOSSAdmin(AdminSistemMixin, admin.ModelAdmin):
    list_display = ["nama", "aktif"]


@admin.register(ImporOSS)
class ImporOSSAdmin(admin.ModelAdmin):
    list_display = ["waktu", "pengguna", "nama_berkas", "jumlah_baris", "baru", "diperbarui", "gagal"]
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
