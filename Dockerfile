# Image aplikasi Django SIK Perizinan DPMPTSP Lombok Timur.
# Dua tahap: compiler hanya ada di tahap build, image akhir cukup library runtime MariaDB.

# ---- Tahap 1: pasang dependensi Python (butuh compiler untuk mysqlclient) ----
FROM python:3.12-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---- Tahap 2: image runtime ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings \
    GUNICORN_BIND=127.0.0.1:8000 \
    GUNICORN_WORKERS=3

# Library runtime mysqlclient saja (tanpa compiler).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmariadb3 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 django \
    && useradd --system --uid 1000 --gid django --create-home django

COPY --from=build /opt/venv /opt/venv

WORKDIR /app
COPY --chown=django:django . .

# Folder tulis dibuat dan dimiliki django sebelum volume dipasang.
RUN chmod +x /app/docker-entrypoint.sh \
    && mkdir -p /app/staticfiles /app/media \
    && chown django:django /app/staticfiles /app/media

USER django

EXPOSE 8000

# /sehat/ ringan, tanpa login, dan dikecualikan dari middleware.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import os, urllib.request as u; u.urlopen('http://' + os.environ.get('GUNICORN_BIND', '127.0.0.1:8000') + '/sehat/', timeout=5)"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind \"$GUNICORN_BIND\" --workers \"$GUNICORN_WORKERS\" --timeout 120 --access-logfile -"]
