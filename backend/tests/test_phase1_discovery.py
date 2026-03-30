from __future__ import annotations

import requests

from app.services.data_service import DataService
import pytest

from app.services.scraper import (
    CaseRow,
    FetchResult,
    _extract_detail_fields,
    _extract_entry_points,
    _enrich_detail_fields,
    _normalize_sources,
    list_supported_sources,
)
from app.services.storage import load_meta


def test_extract_entry_points_collects_links_and_forms() -> None:
    html = """
    <html>
      <body>
        <a href="index.php">Home</a>
        <a href="report_case.php">Add Your Case</a>
        <a href="/donation.php"></a>
        <form action="main.php" method="get">Monthly Case GO</form>
        <form action="search.php" method="post">Search your email address GO</form>
      </body>
    </html>
    """

    entry_points = _extract_entry_points(html)

    assert "link_home" in entry_points
    assert entry_points["link_home"].endswith("index.php")

    assert "link_add_your_case" in entry_points
    assert entry_points["link_add_your_case"].endswith("report_case.php")

    assert "form_monthly_case_go" in entry_points
    assert entry_points["form_monthly_case_go"].endswith("main.php")

    assert "form_search_your_email_address_go" in entry_points
    assert entry_points["form_search_your_email_address_go"].endswith("search.php")


def test_normalize_sources_accepts_alias_and_dedupes() -> None:
    sources = _normalize_sources(["monthly-track", "latest_snapshot", "latest_snapshot"])
    assert sources == ["monthly_track", "latest_snapshot"]
    assert "monthly_track" in list_supported_sources()
    assert "latest_snapshot" in list_supported_sources()


def test_normalize_sources_rejects_unsupported() -> None:
    with pytest.raises(ValueError):
        _normalize_sources(["legacy_table"])


def test_extract_detail_fields_supports_inline_note_cells() -> None:
    html = """
    <html>
      <body>
        <table border="1">
          <tr><td>Employer: N/A</td><td>Status: Clear</td></tr>
          <tr>
            <td colspan="2">
              Note:<br>
              interview 2.5 <br><br>
              Submit documents via email 2.6 <br><br>
              issued 3.18
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    fields = _extract_detail_fields(html)
    assert fields["detail_employer"] == ""
    assert "interview 2.5" in fields["detail_note"]
    assert "issued 3.18" in fields["detail_note"]


def test_enrich_detail_fields_force_note_fetch_when_ratio_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
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
            detail_url="https://example.com/detail/1",
            update_url="https://example.com/update/1",
            detail_employer="",
            detail_note="",
            detail_city="",
            detail_state="",
        ),
        CaseRow(
            source_month="2026-03",
            case_number="A002",
            nickname="beta",
            visa_type="F1",
            visa_entry="I20",
            consulate="ShangHai",
            major="Math",
            status="Pending",
            check_date="2026-03-02",
            complete_date="",
            waiting_days_reported="",
            waiting_days_calc="",
            observed_days="9",
            event=0,
            detail_url="https://example.com/detail/2",
            update_url="https://example.com/update/2",
            detail_employer="",
            detail_note="",
            detail_city="",
            detail_state="",
        ),
    ]

    calls: list[str] = []

    def fake_fetch_html(_session: requests.Session, url: str) -> str:
        calls.append(url)
        return """
        <html><body><table>
          <tr><td>Note: interview 2.5; issued 3.18</td></tr>
        </table></body></html>
        """

    monkeypatch.setattr("app.services.scraper.DETAIL_FETCH_REQUIRE_NOTE", True)
    monkeypatch.setattr("app.services.scraper._fetch_html", fake_fetch_html)

    metrics = _enrich_detail_fields(rows, requests.Session(), sample_ratio=0.0)

    assert len(calls) == 2
    assert metrics["detail_candidate_count"] == 2
    assert metrics["detail_sampled_count"] == 2
    assert metrics["detail_skipped_count"] == 0
    assert metrics["detail_enriched_count"] == 2
    assert metrics["detail_require_note"] is True
    assert all("issued 3.18" in row.detail_note for row in rows)


def test_enrich_detail_fields_respects_sampling_when_force_note_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        CaseRow(
            source_month="2026-03",
            case_number="A003",
            nickname="gamma",
            visa_type="F1",
            visa_entry="I20",
            consulate="GuangZhou",
            major="Physics",
            status="Pending",
            check_date="2026-03-03",
            complete_date="",
            waiting_days_reported="",
            waiting_days_calc="",
            observed_days="8",
            event=0,
            detail_url="https://example.com/detail/3",
            update_url="https://example.com/update/3",
            detail_employer="",
            detail_note="",
            detail_city="",
            detail_state="",
        )
    ]

    monkeypatch.setattr("app.services.scraper.DETAIL_FETCH_REQUIRE_NOTE", False)

    metrics = _enrich_detail_fields(rows, requests.Session(), sample_ratio=0.0)

    assert metrics["detail_candidate_count"] == 1
    assert metrics["detail_sampled_count"] == 0
    assert metrics["detail_skipped_count"] == 1
    assert metrics["detail_require_note"] is False


def test_refresh_writes_source_and_quality_meta(monkeypatch) -> None:
    service = DataService()

    def fake_fetch_cases(
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
    ) -> FetchResult:
        return FetchResult(
            rows=[
                CaseRow(
                    source_month="2026-03",
                    case_number="",
                    nickname="alpha",
                    visa_type="F1",
                    visa_entry="I20",
                    consulate="BeiJing",
                    major="CS",
                    status="Clear",
                    check_date="2026-03-01",
                    complete_date="0000-00-00",
                    waiting_days_reported="",
                    waiting_days_calc="",
                    observed_days="",
                    event=1,
                    detail_url="",
                    update_url="https://example.com/update/1",
                    detail_employer="",
                    detail_note="",
                    detail_city="",
                    detail_state="",
                ),
                CaseRow(
                    source_month="2026-03",
                    case_number="A002",
                    nickname="beta",
                    visa_type="H1B",
                    visa_entry="I129",
                    consulate="Toronto",
                    major="Math",
                    status="Pending",
                    check_date="",
                    complete_date="",
                    waiting_days_reported="",
                    waiting_days_calc="",
                    observed_days="10",
                    event=0,
                    detail_url="https://example.com/detail/2",
                    update_url="",
                    detail_employer="ByteDance",
                    detail_note="pending update",
                    detail_city="Paris",
                    detail_state="Ile-de-France",
                ),
            ],
            fetched_months=["2026-03"],
            truncated_by_limit=False,
            selected_sources=["monthly_track"],
            source_discovery={"link_home": "https://checkee.info/index.php"},
            coverage={
                "selected_sources": ["monthly_track"],
                "available_month_count": 3,
                "selected_month_count": 1,
                "parsed_month_count": 1,
                "months_with_rows": ["2026-03"],
                "months_without_rows": [],
                "raw_case_count": 2,
                "deduped_case_count": 2,
                "dedup_removed_count": 0,
            },
        )

    monkeypatch.setattr("app.services.data_service.fetch_cases", fake_fetch_cases)

    service.refresh(all_months=False, months=1, from_month=None, sources=["monthly_track"])
    meta = load_meta()

    assert meta["source_discovery_count"] == 1
    assert "link_home" in meta["source_discovery"]
    assert meta["selected_sources"] == ["monthly_track"]
    assert meta["requested_sources"] == ["monthly_track"]
    assert "monthly_track" in meta["supported_sources"]

    assert meta["coverage"]["selected_month_count"] == 1
    assert meta["coverage"]["raw_case_count"] == 2

    quality = meta["data_quality"]
    assert quality["total_rows"] == 2
    assert quality["missing_case_number_count"] == 1
    assert quality["missing_detail_url_count"] == 1
    assert quality["missing_update_url_count"] == 1
    assert quality["invalid_check_date_count"] == 1
    assert quality["finalized_missing_complete_date_count"] == 1
