#!/usr/bin/env bash
# Memasang Docker Engine + Docker Compose plugin bila belum ada.
# Untuk Ubuntu / Debian. Jalankan: sudo bash scripts/install-docker.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Jalankan dengan sudo." >&2
  exit 1
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "Docker sudah terpasang: $(docker --version)"
  echo "Compose: $(docker compose version)"
  exit 0
fi

. /etc/os-release
case "$ID" in
  ubuntu|debian) ;;
  *) echo "Distro $ID belum didukung skrip ini. Lihat https://docs.docker.com/engine/install/" >&2; exit 1 ;;
esac

echo "Memasang Docker untuk $PRETTY_NAME ..."
apt-get update
apt-get install -y ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL "https://download.docker.com/linux/${ID}/gpg" -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker

# Izinkan user yang memanggil sudo menjalankan docker tanpa sudo
if [[ -n "${SUDO_USER:-}" ]]; then
  usermod -aG docker "$SUDO_USER"
  echo "User $SUDO_USER ditambahkan ke grup docker (logout/login agar berlaku)."
fi

docker --version
docker compose version
echo "Docker siap."
