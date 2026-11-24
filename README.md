# PANDU LOTIM — Portal Data Perizinan DPMPTSP Lombok Timur

Portal satu pintu: database perizinan 2021–2025, pengajuan izin KKPR nonberusaha online,
informasi investasi, serta data dan analisis. Sistem pengelolanya bernama SIDE SMART.

**Acuan pengembangan: `PRD_Portal_Data_Perizinan_PANDU_LOTIM.md`.** `PRD.md` adalah PRD lama
(alur verifikasi Kasi → Kabid → Kadis) dan hanya disimpan sebagai riwayat; bila bertentangan,
ikuti PRD PANDU LOTIM. Bagian di bawah masih menjelaskan fitur yang sudah ada dari PRD lama.

```
Browser ──HTTPS 443──> Nginx (container) ──> Gunicorn/Django (container, 127.0.0.1:8000) ──> MariaDB (host, 127.0.0.1:3306)
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
| `templates/`, `static/` | Tampilan (font Geist dan ikon Lucide disimpan lokal, tanpa CDN) |
| `nginx/`, `scripts/` | Reverse proxy dan skrip server |

Aturan penting di kode:

- Perubahan status hanya lewat `perizinan/services.py`.
- Aturan akses hanya di `perizinan/permissions.py` dan `akun/permissions.py`.
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

Perintah ini membuat akun di bawah dan satu permohonan KKPR Nonberusaha contoh yang sudah diajukan.
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
0 7 * * 1-5 cd /opt/sik && docker compose exec -T web python manage.py pengingat_sla
```

## Deployment di server

```bash
sudo bash scripts/install-docker.sh          # lewati otomatis bila Docker sudah ada
cp .env.example .env && nano .env            # isi SECRET_KEY, host, SITUS_URL, password, SMTP
sudo bash scripts/setup-mariadb.sh           # memakai DB_* dari .env
bash scripts/gen-selfsigned-cert.sh perizinan.example.go.id
sudo install -d -o 1000 -g 1000 media        # container berjalan sebagai uid 1000
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose logs -f web
```

Buka `https://<ip-atau-domain-server>`. Port 80, 443, dan 8000 di server harus kosong.

Setelah masuk, Admin Sistem membuat akun Petugas DPMPTSP, Pimpinan, dan Instansi Teknis di
`/admin/` (akun instansi wajib memilih instansinya), lalu memeriksa instansi teknis, jenis izin,
daftar syarat KKPR, dan template email.
Untuk memindahkan banyak akun sekaligus dari sistem lama, buka **Pengguna → Impor CSV / Excel**
(`/admin/akun/user/impor/`). Berkas `.csv` atau `.xlsx` berisi kolom `email`, `password`, `nama`,
`peran`, dan data profil pemohon; template bisa diunduh di halaman itu. Password yang kosong diisi
password default (`IMPOR_PASSWORD_DEFAULT` di `.env`, bisa diubah saat mengunggah). Data awalnya berasal dari PRD;
daftar syarat final mengikuti ketetapan dinas.

Tanpa `EMAIL_HOST`, email hanya tercetak di log, sehingga pemohon mandiri tidak menerima kode OTP
dan tidak bisa mengaktifkan akun. Isi SMTP sebelum go-live.

## Ganti ke Let's Encrypt (setelah domain mengarah ke server)

Hook membuat perpanjangan otomatis bekerja: certbot menghentikan Nginx sebentar agar port 80
bebas, menyalin sertifikat baru, lalu menyalakan Nginx lagi.

```bash
D=perizinan.example.go.id
sudo apt install -y certbot
sudo certbot certonly --standalone -d "$D" \
  --pre-hook  "docker compose -f $PWD/docker-compose.yml stop nginx" \
  --deploy-hook "cp /etc/letsencrypt/live/$D/fullchain.pem /etc/letsencrypt/live/$D/privkey.pem $PWD/nginx/certs/" \
  --post-hook "docker compose -f $PWD/docker-compose.yml start nginx"
```

## Cadangan

`scripts/backup.sh` mencadangkan database dan folder `media/`. Tujuan harus berada di disk lain
atau mount jaringan. Contoh crontab sesuai PRD (database harian, berkas mingguan):

```cron
0 1 * * * cd /opt/sik && bash scripts/backup.sh /mnt/cadangan/sik db
0 2 * * 0 cd /opt/sik && bash scripts/backup.sh /mnt/cadangan/sik berkas
```

Pemulihan: `gunzip -c sik-<waktu>.sql.gz | mariadb -u sik -p sik` dan
`tar -xzf media-<waktu>.tar.gz -C /opt/sik`. Mesin perlu klien `mariadb-dump`.

## Catatan keamanan

- User `sik`/`sik` hanya untuk pengembangan. Ganti `DB_PASSWORD` di `.env`, lalu jalankan ulang
  `scripts/setup-mariadb.sh`.
- MariaDB harus listen hanya di `127.0.0.1`. `setup-mariadb.sh` memberi peringatan bila tidak.
- Port yang dibuka di firewall hanya 80 dan 443.
- Riwayat verifikasi dan log audit tidak bisa diubah atau dihapus dari aplikasi.
- Jangan menyalin database pengembangan ke server. Bila terpaksa, hapus dulu semua akun
  `@sik.test` dari akun demo.
