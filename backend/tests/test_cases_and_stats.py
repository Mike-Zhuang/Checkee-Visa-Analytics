from __future__ import annotations

from app.services import storage


def test_cases_pagination(client, seed_cases) -> None:
    response = client.get("/api/v1/cases", params={"limit": 2, "offset": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 4
    assert payload["limit"] == 2
    assert payload["offset"] == 1
    assert len(payload["items"]) == 2


def test_cases_detail_filters_and_text_search(client, seed_cases) -> None:
    response = client.get(
        "/api/v1/cases",
        params={
            "majors": "Math",
            "employers": "Amazon",
            "detail_cities": "Toronto",
            "detail_states": "Ontario",
            "search_text": "amazon cleared",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["case_number"] == "A002"


def test_cases_major_category_filters(client, seed_cases) -> None:
    response = client.get(
        "/api/v1/cases",
        params={
            "major_categories_l1": "STEM",
            "major_categories_l2": "Software & Systems",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["case_number"] == "A001"


def test_cases_major_category_filters_engineering_abbreviation(client, seed_cases) -> None:
    response = client.get(
        "/api/v1/cases",
        params={
            "major_categories_l1": "STEM",
            "major_categories_l2": "Engineering",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["case_number"] == "A003"


def test_cases_has_note_filter(client, seed_cases) -> None:
    rows = storage.load_cases()
    rows[0]["detail_note"] = ""
    storage.save_cases(rows)

    response = client.get("/api/v1/cases", params={"has_note": "true"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert all(str(item.get("detail_note") or "").strip() for item in payload["items"])


def test_cases_sort_by_check_date_desc(client, seed_cases) -> None:
    response = client.get(
        "/api/v1/cases",
        params={"sort_by": "check_date", "sort_order": "desc", "limit": 10},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["case_number"] for item in items] == ["A002", "A001", "A003", "A004"]


def test_cases_sort_by_complete_date_desc_puts_empty_to_end(client, seed_cases) -> None:
    response = client.get(
        "/api/v1/cases",
        params={"sort_by": "complete_date", "sort_order": "desc", "limit": 10},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["case_number"] for item in items[:2]] == ["A002", "A001"]
    assert [item["case_number"] for item in items[2:]] == ["A003", "A004"]


def test_cases_sort_by_complete_date_asc(client, seed_cases) -> None:
    response = client.get(
        "/api/v1/cases",
        params={"sort_by": "complete_date", "sort_order": "asc", "limit": 10},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["case_number"] for item in items[:2]] == ["A001", "A002"]
    assert [item["case_number"] for item in items[2:]] == ["A003", "A004"]


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


def test_recommendation_returns_probability_intervals(client, seed_cases) -> None:
    response = client.get("/api/v1/stats/recommendation")
    assert response.status_code == 200

    payload = response.json()
    assert payload["summary"]["sample_size"] == 4
    assert payload["summary"]["finalized_cases"] == 2
    assert payload["summary"]["insufficient_data"] is True

    items = payload["items"]
    assert len(items) == 3
    for item in items:
        low = item["probability_interval_low"]
        estimate = item["estimate"]
        high = item["probability_interval_high"]
        assert item["level"] == "insufficient"
        assert 0.0 <= low <= estimate <= high <= 1.0
        assert item["evidence"]


def test_recommendation_no_match_returns_empty_items(client, seed_cases) -> None:
    response = client.get("/api/v1/stats/recommendation", params={"months": "1999-01"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["summary"]["sample_size"] == 0
    assert payload["summary"]["insufficient_data"] is True
    assert payload["summary"]["confidence_band"] == "insufficient"
    assert payload["items"] == []


def test_recommendation_includes_filter_snapshot(client, seed_cases) -> None:
    response = client.get(
        "/api/v1/stats/recommendation",
        params={
            "visa_types": "f1",
            "statuses": "Pending",
            "months": "2026-03",
            "has_note": "true",
            "search_text": "amazon",
        },
    )
    assert response.status_code == 200

    payload = response.json()
    applied = payload["filter_applied"]
    assert applied["visa_types"] == ["F1"]
    assert applied["statuses"] == ["Pending"]
    assert applied["months"] == ["2026-03"]
    assert applied["has_note"] is True
    assert applied["search_text"] == "amazon"


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
