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
                onPageChange={vi.fn()}
                onPageSizeChange={vi.fn()}
            />
        )

        expect(screen.getByRole('columnheader', { name: '雇主' })).toHaveClass('case-col-optional')
        expect(screen.getByRole('columnheader', { name: 'Entry' })).toHaveClass('case-col-tertiary')
        expect(screen.getByText('Google').closest('td')).toHaveClass('case-col-optional')
        expect(screen.getByText('I20').closest('td')).toHaveClass('case-col-tertiary')
    })
})
