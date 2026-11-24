"""Data awal dari PRD. Semua bisa diubah Admin Sistem; daftar syarat final menunggu dinas."""

from django.db import migrations

SYARAT_DASAR = [
    ("KTP", "semua"),
    ("NPWP", "semua"),
    ("Data permodalan", "semua"),
    ("Akta perusahaan", "badan_hukum"),
]

JENIS = [
    ("Izin Lokasi", "", False),
    ("Izin Lingkungan (UKL-UPL/AMDAL)", "DLHK", False),
    ("IMB", "", False),
    ("Izin Usaha", "", True),
    ("Izin Komersial/Operasional", "", True),
]

EMAIL = [
    (
        "diterima",
        "Berkas {nomor} diterima",
        "Yth. {nama},\n\nPermohonan {jenis_izin} dengan nomor {nomor} telah kami terima "
        "dan masuk antrean verifikasi.\n\nPantau status: {tautan}\n",
    ),
    (
        "dikembalikan",
        "Berkas {nomor} dikembalikan",
        "Yth. {nama},\n\nPermohonan {jenis_izin} nomor {nomor} dikembalikan untuk diperbaiki.\n\n"
        "Catatan: {catatan}\n\nPerbaiki di: {tautan}\n",
    ),
    (
        "ditolak",
        "Permohonan {nomor} ditolak",
        "Yth. {nama},\n\nPermohonan {jenis_izin} nomor {nomor} tidak disetujui.\n\n"
        "Alasan: {catatan}\n\nDetail: {tautan}\n",
    ),
    (
        "komitmen_ditolak",
        "Komitmen permohonan {nomor} ditolak",
        "Yth. {nama},\n\nKomitmen pada permohonan {jenis_izin} nomor {nomor} tidak dipenuhi. "
        "Silakan mengajukan permohonan baru.\n\nAlasan: {catatan}\n\nDetail: {tautan}\n",
    ),
    (
        "terbit",
        "Izin {nomor} telah terbit",
        "Yth. {nama},\n\n{jenis_izin} untuk permohonan {nomor} telah terbit. "
        "Unduh dokumen izin di: {tautan}\n",
    ),
]


def isi(apps, schema_editor):
    JenisIzin = apps.get_model("perizinan", "JenisIzin")
    SyaratIzin = apps.get_model("perizinan", "SyaratIzin")
    TemplateEmail = apps.get_model("perizinan", "TemplateEmail")

    dibuat = {}
    for urutan, (nama, instansi, hanya_lanjutan) in enumerate(JENIS, start=1):
        jenis = JenisIzin.objects.create(
            nama=nama, instansi_teknis=instansi, hanya_lanjutan=hanya_lanjutan, urutan=urutan
        )
        dibuat[nama] = jenis
        for no, (syarat, berlaku) in enumerate(SYARAT_DASAR, start=1):
            SyaratIzin.objects.create(
                jenis_izin=jenis, nama=syarat, berlaku_untuk=berlaku, urutan=no
            )

    usaha = dibuat["Izin Usaha"]
    for nama in ("Izin Lokasi", "Izin Lingkungan (UKL-UPL/AMDAL)", "IMB"):
        dibuat[nama].lanjutan = usaha
        dibuat[nama].save(update_fields=["lanjutan"])
    usaha.lanjutan = dibuat["Izin Komersial/Operasional"]
    usaha.save(update_fields=["lanjutan"])

    for kode, subjek, teks in EMAIL:
        TemplateEmail.objects.create(kode=kode, subjek=subjek, isi=teks)


class Migration(migrations.Migration):
    dependencies = [("perizinan", "0001_initial")]
    operations = [migrations.RunPython(isi, migrations.RunPython.noop)]
