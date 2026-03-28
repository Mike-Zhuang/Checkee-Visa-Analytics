from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import CASES_CSV, DATA_DIR, META_JSON, MONTHLY_CSV, REPORT_MD


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    ensure_data_dir()
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]


def save_cases(rows: list[Any]) -> None:
    payload = [asdict(r) if not isinstance(r, dict) else r for r in rows]
    headers = list(payload[0].keys()) if payload else []
    if headers:
        write_csv(CASES_CSV, payload, headers)


def load_cases() -> list[dict[str, str]]:
    return read_csv(CASES_CSV)


def save_monthly(rows: list[dict[str, Any]]) -> None:
    headers = list(rows[0].keys()) if rows else []
    if headers:
        write_csv(MONTHLY_CSV, rows, headers)


def load_monthly() -> list[dict[str, str]]:
    return read_csv(MONTHLY_CSV)


def save_report(content: str) -> None:
    ensure_data_dir()
    REPORT_MD.write_text(content, encoding="utf-8")


def load_report() -> str:
    if not REPORT_MD.exists():
        return ""
    return REPORT_MD.read_text(encoding="utf-8")


def save_meta(data: dict[str, Any], *, update_timestamp: bool = True) -> None:
    ensure_data_dir()
    payload = dict(data)
    if update_timestamp:
        payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    META_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_meta() -> dict[str, Any]:
    if not META_JSON.exists():
        return {}
    return json.loads(META_JSON.read_text(encoding="utf-8"))
