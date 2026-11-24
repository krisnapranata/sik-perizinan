#!/usr/bin/env bash
# Cadangan sesuai PRD: database harian, berkas mingguan, ke media terpisah dari server.
# Pemakaian: bash scripts/backup.sh <folder-tujuan> [db|berkas|semua]
# Folder tujuan harus berada di disk lain atau mount jaringan. Contoh cron ada di README.
set -euo pipefail

TUJUAN="${1:?Pemakaian: backup.sh <folder-tujuan> [db|berkas|semua]}"
JENIS="${2:-db}"
SIMPAN_DB_HARI="${SIMPAN_DB_HARI:-30}"
SIMPAN_BERKAS_HARI="${SIMPAN_BERKAS_HARI:-60}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"

dari_env() {
  [[ -f "$ENV_FILE" ]] && sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1
  return 0
}

DB_HOST="${DB_HOST:-$(dari_env DB_HOST)}"
DB_PORT="${DB_PORT:-$(dari_env DB_PORT)}"
DB_NAME="${DB_NAME:-$(dari_env DB_NAME)}"
DB_USER="${DB_USER:-$(dari_env DB_USER)}"
DB_PASSWORD="${DB_PASSWORD:-$(dari_env DB_PASSWORD)}"
WAKTU="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$TUJUAN/db" "$TUJUAN/berkas"
chmod 700 "$TUJUAN"
umask 077

cadangkan_db() {
  local tmp="$TUJUAN/db/.sik-$WAKTU.sql.gz" hasil="$TUJUAN/db/sik-$WAKTU.sql.gz"
  local dump
  dump="$(command -v mariadb-dump || command -v mysqldump)"
  # Password lewat environment agar tidak terlihat di daftar proses.
  MYSQL_PWD="${DB_PASSWORD:-sik}" "$dump" --single-transaction --quick \
    -h "${DB_HOST:-127.0.0.1}" -P "${DB_PORT:-3306}" -u "${DB_USER:-sik}" "${DB_NAME:-sik}" \
    | gzip > "$tmp"
  mv "$tmp" "$hasil"
  find "$TUJUAN/db" -name 'sik-*.sql.gz' -mtime +"$SIMPAN_DB_HARI" -delete
  echo "Database dicadangkan: $hasil"
}

cadangkan_berkas() {
  local tmp="$TUJUAN/berkas/.media-$WAKTU.tar.gz" hasil="$TUJUAN/berkas/media-$WAKTU.tar.gz"
  tar -czf "$tmp" -C "$ROOT" media
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
