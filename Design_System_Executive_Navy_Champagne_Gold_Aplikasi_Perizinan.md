# Design System UI/UX — Executive Navy & Champagne Gold
## Arah Visual Premium untuk Aplikasi Perizinan

**Versi:** 1.0  
**Tema:** Executive Navy & Champagne Gold  
**Karakter:** Premium, resmi, elegan, modern, tepercaya, dan berorientasi pelayanan publik  
**Mode rekomendasi:** Hybrid — sidebar gelap, area kerja terang  
**Target:** Admin/petugas, pimpinan, verifikator, approver, dan portal pemohon

---

## 1. Tujuan desain

Membangun identitas visual aplikasi perizinan yang terasa seperti platform enterprise kelas atas, bukan template admin generik. Desain harus memberi kesan:

- **Berwibawa:** sesuai konteks layanan pemerintahan dan administrasi resmi.
- **Premium:** penggunaan warna, tipografi, ruang, dan detail visual yang terkendali.
- **Jelas:** status permohonan, tenggat, tindakan, dan tanggung jawab mudah dipahami.
- **Efisien:** petugas dapat memproses banyak permohonan tanpa tampilan yang melelahkan.
- **Responsif dan inklusif:** nyaman di desktop, tablet, dan ponsel; kontras dan fokus keyboard harus memadai.

Kemewahan tidak boleh mengorbankan keterbacaan, aksesibilitas, kecepatan, atau konsistensi.

## 2. Prinsip desain

1. **Clarity over decoration** — informasi dan tindakan utama selalu lebih menonjol daripada ornamen.
2. **Restrained luxury** — Champagne Gold adalah aksen, bukan warna latar dominan.
3. **Consistent workflow** — pola status, tombol, formulir, dan persetujuan konsisten di seluruh modul.
4. **Trust by design** — tampilkan nomor registrasi, waktu, pemilik tugas, sumber data, dan riwayat perubahan secara jelas.
5. **Progressive disclosure** — detail lanjutan ditampilkan saat diperlukan; halaman utama tidak penuh sesak.
6. **Accessible by default** — jangan mengandalkan warna saja untuk menyampaikan status.

## 3. Palet warna

### 3.1 Warna inti

| Token | Hex | Pemakaian |
|---|---|---|
| `navy-950` | `#101B32` | Sidebar, header gelap, area identitas |
| `navy-900` | `#17243D` | Hover/active sidebar, panel gelap |
| `navy-800` | `#243550` | Variasi panel dan elemen sekunder |
| `champagne-500` | `#C5A46D` | Aksen premium, ikon/garis terpilih |
| `champagne-600` | `#A9854D` | Aksen lebih kuat; gunakan dengan kontras yang cukup |
| `ivory-50` | `#F7F5EF` | Latar utama lembut |
| `white` | `#FFFFFF` | Kartu, tabel, formulir |
| `slate-700` | `#344054` | Teks sekunder kuat |
| `slate-500` | `#667085` | Teks pendukung |
| `slate-300` | `#D0D5DD` | Border dan divider |
| `slate-100` | `#F2F4F7` | Latar elemen netral |

### 3.2 Warna semantik

| Token | Hex | Makna |
|---|---|---|
| `success-700` | `#027A48` | Disetujui, selesai |
| `success-50` | `#ECFDF3` | Latar status sukses |
| `info-700` | `#175CD3` | Informasi, sedang diproses |
| `info-50` | `#EFF8FF` | Latar status informasi |
| `warning-700` | `#B54708` | Perlu tindakan, mendekati tenggat |
| `warning-50` | `#FFFAEB` | Latar status peringatan |
| `danger-700` | `#B42318` | Ditolak, gagal, bermasalah |
| `danger-50` | `#FEF3F2` | Latar status bahaya |

**Aturan:** status wajib memiliki teks/label dan bila perlu ikon; jangan hanya memakai warna. Pastikan rasio kontras teks memenuhi WCAG 2.2 AA sejauh memungkinkan.

## 4. Tipografi

Gunakan font sans-serif yang mudah dibaca dan tersedia luas.

- **Utama:** Inter.
- **Alternatif:** system-ui, `-apple-system`, BlinkMacSystemFont, "Segoe UI", sans-serif.
- **Angka/ID:** gunakan angka tabular bila tersedia agar kolom nomor dan statistik rapi.

Skala yang disarankan:

| Peran | Ukuran | Weight |
|---|---:|---:|
| Page title | 28–32 px | 650–700 |
| Section title | 20–24 px | 600 |
| Card title | 15–17 px | 600 |
| Body | 14–16 px | 400 |
| Label/form | 13–14 px | 500 |
| Caption/helper | 12–13 px | 400 |
| KPI value | 28–36 px | 650–700 |

Gunakan line-height sekitar 1.45–1.6 untuk teks isi. Hindari terlalu banyak huruf kapital dan font dekoratif.

## 5. Layout dan struktur aplikasi

### 5.1 Desktop — Hybrid Layout

- **Sidebar kiri:** navy gelap, lebar sekitar 248–272 px; dapat diciutkan.
- **Topbar:** putih, tinggi sekitar 64–72 px; memuat breadcrumb, pencarian, notifikasi, bantuan, dan profil.
- **Main canvas:** ivory lembut dengan konten utama pada kartu putih.
- **Content width:** gunakan ruang layar secara proporsional; hindari baris tabel yang terlalu sempit.
- **Spacing:** sistem kelipatan 4/8 px; jarak antarseksi 24–32 px.
- **Border radius:** 10–14 px untuk kartu; 8–10 px untuk input dan tombol.
- **Shadow:** halus dan jarang; utamakan border tipis daripada bayangan tebal.

Contoh struktur:

```text
┌────────────────────────────────────────────────────────────────┐
│ SIDEBAR NAVY │ TOPBAR: Breadcrumb | Search | Bell | Profile     │
│              ├─────────────────────────────────────────────────┤
│ Brand        │ Page title                         Primary CTA   │
│ Dashboard    │ Supporting description                          │
│ Permohonan   │ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ Verifikasi   │ │ KPI     │ │ KPI     │ │ KPI     │ │ KPI     │ │
│ Persetujuan  │ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
│ Dokumen      │ ┌─────────────────────────┐ ┌──────────────────┐ │
│ Laporan      │ │ Trend / workload        │ │ SLA / activity   │ │
│ Pengaturan   │ └─────────────────────────┘ └──────────────────┘ │
└──────────────┴─────────────────────────────────────────────────┘
```

### 5.2 Navigasi yang disarankan

1. Ringkasan / Dashboard
2. Permohonan
   - Semua permohonan
   - Draft
   - Menunggu verifikasi
   - Perlu perbaikan
   - Menunggu persetujuan
   - Selesai / izin terbit
   - Ditolak
3. Verifikasi
4. Persetujuan
5. Dokumen
6. Jadwal dan SLA
7. Laporan
8. Audit Trail
9. Master Data
10. Pengguna dan Hak Akses
11. Pengaturan

Menu harus disesuaikan dengan proses bisnis sebenarnya. Sembunyikan menu yang tidak relevan dengan role pengguna.

## 6. Komponen UI

### 6.1 Sidebar

- Latar `navy-950`.
- Logo dan nama aplikasi di bagian atas.
- Menu aktif memakai panel `navy-900`, aksen garis champagne tipis, ikon dan label jelas.
- Ikon sederhana dengan ukuran konsisten.
- Kelompok menu diberi jarak dan label kecil.
- Bagian bawah: versi aplikasi, bantuan, dan identitas organisasi bila dibutuhkan.

### 6.2 Topbar

Komponen:
- Breadcrumb.
- Global search.
- Tombol bantuan.
- Notifikasi dengan indikator yang tidak berlebihan.
- Profil pengguna, role, dan menu akun.

Jangan menampilkan terlalu banyak ikon tanpa label atau tooltip.

### 6.3 KPI cards

Kartu KPI yang disarankan:
- Total permohonan.
- Permohonan baru.
- Dalam proses.
- Menunggu persetujuan.
- Mendekati/melewati SLA.
- Izin diterbitkan.

Setiap kartu menampilkan label, angka, periode atau konteks, dan tautan menuju daftar terfilter. Gunakan gold hanya sebagai aksen kecil, bukan latar seluruh kartu.

### 6.4 Tabel permohonan

Kolom yang dapat digunakan:
- Nomor registrasi.
- Nama pemohon/organisasi.
- Jenis izin.
- Tanggal pengajuan.
- Petugas/penanggung jawab.
- Status.
- Sisa SLA.
- Aksi.

Fitur:
- Search, filter, sort, pagination.
- Filter status dan rentang tanggal.
- Pilih kolom bila diperlukan.
- Bulk action hanya untuk tindakan yang aman dan memiliki konfirmasi.
- Header tabel jelas; row hover lembut.
- Status menggunakan badge berlabel.
- Aksi utama terlihat; aksi sekunder masuk menu.

### 6.5 Status permohonan

Gunakan label konsisten, misalnya:
- Draft
- Diajukan
- Pemeriksaan Administrasi
- Perlu Perbaikan
- Verifikasi Teknis
- Menunggu Persetujuan
- Disetujui
- Izin Diterbitkan
- Ditolak
- Dicabut / Kedaluwarsa

Status final dan status proses harus dibedakan. Definisi status wajib mengikuti SOP dan regulasi organisasi.

### 6.6 Formulir

- Label berada di atas field.
- Tandai field wajib dengan jelas.
- Helper text menjelaskan format atau dokumen yang diperlukan.
- Validasi inline dekat field terkait.
- Kelompokkan formulir panjang dalam section atau stepper.
- Simpan draft otomatis hanya bila mekanisme penyimpanan dan indikatornya jelas.
- Jangan menghapus input pengguna ketika validasi gagal.
- Tampilkan ringkasan kesalahan di bagian atas untuk formulir panjang.

### 6.7 Detail permohonan

Layout dua kolom pada desktop:
- **Kolom utama:** informasi pemohon, data izin, dokumen, catatan, dan riwayat.
- **Kolom samping:** status, SLA, penanggung jawab, tindakan yang tersedia.

Gunakan timeline untuk perjalanan permohonan. Setiap aktivitas menampilkan pelaku, waktu, tindakan, dan catatan.

### 6.8 Approval center

- Tampilkan ringkasan permohonan sebelum tombol keputusan.
- Aksi setujui/tolak harus memiliki konfirmasi.
- Penolakan atau permintaan perbaikan wajib menyediakan alasan.
- Catat identitas approver, waktu, keputusan, dan versi dokumen.
- Tanda tangan elektronik hanya melalui penyedia/layanan yang sah dan terintegrasi sesuai ketentuan.

### 6.9 Document center

- Daftar dokumen dengan nama, jenis, versi, ukuran, tanggal unggah, dan status validasi.
- Preview PDF di panel atau dialog.
- Tampilkan alasan dokumen tidak valid.
- Batasi tipe dan ukuran file; lakukan validasi server-side dan pemindaian keamanan.
- Simpan metadata dan audit akses dokumen.

## 7. Contoh token CSS

```css
:root {
  /* Brand */
  --color-navy-950: #101B32;
  --color-navy-900: #17243D;
  --color-navy-800: #243550;
  --color-champagne-500: #C5A46D;
  --color-champagne-600: #A9854D;

  /* Surface */
  --color-ivory-50: #F7F5EF;
  --color-white: #FFFFFF;
  --color-slate-100: #F2F4F7;
  --color-slate-300: #D0D5DD;

  /* Text */
  --color-text-primary: #101828;
  --color-text-secondary: #475467;
  --color-text-muted: #667085;

  /* Semantic */
  --color-success: #027A48;
  --color-info: #175CD3;
  --color-warning: #B54708;
  --color-danger: #B42318;

  /* Shape and spacing */
  --radius-card: 12px;
  --radius-control: 9px;
  --shadow-card: 0 2px 10px rgba(16, 27, 50, 0.05);
  --border-default: 1px solid #EAECF0;
}

body {
  color: var(--color-text-primary);
  background: var(--color-ivory-50);
  font-family: Inter, system-ui, sans-serif;
}

.app-sidebar {
  color: #FFFFFF;
  background: var(--color-navy-950);
}

.app-sidebar .nav-link.active {
  color: #FFFFFF;
  background: var(--color-navy-900);
  border-left: 3px solid var(--color-champagne-500);
}

.surface-card {
  background: var(--color-white);
  border: var(--border-default);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}
```

## 8. Contoh komposisi dashboard

### Header

**Selamat pagi, [Nama Petugas]**  
Ringkasan pekerjaan dan status pelayanan perizinan hari ini.

Tombol utama: `+ Permohonan Baru` (hanya jika role berwenang).

### KPI

| KPI | Contoh nilai ilustratif |
|---|---:|
| Total permohonan | 1.284 |
| Permohonan baru | 48 |
| Dalam proses | 216 |
| Menunggu persetujuan | 32 |
| Mendekati SLA | 14 |
| Izin diterbitkan bulan ini | 173 |

Angka di atas hanya contoh untuk mockup, bukan data operasional.

### Area analitik

- Tren permohonan masuk dan selesai.
- Distribusi berdasarkan jenis izin.
- Beban kerja per unit/petugas.
- Kepatuhan SLA.
- Aktivitas terbaru.

Chart harus memiliki label, rentang tanggal, satuan, dan tabel/alternatif tekstual bila dibutuhkan.

## 9. Responsif dan mobile

### Breakpoint acuan

- Mobile: `< 576px`
- Tablet: `576–991px`
- Desktop: `992–1199px`
- Wide desktop: `>= 1200px`

### Aturan mobile

- Sidebar menjadi drawer.
- KPI menjadi satu atau dua kolom.
- Tabel lebar berubah menjadi daftar kartu atau menyediakan horizontal scroll yang jelas.
- Tombol tindakan utama mudah dijangkau.
- Form menggunakan satu kolom.
- Dialog panjang berubah menjadi halaman/panel penuh.
- Jangan menyembunyikan status, SLA, atau tindakan penting.

## 10. Motion dan micro-interaction

Gunakan animasi ringan dan fungsional:
- Hover tombol dan menu: 120–180 ms.
- Drawer/sidebar: 180–240 ms.
- Skeleton loading untuk proses pemuatan.
- Toast untuk hasil tindakan.
- Progress indicator untuk upload dan proses yang memerlukan waktu.

Hormati preferensi `prefers-reduced-motion`. Hindari parallax, animasi dekoratif terus-menerus, dan transisi yang memperlambat kerja.

## 11. Aksesibilitas, keamanan, dan kepercayaan

- Kontras teks dan kontrol memenuhi WCAG 2.2 AA sebagai target.
- Semua fungsi dapat digunakan dengan keyboard.
- Fokus keyboard terlihat jelas.
- Label form terhubung dengan input.
- Pesan error menjelaskan cara memperbaiki.
- Jangan menyampaikan status hanya dengan warna.
- Terapkan role-based access control dan prinsip least privilege.
- Lindungi data pribadi dan dokumen pemohon.
- Audit tindakan penting dan perubahan data.
- Gunakan HTTPS, session management yang aman, CSRF protection, validasi server-side, serta kebijakan retensi data.
- Tampilkan data sensitif hanya kepada pengguna yang berwenang.

## 12. Panduan implementasi frontend

Dokumen ini adalah design system, bukan instruksi untuk mengganti seluruh stack aplikasi. Terapkan secara bertahap pada komponen bersama.

Rekomendasi:
- Gunakan design token sebagai sumber warna, spacing, radius, dan shadow.
- Buat komponen reusable: `AppSidebar`, `Topbar`, `PageHeader`, `KpiCard`, `StatusBadge`, `DataTable`, `FormField`, `Timeline`, `DocumentPreview`, dan `ConfirmDialog`.
- Pertahankan pola navigasi dan perilaku aplikasi yang sudah berjalan.
- Bila menggunakan Django + Bootstrap, gunakan Bootstrap sebagai fondasi layout dan komponen, lalu override melalui stylesheet tema terpisah.
- Bila menggunakan HTMX, pastikan komponen hasil swap tetap memiliki state, event, dan aksesibilitas yang konsisten.
- Jangan menambahkan dependensi frontend hanya untuk efek visual kecil.
- Pastikan tema dapat digunakan dengan data nyata, loading, empty state, error state, dan permission state.

### Struktur file tema yang disarankan

```text
static/
└── css/
    └── themes/
        └── executive-navy-gold.css
```

Pisahkan token dari styling komponen jika skala aplikasi berkembang:

```text
static/css/themes/
├── executive-navy-gold/
│   ├── tokens.css
│   ├── layout.css
│   ├── components.css
│   └── utilities.css
```

## 13. Checklist penerimaan desain

- [ ] Sidebar navy konsisten di semua modul.
- [ ] Champagne Gold digunakan sebagai aksen, bukan warna dominan.
- [ ] Area kerja terang dan nyaman dibaca.
- [ ] Hierarki heading dan tipografi konsisten.
- [ ] Semua status memiliki label yang jelas.
- [ ] Tabel mendukung pencarian, filter, sorting, dan pagination.
- [ ] Form memiliki validasi dan pesan error yang mudah dipahami.
- [ ] Workflow menunjukkan tahap, penanggung jawab, dan waktu.
- [ ] Approval memiliki konfirmasi dan audit trail.
- [ ] Empty, loading, error, dan unauthorized states tersedia.
- [ ] Tampilan mobile dapat digunakan tanpa kehilangan fungsi penting.
- [ ] Keyboard navigation dan focus state berfungsi.
- [ ] Kontras warna diperiksa.
- [ ] Data contoh/mockup tidak tertukar dengan data produksi.

## 14. Prompt singkat untuk AI coding agent

Gunakan instruksi berikut saat menerapkan tema pada aplikasi:

> Terapkan design system **Executive Navy & Champagne Gold** berdasarkan dokumen ini ke aplikasi perizinan yang sudah ada. Lakukan audit struktur template, stylesheet, komponen, dan navigasi terlebih dahulu. Pertahankan seluruh business logic, URL, permission, validasi, integrasi, dan perilaku workflow. Jangan mengubah skema database atau menghapus fitur demi perubahan visual. Implementasikan tema melalui design tokens dan reusable components. Prioritaskan hybrid layout: sidebar navy gelap, topbar putih, canvas ivory, surface putih, dan champagne gold sebagai aksen terbatas. Pastikan tabel, formulir, status, timeline, approval, document preview, notifikasi, empty/loading/error states, serta tampilan mobile konsisten. Uji semua role dan halaman penting setelah perubahan, termasuk keyboard navigation dan kontras. Laporkan file yang diubah, risiko, dan hasil pengujian.

---

**Arah akhir:** aplikasi harus terasa seperti platform layanan perizinan enterprise yang resmi dan premium—tenang, rapi, mudah dipercaya, dan cepat digunakan. Jangan menjadikan gold sebagai dekorasi berlebihan; kekuatan desain ini berasal dari proporsi navy, ivory, whitespace, tipografi, dan detail yang konsisten.
