import type { CaseItem, Filters, MonthlyItem, OptionsResponse, OverviewStats, SensitivityItem } from './types'

const API_BASE = 'http://127.0.0.1:8000/api/v1'

function paramsFromFilters(filters: Filters): URLSearchParams {
    const params = new URLSearchParams()
    const assign = (key: keyof Filters) => {
        if (filters[key].length) {
            params.set(key, filters[key].join(','))
        }
    }
    assign('visa_types')
    assign('consulates')
    assign('statuses')
    assign('entries')
    assign('months')
    return params
}

async function fetchJson<T>(path: string): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`)
    if (!res.ok) {
        throw new Error(`API ${path} failed: ${res.status}`)
    }
    return await res.json() as T
}

export async function getOptions(): Promise<OptionsResponse> {
    return fetchJson<OptionsResponse>('/meta/options')
}

export async function refreshData(allMonths = false, months = 6): Promise<void> {
    const res = await fetch(`${API_BASE}/tasks/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ all_months: allMonths, months })
    })
    if (!res.ok) {
        throw new Error(`refresh failed: ${res.status}`)
    }
}

export async function getOverview(filters: Filters): Promise<OverviewStats> {
    const params = paramsFromFilters(filters)
    return fetchJson<OverviewStats>(`/stats/overview?${params.toString()}`)
}

export async function getMonthly(filters: Filters): Promise<MonthlyItem[]> {
    const params = paramsFromFilters(filters)
    const data = await fetchJson<{ items: MonthlyItem[] }>(`/stats/monthly?${params.toString()}`)
    return data.items
}

export async function getSensitivity(filters: Filters): Promise<SensitivityItem[]> {
    const params = paramsFromFilters(filters)
    const data = await fetchJson<{ items: SensitivityItem[] }>(`/stats/sensitivity?${params.toString()}`)
    return data.items
}

export async function getCases(filters: Filters, limit = 200): Promise<{ total: number; items: CaseItem[] }> {
    const params = paramsFromFilters(filters)
    params.set('limit', String(limit))
    return fetchJson<{ total: number; limit: number; offset: number; items: CaseItem[] }>(`/cases?${params.toString()}`)
}

export function exportCasesUrl(filters: Filters): string {
    const params = paramsFromFilters(filters)
    return `${API_BASE}/export/cases.csv?${params.toString()}`
}

export function exportReportUrl(filters: Filters): string {
    const params = paramsFromFilters(filters)
    return `${API_BASE}/export/report?${params.toString()}`
}
