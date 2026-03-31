import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import CaseTable from '../components/CaseTable'
import type { CaseItem } from '../types'

const rows: CaseItem[] = [
    {
        source_month: '2026-03',
        case_number: 'A001',
        nickname: 'alpha',
        visa_type: 'F1',
        visa_entry: 'I20',
        consulate: 'BeiJing',
        major: 'CS',
        major_category_l1: 'STEM',
        major_category_l2: 'Software & Systems',
        major_classification_source: 'auto',
        status: 'Clear',
        check_date: '2026-03-01',
        complete_date: '2026-03-25',
        waiting_days_reported: '24',
        waiting_days_calc: '24',
        observed_days: '',
        event: '1',
        detail_url: '',
        update_url: '',
        detail_employer: 'Google',
        detail_note: 'STEM case with complete timeline',
        detail_city: 'Beijing',
        detail_state: 'Beijing'
    }
]

describe('CaseTable', () => {
    it('无数据时展示空态', () => {
        render(
            <CaseTable
                rows={[]}
                total={0}
                page={1}
                pageSize={50}
                localHasNoteOnly={false}
                onLocalHasNoteOnlyChange={vi.fn()}
                sortBy="check_date"
                sortOrder="desc"
                onSortByChange={vi.fn()}
                onSortOrderChange={vi.fn()}
                onPageChange={vi.fn()}
                onPageSizeChange={vi.fn()}
            />
        )

        expect(screen.getByText('暂时没有匹配的案例')).toBeInTheDocument()
    })

    it('点击下一页会触发 onPageChange', async () => {
        const onPageChange = vi.fn()
        const user = userEvent.setup()

        render(
            <CaseTable
                rows={rows}
                total={120}
                page={1}
                pageSize={50}
                localHasNoteOnly={false}
                onLocalHasNoteOnlyChange={vi.fn()}
                sortBy="check_date"
                sortOrder="desc"
                onSortByChange={vi.fn()}
                onSortOrderChange={vi.fn()}
                onPageChange={onPageChange}
                onPageSizeChange={vi.fn()}
            />
        )

        await user.click(screen.getByRole('button', { name: '下一页' }))
        expect(onPageChange).toHaveBeenCalledWith(2)
    })

    it('应保留移动端列隐藏所需 class 挂点', () => {
        render(
            <CaseTable
                rows={rows}
                total={1}
                page={1}
                pageSize={50}
                localHasNoteOnly={false}
                onLocalHasNoteOnlyChange={vi.fn()}
                sortBy="check_date"
                sortOrder="desc"
                onSortByChange={vi.fn()}
                onSortOrderChange={vi.fn()}
                onPageChange={vi.fn()}
                onPageSizeChange={vi.fn()}
            />
        )

        expect(screen.getByRole('columnheader', { name: '雇主' })).toHaveClass('case-col-optional')
        expect(screen.getByRole('columnheader', { name: 'Entry' })).toHaveClass('case-col-tertiary')
        expect(screen.getByText('Google').closest('td')).toHaveClass('case-col-optional')
        expect(screen.getByText('I20').closest('td')).toHaveClass('case-col-tertiary')
    })

    it('备注命中时间线时仅展示时间线卡片', () => {
        const timelineRows: CaseItem[] = [
            {
                ...rows[0],
                case_number: 'A002',
                detail_note: 'interview 2.5 Submit documents via email 2.6 issued 3.18'
            }
        ]

        render(
            <CaseTable
                rows={timelineRows}
                total={1}
                page={1}
                pageSize={50}
                localHasNoteOnly={false}
                onLocalHasNoteOnlyChange={vi.fn()}
                sortBy="check_date"
                sortOrder="desc"
                onSortByChange={vi.fn()}
                onSortOrderChange={vi.fn()}
                onPageChange={vi.fn()}
                onPageSizeChange={vi.fn()}
            />
        )

        expect(screen.getByLabelText('时间线')).toBeInTheDocument()
        expect(screen.getByText('2.5')).toBeInTheDocument()
        expect(screen.getByText('3.18')).toBeInTheDocument()
        expect(screen.queryByText(/interview 2.5 Submit documents via email/i)).not.toBeInTheDocument()
    })

    it('时间线默认折叠并支持展开收起', async () => {
        const user = userEvent.setup()
        const timelineRows: CaseItem[] = [
            {
                ...rows[0],
                case_number: 'A003',
                detail_note: 'interview 2.1 submit docs 2.2 dropoff 2.3 admin processing 2.4 approved 2.5 printed 2.6 delivered 2.7'
            }
        ]

        render(
            <CaseTable
                rows={timelineRows}
                total={1}
                page={1}
                pageSize={50}
                localHasNoteOnly={false}
                onLocalHasNoteOnlyChange={vi.fn()}
                sortBy="check_date"
                sortOrder="desc"
                onSortByChange={vi.fn()}
                onSortOrderChange={vi.fn()}
                onPageChange={vi.fn()}
                onPageSizeChange={vi.fn()}
            />
        )

        expect(screen.queryByText('2.7')).not.toBeInTheDocument()
        await user.click(screen.getByRole('button', { name: '展开全部时间线' }))
        expect(screen.getByText('2.7')).toBeInTheDocument()
        await user.click(screen.getByRole('button', { name: '收起时间线' }))
        expect(screen.queryByText('2.7')).not.toBeInTheDocument()
    })

    it('无时间线备注使用多行预览并支持展开收起', async () => {
        const user = userEvent.setup()
        const longPlainNote = 'This note has no date markers but contains enough text to trigger preview mode. '.repeat(4)
        const noTimelineRows: CaseItem[] = [
            {
                ...rows[0],
                case_number: 'A004',
                detail_note: longPlainNote
            }
        ]

        const { container } = render(
            <CaseTable
                rows={noTimelineRows}
                total={1}
                page={1}
                pageSize={50}
                localHasNoteOnly={false}
                onLocalHasNoteOnlyChange={vi.fn()}
                sortBy="check_date"
                sortOrder="desc"
                onSortByChange={vi.fn()}
                onSortOrderChange={vi.fn()}
                onPageChange={vi.fn()}
                onPageSizeChange={vi.fn()}
            />
        )

        const noteElement = container.querySelector('.note-raw')
        expect(noteElement).not.toBeNull()
        expect(noteElement).toHaveClass('note-raw-collapsed')
        expect(screen.queryByLabelText('时间线')).not.toBeInTheDocument()
        await user.click(screen.getByRole('button', { name: '展开 Note' }))
        expect(noteElement).toHaveClass('note-raw-expanded')
        await user.click(screen.getByRole('button', { name: '收起 Note' }))
        expect(noteElement).toHaveClass('note-raw-collapsed')
    })

    it('应识别 YYYY-MM-DD 时间线并按日期升序展示', () => {
        const timelineRows: CaseItem[] = [
            {
                ...rows[0],
                case_number: 'A005',
                detail_note: '2025-10-15 Refused under 221g 2026-01-06 Receive email to send passport back 2026-01-12 Approved 2026-01-14 Issued'
            }
        ]

        const { container } = render(
            <CaseTable
                rows={timelineRows}
                total={1}
                page={1}
                pageSize={50}
                localHasNoteOnly={false}
                onLocalHasNoteOnlyChange={vi.fn()}
                sortBy="check_date"
                sortOrder="desc"
                onSortByChange={vi.fn()}
                onSortOrderChange={vi.fn()}
                onPageChange={vi.fn()}
                onPageSizeChange={vi.fn()}
            />
        )

        const timelineItems = Array.from(container.querySelectorAll('.note-timeline-item strong')).map((el) => el.textContent)
        expect(timelineItems).toEqual(['2025-10-15', '2026-01-06', '2026-01-12', '2026-01-14'])
        expect(screen.getByText('Refused under 221g')).toBeInTheDocument()
        expect(screen.getByText('Receive email to send passport back')).toBeInTheDocument()
        expect(screen.getByText('Approved')).toBeInTheDocument()
        expect(screen.getByText('Issued')).toBeInTheDocument()
    })

    it('短无时间线备注不应出现展开按钮', () => {
        const plainRows: CaseItem[] = [
            {
                ...rows[0],
                case_number: 'A006',
                detail_note: 'No timeline here, just a short note.'
            }
        ]

        render(
            <CaseTable
                rows={plainRows}
                total={1}
                page={1}
                pageSize={50}
                localHasNoteOnly={false}
                onLocalHasNoteOnlyChange={vi.fn()}
                sortBy="check_date"
                sortOrder="desc"
                onSortByChange={vi.fn()}
                onSortOrderChange={vi.fn()}
                onPageChange={vi.fn()}
                onPageSizeChange={vi.fn()}
            />
        )

        expect(screen.queryByRole('button', { name: '展开 Note' })).not.toBeInTheDocument()
        expect(screen.queryByRole('button', { name: '收起 Note' })).not.toBeInTheDocument()
    })

    it('本地 Note 开关应触发 onLocalHasNoteOnlyChange', async () => {
        const onLocalHasNoteOnlyChange = vi.fn()
        const user = userEvent.setup()

        render(
            <CaseTable
                rows={rows}
                total={1}
                page={1}
                pageSize={50}
                localHasNoteOnly={false}
                onLocalHasNoteOnlyChange={onLocalHasNoteOnlyChange}
                sortBy="check_date"
                sortOrder="desc"
                onSortByChange={vi.fn()}
                onSortOrderChange={vi.fn()}
                onPageChange={vi.fn()}
                onPageSizeChange={vi.fn()}
            />
        )

        await user.click(screen.getByRole('checkbox', { name: '仅看有 Note（仅明细）' }))
        expect(onLocalHasNoteOnlyChange).toHaveBeenCalledWith(true)
    })

    it('排序控件应触发对应回调', async () => {
        const onSortByChange = vi.fn()
        const onSortOrderChange = vi.fn()
        const user = userEvent.setup()

        render(
            <CaseTable
                rows={rows}
                total={1}
                page={1}
                pageSize={50}
                localHasNoteOnly={false}
                onLocalHasNoteOnlyChange={vi.fn()}
                sortBy="check_date"
                sortOrder="desc"
                onSortByChange={onSortByChange}
                onSortOrderChange={onSortOrderChange}
                onPageChange={vi.fn()}
                onPageSizeChange={vi.fn()}
            />
        )

        await user.selectOptions(screen.getByLabelText('排序字段'), 'complete_date')
        await user.selectOptions(screen.getByLabelText('排序方向'), 'asc')
        expect(onSortByChange).toHaveBeenCalledWith('complete_date')
        expect(onSortOrderChange).toHaveBeenCalledWith('asc')
    })
})
