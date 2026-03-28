from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import storage


SAMPLE_CASES: list[dict[str, Any]] = [
    {
        "source_month": "2026-03",
        "case_number": "A001",
        "nickname": "alpha",
        "visa_type": "F1",
        "visa_entry": "I20",
        "consulate": "BeiJing",
        "major": "CS",
        "status": "Clear",
        "check_date": "2026-03-01",
        "complete_date": "2026-03-25",
        "waiting_days_reported": "24",
        "waiting_days_calc": "24",
        "observed_days": "",
        "event": "1",
        "detail_url": "https://example.com/detail/A001",
        "update_url": "https://example.com/update/A001",
        "detail_employer": "Google",
        "detail_note": "STEM case with complete timeline",
        "detail_city": "Beijing",
        "detail_state": "Beijing",
    },
    {
        "source_month": "2026-03",
        "case_number": "A002",
        "nickname": "beta",
        "visa_type": "F1",
        "visa_entry": "I20",
        "consulate": "Toronto",
        "major": "Math",
        "status": "Reject",
        "check_date": "2026-03-05",
        "complete_date": "2026-04-10",
        "waiting_days_reported": "36",
        "waiting_days_calc": "36",
        "observed_days": "",
        "event": "1",
        "detail_url": "https://example.com/detail/A002",
        "update_url": "https://example.com/update/A002",
        "detail_employer": "Amazon",
        "detail_note": "Administrative processing then cleared",
        "detail_city": "Toronto",
        "detail_state": "Ontario",
    },
    {
        "source_month": "2026-02",
        "case_number": "A003",
        "nickname": "gamma",
        "visa_type": "H1B",
        "visa_entry": "I129",
        "consulate": "Europe",
        "major": "EE",
        "status": "Pending",
        "check_date": "2026-02-12",
        "complete_date": "",
        "waiting_days_reported": "",
        "waiting_days_calc": "",
        "observed_days": "44",
        "event": "0",
        "detail_url": "https://example.com/detail/A003",
        "update_url": "https://example.com/update/A003",
        "detail_employer": "ByteDance",
        "detail_note": "Pending and waiting for embassy update",
        "detail_city": "Paris",
        "detail_state": "Ile-de-France",
    },
    {
        "source_month": "2026-01",
        "case_number": "A004",
        "nickname": "delta",
        "visa_type": "L1",
        "visa_entry": "L1A",
        "consulate": "MoonBase",
        "major": "Biz",
        "status": "Pending",
        "check_date": "2026-01-20",
        "complete_date": "",
        "waiting_days_reported": "",
        "waiting_days_calc": "",
        "observed_days": "67",
        "event": "0",
        "detail_url": "https://example.com/detail/A004",
        "update_url": "https://example.com/update/A004",
        "detail_employer": "SpaceY",
        "detail_note": "Long pending case with no reply",
        "detail_city": "Seattle",
        "detail_state": "Washington",
    },
]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(storage, "DATA_DIR", data_dir)
    monkeypatch.setattr(storage, "CASES_CSV", data_dir / "live_cases_all_visa.csv")
    monkeypatch.setattr(storage, "MONTHLY_CSV", data_dir / "live_monthly_all_visa.csv")
    monkeypatch.setattr(storage, "REPORT_MD", data_dir / "live_report_all_visa.md")
    monkeypatch.setattr(storage, "META_JSON", data_dir / "meta.json")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def seed_cases() -> list[dict[str, Any]]:
    _write_csv(storage.CASES_CSV, SAMPLE_CASES)
    storage.META_JSON.write_text(
        json.dumps(
            {
                "fetched_months": ["2026-03", "2026-02", "2026-01"],
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    storage.REPORT_MD.write_text("# test report", encoding="utf-8")
    return SAMPLE_CASES
