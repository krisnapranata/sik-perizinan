#!/usr/bin/env bash
# Membuat sertifikat self-signed untuk HTTPS awal.
# Pemakaian: bash scripts/gen-selfsigned-cert.sh [domain-atau-ip]
set -euo pipefail

CN="${1:-localhost}"
DIR="$(cd "$(dirname "$0")/.." && pwd)/nginx/certs"
mkdir -p "$DIR"

# Alamat IP harus masuk SAN sebagai IP:, bukan DNS:, agar diterima browser.
if [[ "$CN" =~ ^[0-9.]+$ || "$CN" == *:* ]]; then
  SAN="IP:${CN}"
else
  SAN="DNS:${CN}"
fi

openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout "$DIR/privkey.pem" -out "$DIR/fullchain.pem" \
  -subj "/C=ID/ST=NTB/L=Lombok Timur/O=DPMPTSP Lombok Timur/CN=${CN}" \
  -addext "subjectAltName=${SAN},DNS:localhost,IP:127.0.0.1"

chmod 600 "$DIR/privkey.pem"
echo "Sertifikat dibuat di $DIR (berlaku 365 hari, CN=${CN})."
echo "Setelah domain aktif, ganti dengan Let's Encrypt (lihat README)."
