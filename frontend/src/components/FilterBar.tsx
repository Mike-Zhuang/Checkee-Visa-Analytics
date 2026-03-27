import type { ConsulateGroup, Filters, OptionsResponse, RefreshPayload } from '../types'

type Props = {
    options: OptionsResponse
    consulateGroups: ConsulateGroup[]
    filters: Filters
    refreshFromMonth: string
    onRefreshFromMonthChange: (value: string) => void
    onChange: (next: Filters) => void
    onReset: () => void
    onRefresh: (payload: RefreshPayload) => void
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

function toggleValue(values: string[], value: string): string[] {
    if (values.includes(value)) {
        return values.filter((v) => v !== value)
    }
    return [...values, value]
}

export default function FilterBar({
    options,
    consulateGroups,
    filters,
    refreshFromMonth,
    onRefreshFromMonthChange,
    onChange,
    onReset,
    onRefresh
}: Props) {
    const chips = [
        ...filters.visa_types.map((v) => ({ field: 'visa_types' as const, value: v, label: `签证:${v}` })),
        ...filters.months.map((v) => ({ field: 'months' as const, value: v, label: `月份:${v}` })),
        ...filters.consulates.map((v) => ({ field: 'consulates' as const, value: v, label: `领馆:${v}` })),
        ...filters.statuses.map((v) => ({ field: 'statuses' as const, value: v, label: `状态:${v}` })),
        ...filters.entries.map((v) => ({ field: 'entries' as const, value: v, label: `条目:${v}` }))
    ]

    const removeChip = (field: keyof Filters, value: string) => {
        onChange({ ...filters, [field]: filters[field].filter((x) => x !== value) })
    }

    const applyRecentMonths = (count: number) => {
        onChange({ ...filters, months: options.months.slice(0, count) })
    }

    const toggleConsulateGroup = (group: ConsulateGroup) => {
        const allSelected = group.consulates.every((c) => filters.consulates.includes(c))
        if (allSelected) {
            onChange({ ...filters, consulates: filters.consulates.filter((c) => !group.consulates.includes(c)) })
            return
        }
        const merged = new Set([...filters.consulates, ...group.consulates])
        onChange({ ...filters, consulates: Array.from(merged) })
    }

    return (
        <section className="filter-card">
            <h3>筛选条件</h3>
            <p className="hint">可多选；按住 Command 可快速多选。支持按起始月份向前抓取更多历史数据。</p>

            <div className="refresh-row">
                <label className="field field-inline">
                    <span>抓取起始月份</span>
                    <input
                        type="month"
                        value={refreshFromMonth}
                        onChange={(e) => onRefreshFromMonthChange(e.currentTarget.value)}
                    />
                </label>
                <div className="actions compact">
                    <button
                        onClick={() =>
                            onRefresh({
                                all_months: false,
                                months: 6,
                                from_month: refreshFromMonth || null
                            })
                        }
                    >
                        刷新数据
                    </button>
                    <button className="ghost" onClick={onReset}>重置筛选</button>
                </div>
            </div>

            <div className="chip-row">
                {chips.length === 0 ? <span className="chip empty">当前无筛选条件</span> : null}
                {chips.map((chip) => (
                    <button
                        key={`${chip.field}-${chip.value}`}
                        className="chip"
                        onClick={() => removeChip(chip.field, chip.value)}
                        title="点击移除"
                    >
                        {chip.label} ×
                    </button>
                ))}
            </div>

            <div className="filter-grid">
                <MultiSelect label="签证类型" values={options.visa_types} selected={filters.visa_types} onPick={(v) => onChange({ ...filters, visa_types: v })} />
                <label className="field">
                    <span>月份</span>
                    <select
                        multiple
                        value={filters.months}
                        onChange={(e) => {
                            const next = Array.from(e.currentTarget.selectedOptions).map((o) => o.value)
                            onChange({ ...filters, months: next })
                        }}
                    >
                        {options.months.map((v) => (
                            <option key={v} value={v}>{v}</option>
                        ))}
                    </select>
                    <div className="quick-actions">
                        <button className="ghost" onClick={() => applyRecentMonths(3)}>最近3月</button>
                        <button className="ghost" onClick={() => applyRecentMonths(6)}>最近6月</button>
                        <button className="ghost" onClick={() => applyRecentMonths(12)}>最近12月</button>
                    </div>
                </label>
                <MultiSelect label="状态" values={options.statuses} selected={filters.statuses} onPick={(v) => onChange({ ...filters, statuses: v })} />
                <MultiSelect label="签证条目" values={options.entries} selected={filters.entries} onPick={(v) => onChange({ ...filters, entries: v })} />
            </div>

            <div className="consulate-section">
                <h4>领馆（按国家/地区分组）</h4>
                <div className="consulate-groups">
                    {consulateGroups.map((group) => (
                        <div className="consulate-group" key={group.key}>
                            <div className="consulate-group-title">
                                <strong>{group.label}</strong>
                                <button className="ghost" onClick={() => toggleConsulateGroup(group)}>整组切换</button>
                            </div>
                            <div className="consulate-items">
                                {group.consulates.map((city) => (
                                    <label key={city} className="consulate-item">
                                        <input
                                            type="checkbox"
                                            checked={filters.consulates.includes(city)}
                                            onChange={() => onChange({ ...filters, consulates: toggleValue(filters.consulates, city) })}
                                        />
                                        <span>{city}</span>
                                    </label>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    )
}
