> **DIGANTIKAN** oleh `PRD_Portal_Data_Perizinan_PANDU_LOTIM.md` (17 Nov 2026). Dokumen ini hanya riwayat.

PRD Aplikasi Sistem Informasi dan Pendaftaran Perizinan DPMPTSP Lombok Timur
Nov 5, 2026 · @Krisna Pranata
Ringkasan dan latar belakang
Aplikasi ini mendigitalkan alur perizinan internal DPMPTSP Kabupaten Lombok Timur: pendaftaran pemohon, unggah syarat, verifikasi berjenjang Kasi → Kabid → Kadis, hingga penerbitan izin dan pelacakan status.
Saat ini alur di bagan "Mekanisme/Prosedur Perizinan Internal pada DPM PTSP" berjalan lewat dua jalur: layanan berbantuan di kantor DPMPTSP dan layanan mandiri dari rumah/HP. Keduanya bergantung pada aplikasi OSS untuk NIB dan izin, sementara verifikasi dokumen di DPMPTSP masih manual. Akibatnya pemohon sulit memantau status, dan dinas sulit mengukur beban serta lama proses.
Aplikasi ini melengkapi OSS, bukan menggantikannya. Ia mengelola antrean, berkas, dan verifikasi internal di sisi DPMPTSP, serta mencatat nomor NIB dan izin yang terbit di OSS.
Tujuan dan metrik keberhasilan
Target utamanya: setiap permohonan tercatat, bisa dilacak, dan setiap tahap verifikasi punya penanggung jawab serta waktu yang terukur.
Tujuan
Metrik
Target awal (usulan)
Semua permohonan tercatat digital
% permohonan masuk lewat aplikasi (mandiri + berbantuan)
100% dalam 3 bulan setelah go-live
Pemohon bisa memantau status sendiri
% permohonan yang statusnya dicek pemohon tanpa datang ke kantor
≥ 60%
Verifikasi lebih cepat dan terukur
Rata-rata waktu dari berkas lengkap sampai Terbit
Diukur di bulan 1 sebagai baseline, lalu turun 30%
Berkas tidak bolak-balik
% berkas dikembalikan karena syarat kurang
Turun 50% dari baseline
Pimpinan punya gambaran beban kerja
Laporan bulanan per jenis izin & per verifikator
Tersedia otomatis setiap bulan
Angka target di atas adalah usulan awal dan perlu disepakati dengan DPMPTSP setelah baseline bulan pertama terkumpul.
Ruang lingkup
Versi 1 mencakup pendaftaran, unggah syarat, verifikasi berjenjang, pencatatan hasil OSS, dan pelacakan status. Integrasi API langsung dengan OSS tidak termasuk.
Termasuk (versi 1)
• Registrasi pemohon perorangan dan badan hukum, mandiri maupun lewat petugas loket.
• Unggah syarat dasar: KTP, NPWP, email, data permodalan, akta perusahaan.
• Pencatatan NIB dan pemilihan jalur: Tanpa Komitmen atau Dengan Komitmen.
• Pengajuan Izin Lokasi, Izin Lingkungan (UKL-UPL/AMDAL, koordinasi DLHK), dan IMB.
• Verifikasi dokumen berjenjang Kasi → Kabid → Kadis, dengan catatan dan pengembalian berkas.
• Penandaan Komitmen Ditolak dan pengembalian ke pemohon.
• Pencatatan Izin Usaha dan Izin Komersial/Operasional yang terbit, plus unggah dokumen izin.
• Lacak status untuk pemohon, notifikasi email, dashboard dan laporan untuk pimpinan.
• Manajemen pengguna, peran, dan jenis izin oleh admin.
Tidak termasuk (versi 1)
• Integrasi API otomatis dengan OSS; nomor dan dokumen dari OSS diinput atau diunggah petugas.
• Pembayaran retribusi online.
• Tanda tangan elektronik tersertifikasi (BSrE); izin tetap ditandatangani sesuai prosedur dinas.
• Aplikasi mobile native; layanan HP cukup lewat web responsif.
• Akses langsung oleh instansi teknis selain sebagai pengguna terbatas, jika disepakati.
Pengguna dan peran
Ada tujuh peran; tiga di antaranya (Kasi, Kabid, Kadis) membentuk rantai verifikasi yang wajib dilalui setiap berkas.
Peran
Siapa
Hak utama
Pemohon
Perorangan atau badan hukum
Daftar akun, isi data usaha, unggah syarat, ajukan izin, lacak status, unduh izin terbit
Petugas Loket (Layanan Berbantuan)
Staf front office DPMPTSP
Mendaftarkan dan mengunggah berkas atas nama pemohon yang datang ke kantor
Kasi
Kepala Seksi
Verifikasi tahap 1: cek kelengkapan dan keabsahan, teruskan atau kembalikan
Kabid
Kepala Bidang
Verifikasi tahap 2: telaah teknis, teruskan atau kembalikan
Kadis
Kepala Dinas
Persetujuan akhir, tandai Terbit atau Ditolak
Instansi Teknis
Mis. DLHK untuk Izin Lingkungan
Opsional: lihat berkas terkait dan beri rekomendasi
Admin Sistem
Operator TI DPMPTSP
Kelola pengguna, peran, jenis izin, daftar syarat, dan template notifikasi
Alur proses bisnis
Aplikasi mengikuti bagan prosedur di halaman 3: pemohon mendaftar, NIB terbit di OSS, lalu permohonan masuk lewat jalur Tanpa Komitmen atau Dengan Komitmen sebelum diverifikasi berjenjang.
Kedua jalur bertemu di verifikasi Kasi → Kabid → Kadis. Di tiap tahap berkas bisa dikembalikan ke pemohon untuk diperbaiki, dan komitmen yang tidak dipenuhi berstatus Komitmen Ditolak sehingga pemohon kembali ke awal.
Kebutuhan fungsional
Tujuh modul; prioritas P1 wajib ada saat go-live, P2 boleh menyusul di rilis berikutnya.
ID
Modul
Kebutuhan
Prioritas
F-01
Akun & Registrasi
Pemohon daftar dengan email dan verifikasi email; pilih tipe Perorangan atau Badan Hukum
P1
F-02
Akun & Registrasi
Petugas loket bisa membuat akun dan permohonan atas nama pemohon (Layanan Berbantuan)
P1
F-03
Profil & Syarat
Unggah KTP, NPWP, data permodalan, akta perusahaan (PDF/JPG, maks. 5 MB per file); syarat bisa diatur admin per jenis izin
P1
F-04
Profil & Syarat
Dokumen profil dipakai ulang untuk permohonan berikutnya tanpa unggah ulang
P2
F-05
NIB & Jalur
Input nomor NIB dari OSS beserta unggahan bukti; pilih jalur Tanpa Komitmen atau Dengan Komitmen
P1
F-06
Permohonan
Ajukan Izin Lokasi, Izin Lingkungan (UKL-UPL/AMDAL), dan IMB; tiap permohonan mendapat nomor registrasi unik
P1
F-07
Permohonan
Jalur Dengan Komitmen: catat pengajuan komitmen ke instansi teknis dan penerbitan/pencetakan komitmen via OSS
P1
F-08
Verifikasi
Antrean berkas per verifikator; aksi Teruskan, Kembalikan (wajib catatan), atau Tolak
P1
F-09
Verifikasi
Urutan wajib Kasi → Kabid → Kadis; berkas tidak bisa melompati tahap
P1
F-10
Verifikasi
Checklist kelengkapan per syarat dengan status Sesuai / Tidak Sesuai
P1
F-11
Verifikasi
Instansi teknis (mis. DLHK) memberi rekomendasi pada berkas Izin Lingkungan
P2
F-12
Penerbitan
Tandai Terbit, input nomor izin OSS, unggah dokumen izin; lanjut ke Izin Usaha lalu Izin Komersial/Operasional
P1
F-13
Penerbitan
Status Komitmen Ditolak mengembalikan pemohon ke awal dengan alasan tercatat
P1
F-14
Lacak & Notifikasi
Pemohon melihat status dan riwayat tiap tahap; cek status publik cukup dengan nomor registrasi
P1
F-15
Lacak & Notifikasi
Email otomatis saat berkas diterima, dikembalikan, ditolak, dan terbit
P1
F-16
Lacak & Notifikasi
Notifikasi WhatsApp
P2
F-17
Dashboard & Laporan
Jumlah permohonan per status, per jenis izin, per verifikator; rata-rata lama per tahap
P1
F-18
Dashboard & Laporan
Ekspor laporan bulanan ke Excel/PDF
P1
F-19
Admin
Kelola pengguna, peran, jenis izin, daftar syarat, template email
P1
F-20
Admin
Log audit: siapa melakukan apa, kapan, pada berkas mana
P1
Kebutuhan non-fungsional
Aplikasi harus aman untuk data pribadi pemohon dan tetap nyaman dipakai dari HP dengan koneksi lambat.
Aspek
Kebutuhan
Keamanan
HTTPS wajib; password di-hash; akses berbasis peran; berkas hanya bisa dibuka pemiliknya dan verifikator terkait
Data pribadi
KTP, NPWP, dan akta diperlakukan sebagai data pribadi sesuai UU Pelindungan Data Pribadi; tidak tampil di halaman cek status publik
Ketersediaan
Target uptime 99% di jam layanan
Kinerja
Halaman utama tampil < 3 detik di koneksi 3G; unggah file 5 MB selesai < 30 detik
Kapasitas
Sanggup 50 pengguna bersamaan; ruang penyimpanan berkas dipantau dan bisa diperluas
Cadangan
Backup database harian dan backup berkas mingguan ke media terpisah dari server
Kemudahan
Web responsif untuk HP; Bahasa Indonesia; alur pemohon maksimal 5 langkah sampai berkas terkirim
Jejak audit
Setiap perubahan status tercatat dengan pengguna, waktu, dan catatan; tidak bisa dihapus
Model data dan status permohonan
Inti datanya adalah Permohonan, yang terhubung ke Pemohon, Jenis Izin, Dokumen, dan Riwayat Verifikasi.
Entitas
Atribut utama
Pemohon
Tipe (perorangan/badan hukum), nama, NIK/NPWP, email, HP, alamat, NIB
Jenis Izin
Nama (Izin Lokasi, Izin Lingkungan, IMB, Izin Usaha, Izin Komersial/Operasional), jalur, daftar syarat, instansi teknis
Permohonan
No. registrasi, pemohon, jenis izin, jalur (Tanpa/Dengan Komitmen), kanal (mandiri/berbantuan), status, tahap saat ini, tanggal
Dokumen
Permohonan/pemohon, jenis syarat, file, status cek (Sesuai/Tidak Sesuai)
Riwayat Verifikasi
Permohonan, tahap, verifikator, aksi, catatan, waktu
Izin Terbit
Permohonan, nomor izin OSS, tanggal terbit, file izin
Pengguna
Nama, NIP, peran, unit kerja, status aktif
Status permohonan
Status
Arti
Langkah berikutnya
Draf
Pemohon masih mengisi
Kirim → Diajukan
Diajukan
Berkas masuk antrean Kasi
Verifikasi Kasi
Verifikasi Kasi
Dicek kelengkapan
Teruskan / Dikembalikan
Verifikasi Kabid
Telaah teknis
Teruskan / Dikembalikan
Verifikasi Kadis
Persetujuan akhir
Terbit / Ditolak
Dikembalikan
Ada syarat yang kurang, dengan catatan
Pemohon perbaiki → Diajukan
Komitmen Ditolak
Komitmen tidak dipenuhi
Pemohon kembali ke awal
Ditolak
Permohonan tidak disetujui
Selesai
Terbit
Izin sudah terbit di OSS dan tercatat
Lanjut ke Izin Usaha / Komersial
Stack teknis dan deployment
Aplikasi dikembangkan dengan Django di dalam virtual environment (venv), memakai MariaDB di localhost, dijalankan dalam container Docker, dan diakses lewat Nginx sebagai reverse proxy HTTPS.
Lapisan
Teknologi
Konfigurasi
Backend & web
Python 3.12, Django 5.2 LTS
Dikembangkan dalam venv (python3 -m venv venv); dependensi di requirements.txt
App server
Gunicorn
Listen di 127.0.0.1:8000, 3 worker
Database
MariaDB (terpasang di server)
Host localhost (127.0.0.1:3306), database sik, user sik, password sik
Container
Docker + Docker Compose
Dockerfile membangun image Django; venv dibuat di dalam image (/opt/venv)
Reverse proxy
Nginx
Port 80 dialihkan ke 443; HTTPS dengan sertifikat self-signed, diganti Let's Encrypt setelah domain aktif
Berkas unggahan
Folder media/ di-mount ke host
Dilayani Nginx; batas unggah 10 MB per request
Alur request: Browser → Nginx (HTTPS 443) → Gunicorn/Django di container (127.0.0.1:8000) → MariaDB di localhost (3306).
Container web dan nginx memakai network_mode: host agar Django bisa menjangkau MariaDB di localhost server, sesuai ketentuan koneksi database.
Langkah deployment
1. Jalankan scripts/install-docker.sh: memeriksa Docker dan Docker Compose, lalu menginstalnya bila belum ada.
2. Jalankan scripts/setup-mariadb.sh: memasang MariaDB bila belum ada, lalu membuat database sik dan user sik.
3. Jalankan scripts/gen-selfsigned-cert.sh untuk sertifikat HTTPS awal.
4. Salin .env.example menjadi .env, isi DJANGO_SECRET_KEY dan DJANGO_ALLOWED_HOSTS.
5. docker compose up -d --build; migrasi dan collectstatic berjalan otomatis saat container start.
Pengembangan lokal (tanpa Docker)
1. python3 -m venv venv lalu source venv/bin/activate.
2. pip install -r requirements.txt.
3. python manage.py migrate lalu python manage.py runserver.
Password sik dipakai untuk pengembangan; sebelum go-live sebaiknya diganti dengan password kuat lewat .env.
Rencana rilis, asumsi, risiko
Rilis dibagi empat tahap, dengan go-live setelah pelatihan dan uji coba bersama petugas.
1. Analisis & desain: validasi alur dengan Bpk. Hari dan tim, finalisasi daftar syarat per jenis izin.
2. Pengembangan P1: modul akun, permohonan, verifikasi, penerbitan, lacak status, dashboard.
3. Instalasi & uji coba: deploy dengan Docker di server dinas, uji UAT dengan Kasi, Kabid, Kadis, dan petugas loket.
4. Pelatihan & familiarisasi, lalu go-live; fitur P2 menyusul.
Durasi tiap tahap belum ditetapkan dan perlu disepakati di kontrak.
Pelatihan: sesi untuk petugas loket, verifikator (Kasi, Kabid, Kadis), dan admin sistem, plus panduan singkat untuk pemohon.
Asumsi
• Nomor NIB dan izin tetap diterbitkan di OSS; aplikasi hanya mencatatnya.
• DPMPTSP menyediakan koneksi internet dan ruang server.
• Daftar syarat per jenis izin diberikan dinas sebelum tahap pengembangan.
Risiko
Risiko
Dampak
Mitigasi
Bagan halaman 3 memakai istilah OSS lama (komitmen, Izin Lokasi, IMB); sejak PP 5/2021 OSS berbasis risiko memakai KKPR, PBG, dan Persetujuan Lingkungan
Jenis izin di aplikasi tidak cocok dengan OSS yang berlaku
Jenis izin dibuat konfigurabel oleh admin; konfirmasi alur terbaru dengan dinas
Kredensial database sederhana (sik/sik) terbawa ke produksi
Data pemohon rawan bila server dibobol
MariaDB hanya listen di localhost; ganti password lewat .env sebelum go-live
Sertifikat self-signed memicu peringatan browser
Pemohon ragu membuka situs
Pasang Let's Encrypt begitu domain mengarah ke server
Listrik atau internet kantor terputus
Layanan mandiri tidak bisa diakses
Container restart: unless-stopped; backup harian database
Pertanyaan terbuka
[x] Apakah alur internal masih mengikuti bagan ini, atau sudah disesuaikan dengan OSS berbasis risiko?
[x] Jenis izin apa saja yang masuk versi 1?
[x] Apakah DLHK dan instansi teknis lain akan login ke aplikasi?
[ ] Domain yang dipakai: domain komersial atau subdomain .go.id?
