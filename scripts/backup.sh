#!/usr/bin/env bash
# Cadangan sesuai PRD: database harian, berkas mingguan, ke media terpisah dari server.
# Membaca langsung dari container sik_db (database) dan sik_web (volume media).
# Pemakaian: bash scripts/backup.sh <folder-tujuan> [db|berkas|semua]
# Folder tujuan harus berada di disk lain atau mount jaringan. Contoh cron ada di README.
set -euo pipefail

TUJUAN="${1:?Pemakaian: backup.sh <folder-tujuan> [db|berkas|semua]}"
JENIS="${2:-db}"
SIMPAN_DB_HARI="${SIMPAN_DB_HARI:-30}"
SIMPAN_BERKAS_HARI="${SIMPAN_BERKAS_HARI:-60}"
DB_CONTAINER="${DB_CONTAINER:-sik_db}"
WEB_CONTAINER="${WEB_CONTAINER:-sik_web}"
WAKTU="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$TUJUAN/db" "$TUJUAN/berkas"
chmod 700 "$TUJUAN"
umask 077

cadangkan_db() {
  local tmp="$TUJUAN/db/.sik-$WAKTU.sql.gz" hasil="$TUJUAN/db/sik-$WAKTU.sql.gz"
  # Kredensial diambil dari environment container (.env.db); password lewat MYSQL_PWD
  # agar tidak terlihat di daftar proses.
  docker exec "$DB_CONTAINER" sh -c \
    'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb-dump --single-transaction --quick -u "$MARIADB_USER" "$MARIADB_DATABASE"' \
    | gzip > "$tmp"
  mv "$tmp" "$hasil"
  find "$TUJUAN/db" -name 'sik-*.sql.gz' -mtime +"$SIMPAN_DB_HARI" -delete
  echo "Database dicadangkan: $hasil"
}

cadangkan_berkas() {
  local tmp="$TUJUAN/berkas/.media-$WAKTU.tar.gz" hasil="$TUJUAN/berkas/media-$WAKTU.tar.gz"
  docker exec "$WEB_CONTAINER" tar -czf - -C /app media > "$tmp"
  mv "$tmp" "$hasil"
  find "$TUJUAN/berkas" -name 'media-*.tar.gz' -mtime +"$SIMPAN_BERKAS_HARI" -delete
  echo "Berkas dicadangkan: $hasil"
}

case "$JENIS" in
  db) cadangkan_db ;;
  berkas) cadangkan_berkas ;;
  semua) cadangkan_db; cadangkan_berkas ;;
  *) echo "Jenis harus db, berkas, atau semua." >&2; exit 1 ;;
esac
