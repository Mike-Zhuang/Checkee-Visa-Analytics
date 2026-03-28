import { render, screen, waitFor } from '@testing-library/react'
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
    major_categories_l1: ['STEM', 'Business'],
    major_categories_l2: ['AI & Data', 'Engineering', 'Finance & Accounting'],
    major_category_mapping: {
        STEM: ['AI & Data', 'Engineering'],
        Business: ['Finance & Accounting']
    },
    majors: ['CS', 'Math'],
    employers: ['Google', 'Amazon'],
    detail_cities: ['Beijing', 'Toronto'],
    detail_states: ['Beijing', 'Ontario'],
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
    months: [],
    major_categories_l1: [],
    major_categories_l2: [],
    majors: [],
    employers: [],
    detail_cities: [],
    detail_states: [],
    search_text: ''
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

    it('点击月份胶囊应触发 months 更新', async () => {
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

        await user.click(screen.getByRole('button', { name: '2026-03' }))
        expect(onChange).toHaveBeenCalledWith({
            ...emptyFilters,
            months: ['2026-03']
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

    it('公开只读模式下不显示刷新按钮', () => {
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
                showRefreshControls={false}
                isRefreshing={false}
                refreshFeedback={null}
                onRefreshFromMonthChange={vi.fn()}
                onRefreshSourcesChange={vi.fn()}
                onChange={vi.fn()}
                onReset={vi.fn()}
                onRefresh={vi.fn()}
            />
        )

        expect(screen.queryByRole('button', { name: '开始刷新数据' })).not.toBeInTheDocument()
        expect(screen.getByRole('button', { name: '重置筛选' })).toBeInTheDocument()
    })

    it('点击专业一级胶囊应触发 major_categories_l1 更新', async () => {
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

        await user.click(screen.getByRole('button', { name: 'STEM' }))
        expect(onChange).toHaveBeenCalledWith({
            ...emptyFilters,
            major_categories_l1: ['STEM'],
            major_categories_l2: []
        })
    })

    it('点击雇主胶囊应触发 employers 更新', async () => {
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

        await user.click(screen.getByRole('button', { name: 'Google' }))
        expect(onChange).toHaveBeenCalledWith({
            ...emptyFilters,
            employers: ['Google']
        })
    })

    it('一级分类变化后应自动清理无效二级分类', async () => {
        const onChange = vi.fn()

        render(
            <FilterBar
                options={options}
                consulateGroups={groups}
                filters={{ ...emptyFilters, major_categories_l1: ['Business'], major_categories_l2: ['Engineering'] }}
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

        await waitFor(() => {
            expect(onChange).toHaveBeenCalledWith({
                ...emptyFilters,
                major_categories_l1: ['Business'],
                major_categories_l2: []
            })
        })
    })

    it('输入文本搜索应触发 search_text 更新', async () => {
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

        await user.type(screen.getByPlaceholderText('例如：amazon cleared'), 'amazon')
        expect(onChange).toHaveBeenCalled()
        const latestCallIndex = onChange.mock.calls.length - 1
        const latestPayload = latestCallIndex >= 0 ? onChange.mock.calls[latestCallIndex][0] : null
        expect(latestPayload).toEqual({
            ...emptyFilters,
            search_text: 'n'
        })
    })
})
