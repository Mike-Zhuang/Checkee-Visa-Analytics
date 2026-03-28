import { useTranslation } from 'react-i18next'

import type { AnomalyItem } from '../types'

type Props = {
    rows: AnomalyItem[]
}

export default function AnomalyTable({ rows }: Props) {
    const { t } = useTranslation()

    const reasonLabel = (reason: string): string => {
        if (reason === 'finalized_long_wait') return t('anomaly.reasonFinalizedLongWait')
        if (reason === 'pending_long_wait') return t('anomaly.reasonPendingLongWait')
        return reason
    }

    return (
        <section className="panel">
            <div className="panel-head">
                <h3>{t('anomaly.title')}</h3>
                <p>{t('anomaly.hint')}</p>
            </div>
            {rows.length === 0 ? (
                <div className="empty-box">
                    <strong>{t('anomaly.emptyTitle')}</strong>
                    <p>{t('anomaly.empty')}</p>
                </div>
            ) : (
                <div className="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>{t('anomaly.case')}</th>
                                <th>{t('anomaly.visa')}</th>
                                <th>{t('anomaly.consulate')}</th>
                                <th>{t('anomaly.status')}</th>
                                <th>{t('anomaly.days')}</th>
                                <th>{t('anomaly.reason')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((row) => (
                                <tr key={`${row.case_number}-${row.check_date}-${row.reason}`}>
                                    <td>{row.case_number || '-'}</td>
                                    <td>{row.visa_type}</td>
                                    <td>{row.consulate}</td>
                                    <td>{row.status}</td>
                                    <td>{row.days}</td>
                                    <td>{reasonLabel(row.reason)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    )
}
