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
    entries: ['I20', 'I129'],
    fetch_sources: ['monthly_track', 'latest_snapshot']
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
                refreshSources={['monthly_track']}
                availableRefreshSources={options.fetch_sources}
                defaultRefreshMonths={6}
                showConsulateGroups={true}
                isRefreshing={false}
                refreshFeedback={null}
                onRefreshFromMonthChange={vi.fn()}
                onRefreshSourcesChange={vi.fn()}
                onChange={vi.fn()}
                onReset={vi.fn()}
                onRefresh={vi.fn()}
            />
        )

        expect(screen.getByText('一步一步筛选与刷新')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: '开始刷新数据' })).toBeInTheDocument()
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
                refreshSources={['monthly_track']}
                availableRefreshSources={options.fetch_sources}
                defaultRefreshMonths={6}
                showConsulateGroups={true}
                isRefreshing={false}
                refreshFeedback={null}
                onRefreshFromMonthChange={vi.fn()}
                onRefreshSourcesChange={vi.fn()}
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

    it('点击状态勾选应触发 statuses 更新', async () => {
        const onChange = vi.fn()
        const user = userEvent.setup()

        render(
            <FilterBar
                options={options}
                consulateGroups={groups}
                filters={emptyFilters}
                refreshFromMonth=""
                refreshSources={['monthly_track']}
                availableRefreshSources={options.fetch_sources}
                defaultRefreshMonths={6}
                showConsulateGroups={true}
                isRefreshing={false}
                refreshFeedback={null}
                onRefreshFromMonthChange={vi.fn()}
                onRefreshSourcesChange={vi.fn()}
                onChange={onChange}
                onReset={vi.fn()}
                onRefresh={vi.fn()}
            />
        )

        await user.click(screen.getByRole('checkbox', { name: 'Pending' }))
        expect(onChange).toHaveBeenCalledWith({
            ...emptyFilters,
            statuses: ['Pending']
        })
    })

    it('未分组模式下点击签证勾选应触发 visa_types 更新', async () => {
        const onChange = vi.fn()
        const user = userEvent.setup()

        render(
            <FilterBar
                options={options}
                consulateGroups={groups}
                filters={emptyFilters}
                refreshFromMonth=""
                refreshSources={['monthly_track']}
                availableRefreshSources={options.fetch_sources}
                defaultRefreshMonths={6}
                showConsulateGroups={false}
                isRefreshing={false}
                refreshFeedback={null}
                onRefreshFromMonthChange={vi.fn()}
                onRefreshSourcesChange={vi.fn()}
                onChange={onChange}
                onReset={vi.fn()}
                onRefresh={vi.fn()}
            />
        )

        await user.click(screen.getByRole('checkbox', { name: 'F1' }))
        expect(onChange).toHaveBeenCalledWith({
            ...emptyFilters,
            visa_types: ['F1']
        })
    })

    it('点击清空本组应移除该组已选领馆', async () => {
        const onChange = vi.fn()
        const user = userEvent.setup()

        render(
            <FilterBar
                options={options}
                consulateGroups={groups}
                filters={{ ...emptyFilters, consulates: ['BeiJing', 'Toronto'] }}
                refreshFromMonth=""
                refreshSources={['monthly_track']}
                availableRefreshSources={options.fetch_sources}
                defaultRefreshMonths={6}
                showConsulateGroups={true}
                isRefreshing={false}
                refreshFeedback={null}
                onRefreshFromMonthChange={vi.fn()}
                onRefreshSourcesChange={vi.fn()}
                onChange={onChange}
                onReset={vi.fn()}
                onRefresh={vi.fn()}
            />
        )

        await user.click(screen.getAllByRole('button', { name: '清空本组' })[0])
        expect(onChange).toHaveBeenCalledWith({
            ...emptyFilters,
            consulates: ['Toronto']
        })
    })
})
