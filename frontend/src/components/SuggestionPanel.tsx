import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { RecommendationResponse } from '../types'

type SuggestionPanelProps = {
    data: RecommendationResponse | null
    loading: boolean
    error: string | null
}

function asPercent(value: number): string {
    const normalized = Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : 0
    return `${Math.round(normalized * 100)}%`
}

function formatEvidence(metric: string, value: number): string {
    if (metric.endsWith('_ratio') || metric.includes('probability') || metric === 'pending_ratio') {
        return asPercent(value)
    }

    if (metric === 'p90_days') {
        return `${Math.round(value)}d`
    }

    if (metric === 'data_freshness_seconds') {
        if (value <= 0) {
            return '0m'
        }
        return `${Math.max(1, Math.round(value / 60))}m`
    }

    return `${Math.round(value)}`
}

export default function SuggestionPanel({ data, loading, error }: SuggestionPanelProps) {
    const { t } = useTranslation()
    const [expandedItemId, setExpandedItemId] = useState<string | null>(null)

    const toggleEvidence = (itemId: string) => {
        setExpandedItemId((current) => (current === itemId ? null : itemId))
    }

    return (
        <section className="panel suggestion-panel" aria-label={t('suggestion.title')}>
            <div className="suggestion-head">
                <h3>{t('suggestion.title')}</h3>
                <p className="hint">{t('suggestion.hint')}</p>
            </div>

            {loading && !data ? <p className="empty-copy">{t('suggestion.loading')}</p> : null}
            {error && !data ? <p className="error-inline">{error}</p> : null}

            {!loading && !error && !data ? <p className="empty-copy">{t('suggestion.empty')}</p> : null}

            {data ? (
                <>
                    <div className="suggestion-summary">
                        <span>
                            {t('suggestion.confidenceBand')}: {t(`suggestion.level.${data.summary.confidence_band}`)}
                        </span>
                        <span>
                            {t('suggestion.sampleSize')}: {data.summary.sample_size}
                        </span>
                        <span>
                            {t('suggestion.maturity')}: {asPercent(data.summary.maturity_ratio)}
                        </span>
                    </div>

                    {data.summary.insufficient_data ? (
                        <p className="empty-copy">{t('suggestion.insufficient')}</p>
                    ) : null}

                    {data.items.length === 0 ? (
                        <p className="empty-copy">{t('suggestion.empty')}</p>
                    ) : (
                        <div className="suggestion-list">
                            {data.items.map((item) => {
                                const expanded = expandedItemId === item.id
                                return (
                                    <article key={item.id} className="suggestion-item">
                                        <header className="suggestion-item-head">
                                            <div>
                                                <h4>{t(`suggestion.items.${item.id}.title`, { defaultValue: item.id })}</h4>
                                                <p>
                                                    {t('suggestion.probability')}: {asPercent(item.estimate)} ({t('suggestion.interval')}{' '}
                                                    {asPercent(item.probability_interval_low)} - {asPercent(item.probability_interval_high)})
                                                </p>
                                            </div>
                                            <div className={`suggestion-level level-${item.level}`}>
                                                {t(`suggestion.level.${item.level}`)}
                                            </div>
                                        </header>

                                        <div className="suggestion-reasons">
                                            {item.reasons.map((reason) => (
                                                <span key={reason} className="chip">
                                                    {t(`suggestion.metrics.${reason}`, { defaultValue: reason })}
                                                </span>
                                            ))}
                                        </div>

                                        <div className="suggestion-actions">
                                            <span className="hint">
                                                {t(`suggestion.direction.${item.direction}`)}
                                            </span>
                                            <button
                                                type="button"
                                                className="ghost"
                                                onClick={() => toggleEvidence(item.id)}
                                            >
                                                {expanded ? t('suggestion.hideEvidence') : t('suggestion.showEvidence')}
                                            </button>
                                        </div>

                                        {expanded ? (
                                            <ul className="suggestion-evidence-list">
                                                {item.evidence.map((evidence) => (
                                                    <li key={`${item.id}-${evidence.metric}`}>
                                                        <strong>{t(`suggestion.metrics.${evidence.metric}`, { defaultValue: evidence.metric })}</strong>
                                                        <span>{formatEvidence(evidence.metric, evidence.value)}</span>
                                                        {evidence.note ? <em>{evidence.note}</em> : null}
                                                    </li>
                                                ))}
                                            </ul>
                                        ) : null}
                                    </article>
                                )
                            })}
                        </div>
                    )}
                </>
            ) : null}
        </section>
    )
}
