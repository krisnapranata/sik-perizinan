from django import forms

from akun.models import Instansi
from core.validators import validasi_berkas
from perizinan.models import HasilPenilaian, JenisIzin, Permohonan


class PermohonanBaruForm(forms.Form):
    jenis_izin = forms.ModelChoiceField(JenisIzin.objects.filter(aktif=True), label="Jenis izin")


class FormulirForm(forms.ModelForm):
    """Data formulir permohonan: lokasi objek dan rencana kegiatan (PRD IZ-03)."""

    class Meta:
        model = Permohonan
        fields = [
            "lokasi_alamat",
            "kecamatan",
            "kelurahan_nama",
            "luas_tanah",
            "koordinat",
            "rencana_kegiatan",
        ]
        widgets = {
            "lokasi_alamat": forms.Textarea(attrs={"rows": 2}),
            "rencana_kegiatan": forms.Textarea(attrs={"rows": 3}),
            "luas_tanah": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nama in ("lokasi_alamat", "kecamatan", "rencana_kegiatan"):
            self.fields[nama].required = True


class UnggahDokumenForm(forms.Form):
    berkas = forms.FileField(label="Berkas (PDF/JPG, maks. 5 MB)", validators=[validasi_berkas])


class TeruskanForm(forms.Form):
    instansi = forms.ModelChoiceField(
        Instansi.objects.filter(aktif=True), label="Instansi teknis tujuan", required=False
    )


class PenilaianForm(forms.Form):
    hasil = forms.ChoiceField(choices=HasilPenilaian.choices, label="Hasil penilaian",
                              widget=forms.RadioSelect)
    rekomendasi = forms.CharField(label="Rekomendasi / alasan", widget=forms.Textarea(attrs={"rows": 3}))
    berkas = forms.FileField(
        label="Berkas rekomendasi (opsional, PDF/JPG)", required=False, validators=[validasi_berkas]
    )


class TerbitForm(forms.Form):
    berkas_ttd = forms.FileField(
        label="Dokumen bertanda tangan (opsional)",
        required=False,
        validators=[validasi_berkas],
        help_text="Kosongkan untuk memakai dokumen ber-QR yang dibuat sistem.",
    )


class GantiDokumenIzinForm(forms.Form):
    berkas = forms.FileField(
        label="Pindaian dokumen izin bertanda tangan (PDF/JPG)", validators=[validasi_berkas]
    )


class CekStatusForm(forms.Form):
    nomor = forms.CharField(label="Nomor registrasi", max_length=24)
