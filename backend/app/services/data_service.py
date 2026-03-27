from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from threading import RLock
from typing import Any

from app.core.config import MAX_FETCH_MONTHS
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
            rows, fetched_months, truncated_by_limit = fetch_cases(
                all_months=all_months,
                months=months,
                from_month=from_month,
            )
            payload = [asdict(r) if isinstance(r, CaseRow) else r for r in rows]

            save_cases(payload)
            monthly = analytics.monthly_stats(payload)
            save_monthly(monthly)

            report = analytics.markdown_report(payload)
            save_report(report)

            save_meta(
                {
                    "fetched_months": fetched_months,
                    "fetched_month_count": len(fetched_months),
                    "total_cases": len(payload),
                    "all_months": all_months,
                    "months_arg": months,
                    "from_month": from_month,
                    "truncated_by_limit": truncated_by_limit,
                    "month_limit": MAX_FETCH_MONTHS,
                }
            )

            return {
                "success": True,
                "message": "refresh completed",
                "fetched_months": fetched_months,
                "total_cases": len(payload),
                "truncated_by_limit": truncated_by_limit,
                "month_limit": MAX_FETCH_MONTHS,
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

    def get_consulate_groups(self, rows: list[dict[str, str]]) -> dict[str, Any]:
        return analytics.consulate_groups(rows)

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
        meta = load_meta()
        rows = self.get_cases()
        now = datetime.now()

        updated_at_raw = meta.get("updated_at")
        freshness_seconds: int | None = None
        if updated_at_raw:
            try:
                updated_dt = datetime.fromisoformat(str(updated_at_raw))
                freshness_seconds = max(0, int((now - updated_dt).total_seconds()))
            except ValueError:
                freshness_seconds = None

        fetched_months = meta.get("fetched_months") or []
        return {
            **meta,
            "has_data": len(rows) > 0,
            "current_case_count": len(rows),
            "data_freshness_seconds": freshness_seconds,
            "fetched_month_range": {
                "latest": fetched_months[0] if fetched_months else None,
                "earliest": fetched_months[-1] if fetched_months else None,
            },
        }


service = DataService()
