import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
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
    getSensitivity,
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
import type {
    AnomalyItem,
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
    RefreshPayload,
    SensitivityItem
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
    search_text: ''
}

type ErrorKey =
    | 'overview'
    | 'monthly'
    | 'sensitivity'
    | 'cohorts'
    | 'distribution'
    | 'comparison'
    | 'anomalies'
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
    const [overviewLoading, setOverviewLoading] = useState(false)
    const [casesLoading, setCasesLoading] = useState(false)
    const [errors, setErrors] = useState<Partial<Record<ErrorKey, string>>>({})
    const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
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
    const [cases, setCases] = useState<CaseItem[]>([])
    const [caseTotal, setCaseTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(frontendConfig.defaultPageSize)
    const [glassTier, setGlassTier] = useState<GlassTier>(() => detectGlassTier())

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

    const fetchOverviewBundle = async (activeFilters: Filters) => {
        setOverviewLoading(true)
        clearErrors(['overview', 'monthly', 'sensitivity', 'cohorts', 'distribution', 'comparison', 'anomalies', 'metaState'])

        const [
            overviewRes,
            monthlyRes,
            sensitivityRes,
            cohortsRes,
            distributionRes,
            comparisonRes,
            anomaliesRes,
            stateRes
        ] = await Promise.allSettled([
            getOverview(activeFilters),
            getMonthly(activeFilters),
            getSensitivity(activeFilters),
            getCohorts(activeFilters),
            getDistribution(activeFilters),
            getComparison(activeFilters),
            getAnomalies(activeFilters),
            getMetaState()
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

        if (stateRes.status === 'fulfilled') {
            setMetaState(stateRes.value)
        } else {
            setError('metaState', t('errors.metaState', { message: formatReason(stateRes.reason) }))
        }

        setOverviewLoading(false)
    }

    const fetchCasesPage = async (activeFilters: Filters, nextPage: number, nextPageSize: number) => {
        setCasesLoading(true)
        try {
            const offset = (nextPage - 1) * nextPageSize
            const ca = await getCases(activeFilters, nextPageSize, offset)
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

        clearErrors(['options', 'groups'])
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
        }
    }

    const init = async () => {
        setErrors({})
        await fetchMetaOptions()
        await fetchOverviewBundle(filters)
        await fetchCasesPage(filters, 1, pageSize)
        setInitialized(true)
    }

    useEffect(() => {
        void init()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    useEffect(() => {
        if (!initialized) return
        setPage(1)
        void fetchOverviewBundle(filters)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filters])

    useEffect(() => {
        if (!initialized) return
        void fetchCasesPage(filters, page, pageSize)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filters, page, pageSize, initialized])

    const onRefresh = async (payload: RefreshPayload) => {
        setIsRefreshing(true)
        setRefreshFeedback(null)
        try {
            await refreshData(payload)
            await fetchMetaOptions()
            setPage(1)
            await fetchOverviewBundle(filters)
            await fetchCasesPage(filters, 1, pageSize)
            clearErrors(['refresh'])
            setRefreshFeedback({ kind: 'success', message: t('filter.refreshSuccess') })
        } catch (e) {
            setError('refresh', t('errors.refresh', { message: formatReason(e) }))
            setRefreshFeedback({ kind: 'error', message: t('filter.refreshFailedHint') })
        } finally {
            setIsRefreshing(false)
        }
    }

    const onFilterChange = (next: Filters) => {
        setFilters(next)
    }

    const reportLink = useMemo(() => exportReportUrl(filters), [filters])
    const casesLink = useMemo(() => exportCasesUrl(filters), [filters])

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
                filters={filters}
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
                onChange={onFilterChange}
                onReset={() => setFilters(EMPTY_FILTERS)}
                onRefresh={onRefresh}
            />

            <StatCards data={overview} />
            <MonthlyChart
                data={monthly}
                onSelectMonth={(month) => {
                    setFilters((old) => ({ ...old, months: [month] }))
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
                onPageChange={(next) => setPage(Math.max(1, next))}
                onPageSizeChange={(size) => {
                    setPage(1)
                    setPageSize(size)
                }}
            />
        </main>
    )
}
