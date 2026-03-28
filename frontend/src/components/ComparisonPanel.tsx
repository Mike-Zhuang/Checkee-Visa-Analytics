import { useTranslation } from 'react-i18next'

import type { ComparisonData } from '../types'

type Props = {
    data: ComparisonData | null
}

function fmtDays(value: number | null | undefined): string {
    if (value == null || Number.isNaN(value)) return '-'
    return `${value.toFixed(2)}d`
}

function fmtPct(value: number | null | undefined): string {
    if (value == null || Number.isNaN(value)) return '-'
    return `${(value * 100).toFixed(2)}%`
}

function fmtDelta(value: number | null | undefined, digits = 2): string {
    if (value == null || Number.isNaN(value)) return '-'
    const prefix = value > 0 ? '+' : ''
    return `${prefix}${value.toFixed(digits)}`
}

export default function ComparisonPanel({ data }: Props) {
    const { t } = useTranslation()

    return (
        <section className="panel">
            <div className="panel-head">
                <h3>{t('comparison.title')}</h3>
                <p>{t('comparison.hint')}</p>
            </div>
            {!data?.latest || !data.baseline || !data.delta ? (
                <div className="empty-box">
                    <strong>{t('comparison.emptyTitle')}</strong>
                    <p>{t('comparison.empty')}</p>
                    <p>{t('comparison.emptyAction')}</p>
                </div>
            ) : (
                <>
                    <div className="comparison-meta">
                        <span>{t('comparison.latestMonth')}: {data.latest_month ?? '-'}</span>
                        <span>{t('comparison.baselineMonth')}: {data.baseline_month ?? '-'}</span>
                    </div>
                    <div className="comparison-grid">
                        <article className="comparison-card">
                            <h4>{t('comparison.median')}</h4>
                            <p>{fmtDays(data.latest.median_days)} / {fmtDays(data.baseline.median_days)}</p>
                            <small>{t('comparison.delta')}: {fmtDelta(data.delta.median_days, 2)}</small>
                        </article>
                        <article className="comparison-card">
                            <h4>{t('comparison.p90')}</h4>
                            <p>{fmtDays(data.latest.p90_days)} / {fmtDays(data.baseline.p90_days)}</p>
                            <small>{t('comparison.delta')}: {fmtDelta(data.delta.p90_days, 2)}</small>
                        </article>
                        <article className="comparison-card">
                            <h4>{t('comparison.pendingRatio')}</h4>
                            <p>{fmtPct(data.latest.pending_ratio)} / {fmtPct(data.baseline.pending_ratio)}</p>
                            <small>{t('comparison.delta')}: {fmtDelta(data.delta.pending_ratio * 100, 2)}%</small>
                        </article>
                    </div>
                </>
            )}
        </section>
    )
}
