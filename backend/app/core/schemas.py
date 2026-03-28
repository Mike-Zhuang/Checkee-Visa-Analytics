from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import API_DEFAULT_REFRESH_MONTHS, API_MAX_REFRESH_MONTHS


class RefreshRequest(BaseModel):
    all_months: bool = False
    months: int = Field(default=API_DEFAULT_REFRESH_MONTHS, ge=1, le=API_MAX_REFRESH_MONTHS)
    from_month: str | None = None
    sources: list[str] | None = Field(default=None, min_length=1)


class AdminLoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class AdminSessionResponse(BaseModel):
    token: str
    expires_at: datetime


class AdminSessionStateResponse(BaseModel):
    authenticated: bool
    expires_at: datetime


class AdminLogoutResponse(BaseModel):
    success: bool
    message: str


class RefreshResponse(BaseModel):
    success: bool
    message: str
    fetched_months: list[str]
    total_cases: int
    selected_sources: list[str]
    truncated_by_limit: bool = False
    month_limit: int
    generated_at: datetime


class OverviewStats(BaseModel):
    total_cases: int
    finalized_cases: int
    pending_cases: int
    maturity_ratio: float
    median_days: float
    median_ci_low: float
    median_ci_high: float
    p90_days: float
    p90_ci_low: float
    p90_ci_high: float
    mean_days: float
    iqr_days: float
    std_days: float
    long_tail_90plus_ratio: float


class SensitivityRow(BaseModel):
    scenario: Literal["Conservative", "Neutral", "Aggressive"]
    median_days: float
    p90_days: float
    long_tail_90plus_ratio: float


class MonthlyStatsRow(BaseModel):
    submit_month: str
    total_cases: int
    clear_cases: int
    reject_cases: int
    pending_cases: int
    pending_ratio: float
    maturity_ratio: float
    finalized_count: int
    median_days: float | None = None
    p90_days: float | None = None
    long_tail_90plus_ratio: float | None = None


class OptionsResponse(BaseModel):
    months: list[str]
    visa_types: list[str]
    consulates: list[str]
    statuses: list[str]
    entries: list[str]
    major_categories_l1: list[str]
    major_categories_l2: list[str]
    major_category_mapping: dict[str, list[str]]
    majors: list[str]
    employers: list[str]
    detail_cities: list[str]
    detail_states: list[str]
    fetch_sources: list[str]


class MajorClassificationRow(BaseModel):
    major: str
    major_normalized: str
    count: int
    auto_category_l1: str
    auto_category_l2: str
    effective_category_l1: str
    effective_category_l2: str
    source: Literal["manual", "auto", "not_applicable", "unknown"]
    has_manual_override: bool
    override_updated_at: str | None = None


class MajorClassificationsResponse(BaseModel):
    total: int
    items: list[MajorClassificationRow]
    category_l1_options: list[str]
    category_l2_options: list[str]


class MajorOverrideItem(BaseModel):
    major: str = Field(min_length=1)
    category_l1: str = Field(min_length=1)
    category_l2: str = Field(min_length=1)


class MajorOverrideUpsertRequest(BaseModel):
    items: list[MajorOverrideItem] = Field(min_length=1)


class MajorOverrideMutationResponse(BaseModel):
    success: bool
    updated: int
    message: str


class CohortStatsRow(BaseModel):
    cohort: str
    total_cases: int
    finalized_cases: int
    pending_cases: int
    maturity_ratio: float
    median_days: float | None = None
    p90_days: float | None = None
    long_tail_90plus_ratio: float | None = None


class DistributionRow(BaseModel):
    bucket: str
    count: int
    ratio: float


class ComparisonMetrics(BaseModel):
    median_days: float
    p90_days: float
    pending_ratio: float


class ComparisonResponse(BaseModel):
    latest_month: str | None = None
    baseline_month: str | None = None
    latest: ComparisonMetrics | None = None
    baseline: ComparisonMetrics | None = None
    delta: ComparisonMetrics | None = None


class AnomalyRow(BaseModel):
    case_number: str
    visa_type: str
    consulate: str
    status: str
    check_date: str
    days: int
    reason: str
    detail_url: str
    update_url: str


class ConsulateGroup(BaseModel):
    key: str
    label: str
    consulates: list[str]


class ConsulateGroupsResponse(BaseModel):
    groups: list[ConsulateGroup]
    ungrouped: list[str]


class HealthResponse(BaseModel):
    status: str
    has_data: bool
