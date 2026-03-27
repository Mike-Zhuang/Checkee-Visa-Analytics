from __future__ import annotations

import os
from pathlib import Path


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip() or default


def _env_int(name: str, default: int, minimum: int | None = None) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    if minimum is not None:
        return max(minimum, parsed)
    return parsed


def _env_float(name: str, default: float, minimum: float | None = None) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    if minimum is not None:
        return max(minimum, parsed)
    return parsed


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default
    parsed = [item.strip() for item in value.split(",") if item.strip()]
    return parsed or default


BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR_RAW = os.getenv("CHECKEE_DATA_DIR")
if DATA_DIR_RAW:
    data_dir_path = Path(DATA_DIR_RAW).expanduser()
    DATA_DIR = data_dir_path if data_dir_path.is_absolute() else (BASE_DIR / data_dir_path)
else:
    DATA_DIR = BASE_DIR / "backend" / "data"

CASES_CSV = DATA_DIR / "live_cases_all_visa.csv"
MONTHLY_CSV = DATA_DIR / "live_monthly_all_visa.csv"
REPORT_MD = DATA_DIR / "live_report_all_visa.md"
META_JSON = DATA_DIR / "meta.json"

APP_NAME = _env_str("CHECKEE_APP_NAME", "Checkee Analytics API")
APP_VERSION = _env_str("CHECKEE_APP_VERSION", "0.2.0")

CHECKEE_BASE_URL = _env_str("CHECKEE_BASE_URL", "https://checkee.info/")
REQUEST_TIMEOUT_SECONDS = _env_int("CHECKEE_REQUEST_TIMEOUT_SECONDS", 25, minimum=1)
REQUEST_RETRIES = _env_int("CHECKEE_REQUEST_RETRIES", 1, minimum=0)
RETRY_SLEEP_SECONDS = _env_float("CHECKEE_RETRY_SLEEP_SECONDS", 2.0, minimum=0.0)
FETCH_DELAY_SECONDS = _env_float("CHECKEE_FETCH_DELAY_SECONDS", 0.2, minimum=0.0)
MAX_FETCH_MONTHS = _env_int("CHECKEE_MAX_FETCH_MONTHS", 120, minimum=1)

API_DEFAULT_REFRESH_MONTHS = _env_int("CHECKEE_API_DEFAULT_REFRESH_MONTHS", 6, minimum=1)
API_MAX_REFRESH_MONTHS = _env_int("CHECKEE_API_MAX_REFRESH_MONTHS", 240, minimum=1)
API_DEFAULT_CASES_LIMIT = _env_int("CHECKEE_API_DEFAULT_CASES_LIMIT", 200, minimum=1)
API_MAX_CASES_LIMIT = _env_int("CHECKEE_API_MAX_CASES_LIMIT", 5000, minimum=1)

BOOTSTRAP_SEED = _env_int("CHECKEE_BOOTSTRAP_SEED", 20260327)

CORS_ALLOW_ORIGINS = _env_csv("CHECKEE_CORS_ALLOW_ORIGINS", ["*"])
CORS_ALLOW_METHODS = _env_csv("CHECKEE_CORS_ALLOW_METHODS", ["*"])
CORS_ALLOW_HEADERS = _env_csv("CHECKEE_CORS_ALLOW_HEADERS", ["*"])
CORS_ALLOW_CREDENTIALS = _env_bool("CHECKEE_CORS_ALLOW_CREDENTIALS", True)

USER_AGENT = (
    _env_str(
        "CHECKEE_USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36",
    )
)
