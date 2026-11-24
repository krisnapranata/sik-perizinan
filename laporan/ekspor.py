from io import BytesIO

from django.utils.formats import date_format
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _bagian(data):
    return [
        ("Per status", ["Status", "Jumlah"], data["per_status"]),
        ("Per jenis izin", ["Jenis izin", "Jumlah"], data["per_jenis"]),
        (
            "Keputusan per petugas",
            ["Petugas", "Lolos tahap", "Perlu perbaikan", "Ditolak", "Terbit", "Total"],
            [
                (v["nama"], v["teruskan"], v["kembalikan"], v["tolak"], v["terbit"], v["total"])
                for v in data["per_verifikator"]
            ],
        ),
        (
            "Rata-rata lama per tahap",
            ["Tahap", "Jumlah berkas", "Rata-rata (jam)"],
            data["lama_tahap"],
        ),
    ]


def _lama(data):
    lama = data["lama_proses"]
    return lama["rata_hari"] if lama["rata_hari"] is not None else "-"


def _judul(data):
    return f"Laporan Layanan Izin Nonberusaha {date_format(data['judul_bulan'], 'F Y')}"


def ke_excel(data):
    buku = Workbook()
    lembar = buku.active
    lembar.title = "Laporan"
    lembar.append([_judul(data)])
    lembar["A1"].font = Font(bold=True, size=14)
    lembar.append(["Total permohonan masuk", data["total"]])
    lembar.append(["Rata-rata lama proses (hari)", _lama(data)])
    for judul, kepala, baris in _bagian(data):
        lembar.append([])
        lembar.append([judul])
        lembar.cell(lembar.max_row, 1).font = Font(bold=True)
        lembar.append(kepala)
        for b in baris:
            lembar.append(list(b))
    lembar.column_dimensions["A"].width = 34
    keluaran = BytesIO()
    buku.save(keluaran)
    return keluaran.getvalue()


def ke_pdf(data):
    keluaran = BytesIO()
    gaya = getSampleStyleSheet()
    isi = [
        Paragraph(_judul(data), gaya["Title"]),
        Paragraph(f"Total permohonan masuk: {data['total']}", gaya["Normal"]),
        Paragraph(f"Rata-rata lama proses sampai terbit: {_lama(data)} hari", gaya["Normal"]),
    ]
    gaya_tabel = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f5c4d")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]
    )
    for judul, kepala, baris in _bagian(data):
        isi += [Spacer(1, 14), Paragraph(judul, gaya["Heading3"])]
        if baris:
            isi.append(Table([kepala, *[list(b) for b in baris]], style=gaya_tabel, hAlign="LEFT"))
        else:
            isi.append(Paragraph("Belum ada data.", gaya["Normal"]))
    SimpleDocTemplate(keluaran, pagesize=A4, title=_judul(data)).build(isi)
    return keluaran.getvalue()
