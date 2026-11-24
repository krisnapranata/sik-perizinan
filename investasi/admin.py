from django.contrib import admin

from core.admin import AdminSistemMixin
from investasi.forms import PeluangInvestasiAdminForm
from investasi.models import PeluangInvestasi


@admin.register(PeluangInvestasi)
class PeluangInvestasiAdmin(AdminSistemMixin, admin.ModelAdmin):
    """IN-07: Admin mengelola konten portofolio tanpa bantuan pengembang.
    Tidak bisa dihapus (bawaan AdminSistemMixin); matikan 'tampil' untuk menurunkan dari portal."""

    form = PeluangInvestasiAdminForm
    list_display = ["nama", "tingkat", "sektor", "kecamatan", "ada_titik", "tampil", "diperbarui"]
    list_filter = ["tingkat", "sektor", "kecamatan", "tampil"]
    list_editable = ["tampil"]
    search_fields = ["nama", "lokasi", "deskripsi"]
    list_select_related = ["kecamatan"]
    fieldsets = [
        (None, {"fields": ["nama", "tingkat", "sektor", "deskripsi", "tampil"]}),
        ("Lokasi", {"fields": ["kecamatan", "lokasi", "koordinat"]}),
        ("Kajian (wajib untuk peluang dan proyek siap tawar)",
         {"fields": ["estimasi_investasi", "potensi_pasar", "luas_lahan_ha", "kontak"]}),
    ]

    @admin.display(boolean=True, description="titik peta")
    def ada_titik(self, obj):
        return obj.ada_koordinat
