from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from threading import RLock
from typing import Any

from app.services import analytics
from app.services.scraper import CaseRow, fetch_cases
from app.services.storage import (
    load_cases,
    load_meta,
    load_monthly,
    load_report,
    save_cases,
    save_meta,
    save_monthly,
    save_report,
)


class DataService:
    def __init__(self) -> None:
        self._lock = RLock()

    def refresh(self, all_months: bool = False, months: int = 6, from_month: str | None = None) -> dict[str, Any]:
        with self._lock:
            rows, fetched_months = fetch_cases(all_months=all_months, months=months, from_month=from_month)
            payload = [asdict(r) if isinstance(r, CaseRow) else r for r in rows]

            save_cases(payload)
            monthly = analytics.monthly_stats(payload)
            save_monthly(monthly)

            report = analytics.markdown_report(payload)
            save_report(report)

            save_meta(
                {
                    "fetched_months": fetched_months,
                    "total_cases": len(payload),
                    "all_months": all_months,
                    "months_arg": months,
                    "from_month": from_month,
                }
            )

            return {
                "success": True,
                "message": "refresh completed",
                "fetched_months": fetched_months,
                "total_cases": len(payload),
                "generated_at": datetime.now(),
            }

    def get_cases(self) -> list[dict[str, str]]:
        return load_cases()

    def get_overview(self, rows: list[dict[str, str]]) -> dict[str, Any]:
        return analytics.overview_stats(rows)

    def get_monthly(self, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
        return analytics.monthly_stats(rows)

    def get_sensitivity(self, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
        return analytics.sensitivity_stats(rows)

    def get_options(self, rows: list[dict[str, str]]) -> dict[str, list[str]]:
        return analytics.options(rows)

    def get_report(self, rows: list[dict[str, str]]) -> str:
        if not rows:
            return load_report()
        return analytics.markdown_report(rows)

    def filter_rows(
        self,
        rows: list[dict[str, str]],
        visa_types: set[str] | None,
        consulates: set[str] | None,
        statuses: set[str] | None,
        entries: set[str] | None,
        months: set[str] | None,
    ) -> list[dict[str, str]]:
        return analytics.filter_rows(
            rows,
            visa_types=visa_types,
            consulates=consulates,
            statuses=statuses,
            entries=entries,
            months=months,
        )

    def get_meta(self) -> dict[str, Any]:
        return load_meta()


service = DataService()
