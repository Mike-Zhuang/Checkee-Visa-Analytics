import type {
    AnomalyItem,
    CaseItem,
    CohortItem,
    ComparisonData,
    ConsulateGroupsResponse,
    DistributionItem,
    Filters,
    MetaState,
    MonthlyItem,
    OptionsResponse,
    OverviewStats,
    RefreshPayload,
    SensitivityItem
} from './types'
import { frontendConfig } from './config'

const API_BASE = frontendConfig.apiBaseUrl

export function paramsFromFilters(filters: Filters): URLSearchParams {
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

async function parseErrorDetail(response: Response): Promise<string> {
    try {
        const payload = await response.json() as { detail?: string }
        if (payload.detail) {
            return payload.detail
        }
    } catch {
        return ''
    }
    return ''
}

async function refreshDataInternal(payload: RefreshPayload, adminKey?: string): Promise<void> {
    const headers: HeadersInit = { 'Content-Type': 'application/json' }
    const normalizedAdminKey = adminKey?.trim()
    if (normalizedAdminKey) {
        headers['X-Admin-Key'] = normalizedAdminKey
    }

    const res = await fetch(`${API_BASE}/tasks/refresh`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`refresh failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
}

export async function refreshData(payload: RefreshPayload = { all_months: false, months: 6 }): Promise<void> {
    return refreshDataInternal(payload)
}

export async function refreshDataAsAdmin(
    payload: RefreshPayload = { all_months: false, months: 6 },
    adminKey: string
): Promise<void> {
    return refreshDataInternal(payload, adminKey)
}

export async function getMetaState(): Promise<MetaState> {
    return fetchJson<MetaState>('/meta/state')
}

export async function getConsulateGroups(): Promise<ConsulateGroupsResponse> {
    return fetchJson<ConsulateGroupsResponse>('/meta/consulate-groups')
}

export async function getOverview(filters: Filters): Promise<OverviewStats> {
    const params = paramsFromFilters(filters)
    const query = params.toString()
    return fetchJson<OverviewStats>(`/stats/overview${query ? `?${query}` : ''}`)
}

export async function getMonthly(filters: Filters): Promise<MonthlyItem[]> {
    const params = paramsFromFilters(filters)
    const query = params.toString()
    const data = await fetchJson<{ items: MonthlyItem[] }>(`/stats/monthly${query ? `?${query}` : ''}`)
    return data.items
}

export async function getSensitivity(filters: Filters): Promise<SensitivityItem[]> {
    const params = paramsFromFilters(filters)
    const query = params.toString()
    const data = await fetchJson<{ items: SensitivityItem[] }>(`/stats/sensitivity${query ? `?${query}` : ''}`)
    return data.items
}

export async function getCohorts(filters: Filters): Promise<CohortItem[]> {
    const params = paramsFromFilters(filters)
    const query = params.toString()
    const data = await fetchJson<{ items: CohortItem[] }>(`/stats/cohorts${query ? `?${query}` : ''}`)
    return data.items
}

export async function getDistribution(filters: Filters): Promise<DistributionItem[]> {
    const params = paramsFromFilters(filters)
    const query = params.toString()
    const data = await fetchJson<{ items: DistributionItem[] }>(`/stats/distribution${query ? `?${query}` : ''}`)
    return data.items
}

export async function getComparison(filters: Filters): Promise<ComparisonData> {
    const params = paramsFromFilters(filters)
    const query = params.toString()
    return fetchJson<ComparisonData>(`/stats/comparison${query ? `?${query}` : ''}`)
}

export async function getAnomalies(filters: Filters, thresholdDays = 120, limit = 50): Promise<AnomalyItem[]> {
    const params = paramsFromFilters(filters)
    params.set('threshold_days', String(thresholdDays))
    params.set('limit', String(limit))
    const data = await fetchJson<{ items: AnomalyItem[] }>(`/stats/anomalies?${params.toString()}`)
    return data.items
}

export async function getCases(filters: Filters, limit = 200, offset = 0): Promise<{ total: number; items: CaseItem[] }> {
    const params = paramsFromFilters(filters)
    params.set('limit', String(limit))
    params.set('offset', String(offset))
    return fetchJson<{ total: number; limit: number; offset: number; items: CaseItem[] }>(`/cases?${params.toString()}`)
}

export function exportCasesUrl(filters: Filters): string {
    const params = paramsFromFilters(filters)
    const query = params.toString()
    return `${API_BASE}/export/cases.csv${query ? `?${query}` : ''}`
}

export function exportReportUrl(filters: Filters): string {
    const params = paramsFromFilters(filters)
    const query = params.toString()
    return `${API_BASE}/export/report${query ? `?${query}` : ''}`
}
