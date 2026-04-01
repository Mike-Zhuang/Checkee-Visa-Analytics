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
