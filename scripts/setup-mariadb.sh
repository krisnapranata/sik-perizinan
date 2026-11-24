#!/usr/bin/env bash
# Memasang MariaDB (bila belum ada) dan membuat database + user aplikasi.
# Nilai DB_NAME, DB_USER, DB_PASSWORD dibaca dari .env (bila ada), lalu bawaan sik/sik/sik.
# Jalankan ulang setelah mengganti password di .env agar MariaDB ikut berubah.
# Jalankan: sudo bash scripts/setup-mariadb.sh
set -euo pipefail

ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"

dari_env() {
  [[ -f "$ENV_FILE" ]] && sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1
  return 0
}

DB_NAME="${DB_NAME:-$(dari_env DB_NAME)}"
DB_USER="${DB_USER:-$(dari_env DB_USER)}"
DB_PASSWORD="${DB_PASSWORD:-$(dari_env DB_PASSWORD)}"
DB_NAME="${DB_NAME:-sik}"
DB_USER="${DB_USER:-sik}"
DB_PASSWORD="${DB_PASSWORD:-sik}"

if [[ $EUID -ne 0 ]]; then
  echo "Jalankan dengan sudo." >&2
  exit 1
fi

if [[ ! "$DB_NAME" =~ ^[A-Za-z0-9_]+$ || ! "$DB_USER" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "DB_NAME dan DB_USER hanya boleh huruf, angka, dan garis bawah." >&2
  exit 1
fi

if ! command -v mariadb >/dev/null 2>&1 && ! command -v mysql >/dev/null 2>&1; then
  echo "Memasang MariaDB ..."
  apt-get update
  apt-get install -y mariadb-server
fi

systemctl enable --now mariadb

CLIENT="$(command -v mariadb || command -v mysql)"

# Escape untuk literal SQL: backslash dulu, lalu kutip tunggal.
PASS_SQL="${DB_PASSWORD//\\/\\\\}"
PASS_SQL="${PASS_SQL//\'/\'\'}"

# User dibuat untuk socket (localhost) dan TCP (127.0.0.1).
# ALTER USER menyelaraskan password bila user sudah ada.
# test_<nama> diperlukan oleh "python manage.py test".
"$CLIENT" -u root <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${PASS_SQL}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'127.0.0.1' IDENTIFIED BY '${PASS_SQL}';
ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${PASS_SQL}';
ALTER USER '${DB_USER}'@'127.0.0.1' IDENTIFIED BY '${PASS_SQL}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'127.0.0.1';
GRANT ALL PRIVILEGES ON \`test_${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON \`test_${DB_NAME}\`.* TO '${DB_USER}'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

echo "Database '${DB_NAME}' dan user '${DB_USER}' siap."

BIND="$("$CLIENT" -u root -N -e "SELECT @@bind_address" 2>/dev/null || true)"
if [[ "$BIND" != "127.0.0.1" && "$BIND" != "localhost" ]]; then
  echo "PERINGATAN: MariaDB listen di '${BIND:-semua alamat}', bukan hanya 127.0.0.1." >&2
  echo "Set bind-address = 127.0.0.1 di konfigurasi MariaDB, lalu restart." >&2
fi
