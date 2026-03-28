from __future__ import annotations

from datetime import datetime

import pytest

from app.services.admin_auth import reset_sessions


@pytest.fixture(autouse=True)
def reset_admin_sessions() -> None:
    reset_sessions()


def test_admin_login_requires_configured_key(client, monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "ADMIN_REFRESH_KEY", "")

    response = client.post("/api/v1/admin/login", json={"password": "anything"})
    assert response.status_code == 503


def test_admin_login_and_session_ok(client, monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "ADMIN_REFRESH_KEY", "super-secret")
    monkeypatch.setattr(routes, "ADMIN_SESSION_TTL_SECONDS", 3600)

    login_response = client.post("/api/v1/admin/login", json={"password": "super-secret"})
    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["token"]
    assert payload["expires_at"]

    token = payload["token"]
    session_response = client.get(
        "/api/v1/admin/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is True


def test_admin_login_rejects_wrong_password(client, monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "ADMIN_REFRESH_KEY", "super-secret")

    response = client.post("/api/v1/admin/login", json={"password": "wrong"})
    assert response.status_code == 401


def test_admin_logout_revokes_session(client, monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "ADMIN_REFRESH_KEY", "super-secret")
    monkeypatch.setattr(routes, "ADMIN_SESSION_TTL_SECONDS", 3600)

    login_response = client.post("/api/v1/admin/login", json={"password": "super-secret"})
    token = login_response.json()["token"]

    logout_response = client.post(
        "/api/v1/admin/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200

    session_response = client.get(
        "/api/v1/admin/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert session_response.status_code == 401


def test_refresh_allows_bearer_session_when_admin_key_required(client, monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "REFRESH_REQUIRE_ADMIN_KEY", True)
    monkeypatch.setattr(routes, "ADMIN_REFRESH_KEY", "super-secret")
    monkeypatch.setattr(routes, "ADMIN_SESSION_TTL_SECONDS", 3600)

    def fake_refresh(*, all_months: bool, months: int, from_month: str | None, sources: list[str] | None):
        return {
            "success": True,
            "message": "refresh completed",
            "fetched_months": ["2026-03"],
            "total_cases": 100,
            "selected_sources": ["monthly_track"],
            "truncated_by_limit": False,
            "month_limit": 120,
            "generated_at": datetime.now(),
        }

    monkeypatch.setattr(routes.service, "refresh", fake_refresh)

    login_response = client.post("/api/v1/admin/login", json={"password": "super-secret"})
    token = login_response.json()["token"]

    refresh_response = client.post(
        "/api/v1/tasks/refresh",
        json={"months": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["success"] is True


def test_admin_major_classifications_requires_session(client) -> None:
    response = client.get("/api/v1/admin/major-classifications")
    assert response.status_code == 401


def test_admin_major_classification_override_roundtrip(client, monkeypatch, seed_cases) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "ADMIN_REFRESH_KEY", "super-secret")
    monkeypatch.setattr(routes, "ADMIN_SESSION_TTL_SECONDS", 3600)

    login_response = client.post("/api/v1/admin/login", json={"password": "super-secret"})
    token = login_response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    list_before = client.get("/api/v1/admin/major-classifications", headers=headers)
    assert list_before.status_code == 200
    items_before = list_before.json()["items"]
    cs_row = next(item for item in items_before if item["major"] == "CS")
    assert cs_row["effective_category_l1"] == "STEM"

    update_response = client.put(
        "/api/v1/admin/major-classifications",
        headers=headers,
        json={"items": [{"major": "CS", "category_l1": "Business", "category_l2": "Finance & Accounting"}]},
    )
    assert update_response.status_code == 200
    assert update_response.json()["updated"] == 1

    list_after = client.get("/api/v1/admin/major-classifications", headers=headers, params={"q": "cs"})
    assert list_after.status_code == 200
    cs_after = list_after.json()["items"][0]
    assert cs_after["source"] == "manual"
    assert cs_after["effective_category_l1"] == "Business"

    delete_response = client.delete(
        "/api/v1/admin/major-classifications",
        headers=headers,
        params={"major": "CS"},
    )
    assert delete_response.status_code == 200

    list_reset = client.get("/api/v1/admin/major-classifications", headers=headers, params={"q": "cs"})
    assert list_reset.status_code == 200
    cs_reset = list_reset.json()["items"][0]
    assert cs_reset["source"] in {"auto", "unknown"}
    assert cs_reset["effective_category_l1"] == "STEM"


def test_admin_major_classification_rejects_not_applicable_override(client, monkeypatch, seed_cases) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "ADMIN_REFRESH_KEY", "super-secret")
    monkeypatch.setattr(routes, "ADMIN_SESSION_TTL_SECONDS", 3600)

    login_response = client.post("/api/v1/admin/login", json={"password": "super-secret"})
    token = login_response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_response = client.put(
        "/api/v1/admin/major-classifications",
        headers=headers,
        json={"items": [{"major": "N/A", "category_l1": "Business", "category_l2": "Finance & Accounting"}]},
    )
    assert update_response.status_code == 200
    assert update_response.json()["updated"] == 0
