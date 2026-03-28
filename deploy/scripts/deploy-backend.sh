#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
APP_DIR="/opt/checkee"
SERVICE_NAME="checkee-backend.service"
REFRESH_SERVICE_NAME="checkee-refresh.service"
REFRESH_TIMER_NAME="checkee-refresh.timer"

echo "[1/7] Sync repository to ${APP_DIR}"
sudo mkdir -p "${APP_DIR}"
sudo rsync -a --delete --exclude '.git' "${ROOT_DIR}/" "${APP_DIR}/"

echo "[2/7] Create Python virtual environment"
if [[ ! -d "${APP_DIR}/.venv" ]]; then
    sudo python3 -m venv "${APP_DIR}/.venv"
fi

echo "[3/7] Install backend dependencies"
sudo "${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
sudo "${APP_DIR}/.venv/bin/python" -m pip install -r "${APP_DIR}/backend/requirements.txt"

echo "[4/7] Build frontend"
cd "${APP_DIR}/frontend"
if [[ -f pnpm-lock.yaml || -f ../pnpm-lock.yaml ]]; then
    sudo pnpm install --frozen-lockfile
    sudo pnpm run build
else
    sudo npm ci
    sudo npm run build
fi

echo "[5/7] Install and reload systemd units"
sudo cp "${APP_DIR}/deploy/systemd/${SERVICE_NAME}" "/etc/systemd/system/${SERVICE_NAME}"
sudo cp "${APP_DIR}/deploy/systemd/${REFRESH_SERVICE_NAME}" "/etc/systemd/system/${REFRESH_SERVICE_NAME}"
sudo cp "${APP_DIR}/deploy/systemd/${REFRESH_TIMER_NAME}" "/etc/systemd/system/${REFRESH_TIMER_NAME}"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl enable "${REFRESH_TIMER_NAME}"
sudo systemctl restart "${SERVICE_NAME}"
sudo systemctl restart "${REFRESH_TIMER_NAME}"

echo "[6/7] Show backend status"
sudo systemctl --no-pager status "${SERVICE_NAME}"

echo "[7/7] Show timer status"
sudo systemctl --no-pager status "${REFRESH_TIMER_NAME}"

echo "Done. Remember to install deploy/nginx/checkee.conf and reload nginx."
