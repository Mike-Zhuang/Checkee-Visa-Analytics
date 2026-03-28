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


def test_cohorts_distribution_and_comparison(client, seed_cases) -> None:
    cohorts_res = client.get("/api/v1/stats/cohorts")
    assert cohorts_res.status_code == 200
    cohorts = cohorts_res.json()["items"]
    cohort_map = {row["cohort"]: row for row in cohorts}
    assert cohort_map["F1"]["total_cases"] == 2
    assert cohort_map["F1"]["finalized_cases"] == 2
    assert cohort_map["F1"]["maturity_ratio"] == 1.0

    dist_res = client.get("/api/v1/stats/distribution")
    assert dist_res.status_code == 200
    dist_map = {row["bucket"]: row for row in dist_res.json()["items"]}
    assert dist_map["0-30"]["count"] == 1
    assert dist_map["31-60"]["count"] == 1
    assert dist_map["61-90"]["count"] == 0

    cmp_res = client.get("/api/v1/stats/comparison")
    assert cmp_res.status_code == 200
    cmp_payload = cmp_res.json()
    assert cmp_payload["latest_month"] == "2026-03"
    assert cmp_payload["baseline_month"] == "2026-02"
    assert cmp_payload["latest"]["median_days"] > cmp_payload["baseline"]["median_days"]


def test_anomalies_threshold_filter(client, seed_cases) -> None:
    response = client.get("/api/v1/stats/anomalies", params={"threshold_days": 40, "limit": 10})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assert items[0]["days"] >= items[1]["days"]
    assert {item["case_number"] for item in items} == {"A003", "A004"}
