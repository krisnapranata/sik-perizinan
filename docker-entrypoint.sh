#!/bin/sh
set -e

echo "Menunggu MariaDB di ${DB_HOST:-127.0.0.1}:${DB_PORT:-3306} ..."
python - <<'PY'
import os, time, MySQLdb
for i in range(30):
    try:
        MySQLdb.connect(
            host=os.environ.get("DB_HOST", "127.0.0.1"),
            port=int(os.environ.get("DB_PORT", "3306")),
            user=os.environ.get("DB_USER", "sik"),
            passwd=os.environ.get("DB_PASSWORD", "sik"),
            db=os.environ.get("DB_NAME", "sik"),
        ).close()
        print("MariaDB siap.")
        break
    except Exception as e:
        print(f"Belum siap ({e}), coba lagi...")
        time.sleep(2)
else:
    raise SystemExit("MariaDB tidak bisa dihubungi.")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
