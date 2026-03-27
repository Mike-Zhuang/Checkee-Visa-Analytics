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
import type { MonthlyItem } from '../types'

type Props = {
    data: MonthlyItem[]
    onSelectMonth: (month: string) => void
}

export default function MonthlyChart({ data, onSelectMonth }: Props) {
    return (
        <section className="panel">
            <div className="panel-head">
                <h3>趋势与成熟度</h3>
                <p>点击某个月可钻取该月案例明细</p>
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
                        <Bar yAxisId="right" dataKey="pending_ratio" name="Pending比率" fill="#ffd166" onClick={(s) => onSelectMonth(String(s.submit_month))} />
                        <Line yAxisId="left" dataKey="median_days" name="中位数(天)" stroke="#0d3b66" strokeWidth={2} dot={{ r: 3 }} />
                        <Line yAxisId="left" dataKey="p90_days" name="P90(天)" stroke="#ef476f" strokeWidth={2} dot={{ r: 3 }} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </section>
    )
}
