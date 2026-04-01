from __future__ import annotations

import pytest


@pytest.fixture
def enable_user_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "ENABLE_USER_AUTH", True)


@pytest.fixture
def disable_user_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "ENABLE_USER_AUTH", False)


def test_user_register_returns_404_when_feature_disabled(client, disable_user_auth) -> None:
    response = client.post(
        "/api/v1/user/register",
        json={"username": "alice", "password": "password123"},
    )
    assert response.status_code == 404


def test_user_register_login_session_logout_flow(client, enable_user_auth) -> None:
    register_response = client.post(
        "/api/v1/user/register",
        json={"username": "alice", "password": "password123"},
    )
    assert register_response.status_code == 200
    register_payload = register_response.json()
    assert register_payload["username"] == "alice"
    assert register_payload["token"]

    token = register_payload["token"]
    session_response = client.get(
        "/api/v1/user/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is True

    logout_response = client.post(
        "/api/v1/user/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200

    session_after_logout = client.get(
        "/api/v1/user/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert session_after_logout.status_code == 401

    login_response = client.post(
        "/api/v1/user/login",
        json={"username": "alice", "password": "password123"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["username"] == "alice"
    assert login_payload["token"] != token


def test_user_register_duplicate_username_conflict(client, enable_user_auth) -> None:
    first = client.post(
        "/api/v1/user/register",
        json={"username": "bob", "password": "password123"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/user/register",
        json={"username": "bob", "password": "password123"},
    )
    assert second.status_code == 409


def test_user_register_invalid_username(client, enable_user_auth) -> None:
    response = client.post(
        "/api/v1/user/register",
        json={"username": "Bad User", "password": "password123"},
    )
    assert response.status_code == 400
    assert "username" in response.json()["detail"]


def test_user_filter_presets_crud(client, enable_user_auth) -> None:
    register_response = client.post(
        "/api/v1/user/register",
        json={"username": "carol", "password": "password123"},
    )
    token = register_response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    empty_list = client.get("/api/v1/user/filter-presets", headers=headers)
    assert empty_list.status_code == 200
    assert empty_list.json()["total"] == 0

    create_response = client.post(
        "/api/v1/user/filter-presets",
        headers=headers,
        json={
            "name": "F1 Toronto",
            "filters": {
                "visa_types": ["F1"],
                "consulates": ["Toronto"],
            },
        },
    )
    assert create_response.status_code == 200
    created_item = create_response.json()["item"]
    assert created_item["name"] == "F1 Toronto"
    assert created_item["filters"]["visa_types"] == ["F1"]

    duplicate_name_response = client.post(
        "/api/v1/user/filter-presets",
        headers=headers,
        json={"name": "F1 Toronto", "filters": {"visa_types": ["F1"]}},
    )
    assert duplicate_name_response.status_code == 409

    list_response = client.get("/api/v1/user/filter-presets", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    preset_id = created_item["id"]
    update_response = client.put(
        f"/api/v1/user/filter-presets/{preset_id}",
        headers=headers,
        json={
            "name": "F1 Toronto Updated",
            "filters": {
                "visa_types": ["F1"],
                "consulates": ["Toronto"],
                "statuses": ["Pending"],
            },
        },
    )
    assert update_response.status_code == 200
    updated_item = update_response.json()["item"]
    assert updated_item["name"] == "F1 Toronto Updated"
    assert updated_item["filters"]["statuses"] == ["Pending"]

    delete_response = client.delete(
        f"/api/v1/user/filter-presets/{preset_id}",
        headers=headers,
    )
    assert delete_response.status_code == 200

    list_after_delete = client.get("/api/v1/user/filter-presets", headers=headers)
    assert list_after_delete.status_code == 200
    assert list_after_delete.json()["total"] == 0


def test_user_filter_presets_limit(client, enable_user_auth, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import user_auth

    monkeypatch.setattr(user_auth, "USER_MAX_FILTER_PRESETS", 2)

    register_response = client.post(
        "/api/v1/user/register",
        json={"username": "dora", "password": "password123"},
    )
    token = register_response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.post(
        "/api/v1/user/filter-presets",
        headers=headers,
        json={"name": "P1", "filters": {"months": ["2026-03"]}},
    ).status_code == 200

    assert client.post(
        "/api/v1/user/filter-presets",
        headers=headers,
        json={"name": "P2", "filters": {"months": ["2026-02"]}},
    ).status_code == 200

    limit_response = client.post(
        "/api/v1/user/filter-presets",
        headers=headers,
        json={"name": "P3", "filters": {"months": ["2026-01"]}},
    )
    assert limit_response.status_code == 429


def test_user_filter_presets_require_session(client, enable_user_auth) -> None:
    list_response = client.get("/api/v1/user/filter-presets")
    assert list_response.status_code == 401

    create_response = client.post(
        "/api/v1/user/filter-presets",
        json={"name": "NoAuth", "filters": {}},
    )
    assert create_response.status_code == 401


def test_user_subscriptions_crud(client, enable_user_auth) -> None:
    register_response = client.post(
        "/api/v1/user/register",
        json={"username": "nina", "password": "password123"},
    )
    token = register_response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    preset_response = client.post(
        "/api/v1/user/filter-presets",
        headers=headers,
        json={"name": "F1 Watch", "filters": {"visa_types": ["F1"]}},
    )
    preset_id = preset_response.json()["item"]["id"]

    create_response = client.post(
        "/api/v1/user/subscriptions",
        headers=headers,
        json={
            "preset_id": preset_id,
            "channel": "in_app",
            "rule": {
                "pending_ratio_delta_ge": 0.1,
                "median_days_delta_ge": 8,
                "p90_days_delta_ge": 12,
                "long_tail_ratio_delta_ge": 0.05,
                "min_sample_size": 5,
            },
            "enabled": True,
        },
    )
    assert create_response.status_code == 200
    item = create_response.json()["item"]
    assert item["preset_id"] == preset_id
    assert item["channel"] == "in_app"
    assert item["enabled"] is True

    list_response = client.get("/api/v1/user/subscriptions", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    subscription_id = item["id"]
    update_response = client.put(
        f"/api/v1/user/subscriptions/{subscription_id}",
        headers=headers,
        json={"enabled": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["item"]["enabled"] is False

    delete_response = client.delete(
        f"/api/v1/user/subscriptions/{subscription_id}",
        headers=headers,
    )
    assert delete_response.status_code == 200

    list_after_delete = client.get("/api/v1/user/subscriptions", headers=headers)
    assert list_after_delete.status_code == 200
    assert list_after_delete.json()["total"] == 0


def test_user_notifications_flow(client, enable_user_auth, seed_cases) -> None:
    from app.services import storage
    from app.services import user_auth

    register_response = client.post(
        "/api/v1/user/register",
        json={"username": "omar", "password": "password123"},
    )
    token = register_response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    preset_response = client.post(
        "/api/v1/user/filter-presets",
        headers=headers,
        json={"name": "F1 Notify", "filters": {"visa_types": ["F1"]}},
    )
    preset_id = preset_response.json()["item"]["id"]

    subscription_response = client.post(
        "/api/v1/user/subscriptions",
        headers=headers,
        json={
            "preset_id": preset_id,
            "channel": "in_app",
            "rule": {
                "pending_ratio_delta_ge": 0.0,
                "median_days_delta_ge": 0.0,
                "p90_days_delta_ge": 0.0,
                "long_tail_ratio_delta_ge": 0.0,
                "min_sample_size": 1,
                "cooldown_hours": 1,
            },
            "enabled": True,
        },
    )
    assert subscription_response.status_code == 200

    rows = storage.load_cases()
    created_count = user_auth.user_auth_service.evaluate_subscriptions(rows=rows, previous_rows=rows)
    assert created_count == 1

    notifications_response = client.get("/api/v1/user/notifications", headers=headers)
    assert notifications_response.status_code == 200
    payload = notifications_response.json()
    assert payload["total"] == 1
    assert payload["unread_count"] == 1
    notification_id = payload["items"][0]["id"]
    assert payload["items"][0]["read_at"] is None

    mark_read_response = client.post(
        f"/api/v1/user/notifications/{notification_id}/read",
        headers=headers,
    )
    assert mark_read_response.status_code == 200
    assert mark_read_response.json()["item"]["read_at"] is not None

    unread_response = client.get(
        "/api/v1/user/notifications",
        headers=headers,
        params={"unread_only": "true"},
    )
    assert unread_response.status_code == 200
    assert unread_response.json()["total"] == 0


def test_data_service_refresh_triggers_subscription_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.data_service import DataService
    from app.services.scraper import CaseRow, FetchResult

    service = DataService()
    captured: dict[str, int] = {}

    def fake_fetch_cases(*, all_months: bool, months: int, from_month: str | None, sources: list[str] | None) -> FetchResult:
        return FetchResult(
            rows=[
                CaseRow(
                    source_month="2026-03",
                    case_number="Z001",
                    nickname="zeta",
                    visa_type="F1",
                    visa_entry="I20",
                    consulate="BeiJing",
                    major="CS",
                    status="Pending",
                    check_date="2026-03-01",
                    complete_date="",
                    waiting_days_reported="",
                    waiting_days_calc="",
                    observed_days="20",
                    event=0,
                    detail_url="https://example.com/detail/Z001",
                    update_url="https://example.com/update/Z001",
                    detail_employer="",
                    detail_note="",
                    detail_city="",
                    detail_state="",
                )
            ],
            fetched_months=["2026-03"],
            truncated_by_limit=False,
            selected_sources=["monthly_track"],
            source_discovery={},
            coverage={
                "selected_sources": ["monthly_track"],
                "available_month_count": 1,
                "selected_month_count": 1,
                "parsed_month_count": 1,
                "months_with_rows": ["2026-03"],
                "months_without_rows": [],
                "raw_case_count": 1,
                "deduped_case_count": 1,
                "dedup_removed_count": 0,
                "detail_deferred": False,
            },
        )

    def fake_evaluate(*, rows, previous_rows):
        captured["rows"] = len(rows)
        captured["previous_rows"] = len(previous_rows)
        return 3

    monkeypatch.setattr(service, "_enforce_refresh_interval", lambda: None)
    monkeypatch.setattr("app.services.data_service.fetch_cases", fake_fetch_cases)
    monkeypatch.setattr("app.services.data_service.user_auth_service.evaluate_subscriptions", fake_evaluate)

    result = service.refresh(
        all_months=False,
        months=1,
        from_month=None,
        sources=["monthly_track"],
        triggered_by="manual",
    )

    assert captured["rows"] == 1
    assert captured["previous_rows"] == 0
    assert result["notification_created_count"] == 3
