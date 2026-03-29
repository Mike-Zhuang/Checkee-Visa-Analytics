#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/checkee"
FRONTEND_DIST="/var/www/checkee/frontend/dist"
FETCH_RETRY_DELAYS=(3 10 20)

fetch_origin_main_with_retry() {
    local attempt=1
    local total_attempts
    total_attempts=$(( ${#FETCH_RETRY_DELAYS[@]} + 1 ))

    while true; do
        if git fetch origin main; then
            return 0
        fi

        if (( attempt >= total_attempts )); then
            echo "[checkee-sync] git fetch origin main failed after ${attempt} attempts"
            return 1
        fi

        local delay
        delay="${FETCH_RETRY_DELAYS[$((attempt - 1))]}"
        echo "[checkee-sync] git fetch failed, retry ${attempt}/${total_attempts} in ${delay}s"
        sleep "${delay}"
        attempt=$((attempt + 1))
    done
}

cd "${APP_DIR}"

if [[ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]]; then
    git checkout main
fi

fetch_origin_main_with_retry

LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse origin/main)"

if [[ "${LOCAL_SHA}" == "${REMOTE_SHA}" ]]; then
    echo "[checkee-sync] no update"
    exit 0
fi

git pull --ff-only origin main

if [[ ! -d "${APP_DIR}/.venv" ]]; then
    python3 -m venv "${APP_DIR}/.venv"
fi

"${APP_DIR}/.venv/bin/python" -m pip install -r "${APP_DIR}/backend/requirements.txt"
"${APP_DIR}/.venv/bin/python" -m pip install eval_type_backport

cat > "${APP_DIR}/frontend/.env.production" <<'ENVEOF'
VITE_API_BASE_URL=/api/v1
VITE_DEFAULT_PAGE_SIZE=50
VITE_DEFAULT_REFRESH_MONTHS=6
VITE_PAGE_SIZE_OPTIONS=50,100,200

VITE_ENABLE_LANGUAGE_SWITCH=true
VITE_ENABLE_SENSITIVITY=true
VITE_ENABLE_CONSULATE_GROUPS=true
VITE_ENABLE_PUBLIC_REFRESH=false
VITE_ENABLE_ADMIN_PAGE=true
VITE_ADMIN_ROUTE_PATH=/admin-ops
VITE_ADMIN_REQUIRE_ACCESS_CODE=false
VITE_ADMIN_ACCESS_CODE=
ENVEOF

cd "${APP_DIR}/frontend"
/usr/local/bin/pnpm install --frozen-lockfile
/usr/local/bin/pnpm run build

mkdir -p "${FRONTEND_DIST}"
rsync -a --delete "${APP_DIR}/frontend/dist/" "${FRONTEND_DIST}/"

chown -R www:www /var/www/checkee
chown -R www-data:www-data "${APP_DIR}/backend/data"

systemctl restart checkee-backend.service
/etc/init.d/nginx reload

echo "[checkee-sync] deployed ${REMOTE_SHA}"
