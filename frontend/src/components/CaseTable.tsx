import type { CaseItem } from '../types'
import { useTranslation } from 'react-i18next'

import { frontendConfig } from '../config'

type Props = {
    rows: CaseItem[]
    total: number
    page: number
    pageSize: number
    onPageChange: (page: number) => void
    onPageSizeChange: (size: number) => void
}

export default function CaseTable({ rows, total, page, pageSize, onPageChange, onPageSizeChange }: Props) {
    const { t } = useTranslation()
    const totalPages = Math.max(1, Math.ceil(total / pageSize))

    const compactNote = (value: string): string => {
        if (!value) {
            return '-'
        }
        if (value.length <= 72) {
            return value
        }
        return `${value.slice(0, 69).trimEnd()}...`
    }

    const detailLocation = (city: string, state: string): string => {
        const parts = [city, state].filter(Boolean)
        return parts.length > 0 ? parts.join(' / ') : '-'
    }

    return (
        <section className="panel" role="region" aria-labelledby="cases-title">
            <div className="panel-head">
                <h3 id="cases-title">{t('cases.title')}</h3>
                <p>{t('cases.summary', { count: rows.length, total })}</p>
            </div>

            {total === 0 ? (
                <div className="empty-box">
                    <strong>{t('cases.emptyTitle')}</strong>
                    <p>{t('cases.empty')}</p>
                    <p>{t('cases.emptyAction')}</p>
                </div>
            ) : null}

            <div className="table-wrap">
                <table>
                    <caption>{t('cases.caption')}</caption>
                    <thead>
                        <tr>
                            <th scope="col">{t('cases.case')}</th>
                            <th scope="col">{t('cases.visa')}</th>
                            <th scope="col">{t('cases.entry')}</th>
                            <th scope="col">{t('cases.consulate')}</th>
                            <th scope="col">{t('cases.major')}</th>
                            <th scope="col">{t('cases.employer')}</th>
                            <th scope="col">{t('cases.location')}</th>
                            <th scope="col">{t('cases.status')}</th>
                            <th scope="col">{t('cases.checkDate')}</th>
                            <th scope="col">{t('cases.completeDate')}</th>
                            <th scope="col">{t('cases.calcDays')}</th>
                            <th scope="col">{t('cases.note')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((r) => (
                            <tr key={`${r.case_number}-${r.check_date}`}>
                                <td>{r.nickname}</td>
                                <td>{r.visa_type}</td>
                                <td>{r.visa_entry}</td>
                                <td>{r.consulate}</td>
                                <td>{r.major || '-'}</td>
                                <td>{r.detail_employer || '-'}</td>
                                <td>{detailLocation(r.detail_city, r.detail_state)}</td>
                                <td>{r.status}</td>
                                <td>{r.check_date}</td>
                                <td>{r.complete_date}</td>
                                <td>{r.waiting_days_calc || r.observed_days}</td>
                                <td title={r.detail_note || ''}>{compactNote(r.detail_note)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="pagination">
                <button type="button" className="ghost" onClick={() => onPageChange(1)} disabled={page <= 1} aria-label={t('cases.first')}>
                    {t('cases.first')}
                </button>
                <button type="button" className="ghost" onClick={() => onPageChange(page - 1)} disabled={page <= 1} aria-label={t('cases.prev')}>
                    {t('cases.prev')}
                </button>
                <span aria-live="polite">{t('cases.page', { page, total: totalPages })}</span>
                <button type="button" className="ghost" onClick={() => onPageChange(page + 1)} disabled={page >= totalPages} aria-label={t('cases.next')}>
                    {t('cases.next')}
                </button>
                <button type="button" className="ghost" onClick={() => onPageChange(totalPages)} disabled={page >= totalPages} aria-label={t('cases.last')}>
                    {t('cases.last')}
                </button>
                <label className="page-size" htmlFor="page-size-select">
                    {t('cases.perPage')}
                    <select id="page-size-select" value={String(pageSize)} onChange={(e) => onPageSizeChange(Number(e.currentTarget.value))}>
                        {frontendConfig.pageSizeOptions.map((item) => (
                            <option key={item} value={String(item)}>{item}</option>
                        ))}
                    </select>
                    {t('cases.rows')}
                </label>
            </div>
        </section>
    )
}
