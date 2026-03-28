import { useTranslation } from 'react-i18next'

import type { CohortItem } from '../types'

type Props = {
    rows: CohortItem[]
}

function fmtNumber(value: number | null): string {
    if (value == null || Number.isNaN(value)) return '-'
    return value.toFixed(2)
}

function fmtPct(value: number | null): string {
    if (value == null || Number.isNaN(value)) return '-'
    return `${(value * 100).toFixed(2)}%`
}

export default function CohortTable({ rows }: Props) {
    const { t } = useTranslation()

    return (
        <section className="panel">
            <div className="panel-head">
                <h3>{t('cohort.title')}</h3>
                <p>{t('cohort.hint')}</p>
            </div>
            <div className="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>{t('cohort.cohort')}</th>
                            <th>{t('cohort.total')}</th>
                            <th>{t('cohort.finalized')}</th>
                            <th>{t('cohort.pending')}</th>
                            <th>{t('cohort.maturity')}</th>
                            <th>{t('cohort.median')}</th>
                            <th>{t('cohort.p90')}</th>
                            <th>{t('cohort.tail')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row) => (
                            <tr key={row.cohort}>
                                <td>{row.cohort}</td>
                                <td>{row.total_cases}</td>
                                <td>{row.finalized_cases}</td>
                                <td>{row.pending_cases}</td>
                                <td>{fmtPct(row.maturity_ratio)}</td>
                                <td>{fmtNumber(row.median_days)}</td>
                                <td>{fmtNumber(row.p90_days)}</td>
                                <td>{fmtPct(row.long_tail_90plus_ratio)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </section>
    )
}
