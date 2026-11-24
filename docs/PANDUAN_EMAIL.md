# Panduan menyiapkan email pengirim (SMTP)

PANDU LOTIM mengirim email untuk:

- **Kode OTP pendaftaran**: pemohon yang mendaftar mandiri baru bisa mengaktifkan akun setelah
  memasukkan kode 6 digit dari email.
- Tautan atur ulang password.
- Notifikasi perubahan status permohonan.

Selama `EMAIL_HOST` kosong, email **tidak terkirim**. Isinya hanya tercetak di log. Akibatnya pemohon
tidak menerima OTP dan tidak bisa mendaftar. Lengkapi pengaturan ini sebelum go-live.

## Ringkasan pengaturan

Semua pengaturan ada di `.env.production` di server (di komputer pengembang: `.env`).

| Variabel | Isi |
| --- | --- |
| `EMAIL_HOST` | Alamat server SMTP, mis. `smtp.gmail.com` |
| `EMAIL_PORT` | `587` (STARTTLS) atau `465` (SSL) |
| `EMAIL_USE_TLS` | `1` untuk port 587 |
| `EMAIL_USE_SSL` | `1` untuk port 465 (lalu `EMAIL_USE_TLS` diabaikan) |
| `EMAIL_HOST_USER` | Alamat email lengkap untuk login SMTP |
| `EMAIL_HOST_PASSWORD` | **Sandi aplikasi** atau kunci SMTP, bukan sandi login biasa |
| `EMAIL_FROM` | Nama dan alamat pengirim yang dilihat pemohon |

Pilih **salah satu** dari tiga cara berikut.

---

## Cara A: Gmail atau Google Workspace dengan sandi aplikasi

Cara tercepat. Gunakan akun **khusus layanan**, misalnya `pandulotim.dpmptsp@gmail.com`, bukan
email pribadi pegawai. Kalau pegawai itu pindah tugas, akunnya tidak ikut pergi.

Batas kirim: sekitar 500 penerima per hari untuk Gmail biasa, dan sekitar 2.000 untuk
Google Workspace. Batas ini bisa berubah; cek halaman bantuan Google bila volume pendaftar tinggi.

### 1. Aktifkan Verifikasi 2 Langkah

Sandi aplikasi hanya tersedia bila Verifikasi 2 Langkah aktif.

1. Masuk ke akun Google yang akan dipakai, buka <https://myaccount.google.com/security>.
2. Di bagian **Cara Anda login ke Google**, pilih **Verifikasi 2 Langkah**, lalu ikuti langkahnya
   sampai statusnya **Aktif**. Pakai nomor HP dinas atau aplikasi autentikator yang bisa diakses
   lebih dari satu petugas.

### 2. Buat sandi aplikasi

1. Buka <https://myaccount.google.com/apppasswords> (login ulang bila diminta).
2. Di kolom **Nama aplikasi**, ketik `PANDU LOTIM`, lalu klik **Buat**.
3. Google menampilkan sandi **16 huruf** dalam empat kelompok, misalnya `abcd efgh ijkl mnop`.
   **Salin sekarang**, karena sandi ini tidak bisa ditampilkan lagi. Kalau lupa, hapus lalu buat
   yang baru.

Kalau menu sandi aplikasi tidak muncul:

- Verifikasi 2 Langkah belum aktif.
- Akun Google Workspace: admin domain mematikan fitur ini. Minta admin Workspace mengizinkannya.
- Akun memakai **Program Perlindungan Lanjutan**: sandi aplikasi tidak tersedia. Pakai akun lain.

### 3. Isi pengaturan

Tulis sandi **tanpa spasi**:

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_USE_SSL=0
EMAIL_HOST_USER=pandulotim.dpmptsp@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop
EMAIL_FROM=PANDU LOTIM DPMPTSP Lombok Timur <pandulotim.dpmptsp@gmail.com>
```

Gmail selalu memakai alamat `EMAIL_HOST_USER` sebagai pengirim. Nama tampilan di `EMAIL_FROM` tetap
dipakai, tetapi alamat lain di dalamnya akan diganti Gmail kecuali sudah didaftarkan di Gmail →
**Setelan → Akun → Kirim email sebagai**.

---

## Cara B: Email dinas domain go.id (hosting/cPanel)

Paling resmi bagi pemohon karena pengirimnya `@lomboktimurkab.go.id` atau domain dinas lain.
Mintalah ke pengelola domain (biasanya Diskominfo):

1. Satu kotak surat khusus, misalnya `noreply@<domain-dinas>` atau `pandulotim@<domain-dinas>`.
2. **Nama server SMTP**, **port**, dan jenis enkripsi. Di cPanel, cari di **Email Accounts →
   Connect Devices** (`Outgoing Server`).
3. Pastikan domain punya catatan **SPF** dan **DKIM** yang mengizinkan server itu, supaya email tidak
   masuk spam.

Contoh umum cPanel (sesuaikan dengan data dari pengelola):

```env
EMAIL_HOST=mail.<domain-dinas>
EMAIL_PORT=465
EMAIL_USE_SSL=1
EMAIL_USE_TLS=0
EMAIL_HOST_USER=pandulotim@<domain-dinas>
EMAIL_HOST_PASSWORD=<sandi kotak surat>
EMAIL_FROM=PANDU LOTIM DPMPTSP Lombok Timur <pandulotim@<domain-dinas>>
```

Kalau penyedia memberi port 587, pakai `EMAIL_PORT=587`, `EMAIL_USE_TLS=1`, dan `EMAIL_USE_SSL=0`.

---

## Cara C: Layanan email transaksional (Brevo, Mailgun, Amazon SES, dan sejenisnya)

Cocok bila volume tinggi atau Gmail sering membatasi pengiriman. Pola umumnya:

1. Daftar di layanan tersebut, lalu **verifikasi domain pengirim** dengan menambah catatan DNS
   (SPF, DKIM) sesuai petunjuk layanan.
2. Buat **kunci SMTP** (SMTP key / SMTP credentials) di dasbor layanan.
3. Isi `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER` (login SMTP dari dasbor, kadang bukan alamat
   email), dan `EMAIL_HOST_PASSWORD` (kunci SMTP) sesuai yang tertulis di dasbor.

Kuota gratis dan harga tiap layanan berubah; cek halaman harga resminya sebelum memilih.

---

## Menerapkan di server

```bash
cd /srv/sik-perizinan
nano .env.production            # isi variabel EMAIL_*
chmod 600 .env.production
docker compose up -d web        # buat ulang container agar membaca .env.production yang baru
```

`docker compose restart` **tidak** membaca ulang `.env.production`. Gunakan `docker compose up -d web`.

## Menguji

### 1. Kirim email uji

Ganti alamatnya dengan email Anda sendiri:

```bash
docker compose exec web python manage.py sendtestemail alamat.anda@contoh.com
```

Kalau tidak ada pesan galat dan email uji masuk (cek juga folder Spam), pengaturan sudah benar.
Kalau gagal, pesan galat langsung tampil di layar; cocokkan dengan tabel **Masalah umum** di bawah.

Di komputer pengembang: `python manage.py sendtestemail alamat.anda@contoh.com`.

### 2. Uji alur pendaftaran

1. Buka `https://<domain>/akun/daftar/` di jendela penyamaran (incognito).
2. Daftar dengan email yang bisa Anda buka.
3. Kode OTP 6 digit seharusnya masuk dalam satu menit. Masukkan kodenya; akun menjadi aktif.

Kalau OTP tidak datang, lihat log:

```bash
docker compose logs --tail=100 web | grep -i -A5 "sik.email"
```

Galat pengiriman tercatat sebagai `Email kode OTP ke <alamat> gagal dikirim.` beserta penyebabnya.

## Masalah umum

| Pesan / gejala | Penyebab | Perbaikan |
| --- | --- | --- |
| `535 5.7.8 Username and Password not accepted` (Gmail) | Memakai sandi login biasa, sandi aplikasi salah, atau masih ada spasi | Buat sandi aplikasi baru, tulis tanpa spasi |
| `535` di server lain | Login atau sandi salah, atau `EMAIL_HOST_USER` bukan alamat lengkap | Cek ulang dengan pengelola kotak surat |
| `SMTPServerDisconnected` / `Connection unexpectedly closed` | Port 465 dengan `EMAIL_USE_TLS=1` | Port 465 → `EMAIL_USE_SSL=1`, `EMAIL_USE_TLS=0` |
| `timed out` / `Connection refused` | Server memblokir koneksi keluar ke port SMTP, atau nama host salah | Uji dari server: `docker compose exec web python -c "import socket; socket.create_connection(('smtp.gmail.com', 587), 5); print('ok')"`. Kalau gagal, minta pengelola jaringan membuka port 587/465 keluar |
| `SSL: WRONG_VERSION_NUMBER` | Port 587 dengan `EMAIL_USE_SSL=1` | Port 587 → `EMAIL_USE_TLS=1`, `EMAIL_USE_SSL=0` |
| Email uji berhasil tetapi masuk Spam | Domain pengirim tanpa SPF/DKIM, atau alamat From tidak cocok dengan akun login | Pakai Cara B/C dengan SPF dan DKIM, atau samakan alamat di `EMAIL_FROM` dengan `EMAIL_HOST_USER` |
| `550 Daily user sending limit exceeded` | Batas harian Gmail habis | Tunggu 24 jam; untuk jangka panjang pindah ke Cara B atau C |
| OTP tidak datang, log tidak ada galat | `EMAIL_HOST` kosong sehingga email hanya dicetak di log | Isi `EMAIL_HOST`, lalu `docker compose up -d web` |

## Keamanan

- `EMAIL_HOST_PASSWORD` adalah rahasia. Simpan hanya di `.env.production` (izin `600`), jangan
  dikirim lewat chat, dan jangan di-commit ke git.
- Sandi aplikasi bisa dicabut kapan saja di <https://myaccount.google.com/apppasswords> tanpa
  mengganti sandi akun. Cabut dan buat baru bila sandi sempat terlihat orang lain atau petugas
  pengelola berganti.
- Catat siapa pemegang akun email layanan dan nomor HP pemulihannya di dokumen serah terima dinas.
