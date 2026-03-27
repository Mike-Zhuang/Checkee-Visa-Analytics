import type { CaseItem } from '../types'

type Props = {
    rows: CaseItem[]
    total: number
    page: number
    pageSize: number
    onPageChange: (page: number) => void
    onPageSizeChange: (size: number) => void
}

export default function CaseTable({ rows, total, page, pageSize, onPageChange, onPageSizeChange }: Props) {
    const totalPages = Math.max(1, Math.ceil(total / pageSize))

    return (
        <section className="panel">
            <div className="panel-head">
                <h3>案例明细</h3>
                <p>当前返回 {rows.length} / {total}</p>
            </div>

            {total === 0 ? <div className="empty-box">当前筛选条件下无案例数据，请调整筛选或先刷新抓取。</div> : null}

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

            <div className="pagination">
                <button className="ghost" onClick={() => onPageChange(1)} disabled={page <= 1}>首页</button>
                <button className="ghost" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>上一页</button>
                <span>第 {page} / {totalPages} 页</span>
                <button className="ghost" onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}>下一页</button>
                <button className="ghost" onClick={() => onPageChange(totalPages)} disabled={page >= totalPages}>末页</button>
                <label className="page-size">
                    每页
                    <select value={String(pageSize)} onChange={(e) => onPageSizeChange(Number(e.currentTarget.value))}>
                        <option value="50">50</option>
                        <option value="100">100</option>
                        <option value="200">200</option>
                    </select>
                    条
                </label>
            </div>
        </section>
    )
}
