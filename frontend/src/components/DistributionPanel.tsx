import { useTranslation } from 'react-i18next'

import type { DistributionItem } from '../types'

type Props = {
    rows: DistributionItem[]
}

export default function DistributionPanel({ rows }: Props) {
    const { t } = useTranslation()

    return (
        <section className="panel">
            <div className="panel-head">
                <h3>{t('distribution.title')}</h3>
                <p>{t('distribution.hint')}</p>
            </div>
            <div className="distribution-list">
                {rows.map((row) => (
                    <div className="distribution-item" key={row.bucket}>
                        <div className="distribution-head">
                            <span>{row.bucket}</span>
                            <span>{row.count} ({(row.ratio * 100).toFixed(2)}%)</span>
                        </div>
                        <div className="distribution-track" aria-hidden="true">
                            <div className="distribution-fill" style={{ width: `${Math.max(2, row.ratio * 100)}%` }} />
                        </div>
                    </div>
                ))}
            </div>
        </section>
    )
}
