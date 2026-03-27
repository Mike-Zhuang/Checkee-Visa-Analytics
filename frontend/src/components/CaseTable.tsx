import type { CaseItem } from '../types'

type Props = {
    rows: CaseItem[]
    total: number
}

export default function CaseTable({ rows, total }: Props) {
    return (
        <section className="panel">
            <div className="panel-head">
                <h3>案例明细</h3>
                <p>当前返回 {rows.length} / {total}</p>
            </div>
            <div className="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Case</th>
                            <th>Visa</th>
                            <th>Entry</th>
                            <th>Consulate</th>
                            <th>Status</th>
                            <th>Check Date</th>
                            <th>Complete Date</th>
                            <th>Calc Days</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((r) => (
                            <tr key={`${r.case_number}-${r.check_date}`}>
                                <td>{r.nickname}</td>
                                <td>{r.visa_type}</td>
                                <td>{r.visa_entry}</td>
                                <td>{r.consulate}</td>
                                <td>{r.status}</td>
                                <td>{r.check_date}</td>
                                <td>{r.complete_date}</td>
                                <td>{r.waiting_days_calc || r.observed_days}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </section>
    )
}
