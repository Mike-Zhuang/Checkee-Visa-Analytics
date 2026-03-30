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

type NoteTimelineItem = {
    action: string
    date: string
}

export default function CaseTable({ rows, total, page, pageSize, onPageChange, onPageSizeChange }: Props) {
    const { t } = useTranslation()
    const totalPages = Math.max(1, Math.ceil(total / pageSize))

    const compactNote = (value: string, maxLength = 96): string => {
        if (!value) {
            return '-'
        }
        if (value.length <= maxLength) {
            return value
        }
        return `${value.slice(0, maxLength - 3).trimEnd()}...`
    }

    const detailLocation = (city: string, state: string): string => {
        const parts = [city, state].filter(Boolean)
        return parts.length > 0 ? parts.join(' / ') : '-'
    }

    const sourceLabel = (source: string): string => {
        if (source === 'manual') return t('cases.classificationSourceManual')
        if (source === 'auto') return t('cases.classificationSourceAuto')
        if (source === 'not_applicable') return t('cases.classificationSourceNotApplicable')
        return t('cases.classificationSourceUnknown')
    }

    const buildNoteTimeline = (note: string): NoteTimelineItem[] => {
        const normalized = note.replace(/\s+/g, ' ').trim()
        if (!normalized) {
            return []
        }

        const timeline: NoteTimelineItem[] = []
        const seen = new Set<string>()
        const dateFirstRegex = /(?:^|[;,.。]\s*)(\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)\s*[:：-]?\s*([A-Za-z\u4e00-\u9fa5][^.;。]{1,80})/g
        const actionFirstRegex = /([A-Za-z\u4e00-\u9fa5][^.;。]{1,80}?)\s+(\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)/g

        const pushTimeline = (date: string, action: string) => {
            const compactAction = action.replace(/\s+/g, ' ').trim()
            if (!compactAction) {
                return
            }
            const dedupeKey = `${date}::${compactAction.toLowerCase()}`
            if (seen.has(dedupeKey)) {
                return
            }
            seen.add(dedupeKey)
            timeline.push({ date, action: compactAction })
        }

        let match: RegExpExecArray | null
        while ((match = actionFirstRegex.exec(normalized)) !== null) {
            pushTimeline(match[2], match[1])
        }
        while ((match = dateFirstRegex.exec(normalized)) !== null) {
            pushTimeline(match[1], match[2])
        }

        return timeline.slice(0, 5)
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
                            <th scope="col" className="case-col-case">{t('cases.case')}</th>
                            <th scope="col" className="case-col-visa">{t('cases.visa')}</th>
                            <th scope="col" className="case-col-entry case-col-tertiary">{t('cases.entry')}</th>
                            <th scope="col" className="case-col-consulate">{t('cases.consulate')}</th>
                            <th scope="col" className="case-col-major">{t('cases.major')}</th>
                            <th scope="col" className="case-col-employer case-col-optional">{t('cases.employer')}</th>
                            <th scope="col" className="case-col-location case-col-optional">{t('cases.location')}</th>
                            <th scope="col" className="case-col-status">{t('cases.status')}</th>
                            <th scope="col" className="case-col-check-date">{t('cases.checkDate')}</th>
                            <th scope="col" className="case-col-complete-date case-col-optional">{t('cases.completeDate')}</th>
                            <th scope="col" className="case-col-calc-days case-col-optional">{t('cases.calcDays')}</th>
                            <th scope="col" className="case-col-note case-col-optional">{t('cases.note')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((r) => {
                            const noteTimeline = buildNoteTimeline(r.detail_note)
                            return (
                                <tr key={`${r.case_number}-${r.check_date}`}>
                                    <td className="case-col-case">{r.nickname}</td>
                                    <td className="case-col-visa">{r.visa_type}</td>
                                    <td className="case-col-entry case-col-tertiary">{r.visa_entry}</td>
                                    <td className="case-col-consulate">{r.consulate}</td>
                                    <td className="case-col-major">
                                        <div className="major-cell">
                                            <span className="major-primary">{r.major || '-'}</span>
                                            <small className="major-secondary">
                                                {(r.major_category_l1 || '-')}
                                                {' / '}
                                                {(r.major_category_l2 || '-')}
                                            </small>
                                            <small className={`major-source major-source-${r.major_classification_source || 'unknown'}`}>
                                                {sourceLabel(r.major_classification_source || 'unknown')}
                                            </small>
                                        </div>
                                    </td>
                                    <td className="case-col-employer case-col-optional">{r.detail_employer || '-'}</td>
                                    <td className="case-col-location case-col-optional">{detailLocation(r.detail_city, r.detail_state)}</td>
                                    <td className="case-col-status">{r.status}</td>
                                    <td className="case-col-check-date">{r.check_date}</td>
                                    <td className="case-col-complete-date case-col-optional">{r.complete_date}</td>
                                    <td className="case-col-calc-days case-col-optional">{r.waiting_days_calc || r.observed_days}</td>
                                    <td className="case-col-note case-col-optional" title={r.detail_note || ''}>
                                        {r.detail_note ? (
                                            <div className="note-cell">
                                                <div className="note-raw">{compactNote(r.detail_note)}</div>
                                                {noteTimeline.length > 0 ? (
                                                    <div className="note-timeline" aria-label={t('cases.noteTimeline')}>
                                                        {noteTimeline.map((item, index) => (
                                                            <span className="note-timeline-item" key={`${item.date}-${item.action}-${index}`}>
                                                                <strong>{item.date}</strong>
                                                                <em>{compactNote(item.action, 36)}</em>
                                                            </span>
                                                        ))}
                                                    </div>
                                                ) : null}
                                            </div>
                                        ) : '-'}
                                    </td>
                                </tr>
                            )
                        })}
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
                    <select id="page-size-select" className="select-modern" value={String(pageSize)} onChange={(e) => onPageSizeChange(Number(e.currentTarget.value))}>
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
