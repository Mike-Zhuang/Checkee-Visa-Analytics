from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from threading import RLock, Thread
from typing import Any

from app.core.config import DETAIL_FETCH_SYNC_ON_REFRESH, MAX_FETCH_MONTHS, REFRESH_MIN_INTERVAL_SECONDS
from app.services import analytics, major_classifier
from app.services.scraper import (
    CaseRow,
    FetchResult,
    enrich_missing_details_for_payload_rows,
    fetch_cases,
    list_supported_sources,
)
from app.services.storage import (
    load_cases,
    load_major_overrides,
    load_major_taxonomy,
    load_meta,
    load_monthly,
    load_report,
    save_cases,
    save_major_overrides,
    save_meta,
    save_monthly,
    save_report,
)


class RefreshRateLimitError(ValueError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("refresh cooldown not reached")
        self.retry_after_seconds = max(1, retry_after_seconds)


class DataService:
    _DETAIL_ENRICHMENT_BATCH_SIZE = 50
    _DETAIL_PLACEHOLDERS = {
        "-",
        "--",
        "n/a",
        "na",
        "n a",
        "none",
        "null",
        "nil",
        "not applicable",
        "not available",
        "unknown",
    }

    def __init__(self) -> None:
        self._lock = RLock()
        self._detail_enrichment_running = False
        self._refresh_job_running = False

    @staticmethod
    def _row_identity(row: dict[str, Any]) -> str:
        for key in ("case_number", "update_url", "detail_url"):
            value = str(row.get(key) or "").strip()
            if value:
                return f"{key}:{value}"
        fallback = "|".join(
            [
                str(row.get("nickname") or "").strip(),
                str(row.get("check_date") or "").strip(),
                str(row.get("consulate") or "").strip(),
            ]
        )
        return f"fallback:{fallback}"

    @classmethod
    def _is_meaningful_detail_value(cls, value: str) -> bool:
        normalized = " ".join(str(value or "").strip().lower().replace("/", " ").split())
        return bool(normalized) and normalized not in cls._DETAIL_PLACEHOLDERS

    def _merge_existing_detail_fields(
        self,
        rows: list[dict[str, Any]],
        previous_rows: list[dict[str, str]],
    ) -> int:
        if not rows or not previous_rows:
            return 0

        detail_fields = ("detail_employer", "detail_note", "detail_city", "detail_state")
        previous_index = {self._row_identity(row): row for row in previous_rows}
        merged_count = 0

        for row in rows:
            old = previous_index.get(self._row_identity(row))
            if old is None:
                continue

            merged = False
            for field in detail_fields:
                current_value = str(row.get(field) or "").strip()
                if current_value:
                    continue
                old_value = str(old.get(field) or "").strip()
                if old_value:
                    row[field] = old_value
                    merged = True

            if merged:
                merged_count += 1

        return merged_count

    @staticmethod
    def _append_refresh_history(
        history: list[dict[str, Any]] | None,
        entry: dict[str, Any],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        normalized = [dict(item) for item in (history or []) if isinstance(item, dict)]
        normalized.insert(0, entry)
        return normalized[:limit]

    @staticmethod
    def _month_to_index(month_token: str) -> int | None:
        normalized = str(month_token or "").strip()
        if len(normalized) != 7:
            return None
        try:
            year_str, month_str = normalized.split("-", maxsplit=1)
            year = int(year_str)
            month = int(month_str)
        except (TypeError, ValueError):
            return None
        if year <= 0 or month < 1 or month > 12:
            return None
        return year * 12 + month

    @staticmethod
    def _index_to_month(index: int) -> str:
        month = index % 12
        year = index // 12
        if month == 0:
            month = 12
            year -= 1
        return f"{year:04d}-{month:02d}"

    def _current_month_token(self) -> str:
        return datetime.now().strftime("%Y-%m")

    def _auto_refresh_effective_from_month(
        self,
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        triggered_by: str,
    ) -> tuple[str | None, bool]:
        requested_from_month = str(from_month or "").strip() or None
        if all_months or requested_from_month:
            return requested_from_month, False

        if triggered_by not in {"scheduled", "auto_fallback"}:
            return None, False

        current_index = self._month_to_index(self._current_month_token())
        if current_index is None:
            return None, False

        request_start_index = current_index - max(0, int(months) - 1)

        meta = load_meta()
        fetched_months = meta.get("fetched_months")
        if not isinstance(fetched_months, list):
            return None, False

        historical_indexes = [
            idx
            for month in fetched_months
            for idx in [self._month_to_index(str(month))]
            if idx is not None
        ]
        if not historical_indexes:
            return None, False

        earliest_historical_index = min(historical_indexes)
        if earliest_historical_index < request_start_index:
            return self._index_to_month(earliest_historical_index), True
        return None, False

    def _taxonomy_rules(self) -> list[dict[str, Any]]:
        payload = load_major_taxonomy()
        rules = payload.get("rules") if isinstance(payload, dict) else None
        if isinstance(rules, list) and rules:
            return [dict(item) for item in rules if isinstance(item, dict)]
        return [dict(item) for item in major_classifier.DEFAULT_MAJOR_TAXONOMY_RULES]

    @staticmethod
    def _taxonomy_l1_options(rules: list[dict[str, Any]]) -> list[str]:
        return major_classifier.taxonomy_l1_options(rules)

    @staticmethod
    def _taxonomy_l2_options(rules: list[dict[str, Any]]) -> list[str]:
        return major_classifier.taxonomy_l2_options(rules)

    def _major_overrides(self) -> dict[str, dict[str, Any]]:
        return load_major_overrides()

    def _ensure_major_classification(self, rows: list[dict[str, Any]]) -> dict[str, int]:
        rules = self._taxonomy_rules()
        overrides = self._major_overrides()
        return major_classifier.apply_major_classification(rows, overrides, rules)

    def _reclassify_and_save_rows(self, rows: list[dict[str, Any]]) -> dict[str, int]:
        metrics = self._ensure_major_classification(rows)
        if rows:
            save_cases(rows)
        return metrics

    def _apply_detail_updates_by_identity(
        self,
        rows: list[dict[str, Any]],
        updates_by_identity: dict[str, dict[str, str]],
    ) -> int:
        updated_count = 0
        for row in rows:
            identity = self._row_identity(row)
            update = updates_by_identity.get(identity)
            if not update:
                continue

            changed = False
            for field in ("detail_employer", "detail_note", "detail_city", "detail_state"):
                current_value = str(row.get(field) or "").strip()
                if self._is_meaningful_detail_value(current_value):
                    continue
                next_value = str(update.get(field) or "").strip()
                if not self._is_meaningful_detail_value(next_value):
                    continue
                row[field] = next_value
                changed = True

            if changed:
                updated_count += 1
        return updated_count

    def _detail_enrichment_state(self) -> dict[str, Any]:
        meta = load_meta()
        state = meta.get("detail_enrichment")
        return dict(state) if isinstance(state, dict) else {"status": "idle"}

    def _set_detail_enrichment_state(self, payload: dict[str, Any]) -> None:
        meta = load_meta()
        save_meta({**meta, "detail_enrichment": payload}, update_timestamp=False)

    def _collect_detail_enrichment_candidates(self, rows: list[dict[str, Any]]) -> list[str]:
        identities: list[str] = []
        for row in rows:
            detail_url = str(row.get("detail_url") or "").strip()
            detail_note = str(row.get("detail_note") or "").strip()
            if not detail_url or self._is_meaningful_detail_value(detail_note):
                continue
            identities.append(self._row_identity(row))
        return identities

    def _build_updates_by_identity(self, rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
        return {
            self._row_identity(row): {
                "detail_employer": str(row.get("detail_employer") or ""),
                "detail_note": str(row.get("detail_note") or ""),
                "detail_city": str(row.get("detail_city") or ""),
                "detail_state": str(row.get("detail_state") or ""),
            }
            for row in rows
        }

    def _run_detail_enrichment_job_with_candidates(self, candidate_identities: list[str]) -> None:
        processed_count = 0
        updated_count = 0
        fetch_error_count = 0
        forbidden_count = 0
        parse_empty_count = 0
        enriched_count = 0
        started_at = datetime.now().isoformat(timespec="seconds")

        try:
            candidate_set = set(candidate_identities)
            candidate_count = len(candidate_identities)
            if candidate_count == 0:
                with self._lock:
                    self._set_detail_enrichment_state(
                        {
                            "status": "completed",
                            "started_at": started_at,
                            "finished_at": datetime.now().isoformat(timespec="seconds"),
                            "candidate_count": 0,
                            "processed_count": 0,
                            "updated_count": 0,
                            "fetch_error_count": 0,
                            "forbidden_count": 0,
                            "parse_empty_count": 0,
                            "enriched_count": 0,
                            "last_error": "",
                            "last_updated_at": datetime.now().isoformat(timespec="seconds"),
                        }
                    )
                return

            for chunk_start in range(0, candidate_count, self._DETAIL_ENRICHMENT_BATCH_SIZE):
                chunk_identities = set(
                    candidate_identities[chunk_start: chunk_start + self._DETAIL_ENRICHMENT_BATCH_SIZE]
                )
                if not chunk_identities:
                    continue

                with self._lock:
                    latest_rows = load_cases()
                    chunk_rows = [
                        dict(row)
                        for row in latest_rows
                        if self._row_identity(row) in chunk_identities
                        and self._row_identity(row) in candidate_set
                    ]

                if not chunk_rows:
                    processed_count += len(chunk_identities)
                    continue

                metrics = enrich_missing_details_for_payload_rows(chunk_rows)
                updates_by_identity = self._build_updates_by_identity(chunk_rows)

                chunk_processed = len(chunk_rows)
                chunk_fetch_error = int(metrics.get("detail_fetch_error_count") or 0)
                chunk_forbidden = int(metrics.get("detail_forbidden_count") or 0)
                chunk_parse_empty = int(metrics.get("detail_parse_empty_count") or 0)
                chunk_enriched = int(metrics.get("detail_enriched_count") or 0)

                with self._lock:
                    latest_rows = load_cases()
                    chunk_updated = self._apply_detail_updates_by_identity(latest_rows, updates_by_identity)
                    if chunk_updated > 0:
                        save_cases(latest_rows)

                    processed_count += chunk_processed
                    updated_count += chunk_updated
                    fetch_error_count += chunk_fetch_error
                    forbidden_count += chunk_forbidden
                    parse_empty_count += chunk_parse_empty
                    enriched_count += chunk_enriched

                    self._set_detail_enrichment_state(
                        {
                            "status": "running",
                            "started_at": started_at,
                            "candidate_count": candidate_count,
                            "processed_count": processed_count,
                            "updated_count": updated_count,
                            "fetch_error_count": fetch_error_count,
                            "forbidden_count": forbidden_count,
                            "parse_empty_count": parse_empty_count,
                            "enriched_count": enriched_count,
                            "last_error": "",
                            "last_updated_at": datetime.now().isoformat(timespec="seconds"),
                        }
                    )

            with self._lock:
                self._set_detail_enrichment_state(
                    {
                        "status": "completed",
                        "started_at": started_at,
                        "finished_at": datetime.now().isoformat(timespec="seconds"),
                        "candidate_count": len(candidate_identities),
                        "processed_count": processed_count,
                        "updated_count": updated_count,
                        "fetch_error_count": fetch_error_count,
                        "forbidden_count": forbidden_count,
                        "parse_empty_count": parse_empty_count,
                        "enriched_count": enriched_count,
                        "last_error": "",
                        "last_updated_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._set_detail_enrichment_state(
                    {
                        "status": "failed",
                        "started_at": started_at,
                        "finished_at": datetime.now().isoformat(timespec="seconds"),
                        "candidate_count": len(candidate_identities),
                        "processed_count": processed_count,
                        "updated_count": updated_count,
                        "fetch_error_count": fetch_error_count,
                        "forbidden_count": forbidden_count,
                        "parse_empty_count": parse_empty_count,
                        "enriched_count": enriched_count,
                        "last_error": str(exc),
                        "last_updated_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )
        finally:
            with self._lock:
                self._detail_enrichment_running = False

    def _start_detail_enrichment_job(self) -> bool:
        with self._lock:
            if self._detail_enrichment_running:
                return False

            rows = load_cases()
            candidate_identities = self._collect_detail_enrichment_candidates(rows)
            started_at = datetime.now().isoformat(timespec="seconds")

            if not candidate_identities:
                self._set_detail_enrichment_state(
                    {
                        "status": "completed",
                        "started_at": started_at,
                        "finished_at": started_at,
                        "candidate_count": 0,
                        "processed_count": 0,
                        "updated_count": 0,
                        "fetch_error_count": 0,
                        "forbidden_count": 0,
                        "parse_empty_count": 0,
                        "enriched_count": 0,
                        "last_error": "",
                        "last_updated_at": started_at,
                    }
                )
                return False

            self._detail_enrichment_running = True
            self._set_detail_enrichment_state(
                {
                    "status": "running",
                    "started_at": started_at,
                    "candidate_count": len(candidate_identities),
                    "processed_count": 0,
                    "updated_count": 0,
                    "fetch_error_count": 0,
                    "forbidden_count": 0,
                    "parse_empty_count": 0,
                    "enriched_count": 0,
                    "last_error": "",
                    "last_updated_at": started_at,
                }
            )

        worker = Thread(
            target=self._run_detail_enrichment_job_with_candidates,
            args=(candidate_identities,),
            daemon=True,
            name="checkee-detail-enrichment",
        )
        worker.start()
        return True

    def trigger_detail_enrichment(self) -> dict[str, Any]:
        started = self._start_detail_enrichment_job()
        state = self._detail_enrichment_state()
        status = str(state.get("status") or "idle")
        if started:
            return {"started": True, "status": status, "message": "detail enrichment started", "state": state}
        if self._detail_enrichment_running:
            return {"started": False, "status": "running", "message": "detail enrichment already running", "state": state}
        if status == "completed" and int(state.get("candidate_count") or 0) == 0:
            return {"started": False, "status": "completed", "message": "no note candidates", "state": state}
        return {"started": False, "status": status, "message": "detail enrichment not started", "state": state}

    def _refresh_job_state(self) -> dict[str, Any]:
        meta = load_meta()
        state = meta.get("refresh_job")
        return dict(state) if isinstance(state, dict) else {"status": "idle"}

    def _set_refresh_job_state(self, payload: dict[str, Any]) -> None:
        meta = load_meta()
        save_meta({**meta, "refresh_job": payload}, update_timestamp=False)

    def _run_refresh_job(
        self,
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
        started_at: str,
    ) -> None:
        try:
            self._set_refresh_job_state(
                {
                    "triggered_by": triggered_by,
                    "status": "running",
                    "started_at": started_at,
                    "finished_at": None,
                    "all_months": all_months,
                    "months": months,
                    "from_month": from_month,
                    "sources": sources or [],
                    "last_error": "",
                    "last_updated_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            result = self.refresh(
                all_months=all_months,
                months=months,
                from_month=from_month,
                sources=sources,
                triggered_by=triggered_by,
            )
            self._set_refresh_job_state(
                {
                    "triggered_by": triggered_by,
                    "status": "completed",
                    "started_at": started_at,
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                    "all_months": all_months,
                    "months": months,
                    "from_month": from_month,
                    "sources": sources or [],
                    "last_error": "",
                    "last_updated_at": datetime.now().isoformat(timespec="seconds"),
                    "result": {
                        "total_cases": int(result.get("total_cases") or 0),
                        "fetched_month_count": len(result.get("fetched_months") or []),
                    },
                }
            )
        except Exception as exc:  # noqa: BLE001
            self.record_refresh_event(
                status="error",
                message=f"admin async refresh failed: {exc}",
                triggered_by=triggered_by,
            )
            self._set_refresh_job_state(
                {
                    "triggered_by": triggered_by,
                    "status": "failed",
                    "started_at": started_at,
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                    "all_months": all_months,
                    "months": months,
                    "from_month": from_month,
                    "sources": sources or [],
                    "last_error": str(exc),
                    "last_updated_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
        finally:
            with self._lock:
                self._refresh_job_running = False

    def start_refresh_job(
        self,
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
    ) -> dict[str, Any]:
        with self._lock:
            if self._refresh_job_running:
                state = self._refresh_job_state()
                return {"started": False, "message": "refresh job already running", "state": state}
            self._refresh_job_running = True
            started_at = datetime.now().isoformat(timespec="seconds")
            self._set_refresh_job_state(
                {
                    "triggered_by": triggered_by,
                    "status": "started",
                    "started_at": started_at,
                    "finished_at": None,
                    "all_months": all_months,
                    "months": months,
                    "from_month": from_month,
                    "sources": sources or [],
                    "last_error": "",
                    "last_updated_at": started_at,
                }
            )

        worker = Thread(
            target=self._run_refresh_job,
            kwargs={
                "all_months": all_months,
                "months": months,
                "from_month": from_month,
                "sources": sources,
                "triggered_by": triggered_by,
                "started_at": started_at,
            },
            daemon=True,
            name="checkee-admin-refresh",
        )
        worker.start()
        state = self._refresh_job_state()
        return {"started": True, "message": "refresh job started", "state": state}

    def get_refresh_job_state(self) -> dict[str, Any]:
        return self._refresh_job_state()

    def get_detail_enrichment_state(self) -> dict[str, Any]:
        return self._detail_enrichment_state()

    def record_refresh_event(
        self,
        *,
        status: str,
        message: str,
        triggered_by: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            meta = load_meta()
            entry: dict[str, Any] = {
                "occurred_at": datetime.now().isoformat(timespec="seconds"),
                "status": status,
                "message": message,
                "triggered_by": triggered_by,
            }
            if details:
                entry["details"] = details

            history = self._append_refresh_history(meta.get("refresh_history"), entry)
            payload = {
                **meta,
                "last_refresh_result": entry,
                "refresh_history": history,
            }
            save_meta(payload, update_timestamp=False)

    def refresh(
        self,
        all_months: bool = False,
        months: int = 6,
        from_month: str | None = None,
        sources: list[str] | None = None,
        triggered_by: str = "manual",
    ) -> dict[str, Any]:
        with self._lock:
            self._enforce_refresh_interval()
            requested_from_month = str(from_month or "").strip() or None
            effective_from_month, range_preserved = self._auto_refresh_effective_from_month(
                all_months=all_months,
                months=months,
                from_month=requested_from_month,
                triggered_by=triggered_by,
            )
            fetch_from_month = effective_from_month if effective_from_month else requested_from_month
            previous_rows = load_cases()
            fetch_result: FetchResult = fetch_cases(
                all_months=all_months,
                months=months,
                from_month=fetch_from_month,
                sources=sources,
            )
            rows = fetch_result.rows
            payload = [asdict(r) if isinstance(r, CaseRow) else r for r in rows]
            merged_detail_count = self._merge_existing_detail_fields(payload, previous_rows)
            classification_metrics = self._ensure_major_classification(payload)
            coverage = {
                **fetch_result.coverage,
                "detail_merged_from_history_count": merged_detail_count,
                **classification_metrics,
            }
            data_quality = self._compute_data_quality(payload)

            save_cases(payload)
            monthly = analytics.monthly_stats(payload)
            save_monthly(monthly)

            report = analytics.markdown_report(payload)
            save_report(report)

            previous_meta = load_meta()
            success_entry = {
                "occurred_at": datetime.now().isoformat(timespec="seconds"),
                "status": "success",
                "message": "refresh completed",
                "triggered_by": triggered_by,
                "details": {
                    "total_cases": len(payload),
                    "fetched_month_count": len(fetch_result.fetched_months),
                    "selected_sources": fetch_result.selected_sources,
                    "requested_from_month": requested_from_month,
                    "effective_from_month": fetch_from_month,
                    "range_preserved": range_preserved,
                },
            }

            save_meta(
                {
                    "fetched_months": fetch_result.fetched_months,
                    "fetched_month_count": len(fetch_result.fetched_months),
                    "total_cases": len(payload),
                    "all_months": all_months,
                    "months_arg": months,
                    "from_month": requested_from_month,
                    "refresh_effective_from_month": fetch_from_month,
                    "refresh_range_preserved": range_preserved,
                    "requested_sources": sources,
                    "selected_sources": fetch_result.selected_sources,
                    "supported_sources": list_supported_sources(),
                    "truncated_by_limit": fetch_result.truncated_by_limit,
                    "month_limit": MAX_FETCH_MONTHS,
                    "source_discovery": fetch_result.source_discovery,
                    "source_discovery_count": len(fetch_result.source_discovery),
                    "coverage": coverage,
                    "data_quality": data_quality,
                    "major_classification": {
                        "category_l1_options": self._taxonomy_l1_options(self._taxonomy_rules()),
                        "category_l2_options": self._taxonomy_l2_options(self._taxonomy_rules()),
                        **classification_metrics,
                    },
                    "last_refresh_result": success_entry,
                    "refresh_history": self._append_refresh_history(
                        previous_meta.get("refresh_history"),
                        success_entry,
                    ),
                }
            )

            detail_enrichment_started = False
            if bool(fetch_result.coverage.get("detail_deferred")) and not DETAIL_FETCH_SYNC_ON_REFRESH:
                detail_enrichment_started = self._start_detail_enrichment_job()

            return {
                "success": True,
                "message": "refresh completed",
                "fetched_months": fetch_result.fetched_months,
                "total_cases": len(payload),
                "selected_sources": fetch_result.selected_sources,
                "truncated_by_limit": fetch_result.truncated_by_limit,
                "month_limit": MAX_FETCH_MONTHS,
                "generated_at": datetime.now(),
                "detail_enrichment_started": detail_enrichment_started,
                "effective_from_month": fetch_from_month,
                "range_preserved": range_preserved,
            }

    def _enforce_refresh_interval(self) -> None:
        if REFRESH_MIN_INTERVAL_SECONDS <= 0:
            return

        meta = load_meta()
        updated_at_raw = meta.get("updated_at")
        if not updated_at_raw:
            return

        try:
            updated_dt = datetime.fromisoformat(str(updated_at_raw))
        except ValueError:
            return

        elapsed_seconds = max(0, int((datetime.now() - updated_dt).total_seconds()))
        if elapsed_seconds < REFRESH_MIN_INTERVAL_SECONDS:
            raise RefreshRateLimitError(REFRESH_MIN_INTERVAL_SECONDS - elapsed_seconds)

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
        rows = load_cases()
        if not rows:
            return rows

        before_snapshot = [
            (
                str(row.get("major_category_l1") or "").strip(),
                str(row.get("major_category_l2") or "").strip(),
                str(row.get("major_classification_source") or "").strip(),
            )
            for row in rows
        ]
        self._ensure_major_classification(rows)
        after_snapshot = [
            (
                str(row.get("major_category_l1") or "").strip(),
                str(row.get("major_category_l2") or "").strip(),
                str(row.get("major_classification_source") or "").strip(),
            )
            for row in rows
        ]
        if before_snapshot != after_snapshot:
            with self._lock:
                save_cases(rows)
        return rows

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

    def get_recommendation(
        self,
        rows: list[dict[str, str]],
        *,
        data_freshness_seconds: int | None = None,
    ) -> dict[str, Any]:
        return analytics.recommendation_stats(rows, data_freshness_seconds=data_freshness_seconds)

    def get_options(self, rows: list[dict[str, str]]) -> dict[str, Any]:
        options_payload = analytics.options(rows)
        rules = self._taxonomy_rules()

        l1_options = set(options_payload.get("major_categories_l1") or [])
        l1_options.update(self._taxonomy_l1_options(rules))

        l2_options = set(options_payload.get("major_categories_l2") or [])
        l2_options.update(self._taxonomy_l2_options(rules))

        mapping_raw = options_payload.get("major_category_mapping") or {}
        mapping: dict[str, set[str]] = {
            str(category_l1): {str(item) for item in values}
            for category_l1, values in mapping_raw.items()
        }

        for category_l1 in l1_options:
            mapping.setdefault(category_l1, set()).add(major_classifier.MAJOR_UNSPECIFIED_L2)

        options_payload["major_categories_l1"] = sorted(l1_options)
        options_payload["major_categories_l2"] = sorted(l2_options)
        options_payload["major_category_mapping"] = {
            category_l1: sorted(values)
            for category_l1, values in sorted(mapping.items(), key=lambda item: item[0])
        }
        return options_payload

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
        majors: set[str] | None,
        major_categories_l1: set[str] | None,
        major_categories_l2: set[str] | None,
        employers: set[str] | None,
        detail_cities: set[str] | None,
        detail_states: set[str] | None,
        has_note: bool | None,
        search_text: str | None,
    ) -> list[dict[str, str]]:
        return analytics.filter_rows(
            rows,
            visa_types=visa_types,
            consulates=consulates,
            statuses=statuses,
            entries=entries,
            months=months,
            majors=majors,
            major_categories_l1=major_categories_l1,
            major_categories_l2=major_categories_l2,
            employers=employers,
            detail_cities=detail_cities,
            detail_states=detail_states,
            has_note=has_note,
            search_text=search_text,
        )

    def get_major_classifications(self, rows: list[dict[str, str]], query: str | None, limit: int = 500) -> dict[str, Any]:
        rules = self._taxonomy_rules()
        overrides = self._major_overrides()
        items = major_classifier.major_classification_items(rows, overrides, rules)

        keyword = (query or "").strip().lower()
        if keyword:
            items = [
                item
                for item in items
                if keyword in str(item.get("major") or "").lower()
                or keyword in str(item.get("major_normalized") or "").lower()
            ]

        return {
            "total": len(items),
            "items": items[: max(1, limit)],
            "category_l1_options": self._taxonomy_l1_options(rules),
            "category_l2_options": self._taxonomy_l2_options(rules),
        }

    def upsert_major_overrides(
        self,
        items: list[dict[str, str]],
        *,
        operator: str,
    ) -> int:
        updated = 0
        now = datetime.now().isoformat(timespec="seconds")

        with self._lock:
            overrides = self._major_overrides()
            for item in items:
                major = str(item.get("major") or "").strip()
                major_norm = major_classifier.normalize_major(major)
                if not major_norm:
                    continue
                if major_classifier.is_not_applicable_major(major_norm):
                    continue

                category_l1 = str(item.get("category_l1") or "").strip() or "Other"
                category_l2 = str(item.get("category_l2") or "").strip() or "Unspecified"

                overrides[major_norm] = {
                    "major": major,
                    "category_l1": category_l1,
                    "category_l2": category_l2,
                    "updated_at": now,
                    "updated_by": operator,
                }
                updated += 1

            save_major_overrides(overrides)
            rows = load_cases()
            if rows:
                self._reclassify_and_save_rows(rows)

        return updated

    def delete_major_override(self, major: str) -> bool:
        major_norm = major_classifier.normalize_major(major)
        if not major_norm:
            return False
        if major_classifier.is_not_applicable_major(major_norm):
            return False

        with self._lock:
            overrides = self._major_overrides()
            if major_norm not in overrides:
                return False

            overrides.pop(major_norm, None)
            save_major_overrides(overrides)
            rows = load_cases()
            if rows:
                self._reclassify_and_save_rows(rows)

        return True

    def get_meta(self) -> dict[str, Any]:
        meta = load_meta()
        rows = self.get_cases()
        now = datetime.now()

        meta.setdefault("supported_sources", list_supported_sources())
        if "selected_sources" not in meta and "supported_sources" in meta:
            meta["selected_sources"] = meta["supported_sources"]

        updated_at_raw = meta.get("updated_at")
        freshness_seconds: int | None = None
        refresh_available_in_seconds = 0
        if updated_at_raw:
            try:
                updated_dt = datetime.fromisoformat(str(updated_at_raw))
                freshness_seconds = max(0, int((now - updated_dt).total_seconds()))
                refresh_available_in_seconds = max(0, REFRESH_MIN_INTERVAL_SECONDS - freshness_seconds)
            except ValueError:
                freshness_seconds = None
                refresh_available_in_seconds = 0

        fetched_months = meta.get("fetched_months") or []
        return {
            **meta,
            "has_data": len(rows) > 0,
            "current_case_count": len(rows),
            "data_freshness_seconds": freshness_seconds,
            "refresh_min_interval_seconds": REFRESH_MIN_INTERVAL_SECONDS,
            "refresh_available_in_seconds": refresh_available_in_seconds,
            "fetched_month_range": {
                "latest": fetched_months[0] if fetched_months else None,
                "earliest": fetched_months[-1] if fetched_months else None,
            },
        }


service = DataService()
