from __future__ import annotations

from datetime import datetime


def test_refresh_months_out_of_range(client) -> None:
    response = client.post("/api/v1/tasks/refresh", json={"months": 0})
    assert response.status_code == 422


def test_refresh_invalid_from_month_returns_400(client, monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "REFRESH_REQUIRE_ADMIN_KEY", False)

    def fake_refresh(
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
    ):
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

    monkeypatch.setattr(routes, "REFRESH_REQUIRE_ADMIN_KEY", False)

    captured: dict[str, str] = {}

    def fake_refresh(
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
    ):
        captured["triggered_by"] = triggered_by
        return {
            "success": True,
            "message": "refresh completed",
            "fetched_months": ["2026-03", "2026-02"],
            "total_cases": 123,
            "selected_sources": ["monthly_track"],
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
    assert payload["selected_sources"] == ["monthly_track"]
    assert captured["triggered_by"] == "manual"


def test_refresh_unsupported_sources_returns_400(client, monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "REFRESH_REQUIRE_ADMIN_KEY", False)

    def fake_refresh(
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
    ):
        raise ValueError("unsupported sources: legacy_table; supported sources: monthly_track")

    monkeypatch.setattr(routes.service, "refresh", fake_refresh)
    response = client.post(
        "/api/v1/tasks/refresh",
        json={"all_months": False, "months": 3, "sources": ["legacy_table"]},
    )
    assert response.status_code == 400
    assert "unsupported sources" in response.json()["detail"]


def test_refresh_requires_admin_key_when_enabled(client, monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "REFRESH_REQUIRE_ADMIN_KEY", True)
    monkeypatch.setattr(routes, "ADMIN_REFRESH_KEY", "test-admin-key")

    captured: dict[str, str] = {}

    def fake_refresh(
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
    ):
        captured["triggered_by"] = triggered_by
        return {
            "success": True,
            "message": "refresh completed",
            "fetched_months": ["2026-03"],
            "total_cases": 10,
            "selected_sources": ["monthly_track"],
            "truncated_by_limit": False,
            "month_limit": 120,
            "generated_at": datetime.now(),
        }

    monkeypatch.setattr(routes.service, "refresh", fake_refresh)

    response = client.post("/api/v1/tasks/refresh", json={"months": 2})
    assert response.status_code == 403
    state_payload = client.get("/api/v1/meta/state").json()
    assert state_payload["refresh_history"][0]["status"] == "denied"

    response = client.post(
        "/api/v1/tasks/refresh",
        json={"months": 2},
        headers={"X-Admin-Key": "wrong-key"},
    )
    assert response.status_code == 403
    denied_with_key = client.get("/api/v1/meta/state").json()["refresh_history"][0]
    assert denied_with_key["triggered_by"] == "scheduled"

    response = client.post(
        "/api/v1/tasks/refresh",
        json={"months": 2},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert response.status_code == 200
    assert captured["triggered_by"] == "scheduled"


def test_refresh_cooldown_returns_429(client, monkeypatch) -> None:
    from app.api import routes
    from app.services.data_service import RefreshRateLimitError

    monkeypatch.setattr(routes, "REFRESH_REQUIRE_ADMIN_KEY", False)

    def fake_refresh(
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
    ):
        raise RefreshRateLimitError(119)

    monkeypatch.setattr(routes.service, "refresh", fake_refresh)

    response = client.post("/api/v1/tasks/refresh", json={"months": 2})
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "119"
    assert "retry in 119s" in response.json()["detail"]

    state_payload = client.get("/api/v1/meta/state").json()
    assert state_payload["refresh_history"][0]["status"] == "blocked"


def test_admin_stale_refresh_fresh_enough(client, monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "_require_admin_session", lambda request: datetime.now())
    monkeypatch.setattr(
        routes.service,
        "get_meta",
        lambda: {
            "updated_at": "2026-03-29T10:00:00",
            "data_freshness_seconds": 1800,
        },
    )

    response = client.post("/api/v1/admin/refresh/stale-trigger")
    assert response.status_code == 200
    payload = response.json()
    assert payload["triggered"] is False
    assert payload["reason"] == "fresh_enough"
    assert payload["updated_at"] == "2026-03-29T10:00:00"


def test_admin_stale_refresh_triggered(client, monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "_require_admin_session", lambda request: datetime.now())
    meta_calls = [
        {
            "updated_at": "2026-03-28T10:00:00",
            "data_freshness_seconds": 90000,
            "selected_sources": ["monthly_track"],
            "months_arg": 6,
            "from_month": None,
        },
        {
            "updated_at": "2026-03-29T10:30:00",
            "data_freshness_seconds": 0,
            "selected_sources": ["monthly_track"],
            "months_arg": 6,
            "from_month": None,
        },
    ]

    monkeypatch.setattr(routes.service, "get_meta", lambda: meta_calls.pop(0))
    def fake_refresh(*, all_months: bool, months: int, from_month: str | None, sources: list[str] | None, triggered_by: str):
        assert triggered_by == "auto_fallback"
        return {
            "success": True,
            "message": "refresh completed",
            "fetched_months": ["2026-03"],
            "total_cases": 123,
            "selected_sources": sources,
            "truncated_by_limit": False,
            "month_limit": 120,
            "generated_at": datetime.now(),
        }

    monkeypatch.setattr(routes.service, "refresh", fake_refresh)

    response = client.post("/api/v1/admin/refresh/stale-trigger")
    assert response.status_code == 200
    payload = response.json()
    assert payload["triggered"] is True
    assert payload["reason"] == "stale_triggered"
    assert payload["updated_at"] == "2026-03-29T10:30:00"


def test_admin_stale_refresh_cooldown(client, monkeypatch) -> None:
    from app.api import routes
    from app.services.data_service import RefreshRateLimitError

    monkeypatch.setattr(routes, "_require_admin_session", lambda request: datetime.now())
    monkeypatch.setattr(
        routes.service,
        "get_meta",
        lambda: {
            "updated_at": "2026-03-29T10:00:00",
            "data_freshness_seconds": 90000,
            "selected_sources": ["monthly_track"],
            "months_arg": 6,
            "from_month": None,
        },
    )

    def fake_refresh(
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
    ):
        assert triggered_by == "auto_fallback"
        raise RefreshRateLimitError(123)

    monkeypatch.setattr(routes.service, "refresh", fake_refresh)

    response = client.post("/api/v1/admin/refresh/stale-trigger")
    assert response.status_code == 200
    payload = response.json()
    assert payload["triggered"] is False
    assert payload["reason"] == "cooldown"
    assert "123s" in payload["message"]


def test_admin_stale_refresh_error(client, monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "_require_admin_session", lambda request: datetime.now())
    monkeypatch.setattr(
        routes.service,
        "get_meta",
        lambda: {
            "updated_at": "2026-03-29T10:00:00",
            "data_freshness_seconds": 90000,
            "selected_sources": ["monthly_track"],
            "months_arg": 6,
            "from_month": None,
        },
    )

    def fake_refresh(
        *,
        all_months: bool,
        months: int,
        from_month: str | None,
        sources: list[str] | None,
        triggered_by: str,
    ):
        assert triggered_by == "auto_fallback"
        raise RuntimeError("boom")

    monkeypatch.setattr(routes.service, "refresh", fake_refresh)

    response = client.post("/api/v1/admin/refresh/stale-trigger")
    assert response.status_code == 200
    payload = response.json()
    assert payload["triggered"] is False
    assert payload["reason"] == "error"
    assert payload["message"] == "boom"
