from django import forms
from django.contrib.auth.forms import BaseUserCreationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password

from akun.models import Pemohon, TipePemohon, User


class ProfilForm(forms.ModelForm):
    class Meta:
        model = Pemohon
        fields = ["tipe", "nama", "nik", "npwp", "hp", "alamat", "nib", "bukti_nib"]
        widgets = {"alamat": forms.Textarea(attrs={"rows": 3}), "bukti_nib": forms.FileInput}

    def clean(self):
        data = super().clean()
        if data.get("tipe") == TipePemohon.PERORANGAN and not data.get("nik"):
            self.add_error("nik", "NIK wajib untuk pemohon perorangan.")
        if data.get("tipe") == TipePemohon.BADAN_HUKUM and not data.get("npwp"):
            self.add_error("npwp", "NPWP wajib untuk badan hukum.")
        return data


class _DataDiriForm(ProfilForm):
    email = forms.EmailField(label="Email")
    field_order = ["email", "tipe", "nama", "nik", "npwp", "hp", "alamat"]

    class Meta(ProfilForm.Meta):
        fields = ["tipe", "nama", "nik", "npwp", "hp", "alamat"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email ini sudah terdaftar.")
        return email

    def data_pemohon(self):
        return {k: self.cleaned_data[k] for k in self.Meta.fields}


class DaftarForm(_DataDiriForm):
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    ulangi_password = forms.CharField(label="Ulangi password", widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        password = data.get("password")
        if password and password != data.get("ulangi_password"):
            self.add_error("ulangi_password", "Password tidak sama.")
        elif password:
            try:
                validate_password(password)
            except forms.ValidationError as galat:
                self.add_error("password", galat)
        return data


class DaftarLoketForm(_DataDiriForm):
    pass


class OTPForm(forms.Form):
    kode = forms.CharField(
        label="Kode verifikasi",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={"inputmode": "numeric", "autocomplete": "one-time-code", "pattern": "[0-9]{6}"}
        ),
    )


class CariPemohonForm(forms.Form):
    q = forms.CharField(label="Email, NIK, atau NIB", max_length=254)


class TambahPenggunaForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ["email", "nama", "nip", "unit_kerja", "peran", "instansi"]


class ImporPenggunaForm(forms.Form):
    berkas = forms.FileField(
        label="Berkas CSV atau Excel",
        help_text="Format .csv atau .xlsx, maksimal 5 MB. Baris pertama berisi nama kolom.",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,.xlsx,.xlsm"}),
    )
    password_default = forms.CharField(
        label="Password default",
        help_text="Dipakai untuk baris yang kolom password-nya kosong.",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    def clean_berkas(self):
        berkas = self.cleaned_data["berkas"]
        if berkas.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Berkas lebih dari 5 MB.")
        return berkas

    def clean_password_default(self):
        password = self.cleaned_data["password_default"]
        validate_password(password)
        return password


class GantiPasswordForm(PasswordChangeForm):
    def clean_new_password1(self):
        password = self.cleaned_data["new_password1"]
        if self.user.check_password(password):
            raise forms.ValidationError("Password baru harus berbeda dari password lama.")
        return password
