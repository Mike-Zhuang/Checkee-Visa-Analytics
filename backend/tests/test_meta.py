from __future__ import annotations


def test_meta_options_and_state(client, seed_cases) -> None:
    options_res = client.get("/api/v1/meta/options")
    assert options_res.status_code == 200
    options_payload = options_res.json()
    assert "F1" in options_payload["visa_types"]
    assert "H1B" in options_payload["visa_types"]
    assert "BeiJing" in options_payload["consulates"]
    assert "CS" in options_payload["majors"]
    assert "STEM" in options_payload["major_categories_l1"]
    assert options_payload["major_categories_l2"]
    assert "Unspecified" in options_payload["major_categories_l2"]
    assert "major_category_mapping" in options_payload
    assert "STEM" in options_payload["major_category_mapping"]
    assert "Software & Systems" in options_payload["major_category_mapping"]["STEM"]
    assert "Unspecified" in options_payload["major_category_mapping"]["STEM"]
    assert "Google" in options_payload["employers"]
    assert "Beijing" in options_payload["detail_cities"]
    assert "Ontario" in options_payload["detail_states"]
    assert "monthly_track" in options_payload["fetch_sources"]
    assert "latest_snapshot" in options_payload["fetch_sources"]

    state_res = client.get("/api/v1/meta/state")
    assert state_res.status_code == 200
    state_payload = state_res.json()
    assert state_payload["has_data"] is True
    assert state_payload["current_case_count"] == 4
    assert state_payload["fetched_month_range"]["latest"] == "2026-03"
    assert "refresh_min_interval_seconds" in state_payload
    assert "refresh_available_in_seconds" in state_payload


def test_meta_consulate_groups(client, seed_cases) -> None:
    response = client.get("/api/v1/meta/consulate-groups")
    assert response.status_code == 200
    payload = response.json()

    groups = {item["key"]: item for item in payload["groups"]}
    assert "china" in groups
    assert "canada" in groups
    assert "europe" in groups
    assert "ungrouped" in groups

    assert "BeiJing" in groups["china"]["consulates"]
    assert "Toronto" in groups["canada"]["consulates"]
    assert "MoonBase" in payload["ungrouped"]
