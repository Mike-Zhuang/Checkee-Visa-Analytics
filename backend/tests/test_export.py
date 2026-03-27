from __future__ import annotations


def test_export_report(client, seed_cases) -> None:
    response = client.get("/api/v1/export/report")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "Checkee 全签证实时分析报告" in response.text


def test_export_cases_csv(client, seed_cases) -> None:
    response = client.get("/api/v1/export/cases.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert "case_number" in response.text
    assert "A001" in response.text
