import { useEffect, useMemo, useState } from 'react'
import {
    exportCasesUrl,
    exportReportUrl,
    getCases,
    getConsulateGroups,
    getMetaState,
    getMonthly,
    getOptions,
    getOverview,
    getSensitivity,
    refreshData
} from './api'
import CaseTable from './components/CaseTable'
import FilterBar from './components/FilterBar'
import MonthlyChart from './components/MonthlyChart'
import SensitivityTable from './components/SensitivityTable'
import StatCards from './components/StatCards'
import type {
    CaseItem,
    ConsulateGroup,
    Filters,
    MetaState,
    MonthlyItem,
    OptionsResponse,
    OverviewStats,
    RefreshPayload,
    SensitivityItem
} from './types'

const EMPTY_FILTERS: Filters = {
    visa_types: [],
    consulates: [],
    statuses: [],
    entries: [],
    months: []
}

export default function App() {
    const [initialized, setInitialized] = useState(false)
    const [overviewLoading, setOverviewLoading] = useState(false)
    const [casesLoading, setCasesLoading] = useState(false)
    const [errors, setErrors] = useState<string[]>([])
    const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
    const [refreshFromMonth, setRefreshFromMonth] = useState('')
    const [options, setOptions] = useState<OptionsResponse>({
        months: [],
        visa_types: [],
        consulates: [],
        statuses: [],
        entries: []
    })
    const [consulateGroups, setConsulateGroups] = useState<ConsulateGroup[]>([])
    const [metaState, setMetaState] = useState<MetaState | null>(null)
    const [overview, setOverview] = useState<OverviewStats | null>(null)
    const [monthly, setMonthly] = useState<MonthlyItem[]>([])
    const [sensitivity, setSensitivity] = useState<SensitivityItem[]>([])
    const [cases, setCases] = useState<CaseItem[]>([])
    const [caseTotal, setCaseTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(50)

    const fetchOverviewBundle = async (activeFilters: Filters) => {
        setOverviewLoading(true)
        const localErrors: string[] = []

        const [overviewRes, monthlyRes, sensitivityRes, stateRes] = await Promise.allSettled([
            getOverview(activeFilters),
            getMonthly(activeFilters),
            getSensitivity(activeFilters),
            getMetaState()
        ])

        if (overviewRes.status === 'fulfilled') {
            setOverview(overviewRes.value)
        } else {
            localErrors.push(`概览加载失败: ${overviewRes.reason}`)
        }

        if (monthlyRes.status === 'fulfilled') {
            setMonthly(monthlyRes.value)
        } else {
            localErrors.push(`月度统计加载失败: ${monthlyRes.reason}`)
        }

        if (sensitivityRes.status === 'fulfilled') {
            setSensitivity(sensitivityRes.value)
        } else {
            localErrors.push(`敏感性分析加载失败: ${sensitivityRes.reason}`)
        }

        if (stateRes.status === 'fulfilled') {
            setMetaState(stateRes.value)
        } else {
            localErrors.push(`状态信息加载失败: ${stateRes.reason}`)
        }

        setErrors((prev) => [...prev.filter((x) => !x.includes('概览') && !x.includes('月度') && !x.includes('敏感性') && !x.includes('状态信息')), ...localErrors])
        setOverviewLoading(false)
    }

    const fetchCasesPage = async (activeFilters: Filters, nextPage: number, nextPageSize: number) => {
        setCasesLoading(true)
        try {
            const offset = (nextPage - 1) * nextPageSize
            const ca = await getCases(activeFilters, nextPageSize, offset)
            setCases(ca.items)
            setCaseTotal(ca.total)
            setErrors((prev) => prev.filter((x) => !x.includes('案例明细')))
        } catch (e) {
            setErrors((prev) => [...prev.filter((x) => !x.includes('案例明细')), `案例明细加载失败: ${(e as Error).message}`])
        } finally {
            setCasesLoading(false)
        }
    }

    const fetchMetaOptions = async () => {
        const [optionsRes, groupsRes, stateRes] = await Promise.allSettled([
            getOptions(),
            getConsulateGroups(),
            getMetaState()
        ])

        const localErrors: string[] = []
        if (optionsRes.status === 'fulfilled') {
            setOptions(optionsRes.value)
        } else {
            localErrors.push(`筛选项加载失败: ${optionsRes.reason}`)
        }

        if (groupsRes.status === 'fulfilled') {
            setConsulateGroups(groupsRes.value.groups)
        } else {
            localErrors.push(`领馆分组加载失败: ${groupsRes.reason}`)
        }

        if (stateRes.status === 'fulfilled') {
            setMetaState(stateRes.value)
        }

        setErrors((prev) => [...prev.filter((x) => !x.includes('筛选项') && !x.includes('领馆分组')), ...localErrors])
    }

    const init = async () => {
        setErrors([])
        await fetchMetaOptions()
        await fetchOverviewBundle(filters)
        await fetchCasesPage(filters, 1, pageSize)
        setInitialized(true)
    }

    useEffect(() => {
        void init()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    useEffect(() => {
        if (!initialized) return
        setPage(1)
        void fetchOverviewBundle(filters)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filters])

    useEffect(() => {
        if (!initialized) return
        void fetchCasesPage(filters, page, pageSize)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filters, page, pageSize, initialized])

    const onRefresh = async (payload: RefreshPayload) => {
        try {
            await refreshData(payload)
            await fetchMetaOptions()
            setPage(1)
            await fetchOverviewBundle(filters)
            await fetchCasesPage(filters, 1, pageSize)
        } catch (e) {
            setErrors((prev) => [...prev, `刷新失败: ${(e as Error).message}`])
        }
    }

    const onFilterChange = (next: Filters) => {
        setFilters(next)
    }

    const reportLink = useMemo(() => exportReportUrl(filters), [filters])
    const casesLink = useMemo(() => exportCasesUrl(filters), [filters])

    const freshnessHint = useMemo(() => {
        if (!metaState?.updated_at) return '尚无刷新记录'
        const fresh = metaState.data_freshness_seconds
        if (fresh == null) return `更新时间: ${metaState.updated_at}`
        return `更新时间: ${metaState.updated_at}（距今约 ${Math.floor(fresh / 60)} 分钟）`
    }, [metaState])

    return (
        <main className="app-shell">
            <header className="hero">
                <div>
                    <h1>Checkee Visa Analytics</h1>
                    <p>全签证类型实时分析平台 · 前后端分离 MVP</p>
                </div>
                <div className="hero-actions">
                    <a href={reportLink} target="_blank" rel="noreferrer">导出报告</a>
                    <a href={casesLink} target="_blank" rel="noreferrer">导出CSV</a>
                </div>
            </header>

            <section className="meta-strip">
                <span>{freshnessHint}</span>
                <span>样本数: {metaState?.current_case_count ?? 0}</span>
                <span>抓取范围: {metaState?.fetched_month_range?.earliest ?? '-'} ~ {metaState?.fetched_month_range?.latest ?? '-'}</span>
                {metaState?.truncated_by_limit ? <span className="warn">已触发月份上限: {metaState.month_limit}</span> : null}
            </section>

            {errors.length > 0 ? <div className="error-box">{errors.join(' | ')}</div> : null}
            {(overviewLoading || casesLoading) ? <div className="loading">加载中... {overviewLoading ? '统计模块 ' : ''}{casesLoading ? '明细模块' : ''}</div> : null}

            <FilterBar
                options={options}
                consulateGroups={consulateGroups}
                filters={filters}
                refreshFromMonth={refreshFromMonth}
                onRefreshFromMonthChange={setRefreshFromMonth}
                onChange={onFilterChange}
                onReset={() => setFilters(EMPTY_FILTERS)}
                onRefresh={onRefresh}
            />

            <StatCards data={overview} />
            <MonthlyChart
                data={monthly}
                onSelectMonth={(month) => {
                    setFilters((old) => ({ ...old, months: [month] }))
                }}
            />
            <SensitivityTable rows={sensitivity} />
            <CaseTable
                rows={cases}
                total={caseTotal}
                page={page}
                pageSize={pageSize}
                onPageChange={(next) => setPage(Math.max(1, next))}
                onPageSizeChange={(size) => {
                    setPage(1)
                    setPageSize(size)
                }}
            />
        </main>
    )
}
