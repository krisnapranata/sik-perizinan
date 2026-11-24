# PANDU LOTIM — Portal Data Perizinan DPMPTSP Lombok Timur

Portal satu pintu: database perizinan 2021–2025, pengajuan izin KKPR nonberusaha online,
informasi investasi, serta data dan analisis. Sistem pengelolanya bernama SIDE SMART.

**Acuan pengembangan: `PRD_Portal_Data_Perizinan_PANDU_LOTIM.md`.** `PRD.md` adalah PRD lama
(alur verifikasi Kasi → Kabid → Kadis) dan hanya disimpan sebagai riwayat; bila bertentangan,
ikuti PRD PANDU LOTIM. Bagian di bawah masih menjelaskan fitur yang sudah ada dari PRD lama.

```
Browser ──HTTPS 443──> Nginx Proxy Manager ──> sik_nginx :80 (host 8040) ──> sik_web Gunicorn :8000 ──> sik_db MariaDB 10.11
```

## Struktur

| Lokasi | Isi |
| --- | --- |
| `config/` | Settings dan URL utama |
| `core/` | Log audit, validasi unggahan, pengiriman berkas privat, `/sehat/` |
| `akun/` | Pengguna, peran, pemohon, registrasi, layanan loket, perintah `buat_akun_demo` |
| `perizinan/` | Modul 2: katalog izin, permohonan KKPR, verifikasi petugas, penilaian instansi teknis, nomor izin otomatis, dokumen izin ber-QR, cek status, notifikasi, pengingat SLA |
| `laporan/` | Laporan bulanan dan ekspor Excel/PDF |
| `basisdata/` | Modul 1 dan 4 PRD PANDU LOTIM: database OSS-RBA (impor ekspor OSS), database NonOSS, statistik publik `/statistik/`, ekspor dengan kop |
| `investasi/` | Modul 3: Pusat Informasi Investasi `/investasi/` (potensi, peluang, proyek siap tawar) dengan peta Google Maps |
| `templates/`, `static/` | Tampilan (font Geist dan ikon Lucide disimpan lokal, tanpa CDN) |
| `deploy/`, `scripts/` | Nginx internal, contoh env produksi, skrip cadangan |

Aturan penting di kode:

- Perubahan status hanya lewat `perizinan/services.py`.
- Aturan akses hanya di `perizinan/permissions.py` dan `akun/permissions.py`.
- CSS/JS dimuat dengan `{% load aset %}{% aset 'css/sik.css' %}` (bukan `{% static %}`), yang menambahkan
  `?v=<hash isi berkas>`. Nginx menyimpan URL ber-`v` selama setahun, jadi browser langsung memakai
  berkas baru setelah deploy tanpa perlu menaikkan nomor versi manual.
- Berkas tidak punya URL publik. Django memeriksa izin, lalu Nginx mengirim isinya lewat
  `X-Accel-Redirect` ke lokasi internal `/_berkas/`.

## Database Perizinan (Rilis 1)

- **Impor OSS-RBA**: menu *Impor OSS* (`/database/oss/impor/`). Id Proyek adalah kunci, jadi ekspor yang
  sama aman diunggah ulang. Kolom dicocokkan lewat `ALIAS` di `basisdata/impor.py`; bila OSS mengganti
  nama kolom, tambahkan alias di sana.
- **Tahun rekap** ditentukan di satu tempat, `tahun_proyek()` di `basisdata/models.py`.
- **Sektor KAK** diisi otomatis dari dua digit awal KBLI; koreksi per KBLI di `/admin/` → KBLI.
- **Kop ekspor** diatur lewat `KOP_INSTANSI`, `KOP_DINAS`, `KOP_ALAMAT` di `.env`.
- Data rinci hanya untuk Petugas DPMPTSP (PRD DB-08). Pimpinan dan publik hanya melihat agregat.
- Login dikunci 15 menit setelah 5 kali gagal per akun (30 per alamat IP).

## Pusat Informasi Investasi (Modul 3)

Halaman publik `/investasi/` (tanpa login): daftar dengan filter sektor, kecamatan, dan tingkat kesiapan
(IN-01), profil lengkap (IN-02), dan peta lokasi Google Maps (IN-03). Admin Sistem mengisi kontennya di
`/admin/` → **Potensi dan peluang investasi** (IN-07). Titik lokasi cukup ditempel dari Google Maps:
klik kanan titik di peta, klik angka koordinat untuk menyalin, lalu tempel ke kolom *Titik koordinat*.
Data minimum mengikuti PRD 7.1: peluang wajib punya estimasi investasi dan potensi pasar, sedangkan proyek
siap tawar juga wajib punya luas lahan dan kontak. Untuk menurunkan konten dari portal, matikan *tampil*.

Peta bekerja tanpa kunci API: setiap profil memakai embed Google Maps, dan di halaman daftar tombol
**Lihat di peta** memindahkan peta ke titik yang dipilih. Isi `GOOGLE_MAPS_API_KEY` supaya semua
titik tampil sekaligus di satu peta. Aktifkan Maps JavaScript API dan Maps Embed API, lalu batasi kunci
dengan HTTP referrer ke domain portal.

Belum dibuat: foto dan dokumen kajian per proyek, unduh profil PDF (IN-04), formulir minat investor
(IN-05), dan versi bahasa Inggris (IN-06).

## Pengembangan lokal

Ubuntu perlu: `sudo apt install python3-venv pkg-config libmariadb-dev build-essential`.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
sed -i 's/^DJANGO_DEBUG=0/DJANGO_DEBUG=1/' .env   # tanpa ini settings menolak jalan
sudo bash scripts/setup-mariadb.sh
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
python manage.py test          # butuh MariaDB; user sik punya hak atas test_sik
```

`manage.py` membaca `.env` otomatis. Variabel environment yang sudah di-set tetap didahulukan.

Login memakai **email**, bukan username.

### Akun demo

Untuk mencoba semua peran tanpa membuat akun satu per satu:

```bash
python manage.py buat_akun_demo
```

Perintah ini membuat akun di bawah, satu permohonan KKPR Nonberusaha contoh yang sudah diajukan,
dan tiga contoh potensi investasi bertanda "(contoh)" untuk mencoba peta.
Aman dijalankan ulang: akun yang sudah ada tidak dibuat ganda, tetapi passwordnya disetel ulang ke `demo123`. Perintah ini **menolak berjalan bila
`DJANGO_DEBUG` bukan 1**, jadi tidak bisa membuat akun berpassword lemah di server produksi.

| Email | Password | Peran (PRD bagian 3) |
| --- | --- | --- |
| `pemohon@sik.test` | `demo123` | Pemohon |
| `petugas@sik.test` | `demo123` | Petugas DPMPTSP (front office dan verifikator) |
| `pupr@sik.test` | `demo123` | Instansi Teknis (Dinas PUPR) |
| `pimpinan@sik.test` | `demo123` | Pimpinan (dashboard dan laporan) |
| `admin@sik.test` | `demo123` | Admin Sistem (panel admin) |

### Mencoba alur sampai izin terbit (PRD 6.4)

Buka `http://localhost:8000/akun/masuk/`. Untuk berganti akun, klik ikon keluar di pojok kiri
bawah sidebar.

1. **Petugas** (`petugas@sik.test`): buka **Antrean saya**, pilih permohonan, tandai setiap
   dokumen **Sesuai** (atau **Tidak sesuai** dengan catatan, lalu **Minta perbaikan**).
   Jenis izin yang perlu kajian teknis: **Teruskan ke instansi teknis**. Yang tidak: **Setujui**.
2. **Instansi teknis** (`pupr@sik.test`): buka permohonan dari **Antrean saya**, pilih hasil
   **Memenuhi** (permohonan disetujui) atau **Tidak memenuhi** (ditolak), isi rekomendasi.
3. **Petugas**: buka permohonan yang **Disetujui**, klik **Terbitkan izin**. Nomor izin dibuat
   otomatis (format `FORMAT_NOMOR_IZIN` di `.env`) dan dokumen izin ber-QR dibuat sistem. Pindaian
   yang sudah ditandatangani bisa diunggah sesudahnya.
4. **Pemohon**: izin tampil terbit dan dokumennya bisa diunduh. QR di dokumen membuka halaman
   `/verifikasi/<kode>/` untuk cek keaslian. Izin yang terbit otomatis masuk Database NonOSS.

Pendaftaran mandiri memakai **kode OTP 6 digit** yang dikirim ke email (berlaku 15 menit, maksimal
5 kali salah). Selama `EMAIL_HOST` kosong, email (OTP, notifikasi status) hanya tercetak di
terminal `runserver`; salin kodenya dari sana.

Petugas juga melayani pemohon yang datang ke kantor lewat **Layanan berbantuan**.

### Pengingat batas waktu layanan (IZ-10)

Setiap jenis izin punya batas layanan (hari, diatur di `/admin/`). Jalankan harian lewat cron:

```cron
0 7 * * 1-5 docker exec sik_web python manage.py pengingat_sla
```

## Deployment di server (pola SIMBAK / E-Office)

SIK berjalan berdampingan dengan aplikasi lain di belakang **Nginx Proxy Manager** (NPM, container
`proxy-npm-1`). NPM memegang domain dan HTTPS; SIK punya container sendiri dengan awalan `sik`:

| Container | Isi | Port host |
| --- | --- | --- |
| `sik_db` | MariaDB 10.11, volume `sik_db_data` | - |
| `sik_web` | Django + Gunicorn :8000 (migrate dan collectstatic saat start) | - |
| `sik_nginx` | Nginx internal: static, berkas pemohon via X-Accel, batas login | `8040` (`SIK_PORT`) |

```bash
cd /srv && git clone https://github.com/krisnapranata/sik-perizinan.git && cd sik-perizinan
cp deploy/env.production.contoh .env.production && nano .env.production   # SECRET_KEY, domain, DB, SMTP
cp deploy/env.db.contoh .env.db && nano .env.db                            # sandi sama dengan DB_PASSWORD
chmod 600 .env.production .env.db
docker inspect proxy-npm-1 -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
#   bila bukan proxy_default: echo NPM_NETWORK=<nama> > .env
docker compose up -d --build
docker compose ps                                  # sik_db dan sik_web "healthy"
curl -fsS http://127.0.0.1:8040/sehat/
docker compose exec web python manage.py createsuperuser
```

Di NPM buat **Proxy Host**: domain → scheme `http`, host `sik_nginx`, port `80`. Tab SSL: minta
sertifikat Let's Encrypt, aktifkan **Force SSL** dan **HSTS**. Tab Advanced:
`client_max_body_size 30m;`. Domain yang sama harus ada di `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CSRF_TRUSTED_ORIGINS` (dengan `https://`), dan `SITUS_URL`.

Memperbarui: `git pull && docker compose up -d --build`. **Cadangkan database dulu** bila pembaruan
memuat migrasi. Jangan jalankan `docker compose down -v` karena menghapus volume database dan berkas.

Setelah masuk, Admin Sistem membuat akun Petugas DPMPTSP, Pimpinan, dan Instansi Teknis di
`/admin/` (akun instansi wajib memilih instansinya), lalu memeriksa instansi teknis, jenis izin,
daftar syarat KKPR, dan template email.
Untuk memindahkan banyak akun sekaligus dari sistem lama, buka **Pengguna → Impor CSV / Excel**
(`/admin/akun/user/impor/`). Berkas `.csv` atau `.xlsx` berisi kolom `email`, `password`, `nama`,
`peran`, dan data profil pemohon; template bisa diunduh di halaman itu. Password yang kosong diisi
password default (`IMPOR_PASSWORD_DEFAULT` di `.env.production`, bisa diubah saat mengunggah).
Data awalnya berasal dari PRD; daftar syarat final mengikuti ketetapan dinas.

Tanpa `EMAIL_HOST`, email hanya tercetak di log, sehingga pemohon mandiri tidak menerima kode OTP
dan tidak bisa mengaktifkan akun. Isi SMTP sebelum go-live.
Langkah membuat sandi aplikasi Gmail atau memakai email dinas ada di
[docs/PANDUAN_EMAIL.md](docs/PANDUAN_EMAIL.md).

## Cadangan

`scripts/backup.sh` mencadangkan database (dari `sik_db`) dan berkas pemohon (volume media lewat
`sik_web`). Tujuan harus berada di disk lain atau mount jaringan. Contoh crontab sesuai PRD
(database harian, berkas mingguan):

```cron
0 1 * * * cd /srv/sik-perizinan && bash scripts/backup.sh /mnt/cadangan/sik db
0 2 * * 0 cd /srv/sik-perizinan && bash scripts/backup.sh /mnt/cadangan/sik berkas
```

Pemulihan:

```bash
gunzip -c sik-<waktu>.sql.gz | docker exec -i sik_db sh -c 'MYSQL_PWD="$MARIADB_PASSWORD" mariadb -u "$MARIADB_USER" "$MARIADB_DATABASE"'
docker exec -i sik_web tar -xzf - -C /app < media-<waktu>.tar.gz
```

## Catatan keamanan

- `.env.production` dan `.env.db` berisi rahasia: tidak di-commit, izin berkas `600`.
- `sik_db` dan `sik_web` tidak membuka port ke host; hanya `sik_nginx` (8040). Port 8040 cukup
  dijangkau NPM, jadi tutup dari luar di firewall (yang dibuka hanya 80 dan 443 milik NPM).
- `sik_nginx` hanya mempercayai `X-Real-IP` dari jaringan privat (NPM/Docker), sehingga batas
  percobaan login dihitung per IP asli pengguna.
- User `sik`/`sik` di `.env.example` hanya untuk mesin pengembang (`scripts/setup-mariadb.sh`).
- Riwayat verifikasi dan log audit tidak bisa diubah atau dihapus dari aplikasi.
- Jangan menyalin database pengembangan ke server. Bila terpaksa, hapus dulu semua akun
  `@sik.test` dari akun demo.
