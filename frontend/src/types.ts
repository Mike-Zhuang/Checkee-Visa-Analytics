export type OptionsResponse = {
    months: string[]
    visa_types: string[]
    consulates: string[]
    statuses: string[]
    entries: string[]
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
