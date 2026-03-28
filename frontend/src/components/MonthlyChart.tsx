import {
    Bar,
    CartesianGrid,
    ComposedChart,
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

function toNumber(value: unknown): number | null {
    if (value == null || value === '') return null
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
}

function clamp01(value: number): number {
    if (value < 0) return 0
    if (value > 1) return 1
    return value
}

export default function MonthlyChart({ data, onSelectMonth }: Props) {
    const { t } = useTranslation()
    const chartData = data.map((row) => {
        const totalCases = toNumber(row.total_cases) ?? 0
        const pendingCases = toNumber(row.pending_cases)
        const clearCases = toNumber(row.clear_cases)

        const pendingRatioRaw =
            toNumber(row.pending_ratio)
            ?? (totalCases > 0 && pendingCases != null ? pendingCases / totalCases : 0)

        const clearRatioRaw =
            toNumber(row.clear_ratio)
            ?? (totalCases > 0 && clearCases != null ? clearCases / totalCases : null)

        return {
            ...row,
            pending_ratio: clamp01(pendingRatioRaw),
            clear_ratio: clamp01(clearRatioRaw ?? (1 - clamp01(pendingRatioRaw))),
            median_days: toNumber(row.median_days),
            p90_days: toNumber(row.p90_days)
        }
    })

    const hasDurationSeries = chartData.some((row) => row.median_days != null || row.p90_days != null)

    return (
        <section className="panel">
            <div className="panel-head">
                <h3>{t('chart.title')}</h3>
                <p>{t('chart.hint')}</p>
            </div>
            <div className="chart-read-guide">
                <span>{t('chart.readGuidePending')}</span>
                <span>{t('chart.readGuideClear')}</span>
                <span>{t('chart.readGuideMedian')}</span>
                <span>{t('chart.readGuideP90')}</span>
            </div>
            {!hasDurationSeries ? <div className="chart-note">{t('chart.noDurationSeries')}</div> : null}
            <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={360}>
                    <ComposedChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="submit_month" />
                        <YAxis yAxisId="left" domain={[0, 'auto']} allowDecimals={false} />
                        <YAxis yAxisId="right" orientation="right" domain={[0, 1]} />
                        <Tooltip />
                        <Legend />
                        <Bar yAxisId="right" dataKey="pending_ratio" name={t('chart.pendingRatio')} fill="#ffd166" fillOpacity={0.7} onClick={(s) => onSelectMonth(String(s.submit_month))} />
                        <Line yAxisId="right" type="monotone" connectNulls dataKey="clear_ratio" name={t('chart.clearRatio')} stroke="#2f9e44" strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                        <Line yAxisId="left" type="monotone" connectNulls dataKey="median_days" name={t('chart.medianDays')} stroke="#0d3b66" strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                        <Line yAxisId="left" type="monotone" connectNulls dataKey="p90_days" name={t('chart.p90Days')} stroke="#ef476f" strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>
        </section>
    )
}
