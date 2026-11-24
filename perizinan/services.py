"""Semua perubahan status permohonan hanya lewat modul ini (alur PRD PANDU LOTIM 6.1 dan 6.4)."""

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from akun.models import Peran
from core.audit import catat
from perizinan import notifikasi
from perizinan.models import (
    Aksi,
    Dokumen,
    HasilPenilaian,
    IzinTerbit,
    Kanal,
    PenilaianTeknis,
    PenomoranIzin,
    Permohonan,
    RiwayatVerifikasi,
    StatusCek,
    StatusPermohonan,
    nomor_registrasi_baru,
)
from perizinan.permissions import (
    bisa_cek_dokumen,
    bisa_nilai,
    bisa_perbaiki,
    bisa_verifikasi,
)

S = StatusPermohonan


class TransisiTidakValid(Exception):
    """Pesannya aman ditampilkan ke pengguna."""


# (status sekarang, aksi) -> status baru. Aksi petugas; penilaian instansi lewat nilai().
TRANSISI = {
    (S.DIAJUKAN, Aksi.MINTA_PERBAIKAN): S.PERLU_PERBAIKAN,
    (S.DIAJUKAN, Aksi.TERUSKAN): S.PENILAIAN_TEKNIS,
    (S.DIAJUKAN, Aksi.SETUJUI): S.DISETUJUI,
    (S.DIAJUKAN, Aksi.TOLAK): S.DITOLAK,
    (S.DISETUJUI, Aksi.TERBIT): S.TERBIT,
}
WAJIB_CATATAN = {Aksi.MINTA_PERBAIKAN, Aksi.TOLAK}
EMAIL_AKSI = {
    Aksi.MINTA_PERBAIKAN: "perlu_perbaikan",
    Aksi.TERUSKAN: "penilaian_teknis",
    Aksi.SETUJUI: "disetujui",
    Aksi.TOLAK: "ditolak",
}


def aksi_tersedia(permohonan):
    """Penilaian teknis hanya bila jenis izinnya memerlukan (PRD 6.4)."""
    aksi = [a for (status, a) in TRANSISI if status == permohonan.status and a != Aksi.TERBIT]
    if permohonan.jenis_izin.perlu_kajian_teknis:
        aksi = [a for a in aksi if a != Aksi.SETUJUI]
    else:
        aksi = [a for a in aksi if a != Aksi.TERUSKAN]
    return aksi


def _kunci(permohonan):
    return Permohonan.objects.select_for_update().get(pk=permohonan.pk)


def _pindah(permohonan, aksi, ke_status, pengguna, catatan="", kolom=()):
    dari = permohonan.status
    permohonan.status = ke_status
    permohonan.catatan_terakhir = catatan
    permohonan.save(update_fields=["status", "catatan_terakhir", "diperbarui_pada", *kolom])
    RiwayatVerifikasi.objects.create(
        permohonan=permohonan,
        dari_status=dari,
        ke_status=ke_status,
        aksi=aksi,
        verifikator=pengguna,
        catatan=catatan,
    )
    catat(pengguna, f"permohonan.{aksi}", permohonan, f"{dari} -> {ke_status}")


def buat_permohonan(pemohon, jenis_izin, pengguna):
    if not jenis_izin.aktif:
        raise TransisiTidakValid("Jenis izin ini tidak aktif.")
    kanal = Kanal.MANDIRI if pemohon.user_id == pengguna.pk else Kanal.BERBANTUAN
    for _ in range(5):  # tabrakan nomor acak sangat jarang, tetapi ditangani
        try:
            with transaction.atomic():
                permohonan = Permohonan.objects.create(
                    nomor_registrasi=nomor_registrasi_baru(timezone.localdate()),
                    pemohon=pemohon,
                    jenis_izin=jenis_izin,
                    kanal=kanal,
                    dibuat_oleh=pengguna,
                )
                catat(pengguna, "permohonan.buat", permohonan)
                return permohonan
        except IntegrityError:
            continue
    raise TransisiTidakValid("Gagal membuat nomor registrasi, silakan coba lagi.")


@transaction.atomic
def unggah_dokumen(permohonan, syarat, berkas, pengguna):
    permohonan = _kunci(permohonan)
    if not bisa_perbaiki(pengguna, permohonan):
        raise TransisiTidakValid("Berkas tidak bisa diubah pada status ini.")
    if not permohonan.syarat_berlaku().filter(pk=syarat.pk).exists():
        raise TransisiTidakValid("Syarat ini tidak berlaku untuk permohonan ini.")

    # Berkas lama tidak dihapus dari disk agar jejak pemeriksaan tetap bisa ditelusuri.
    dokumen, _ = Dokumen.objects.update_or_create(
        permohonan=permohonan,
        syarat=syarat,
        defaults={
            "berkas": berkas,
            "status_cek": StatusCek.BELUM,
            "catatan_cek": "",
            "diunggah_oleh": pengguna,
        },
    )
    catat(pengguna, "dokumen.unggah", dokumen)
    return dokumen


@transaction.atomic
def simpan_formulir(permohonan, form, pengguna):
    """`form` adalah FormulirForm yang sudah valid untuk `permohonan`."""
    if not bisa_perbaiki(pengguna, _kunci(permohonan)):
        raise TransisiTidakValid("Formulir tidak bisa diubah pada status ini.")
    form.save(commit=False).save(update_fields=[*form.Meta.fields, "diperbarui_pada"])
    catat(pengguna, "permohonan.formulir", permohonan, f"Kolom: {', '.join(form.changed_data)}")
    return permohonan


def kekurangan(permohonan):
    """Daftar alasan permohonan belum bisa dikirim."""
    alasan = []
    if not (permohonan.lokasi_alamat and permohonan.kecamatan_id and permohonan.rencana_kegiatan):
        alasan.append("Formulir lokasi dan rencana kegiatan belum lengkap.")
    terunggah = set(permohonan.dokumen.values_list("syarat_id", flat=True))
    for syarat in permohonan.syarat_berlaku().filter(wajib=True):
        if syarat.pk not in terunggah:
            alasan.append(f"Syarat belum diunggah: {syarat.nama}.")
    return alasan


@transaction.atomic
def kirim(permohonan, pengguna):
    permohonan = _kunci(permohonan)
    if not bisa_perbaiki(pengguna, permohonan):
        raise TransisiTidakValid("Permohonan tidak bisa dikirim pada status ini.")
    alasan = kekurangan(permohonan)
    if alasan:
        raise TransisiTidakValid(" ".join(alasan))
    permohonan.diajukan_pada = timezone.now()  # IZ-10: batas layanan dihitung ulang
    _pindah(permohonan, Aksi.KIRIM, S.DIAJUKAN, pengguna, kolom=["diajukan_pada"])
    notifikasi.kirim_email(permohonan, "diterima")
    return permohonan


def _pastikan_dokumen_sesuai(permohonan):
    """Permohonan hanya maju bila semua dokumen sudah diperiksa dan berstatus Sesuai."""
    if permohonan.dokumen.exclude(status_cek=StatusCek.SESUAI).exists():
        raise TransisiTidakValid("Semua dokumen harus berstatus Sesuai terlebih dahulu.")


@transaction.atomic
def proses(permohonan, aksi, pengguna, catatan="", instansi=None):
    """Keputusan petugas pada verifikasi administrasi (IZ-04)."""
    permohonan = _kunci(permohonan)
    catatan = catatan.strip()
    if not bisa_verifikasi(pengguna, permohonan):
        raise TransisiTidakValid("Anda tidak berwenang memproses permohonan pada tahap ini.")
    if aksi not in aksi_tersedia(permohonan):
        raise TransisiTidakValid("Aksi tidak tersedia pada tahap ini.")
    if aksi in WAJIB_CATATAN and not catatan:
        raise TransisiTidakValid("Catatan wajib diisi.")

    kolom = []
    if aksi in (Aksi.TERUSKAN, Aksi.SETUJUI):
        _pastikan_dokumen_sesuai(permohonan)
    if aksi == Aksi.TERUSKAN:
        instansi = instansi or permohonan.jenis_izin.instansi
        if instansi is None or not instansi.aktif:
            raise TransisiTidakValid("Pilih instansi teknis tujuan.")
        permohonan.instansi_penilai = instansi
        kolom.append("instansi_penilai")
        catatan = catatan or f"Diteruskan ke {instansi.nama}."

    _pindah(permohonan, aksi, TRANSISI[(permohonan.status, aksi)], pengguna, catatan, kolom)
    notifikasi.kirim_email(permohonan, EMAIL_AKSI[aksi])
    if aksi == Aksi.TERUSKAN:
        notifikasi.kabari_instansi(permohonan)
    if aksi == Aksi.TOLAK:
        _catat_ke_database(permohonan, pengguna)
    return permohonan


@transaction.atomic
def cek_dokumen(dokumen, status_cek, pengguna, catatan=""):
    """IZ-04 / PRD 6.3: catatan per dokumen agar pemohon tahu persis yang harus diperbaiki."""
    permohonan = _kunci(dokumen.permohonan)
    if not bisa_cek_dokumen(pengguna, permohonan):
        raise TransisiTidakValid("Anda tidak berwenang memeriksa dokumen pada tahap ini.")
    if status_cek not in (StatusCek.SESUAI, StatusCek.TIDAK_SESUAI):
        raise TransisiTidakValid("Status cek tidak valid.")
    if status_cek == StatusCek.TIDAK_SESUAI and not catatan.strip():
        raise TransisiTidakValid("Tulis catatan agar pemohon tahu apa yang harus diperbaiki.")
    dokumen.status_cek = status_cek
    dokumen.catatan_cek = catatan.strip()
    dokumen.save(update_fields=["status_cek", "catatan_cek"])
    catat(pengguna, "dokumen.cek", dokumen, status_cek)
    return dokumen


@transaction.atomic
def nilai(permohonan, pengguna, hasil, rekomendasi, berkas=None):
    """IZ-05: memenuhi -> Disetujui; tidak memenuhi -> Ditolak dengan alasan (PRD 6.4)."""
    permohonan = _kunci(permohonan)
    rekomendasi = (rekomendasi or "").strip()
    if not bisa_nilai(pengguna, permohonan):
        raise TransisiTidakValid("Anda tidak berwenang menilai permohonan ini.")
    if hasil not in HasilPenilaian.values:
        raise TransisiTidakValid("Hasil penilaian tidak valid.")
    if not rekomendasi:
        raise TransisiTidakValid("Rekomendasi atau alasan wajib diisi.")
    PenilaianTeknis.objects.create(
        permohonan=permohonan,
        instansi=pengguna.instansi,
        penilai=pengguna,
        hasil=hasil,
        rekomendasi=rekomendasi,
        berkas=berkas or "",
    )
    memenuhi = hasil == HasilPenilaian.MEMENUHI
    aksi = Aksi.MEMENUHI if memenuhi else Aksi.TIDAK_MEMENUHI
    _pindah(permohonan, aksi, S.DISETUJUI if memenuhi else S.DITOLAK, pengguna, rekomendasi)
    notifikasi.kirim_email(permohonan, "disetujui" if memenuhi else "ditolak")
    if not memenuhi:
        _catat_ke_database(permohonan, pengguna)
    return permohonan


def _nomor_izin_baru(jenis_izin, tanggal):
    """IZ-06: nomor urut per jenis per tahun, dikunci agar dua penerbitan tidak dapat nomor sama."""
    nomor, _ = PenomoranIzin.objects.get_or_create(jenis_izin=jenis_izin, tahun=tanggal.year)
    nomor = PenomoranIzin.objects.select_for_update().get(pk=nomor.pk)
    nomor.terakhir += 1
    nomor.save(update_fields=["terakhir"])
    return settings.FORMAT_NOMOR_IZIN.format(
        urut=nomor.terakhir, kode=jenis_izin.kode or "IZIN", tahun=tanggal.year,
        bulan=tanggal.month,
    )


@transaction.atomic
def terbitkan(permohonan, pengguna, berkas_ttd=None):
    """IZ-06 dan IZ-09: nomor otomatis, dokumen izin ber-QR dibuat sistem."""
    from perizinan.dokumen_izin import buat_pdf

    permohonan = _kunci(permohonan)
    if not bisa_verifikasi(pengguna, permohonan) or permohonan.status != S.DISETUJUI:
        raise TransisiTidakValid("Izin hanya bisa diterbitkan setelah permohonan disetujui.")
    tanggal = timezone.localdate()
    izin = IzinTerbit(
        permohonan=permohonan,
        nomor_izin=_nomor_izin_baru(permohonan.jenis_izin, tanggal),
        tanggal_terbit=tanggal,
    )
    izin.berkas.save("izin.pdf", ContentFile(buat_pdf(izin)), save=False)
    if berkas_ttd:
        izin.berkas_ttd = berkas_ttd
    izin.save()
    _pindah(permohonan, Aksi.TERBIT, S.TERBIT, pengguna, f"Nomor izin {izin.nomor_izin}.")
    notifikasi.kirim_email(permohonan, "terbit")
    _catat_ke_database(permohonan, pengguna, izin)
    return permohonan


@transaction.atomic
def ganti_dokumen_izin(permohonan, berkas, pengguna):
    izin = IzinTerbit.objects.select_for_update().get(permohonan=permohonan)
    izin.berkas_ttd = berkas
    izin.save(update_fields=["berkas_ttd"])
    catat(pengguna, "izin.unggah_ttd", izin)
    return izin


def _catat_ke_database(permohonan, pengguna, izin=None):
    """PRD 5.2: permohonan yang selesai di Modul 2 otomatis masuk Database NonOSS."""
    from basisdata.models import IzinNonOSS, JenisIzinNonOSS, Kelurahan, StatusNonOSS

    if permohonan.kecamatan_id is None:
        return None  # permohonan dari alur lama tanpa data lokasi
    jenis, _ = JenisIzinNonOSS.objects.get_or_create(nama=permohonan.jenis_izin.nama)
    kelurahan = None
    if permohonan.kelurahan_nama and permohonan.kecamatan_id:
        nama = " ".join(permohonan.kelurahan_nama.split())
        kelurahan = Kelurahan.objects.filter(
            kecamatan_id=permohonan.kecamatan_id, nama__iexact=nama
        ).first() or Kelurahan.objects.create(kecamatan_id=permohonan.kecamatan_id,
                                              nama=nama.title())
    riwayat_kirim = permohonan.riwayat.filter(aksi=Aksi.KIRIM).order_by("waktu").first()
    tanggal_permohonan = (
        timezone.localtime(riwayat_kirim.waktu).date() if riwayat_kirim else timezone.localdate()
    )
    data = {
        "jenis": jenis,
        "nomor_izin": izin.nomor_izin if izin else None,
        "nama_pemohon": permohonan.pemohon.nama,
        "nik": permohonan.pemohon.nik,
        "tanggal_permohonan": tanggal_permohonan,
        "tanggal_terbit": izin.tanggal_terbit if izin else None,
        "alamat_objek": permohonan.lokasi_alamat,
        "kecamatan_id": permohonan.kecamatan_id,
        "kelurahan": kelurahan,
        "status": StatusNonOSS.TERBIT if izin else StatusNonOSS.DITOLAK,
        "instansi_teknis": permohonan.instansi_penilai.nama if permohonan.instansi_penilai else "",
        "dokumen": izin.berkas_unduhan.name if izin else "",
    }
    catatan, dibuat = IzinNonOSS.objects.update_or_create(
        permohonan=permohonan, defaults={**data, "dibuat_oleh": pengguna}
    )
    catat(pengguna, "database.nonoss_tambah" if dibuat else "database.nonoss_ubah", catatan,
          f"Otomatis dari permohonan {permohonan.nomor_registrasi}")
    return catatan


def antrean(pengguna):
    """Permohonan yang menunggu tindakan pengguna, yang paling lama menunggu di atas."""
    qs = Permohonan.objects.select_related("pemohon", "jenis_izin", "kecamatan")
    if pengguna.peran == Peran.PETUGAS:
        qs = qs.filter(status__in=[S.DIAJUKAN, S.DISETUJUI])
    elif pengguna.peran == Peran.INSTANSI and pengguna.instansi_id:
        qs = qs.filter(status=S.PENILAIAN_TEKNIS, instansi_penilai_id=pengguna.instansi_id)
    else:
        return qs.none()
    return qs.order_by("diajukan_pada", "diperbarui_pada")
