import {
    Bar,
    BarChart,
    CartesianGrid,
    Legend,
    Line,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts'
import { useTranslation } from 'react-i18next'
import type { MonthlyItem } from '../types'

type Props = {
    data: MonthlyItem[]
    onSelectMonth: (month: string) => void
}

export default function MonthlyChart({ data, onSelectMonth }: Props) {
    const { t } = useTranslation()

    return (
        <section className="panel">
            <div className="panel-head">
                <h3>{t('chart.title')}</h3>
                <p>{t('chart.hint')}</p>
            </div>
            <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={360}>
                    <BarChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="submit_month" />
                        <YAxis yAxisId="left" />
                        <YAxis yAxisId="right" orientation="right" />
                        <Tooltip />
                        <Legend />
                        <Bar yAxisId="right" dataKey="pending_ratio" name={t('chart.pendingRatio')} fill="#ffd166" onClick={(s) => onSelectMonth(String(s.submit_month))} />
                        <Line yAxisId="left" dataKey="median_days" name={t('chart.medianDays')} stroke="#0d3b66" strokeWidth={2} dot={{ r: 3 }} />
                        <Line yAxisId="left" dataKey="p90_days" name={t('chart.p90Days')} stroke="#ef476f" strokeWidth={2} dot={{ r: 3 }} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </section>
    )
}
