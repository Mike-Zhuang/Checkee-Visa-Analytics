from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "backend" / "data"

CASES_CSV = DATA_DIR / "live_cases_all_visa.csv"
MONTHLY_CSV = DATA_DIR / "live_monthly_all_visa.csv"
REPORT_MD = DATA_DIR / "live_report_all_visa.md"
META_JSON = DATA_DIR / "meta.json"

CHECKEE_BASE_URL = "https://checkee.info/"
REQUEST_TIMEOUT_SECONDS = 25
REQUEST_RETRIES = 1
RETRY_SLEEP_SECONDS = 2
FETCH_DELAY_SECONDS = 0.2

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
