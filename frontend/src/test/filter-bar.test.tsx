import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import FilterBar from '../components/FilterBar'
import type { ConsulateGroup, Filters, OptionsResponse } from '../types'

const options: OptionsResponse = {
    months: ['2026-03', '2026-02', '2026-01', '2025-12', '2025-11', '2025-10'],
    visa_types: ['F1', 'H1B'],
    consulates: ['BeiJing', 'Toronto'],
    statuses: ['Pending', 'Clear'],
    entries: ['I20', 'I129']
}

const groups: ConsulateGroup[] = [
    { key: 'china', label: '中国', consulates: ['BeiJing'] },
    { key: 'canada', label: '加拿大', consulates: ['Toronto'] }
]

const emptyFilters: Filters = {
    visa_types: [],
    consulates: [],
    statuses: [],
    entries: [],
    months: []
}

describe('FilterBar', () => {
    it('可渲染筛选区域与核心按钮', () => {
        render(
            <FilterBar
                options={options}
                consulateGroups={groups}
                filters={emptyFilters}
                refreshFromMonth=""
                defaultRefreshMonths={6}
                showConsulateGroups={true}
                onRefreshFromMonthChange={vi.fn()}
                onChange={vi.fn()}
                onReset={vi.fn()}
                onRefresh={vi.fn()}
            />
        )

        expect(screen.getByText('筛选条件')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: '刷新数据' })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: '重置筛选' })).toBeInTheDocument()
    })

    it('点击最近6月应触发 months 更新', async () => {
        const onChange = vi.fn()
        const user = userEvent.setup()

        render(
            <FilterBar
                options={options}
                consulateGroups={groups}
                filters={emptyFilters}
                refreshFromMonth=""
                defaultRefreshMonths={6}
                showConsulateGroups={true}
                onRefreshFromMonthChange={vi.fn()}
                onChange={onChange}
                onReset={vi.fn()}
                onRefresh={vi.fn()}
            />
        )

        await user.click(screen.getByRole('button', { name: '最近6月' }))
        expect(onChange).toHaveBeenCalledTimes(1)
        expect(onChange).toHaveBeenCalledWith({
            ...emptyFilters,
            months: ['2026-03', '2026-02', '2026-01', '2025-12', '2025-11', '2025-10']
        })
    })
})
