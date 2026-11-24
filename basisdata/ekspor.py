"""Ekspor Excel dan PDF dengan kop DPMPTSP (PRD DB-04, AN-06)."""

from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone
from django.utils.formats import date_format
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

MAKS_BARIS_PDF = 2000
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

KOLOM_OSS = [
    ("Id Proyek", lambda p: p.id_proyek),
    ("NIB", lambda p: p.pelaku_id),
    ("Nama Perusahaan", lambda p: p.pelaku.nama),
    ("Jenis Perusahaan", lambda p: p.pelaku.jenis_perusahaan),
    ("Status PM", lambda p: p.pelaku.status_pm),
    ("Jenis Proyek", lambda p: p.jenis_proyek),
    ("Nama Proyek", lambda p: p.nama_proyek),
    ("KBLI", lambda p: p.kbli_id or ""),
    ("Judul KBLI", lambda p: p.kbli.judul if p.kbli else ""),
    ("Sektor", lambda p: p.kbli.get_sektor_display() if p.kbli else ""),
    ("Skala Usaha", lambda p: p.skala),
    ("Risiko", lambda p: p.risiko),
    ("Alamat Usaha", lambda p: p.alamat),
    ("Kecamatan", lambda p: p.kecamatan.nama),
    ("Kelurahan/Desa", lambda p: p.kelurahan.nama if p.kelurahan else ""),
    ("Tanggal Terbit OSS", lambda p: p.tanggal_terbit),
    ("Tanggal Pengajuan Proyek", lambda p: p.tanggal_pengajuan),
    ("Tahun", lambda p: p.tahun),
    ("Luas Tanah", lambda p: p.luas_tanah),
    ("Satuan", lambda p: p.satuan_tanah),
    ("Jumlah Investasi (Rp)", lambda p: p.investasi),
    ("TKI", lambda p: p.tki),
    ("Status Izin", lambda p: p.get_status_izin_display()),
]
KOLOM_OSS_PDF = ["NIB", "Nama Perusahaan", "Nama Proyek", "KBLI", "Kecamatan", "Tahun",
                 "Jumlah Investasi (Rp)", "TKI"]

# NIK tidak ikut diekspor (UU PDP); buka halaman detail bila memang diperlukan.
KOLOM_NONOSS = [
    ("Nomor Izin", lambda i: i.nomor_izin or ""),
    ("Jenis Perizinan", lambda i: i.jenis.nama),
    ("Nama Pemohon", lambda i: i.nama_pemohon),
    ("Tanggal Permohonan", lambda i: i.tanggal_permohonan),
    ("Tanggal Terbit", lambda i: i.tanggal_terbit),
    ("Lokasi Objek", lambda i: i.alamat_objek),
    ("Kecamatan", lambda i: i.kecamatan.nama),
    ("Kelurahan/Desa", lambda i: i.kelurahan.nama if i.kelurahan else ""),
    ("Status", lambda i: i.get_status_display()),
    ("Instansi Teknis", lambda i: i.instansi_teknis),
]
KOLOM_NONOSS_PDF = ["Nomor Izin", "Jenis Perizinan", "Nama Pemohon", "Tanggal Terbit",
                    "Kecamatan", "Status"]


def rupiah(n):
    return "Rp" + f"{n or 0:,}".replace(",", ".")


def _ribuan(n):
    return f"{n or 0:,}".replace(",", ".")


def _kop():
    return [settings.KOP_INSTANSI, settings.KOP_DINAS, settings.KOP_ALAMAT]


def _keterangan_filter(filter_aktif):
    if not filter_aktif:
        return "Filter: semua data"
    return "Filter: " + "; ".join(f"{k} = {v}" for k, v in filter_aktif.items())


# ---------------------------------------------------------------- Excel


def _buku(judul, filter_aktif):
    buku = Workbook(write_only=True)
    lembar = buku.create_sheet("Data")
    for teks in [*_kop(), "", judul, _keterangan_filter(filter_aktif),
                 f"Dicetak {date_format(timezone.localtime(), 'j F Y H.i')}", ""]:
        lembar.append([teks] if teks else [])
    return buku, lembar


def _simpan(buku):
    keluaran = BytesIO()
    buku.save(keluaran)
    return keluaran.getvalue()


def daftar_excel(judul, kolom, baris, filter_aktif, rekap=None):
    buku, lembar = _buku(judul, filter_aktif)
    for label, nilai in (rekap or []):
        lembar.append([label, nilai])
    if rekap:
        lembar.append([])
    lembar.append([k for k, _ in kolom])
    for obj in baris.iterator(chunk_size=2000):
        lembar.append([f(obj) for _, f in kolom])
    return _simpan(buku)


def statistik_excel(data):
    buku, lembar = _buku(_judul_statistik(data), {})
    for judul, kepala, isi in _bagian_statistik(data, mentah=True):
        lembar.append([judul])
        lembar.append(kepala)
        for b in isi:
            lembar.append(list(b))
        lembar.append([])
    return _simpan(buku)


# ---------------------------------------------------------------- PDF


def gaya_pdf():
    dasar = getSampleStyleSheet()
    return {
        "kop1": ParagraphStyle("kop1", parent=dasar["Normal"], fontName="Helvetica-Bold",
                               fontSize=12, alignment=1, leading=15),
        "kop2": ParagraphStyle("kop2", parent=dasar["Normal"], fontName="Helvetica-Bold",
                               fontSize=14, alignment=1, leading=18),
        "kop3": ParagraphStyle("kop3", parent=dasar["Normal"], fontSize=9, alignment=1),
        "judul": ParagraphStyle("judul", parent=dasar["Heading2"], alignment=1),
        "kecil": ParagraphStyle("kecil", parent=dasar["Normal"], fontSize=8, leading=10),
        "kepala": ParagraphStyle("kepala", parent=dasar["Normal"], fontSize=8, leading=10,
                                 fontName="Helvetica-Bold", textColor=colors.white),
        "normal": dasar["Normal"],
        "sub": dasar["Heading4"],
    }


def _kop_pdf(gaya, judul, filter_aktif):
    kop1, kop2, kop3 = (escape(t) for t in _kop())
    return [
        Paragraph(kop1, gaya["kop1"]),
        Paragraph(kop2, gaya["kop2"]),
        Paragraph(kop3, gaya["kop3"]),
        Spacer(1, 2 * mm),
        HRFlowable(width="100%", thickness=1.6, color=colors.black, spaceAfter=1),
        HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceAfter=6 * mm),
        Paragraph(escape(judul), gaya["judul"]),
        Paragraph(escape(_keterangan_filter(filter_aktif)), gaya["kecil"]),
        Paragraph(
            "Dicetak " + escape(date_format(timezone.localtime(), "j F Y H.i")), gaya["kecil"]
        ),
        Spacer(1, 4 * mm),
    ]


def _tabel(kepala, isi, gaya):
    sel = [[Paragraph(escape(str(k)), gaya["kepala"]) for k in kepala]]
    sel += [[Paragraph(escape("" if v is None else str(v)), gaya["kecil"]) for v in b] for b in isi]
    t = Table(sel, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2a44")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _pdf(isi, judul, mendatar=False):
    keluaran = BytesIO()
    ukuran = landscape(A4) if mendatar else A4
    SimpleDocTemplate(
        keluaran, pagesize=ukuran, title=judul, leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    ).build(isi)
    return keluaran.getvalue()


def daftar_pdf(judul, kolom, kolom_pdf, baris, filter_aktif, rekap=None):
    gaya = gaya_pdf()
    isi = _kop_pdf(gaya, judul, filter_aktif)
    if rekap:
        isi += [_tabel(["Rekap", "Nilai"], [(a, b) for a, b in rekap], gaya), Spacer(1, 4 * mm)]
    pilih = [(k, f) for k, f in kolom if k in kolom_pdf]
    total = baris.count()
    data = [
        [_format(k, f(obj)) for k, f in pilih] for obj in baris[:MAKS_BARIS_PDF].iterator()
    ]
    isi.append(_tabel([k for k, _ in pilih], data, gaya))
    if total > MAKS_BARIS_PDF:
        isi += [Spacer(1, 3 * mm), Paragraph(
            f"Ditampilkan {_ribuan(MAKS_BARIS_PDF)} dari {_ribuan(total)} baris. "
            "Gunakan ekspor Excel untuk data lengkap.", gaya["kecil"])]
    return _pdf(isi, judul, mendatar=True)


def _format(kolom, nilai):
    if "Investasi" in kolom:
        return rupiah(nilai)
    if hasattr(nilai, "strftime"):
        return nilai.strftime("%d/%m/%Y")
    return nilai


def _judul_statistik(data):
    return "Statistik Perizinan Berusaha dan Nonberusaha" + (
        f" Tahun {data['tahun']}" if data["tahun"] else ""
    )


def _bagian_statistik(data, mentah=False):
    uang = (lambda n: n) if mentah else rupiah
    r = data["ringkasan"]
    bagian = [
        ("Ringkasan", ["Ukuran", "Nilai"], [
            ("Jumlah usaha (NIB unik)", r["usaha"]),
            ("Jumlah proyek", r["proyek"]),
            ("Total nilai investasi", uang(r["investasi"])),
            ("Total tenaga kerja", r["tki"]),
        ]),
        ("Tren per tahun", ["Tahun", "Usaha", "Proyek", "Investasi"],
         [(t["tahun"], t["usaha"], t["proyek"], uang(t["investasi"])) for t in data["tren"]]),
    ]
    for judul, kunci in [("Per kecamatan", "per_kecamatan"), ("Per sektor", "per_sektor"),
                         ("Per skala usaha", "per_skala"), ("Per tingkat risiko", "per_risiko")]:
        bagian.append((judul, ["Nama", "Usaha", "Proyek", "Investasi"],
                       [(b["nama"], b["usaha"], b["proyek"], uang(b["investasi"]))
                        for b in data[kunci]]))
    lama = data["layanan"]["lama"]["rata_hari"]
    bagian.append(("Layanan izin online per status", ["Status", "Jumlah"],
                   [*data["layanan"]["per_status"],
                    ("Rata-rata lama proses (hari)", "-" if lama is None else lama)]))
    bagian.append(("Perizinan NonOSS per jenis", ["Jenis", "Jumlah"], data["nonoss"]["per_jenis"]))
    bagian.append(("Perizinan NonOSS per status", ["Status", "Jumlah"],
                   data["nonoss"]["per_status"]))
    return bagian


def statistik_pdf(data):
    gaya = gaya_pdf()
    judul = _judul_statistik(data)
    isi = _kop_pdf(gaya, judul, {})
    for sub, kepala, baris in _bagian_statistik(data):
        isi.append(Paragraph(escape(sub), gaya["sub"]))
        isi.append(_tabel(kepala, baris, gaya) if baris else Paragraph("Belum ada data.", gaya["kecil"]))
        isi.append(Spacer(1, 4 * mm))
    return _pdf(isi, judul)
