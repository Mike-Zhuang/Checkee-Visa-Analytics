from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from threading import RLock
from typing import Any

from app.core.config import MAX_FETCH_MONTHS
from app.services import analytics
from app.services.scraper import CaseRow, FetchResult, fetch_cases, list_supported_sources
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

    def refresh(
        self,
        all_months: bool = False,
        months: int = 6,
        from_month: str | None = None,
        sources: list[str] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            fetch_result: FetchResult = fetch_cases(
                all_months=all_months,
                months=months,
                from_month=from_month,
                sources=sources,
            )
            rows = fetch_result.rows
            payload = [asdict(r) if isinstance(r, CaseRow) else r for r in rows]
            data_quality = self._compute_data_quality(payload)

            save_cases(payload)
            monthly = analytics.monthly_stats(payload)
            save_monthly(monthly)

            report = analytics.markdown_report(payload)
            save_report(report)

            save_meta(
                {
                    "fetched_months": fetch_result.fetched_months,
                    "fetched_month_count": len(fetch_result.fetched_months),
                    "total_cases": len(payload),
                    "all_months": all_months,
                    "months_arg": months,
                    "from_month": from_month,
                    "requested_sources": sources,
                    "selected_sources": fetch_result.selected_sources,
                    "supported_sources": list_supported_sources(),
                    "truncated_by_limit": fetch_result.truncated_by_limit,
                    "month_limit": MAX_FETCH_MONTHS,
                    "source_discovery": fetch_result.source_discovery,
                    "source_discovery_count": len(fetch_result.source_discovery),
                    "coverage": fetch_result.coverage,
                    "data_quality": data_quality,
                }
            )

            return {
                "success": True,
                "message": "refresh completed",
                "fetched_months": fetch_result.fetched_months,
                "total_cases": len(payload),
                "selected_sources": fetch_result.selected_sources,
                "truncated_by_limit": fetch_result.truncated_by_limit,
                "month_limit": MAX_FETCH_MONTHS,
                "generated_at": datetime.now(),
            }

    @staticmethod
    def _is_valid_date(value: str) -> bool:
        if not value or value == "0000-00-00":
            return False
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _compute_data_quality(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(rows)
        if total == 0:
            return {
                "total_rows": 0,
                "missing_case_number_count": 0,
                "missing_case_number_rate": 0.0,
                "missing_detail_url_count": 0,
                "missing_detail_url_rate": 0.0,
                "missing_update_url_count": 0,
                "missing_update_url_rate": 0.0,
                "invalid_check_date_count": 0,
                "invalid_check_date_rate": 0.0,
                "finalized_missing_complete_date_count": 0,
                "finalized_missing_complete_date_rate": 0.0,
            }

        missing_case_number_count = sum(1 for row in rows if not str(row.get("case_number") or "").strip())
        missing_detail_url_count = sum(1 for row in rows if not str(row.get("detail_url") or "").strip())
        missing_update_url_count = sum(1 for row in rows if not str(row.get("update_url") or "").strip())
        invalid_check_date_count = sum(1 for row in rows if not self._is_valid_date(str(row.get("check_date") or "")))

        finalized_rows = [
            row
            for row in rows
            if str(row.get("status") or "").strip().capitalize() in {"Clear", "Reject"}
        ]
        finalized_missing_complete_date_count = sum(
            1
            for row in finalized_rows
            if not self._is_valid_date(str(row.get("complete_date") or ""))
        )
        finalized_total = len(finalized_rows)

        def _rate(count: int, denominator: int) -> float:
            if denominator <= 0:
                return 0.0
            return round(count / denominator, 6)

        return {
            "total_rows": total,
            "missing_case_number_count": missing_case_number_count,
            "missing_case_number_rate": _rate(missing_case_number_count, total),
            "missing_detail_url_count": missing_detail_url_count,
            "missing_detail_url_rate": _rate(missing_detail_url_count, total),
            "missing_update_url_count": missing_update_url_count,
            "missing_update_url_rate": _rate(missing_update_url_count, total),
            "invalid_check_date_count": invalid_check_date_count,
            "invalid_check_date_rate": _rate(invalid_check_date_count, total),
            "finalized_missing_complete_date_count": finalized_missing_complete_date_count,
            "finalized_missing_complete_date_rate": _rate(finalized_missing_complete_date_count, finalized_total),
        }

    def get_cases(self) -> list[dict[str, str]]:
        return load_cases()

    def get_overview(self, rows: list[dict[str, str]]) -> dict[str, Any]:
        return analytics.overview_stats(rows)

    def get_monthly(self, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
        return analytics.monthly_stats(rows)

    def get_sensitivity(self, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
        return analytics.sensitivity_stats(rows)

    def get_cohorts(self, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
        return analytics.cohort_stats(rows)

    def get_distribution(self, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
        return analytics.distribution_stats(rows)

    def get_comparison(self, rows: list[dict[str, str]]) -> dict[str, Any]:
        return analytics.comparison_stats(rows)

    def get_anomalies(self, rows: list[dict[str, str]], threshold_days: int, limit: int) -> list[dict[str, Any]]:
        return analytics.anomalies(rows, threshold_days=threshold_days, limit=limit)

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

        meta.setdefault("supported_sources", list_supported_sources())
        if "selected_sources" not in meta and "supported_sources" in meta:
            meta["selected_sources"] = meta["supported_sources"]

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
