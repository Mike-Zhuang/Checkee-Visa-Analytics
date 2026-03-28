import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { getMetaState, getOptions, refreshDataAsAdmin } from './api'
import { frontendConfig } from './config'
import type { MetaState, OptionsResponse, RefreshHistoryItem, RefreshPayload } from './types'

const EMPTY_OPTIONS: OptionsResponse = {
    months: [],
    visa_types: [],
    consulates: [],
    statuses: [],
    entries: [],
    fetch_sources: []
}

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
    const [adminKey, setAdminKey] = useState('')
    const [accessCodeInput, setAccessCodeInput] = useState('')
    const [accessCodeError, setAccessCodeError] = useState<string | null>(null)
    const [refreshFromMonth, setRefreshFromMonth] = useState('')
    const [refreshSources, setRefreshSources] = useState<string[]>(['monthly_track'])
    const [lastAttemptPayload, setLastAttemptPayload] = useState<RefreshPayload | null>(null)
    const [metaState, setMetaState] = useState<MetaState | null>(null)
    const [options, setOptions] = useState<OptionsResponse>(EMPTY_OPTIONS)
    const [isLoading, setIsLoading] = useState(false)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [loadError, setLoadError] = useState<string | null>(null)
    const [feedback, setFeedback] = useState<{ kind: 'success' | 'error'; message: string } | null>(null)
    const [uiUnlocked, setUiUnlocked] = useState<boolean>(() => {
        if (!frontendConfig.adminRequireAccessCode) {
            return true
        }
        if (typeof window === 'undefined') {
            return false
        }
        return window.sessionStorage.getItem('checkee-admin-ui-unlocked') === '1'
    })
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

    const loadMetaAndOptions = async () => {
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
    }

    useEffect(() => {
        void loadMetaAndOptions()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

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
        if (!adminKey.trim()) {
            setFeedback({ kind: 'error', message: t('admin.keyRequired') })
            return
        }
        if (!uiUnlocked) {
            setFeedback({ kind: 'error', message: t('admin.accessCodeRequired') })
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
            await refreshDataAsAdmin(payload, adminKey)
            await loadMetaAndOptions()
            setFeedback({ kind: 'success', message: t('admin.refreshSuccess') })
        } catch (error) {
            const message = error instanceof Error ? error.message : t('admin.refreshFailed')
            setFeedback({ kind: 'error', message: `${t('admin.refreshFailed')}: ${message}` })
        } finally {
            setIsRefreshing(false)
        }
    }

    const unlockAdminUi = () => {
        if (!frontendConfig.adminRequireAccessCode) {
            setUiUnlocked(true)
            return
        }

        const requiredCode = frontendConfig.adminAccessCode.trim()
        if (!requiredCode) {
            setAccessCodeError(t('admin.accessCodeNotConfigured'))
            return
        }

        if (accessCodeInput !== requiredCode) {
            setAccessCodeError(t('admin.accessCodeInvalid'))
            return
        }

        setAccessCodeError(null)
        setUiUnlocked(true)
        if (typeof window !== 'undefined') {
            window.sessionStorage.setItem('checkee-admin-ui-unlocked', '1')
        }
    }

    const languageValue = i18n.resolvedLanguage?.startsWith('en') ? 'en' : 'zh'
    const history = metaState?.refresh_history ?? []

    const showAccessGate = frontendConfig.adminRequireAccessCode && !uiUnlocked

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

            {showAccessGate ? (
                <section className="panel admin-panel" role="region" aria-labelledby="admin-access-title">
                    <div className="panel-head">
                        <h3 id="admin-access-title">{t('admin.accessGateTitle')}</h3>
                        <p>{t('admin.accessGateHint')}</p>
                    </div>
                    <div className="admin-grid">
                        <label className="field field-inline" htmlFor="admin-access-code">
                            <span>{t('admin.accessCodeLabel')}</span>
                            <input
                                id="admin-access-code"
                                type="password"
                                value={accessCodeInput}
                                autoComplete="off"
                                placeholder={t('admin.accessCodePlaceholder')}
                                onChange={(e) => setAccessCodeInput(e.currentTarget.value)}
                            />
                            <small className="field-help">{t('admin.accessCodeHelp')}</small>
                        </label>
                    </div>

                    {accessCodeError ? <div className="refresh-feedback error">{accessCodeError}</div> : null}

                    <div className="actions">
                        <button type="button" onClick={unlockAdminUi}>{t('admin.unlock')}</button>
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
                    <label className="field field-inline" htmlFor="admin-key">
                        <span>{t('admin.keyLabel')}</span>
                        <input
                            id="admin-key"
                            type="password"
                            value={adminKey}
                            autoComplete="off"
                            placeholder={t('admin.keyPlaceholder')}
                            disabled={showAccessGate || isRefreshing}
                            onChange={(e) => setAdminKey(e.currentTarget.value)}
                        />
                        <small className="field-help">{t('admin.keyHelp')}</small>
                    </label>

                    <label className="field field-inline" htmlFor="admin-refresh-from-month">
                        <span>{t('filter.refreshFromMonth')}</span>
                        <input
                            id="admin-refresh-from-month"
                            type="month"
                            value={refreshFromMonth}
                            disabled={showAccessGate || isRefreshing}
                            onChange={(e) => setRefreshFromMonth(e.currentTarget.value)}
                        />
                        <small className="field-help">
                            {t('filter.refreshFromMonthHelp', { months: frontendConfig.defaultRefreshMonths })}
                        </small>
                    </label>
                </div>

                <fieldset className="refresh-sources-panel admin-sources">
                    <span>{t('filter.refreshSources')}</span>
                    <small className="field-help">{t('filter.refreshSourcesHelp')}</small>
                    <div className="source-options">
                        {options.fetch_sources.map((source) => (
                            <label className="source-option" key={source}>
                                <input
                                    type="checkbox"
                                    checked={refreshSources.includes(source)}
                                    disabled={showAccessGate || isRefreshing}
                                    onChange={() => toggleSource(source)}
                                />
                                <span className="source-title">{sourceName(source)}</span>
                            </label>
                        ))}
                    </div>
                </fieldset>

                <div className="actions">
                    <button type="button" disabled={isLoading || isRefreshing || showAccessGate} onClick={() => void onAdminRefresh()}>
                        {isRefreshing ? t('filter.refreshing') : t('admin.refreshNow')}
                    </button>
                    <button
                        type="button"
                        className="ghost"
                        disabled={isLoading || isRefreshing || showAccessGate || !lastAttemptPayload}
                        onClick={() => void onAdminRefresh(lastAttemptPayload ?? undefined)}
                    >
                        {t('admin.retryLast')}
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
        </main>
    )
}
