from __future__ import annotations

from app.services import storage
from app.services.data_service import DataService
from app.services.scraper import CaseRow, FetchResult


def _minimal_fetch_result() -> FetchResult:
    return FetchResult(
        rows=[
            CaseRow(
                source_month="2026-03",
                case_number="A001",
                nickname="alpha",
                visa_type="F1",
                visa_entry="I20",
                consulate="BeiJing",
                major="CS",
                status="Pending",
                check_date="2026-03-01",
                complete_date="",
                waiting_days_reported="",
                waiting_days_calc="",
                observed_days="10",
                event=0,
                detail_url="https://example.com/detail/A001",
                update_url="https://example.com/update/A001",
                detail_employer="",
                detail_note="",
                detail_city="",
                detail_state="",
            )
        ],
        fetched_months=["2026-03", "2026-02", "2026-01"],
        truncated_by_limit=False,
        selected_sources=["monthly_track"],
        source_discovery={},
        coverage={
            "selected_sources": ["monthly_track"],
            "available_month_count": 3,
            "selected_month_count": 3,
            "parsed_month_count": 3,
            "months_with_rows": ["2026-03", "2026-02", "2026-01"],
            "months_without_rows": [],
            "raw_case_count": 1,
            "deduped_case_count": 1,
            "dedup_removed_count": 0,
            "detail_deferred": False,
        },
    )


def test_auto_refresh_preserves_historical_window(monkeypatch) -> None:
    service = DataService()
    captured: dict[str, str | None] = {}

    storage.save_meta(
        {
            "fetched_months": ["2026-03", "2026-02", "2025-03"],
        },
        update_timestamp=False,
    )

    def fake_fetch_cases(*, all_months: bool, months: int, from_month: str | None, sources: list[str] | None) -> FetchResult:
        captured["from_month"] = from_month
        return _minimal_fetch_result()

    monkeypatch.setattr(service, "_enforce_refresh_interval", lambda: None)
    monkeypatch.setattr(service, "_current_month_token", lambda: "2026-03")
    monkeypatch.setattr("app.services.data_service.fetch_cases", fake_fetch_cases)

    result = service.refresh(
        all_months=False,
        months=6,
        from_month=None,
        sources=["monthly_track"],
        triggered_by="scheduled",
    )

    meta = storage.load_meta()
    assert captured["from_month"] == "2025-03"
    assert result["effective_from_month"] == "2025-03"
    assert result["range_preserved"] is True
    assert meta["refresh_effective_from_month"] == "2025-03"
    assert meta["refresh_range_preserved"] is True
    assert meta["last_refresh_result"]["details"]["effective_from_month"] == "2025-03"
    assert meta["last_refresh_result"]["details"]["range_preserved"] is True


def test_auto_refresh_without_history_keeps_original_window(monkeypatch) -> None:
    service = DataService()
    captured: dict[str, str | None] = {}

    storage.save_meta({}, update_timestamp=False)

    def fake_fetch_cases(*, all_months: bool, months: int, from_month: str | None, sources: list[str] | None) -> FetchResult:
        captured["from_month"] = from_month
        return _minimal_fetch_result()

    monkeypatch.setattr(service, "_enforce_refresh_interval", lambda: None)
    monkeypatch.setattr(service, "_current_month_token", lambda: "2026-03")
    monkeypatch.setattr("app.services.data_service.fetch_cases", fake_fetch_cases)

    result = service.refresh(
        all_months=False,
        months=6,
        from_month=None,
        sources=["monthly_track"],
        triggered_by="scheduled",
    )

    meta = storage.load_meta()
    assert captured["from_month"] is None
    assert result["effective_from_month"] is None
    assert result["range_preserved"] is False
    assert meta["refresh_effective_from_month"] is None
    assert meta["refresh_range_preserved"] is False


def test_manual_refresh_does_not_force_preserve_window(monkeypatch) -> None:
    service = DataService()
    captured: dict[str, str | None] = {}

    storage.save_meta(
        {
            "fetched_months": ["2026-03", "2026-02", "2025-03"],
        },
        update_timestamp=False,
    )

    def fake_fetch_cases(*, all_months: bool, months: int, from_month: str | None, sources: list[str] | None) -> FetchResult:
        captured["from_month"] = from_month
        return _minimal_fetch_result()

    monkeypatch.setattr(service, "_enforce_refresh_interval", lambda: None)
    monkeypatch.setattr(service, "_current_month_token", lambda: "2026-03")
    monkeypatch.setattr("app.services.data_service.fetch_cases", fake_fetch_cases)

    result = service.refresh(
        all_months=False,
        months=6,
        from_month=None,
        sources=["monthly_track"],
        triggered_by="manual",
    )

    meta = storage.load_meta()
    assert captured["from_month"] is None
    assert result["effective_from_month"] is None
    assert result["range_preserved"] is False
    assert meta["refresh_effective_from_month"] is None
    assert meta["refresh_range_preserved"] is False
