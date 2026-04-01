import type {
    AsyncRefreshJobState,
    AsyncRefreshStartResponse,
    AdminLoginResponse,
    CaseSortBy,
    CaseSortOrder,
    DetailEnrichmentStartResponse,
    DetailEnrichmentState,
    MajorClassificationsResponse,
    AdminStaleRefreshResponse,
    AdminSessionStateResponse,
    UserSessionResponse,
    UserSessionStateResponse,
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
    RecommendationResponse,
    OverviewStats,
    RefreshPayload,
    SensitivityItem,
    UserFilterPresetListResponse,
    UserFilterPresetMutationResponse
} from './types'
import { frontendConfig } from './config'

const API_BASE = frontendConfig.apiBaseUrl

export function paramsFromFilters(filters: Filters): URLSearchParams {
    const params = new URLSearchParams()
    type ArrayFilterKey =
        | 'visa_types'
        | 'consulates'
        | 'statuses'
        | 'entries'
        | 'months'
        | 'major_categories_l1'
        | 'major_categories_l2'
        | 'majors'
        | 'employers'
        | 'detail_cities'
        | 'detail_states'

    const assignArray = (key: ArrayFilterKey) => {
        const values = filters[key]
        if (values.length) {
            params.set(key, values.join(','))
        }
    }
    assignArray('visa_types')
    assignArray('consulates')
    assignArray('statuses')
    assignArray('entries')
    assignArray('months')
    assignArray('major_categories_l1')
    assignArray('major_categories_l2')
    assignArray('majors')
    assignArray('employers')
    assignArray('detail_cities')
    assignArray('detail_states')

    if (filters.has_note) {
        params.set('has_note', 'true')
    }

    const searchText = filters.search_text.trim()
    if (searchText) {
        params.set('search_text', searchText)
    }

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

async function refreshDataInternal(payload: RefreshPayload, adminKey?: string, adminToken?: string): Promise<void> {
    const headers: HeadersInit = { 'Content-Type': 'application/json' }
    const normalizedAdminKey = adminKey?.trim()
    if (normalizedAdminKey) {
        headers['X-Admin-Key'] = normalizedAdminKey
    }

    const normalizedAdminToken = adminToken?.trim()
    if (normalizedAdminToken) {
        headers.Authorization = `Bearer ${normalizedAdminToken}`
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

export async function refreshDataWithSession(
    payload: RefreshPayload = { all_months: false, months: 6 },
    adminToken: string
): Promise<void> {
    return refreshDataInternal(payload, undefined, adminToken)
}

export async function startAdminAsyncRefresh(
    payload: RefreshPayload = { all_months: false, months: 6 },
    adminToken: string
): Promise<AsyncRefreshStartResponse> {
    const res = await fetch(`${API_BASE}/admin/refresh/async-start`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${adminToken.trim()}`
        },
        body: JSON.stringify(payload)
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`admin async refresh start failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as AsyncRefreshStartResponse
}

export async function getAdminAsyncRefreshState(adminToken: string): Promise<AsyncRefreshJobState> {
    const res = await fetch(`${API_BASE}/admin/refresh/async-state`, {
        headers: { Authorization: `Bearer ${adminToken.trim()}` }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`admin async refresh state failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as AsyncRefreshJobState
}

export async function startAdminDetailEnrichment(adminToken: string): Promise<DetailEnrichmentStartResponse> {
    const res = await fetch(`${API_BASE}/admin/detail-enrichment/start`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${adminToken.trim()}` }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`admin detail enrichment start failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as DetailEnrichmentStartResponse
}

export async function getAdminDetailEnrichmentState(adminToken: string): Promise<DetailEnrichmentState> {
    const res = await fetch(`${API_BASE}/admin/detail-enrichment/state`, {
        headers: { Authorization: `Bearer ${adminToken.trim()}` }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`admin detail enrichment state failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as DetailEnrichmentState
}

export async function loginAdmin(password: string): Promise<AdminLoginResponse> {
    const res = await fetch(`${API_BASE}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`admin login failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as AdminLoginResponse
}

export async function getAdminSession(adminToken: string): Promise<AdminSessionStateResponse> {
    const res = await fetch(`${API_BASE}/admin/session`, {
        headers: { Authorization: `Bearer ${adminToken.trim()}` }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`admin session failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as AdminSessionStateResponse
}

export async function triggerAdminStaleRefresh(adminToken: string): Promise<AdminStaleRefreshResponse> {
    const res = await fetch(`${API_BASE}/admin/refresh/stale-trigger`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${adminToken.trim()}` }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`admin stale refresh failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as AdminStaleRefreshResponse
}

export async function logoutAdmin(adminToken: string): Promise<void> {
    const res = await fetch(`${API_BASE}/admin/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${adminToken.trim()}` }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`admin logout failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
}

export async function registerUser(username: string, password: string): Promise<UserSessionResponse> {
    const res = await fetch(`${API_BASE}/user/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`user register failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as UserSessionResponse
}

export async function loginUser(username: string, password: string): Promise<UserSessionResponse> {
    const res = await fetch(`${API_BASE}/user/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`user login failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as UserSessionResponse
}

export async function getUserSession(userToken: string): Promise<UserSessionStateResponse> {
    const res = await fetch(`${API_BASE}/user/session`, {
        headers: { Authorization: `Bearer ${userToken.trim()}` }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`user session failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as UserSessionStateResponse
}

export async function logoutUser(userToken: string): Promise<void> {
    const res = await fetch(`${API_BASE}/user/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${userToken.trim()}` }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`user logout failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
}

export async function getUserFilterPresets(userToken: string): Promise<UserFilterPresetListResponse> {
    const res = await fetch(`${API_BASE}/user/filter-presets`, {
        headers: { Authorization: `Bearer ${userToken.trim()}` }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`user filter presets failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as UserFilterPresetListResponse
}

export async function createUserFilterPreset(
    userToken: string,
    name: string,
    filters: Filters
): Promise<UserFilterPresetMutationResponse> {
    const res = await fetch(`${API_BASE}/user/filter-presets`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${userToken.trim()}`
        },
        body: JSON.stringify({ name, filters })
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`user create preset failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as UserFilterPresetMutationResponse
}

export async function updateUserFilterPreset(
    userToken: string,
    presetId: string,
    payload: { name?: string; filters?: Filters }
): Promise<UserFilterPresetMutationResponse> {
    const res = await fetch(`${API_BASE}/user/filter-presets/${encodeURIComponent(presetId)}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${userToken.trim()}`
        },
        body: JSON.stringify(payload)
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`user update preset failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as UserFilterPresetMutationResponse
}

export async function deleteUserFilterPreset(userToken: string, presetId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/user/filter-presets/${encodeURIComponent(presetId)}`, {
        method: 'DELETE',
        headers: {
            Authorization: `Bearer ${userToken.trim()}`
        }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`user delete preset failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
}

export async function getAdminMajorClassifications(
    adminToken: string,
    query = '',
    limit = 500
): Promise<MajorClassificationsResponse> {
    const params = new URLSearchParams()
    if (query.trim()) {
        params.set('q', query.trim())
    }
    params.set('limit', String(limit))
    const suffix = params.toString() ? `?${params.toString()}` : ''

    const res = await fetch(`${API_BASE}/admin/major-classifications${suffix}`, {
        headers: { Authorization: `Bearer ${adminToken.trim()}` }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`admin major classifications failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
    return await res.json() as MajorClassificationsResponse
}

export async function saveAdminMajorOverrides(
    adminToken: string,
    items: Array<{ major: string; category_l1: string; category_l2: string }>
): Promise<void> {
    const res = await fetch(`${API_BASE}/admin/major-classifications`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${adminToken.trim()}`
        },
        body: JSON.stringify({ items })
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`admin major override save failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
}

export async function deleteAdminMajorOverride(adminToken: string, major: string): Promise<void> {
    const params = new URLSearchParams({ major })
    const res = await fetch(`${API_BASE}/admin/major-classifications?${params.toString()}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${adminToken.trim()}` }
    })
    if (!res.ok) {
        const detail = await parseErrorDetail(res)
        throw new Error(`admin major override delete failed: ${res.status}${detail ? ` ${detail}` : ''}`)
    }
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

export async function getRecommendation(filters: Filters): Promise<RecommendationResponse> {
    const params = paramsFromFilters(filters)
    const query = params.toString()
    return fetchJson<RecommendationResponse>(`/stats/recommendation${query ? `?${query}` : ''}`)
}

export async function getAnomalies(filters: Filters, thresholdDays = 120, limit = 50): Promise<AnomalyItem[]> {
    const params = paramsFromFilters(filters)
    params.set('threshold_days', String(thresholdDays))
    params.set('limit', String(limit))
    const data = await fetchJson<{ items: AnomalyItem[] }>(`/stats/anomalies?${params.toString()}`)
    return data.items
}

export async function getCases(
    filters: Filters,
    limit = 200,
    offset = 0,
    sortBy: CaseSortBy = 'check_date',
    sortOrder: CaseSortOrder = 'desc'
): Promise<{ total: number; items: CaseItem[] }> {
    const params = paramsFromFilters(filters)
    params.set('limit', String(limit))
    params.set('offset', String(offset))
    params.set('sort_by', sortBy)
    params.set('sort_order', sortOrder)
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
