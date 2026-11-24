"""Peran mengikuti PRD PANDU LOTIM bagian 3.

Loket, Kasi, dan Kabid -> Petugas DPMPTSP (front office dan verifikator).
Kadis -> Pimpinan (melihat dashboard dan laporan).
"""

import django.db.models.deletion
from django.db import migrations, models

PEMETAAN = {"loket": "petugas", "kasi": "petugas", "kabid": "petugas", "kadis": "pimpinan"}
BALIK = {"petugas": "kasi", "pimpinan": "kadis"}


def maju(apps, schema_editor):
    User = apps.get_model("akun", "User")
    for lama, baru in PEMETAAN.items():
        User.objects.filter(peran=lama).update(peran=baru)


def mundur(apps, schema_editor):
    User = apps.get_model("akun", "User")
    for baru, lama in BALIK.items():
        User.objects.filter(peran=baru).update(peran=lama)


PERAN = [
    ("pemohon", "Pemohon"),
    ("petugas", "Petugas DPMPTSP"),
    ("instansi", "Instansi Teknis"),
    ("pimpinan", "Pimpinan"),
    ("admin", "Admin Sistem"),
]


class Migration(migrations.Migration):
    dependencies = [("akun", "0003_percobaanmasuk")]

    operations = [
        migrations.CreateModel(
            name="Instansi",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nama", models.CharField(max_length=150, unique=True, verbose_name="nama")),
                ("singkatan", models.CharField(blank=True, max_length=30, verbose_name="singkatan")),
                ("aktif", models.BooleanField(default=True, verbose_name="aktif")),
            ],
            options={
                "verbose_name": "instansi teknis",
                "verbose_name_plural": "instansi teknis",
                "ordering": ["nama"],
            },
        ),
        migrations.AddField(
            model_name="user",
            name="instansi",
            field=models.ForeignKey(
                blank=True,
                help_text="Wajib untuk peran Instansi Teknis.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pengguna",
                to="akun.instansi",
                verbose_name="instansi",
            ),
        ),
        migrations.RunPython(maju, mundur),
        migrations.AlterField(
            model_name="user",
            name="peran",
            field=models.CharField(choices=PERAN, default="pemohon", max_length=12, verbose_name="peran"),
        ),
        migrations.CreateModel(
            name="KodeOTP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kode_hash", models.CharField(max_length=64)),
                ("dibuat", models.DateTimeField(auto_now_add=True)),
                ("kedaluwarsa", models.DateTimeField()),
                ("percobaan", models.PositiveSmallIntegerField(default=0)),
                ("dipakai", models.BooleanField(default=False)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kode_otp",
                        to="akun.user",
                    ),
                ),
            ],
            options={"verbose_name": "kode OTP", "verbose_name_plural": "kode OTP", "ordering": ["-dibuat"]},
        ),
    ]
