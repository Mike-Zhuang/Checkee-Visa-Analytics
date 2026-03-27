import type { SensitivityItem } from '../types'

type Props = { rows: SensitivityItem[] }

export default function SensitivityTable({ rows }: Props) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>右删失敏感性分析</h3>
        <p>Conservative / Neutral / Aggressive 三口径区间</p>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Median (days)</th>
              <th>P90 (days)</th>
              <th>&gt;=90d Ratio</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.scenario}>
                <td>{r.scenario}</td>
                <td>{r.median_days.toFixed(2)}</td>
                <td>{r.p90_days.toFixed(2)}</td>
                <td>{(r.long_tail_90plus_ratio * 100).toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
