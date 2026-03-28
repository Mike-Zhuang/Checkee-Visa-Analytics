export type OptionsResponse = {
    months: string[]
    visa_types: string[]
    consulates: string[]
    statuses: string[]
    entries: string[]
    fetch_sources: string[]
}

export type ConsulateGroup = {
    key: string
    label: string
    consulates: string[]
}

export type ConsulateGroupsResponse = {
    groups: ConsulateGroup[]
    ungrouped: string[]
}

export type MetaState = {
    fetched_months: string[]
    fetched_month_count: number
    total_cases: number
    all_months: boolean
    months_arg: number
    from_month: string | null
    truncated_by_limit: boolean
    month_limit: number
    updated_at: string
    has_data: boolean
    current_case_count: number
    data_freshness_seconds: number | null
    refresh_min_interval_seconds?: number
    refresh_available_in_seconds?: number
    last_refresh_result?: RefreshHistoryItem
    refresh_history?: RefreshHistoryItem[]
    fetched_month_range: {
        latest: string | null
        earliest: string | null
    }
    selected_sources?: string[]
    supported_sources?: string[]
}

export type RefreshHistoryItem = {
    occurred_at: string
    status: 'success' | 'error' | 'blocked' | 'denied' | string
    message: string
    triggered_by: string
    details?: Record<string, unknown>
}

export type OverviewStats = {
    total_cases: number
    finalized_cases: number
    pending_cases: number
    maturity_ratio: number
    median_days: number
    median_ci_low: number
    median_ci_high: number
    p90_days: number
    p90_ci_low: number
    p90_ci_high: number
    mean_days: number
    iqr_days: number
    std_days: number
    long_tail_90plus_ratio: number
}

export type MonthlyItem = {
    submit_month: string
    total_cases: number
    clear_cases: number
    reject_cases: number
    pending_cases: number
    clear_ratio: number
    pending_ratio: number
    maturity_ratio: number
    finalized_count: number
    median_days: number | null
    p90_days: number | null
    long_tail_90plus_ratio: number | null
}

export type SensitivityItem = {
    scenario: 'Conservative' | 'Neutral' | 'Aggressive'
    median_days: number
    p90_days: number
    long_tail_90plus_ratio: number
}

export type CaseItem = {
    source_month: string
    case_number: string
    nickname: string
    visa_type: string
    visa_entry: string
    consulate: string
    major: string
    status: string
    check_date: string
    complete_date: string
    waiting_days_reported: string
    waiting_days_calc: string
    observed_days: string
    event: string
    detail_url: string
    update_url: string
}

export type Filters = {
    visa_types: string[]
    consulates: string[]
    statuses: string[]
    entries: string[]
    months: string[]
}

export type RefreshPayload = {
    all_months?: boolean
    months?: number
    from_month?: string | null
    sources?: string[]
}

export type CohortItem = {
    cohort: string
    total_cases: number
    finalized_cases: number
    pending_cases: number
    maturity_ratio: number
    median_days: number | null
    p90_days: number | null
    long_tail_90plus_ratio: number | null
}

export type DistributionItem = {
    bucket: string
    count: number
    ratio: number
}

export type ComparisonMetrics = {
    median_days: number
    p90_days: number
    pending_ratio: number
}

export type ComparisonData = {
    latest_month: string | null
    baseline_month: string | null
    latest: ComparisonMetrics | null
    baseline: ComparisonMetrics | null
    delta: ComparisonMetrics | null
}

export type AnomalyItem = {
    case_number: string
    visa_type: string
    consulate: string
    status: string
    check_date: string
    days: number
    reason: string
    detail_url: string
    update_url: string
}
