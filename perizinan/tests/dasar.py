"""Data uji rekaan. Jangan pernah memakai data pemohon sungguhan."""

import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from akun.models import Instansi, Pemohon, Peran, User
from basisdata.models import Kecamatan
from perizinan import services
from perizinan.forms import FormulirForm
from perizinan.models import Aksi, HasilPenilaian, JenisIzin, StatusCek, SyaratIzin

PDF = b"%PDF-1.4 uji"
SANDI = "SandiUji-9x!"


def berkas(nama="uji.pdf", isi=PDF):
    return SimpleUploadedFile(nama, isi, content_type="application/pdf")


def buat_pemohon(email, tipe="perorangan"):
    user = User.objects.create_user(email=email, password=SANDI, nama=email)
    return Pemohon.objects.create(
        user=user,
        tipe=tipe,
        nama=f"Pemohon {email}",
        nik="1234567890123456",
        hp="081234567890",
        alamat="Alamat rekaan",
    )


FORMULIR = {
    "lokasi_alamat": "Dusun Rekaan",
    "kelurahan_nama": "Desa Uji",
    "luas_tanah": "250.5",
    "koordinat": "-8.65, 116.53",
    "rencana_kegiatan": "Rumah tinggal",
}


class DasarUji(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media = tempfile.mkdtemp()
        cls._override = override_settings(MEDIA_ROOT=cls._media)
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._media, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        def akun(email, peran, **kolom):
            return User.objects.create_user(
                email=email, password=SANDI, nama=email.split("@")[0], peran=peran, **kolom
            )

        cls.pupr = Instansi.objects.get(singkatan="PUPR")
        cls.bappeda = Instansi.objects.get(singkatan="Bappeda")
        cls.petugas = akun("petugas@uji.test", Peran.PETUGAS)
        cls.petugas_lain = akun("petugas2@uji.test", Peran.PETUGAS)
        cls.penilai = akun("pupr@uji.test", Peran.INSTANSI, instansi=cls.pupr)
        cls.penilai_lain = akun("bappeda@uji.test", Peran.INSTANSI, instansi=cls.bappeda)
        cls.pimpinan = akun("pimpinan@uji.test", Peran.PIMPINAN)
        cls.admin_sistem = akun("admin@uji.test", Peran.ADMIN)
        cls.pemohon = buat_pemohon("a@uji.test")
        cls.pemohon_lain = buat_pemohon("b@uji.test")
        cls.selong = Kecamatan.objects.get(nama="Selong")
        cls.kkpr = JenisIzin.objects.get(kode="KKPR-NB")  # perlu penilaian PUPR
        cls.sederhana = JenisIzin.objects.create(nama="Izin Sederhana Uji", kode="UJI", sla_hari=5)
        SyaratIzin.objects.create(jenis_izin=cls.sederhana, nama="KTP pemohon")

    def draf(self, pemohon=None, jenis=None):
        pemohon = pemohon or self.pemohon
        p = services.buat_permohonan(pemohon, jenis or self.kkpr, pemohon.user)
        form = FormulirForm({**FORMULIR, "kecamatan": self.selong.pk}, instance=p)
        assert form.is_valid(), form.errors
        services.simpan_formulir(p, form, pemohon.user)
        for syarat in p.syarat_berlaku():
            services.unggah_dokumen(p, syarat, berkas(), pemohon.user)
        p.refresh_from_db()
        return p

    def terkirim(self, **kw):
        p = self.draf(**kw)
        return services.kirim(p, p.pemohon.user)

    def setujui_dokumen(self, p):
        for d in p.dokumen.all():
            services.cek_dokumen(d, StatusCek.SESUAI, self.petugas)

    def dinilai(self, **kw):
        p = self.terkirim(**kw)
        self.setujui_dokumen(p)
        services.proses(p, Aksi.TERUSKAN, self.petugas)
        p.refresh_from_db()
        return p

    def disetujui(self, **kw):
        p = self.dinilai(**kw)
        services.nilai(p, self.penilai, HasilPenilaian.MEMENUHI, "Sesuai RTRW.")
        p.refresh_from_db()
        return p

    def terbit(self, **kw):
        p = self.disetujui(**kw)
        services.terbitkan(p, self.petugas)
        p.refresh_from_db()
        return p
