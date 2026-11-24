"""Alur izin nonberusaha (KKPR) sesuai PRD PANDU LOTIM 6.1 dan 6.4.

- Status lama dipetakan ke status PRD. Riwayat verifikasi TIDAK diubah (jejak audit).
- Jenis izin berusaha lama (Izin Lokasi, IMB, dst.) dinonaktifkan, tidak dihapus.
- Jalur komitmen OSS dan izin lanjutan dihapus: tidak ada di PRD.
"""

import secrets

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import core.validators
import perizinan.models

STATUS = [
    ("draf", "Draf"),
    ("diajukan", "Diajukan"),
    ("perlu_perbaikan", "Perlu perbaikan"),
    ("penilaian_teknis", "Penilaian teknis"),
    ("disetujui", "Disetujui"),
    ("ditolak", "Ditolak"),
    ("terbit", "Terbit"),
]
STATUS_RIWAYAT = STATUS + [
    ("verifikasi_kasi", "Verifikasi Kasi"),
    ("verifikasi_kabid", "Verifikasi Kabid"),
    ("verifikasi_kadis", "Verifikasi Kadis"),
    ("dikembalikan", "Dikembalikan"),
    ("komitmen_ditolak", "Komitmen Ditolak"),
]
AKSI_RIWAYAT = [
    ("kirim", "Kirim"),
    ("minta_perbaikan", "Minta perbaikan"),
    ("teruskan", "Teruskan ke instansi teknis"),
    ("setujui", "Setujui"),
    ("tolak", "Tolak"),
    ("memenuhi", "Rekomendasi: memenuhi"),
    ("tidak_memenuhi", "Rekomendasi: tidak memenuhi"),
    ("terbit", "Terbitkan izin"),
    ("mulai", "Mulai verifikasi"),
    ("kembalikan", "Kembalikan"),
    ("komitmen_ditolak", "Komitmen Ditolak"),
]
KODE_EMAIL = [
    ("diterima", "Permohonan diterima"),
    ("perlu_perbaikan", "Perlu perbaikan"),
    ("penilaian_teknis", "Diteruskan ke instansi teknis"),
    ("disetujui", "Permohonan disetujui"),
    ("ditolak", "Permohonan ditolak"),
    ("terbit", "Izin terbit"),
]
PETA_STATUS = {
    "verifikasi_kasi": "diajukan",
    "verifikasi_kabid": "diajukan",
    "verifikasi_kadis": "diajukan",
    "dikembalikan": "perlu_perbaikan",
    "komitmen_ditolak": "ditolak",
}

INSTANSI = [
    ("Dinas Pekerjaan Umum dan Penataan Ruang", "PUPR"),
    ("Badan Perencanaan Pembangunan Daerah", "Bappeda"),
]
# Contoh awal; daftar final mengikuti ketetapan dinas dan bisa diubah Admin Sistem.
SYARAT_KKPR = [
    ("Surat permohonan", "semua", ""),
    ("KTP pemohon", "semua", ""),
    ("Akta pendirian badan hukum", "badan_hukum", ""),
    ("Bukti penguasaan tanah", "semua", "Sertifikat, akta jual beli, atau surat keterangan desa"),
    ("Gambar lokasi dan titik koordinat", "semua", "Sketsa bidang tanah atau peta lokasi"),
]
EMAIL = {
    "diterima": (
        "Permohonan {nomor} diterima",
        "Yth. {nama},\n\nPermohonan {jenis_izin} dengan nomor {nomor} telah kami terima "
        "dan masuk antrean verifikasi.\n\nPantau status: {tautan}\n",
    ),
    "perlu_perbaikan": (
        "Permohonan {nomor} perlu perbaikan",
        "Yth. {nama},\n\nPermohonan {jenis_izin} nomor {nomor} perlu diperbaiki sebelum "
        "diproses lebih lanjut.\n\nCatatan: {catatan}\n\nPerbaiki di: {tautan}\n",
    ),
    "penilaian_teknis": (
        "Permohonan {nomor} dalam penilaian teknis",
        "Yth. {nama},\n\nDokumen permohonan {jenis_izin} nomor {nomor} sudah lengkap dan "
        "diteruskan ke instansi teknis untuk penilaian.\n\nPantau status: {tautan}\n",
    ),
    "disetujui": (
        "Permohonan {nomor} disetujui",
        "Yth. {nama},\n\nPermohonan {jenis_izin} nomor {nomor} disetujui. Dokumen izin sedang "
        "diterbitkan.\n\nPantau status: {tautan}\n",
    ),
    "ditolak": (
        "Permohonan {nomor} ditolak",
        "Yth. {nama},\n\nPermohonan {jenis_izin} nomor {nomor} tidak memenuhi ketentuan.\n\n"
        "Alasan: {catatan}\n\nDetail: {tautan}\n",
    ),
    "terbit": (
        "Izin {nomor} telah terbit",
        "Yth. {nama},\n\n{jenis_izin} untuk permohonan {nomor} telah terbit. "
        "Unduh dokumen izin di: {tautan}\n",
    ),
}


def maju(apps, schema_editor):
    JenisIzin = apps.get_model("perizinan", "JenisIzin")
    SyaratIzin = apps.get_model("perizinan", "SyaratIzin")
    Permohonan = apps.get_model("perizinan", "Permohonan")
    Riwayat = apps.get_model("perizinan", "RiwayatVerifikasi")
    IzinTerbit = apps.get_model("perizinan", "IzinTerbit")
    TemplateEmail = apps.get_model("perizinan", "TemplateEmail")
    Instansi = apps.get_model("akun", "Instansi")

    for nama, singkatan in INSTANSI:
        Instansi.objects.get_or_create(nama=nama, defaults={"singkatan": singkatan})
    for jenis in JenisIzin.objects.all():
        if jenis.instansi_teknis:
            jenis.instansi, _ = Instansi.objects.get_or_create(nama=jenis.instansi_teknis)
            jenis.perlu_kajian_teknis = True
        jenis.aktif = False  # izin berusaha: tetap lewat OSS-RBA (PRD bagian 4)
        jenis.save()

    kkpr, _ = JenisIzin.objects.get_or_create(
        nama="KKPR Nonberusaha",
        defaults={
            "kode": "KKPR-NB",
            "keterangan": "Kesesuaian Kegiatan Pemanfaatan Ruang untuk kegiatan nonberusaha, "
            "misalnya rumah tinggal, tempat ibadah, atau fasilitas sosial.",
            "perlu_kajian_teknis": True,
            "instansi": Instansi.objects.get(singkatan="PUPR"),
            "sla_hari": 14,
            "urutan": 1,
        },
    )
    for no, (nama, berlaku, keterangan) in enumerate(SYARAT_KKPR, start=1):
        SyaratIzin.objects.get_or_create(
            jenis_izin=kkpr,
            nama=nama,
            defaults={"berlaku_untuk": berlaku, "keterangan": keterangan, "urutan": no},
        )

    for lama, baru in PETA_STATUS.items():
        Permohonan.objects.filter(status=lama).update(status=baru)
    for p in Permohonan.objects.exclude(status="draf"):
        kirim = Riwayat.objects.filter(permohonan=p, aksi="kirim").order_by("-waktu").first()
        if kirim:
            Permohonan.objects.filter(pk=p.pk).update(diajukan_pada=kirim.waktu)

    for izin in IzinTerbit.objects.all():
        izin.kode_verifikasi = secrets.token_urlsafe(18)
        izin.save(update_fields=["kode_verifikasi"])

    TemplateEmail.objects.filter(kode__in=["dikembalikan", "komitmen_ditolak"]).delete()
    for kode, (subjek, isi) in EMAIL.items():
        TemplateEmail.objects.update_or_create(kode=kode, defaults={"subjek": subjek, "isi": isi})


class Migration(migrations.Migration):
    dependencies = [
        ("perizinan", "0002_data_awal"),
        ("akun", "0004_peran_prd_pandu"),
        ("basisdata", "0002_data_awal"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Kolom dan tabel baru
        migrations.AddField(
            model_name="jenisizin",
            name="kode",
            field=models.CharField(blank=True, help_text="Dipakai di nomor izin otomatis, mis. KKPR-NB.", max_length=20, verbose_name="kode nomor izin"),
        ),
        migrations.AlterField(
            model_name="jenisizin",
            name="keterangan",
            field=models.TextField(blank=True, help_text="Penjelasan singkat untuk pemohon di katalog izin.", verbose_name="keterangan"),
        ),
        migrations.AddField(
            model_name="jenisizin",
            name="perlu_kajian_teknis",
            field=models.BooleanField(default=False, help_text="Bila dicentang, petugas wajib meneruskan permohonan ke instansi teknis.", verbose_name="perlu penilaian instansi teknis"),
        ),
        migrations.AddField(
            model_name="jenisizin",
            name="instansi",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="jenis_izin", to="akun.instansi", verbose_name="instansi teknis bawaan"),
        ),
        migrations.AddField(
            model_name="jenisizin",
            name="sla_hari",
            field=models.PositiveSmallIntegerField(default=14, help_text="Dihitung sejak permohonan terakhir diajukan. Dipakai untuk pengingat SLA.", verbose_name="batas waktu layanan (hari)"),
        ),
        migrations.AddField(
            model_name="syaratizin",
            name="keterangan",
            field=models.CharField(blank=True, max_length=255, verbose_name="keterangan"),
        ),
        migrations.AddField(
            model_name="permohonan",
            name="lokasi_alamat",
            field=models.TextField(blank=True, verbose_name="alamat lokasi objek"),
        ),
        migrations.AddField(
            model_name="permohonan",
            name="kecamatan",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="permohonan", to="basisdata.kecamatan", verbose_name="kecamatan"),
        ),
        migrations.AddField(
            model_name="permohonan",
            name="kelurahan_nama",
            field=models.CharField(blank=True, max_length=80, verbose_name="kelurahan/desa"),
        ),
        migrations.AddField(
            model_name="permohonan",
            name="luas_tanah",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name="luas tanah (m²)"),
        ),
        migrations.AddField(
            model_name="permohonan",
            name="rencana_kegiatan",
            field=models.TextField(blank=True, verbose_name="rencana kegiatan / pemanfaatan ruang"),
        ),
        migrations.AddField(
            model_name="permohonan",
            name="koordinat",
            field=models.CharField(blank=True, help_text="Contoh: -8.6512, 116.5321", max_length=60, verbose_name="titik koordinat"),
        ),
        migrations.AddField(
            model_name="permohonan",
            name="instansi_penilai",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="permohonan", to="akun.instansi", verbose_name="instansi teknis penilai"),
        ),
        migrations.AddField(
            model_name="permohonan",
            name="diajukan_pada",
            field=models.DateTimeField(blank=True, null=True, verbose_name="terakhir diajukan"),
        ),
        migrations.RenameField(model_name="izinterbit", old_name="nomor_izin_oss", new_name="nomor_izin"),
        migrations.AddField(
            model_name="izinterbit",
            name="berkas_ttd",
            field=models.FileField(blank=True, upload_to=perizinan.models.lokasi_izin, validators=[core.validators.validasi_berkas], verbose_name="dokumen bertanda tangan"),
        ),
        migrations.AddField(
            model_name="izinterbit",
            name="kode_verifikasi",
            field=models.CharField(editable=False, max_length=40, null=True, verbose_name="kode verifikasi"),
        ),
        migrations.CreateModel(
            name="PenilaianTeknis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hasil", models.CharField(choices=[("memenuhi", "Memenuhi"), ("tidak_memenuhi", "Tidak memenuhi")], max_length=16, verbose_name="hasil")),
                ("rekomendasi", models.TextField(verbose_name="rekomendasi / alasan")),
                ("berkas", models.FileField(blank=True, upload_to=perizinan.models.lokasi_rekomendasi, validators=[core.validators.validasi_berkas], verbose_name="berkas rekomendasi")),
                ("waktu", models.DateTimeField(auto_now_add=True, verbose_name="waktu")),
                ("instansi", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="penilaian", to="akun.instansi", verbose_name="instansi")),
                ("penilai", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="penilai")),
                ("permohonan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="penilaian", to="perizinan.permohonan", verbose_name="permohonan")),
            ],
            options={"verbose_name": "penilaian teknis", "verbose_name_plural": "penilaian teknis", "ordering": ["waktu", "id"]},
        ),
        migrations.CreateModel(
            name="PenomoranIzin",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tahun", models.PositiveSmallIntegerField()),
                ("terakhir", models.PositiveIntegerField(default=0)),
                ("jenis_izin", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="perizinan.jenisizin")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("jenis_izin", "tahun"), name="nomor_unik_per_tahun")],
            },
        ),
        # Pilihan kode email diperluas dulu agar data baru boleh disimpan.
        migrations.AlterField(
            model_name="templateemail",
            name="kode",
            field=models.CharField(choices=KODE_EMAIL, max_length=20, unique=True, verbose_name="peristiwa"),
        ),
        # 2. Pindahkan data
        migrations.RunPython(maju, migrations.RunPython.noop),
        # 3. Hapus konsep lama
        migrations.RemoveField(model_name="jenisizin", name="instansi_teknis"),
        migrations.RemoveField(model_name="jenisizin", name="jalur_tersedia"),
        migrations.RemoveField(model_name="jenisizin", name="lanjutan"),
        migrations.RemoveField(model_name="jenisizin", name="hanya_lanjutan"),
        migrations.RemoveField(model_name="permohonan", name="jalur"),
        migrations.RemoveField(model_name="permohonan", name="induk"),
        migrations.RemoveField(model_name="permohonan", name="komitmen_instansi"),
        migrations.RemoveField(model_name="permohonan", name="komitmen_tanggal_ajuan"),
        migrations.RemoveField(model_name="permohonan", name="komitmen_nomor_oss"),
        migrations.RemoveField(model_name="permohonan", name="komitmen_tanggal_terbit"),
        migrations.RemoveField(model_name="permohonan", name="komitmen_berkas"),
        # 4. Pilihan dan batasan akhir
        migrations.AlterField(
            model_name="permohonan",
            name="status",
            field=models.CharField(choices=STATUS, db_index=True, default="draf", max_length=20, verbose_name="status"),
        ),
        migrations.AlterField(
            model_name="riwayatverifikasi",
            name="dari_status",
            field=models.CharField(choices=STATUS_RIWAYAT, max_length=20, verbose_name="tahap"),
        ),
        migrations.AlterField(
            model_name="riwayatverifikasi",
            name="ke_status",
            field=models.CharField(choices=STATUS_RIWAYAT, max_length=20, verbose_name="status baru"),
        ),
        migrations.AlterField(
            model_name="riwayatverifikasi",
            name="aksi",
            field=models.CharField(choices=AKSI_RIWAYAT, max_length=20, verbose_name="aksi"),
        ),
        migrations.AlterField(
            model_name="izinterbit",
            name="nomor_izin",
            field=models.CharField(max_length=80, unique=True, verbose_name="nomor izin"),
        ),
        migrations.AlterField(
            model_name="izinterbit",
            name="kode_verifikasi",
            field=models.CharField(default=perizinan.models.kode_verifikasi_baru, editable=False, max_length=40, unique=True, verbose_name="kode verifikasi"),
        ),
    ]
