from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from app.services import storage
from app.services.data_service import DataService


def _seed_detail_rows() -> list[dict[str, Any]]:
    return [
        {
            "source_month": "2026-03",
            "case_number": "N001",
            "nickname": "alpha",
            "visa_type": "F1",
            "visa_entry": "I20",
            "consulate": "BeiJing",
            "major": "CS",
            "status": "Pending",
            "check_date": "2026-03-01",
            "complete_date": "",
            "waiting_days_reported": "",
            "waiting_days_calc": "",
            "observed_days": "10",
            "event": "0",
            "detail_url": "https://example.com/detail/N001",
            "update_url": "https://example.com/update/N001",
            "detail_employer": "",
            "detail_note": "",
            "detail_city": "",
            "detail_state": "",
        },
        {
            "source_month": "2026-03",
            "case_number": "N002",
            "nickname": "beta",
            "visa_type": "F1",
            "visa_entry": "I20",
            "consulate": "ShangHai",
            "major": "Math",
            "status": "Pending",
            "check_date": "2026-03-02",
            "complete_date": "",
            "waiting_days_reported": "",
            "waiting_days_calc": "",
            "observed_days": "9",
            "event": "0",
            "detail_url": "https://example.com/detail/N002",
            "update_url": "https://example.com/update/N002",
            "detail_employer": "",
            "detail_note": "",
            "detail_city": "",
            "detail_state": "",
        },
        {
            "source_month": "2026-03",
            "case_number": "N003",
            "nickname": "gamma",
            "visa_type": "F1",
            "visa_entry": "I20",
            "consulate": "GuangZhou",
            "major": "Physics",
            "status": "Pending",
            "check_date": "2026-03-03",
            "complete_date": "",
            "waiting_days_reported": "",
            "waiting_days_calc": "",
            "observed_days": "8",
            "event": "0",
            "detail_url": "https://example.com/detail/N003",
            "update_url": "https://example.com/update/N003",
            "detail_employer": "",
            "detail_note": "",
            "detail_city": "",
            "detail_state": "",
        },
    ]


def test_detail_enrichment_batch_writes_incrementally(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = _seed_detail_rows()
    storage.save_cases(rows)
    service = DataService()
    service._DETAIL_ENRICHMENT_BATCH_SIZE = 1

    snapshots: list[list[dict[str, Any]]] = []
    original_save_cases = storage.save_cases

    def tracking_save_cases(payload: list[dict[str, Any]]) -> None:
        materialized = [dict(item) for item in payload]
        snapshots.append(materialized)
        original_save_cases(materialized)

    call_seq = {"value": 0}

    def fake_enrich(chunk_rows: list[dict[str, Any]]) -> dict[str, Any]:
        call_seq["value"] += 1
        chunk_rows[0]["detail_note"] = f"note-{call_seq['value']}"
        return {
            "detail_candidate_count": 1,
            "detail_fetch_error_count": 0,
            "detail_forbidden_count": 0,
            "detail_parse_empty_count": 0,
            "detail_enriched_count": 1,
        }

    monkeypatch.setattr("app.services.data_service.save_cases", tracking_save_cases)
    monkeypatch.setattr("app.services.data_service.enrich_missing_details_for_payload_rows", fake_enrich)

    candidates = service._collect_detail_enrichment_candidates(storage.load_cases())
    service._run_detail_enrichment_job_with_candidates(candidates)

    assert len(snapshots) == 3
    assert sum(1 for row in snapshots[0] if str(row.get("detail_note") or "").strip()) == 1
    assert sum(1 for row in snapshots[1] if str(row.get("detail_note") or "").strip()) == 2
    assert sum(1 for row in snapshots[2] if str(row.get("detail_note") or "").strip()) == 3

    state = service.get_detail_enrichment_state()
    assert state["status"] == "completed"
    assert state["candidate_count"] == 3
    assert state["processed_count"] == 3
    assert state["updated_count"] == 3


def test_trigger_detail_enrichment_is_idempotent_when_running() -> None:
    service = DataService()
    service._detail_enrichment_running = True
    storage.save_meta(
        {
            "detail_enrichment": {
                "status": "running",
                "candidate_count": 10,
                "processed_count": 4,
                "updated_count": 2,
            }
        },
        update_timestamp=False,
    )

    payload = service.trigger_detail_enrichment()
    assert payload["started"] is False
    assert payload["status"] == "running"
    assert "already running" in payload["message"]


def test_refresh_job_state_flow_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    service = DataService()
    status_flow: list[str] = []
    original_set_state = service._set_refresh_job_state

    def track_state(payload: dict[str, Any]) -> None:
        status_flow.append(str(payload.get("status") or ""))
        original_set_state(payload)

    def fake_refresh(
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
    ) -> dict[str, Any]:
        return {
            "success": True,
            "message": "refresh completed",
            "fetched_months": ["2026-03"],
            "total_cases": 7,
            "selected_sources": sources or [],
            "truncated_by_limit": False,
            "month_limit": 120,
            "generated_at": datetime.now(),
        }

    monkeypatch.setattr(service, "_set_refresh_job_state", track_state)
    monkeypatch.setattr(service, "refresh", fake_refresh)

    service._run_refresh_job(
        all_months=False,
        months=1,
        from_month=None,
        sources=["monthly_track"],
        triggered_by="manual",
        started_at="2026-03-30T20:10:00",
    )

    state = service.get_refresh_job_state()
    assert status_flow[0] == "running"
    assert status_flow[-1] == "completed"
    assert state["status"] == "completed"
    assert state["triggered_by"] == "manual"
    assert state["result"]["total_cases"] == 7


def test_refresh_job_state_flow_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    service = DataService()
    status_flow: list[str] = []
    original_set_state = service._set_refresh_job_state

    def track_state(payload: dict[str, Any]) -> None:
        status_flow.append(str(payload.get("status") or ""))
        original_set_state(payload)

    def fake_refresh(
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
    ) -> dict[str, Any]:
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "_set_refresh_job_state", track_state)
    monkeypatch.setattr(service, "refresh", fake_refresh)

    service._run_refresh_job(
        all_months=False,
        months=1,
        from_month=None,
        sources=["monthly_track"],
        triggered_by="manual",
        started_at="2026-03-30T20:10:00",
    )

    state = service.get_refresh_job_state()
    assert status_flow[0] == "running"
    assert status_flow[-1] == "failed"
    assert state["status"] == "failed"
    assert "boom" in state["last_error"]


def test_admin_async_endpoints_require_session(client) -> None:
    start_refresh = client.post("/api/v1/admin/refresh/async-start", json={"months": 2})
    assert start_refresh.status_code == 401

    refresh_state = client.get("/api/v1/admin/refresh/async-state")
    assert refresh_state.status_code == 401

    start_note = client.post("/api/v1/admin/detail-enrichment/start")
    assert start_note.status_code == 401

    note_state = client.get("/api/v1/admin/detail-enrichment/state")
    assert note_state.status_code == 401


def test_admin_async_endpoints_proxy_service_calls(client, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api import routes

    captured: dict[str, Any] = {}

    monkeypatch.setattr(routes, "_require_admin_session", lambda request: datetime.now())

    def fake_start_refresh_job(
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
    ) -> dict[str, Any]:
        captured["refresh_payload"] = {
            "all_months": all_months,
            "months": months,
            "from_month": from_month,
            "sources": sources,
            "triggered_by": triggered_by,
        }
        return {"started": True, "message": "refresh job started", "state": {"status": "started"}}

    monkeypatch.setattr(routes.service, "start_refresh_job", fake_start_refresh_job)
    monkeypatch.setattr(routes.service, "get_refresh_job_state", lambda: {"status": "running"})
    monkeypatch.setattr(
        routes.service,
        "trigger_detail_enrichment",
        lambda: {"started": False, "status": "running", "message": "detail enrichment already running"},
    )
    monkeypatch.setattr(
        routes.service,
        "get_detail_enrichment_state",
        lambda: {"status": "running", "processed_count": 10, "candidate_count": 100},
    )

    start_response = client.post(
        "/api/v1/admin/refresh/async-start",
        json={"all_months": False, "months": 2, "from_month": "2026-02", "sources": ["monthly_track"]},
    )
    assert start_response.status_code == 200
    assert start_response.json()["started"] is True
    assert captured["refresh_payload"]["triggered_by"] == "manual"

    state_response = client.get("/api/v1/admin/refresh/async-state")
    assert state_response.status_code == 200
    assert state_response.json()["status"] == "running"

    start_note = client.post("/api/v1/admin/detail-enrichment/start")
    assert start_note.status_code == 200
    assert start_note.json()["status"] == "running"

    note_state = client.get("/api/v1/admin/detail-enrichment/state")
    assert note_state.status_code == 200
    assert note_state.json()["candidate_count"] == 100
