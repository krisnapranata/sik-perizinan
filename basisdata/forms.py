from django import forms

from basisdata.models import IzinNonOSS, JenisIzinNonOSS, Kelurahan, ProyekOSS


class ImporForm(forms.Form):
    berkas = forms.FileField(
        label="File ekspor OSS-RBA",
        help_text="Format .xlsx atau .csv, baris pertama berisi judul kolom seperti ekspor OSS.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx,.xlsm,.csv"}),
    )


class StatusIzinForm(forms.ModelForm):
    class Meta:
        model = ProyekOSS
        fields = ["status_izin"]


class IzinNonOSSForm(forms.ModelForm):
    kelurahan_nama = forms.CharField(label="Kelurahan/desa", max_length=80, required=False)

    class Meta:
        model = IzinNonOSS
        fields = [
            "jenis",
            "nomor_izin",
            "nama_pemohon",
            "nik",
            "tanggal_permohonan",
            "tanggal_terbit",
            "status",
            "alamat_objek",
            "kecamatan",
            "kelurahan_nama",
            "instansi_teknis",
            "dokumen",
        ]
        widgets = {
            "tanggal_permohonan": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "tanggal_terbit": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "alamat_objek": forms.Textarea(attrs={"rows": 2}),
            "nik": forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        jenis = JenisIzinNonOSS.objects.filter(aktif=True)
        if self.instance.pk:
            jenis = jenis | JenisIzinNonOSS.objects.filter(pk=self.instance.jenis_id)
            if self.instance.kelurahan:
                self.initial["kelurahan_nama"] = self.instance.kelurahan.nama
        self.fields["jenis"].queryset = jenis.distinct()

    def clean_nik(self):
        nik = self.cleaned_data["nik"].strip()
        if nik and not (nik.isdigit() and len(nik) == 16):
            raise forms.ValidationError("NIK harus 16 digit angka.")
        return nik

    def clean_nomor_izin(self):
        return self.cleaned_data["nomor_izin"].strip() if self.cleaned_data["nomor_izin"] else None

    def clean(self):
        data = super().clean()
        permohonan, terbit = data.get("tanggal_permohonan"), data.get("tanggal_terbit")
        if permohonan and terbit and terbit < permohonan:
            self.add_error("tanggal_terbit", "Tanggal terbit tidak boleh sebelum tanggal permohonan.")
        if data.get("status") == "terbit":
            if not terbit:
                self.add_error("tanggal_terbit", "Wajib diisi untuk izin yang terbit.")
            if not data.get("nomor_izin"):
                self.add_error("nomor_izin", "Wajib diisi untuk izin yang terbit.")
        return data

    def save(self, commit=True):
        izin = super().save(commit=False)
        nama = " ".join(self.cleaned_data.get("kelurahan_nama", "").split())
        if nama:
            izin.kelurahan = Kelurahan.objects.filter(
                kecamatan=izin.kecamatan, nama__iexact=nama
            ).first() or Kelurahan.objects.create(kecamatan=izin.kecamatan, nama=nama.title())
        else:
            izin.kelurahan = None
        if commit:
            izin.save()
        return izin
