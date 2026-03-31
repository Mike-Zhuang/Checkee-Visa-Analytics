import type { CaseItem, CaseSortBy, CaseSortOrder } from '../types'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { frontendConfig } from '../config'

type Props = {
    rows: CaseItem[]
    total: number
    page: number
    pageSize: number
    localHasNoteOnly: boolean
    onLocalHasNoteOnlyChange: (value: boolean) => void
    sortBy: CaseSortBy
    sortOrder: CaseSortOrder
    onSortByChange: (value: CaseSortBy) => void
    onSortOrderChange: (value: CaseSortOrder) => void
    onPageChange: (page: number) => void
    onPageSizeChange: (size: number) => void
}

type NoteTimelineItem = {
    action: string
    date: string
}

const NOTE_TIMELINE_PREVIEW_COUNT = 6
const NOTE_RAW_PREVIEW_MIN_LENGTH = 140

export default function CaseTable({
    rows,
    total,
    page,
    pageSize,
    localHasNoteOnly,
    onLocalHasNoteOnlyChange,
    sortBy,
    sortOrder,
    onSortByChange,
    onSortOrderChange,
    onPageChange,
    onPageSizeChange
}: Props) {
    const { t } = useTranslation()
    const totalPages = Math.max(1, Math.ceil(total / pageSize))
    const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({})

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
        const dateFirstRegex = /(?:^|[;,.。]\s*)(\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)\s*[:：-]?\s*([A-Za-z\u4e00-\u9fa5][^.;。]{1,240})/g
        const actionFirstRegex = /([A-Za-z\u4e00-\u9fa5][^.;。]{1,240}?)\s+(\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)/g

        const pushTimeline = (date: string, action: string) => {
            const normalizedAction = action.replace(/\s+/g, ' ').trim()
            if (!normalizedAction) {
                return
            }
            const dedupeKey = `${date}::${normalizedAction.toLowerCase()}`
            if (seen.has(dedupeKey)) {
                return
            }
            seen.add(dedupeKey)
            timeline.push({ date, action: normalizedAction })
        }

        let match: RegExpExecArray | null
        while ((match = actionFirstRegex.exec(normalized)) !== null) {
            pushTimeline(match[2], match[1])
        }
        while ((match = dateFirstRegex.exec(normalized)) !== null) {
            pushTimeline(match[1], match[2])
        }

        return timeline
    }

    const isRowExpanded = (rowKey: string): boolean => Boolean(expandedRows[rowKey])
    const toggleRowExpanded = (rowKey: string): void => {
        setExpandedRows((prev) => ({ ...prev, [rowKey]: !prev[rowKey] }))
    }

    return (
        <section className="panel" role="region" aria-labelledby="cases-title">
            <div className="panel-head">
                <h3 id="cases-title">{t('cases.title')}</h3>
                <p>{t('cases.summary', { count: rows.length, total })}</p>
            </div>
            <div className="cases-toolbar">
                <label className="checkbox-item note-filter-toggle" htmlFor="cases-note-only">
                    <input
                        id="cases-note-only"
                        type="checkbox"
                        checked={localHasNoteOnly}
                        onChange={(e) => onLocalHasNoteOnlyChange(e.currentTarget.checked)}
                    />
                    <span>{t('cases.localHasNoteOnly')}</span>
                </label>
                <div className="cases-sorters">
                    <label className="field field-inline" htmlFor="cases-sort-by">
                        <span>{t('cases.sortBy')}</span>
                        <select
                            id="cases-sort-by"
                            className="select-modern"
                            value={sortBy}
                            onChange={(e) => onSortByChange(e.currentTarget.value as CaseSortBy)}
                        >
                            <option value="check_date">{t('cases.sortByCheckDate')}</option>
                            <option value="complete_date">{t('cases.sortByCompleteDate')}</option>
                        </select>
                    </label>
                    <label className="field field-inline" htmlFor="cases-sort-order">
                        <span>{t('cases.sortOrder')}</span>
                        <select
                            id="cases-sort-order"
                            className="select-modern"
                            value={sortOrder}
                            onChange={(e) => onSortOrderChange(e.currentTarget.value as CaseSortOrder)}
                        >
                            <option value="desc">{t('cases.sortOrderDesc')}</option>
                            <option value="asc">{t('cases.sortOrderAsc')}</option>
                        </select>
                    </label>
                </div>
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
                            const rowKey = `${r.case_number}-${r.check_date}-${r.update_url || r.detail_url}`
                            const expanded = isRowExpanded(rowKey)
                            const hasTimeline = noteTimeline.length > 0
                            const visibleTimeline = expanded
                                ? noteTimeline
                                : noteTimeline.slice(0, NOTE_TIMELINE_PREVIEW_COUNT)
                            const showTimelineToggle = noteTimeline.length > NOTE_TIMELINE_PREVIEW_COUNT
                            const showRawToggle = r.detail_note.length > NOTE_RAW_PREVIEW_MIN_LENGTH
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
                                    <td className="case-col-note case-col-optional">
                                        {r.detail_note ? (
                                            <div className="note-cell">
                                                {hasTimeline ? (
                                                    <>
                                                        <div className="note-timeline" aria-label={t('cases.noteTimeline')}>
                                                            {visibleTimeline.map((item, index) => (
                                                                <div className="note-timeline-item" key={`${item.date}-${item.action}-${index}`}>
                                                                    <strong>{item.date}</strong>
                                                                    <em>{item.action}</em>
                                                                </div>
                                                            ))}
                                                        </div>
                                                        {showTimelineToggle ? (
                                                            <button
                                                                type="button"
                                                                className="ghost note-toggle"
                                                                onClick={() => toggleRowExpanded(rowKey)}
                                                            >
                                                                {expanded ? t('cases.collapseTimeline') : t('cases.expandTimeline')}
                                                            </button>
                                                        ) : null}
                                                    </>
                                                ) : (
                                                    <>
                                                        <div className={`note-raw ${expanded ? 'note-raw-expanded' : 'note-raw-collapsed'}`}>
                                                            {r.detail_note}
                                                        </div>
                                                        {showRawToggle ? (
                                                            <button
                                                                type="button"
                                                                className="ghost note-toggle"
                                                                onClick={() => toggleRowExpanded(rowKey)}
                                                            >
                                                                {expanded ? t('cases.collapseNote') : t('cases.expandNote')}
                                                            </button>
                                                        ) : null}
                                                    </>
                                                )}
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
