"""Data rujukan awal: 21 kecamatan Kabupaten Lombok Timur dan jenis izin NonOSS dari PRD.

Kelurahan/desa tidak diisi di sini; dibuat otomatis dari data impor OSS dan input NonOSS.
"""

from django.db import migrations

KECAMATAN = [
    "Aikmel", "Jerowaru", "Keruak", "Labuhan Haji", "Lenek", "Masbagik", "Montong Gading",
    "Pringgabaya", "Pringgasela", "Sakra", "Sakra Barat", "Sakra Timur", "Sambelia", "Selong",
    "Sembalun", "Sikur", "Suela", "Sukamulia", "Suralaga", "Terara", "Wanasaba",
]
JENIS_NONOSS = ["KKPR Nonberusaha"]


def isi(apps, schema_editor):
    Kecamatan = apps.get_model("basisdata", "Kecamatan")
    JenisIzinNonOSS = apps.get_model("basisdata", "JenisIzinNonOSS")
    for nama in KECAMATAN:
        Kecamatan.objects.get_or_create(nama=nama)
    for nama in JENIS_NONOSS:
        JenisIzinNonOSS.objects.get_or_create(nama=nama)


class Migration(migrations.Migration):
    dependencies = [("basisdata", "0001_initial")]

    operations = [migrations.RunPython(isi, migrations.RunPython.noop)]
