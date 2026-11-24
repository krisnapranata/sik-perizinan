"""Dokumen izin PDF dengan kode QR untuk cek keaslian (PRD IZ-09).

Tanda tangan elektronik BSrE tidak termasuk ruang lingkup (PRD bagian 4). Dokumen ini memuat
ruang tanda tangan; petugas boleh mengunggah pindaian yang sudah ditandatangani.
"""

from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.urls import reverse
from django.utils.formats import date_format
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from basisdata.ekspor import gaya_pdf


def url_verifikasi(izin):
    return settings.SITUS_URL + reverse("perizinan:verifikasi_izin", args=[izin.kode_verifikasi])


def _qr(teks, ukuran=32 * mm):
    widget = QrCodeWidget(teks)
    x1, y1, x2, y2 = widget.getBounds()
    gambar = Drawing(ukuran, ukuran, transform=[ukuran / (x2 - x1), 0, 0, ukuran / (y2 - y1), 0, 0])
    gambar.add(widget)
    return gambar


def _luas(n):
    """1234.5 -> '1.234,50 m²'"""
    if n is None:
        return ""
    teks = f"{n:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"{teks} m²"


def buat_pdf(izin):
    p = izin.permohonan
    pemohon = p.pemohon
    gaya = gaya_pdf()
    isi_gaya = ParagraphStyle("isi", parent=gaya["normal"], fontSize=10.5, leading=15)
    tengah = ParagraphStyle("tengah", parent=isi_gaya, alignment=1)

    def baris(label, nilai):
        return [Paragraph(escape(label), isi_gaya), Paragraph(escape(str(nilai or "-")), isi_gaya)]

    lokasi = ", ".join(
        x for x in [p.lokasi_alamat, p.kelurahan_nama, p.kecamatan.nama if p.kecamatan else ""] if x
    )
    data = [
        baris("Nama pemohon", pemohon.nama),
        baris("NIK" if pemohon.nik else "NPWP", pemohon.nik or pemohon.npwp),
        baris("Alamat pemohon", pemohon.alamat),
        baris("Lokasi objek", f"{lokasi}, Kabupaten Lombok Timur" if lokasi else ""),
        baris("Luas tanah", _luas(p.luas_tanah)),
        baris("Titik koordinat", p.koordinat),
        baris("Rencana kegiatan", p.rencana_kegiatan),
        baris("Nomor registrasi", p.nomor_registrasi),
    ]
    tabel = Table(data, colWidths=[46 * mm, 124 * mm], hAlign="LEFT")
    tabel.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))

    tanggal = date_format(izin.tanggal_terbit, "j F Y")
    ttd = Table(
        [[
            [_qr(url_verifikasi(izin)),
             Paragraph("Pindai untuk memeriksa keaslian dokumen", gaya["kecil"])],
            [Paragraph(f"Ditetapkan di Selong<br/>pada tanggal {escape(tanggal)}", isi_gaya),
             Spacer(1, 4 * mm),
             Paragraph(escape(settings.PEJABAT_IZIN), isi_gaya),
             Spacer(1, 22 * mm),
             Paragraph("(.........................................)", isi_gaya)],
        ]],
        colWidths=[60 * mm, 110 * mm],
    )
    ttd.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

    isi = [
        Paragraph(escape(settings.KOP_INSTANSI), gaya["kop1"]),
        Paragraph(escape(settings.KOP_DINAS), gaya["kop2"]),
        Paragraph(escape(settings.KOP_ALAMAT), gaya["kop3"]),
        Spacer(1, 2 * mm),
        HRFlowable(width="100%", thickness=1.6, color=colors.black, spaceAfter=1),
        HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceAfter=8 * mm),
        Paragraph(escape(p.jenis_izin.nama.upper()), gaya["judul"]),
        Paragraph(f"Nomor: {escape(izin.nomor_izin)}", tengah),
        Spacer(1, 8 * mm),
        Paragraph(
            "Berdasarkan permohonan yang telah diverifikasi dan memenuhi ketentuan, "
            "DPMPTSP Kabupaten Lombok Timur memberikan "
            f"{escape(p.jenis_izin.nama)} kepada:",
            isi_gaya,
        ),
        Spacer(1, 4 * mm),
        tabel,
        Spacer(1, 6 * mm),
        Paragraph(
            "Izin ini berlaku untuk lokasi dan kegiatan sebagaimana tersebut di atas dan dapat "
            "ditinjau kembali apabila di kemudian hari terdapat kekeliruan atau pelanggaran.",
            isi_gaya,
        ),
        Spacer(1, 10 * mm),
        ttd,
        Spacer(1, 6 * mm),
        Paragraph(
            "Keaslian dokumen dapat diperiksa di " + escape(url_verifikasi(izin)), gaya["kecil"]
        ),
    ]
    keluaran = BytesIO()
    SimpleDocTemplate(
        keluaran, pagesize=A4, title=f"{p.jenis_izin.nama} {izin.nomor_izin}",
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
    ).build(isi)
    return keluaran.getvalue()
