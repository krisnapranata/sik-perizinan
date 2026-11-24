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

## Panduan aplikasi (khusus Admin Sistem)

Menu **Panduan aplikasi** (`/panduan/`) berisi penjelasan semua fitur, diagram alur permohonan, dan
skenario demo untuk presentasi atau serah terima. Hanya Admin Sistem yang bisa membukanya; peran lain
mendapat 403. Naskahnya ada di `templates/core/panduan.html`; perbarui di sana bila fitur berubah.
Tombol **Cetak / simpan PDF** mencetak panduan tanpa sidebar.

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
Aman dijalankan ulang: akun yang sudah ada tidak dibuat ganda, tetapi passwordnya disetel ulang.
Di komputer pengembang (`DJANGO_DEBUG=1`) password semua akun demo `demo123`. Di server production
password wajib ditentukan sendiri (lihat langkah 5b di bagian Deployment).

| Email | Password (lokal) | Peran (PRD bagian 3) |
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

### 0. Persiapan

- Domain/subdomain (mis. `perizinan.lomboktimurkab.go.id`) sudah diarahkan (record A) ke IP server.
- Akun email pengirim untuk OTP sudah siap ([docs/PANDUAN_EMAIL.md](docs/PANDUAN_EMAIL.md)).
- Port 8040 masih kosong: `ss -ltn | grep 8040` tidak menampilkan apa pun. Bila terpakai, pakai port
  lain lewat `SIK_PORT=<port>` di berkas `.env` (folder ini).

### 1. Ambil kode

```bash
cd /srv
git clone https://github.com/krisnapranata/sik-perizinan.git
cd sik-perizinan
```

Bila repo privat, git meminta login: isi username GitHub dan, untuk password, **Personal Access Token**
(bukan password akun GitHub).

### 2. Siapkan berkas rahasia

```bash
cp deploy/env.production.contoh .env.production
cp deploy/env.db.contoh .env.db
python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # untuk DJANGO_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # untuk sandi database
nano .env.db
nano .env.production
chmod 600 .env.production .env.db
```

`.env.db`: isi `MARIADB_PASSWORD` dan `MARIADB_ROOT_PASSWORD` dengan sandi acak.

`.env.production`:

| Variabel | Isi |
| --- | --- |
| `DJANGO_SECRET_KEY` | hasil perintah pertama di atas |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,<domain>` (127.0.0.1 dan localhost wajib tetap ada untuk healthcheck) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://<domain>` |
| `SITUS_URL` | `https://<domain>` (dipakai tautan di email dan QR dokumen izin) |
| `DB_PASSWORD` | **sama persis** dengan `MARIADB_PASSWORD` di `.env.db` |
| `EMAIL_*` | sesuai [docs/PANDUAN_EMAIL.md](docs/PANDUAN_EMAIL.md) |
| `IMPOR_PASSWORD_DEFAULT` | password awal pengguna hasil impor (wajib diganti saat pertama masuk) |
| `GOOGLE_MAPS_API_KEY` | boleh kosong (lihat Pusat Informasi Investasi) |

`.env.production` dan `.env.db` tidak pernah di-commit (sudah ada di `.gitignore`).

### 3. Cek nama network NPM

```bash
docker inspect proxy-npm-1 -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
```

Bila hasilnya `proxy_default`, tidak perlu apa-apa. Bila lain: `echo NPM_NETWORK=<nama_network> > .env`.

### 4. Jalankan

```bash
docker compose up -d --build
docker compose ps                        # sik_db dan sik_web "healthy", sik_nginx "Up"
curl -fsS http://127.0.0.1:8040/sehat/   # {"status": "ok"}
docker compose logs --tail=50 web        # migrasi OK, gunicorn jalan, tanpa traceback
```

Migrasi berjalan otomatis dan mengisi data awal: kecamatan, instansi teknis, jenis izin KKPR beserta
syaratnya, dan template email.

### 5. Buat Admin Sistem pertama

```bash
docker compose exec web python manage.py createsuperuser
```

Isi email, nama, dan password; akun ini otomatis berperan Admin Sistem. Jangan menjalankan
`buat_akun_demo` di server (perintah itu menolak berjalan bila `DJANGO_DEBUG` bukan 1).

### 5b. Data demo di server (opsional, untuk presentasi)

```bash
docker compose exec web python manage.py buat_akun_demo
```

Perintah ini menanyakan password untuk **semua** akun demo (tidak tampil di layar), lalu membuat akun
`pemohon@`, `petugas@`, `pupr@`, `pimpinan@`, dan `admin@sik.test`, satu permohonan KKPR contoh, dan tiga
contoh potensi investasi bertanda "(contoh)". Masuk ke `https://<domain>/akun/masuk/` dengan email itu
dan password yang baru Anda ketik.

- `demo123` dan password lemah ditolak: `demo123` tertulis di README publik, dan `admin@sik.test`
  berperan Admin Sistem.
- Contoh investasi langsung tampil di halaman publik `/investasi/`, dan email notifikasi permohonan
  contoh dikirim ke alamat `@sik.test` yang tidak ada (email itu memantul ke kotak surat pengirim).
- Setelah presentasi: nonaktifkan akun `@sik.test` di **Pengaturan sistem → Pengguna** (hapus centang
  *Aktif*), dan hapus centang **Tampil di portal** pada contoh investasi.

### 6. Uji email

```bash
docker compose exec web python manage.py sendtestemail alamat.anda@contoh.com
```

Bila gagal, cocokkan pesan galatnya dengan tabel *Masalah umum* di
[docs/PANDUAN_EMAIL.md](docs/PANDUAN_EMAIL.md).

### 7. Pasang domain di Nginx Proxy Manager

Ikuti bagian **[Nginx Proxy Manager (domain dan HTTPS)](#nginx-proxy-manager-domain-dan-https)** di
bawah. Ringkasnya: Proxy Host `<domain>` → `http` `sik_nginx` port `80`, sertifikat Let's Encrypt
dengan Force SSL, dan `client_max_body_size 30m;` di tab Advanced. Setelah itu buka `https://<domain>`
dan masuk dengan akun admin tadi.

### 8. Pengisian awal oleh Admin Sistem

1. **Pengaturan sistem → Pengguna**: buat akun Petugas DPMPTSP, Pimpinan, dan Instansi Teknis (akun
   instansi wajib memilih instansinya). Untuk banyak akun sekaligus, buka **Impor pengguna**
   (`/admin/akun/user/impor/`): berkas `.csv`/`.xlsx` berisi kolom `email`, `password`, `nama`, `peran`,
   dan data profil pemohon; templatnya bisa diunduh di halaman itu. Password kosong diisi
   `IMPOR_PASSWORD_DEFAULT` (bisa diubah saat mengunggah).
2. Periksa **Jenis izin** (syarat, batas waktu layanan, perlu penilaian teknis) dan **Template email**.
   Data awal berasal dari PRD; daftar syarat final mengikuti ketetapan dinas.
3. Isi **Potensi dan peluang investasi** beserta titik koordinatnya.
4. Menu **Panduan aplikasi** menjelaskan setiap fitur untuk presentasi dan serah terima.

Tanpa `EMAIL_HOST`, email hanya tercetak di log: pemohon mandiri tidak menerima kode OTP dan tidak bisa
mengaktifkan akun. Isi SMTP sebelum go-live.

### 9. Jadwal otomatis (cron di server)

`crontab -e`, lalu tambahkan:

```cron
0 7 * * 1-5 docker exec sik_web python manage.py pengingat_sla
0 1 * * * cd /srv/sik-perizinan && bash scripts/backup.sh /mnt/cadangan/sik db
0 2 * * 0 cd /srv/sik-perizinan && bash scripts/backup.sh /mnt/cadangan/sik berkas
```

Ganti `/mnt/cadangan/sik` dengan folder di disk lain atau mount jaringan, bukan disk yang sama dengan
server. Penjelasan dan cara pemulihan ada di bagian **Cadangan**.

### Memperbarui aplikasi

```bash
cd /srv/sik-perizinan
bash scripts/backup.sh /mnt/cadangan/sik db   # cadangkan dulu bila pembaruan memuat migrasi
git pull && docker compose up -d --build
docker compose ps                             # pastikan kembali "healthy"
```

Setelah mengubah `.env.production`, jalankan `docker compose up -d web` (perintah `restart` tidak
membaca ulang berkas env). **Jangan pernah** menjalankan `docker compose down -v`: perintah itu
menghapus volume database dan semua berkas pemohon.

## Nginx Proxy Manager (domain dan HTTPS)

Di server bersama, port 80 dan 443 dipegang oleh **Nginx Proxy Manager** (NPM, container `proxy-npm-1`),
sama seperti SIMBAK dan E-Office. NPM menerima semua request dari internet, memasang sertifikat HTTPS,
lalu meneruskannya ke Nginx internal SIK:

```
Browser ──HTTPS 443──> proxy-npm-1 ──http, network proxy_default──> sik_nginx:80 ──> sik_web:8000
```

`sik_nginx` bergabung ke network NPM (`proxy_default`) sehingga NPM memanggilnya dengan **nama
container**, bukan IP. Port host 8040 hanya untuk uji dari server sendiri; tutup dari luar di firewall.

### Sebelum membuat Proxy Host

1. **DNS sudah mengarah ke server.** Hasil perintah ini harus IP publik server:
   ```bash
   dig +short perizinan.lomboktimurkab.go.id     # atau: nslookup perizinan.lomboktimurkab.go.id
   ```
   Perubahan DNS bisa butuh beberapa menit sampai beberapa jam. Let's Encrypt gagal selama DNS belum benar.
2. **Port 80 dan 443 server terbuka dari internet.** Let's Encrypt memverifikasi domain lewat port 80.
3. **`sik_nginx` bisa dicapai dari network NPM** (keduanya harus `200`/`{"status": "ok"}`):
   ```bash
   docker network inspect proxy_default --format '{{range .Containers}}{{.Name}} {{end}}' | tr ' ' '\n' | grep sik_nginx
   docker run --rm --network proxy_default curlimages/curl:8.10.1 -s http://sik_nginx/sehat/
   ```
   Ganti `proxy_default` bila nama network NPM berbeda (langkah 3 deployment).

### Membuat Proxy Host

1. Buka panel NPM di `http://<ip-server>:81` dan masuk dengan akun admin NPM yang sudah dipakai untuk
   aplikasi lain.
2. **Hosts → Proxy Hosts → Add Proxy Host**.
3. Tab **Details**:

   | Isian | Nilai |
   | --- | --- |
   | Domain Names | `perizinan.lomboktimurkab.go.id` (ketik, lalu Enter) |
   | Scheme | `http` (bukan https: HTTPS berhenti di NPM) |
   | Forward Hostname / IP | `sik_nginx` |
   | Forward Port | `80` |
   | Cache Assets | **mati** (cache CSS/JS sudah diatur `sik_nginx` lewat `?v=`) |
   | Block Common Exploits | nyala |
   | Websockets Support | mati (tidak dipakai) |
   | Access List | Publicly Accessible |

4. Tab **SSL**:
   - SSL Certificate: **Request a new SSL Certificate**.
   - Nyalakan **Force SSL** dan **HTTP/2 Support**.
   - Isi email untuk Let's Encrypt, centang persetujuan, lalu **Save**. Tunggu sampai sertifikat terbit
     (biasanya kurang dari satu menit).
   - **HSTS Enabled**: nyalakan **setelah** `https://<domain>` terbukti berjalan normal. Begitu aktif,
     browser pengunjung menolak versi http domain itu selama berbulan-bulan. Biarkan
     *HSTS Subdomains* mati kecuali semua subdomain juga sudah HTTPS.
5. Tab **Advanced**, kotak *Custom Nginx Configuration*:
   ```nginx
   client_max_body_size 30m;
   proxy_read_timeout 120s;
   proxy_send_timeout 120s;
   ```
   Baris pertama mengizinkan unggahan sampai 30 MB (sama dengan `sik_nginx`); dua baris berikutnya
   memberi waktu ekspor laporan Excel/PDF yang besar.
6. **Save**. Status Proxy Host harus **Online**.

NPM sudah meneruskan `X-Real-IP` dan `X-Forwarded-Proto` secara bawaan, jadi tidak perlu ditambah.
`sik_nginx` hanya mempercayai `X-Real-IP` dari jaringan privat, sehingga batas percobaan login dihitung
per IP asli pengunjung.

### Menguji

```bash
curl -sI http://perizinan.lomboktimurkab.go.id | head -3      # 301 ke https://
curl -s  https://perizinan.lomboktimurkab.go.id/sehat/         # {"status": "ok"}
curl -sI https://perizinan.lomboktimurkab.go.id/akun/masuk/ | head -1   # HTTP/2 200
```

Lalu dari browser: buka `https://<domain>`, pastikan ikon gembok tampil, masuk sebagai admin
(menguji CSRF dan cookie aman), dan coba unggah satu berkas PDF di permohonan (menguji batas unggah).

### Masalah umum

| Gejala | Penyebab | Perbaikan |
| --- | --- | --- |
| **502 Bad Gateway** | `sik_nginx` mati, tidak di network NPM, Forward Hostname salah ketik, atau Scheme diisi `https` | `docker compose ps`; jalankan uji `curl` dari network NPM di atas; pastikan Scheme `http`, hostname `sik_nginx`, port `80` |
| **504 Gateway Timeout** saat ekspor | Proses lebih lama dari batas waktu proxy | Pastikan `proxy_read_timeout 120s;` ada di tab Advanced |
| **413 Request Entity Too Large** | Batas unggah NPM masih bawaan Nginx (1 MB) | Tambahkan `client_max_body_size 30m;` di tab Advanced |
| **400 Bad Request** | Domain belum ada di `DJANGO_ALLOWED_HOSTS` | Tambahkan, lalu `docker compose up -d web` |
| **403 CSRF verification failed** saat login | `DJANGO_CSRF_TRUSTED_ORIGINS` tidak berisi `https://<domain>` | Tambahkan lengkap dengan `https://`, lalu `docker compose up -d web` |
| Sertifikat gagal terbit (*Internal Error*) | DNS belum mengarah ke server, port 80 tertutup, atau batas Let's Encrypt (terlalu sering mencoba) | Cek `dig`, buka port 80, tunggu sekitar satu jam sebelum mencoba lagi |
| Tautan di email/QR mengarah ke `localhost` | `SITUS_URL` belum diisi domain | Isi `SITUS_URL=https://<domain>`, lalu `docker compose up -d web` |
| Semua pengguna kena **429** bersamaan | `X-Real-IP` tidak sampai ke `sik_nginx` | Jangan menimpa header `X-Real-IP` di tab Advanced NPM |
| Tampilan lama setelah update | Cache Assets NPM menyala | Matikan Cache Assets di tab Details |

Log untuk melacak: `docker compose logs --tail=100 nginx web` (SIK) dan `docker logs --tail=100 proxy-npm-1` (NPM).

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
