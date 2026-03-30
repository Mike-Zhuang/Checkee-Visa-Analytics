from __future__ import annotations

import secrets
from datetime import datetime
from io import StringIO

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.core.config import (
    ADMIN_REFRESH_KEY,
    ADMIN_SESSION_TTL_SECONDS,
    API_DEFAULT_REFRESH_MONTHS,
    API_DEFAULT_CASES_LIMIT,
    API_MAX_CASES_LIMIT,
    REFRESH_REQUIRE_ADMIN_KEY,
)
from app.core.schemas import (
    AdminLoginRequest,
    AdminLogoutResponse,
    AdminStaleRefreshResponse,
    MajorClassificationsResponse,
    MajorOverrideMutationResponse,
    MajorOverrideUpsertRequest,
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
ADMIN_STALE_REFRESH_THRESHOLD_SECONDS = 6 * 60 * 60
REFRESH_TRIGGERED_BY_MANUAL = "manual"
REFRESH_TRIGGERED_BY_SCHEDULED = "scheduled"
REFRESH_TRIGGERED_BY_AUTO_FALLBACK = "auto_fallback"


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
    major_categories_l1: str | None,
    major_categories_l2: str | None,
    majors: str | None,
    employers: str | None,
    detail_cities: str | None,
    detail_states: str | None,
    search_text: str | None,
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
        major_categories_l1=_split_csv_values(major_categories_l1),
        major_categories_l2=_split_csv_values(major_categories_l2),
        majors=_split_csv_values(majors),
        employers=_split_csv_values(employers),
        detail_cities=_split_csv_values(detail_cities),
        detail_states=_split_csv_values(detail_states),
        search_text=(search_text or "").strip() or None,
    )


def _resolve_refresh_triggered_by(request: Request) -> str:
    token = _extract_bearer_token(request.headers.get("Authorization"))
    if token and get_session_expiry(token) is not None:
        return REFRESH_TRIGGERED_BY_MANUAL

    provided_key = request.headers.get("X-Admin-Key", "").strip()
    if provided_key:
        return REFRESH_TRIGGERED_BY_SCHEDULED

    return REFRESH_TRIGGERED_BY_MANUAL


def _require_admin_refresh_key(request: Request) -> str:
    triggered_by = _resolve_refresh_triggered_by(request)
    if not REFRESH_REQUIRE_ADMIN_KEY:
        return triggered_by

    bearer_token = _extract_bearer_token(request.headers.get("Authorization"))
    if bearer_token:
        if get_session_expiry(bearer_token) is not None:
            return REFRESH_TRIGGERED_BY_MANUAL

    key = ADMIN_REFRESH_KEY.strip()
    if not key:
        service.record_refresh_event(
            status="error",
            message="admin refresh key is not configured",
            triggered_by=triggered_by,
        )
        raise HTTPException(status_code=503, detail="admin refresh key is not configured")

    provided = request.headers.get("X-Admin-Key", "")
    if not secrets.compare_digest(provided, key):
        remote_addr = request.client.host if request.client else "unknown"
        service.record_refresh_event(
            status="denied",
            message="admin auth invalid",
            triggered_by=triggered_by,
            details={"remote_addr": remote_addr, "has_bearer": bool(bearer_token)},
        )
        raise HTTPException(status_code=403, detail="admin auth invalid")
    return REFRESH_TRIGGERED_BY_SCHEDULED


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
            triggered_by=REFRESH_TRIGGERED_BY_MANUAL,
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


def _refresh_sources_from_meta(meta: dict) -> list[str]:
    selected_sources = meta.get("selected_sources")
    if isinstance(selected_sources, list):
        normalized = [str(item).strip() for item in selected_sources if str(item).strip()]
        if normalized:
            return normalized

    supported_sources = meta.get("supported_sources")
    if isinstance(supported_sources, list):
        normalized = [str(item).strip() for item in supported_sources if str(item).strip()]
        if normalized:
            return normalized

    return ["monthly_track"]


def _refresh_months_from_meta(meta: dict) -> int:
    raw_months = meta.get("months_arg", API_DEFAULT_REFRESH_MONTHS)
    try:
        parsed = int(raw_months)
    except (TypeError, ValueError):
        return API_DEFAULT_REFRESH_MONTHS
    return max(1, parsed)


@router.post("/admin/refresh/stale-trigger", response_model=AdminStaleRefreshResponse)
def admin_refresh_stale_trigger(request: Request) -> AdminStaleRefreshResponse:
    _require_admin_session(request)

    meta = service.get_meta()
    updated_at = str(meta.get("updated_at") or "") or None
    freshness_seconds = meta.get("data_freshness_seconds")

    if isinstance(freshness_seconds, int) and freshness_seconds < ADMIN_STALE_REFRESH_THRESHOLD_SECONDS:
        return AdminStaleRefreshResponse(
            triggered=False,
            reason="fresh_enough",
            updated_at=updated_at,
            message="data is fresh enough",
        )

    sources = _refresh_sources_from_meta(meta)
    months = _refresh_months_from_meta(meta)
    from_month_raw = meta.get("from_month")
    from_month = str(from_month_raw).strip() if from_month_raw else None

    try:
        service.refresh(
            all_months=False,
            months=months,
            from_month=from_month,
            sources=sources,
            triggered_by=REFRESH_TRIGGERED_BY_AUTO_FALLBACK,
        )
        refreshed_meta = service.get_meta()
        refreshed_updated_at = str(refreshed_meta.get("updated_at") or "") or None
        return AdminStaleRefreshResponse(
            triggered=True,
            reason="stale_triggered",
            updated_at=refreshed_updated_at,
            message="stale refresh triggered",
        )
    except RefreshRateLimitError as exc:
        current_meta = service.get_meta()
        current_updated_at = str(current_meta.get("updated_at") or "") or None
        return AdminStaleRefreshResponse(
            triggered=False,
            reason="cooldown",
            updated_at=current_updated_at,
            message=f"refresh cooldown in effect, retry in {exc.retry_after_seconds}s",
        )
    except Exception as exc:  # noqa: BLE001
        service.record_refresh_event(
            status="error",
            message=f"admin stale refresh failed: {exc}",
            triggered_by=REFRESH_TRIGGERED_BY_AUTO_FALLBACK,
        )
        current_meta = service.get_meta()
        current_updated_at = str(current_meta.get("updated_at") or "") or None
        return AdminStaleRefreshResponse(
            triggered=False,
            reason="error",
            updated_at=current_updated_at,
            message=str(exc),
        )


@router.get("/admin/major-classifications", response_model=MajorClassificationsResponse)
def admin_major_classifications(
    request: Request,
    q: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
) -> MajorClassificationsResponse:
    _require_admin_session(request)
    rows = service.get_cases()
    payload = service.get_major_classifications(rows, query=q, limit=limit)
    return MajorClassificationsResponse(**payload)


@router.put("/admin/major-classifications", response_model=MajorOverrideMutationResponse)
def admin_upsert_major_classifications(
    req: MajorOverrideUpsertRequest,
    request: Request,
) -> MajorOverrideMutationResponse:
    _require_admin_session(request)
    updated = service.upsert_major_overrides(
        [item.model_dump() for item in req.items],
        operator="admin",
    )
    return MajorOverrideMutationResponse(success=True, updated=updated, message="major overrides updated")


@router.delete("/admin/major-classifications", response_model=MajorOverrideMutationResponse)
def admin_delete_major_classification(
    request: Request,
    major: str = Query(min_length=1),
) -> MajorOverrideMutationResponse:
    _require_admin_session(request)
    deleted = service.delete_major_override(major)
    if not deleted:
        raise HTTPException(status_code=404, detail="major override not found")
    return MajorOverrideMutationResponse(success=True, updated=1, message="major override deleted")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    has_data = len(service.get_cases()) > 0
    return HealthResponse(status="ok", has_data=has_data)


@router.post("/tasks/refresh", response_model=RefreshResponse)
def refresh(req: RefreshRequest, request: Request) -> RefreshResponse:
    triggered_by = _require_admin_refresh_key(request)

    try:
        result = service.refresh(
            all_months=req.all_months,
            months=req.months,
            from_month=req.from_month,
            sources=req.sources,
            triggered_by=triggered_by,
        )
        return RefreshResponse(**result)
    except RefreshRateLimitError as exc:
        service.record_refresh_event(
            status="blocked",
            message=f"refresh cooldown in effect, retry in {exc.retry_after_seconds}s",
            triggered_by=triggered_by,
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
            triggered_by=triggered_by,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        service.record_refresh_event(
            status="error",
            message=str(exc),
            triggered_by=triggered_by,
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
            major_categories_l1=[],
            major_categories_l2=[],
            major_category_mapping={},
            majors=[],
            employers=[],
            detail_cities=[],
            detail_states=[],
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
    major_categories_l1: str | None = Query(default=None),
    major_categories_l2: str | None = Query(default=None),
    majors: str | None = Query(default=None),
    employers: str | None = Query(default=None),
    detail_cities: str | None = Query(default=None),
    detail_states: str | None = Query(default=None),
    search_text: str | None = Query(default=None),
    limit: int = Query(default=API_DEFAULT_CASES_LIMIT, ge=1, le=API_MAX_CASES_LIMIT),
    offset: int = Query(default=0, ge=0),
):
    filtered = _filtered_rows(
        visa_types,
        consulates,
        statuses,
        entries,
        months,
        major_categories_l1,
        major_categories_l2,
        majors,
        employers,
        detail_cities,
        detail_states,
        search_text,
    )
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
    major_categories_l1: str | None = None,
    major_categories_l2: str | None = None,
    majors: str | None = None,
    employers: str | None = None,
    detail_cities: str | None = None,
    detail_states: str | None = None,
    search_text: str | None = None,
):
    filtered = _filtered_rows(
        visa_types,
        consulates,
        statuses,
        entries,
        months,
        major_categories_l1,
        major_categories_l2,
        majors,
        employers,
        detail_cities,
        detail_states,
        search_text,
    )
    return service.get_overview(filtered)


@router.get("/stats/monthly")
def monthly(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
    major_categories_l1: str | None = None,
    major_categories_l2: str | None = None,
    majors: str | None = None,
    employers: str | None = None,
    detail_cities: str | None = None,
    detail_states: str | None = None,
    search_text: str | None = None,
):
    filtered = _filtered_rows(
        visa_types,
        consulates,
        statuses,
        entries,
        months,
        major_categories_l1,
        major_categories_l2,
        majors,
        employers,
        detail_cities,
        detail_states,
        search_text,
    )
    return {"items": service.get_monthly(filtered)}


@router.get("/stats/sensitivity")
def sensitivity(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
    major_categories_l1: str | None = None,
    major_categories_l2: str | None = None,
    majors: str | None = None,
    employers: str | None = None,
    detail_cities: str | None = None,
    detail_states: str | None = None,
    search_text: str | None = None,
):
    filtered = _filtered_rows(
        visa_types,
        consulates,
        statuses,
        entries,
        months,
        major_categories_l1,
        major_categories_l2,
        majors,
        employers,
        detail_cities,
        detail_states,
        search_text,
    )
    return {"items": service.get_sensitivity(filtered)}


@router.get("/stats/cohorts")
def cohorts(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
    major_categories_l1: str | None = None,
    major_categories_l2: str | None = None,
    majors: str | None = None,
    employers: str | None = None,
    detail_cities: str | None = None,
    detail_states: str | None = None,
    search_text: str | None = None,
):
    filtered = _filtered_rows(
        visa_types,
        consulates,
        statuses,
        entries,
        months,
        major_categories_l1,
        major_categories_l2,
        majors,
        employers,
        detail_cities,
        detail_states,
        search_text,
    )
    items = [CohortStatsRow(**item).model_dump() for item in service.get_cohorts(filtered)]
    return {"items": items}


@router.get("/stats/distribution")
def distribution(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
    major_categories_l1: str | None = None,
    major_categories_l2: str | None = None,
    majors: str | None = None,
    employers: str | None = None,
    detail_cities: str | None = None,
    detail_states: str | None = None,
    search_text: str | None = None,
):
    filtered = _filtered_rows(
        visa_types,
        consulates,
        statuses,
        entries,
        months,
        major_categories_l1,
        major_categories_l2,
        majors,
        employers,
        detail_cities,
        detail_states,
        search_text,
    )
    items = [DistributionRow(**item).model_dump() for item in service.get_distribution(filtered)]
    return {"items": items}


@router.get("/stats/comparison", response_model=ComparisonResponse)
def comparison(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
    major_categories_l1: str | None = None,
    major_categories_l2: str | None = None,
    majors: str | None = None,
    employers: str | None = None,
    detail_cities: str | None = None,
    detail_states: str | None = None,
    search_text: str | None = None,
) -> ComparisonResponse:
    filtered = _filtered_rows(
        visa_types,
        consulates,
        statuses,
        entries,
        months,
        major_categories_l1,
        major_categories_l2,
        majors,
        employers,
        detail_cities,
        detail_states,
        search_text,
    )
    return ComparisonResponse(**service.get_comparison(filtered))


@router.get("/stats/anomalies")
def anomalies(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
    major_categories_l1: str | None = None,
    major_categories_l2: str | None = None,
    majors: str | None = None,
    employers: str | None = None,
    detail_cities: str | None = None,
    detail_states: str | None = None,
    search_text: str | None = None,
    threshold_days: int = Query(default=120, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
):
    filtered = _filtered_rows(
        visa_types,
        consulates,
        statuses,
        entries,
        months,
        major_categories_l1,
        major_categories_l2,
        majors,
        employers,
        detail_cities,
        detail_states,
        search_text,
    )
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
    major_categories_l1: str | None = None,
    major_categories_l2: str | None = None,
    majors: str | None = None,
    employers: str | None = None,
    detail_cities: str | None = None,
    detail_states: str | None = None,
    search_text: str | None = None,
):
    filtered = _filtered_rows(
        visa_types,
        consulates,
        statuses,
        entries,
        months,
        major_categories_l1,
        major_categories_l2,
        majors,
        employers,
        detail_cities,
        detail_states,
        search_text,
    )
    return service.get_report(filtered)


@router.get("/export/cases.csv")
def export_cases_csv(
    visa_types: str | None = None,
    consulates: str | None = None,
    statuses: str | None = None,
    entries: str | None = None,
    months: str | None = None,
    major_categories_l1: str | None = None,
    major_categories_l2: str | None = None,
    majors: str | None = None,
    employers: str | None = None,
    detail_cities: str | None = None,
    detail_states: str | None = None,
    search_text: str | None = None,
):
    rows = _filtered_rows(
        visa_types,
        consulates,
        statuses,
        entries,
        months,
        major_categories_l1,
        major_categories_l2,
        majors,
        employers,
        detail_cities,
        detail_states,
        search_text,
    )
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
        "major_category_l1",
        "major_category_l2",
        "major_classification_source",
        "status",
        "check_date",
        "complete_date",
        "waiting_days_reported",
        "waiting_days_calc",
        "observed_days",
        "event",
        "detail_url",
        "update_url",
        "detail_employer",
        "detail_note",
        "detail_city",
        "detail_state",
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
