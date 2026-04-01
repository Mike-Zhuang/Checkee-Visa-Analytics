import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
    createUserFilterPreset,
    deleteUserFilterPreset,
    exportCasesUrl,
    exportReportUrl,
    getAnomalies,
    getCases,
    getCohorts,
    getComparison,
    getConsulateGroups,
    getDistribution,
    getMetaState,
    getMonthly,
    getOptions,
    getOverview,
    getRecommendation,
    getUserFilterPresets,
    getUserSession,
    loginUser,
    getSensitivity,
    logoutUser,
    registerUser,
    refreshData
} from './api'
import { frontendConfig } from './config'
import CaseTable from './components/CaseTable'
import CohortTable from './components/CohortTable'
import ComparisonPanel from './components/ComparisonPanel'
import DistributionPanel from './components/DistributionPanel'
import FilterBar from './components/FilterBar'
import MonthlyChart from './components/MonthlyChart'
import SensitivityTable from './components/SensitivityTable'
import StatCards from './components/StatCards'
import AnomalyTable from './components/AnomalyTable'
import SuggestionPanel from './components/SuggestionPanel'
import type {
    AnomalyItem,
    CaseSortBy,
    CaseSortOrder,
    CaseItem,
    CohortItem,
    ComparisonData,
    ConsulateGroup,
    DistributionItem,
    Filters,
    MetaState,
    MonthlyItem,
    OptionsResponse,
    OverviewStats,
    RecommendationResponse,
    RefreshPayload,
    SensitivityItem,
    UserFilterPresetItem
} from './types'

const EMPTY_FILTERS: Filters = {
    visa_types: [],
    consulates: [],
    statuses: [],
    entries: [],
    months: [],
    major_categories_l1: [],
    major_categories_l2: [],
    majors: [],
    employers: [],
    detail_cities: [],
    detail_states: [],
    has_note: false,
    search_text: ''
}

const USER_TOKEN_STORAGE_KEY = 'checkee-user-token'

type ErrorKey =
    | 'overview'
    | 'monthly'
    | 'sensitivity'
    | 'cohorts'
    | 'distribution'
    | 'comparison'
    | 'anomalies'
    | 'recommendation'
    | 'metaState'
    | 'cases'
    | 'options'
    | 'groups'
    | 'refresh'

type GlassTier = 'full' | 'lite'

function detectGlassTier(): GlassTier {
    if (typeof window === 'undefined') {
        return 'lite'
    }

    const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    if (prefersReducedMotion) {
        return 'lite'
    }

    const ua = navigator.userAgent.toLowerCase()
    const isFirefox = ua.includes('firefox')
    const isSafari = ua.includes('safari') && !ua.includes('chrome') && !ua.includes('chromium') && !ua.includes('android')
    const isMobile = /mobile|iphone|ipad|ipod|android/.test(ua)
    const cpuCores = navigator.hardwareConcurrency || 4

    if (isFirefox || isSafari || isMobile || cpuCores <= 4) {
        return 'lite'
    }

    return 'full'
}

export default function App() {
    const { t, i18n } = useTranslation()
    const [initialized, setInitialized] = useState(false)
    const hasBootstrappedOverviewRef = useRef(false)
    const hasBootstrappedCasesRef = useRef(false)
    const [overviewLoading, setOverviewLoading] = useState(false)
    const [casesLoading, setCasesLoading] = useState(false)
    const [errors, setErrors] = useState<Partial<Record<ErrorKey, string>>>({})
    const [draftFilters, setDraftFilters] = useState<Filters>(EMPTY_FILTERS)
    const [appliedFilters, setAppliedFilters] = useState<Filters>(EMPTY_FILTERS)
    const [refreshFromMonth, setRefreshFromMonth] = useState('')
    const [refreshSources, setRefreshSources] = useState<string[]>(['monthly_track'])
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [refreshFeedback, setRefreshFeedback] = useState<{ kind: 'success' | 'error'; message: string } | null>(null)
    const [options, setOptions] = useState<OptionsResponse>({
        months: [],
        visa_types: [],
        consulates: [],
        statuses: [],
        entries: [],
        major_categories_l1: [],
        major_categories_l2: [],
        major_category_mapping: {},
        majors: [],
        employers: [],
        detail_cities: [],
        detail_states: [],
        fetch_sources: []
    })
    const [consulateGroups, setConsulateGroups] = useState<ConsulateGroup[]>([])
    const [metaState, setMetaState] = useState<MetaState | null>(null)
    const [overview, setOverview] = useState<OverviewStats | null>(null)
    const [monthly, setMonthly] = useState<MonthlyItem[]>([])
    const [sensitivity, setSensitivity] = useState<SensitivityItem[]>([])
    const [cohorts, setCohorts] = useState<CohortItem[]>([])
    const [distribution, setDistribution] = useState<DistributionItem[]>([])
    const [comparison, setComparison] = useState<ComparisonData | null>(null)
    const [anomalies, setAnomalies] = useState<AnomalyItem[]>([])
    const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null)
    const [cases, setCases] = useState<CaseItem[]>([])
    const [caseTotal, setCaseTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(frontendConfig.defaultPageSize)
    const [localCaseHasNoteOnly, setLocalCaseHasNoteOnly] = useState(false)
    const [caseSortBy, setCaseSortBy] = useState<CaseSortBy>('check_date')
    const [caseSortOrder, setCaseSortOrder] = useState<CaseSortOrder>('desc')
    const [glassTier, setGlassTier] = useState<GlassTier>(() => detectGlassTier())
    const [userToken, setUserToken] = useState<string>(() => {
        if (typeof window === 'undefined') return ''
        return window.sessionStorage.getItem(USER_TOKEN_STORAGE_KEY) ?? ''
    })
    const [userNameInput, setUserNameInput] = useState('')
    const [userPasswordInput, setUserPasswordInput] = useState('')
    const [userName, setUserName] = useState('')
    const [userSessionExpiresAt, setUserSessionExpiresAt] = useState<string | null>(null)
    const [userAuthError, setUserAuthError] = useState<string | null>(null)
    const [isUserAuthLoading, setIsUserAuthLoading] = useState(false)
    const [userPresetName, setUserPresetName] = useState('')
    const [userPresets, setUserPresets] = useState<UserFilterPresetItem[]>([])
    const [isPresetLoading, setIsPresetLoading] = useState(false)
    const [presetFeedback, setPresetFeedback] = useState<{ kind: 'success' | 'error'; message: string } | null>(null)

    useEffect(() => {
        const updateTier = () => setGlassTier(detectGlassTier())
        const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')

        updateTier()

        if (motionQuery.addEventListener) {
            motionQuery.addEventListener('change', updateTier)
            return () => motionQuery.removeEventListener('change', updateTier)
        }

        motionQuery.addListener(updateTier)
        return () => motionQuery.removeListener(updateTier)
    }, [])

    const setError = (key: ErrorKey, value: string) => {
        setErrors((prev) => ({ ...prev, [key]: value }))
    }

    const clearErrors = (keys: ErrorKey[]) => {
        setErrors((prev) => {
            const next = { ...prev }
            for (const key of keys) {
                delete next[key]
            }
            return next
        })
    }

    const clearUserSession = useCallback(() => {
        setUserToken('')
        setUserName('')
        setUserSessionExpiresAt(null)
        setUserPresets([])
        if (typeof window !== 'undefined') {
            window.sessionStorage.removeItem(USER_TOKEN_STORAGE_KEY)
        }
    }, [])

    const loadUserPresets = useCallback(async (token: string) => {
        setIsPresetLoading(true)
        try {
            const payload = await getUserFilterPresets(token)
            setUserPresets(payload.items)
            setPresetFeedback(null)
        } catch (error) {
            const message = error instanceof Error ? error.message : t('userAuth.presetLoadFailed')
            setPresetFeedback({ kind: 'error', message: `${t('userAuth.presetLoadFailed')}: ${message}` })
        } finally {
            setIsPresetLoading(false)
        }
    }, [t])

    const persistUserSession = useCallback((token: string, username: string, expiresAt: string) => {
        setUserToken(token)
        setUserName(username)
        setUserSessionExpiresAt(expiresAt)
        setUserAuthError(null)
        setUserPasswordInput('')
        if (typeof window !== 'undefined') {
            window.sessionStorage.setItem(USER_TOKEN_STORAGE_KEY, token)
        }
    }, [])

    const onUserRegister = useCallback(async () => {
        const username = userNameInput.trim().toLowerCase()
        const password = userPasswordInput
        if (!username || !password) {
            setUserAuthError(t('userAuth.inputRequired'))
            return
        }

        setIsUserAuthLoading(true)
        try {
            const payload = await registerUser(username, password)
            persistUserSession(payload.token, payload.username, payload.expires_at)
            await loadUserPresets(payload.token)
            setUserPresetName('')
        } catch (error) {
            const message = error instanceof Error ? error.message : t('userAuth.registerFailed')
            setUserAuthError(`${t('userAuth.registerFailed')}: ${message}`)
        } finally {
            setIsUserAuthLoading(false)
        }
    }, [loadUserPresets, persistUserSession, t, userNameInput, userPasswordInput])

    const onUserLogin = useCallback(async () => {
        const username = userNameInput.trim().toLowerCase()
        const password = userPasswordInput
        if (!username || !password) {
            setUserAuthError(t('userAuth.inputRequired'))
            return
        }

        setIsUserAuthLoading(true)
        try {
            const payload = await loginUser(username, password)
            persistUserSession(payload.token, payload.username, payload.expires_at)
            await loadUserPresets(payload.token)
            setUserPresetName('')
        } catch (error) {
            const message = error instanceof Error ? error.message : t('userAuth.loginFailed')
            setUserAuthError(`${t('userAuth.loginFailed')}: ${message}`)
        } finally {
            setIsUserAuthLoading(false)
        }
    }, [loadUserPresets, persistUserSession, t, userNameInput, userPasswordInput])

    const onUserLogout = useCallback(async () => {
        if (!userToken.trim()) {
            clearUserSession()
            return
        }

        setIsUserAuthLoading(true)
        try {
            await logoutUser(userToken)
        } catch {
            // 前端会话会被清理，后端退出失败不阻断
        } finally {
            clearUserSession()
            setIsUserAuthLoading(false)
            setPresetFeedback(null)
        }
    }, [clearUserSession, userToken])

    const onSaveCurrentPreset = useCallback(async () => {
        if (!userToken.trim()) {
            setPresetFeedback({ kind: 'error', message: t('userAuth.loginRequired') })
            return
        }

        const name = userPresetName.trim()
        if (!name) {
            setPresetFeedback({ kind: 'error', message: t('userAuth.presetNameRequired') })
            return
        }

        setIsPresetLoading(true)
        try {
            await createUserFilterPreset(userToken, name, draftFilters)
            await loadUserPresets(userToken)
            setPresetFeedback({ kind: 'success', message: t('userAuth.presetSaved') })
            setUserPresetName('')
        } catch (error) {
            const message = error instanceof Error ? error.message : t('userAuth.presetSaveFailed')
            setPresetFeedback({ kind: 'error', message: `${t('userAuth.presetSaveFailed')}: ${message}` })
        } finally {
            setIsPresetLoading(false)
        }
    }, [draftFilters, loadUserPresets, t, userPresetName, userToken])

    const onLoadPresetFilters = useCallback((presetFilters: Filters) => {
        setPage(1)
        setDraftFilters(presetFilters)
        setAppliedFilters(presetFilters)
        setPresetFeedback({ kind: 'success', message: t('userAuth.presetApplied') })
    }, [t])

    const onDeletePreset = useCallback(async (presetId: string) => {
        if (!userToken.trim()) {
            setPresetFeedback({ kind: 'error', message: t('userAuth.loginRequired') })
            return
        }

        setIsPresetLoading(true)
        try {
            await deleteUserFilterPreset(userToken, presetId)
            await loadUserPresets(userToken)
            setPresetFeedback({ kind: 'success', message: t('userAuth.presetDeleted') })
        } catch (error) {
            const message = error instanceof Error ? error.message : t('userAuth.presetDeleteFailed')
            setPresetFeedback({ kind: 'error', message: `${t('userAuth.presetDeleteFailed')}: ${message}` })
        } finally {
            setIsPresetLoading(false)
        }
    }, [loadUserPresets, t, userToken])

    useEffect(() => {
        if (!frontendConfig.enableUserAuth) return
        if (!userToken.trim()) return

        let active = true
        setIsUserAuthLoading(true)
        void getUserSession(userToken)
            .then(async (session) => {
                if (!active) return
                setUserName(session.username)
                setUserSessionExpiresAt(session.expires_at)
                setUserAuthError(null)
                await loadUserPresets(userToken)
            })
            .catch(() => {
                if (!active) return
                clearUserSession()
                setUserAuthError(t('userAuth.sessionExpired'))
            })
            .finally(() => {
                if (!active) return
                setIsUserAuthLoading(false)
            })

        return () => {
            active = false
        }
    }, [clearUserSession, loadUserPresets, t, userToken])

    const formatReason = (reason: unknown): string => {
        if (!(reason instanceof Error)) {
            return t('errors.reason.temporary')
        }

        const message = reason.message.toLowerCase()
        if (message.includes('timeout')) return t('errors.reason.timeout')
        if (message.includes('failed to fetch') || message.includes('network')) return t('errors.reason.network')
        if (message.includes('failed: 5')) return t('errors.reason.serverBusy')
        if (message.includes('failed: 4')) return t('errors.reason.badRequest')
        return t('errors.reason.temporary')
    }

    const sourceName = (source: string): string => {
        if (source === 'monthly_track') return t('filter.sourceMonthlyShort')
        if (source === 'latest_snapshot') return t('filter.sourceLatestShort')
        return source
    }

    const mergeCaseFilters = (baseFilters: Filters, localHasNoteOnly: boolean): Filters => {
        if (!localHasNoteOnly || baseFilters.has_note) {
            return baseFilters
        }
        return { ...baseFilters, has_note: true }
    }

    const fetchOverviewBundle = async (activeFilters: Filters) => {
        setOverviewLoading(true)
        clearErrors(['overview', 'monthly', 'sensitivity', 'cohorts', 'distribution', 'comparison', 'anomalies', 'recommendation'])

        const [
            overviewRes,
            monthlyRes,
            sensitivityRes,
            cohortsRes,
            distributionRes,
            comparisonRes,
            anomaliesRes,
            recommendationRes
        ] = await Promise.allSettled([
            getOverview(activeFilters),
            getMonthly(activeFilters),
            getSensitivity(activeFilters),
            getCohorts(activeFilters),
            getDistribution(activeFilters),
            getComparison(activeFilters),
            getAnomalies(activeFilters),
            getRecommendation(activeFilters)
        ])

        if (overviewRes.status === 'fulfilled') {
            setOverview(overviewRes.value)
        } else {
            setError('overview', t('errors.overview', { message: formatReason(overviewRes.reason) }))
        }

        if (monthlyRes.status === 'fulfilled') {
            setMonthly(monthlyRes.value)
        } else {
            setError('monthly', t('errors.monthly', { message: formatReason(monthlyRes.reason) }))
        }

        if (sensitivityRes.status === 'fulfilled') {
            setSensitivity(sensitivityRes.value)
        } else {
            setError('sensitivity', t('errors.sensitivity', { message: formatReason(sensitivityRes.reason) }))
        }

        if (cohortsRes.status === 'fulfilled') {
            setCohorts(cohortsRes.value)
        } else {
            setError('cohorts', t('errors.cohorts', { message: formatReason(cohortsRes.reason) }))
        }

        if (distributionRes.status === 'fulfilled') {
            setDistribution(distributionRes.value)
        } else {
            setError('distribution', t('errors.distribution', { message: formatReason(distributionRes.reason) }))
        }

        if (comparisonRes.status === 'fulfilled') {
            setComparison(comparisonRes.value)
        } else {
            setError('comparison', t('errors.comparison', { message: formatReason(comparisonRes.reason) }))
        }

        if (anomaliesRes.status === 'fulfilled') {
            setAnomalies(anomaliesRes.value)
        } else {
            setError('anomalies', t('errors.anomalies', { message: formatReason(anomaliesRes.reason) }))
        }

        if (recommendationRes.status === 'fulfilled') {
            setRecommendation(recommendationRes.value)
        } else {
            setError('recommendation', t('errors.recommendation', { message: formatReason(recommendationRes.reason) }))
        }

        setOverviewLoading(false)
    }

    const fetchCasesPage = async (
        activeFilters: Filters,
        nextPage: number,
        nextPageSize: number,
        sortBy: CaseSortBy,
        sortOrder: CaseSortOrder
    ) => {
        setCasesLoading(true)
        try {
            const offset = (nextPage - 1) * nextPageSize
            const ca = await getCases(activeFilters, nextPageSize, offset, sortBy, sortOrder)
            setCases(ca.items)
            setCaseTotal(ca.total)
            clearErrors(['cases'])
        } catch (e) {
            setError('cases', t('errors.cases', { message: formatReason(e) }))
        } finally {
            setCasesLoading(false)
        }
    }

    const fetchMetaOptions = async () => {
        const [optionsRes, groupsRes, stateRes] = await Promise.allSettled([
            getOptions(),
            getConsulateGroups(),
            getMetaState()
        ])

        clearErrors(['options', 'groups', 'metaState'])
        if (optionsRes.status === 'fulfilled') {
            setOptions(optionsRes.value)
            setRefreshSources((prev) => {
                const fetched = optionsRes.value.fetch_sources
                if (fetched.length === 0) return prev
                const kept = prev.filter((item) => fetched.includes(item))
                if (kept.length > 0) return kept
                if (fetched.includes('monthly_track')) return ['monthly_track']
                return [fetched[0]]
            })
        } else {
            setError('options', t('errors.options', { message: formatReason(optionsRes.reason) }))
        }

        if (groupsRes.status === 'fulfilled') {
            setConsulateGroups(groupsRes.value.groups)
        } else {
            setError('groups', t('errors.groups', { message: formatReason(groupsRes.reason) }))
        }

        if (stateRes.status === 'fulfilled') {
            setMetaState(stateRes.value)
        } else {
            setError('metaState', t('errors.metaState', { message: formatReason(stateRes.reason) }))
        }
    }

    const init = async () => {
        setErrors({})
        await fetchMetaOptions()
        await fetchCasesPage(
            mergeCaseFilters(appliedFilters, localCaseHasNoteOnly),
            1,
            pageSize,
            caseSortBy,
            caseSortOrder
        )
        void fetchOverviewBundle(appliedFilters)
        setInitialized(true)
    }

    useEffect(() => {
        void init()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    useEffect(() => {
        if (!initialized) return
        if (!hasBootstrappedOverviewRef.current) {
            hasBootstrappedOverviewRef.current = true
            return
        }
        void fetchOverviewBundle(appliedFilters)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [appliedFilters, initialized])

    const caseFilters = useMemo(
        () => mergeCaseFilters(appliedFilters, localCaseHasNoteOnly),
        [appliedFilters, localCaseHasNoteOnly]
    )

    useEffect(() => {
        if (!initialized) return
        if (!hasBootstrappedCasesRef.current) {
            hasBootstrappedCasesRef.current = true
            return
        }
        void fetchCasesPage(caseFilters, page, pageSize, caseSortBy, caseSortOrder)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [caseFilters, page, pageSize, caseSortBy, caseSortOrder, initialized])

    const onRefresh = async (payload: RefreshPayload) => {
        setIsRefreshing(true)
        setRefreshFeedback(null)
        try {
            await refreshData(payload)
            await fetchMetaOptions()
            setPage(1)
            await fetchOverviewBundle(appliedFilters)
            await fetchCasesPage(caseFilters, 1, pageSize, caseSortBy, caseSortOrder)
            clearErrors(['refresh'])
            setRefreshFeedback({ kind: 'success', message: t('filter.refreshSuccess') })
        } catch (e) {
            setError('refresh', t('errors.refresh', { message: formatReason(e) }))
            setRefreshFeedback({ kind: 'error', message: t('filter.refreshFailedHint') })
        } finally {
            setIsRefreshing(false)
        }
    }

    const onFilterDraftChange = (next: Filters) => {
        setDraftFilters(next)
    }

    const onApplyFilters = () => {
        setPage(1)
        setAppliedFilters(draftFilters)
    }

    const onResetFilters = () => {
        setPage(1)
        setDraftFilters(EMPTY_FILTERS)
        setAppliedFilters(EMPTY_FILTERS)
    }

    const hasPendingFilterChanges = useMemo(
        () => JSON.stringify(draftFilters) !== JSON.stringify(appliedFilters),
        [draftFilters, appliedFilters]
    )

    const reportLink = useMemo(() => exportReportUrl(appliedFilters), [appliedFilters])
    const casesLink = useMemo(() => exportCasesUrl(appliedFilters), [appliedFilters])

    const freshnessHint = useMemo(() => {
        if (!metaState?.updated_at) return t('app.noRefresh')
        const fresh = metaState.data_freshness_seconds
        if (fresh == null) {
            return t('app.updatedOnly', { time: metaState.updated_at })
        }
        return t('app.updatedAgo', { time: metaState.updated_at, minutes: Math.floor(fresh / 60) })
    }, [metaState, t])

    const languageValue = i18n.resolvedLanguage?.startsWith('en') ? 'en' : 'zh'
    const errorList = Object.values(errors)
    const appVersionLabel = frontendConfig.appVersion.startsWith('v')
        ? frontendConfig.appVersion
        : `v${frontendConfig.appVersion}`

    return (
        <main className={`app-shell glass-tier-${glassTier}`}>
            <header className="hero">
                <div>
                    <h1>{t('app.title')}</h1>
                    <p>{t('app.subtitle')}</p>
                </div>
                <div className="hero-actions">
                    {frontendConfig.enableLanguageSwitch ? (
                        <label className="lang-switch" htmlFor="lang-select">
                            <span>{t('app.language')}</span>
                            <select
                                id="lang-select"
                                className="select-modern"
                                aria-label={t('app.language')}
                                value={languageValue}
                                onChange={(e) => void i18n.changeLanguage(e.currentTarget.value)}
                            >
                                <option value="zh">中文</option>
                                <option value="en">English</option>
                            </select>
                        </label>
                    ) : null}
                    <a href={reportLink} target="_blank" rel="noreferrer">{t('app.exportReport')}</a>
                    <a href={casesLink} target="_blank" rel="noreferrer">{t('app.exportCsv')}</a>
                </div>
            </header>

            <section className="meta-strip">
                <div className="meta-core">
                    <strong>{t('app.sampleCount', { count: metaState?.current_case_count ?? 0 })}</strong>
                    <span>{freshnessHint}</span>
                    {!frontendConfig.enablePublicRefresh ? (
                        <span className="public-refresh-off">{t('app.publicRefreshDisabled')}</span>
                    ) : null}
                </div>
                <details className="meta-more">
                    <summary>{t('app.moreInfo')}</summary>
                    <div className="meta-more-grid">
                        <span>
                            {t('app.fetchRange', {
                                earliest: metaState?.fetched_month_range?.earliest ?? t('common.na'),
                                latest: metaState?.fetched_month_range?.latest ?? t('common.na')
                            })}
                        </span>
                        <span>
                            {t('app.selectedSources', {
                                value: (metaState?.selected_sources && metaState.selected_sources.length > 0)
                                    ? metaState.selected_sources.map(sourceName).join(' / ')
                                    : t('common.na')
                            })}
                        </span>
                        {metaState?.truncated_by_limit ? (
                            <span className="warn">{t('app.monthLimit', { limit: metaState.month_limit })}</span>
                        ) : null}
                    </div>
                </details>
            </section>

            {frontendConfig.enableUserAuth ? (
                <section className="user-auth-panel" aria-label={t('userAuth.title')}>
                    <div className="panel-head">
                        <h3>{t('userAuth.title')}</h3>
                        <p>{t('userAuth.hint')}</p>
                    </div>
                    {!userName ? (
                        <div className="user-auth-form">
                            <label className="field field-inline" htmlFor="user-auth-username">
                                <span>{t('userAuth.username')}</span>
                                <input
                                    id="user-auth-username"
                                    type="text"
                                    value={userNameInput}
                                    autoComplete="username"
                                    placeholder={t('userAuth.usernamePlaceholder')}
                                    onChange={(e) => setUserNameInput(e.currentTarget.value)}
                                />
                            </label>
                            <label className="field field-inline" htmlFor="user-auth-password">
                                <span>{t('userAuth.password')}</span>
                                <input
                                    id="user-auth-password"
                                    type="password"
                                    value={userPasswordInput}
                                    autoComplete="current-password"
                                    placeholder={t('userAuth.passwordPlaceholder')}
                                    onChange={(e) => setUserPasswordInput(e.currentTarget.value)}
                                />
                            </label>
                            <div className="actions compact user-auth-actions">
                                <button type="button" className="ghost" disabled={isUserAuthLoading} onClick={() => void onUserRegister()}>
                                    {t('userAuth.register')}
                                </button>
                                <button type="button" disabled={isUserAuthLoading} onClick={() => void onUserLogin()}>
                                    {isUserAuthLoading ? t('userAuth.loading') : t('userAuth.login')}
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="user-auth-session">
                            <strong>{t('userAuth.loggedInAs', { username: userName })}</strong>
                            <span>{t('userAuth.expiresAt', { value: userSessionExpiresAt ?? t('common.na') })}</span>
                            <div className="actions compact user-auth-actions">
                                <button type="button" className="ghost" disabled={isUserAuthLoading} onClick={() => void onUserLogout()}>
                                    {t('userAuth.logout')}
                                </button>
                                <button
                                    type="button"
                                    className="ghost"
                                    disabled={isPresetLoading}
                                    onClick={() => void loadUserPresets(userToken)}
                                >
                                    {t('userAuth.refreshPresets')}
                                </button>
                            </div>
                        </div>
                    )}

                    {userAuthError ? <p className="error-inline">{userAuthError}</p> : null}

                    {userName ? (
                        <div className="user-preset-panel">
                            <div className="user-preset-create">
                                <label className="field field-inline" htmlFor="user-preset-name">
                                    <span>{t('userAuth.presetName')}</span>
                                    <input
                                        id="user-preset-name"
                                        type="text"
                                        value={userPresetName}
                                        placeholder={t('userAuth.presetNamePlaceholder')}
                                        onChange={(e) => setUserPresetName(e.currentTarget.value)}
                                    />
                                </label>
                                <button type="button" disabled={isPresetLoading} onClick={() => void onSaveCurrentPreset()}>
                                    {t('userAuth.saveCurrentFilters')}
                                </button>
                            </div>
                            {presetFeedback ? <p className={presetFeedback.kind === 'error' ? 'error-inline' : 'success-inline'}>{presetFeedback.message}</p> : null}
                            <div className="user-preset-list">
                                {userPresets.length === 0 ? (
                                    <p className="empty-copy">{t('userAuth.noPresets')}</p>
                                ) : (
                                    userPresets.map((preset) => (
                                        <div key={preset.id} className="user-preset-item">
                                            <div>
                                                <strong>{preset.name}</strong>
                                                <small>{t('userAuth.presetUpdatedAt', { value: preset.updated_at })}</small>
                                            </div>
                                            <div className="actions compact">
                                                <button type="button" className="ghost" onClick={() => onLoadPresetFilters(preset.filters)}>
                                                    {t('userAuth.applyPreset')}
                                                </button>
                                                <button type="button" className="ghost" onClick={() => void onDeletePreset(preset.id)}>
                                                    {t('userAuth.deletePreset')}
                                                </button>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    ) : null}
                </section>
            ) : null}

            <section className="starter-guide" role="note" aria-label={t('guide.title')}>
                <h3>{t('guide.title')}</h3>
                <ol>
                    <li>{frontendConfig.enablePublicRefresh ? t('guide.step1') : t('guide.step1Readonly')}</li>
                    <li>{t('guide.step2')}</li>
                    <li>{t('guide.step3')}</li>
                </ol>
            </section>

            {errorList.length > 0 ? (
                <section className="error-box" role="alert" aria-live="assertive" aria-atomic="true">
                    <ul>
                        {errorList.map((errorMsg, idx) => (
                            <li key={`error-${idx}`}>{errorMsg}</li>
                        ))}
                    </ul>
                    <button type="button" className="ghost" onClick={() => void init()}>{t('errors.retryAction')}</button>
                </section>
            ) : null}
            {(overviewLoading || casesLoading) ? (
                <div className="loading loading-floating" role="status" aria-live="polite" aria-atomic="true" aria-busy="true">
                    {t('common.loading')}
                </div>
            ) : null}

            <FilterBar
                options={options}
                consulateGroups={consulateGroups}
                filters={draftFilters}
                refreshFromMonth={refreshFromMonth}
                refreshSources={refreshSources}
                availableRefreshSources={options.fetch_sources}
                defaultRefreshMonths={frontendConfig.defaultRefreshMonths}
                showConsulateGroups={frontendConfig.enableConsulateGroups}
                showRefreshControls={frontendConfig.enablePublicRefresh}
                isRefreshing={isRefreshing}
                refreshFeedback={refreshFeedback}
                onRefreshFromMonthChange={setRefreshFromMonth}
                onRefreshSourcesChange={setRefreshSources}
                onChange={onFilterDraftChange}
                onApply={onApplyFilters}
                hasPendingChanges={hasPendingFilterChanges}
                onReset={onResetFilters}
                onRefresh={onRefresh}
            />

            <StatCards data={overview} />
            <SuggestionPanel
                data={recommendation}
                loading={overviewLoading}
                error={errors.recommendation ?? null}
            />
            <MonthlyChart
                data={monthly}
                onSelectMonth={(month) => {
                    const nextFilters = { ...appliedFilters, months: [month] }
                    setPage(1)
                    setDraftFilters(nextFilters)
                    setAppliedFilters(nextFilters)
                }}
            />
            {frontendConfig.enableSensitivity ? <SensitivityTable rows={sensitivity} /> : null}
            <CohortTable rows={cohorts} />
            <DistributionPanel rows={distribution} />
            <ComparisonPanel data={comparison} />
            <AnomalyTable rows={anomalies} />
            <CaseTable
                rows={cases}
                total={caseTotal}
                page={page}
                pageSize={pageSize}
                localHasNoteOnly={localCaseHasNoteOnly}
                onLocalHasNoteOnlyChange={setLocalCaseHasNoteOnly}
                sortBy={caseSortBy}
                sortOrder={caseSortOrder}
                onSortByChange={(value) => {
                    setPage(1)
                    setCaseSortBy(value)
                }}
                onSortOrderChange={(value) => {
                    setPage(1)
                    setCaseSortOrder(value)
                }}
                onPageChange={(next) => setPage(Math.max(1, next))}
                onPageSizeChange={(size) => {
                    setPage(1)
                    setPageSize(size)
                }}
            />

            <footer className="open-source-footer">
                <span>{t('footer.version', { version: appVersionLabel })}</span>
                <a href={frontendConfig.githubRepoUrl} target="_blank" rel="noreferrer">
                    {t('footer.githubRepo')}
                </a>
                <a href={frontendConfig.maintainerUrl} target="_blank" rel="noreferrer">
                    {t('footer.maintainedBy', { name: frontendConfig.maintainerName })}
                </a>
                {frontendConfig.buyMeCoffeeUrl ? (
                    <a
                        className="coffee-link"
                        href={frontendConfig.buyMeCoffeeUrl}
                        target="_blank"
                        rel="noreferrer"
                    >
                        {t('footer.buyMeCoffee')}
                    </a>
                ) : null}
            </footer>
        </main>
    )
}
