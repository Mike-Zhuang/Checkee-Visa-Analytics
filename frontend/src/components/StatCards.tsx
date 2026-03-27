import type { OverviewStats } from '../types'
import { useTranslation } from 'react-i18next'

type Props = { data: OverviewStats | null }

function fmtPct(v: number | undefined): string {
    if (v === undefined || Number.isNaN(v)) return '-'
    return `${(v * 100).toFixed(2)}%`
}

export default function StatCards({ data }: Props) {
    const { t } = useTranslation()
    if (!data) return null
    return (
        <section className="stats-grid">
            <article className="stat-card"><h4>{t('stats.total')}</h4><p>{data.total_cases}</p></article>
            <article className="stat-card"><h4>{t('stats.finalized')}</h4><p>{data.finalized_cases}</p></article>
            <article className="stat-card"><h4>{t('stats.pending')}</h4><p>{data.pending_cases}</p></article>
            <article className="stat-card"><h4>{t('stats.maturity')}</h4><p>{fmtPct(data.maturity_ratio)}</p></article>
            <article className="stat-card"><h4>{t('stats.median')}</h4><p>{data.median_days.toFixed(2)} {t('stats.days')}</p><small>{t('stats.ci95')} {data.median_ci_low}-{data.median_ci_high}</small></article>
            <article className="stat-card"><h4>{t('stats.p90')}</h4><p>{data.p90_days.toFixed(2)} {t('stats.days')}</p><small>{t('stats.ci95')} {data.p90_ci_low}-{data.p90_ci_high}</small></article>
        </section>
    )
}
