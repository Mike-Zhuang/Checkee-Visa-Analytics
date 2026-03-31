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
const NOTE_RAW_PREVIEW_MIN_LENGTH = 260
const DATE_PATTERN_SOURCE = String.raw`(?<!\d)(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}[./-]\d{1,2})(?!\d)`
const DATE_TOKEN_REGEX = new RegExp(DATE_PATTERN_SOURCE, 'g')

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

    const parseTimelineDate = (dateToken: string): number | null => {
        const normalized = dateToken.replace(/[./]/g, '-').trim()
        const parts = normalized.split('-').map((part) => Number(part))
        if (parts.length < 2 || parts.some((part) => Number.isNaN(part))) {
            return null
        }

        let year = 0
        let month = 0
        let day = 0
        if (parts[0] > 999 && parts.length >= 3) {
            year = parts[0]
            month = parts[1]
            day = parts[2]
        } else if (parts.length >= 3) {
            month = parts[0]
            day = parts[1]
            year = parts[2]
            if (year < 100) {
                year += 2000
            }
        } else {
            return null
        }

        if (month < 1 || month > 12 || day < 1 || day > 31 || year < 1900 || year > 2100) {
            return null
        }
        return Date.UTC(year, month - 1, day)
    }

    const shouldShowRawExpand = (note: string): boolean => {
        const normalized = note.trim()
        if (!normalized) {
            return false
        }
        const newlineCount = (normalized.match(/\n/g) || []).length
        if (newlineCount >= 3) {
            return true
        }
        return normalized.length > NOTE_RAW_PREVIEW_MIN_LENGTH
    }

    const buildNoteTimeline = (note: string): NoteTimelineItem[] => {
        const normalized = note.replace(/\r/g, '').replace(/[ \t]+/g, ' ').trim()
        if (!normalized) {
            return []
        }

        type TimelineDraft = NoteTimelineItem & { order: number; sortValue: number | null }
        const timeline: TimelineDraft[] = []
        const seen = new Set<string>()
        let order = 0

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
            timeline.push({
                date,
                action: normalizedAction,
                order,
                sortValue: parseTimelineDate(date)
            })
            order += 1
        }

        const cleanActionText = (value: string): string => {
            return value
                .replace(/^[-–—:：\s]+/, '')
                .replace(/\(clearance received[:：]?\s*[^)]*\)/gi, '')
                .replace(/\s+/g, ' ')
                .trim()
        }

        const baseSegments = normalized
            .split(/[\n;；。]+/g)
            .map((segment) => segment.trim())
            .filter(Boolean)

        for (const baseSegment of baseSegments) {
            const matches = Array.from(baseSegment.matchAll(DATE_TOKEN_REGEX))
            if (matches.length === 0) {
                continue
            }

            for (let index = 0; index < matches.length; index += 1) {
                const current = matches[index]
                const next = matches[index + 1]
                const previous = matches[index - 1]
                if (!current.index && current.index !== 0) {
                    continue
                }

                const token = current[0]
                const currentEnd = current.index + token.length
                const nextStart = next && next.index !== undefined ? next.index : baseSegment.length
                const previousEnd = previous && previous.index !== undefined ? previous.index + previous[0].length : 0

                const after = cleanActionText(baseSegment.slice(currentEnd, nextStart))
                const before = cleanActionText(baseSegment.slice(previousEnd, current.index))
                const action = after || before
                if (!action) {
                    continue
                }
                pushTimeline(token, action)
            }
        }

        return timeline
            .sort((a, b) => {
                if (a.sortValue !== null && b.sortValue !== null && a.sortValue !== b.sortValue) {
                    return a.sortValue - b.sortValue
                }
                if (a.sortValue !== null && b.sortValue === null) {
                    return -1
                }
                if (a.sortValue === null && b.sortValue !== null) {
                    return 1
                }
                return a.order - b.order
            })
            .map((item) => ({ date: item.date, action: item.action }))
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
                            const showRawToggle = shouldShowRawExpand(r.detail_note)
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
