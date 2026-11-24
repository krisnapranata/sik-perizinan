import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import forms

from investasi.models import PeluangInvestasi

_POLA_KOORDINAT = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


class PeluangInvestasiAdminForm(forms.ModelForm):
    """Admin cukup menempel koordinat dari Google Maps dalam satu kotak."""

    koordinat = forms.CharField(
        label="Titik koordinat",
        required=False,
        help_text=(
            "Di Google Maps, klik kanan titik lokasi lalu klik angka koordinat paling atas untuk "
            "menyalin, kemudian tempel di sini. Contoh: -8.6512, 116.5321"
        ),
    )

    class Meta:
        model = PeluangInvestasi
        exclude = ["lintang", "bujur"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.ada_koordinat:
            self.initial["koordinat"] = f"{self.instance.lintang}, {self.instance.bujur}"

    def clean_koordinat(self):
        teks = self.cleaned_data["koordinat"].strip()
        if not teks:
            return None
        cocok = _POLA_KOORDINAT.match(teks)
        if not cocok:
            raise forms.ValidationError("Tulis sebagai lintang, bujur. Contoh: -8.6512, 116.5321")
        try:
            lintang, bujur = (Decimal(x).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP) for x in cocok.groups())
        except InvalidOperation:
            raise forms.ValidationError("Angka koordinat tidak terbaca.") from None
        if not (-11 <= lintang <= 6 and 95 <= bujur <= 141):
            raise forms.ValidationError(
                "Koordinat di luar wilayah Indonesia. Pastikan urutannya lintang dulu, lalu bujur."
            )
        return lintang, bujur

    def _post_clean(self):
        # Isi lintang/bujur sebelum validasi model berjalan.
        if "koordinat" not in self.errors:
            pasangan = self.cleaned_data.get("koordinat")
            self.instance.lintang, self.instance.bujur = pasangan or (None, None)
        super()._post_clean()
