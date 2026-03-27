import type { OverviewStats } from '../types'

type Props = { data: OverviewStats | null }

function fmtPct(v: number | undefined): string {
  if (v === undefined || Number.isNaN(v)) return '-'
  return `${(v * 100).toFixed(2)}%`
}

export default function StatCards({ data }: Props) {
  if (!data) return null
  return (
    <section className="stats-grid">
      <article className="stat-card"><h4>总样本</h4><p>{data.total_cases}</p></article>
      <article className="stat-card"><h4>结案样本</h4><p>{data.finalized_cases}</p></article>
      <article className="stat-card"><h4>Pending</h4><p>{data.pending_cases}</p></article>
      <article className="stat-card"><h4>样本成熟度</h4><p>{fmtPct(data.maturity_ratio)}</p></article>
      <article className="stat-card"><h4>中位数</h4><p>{data.median_days.toFixed(2)} 天</p><small>95%CI {data.median_ci_low}-{data.median_ci_high}</small></article>
      <article className="stat-card"><h4>P90</h4><p>{data.p90_days.toFixed(2)} 天</p><small>95%CI {data.p90_ci_low}-{data.p90_ci_high}</small></article>
    </section>
  )
}
