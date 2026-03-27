from __future__ import annotations

from datetime import datetime


def test_refresh_months_out_of_range(client) -> None:
    response = client.post("/api/v1/tasks/refresh", json={"months": 0})
    assert response.status_code == 422


def test_refresh_invalid_from_month_returns_400(client, monkeypatch) -> None:
    from app.api import routes

    def fake_refresh(*, all_months: bool, months: int, from_month: str | None):
        raise ValueError("from_month must be in YYYY-MM format")

    monkeypatch.setattr(routes.service, "refresh", fake_refresh)
    response = client.post(
        "/api/v1/tasks/refresh",
        json={"all_months": False, "months": 6, "from_month": "2024/01"},
    )
    assert response.status_code == 400
    assert "YYYY-MM" in response.json()["detail"]


def test_refresh_success_payload(client, monkeypatch) -> None:
    from app.api import routes

    def fake_refresh(*, all_months: bool, months: int, from_month: str | None):
        return {
            "success": True,
            "message": "refresh completed",
            "fetched_months": ["2026-03", "2026-02"],
            "total_cases": 123,
            "truncated_by_limit": False,
            "month_limit": 120,
            "generated_at": datetime.now(),
        }

    monkeypatch.setattr(routes.service, "refresh", fake_refresh)
    response = client.post("/api/v1/tasks/refresh", json={"months": 2})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["total_cases"] == 123
    assert payload["fetched_months"] == ["2026-03", "2026-02"]
