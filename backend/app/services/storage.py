from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import CASES_CSV, DATA_DIR, META_JSON, MONTHLY_CSV, REPORT_MD


MAJOR_TAXONOMY_JSON = DATA_DIR / "major_taxonomy_rules.json"
MAJOR_OVERRIDES_JSON = DATA_DIR / "major_overrides.json"


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


def load_major_taxonomy() -> dict[str, Any]:
    if not MAJOR_TAXONOMY_JSON.exists():
        return {}
    return json.loads(MAJOR_TAXONOMY_JSON.read_text(encoding="utf-8"))


def save_major_taxonomy(data: dict[str, Any]) -> None:
    ensure_data_dir()
    MAJOR_TAXONOMY_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_major_overrides() -> dict[str, dict[str, Any]]:
    if not MAJOR_OVERRIDES_JSON.exists():
        return {}

    payload = json.loads(MAJOR_OVERRIDES_JSON.read_text(encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else []

    result: dict[str, dict[str, Any]] = {}
    for item in items or []:
        major_norm = str(item.get("major_norm") or "").strip()
        if not major_norm:
            continue
        result[major_norm] = {
            "major": str(item.get("major") or "").strip(),
            "category_l1": str(item.get("category_l1") or "Other").strip() or "Other",
            "category_l2": str(item.get("category_l2") or "Unspecified").strip() or "Unspecified",
            "updated_at": str(item.get("updated_at") or "").strip(),
            "updated_by": str(item.get("updated_by") or "").strip(),
        }
    return result


def save_major_overrides(overrides: dict[str, dict[str, Any]]) -> None:
    ensure_data_dir()
    items = []
    for major_norm in sorted(overrides):
        value = overrides[major_norm]
        items.append(
            {
                "major_norm": major_norm,
                "major": str(value.get("major") or "").strip(),
                "category_l1": str(value.get("category_l1") or "Other").strip() or "Other",
                "category_l2": str(value.get("category_l2") or "Unspecified").strip() or "Unspecified",
                "updated_at": str(value.get("updated_at") or "").strip(),
                "updated_by": str(value.get("updated_by") or "").strip(),
            }
        )

    payload = {
        "version": 1,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "items": items,
    }
    MAJOR_OVERRIDES_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
