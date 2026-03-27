from __future__ import annotations


def test_cases_pagination(client, seed_cases) -> None:
    response = client.get("/api/v1/cases", params={"limit": 2, "offset": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 4
    assert payload["limit"] == 2
    assert payload["offset"] == 1
    assert len(payload["items"]) == 2


def test_overview_stats(client, seed_cases) -> None:
    response = client.get("/api/v1/stats/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cases"] == 4
    assert payload["finalized_cases"] == 2
    assert payload["pending_cases"] == 2
    assert payload["median_days"] > 0


def test_overview_with_no_match_returns_zeroes(client, seed_cases) -> None:
    response = client.get("/api/v1/stats/overview", params={"months": "1999-01"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cases"] == 0
    assert payload["finalized_cases"] == 0
    assert payload["pending_cases"] == 0
    assert payload["median_days"] == 0.0
