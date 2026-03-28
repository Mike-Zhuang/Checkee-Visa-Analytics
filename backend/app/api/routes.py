from __future__ import annotations

import secrets
from datetime import datetime
from io import StringIO

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.core.config import (
    ADMIN_REFRESH_KEY,
    ADMIN_SESSION_TTL_SECONDS,
    API_DEFAULT_CASES_LIMIT,
    API_MAX_CASES_LIMIT,
    REFRESH_REQUIRE_ADMIN_KEY,
)
from app.core.schemas import (
    AdminLoginRequest,
    AdminLogoutResponse,
    AdminSessionResponse,
    AdminSessionStateResponse,
    AnomalyRow,
    CohortStatsRow,
    ComparisonResponse,
    ConsulateGroupsResponse,
    DistributionRow,
    HealthResponse,
    OptionsResponse,
    RefreshRequest,
    RefreshResponse,
)
from app.services.data_service import service
from app.services.data_service import RefreshRateLimitError
from app.services.scraper import list_supported_sources
from app.services.admin_auth import create_admin_session, get_session_expiry, revoke_admin_session

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


def _require_admin_refresh_key(request: Request) -> None:
    if not REFRESH_REQUIRE_ADMIN_KEY:
        return

    bearer_token = _extract_bearer_token(request.headers.get("Authorization"))
    if bearer_token:
        if get_session_expiry(bearer_token) is not None:
            return

    key = ADMIN_REFRESH_KEY.strip()
    if not key:
        service.record_refresh_event(
            status="error",
            message="admin refresh key is not configured",
            triggered_by="manual",
        )
        raise HTTPException(status_code=503, detail="admin refresh key is not configured")

    provided = request.headers.get("X-Admin-Key", "")
    if not secrets.compare_digest(provided, key):
        remote_addr = request.client.host if request.client else "unknown"
        service.record_refresh_event(
            status="denied",
            message="admin auth invalid",
            triggered_by="manual",
            details={"remote_addr": remote_addr, "has_bearer": bool(bearer_token)},
        )
        raise HTTPException(status_code=403, detail="admin auth invalid")


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def _require_admin_session(request: Request) -> datetime:
    token = _extract_bearer_token(request.headers.get("Authorization"))
    expires_at = get_session_expiry(token)
    if expires_at is None:
        raise HTTPException(status_code=401, detail="admin session invalid or expired")
    return expires_at


@router.post("/admin/login", response_model=AdminSessionResponse)
def admin_login(req: AdminLoginRequest, request: Request) -> AdminSessionResponse:
    required_key = ADMIN_REFRESH_KEY.strip()
    if not required_key:
        raise HTTPException(status_code=503, detail="admin login key is not configured")

    provided = req.password.strip()
    if not provided or not secrets.compare_digest(provided, required_key):
        remote_addr = request.client.host if request.client else "unknown"
        service.record_refresh_event(
            status="denied",
            message="admin login failed",
            triggered_by="manual",
            details={"remote_addr": remote_addr},
        )
        raise HTTPException(status_code=401, detail="admin password invalid")

    session = create_admin_session(ADMIN_SESSION_TTL_SECONDS)
    return AdminSessionResponse(token=session.token, expires_at=session.expires_at)


@router.get("/admin/session", response_model=AdminSessionStateResponse)
def admin_session(request: Request) -> AdminSessionStateResponse:
    expires_at = _require_admin_session(request)
    return AdminSessionStateResponse(authenticated=True, expires_at=expires_at)


@router.post("/admin/logout", response_model=AdminLogoutResponse)
def admin_logout(request: Request) -> AdminLogoutResponse:
    token = _extract_bearer_token(request.headers.get("Authorization"))
    if not token:
        raise HTTPException(status_code=401, detail="admin session invalid or expired")
    revoke_admin_session(token)
    return AdminLogoutResponse(success=True, message="logout success")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    has_data = len(service.get_cases()) > 0
    return HealthResponse(status="ok", has_data=has_data)


@router.post("/tasks/refresh", response_model=RefreshResponse)
def refresh(req: RefreshRequest, request: Request) -> RefreshResponse:
    _require_admin_refresh_key(request)

    try:
        result = service.refresh(
            all_months=req.all_months,
            months=req.months,
            from_month=req.from_month,
            sources=req.sources,
        )
        return RefreshResponse(**result)
    except RefreshRateLimitError as exc:
        service.record_refresh_event(
            status="blocked",
            message=f"refresh cooldown in effect, retry in {exc.retry_after_seconds}s",
            triggered_by="manual",
            details={"retry_after_seconds": exc.retry_after_seconds},
        )
        raise HTTPException(
            status_code=429,
            detail=f"refresh cooldown in effect, retry in {exc.retry_after_seconds}s",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except ValueError as exc:
        service.record_refresh_event(
            status="error",
            message=str(exc),
            triggered_by="manual",
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        service.record_refresh_event(
            status="error",
            message=str(exc),
            triggered_by="manual",
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/meta/options", response_model=OptionsResponse)
def options() -> OptionsResponse:
    rows = service.get_cases()
    if not rows:
        return OptionsResponse(
            months=[],
            visa_types=[],
            consulates=[],
            statuses=[],
            entries=[],
            fetch_sources=list_supported_sources(),
        )
    return OptionsResponse(**service.get_options(rows), fetch_sources=list_supported_sources())


@router.get("/meta/state")
def state() -> dict:
    return service.get_meta()


@router.get("/meta/consulate-groups", response_model=ConsulateGroupsResponse)
def consulate_groups() -> ConsulateGroupsResponse:
    rows = service.get_cases()
    if not rows:
        return ConsulateGroupsResponse(groups=[], ungrouped=[])
    grouped = service.get_consulate_groups(rows)
    return ConsulateGroupsResponse(**grouped)


@router.get("/cases")
def cases(
    visa_types: str | None = Query(default=None, description="Comma-separated visa types"),
    consulates: str | None = Query(default=None),
    statuses: str | None = Query(default=None),
    entries: str | None = Query(default=None),
    months: str | None = Query(default=None),
    limit: int = Query(default=API_DEFAULT_CASES_LIMIT, ge=1, le=API_MAX_CASES_LIMIT),
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


@router.get("/stats/cohorts")
def cohorts(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
):
    filtered = _filtered_rows(visa_types, consulates, statuses, entries, months)
    items = [CohortStatsRow(**item).model_dump() for item in service.get_cohorts(filtered)]
    return {"items": items}


@router.get("/stats/distribution")
def distribution(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
):
    filtered = _filtered_rows(visa_types, consulates, statuses, entries, months)
    items = [DistributionRow(**item).model_dump() for item in service.get_distribution(filtered)]
    return {"items": items}


@router.get("/stats/comparison", response_model=ComparisonResponse)
def comparison(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
) -> ComparisonResponse:
    filtered = _filtered_rows(visa_types, consulates, statuses, entries, months)
    return ComparisonResponse(**service.get_comparison(filtered))


@router.get("/stats/anomalies")
def anomalies(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
    threshold_days: int = Query(default=120, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
):
    filtered = _filtered_rows(visa_types, consulates, statuses, entries, months)
    items = [
        AnomalyRow(**item).model_dump()
        for item in service.get_anomalies(filtered, threshold_days=threshold_days, limit=limit)
    ]
    return {"items": items}


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
