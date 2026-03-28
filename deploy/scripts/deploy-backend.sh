#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
APP_DIR="/opt/checkee"
SERVICE_NAME="checkee-backend.service"

echo "[1/6] Sync repository to ${APP_DIR}"
sudo mkdir -p "${APP_DIR}"
sudo rsync -a --delete --exclude '.git' "${ROOT_DIR}/" "${APP_DIR}/"

echo "[2/6] Create Python virtual environment"
if [[ ! -d "${APP_DIR}/.venv" ]]; then
    sudo python3 -m venv "${APP_DIR}/.venv"
fi

echo "[3/6] Install backend dependencies"
sudo "${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
sudo "${APP_DIR}/.venv/bin/python" -m pip install -r "${APP_DIR}/backend/requirements.txt"

echo "[4/6] Build frontend"
cd "${APP_DIR}/frontend"
if [[ -f pnpm-lock.yaml || -f ../pnpm-lock.yaml ]]; then
    sudo pnpm install --frozen-lockfile
    sudo pnpm run build
else
    sudo npm ci
    sudo npm run build
fi

echo "[5/6] Install and reload systemd service"
sudo cp "${APP_DIR}/deploy/systemd/${SERVICE_NAME}" "/etc/systemd/system/${SERVICE_NAME}"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

echo "[6/6] Show service status"
sudo systemctl --no-pager status "${SERVICE_NAME}"

echo "Done. Remember to install deploy/nginx/checkee.conf and reload nginx."
