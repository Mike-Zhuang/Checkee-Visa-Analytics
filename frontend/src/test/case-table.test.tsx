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
        status: 'Clear',
        check_date: '2026-03-01',
        complete_date: '2026-03-25',
        waiting_days_reported: '24',
        waiting_days_calc: '24',
        observed_days: '',
        event: '1',
        detail_url: '',
        update_url: ''
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

        expect(screen.getByText('当前筛选条件下无案例数据，请调整筛选或先刷新抓取。')).toBeInTheDocument()
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
})
