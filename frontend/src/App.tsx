import { useEffect, useMemo, useState } from 'react'
import {
    exportCasesUrl,
    exportReportUrl,
    getCases,
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
import type { CaseItem, Filters, MonthlyItem, OptionsResponse, OverviewStats, SensitivityItem } from './types'

const EMPTY_FILTERS: Filters = {
    visa_types: [],
    consulates: [],
    statuses: [],
    entries: [],
    months: []
}

export default function App() {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
    const [options, setOptions] = useState<OptionsResponse>({
        months: [],
        visa_types: [],
        consulates: [],
        statuses: [],
        entries: []
    })
    const [overview, setOverview] = useState<OverviewStats | null>(null)
    const [monthly, setMonthly] = useState<MonthlyItem[]>([])
    const [sensitivity, setSensitivity] = useState<SensitivityItem[]>([])
    const [cases, setCases] = useState<CaseItem[]>([])
    const [caseTotal, setCaseTotal] = useState(0)

    const fetchAll = async () => {
        setLoading(true)
        setError('')
        try {
            const [ov, mo, se, ca] = await Promise.all([
                getOverview(filters),
                getMonthly(filters),
                getSensitivity(filters),
                getCases(filters, 300)
            ])
            setOverview(ov)
            setMonthly(mo)
            setSensitivity(se)
            setCases(ca.items)
            setCaseTotal(ca.total)
        } catch (e) {
            setError((e as Error).message)
        } finally {
            setLoading(false)
        }
    }

    const init = async () => {
        setLoading(true)
        setError('')
        try {
            const op = await getOptions()
            setOptions(op)
            await fetchAll()
        } catch (e) {
            setError((e as Error).message)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        void init()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    useEffect(() => {
        if (!options.months.length) return
        void fetchAll()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filters])

    const onRefresh = async () => {
        setLoading(true)
        setError('')
        try {
            await refreshData(false, 6)
            const op = await getOptions()
            setOptions(op)
            await fetchAll()
        } catch (e) {
            setError((e as Error).message)
        } finally {
            setLoading(false)
        }
    }

    const reportLink = useMemo(() => exportReportUrl(filters), [filters])
    const casesLink = useMemo(() => exportCasesUrl(filters), [filters])

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

            {error ? <div className="error-box">{error}</div> : null}
            {loading ? <div className="loading">加载中...</div> : null}

            <FilterBar
                options={options}
                filters={filters}
                onChange={setFilters}
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
            <CaseTable rows={cases} total={caseTotal} />
        </main>
    )
}
