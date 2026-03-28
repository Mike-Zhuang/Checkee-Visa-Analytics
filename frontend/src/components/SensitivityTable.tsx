import type { SensitivityItem } from '../types'
import { useTranslation } from 'react-i18next'

type Props = { rows: SensitivityItem[] }

export default function SensitivityTable({ rows }: Props) {
    const { t } = useTranslation()

    const scenarioLabel = (value: string): string => {
        if (value === 'Conservative') return t('sensitivity.scenarioLabel.Conservative')
        if (value === 'Neutral') return t('sensitivity.scenarioLabel.Neutral')
        if (value === 'Aggressive') return t('sensitivity.scenarioLabel.Aggressive')
        return value
    }

    return (
        <section className="panel">
            <div className="panel-head">
                <h3>{t('sensitivity.title')}</h3>
                <p>{t('sensitivity.hint')}</p>
            </div>
            <p className="hint">{t('sensitivity.explain')}</p>
            <div className="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>{t('sensitivity.scenario')}</th>
                            <th>{t('sensitivity.median')}</th>
                            <th>{t('sensitivity.p90')}</th>
                            <th>{t('sensitivity.tailRatio')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((r) => (
                            <tr key={r.scenario}>
                                <td>{scenarioLabel(r.scenario)}</td>
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
