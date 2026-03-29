import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
    deleteAdminMajorOverride,
    getAdminMajorClassifications,
    getAdminSession,
    getMetaState,
    getOptions,
    loginAdmin,
    logoutAdmin,
    refreshDataWithSession,
    saveAdminMajorOverrides,
    triggerAdminStaleRefresh
} from './api'
import { frontendConfig } from './config'
import type { MajorClassificationItem, MetaState, OptionsResponse, RefreshHistoryItem, RefreshPayload } from './types'

const EMPTY_OPTIONS: OptionsResponse = {
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
}

const ADMIN_STALE_REFRESH_THRESHOLD_SECONDS = 6 * 60 * 60

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

export default function AdminPage() {
    const { t, i18n } = useTranslation()
    const [adminPassword, setAdminPassword] = useState('')
    const [adminToken, setAdminToken] = useState<string>(() => {
        if (typeof window === 'undefined') {
            return ''
        }
        return window.sessionStorage.getItem('checkee-admin-token') ?? ''
    })
    const [sessionExpiresAt, setSessionExpiresAt] = useState<string | null>(null)
    const [authError, setAuthError] = useState<string | null>(null)
    const [isAuthenticating, setIsAuthenticating] = useState(false)
    const [refreshFromMonth, setRefreshFromMonth] = useState('')
    const [refreshSources, setRefreshSources] = useState<string[]>(['monthly_track'])
    const [lastAttemptPayload, setLastAttemptPayload] = useState<RefreshPayload | null>(null)
    const [metaState, setMetaState] = useState<MetaState | null>(null)
    const [options, setOptions] = useState<OptionsResponse>(EMPTY_OPTIONS)
    const [isLoading, setIsLoading] = useState(false)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [loadError, setLoadError] = useState<string | null>(null)
    const [feedback, setFeedback] = useState<{ kind: 'success' | 'error'; message: string } | null>(null)
    const [majorFeedback, setMajorFeedback] = useState<{ kind: 'success' | 'error'; message: string } | null>(null)
    const [majorSearch, setMajorSearch] = useState('')
    const [majorItems, setMajorItems] = useState<MajorClassificationItem[]>([])
    const [majorTotal, setMajorTotal] = useState(0)
    const [majorCategoryL1Options, setMajorCategoryL1Options] = useState<string[]>([])
    const [majorCategoryL2Options, setMajorCategoryL2Options] = useState<string[]>([])
    const [majorDrafts, setMajorDrafts] = useState<Record<string, { category_l1: string; category_l2: string }>>({})
    const [isLoadingMajors, setIsLoadingMajors] = useState(false)
    const [savingMajorKey, setSavingMajorKey] = useState<string | null>(null)
    const [glassTier, setGlassTier] = useState<GlassTier>(() => detectGlassTier())

    const clearAdminSession = useCallback(() => {
        setAdminToken('')
        setSessionExpiresAt(null)
        if (typeof window !== 'undefined') {
            window.sessionStorage.removeItem('checkee-admin-token')
        }
    }, [])

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

    const sourceName = (source: string): string => {
        if (source === 'monthly_track') return t('filter.sourceMonthlyLabel')
        if (source === 'latest_snapshot') return t('filter.sourceLatestLabel')
        return source
    }

    const statusLabel = (status: string): string => {
        if (status === 'success') return t('admin.logStatusSuccess')
        if (status === 'blocked') return t('admin.logStatusBlocked')
        if (status === 'denied') return t('admin.logStatusDenied')
        if (status === 'error') return t('admin.logStatusError')
        return status
    }

    const historyDetail = (item: RefreshHistoryItem): string | null => {
        const details = item.details
        if (!details) {
            return null
        }
        const retryAfter = details.retry_after_seconds
        if (typeof retryAfter === 'number') {
            return t('admin.logRetryAfter', { seconds: retryAfter })
        }
        const totalCases = details.total_cases
        if (typeof totalCases === 'number') {
            return t('admin.logTotalCases', { count: totalCases })
        }
        return null
    }

    const loadMetaAndOptions = useCallback(async () => {
        setIsLoading(true)
        setLoadError(null)

        const [optionsRes, stateRes] = await Promise.allSettled([
            getOptions(),
            getMetaState()
        ])

        if (optionsRes.status === 'fulfilled') {
            setOptions(optionsRes.value)
            setRefreshSources((prev) => {
                if (optionsRes.value.fetch_sources.length === 0) {
                    return prev
                }
                const kept = prev.filter((item) => optionsRes.value.fetch_sources.includes(item))
                if (kept.length > 0) {
                    return kept
                }
                if (optionsRes.value.fetch_sources.includes('monthly_track')) {
                    return ['monthly_track']
                }
                return [optionsRes.value.fetch_sources[0]]
            })
        } else {
            setLoadError(t('admin.loadFailed'))
        }

        if (stateRes.status === 'fulfilled') {
            setMetaState(stateRes.value)
        } else {
            setLoadError(t('admin.loadFailed'))
        }

        setIsLoading(false)
    }, [t])

    const loadMajorClassifications = useCallback(
        async (token: string, query = '') => {
            if (!token.trim()) {
                setMajorItems([])
                setMajorTotal(0)
                return
            }

            setIsLoadingMajors(true)
            try {
                const payload = await getAdminMajorClassifications(token, query, 600)
                setMajorItems(payload.items)
                setMajorTotal(payload.total)
                setMajorCategoryL1Options(payload.category_l1_options)
                setMajorCategoryL2Options(payload.category_l2_options)
            } catch (error) {
                const message = error instanceof Error ? error.message : t('admin.majorLoadFailed')
                if (message.includes('401') || message.includes('403')) {
                    clearAdminSession()
                    setAuthError(t('admin.sessionExpired'))
                    return
                }
                setMajorFeedback({ kind: 'error', message: `${t('admin.majorLoadFailed')}: ${message}` })
            } finally {
                setIsLoadingMajors(false)
            }
        },
        [clearAdminSession, t]
    )

    useEffect(() => {
        void loadMetaAndOptions()
    }, [loadMetaAndOptions])

    useEffect(() => {
        if (!adminToken.trim()) {
            setMajorItems([])
            setMajorTotal(0)
            setMajorDrafts({})
            setMajorFeedback(null)
            return
        }
        void loadMajorClassifications(adminToken)
    }, [adminToken, loadMajorClassifications])

    const cooldownHint = useMemo(() => {
        const seconds = metaState?.refresh_available_in_seconds ?? 0
        if (seconds <= 0) {
            return t('admin.refreshReady')
        }
        const minutes = Math.ceil(seconds / 60)
        return t('admin.refreshCooldown', { seconds, minutes })
    }, [metaState, t])

    const toggleSource = (source: string) => {
        if (refreshSources.includes(source)) {
            setRefreshSources(refreshSources.filter((item) => item !== source))
            return
        }
        setRefreshSources([...refreshSources, source])
    }

    const buildCurrentPayload = (): RefreshPayload => ({
        all_months: false,
        months: frontendConfig.defaultRefreshMonths,
        from_month: refreshFromMonth || null,
        sources: refreshSources
    })

    const onAdminRefresh = async (overridePayload?: RefreshPayload) => {
        if (!adminToken.trim()) {
            setFeedback({ kind: 'error', message: t('admin.loginRequired') })
            return
        }

        const payload = overridePayload ?? buildCurrentPayload()
        if (!payload.sources || payload.sources.length === 0) {
            setFeedback({ kind: 'error', message: t('admin.sourceRequired') })
            return
        }

        setLastAttemptPayload(payload)
        setIsRefreshing(true)
        setFeedback(null)
        try {
            await refreshDataWithSession(payload, adminToken)
            await loadMetaAndOptions()
            setFeedback({ kind: 'success', message: t('admin.refreshSuccess') })
        } catch (error) {
            const message = error instanceof Error ? error.message : t('admin.refreshFailed')
            if (message.includes('401') || message.includes('403')) {
                clearAdminSession()
                setAuthError(t('admin.sessionExpired'))
            }
            setFeedback({ kind: 'error', message: `${t('admin.refreshFailed')}: ${message}` })
        } finally {
            setIsRefreshing(false)
        }
    }

    const runAdminStaleRefreshFallback = useCallback(async (token: string) => {
        const latestMeta = await getMetaState()
        setMetaState(latestMeta)

        const freshnessSeconds = latestMeta.data_freshness_seconds
        const isFreshEnough = typeof freshnessSeconds === 'number'
            && freshnessSeconds < ADMIN_STALE_REFRESH_THRESHOLD_SECONDS

        if (isFreshEnough) {
            setFeedback({ kind: 'success', message: t('admin.autoRefreshSkipFresh') })
            return
        }

        const fallbackResult = await triggerAdminStaleRefresh(token)

        if (fallbackResult.reason === 'stale_triggered') {
            await loadMetaAndOptions()
            setFeedback({
                kind: 'success',
                message: t('admin.autoRefreshTriggered', { value: fallbackResult.updated_at ?? t('common.na') })
            })
            return
        }

        if (fallbackResult.reason === 'fresh_enough') {
            setFeedback({ kind: 'success', message: t('admin.autoRefreshSkipFresh') })
            return
        }

        if (fallbackResult.reason === 'cooldown') {
            setFeedback({ kind: 'error', message: t('admin.autoRefreshSkipCooldown') })
            return
        }

        const detail = fallbackResult.message ? `: ${fallbackResult.message}` : ''
        setFeedback({ kind: 'error', message: `${t('admin.autoRefreshFailed')}${detail}` })
    }, [loadMetaAndOptions, t])

    const onLogin = async () => {
        if (!adminPassword.trim()) {
            setAuthError(t('admin.passwordRequired'))
            return
        }

        setIsAuthenticating(true)
        setAuthError(null)
        try {
            const loginResult = await loginAdmin(adminPassword.trim())
            setAdminToken(loginResult.token)
            setSessionExpiresAt(loginResult.expires_at)
            setAdminPassword('')
            if (typeof window !== 'undefined') {
                window.sessionStorage.setItem('checkee-admin-token', loginResult.token)
            }
        } catch (error) {
            const message = error instanceof Error ? error.message : t('admin.loginFailed')
            setAuthError(`${t('admin.loginFailed')}: ${message}`)
        } finally {
            setIsAuthenticating(false)
        }
    }

    const onLogout = async () => {
        const token = adminToken
        clearAdminSession()
        setAuthError(null)
        setFeedback(null)
        try {
            if (token) {
                await logoutAdmin(token)
            }
        } catch {
            // 用户本地状态已经清理，后端登出失败不阻断界面退出
        }
    }

    const sourceTag = (source: string): string => {
        if (source === 'manual') return t('admin.majorSource.manual')
        if (source === 'auto') return t('admin.majorSource.auto')
        if (source === 'not_applicable') return t('admin.majorSource.notApplicable')
        return t('admin.majorSource.unknown')
    }

    const rowDraft = (row: MajorClassificationItem): { category_l1: string; category_l2: string } => {
        const draft = majorDrafts[row.major_normalized]
        if (draft) {
            return draft
        }
        return {
            category_l1: row.effective_category_l1,
            category_l2: row.effective_category_l2
        }
    }

    const resolveMajorL2Options = useCallback(
        (categoryL1: string): string[] => {
            const fallback = majorCategoryL2Options.length > 0 ? majorCategoryL2Options : options.major_categories_l2
            const mapped = options.major_category_mapping[categoryL1] ?? []
            if (mapped.length === 0) {
                return fallback
            }

            const fallbackSet = new Set(fallback)
            const ordered = mapped.filter((item) => fallbackSet.has(item))
            if (ordered.length > 0) {
                return ordered
            }

            return fallback
        },
        [majorCategoryL2Options, options.major_categories_l2, options.major_category_mapping]
    )

    const updateMajorDraft = (row: MajorClassificationItem, next: { category_l1?: string; category_l2?: string }) => {
        const current = rowDraft(row)
        const nextCategoryL1 = next.category_l1 ?? current.category_l1
        const allowedCategoryL2 = resolveMajorL2Options(nextCategoryL1)
        let nextCategoryL2 = next.category_l2 ?? current.category_l2
        if (!allowedCategoryL2.includes(nextCategoryL2)) {
            nextCategoryL2 = allowedCategoryL2[0] ?? current.category_l2
        }

        setMajorDrafts((prev) => ({
            ...prev,
            [row.major_normalized]: {
                category_l1: nextCategoryL1,
                category_l2: nextCategoryL2
            }
        }))
    }

    const resetMajorDraft = (row: MajorClassificationItem) => {
        setMajorDrafts((prev) => {
            const next = { ...prev }
            delete next[row.major_normalized]
            return next
        })
    }

    const saveMajorRow = async (row: MajorClassificationItem) => {
        if (!adminToken.trim()) {
            setMajorFeedback({ kind: 'error', message: t('admin.loginRequired') })
            return
        }
        if (row.source === 'not_applicable') {
            setMajorFeedback({ kind: 'error', message: t('admin.majorNotApplicableReadonly') })
            return
        }

        const draft = rowDraft(row)
        setSavingMajorKey(row.major_normalized)
        setMajorFeedback(null)

        try {
            await saveAdminMajorOverrides(adminToken, [
                {
                    major: row.major,
                    category_l1: draft.category_l1,
                    category_l2: draft.category_l2
                }
            ])
            await loadMetaAndOptions()
            await loadMajorClassifications(adminToken, majorSearch)
            setMajorFeedback({ kind: 'success', message: t('admin.majorSaveSuccess', { major: row.major }) })
        } catch (error) {
            const message = error instanceof Error ? error.message : t('admin.majorSaveFailed')
            if (message.includes('401') || message.includes('403')) {
                clearAdminSession()
                setAuthError(t('admin.sessionExpired'))
                return
            }
            setMajorFeedback({ kind: 'error', message: `${t('admin.majorSaveFailed')}: ${message}` })
        } finally {
            setSavingMajorKey(null)
        }
    }

    const removeMajorOverride = async (row: MajorClassificationItem) => {
        if (!adminToken.trim()) {
            setMajorFeedback({ kind: 'error', message: t('admin.loginRequired') })
            return
        }
        if (row.source === 'not_applicable') {
            setMajorFeedback({ kind: 'error', message: t('admin.majorNotApplicableReadonly') })
            return
        }

        setSavingMajorKey(row.major_normalized)
        setMajorFeedback(null)
        try {
            await deleteAdminMajorOverride(adminToken, row.major)
            await loadMetaAndOptions()
            await loadMajorClassifications(adminToken, majorSearch)
            setMajorFeedback({ kind: 'success', message: t('admin.majorDeleteSuccess', { major: row.major }) })
        } catch (error) {
            const message = error instanceof Error ? error.message : t('admin.majorDeleteFailed')
            if (message.includes('401') || message.includes('403')) {
                clearAdminSession()
                setAuthError(t('admin.sessionExpired'))
                return
            }
            setMajorFeedback({ kind: 'error', message: `${t('admin.majorDeleteFailed')}: ${message}` })
        } finally {
            setSavingMajorKey(null)
        }
    }

    useEffect(() => {
        if (!adminToken.trim()) {
            return
        }

        let cancelled = false

        const verifySession = async () => {
            try {
                const session = await getAdminSession(adminToken)
                if (cancelled) {
                    return
                }
                setSessionExpiresAt(session.expires_at)
                setAuthError(null)

                try {
                    await runAdminStaleRefreshFallback(adminToken)
                } catch (error) {
                    if (cancelled) {
                        return
                    }
                    const message = error instanceof Error ? error.message : t('admin.autoRefreshFailed')
                    if (message.includes('401') || message.includes('403')) {
                        clearAdminSession()
                        setAuthError(t('admin.sessionExpired'))
                        return
                    }
                    setFeedback({ kind: 'error', message: `${t('admin.autoRefreshFailed')}: ${message}` })
                }
            } catch {
                if (cancelled) {
                    return
                }
                clearAdminSession()
                setAuthError(t('admin.sessionExpired'))
            }
        }

        void verifySession()

        return () => {
            cancelled = true
        }
    }, [adminToken, clearAdminSession, runAdminStaleRefreshFallback, t])

    const languageValue = i18n.resolvedLanguage?.startsWith('en') ? 'en' : 'zh'
    const history = metaState?.refresh_history ?? []
    const showLoginGate = !adminToken.trim()
    const majorGroups = useMemo(() => {
        const grouped: {
            unknown: MajorClassificationItem[]
            manual: MajorClassificationItem[]
            auto: MajorClassificationItem[]
            not_applicable: MajorClassificationItem[]
        } = {
            unknown: [],
            manual: [],
            auto: [],
            not_applicable: []
        }

        for (const item of majorItems) {
            if (item.source === 'manual') {
                grouped.manual.push(item)
                continue
            }
            if (item.source === 'auto') {
                grouped.auto.push(item)
                continue
            }
            if (item.source === 'not_applicable') {
                grouped.not_applicable.push(item)
                continue
            }
            grouped.unknown.push(item)
        }
        return grouped
    }, [majorItems])

    const majorGroupSections = useMemo(
        () => [
            {
                key: 'unknown' as const,
                label: t('admin.majorGroupUnknownTitle'),
                hint: t('admin.majorGroupUnknownHint'),
                items: majorGroups.unknown
            },
            {
                key: 'manual' as const,
                label: t('admin.majorGroupManualTitle'),
                hint: t('admin.majorGroupManualHint'),
                items: majorGroups.manual
            },
            {
                key: 'auto' as const,
                label: t('admin.majorGroupAutoTitle'),
                hint: t('admin.majorGroupAutoHint'),
                items: majorGroups.auto
            },
            {
                key: 'not_applicable' as const,
                label: t('admin.majorGroupNotApplicableTitle'),
                hint: t('admin.majorGroupNotApplicableHint'),
                items: majorGroups.not_applicable
            }
        ].filter((group) => group.items.length > 0),
        [majorGroups.auto, majorGroups.manual, majorGroups.not_applicable, majorGroups.unknown, t]
    )

    const sessionExpiresAtDisplay = useMemo(() => {
        if (!sessionExpiresAt) {
            return null
        }

        const date = new Date(sessionExpiresAt)
        if (Number.isNaN(date.getTime())) {
            return sessionExpiresAt
        }

        const locale = languageValue === 'en' ? 'en-US' : 'zh-CN'
        return new Intl.DateTimeFormat(locale, {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
            timeZoneName: 'short'
        }).format(date)
    }, [languageValue, sessionExpiresAt])

    return (
        <main className={`app-shell glass-tier-${glassTier} admin-shell`}>
            <header className="hero">
                <div>
                    <h1>{t('admin.title')}</h1>
                    <p>{t('admin.subtitle')}</p>
                </div>
                <div className="hero-actions">
                    <label className="lang-switch" htmlFor="admin-lang-select">
                        <span>{t('app.language')}</span>
                        <select
                            id="admin-lang-select"
                            className="select-modern"
                            aria-label={t('app.language')}
                            value={languageValue}
                            onChange={(e) => void i18n.changeLanguage(e.currentTarget.value)}
                        >
                            <option value="zh">中文</option>
                            <option value="en">English</option>
                        </select>
                    </label>
                    <a href="/">{t('admin.backToDashboard')}</a>
                </div>
            </header>

            {showLoginGate ? (
                <section className="panel admin-panel" role="region" aria-labelledby="admin-login-title">
                    <div className="panel-head">
                        <h3 id="admin-login-title">{t('admin.loginTitle')}</h3>
                        <p>{t('admin.loginHint')}</p>
                    </div>
                    <div className="admin-grid">
                        <label className="field field-inline" htmlFor="admin-password">
                            <span>{t('admin.passwordLabel')}</span>
                            <input
                                id="admin-password"
                                type="password"
                                value={adminPassword}
                                autoComplete="off"
                                placeholder={t('admin.passwordPlaceholder')}
                                onChange={(e) => setAdminPassword(e.currentTarget.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        void onLogin()
                                    }
                                }}
                            />
                            <small className="field-help">{t('admin.passwordHelp')}</small>
                        </label>
                    </div>

                    {authError ? <div className="refresh-feedback error">{authError}</div> : null}

                    <div className="actions">
                        <button type="button" disabled={isAuthenticating} onClick={() => void onLogin()}>
                            {isAuthenticating ? t('admin.logining') : t('admin.loginNow')}
                        </button>
                    </div>
                </section>
            ) : null}

            <section className="panel admin-panel" role="region" aria-labelledby="admin-refresh-title">
                <div className="panel-head">
                    <h3 id="admin-refresh-title">{t('admin.refreshControlTitle')}</h3>
                    <p>{cooldownHint}</p>
                </div>

                {loadError ? <div className="error-box">{loadError}</div> : null}

                <div className="admin-grid">
                    <label className="field field-inline" htmlFor="admin-refresh-from-month">
                        <span>{t('filter.refreshFromMonth')}</span>
                        <input
                            id="admin-refresh-from-month"
                            type="month"
                            value={refreshFromMonth}
                            disabled={showLoginGate || isRefreshing}
                            onChange={(e) => setRefreshFromMonth(e.currentTarget.value)}
                        />
                        <small className="field-help">
                            {t('filter.refreshFromMonthHelp', { months: frontendConfig.defaultRefreshMonths })}
                        </small>
                    </label>
                </div>

                {!showLoginGate ? (
                    <div className="admin-auth-state">
                        <span className="admin-auth-badge">{t('admin.loggedIn')}</span>
                        {sessionExpiresAtDisplay ? <span>{t('admin.sessionValidUntil', { value: sessionExpiresAtDisplay })}</span> : null}
                    </div>
                ) : null}

                {authError && !showLoginGate ? <div className="refresh-feedback error">{authError}</div> : null}

                <fieldset className="refresh-sources-panel admin-sources">
                    <span>{t('filter.refreshSources')}</span>
                    <small className="field-help">{t('filter.refreshSourcesHelp')}</small>
                    <div className="source-options">
                        {options.fetch_sources.map((source) => (
                            <label className="source-option" key={source}>
                                <input
                                    type="checkbox"
                                    checked={refreshSources.includes(source)}
                                    disabled={showLoginGate || isRefreshing}
                                    onChange={() => toggleSource(source)}
                                />
                                <span className="source-title">{sourceName(source)}</span>
                            </label>
                        ))}
                    </div>
                </fieldset>

                <div className="actions">
                    <button type="button" disabled={isLoading || isRefreshing || showLoginGate} onClick={() => void onAdminRefresh()}>
                        {isRefreshing ? t('filter.refreshing') : t('admin.refreshNow')}
                    </button>
                    <button
                        type="button"
                        className="ghost"
                        disabled={isLoading || isRefreshing || showLoginGate || !lastAttemptPayload}
                        onClick={() => void onAdminRefresh(lastAttemptPayload ?? undefined)}
                    >
                        {t('admin.retryLast')}
                    </button>
                    <button type="button" className="ghost" disabled={showLoginGate} onClick={() => void onLogout()}>
                        {t('admin.logout')}
                    </button>
                    <button type="button" className="ghost" disabled={isLoading || isRefreshing} onClick={() => void loadMetaAndOptions()}>
                        {t('admin.reloadState')}
                    </button>
                </div>

                {feedback ? (
                    <div className={`refresh-feedback ${feedback.kind}`} role="status" aria-live="polite">
                        {feedback.message}
                    </div>
                ) : null}

                <div className="meta-more-grid admin-meta-grid">
                    <span>{t('admin.lastUpdated', { value: metaState?.updated_at ?? t('common.na') })}</span>
                    <span>{t('admin.caseCount', { count: metaState?.current_case_count ?? 0 })}</span>
                    <span>{t('admin.currentSources', {
                        value: metaState?.selected_sources?.length
                            ? metaState.selected_sources.map(sourceName).join(' / ')
                            : t('common.na')
                    })}</span>
                    <span>{t('admin.refreshInterval', { seconds: metaState?.refresh_min_interval_seconds ?? 0 })}</span>
                </div>

                <div className="admin-history">
                    <h4>{t('admin.historyTitle')}</h4>
                    {history.length === 0 ? (
                        <p className="hint">{t('admin.historyEmpty')}</p>
                    ) : (
                        <ul className="admin-history-list">
                            {history.slice(0, 8).map((item, index) => (
                                <li key={`${item.occurred_at}-${index}`}>
                                    <div className="admin-history-head">
                                        <span className={`admin-status status-${item.status}`}>{statusLabel(item.status)}</span>
                                        <strong>{item.message}</strong>
                                    </div>
                                    <div className="admin-history-meta">
                                        <span>{t('admin.logOccurredAt', { value: item.occurred_at })}</span>
                                        <span>{t('admin.logTriggeredBy', { value: item.triggered_by })}</span>
                                        {historyDetail(item) ? <span>{historyDetail(item)}</span> : null}
                                    </div>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </section>

            <section className="panel admin-panel major-admin-panel" role="region" aria-labelledby="admin-major-title">
                <div className="panel-head">
                    <h3 id="admin-major-title">{t('admin.majorPanelTitle')}</h3>
                    <p>{t('admin.majorPanelHint', { total: majorTotal })}</p>
                </div>

                {showLoginGate ? (
                    <p className="hint">{t('admin.loginRequired')}</p>
                ) : (
                    <>
                        <div className="admin-major-toolbar">
                            <label className="field" htmlFor="admin-major-search">
                                <span>{t('admin.majorSearchLabel')}</span>
                                <input
                                    id="admin-major-search"
                                    type="text"
                                    value={majorSearch}
                                    placeholder={t('admin.majorSearchPlaceholder')}
                                    onChange={(e) => setMajorSearch(e.currentTarget.value)}
                                />
                            </label>
                            <div className="actions compact">
                                <button
                                    type="button"
                                    className="ghost"
                                    disabled={isLoadingMajors || isRefreshing}
                                    onClick={() => void loadMajorClassifications(adminToken, majorSearch)}
                                >
                                    {t('admin.majorSearchAction')}
                                </button>
                            </div>
                        </div>

                        {majorFeedback ? <div className={`refresh-feedback ${majorFeedback.kind}`}>{majorFeedback.message}</div> : null}

                        <div className="table-wrap admin-major-table-wrap">
                            <table>
                                <thead>
                                    <tr>
                                        <th scope="col">{t('admin.majorColumnMajor')}</th>
                                        <th scope="col">{t('admin.majorColumnCount')}</th>
                                        <th scope="col">{t('admin.majorColumnAuto')}</th>
                                        <th scope="col">{t('admin.majorColumnManual')}</th>
                                        <th scope="col">{t('admin.majorColumnSource')}</th>
                                        <th scope="col">{t('admin.majorColumnActions')}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {majorItems.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} className="admin-major-empty">{t('admin.majorEmpty')}</td>
                                        </tr>
                                    ) : (
                                        majorGroupSections.flatMap((group) => {
                                            const rows = [
                                                <tr key={`group-${group.key}`} className={`admin-major-group-row group-${group.key}`}>
                                                    <td colSpan={6}>
                                                        <div className="admin-major-group-head">
                                                            <strong>{group.label}</strong>
                                                            <span>{t('admin.majorGroupCount', { count: group.items.length })}</span>
                                                            <small>{group.hint}</small>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ]

                                            for (const row of group.items) {
                                                const draft = rowDraft(row)
                                                const isSaving = savingMajorKey === row.major_normalized
                                                const isReadonlyRow = row.source === 'not_applicable'
                                                const isDirty =
                                                    draft.category_l1 !== row.effective_category_l1
                                                    || draft.category_l2 !== row.effective_category_l2
                                                const rowCategoryL2Options = resolveMajorL2Options(draft.category_l1)

                                                rows.push(
                                                    <tr key={row.major_normalized} className={isReadonlyRow ? 'admin-major-row-readonly' : ''}>
                                                        <td>
                                                            <div className="admin-major-name">
                                                                <strong>{row.major}</strong>
                                                                <small>{row.major_normalized}</small>
                                                            </div>
                                                        </td>
                                                        <td>{row.count}</td>
                                                        <td>
                                                            {row.auto_category_l1} / {row.auto_category_l2}
                                                        </td>
                                                        <td>
                                                            <div className="admin-major-selects">
                                                                <select
                                                                    className="select-modern"
                                                                    value={draft.category_l1}
                                                                    disabled={isSaving || isReadonlyRow}
                                                                    onChange={(e) => updateMajorDraft(row, { category_l1: e.currentTarget.value })}
                                                                >
                                                                    {(majorCategoryL1Options.length > 0 ? majorCategoryL1Options : options.major_categories_l1).map((value) => (
                                                                        <option key={`l1-${value}`} value={value}>{value}</option>
                                                                    ))}
                                                                </select>
                                                                <select
                                                                    className="select-modern"
                                                                    value={draft.category_l2}
                                                                    disabled={isSaving || isReadonlyRow}
                                                                    onChange={(e) => updateMajorDraft(row, { category_l2: e.currentTarget.value })}
                                                                >
                                                                    {rowCategoryL2Options.map((value) => (
                                                                        <option key={`l2-${value}`} value={value}>{value}</option>
                                                                    ))}
                                                                </select>
                                                            </div>
                                                        </td>
                                                        <td>
                                                            <span className={`admin-status status-${row.source}`}>{sourceTag(row.source)}</span>
                                                        </td>
                                                        <td>
                                                            <div className="admin-major-actions">
                                                                <button
                                                                    type="button"
                                                                    className="ghost mini"
                                                                    disabled={isReadonlyRow || !isDirty || isSaving}
                                                                    onClick={() => void saveMajorRow(row)}
                                                                >
                                                                    {t('admin.majorSaveAction')}
                                                                </button>
                                                                <button
                                                                    type="button"
                                                                    className="ghost mini"
                                                                    disabled={isReadonlyRow || isSaving}
                                                                    onClick={() => resetMajorDraft(row)}
                                                                >
                                                                    {t('admin.majorResetAction')}
                                                                </button>
                                                                <button
                                                                    type="button"
                                                                    className="ghost mini"
                                                                    disabled={isReadonlyRow || isSaving || !row.has_manual_override}
                                                                    onClick={() => void removeMajorOverride(row)}
                                                                >
                                                                    {t('admin.majorDeleteAction')}
                                                                </button>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                )
                                            }

                                            return rows
                                        })
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </>
                )}
            </section>
        </main>
    )
}
