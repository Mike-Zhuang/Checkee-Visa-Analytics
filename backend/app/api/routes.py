from __future__ import annotations

from datetime import datetime
from io import StringIO

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.core.schemas import HealthResponse, OptionsResponse, RefreshRequest, RefreshResponse
from app.services.data_service import service

router = APIRouter(prefix="/api/v1", tags=["checkee"])


def _split_csv_values(raw: str | None, upper: bool = False) -> set[str] | None:
    if not raw:
        return None
    values = {v.strip() for v in raw.split(",") if v.strip()}
    if not values:
        return None
    if upper:
        return {v.upper() for v in values}
    return values


def _filtered_rows(
    visa_types: str | None,
    consulates: str | None,
    statuses: str | None,
    entries: str | None,
    months: str | None,
):
    rows = service.get_cases()
    if not rows:
        return []
    return service.filter_rows(
        rows,
        visa_types=_split_csv_values(visa_types, upper=True),
        consulates=_split_csv_values(consulates),
        statuses=_split_csv_values(statuses),
        entries=_split_csv_values(entries),
        months=_split_csv_values(months),
    )


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    has_data = len(service.get_cases()) > 0
    return HealthResponse(status="ok", has_data=has_data)


@router.post("/tasks/refresh", response_model=RefreshResponse)
def refresh(req: RefreshRequest) -> RefreshResponse:
    try:
        result = service.refresh(all_months=req.all_months, months=req.months, from_month=req.from_month)
        return RefreshResponse(**result)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/meta/options", response_model=OptionsResponse)
def options() -> OptionsResponse:
    rows = service.get_cases()
    if not rows:
        return OptionsResponse(months=[], visa_types=[], consulates=[], statuses=[], entries=[])
    return OptionsResponse(**service.get_options(rows))


@router.get("/meta/state")
def state() -> dict:
    return service.get_meta()


@router.get("/cases")
def cases(
    visa_types: str | None = Query(default=None, description="Comma-separated visa types"),
    consulates: str | None = Query(default=None),
    statuses: str | None = Query(default=None),
    entries: str | None = Query(default=None),
    months: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
):
    filtered = _filtered_rows(visa_types, consulates, statuses, entries, months)
    total = len(filtered)
    data = filtered[offset : offset + limit]
    return {"total": total, "limit": limit, "offset": offset, "items": data}


@router.get("/stats/overview")
def overview(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
):
    filtered = _filtered_rows(visa_types, consulates, statuses, entries, months)
    return service.get_overview(filtered)


@router.get("/stats/monthly")
def monthly(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
):
    filtered = _filtered_rows(visa_types, consulates, statuses, entries, months)
    return {"items": service.get_monthly(filtered)}


@router.get("/stats/sensitivity")
def sensitivity(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
):
    filtered = _filtered_rows(visa_types, consulates, statuses, entries, months)
    return {"items": service.get_sensitivity(filtered)}


@router.get("/export/report", response_class=PlainTextResponse)
def export_report(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
):
    filtered = _filtered_rows(visa_types, consulates, statuses, entries, months)
    return service.get_report(filtered)


@router.get("/export/cases.csv")
def export_cases_csv(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
):
    rows = _filtered_rows(visa_types, consulates, statuses, entries, months)
    if not rows:
        rows = []

    headers = list(rows[0].keys()) if rows else [
        "source_month",
        "case_number",
        "nickname",
        "visa_type",
        "visa_entry",
        "consulate",
        "major",
        "status",
        "check_date",
        "complete_date",
        "waiting_days_reported",
        "waiting_days_calc",
        "observed_days",
        "event",
        "detail_url",
        "update_url",
    ]

    import csv

    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)

    filename = f"checkee_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
