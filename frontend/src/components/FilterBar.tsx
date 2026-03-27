import type { Filters, OptionsResponse } from '../types'

type Props = {
    options: OptionsResponse
    filters: Filters
    onChange: (next: Filters) => void
    onReset: () => void
    onRefresh: () => void
}

function MultiSelect({
    label,
    values,
    selected,
    onPick
}: {
    label: string
    values: string[]
    selected: string[]
    onPick: (v: string[]) => void
}) {
    return (
        <label className="field">
            <span>{label}</span>
            <select
                multiple
                value={selected}
                onChange={(e) => {
                    const next = Array.from(e.currentTarget.selectedOptions).map((o) => o.value)
                    onPick(next)
                }}
            >
                {values.map((v) => (
                    <option key={v} value={v}>{v}</option>
                ))}
            </select>
        </label>
    )
}

export default function FilterBar({ options, filters, onChange, onReset, onRefresh }: Props) {
    return (
        <section className="filter-card">
            <h3>筛选条件</h3>
            <p className="hint">可多选；按住 Command 可快速多选。</p>
            <div className="filter-grid">
                <MultiSelect label="签证类型" values={options.visa_types} selected={filters.visa_types} onPick={(v) => onChange({ ...filters, visa_types: v })} />
                <MultiSelect label="月份" values={options.months} selected={filters.months} onPick={(v) => onChange({ ...filters, months: v })} />
                <MultiSelect label="领馆" values={options.consulates} selected={filters.consulates} onPick={(v) => onChange({ ...filters, consulates: v })} />
                <MultiSelect label="状态" values={options.statuses} selected={filters.statuses} onPick={(v) => onChange({ ...filters, statuses: v })} />
                <MultiSelect label="签证条目" values={options.entries} selected={filters.entries} onPick={(v) => onChange({ ...filters, entries: v })} />
            </div>
            <div className="actions">
                <button onClick={onRefresh}>刷新数据</button>
                <button className="ghost" onClick={onReset}>重置筛选</button>
            </div>
        </section>
    )
}
