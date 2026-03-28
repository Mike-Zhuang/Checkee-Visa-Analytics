import type { ConsulateGroup, Filters, OptionsResponse, RefreshPayload } from '../types'
import { useTranslation } from 'react-i18next'

type Props = {
    options: OptionsResponse
    consulateGroups: ConsulateGroup[]
    filters: Filters
    refreshFromMonth: string
    refreshSources: string[]
    availableRefreshSources: string[]
    defaultRefreshMonths: number
    showConsulateGroups: boolean
    onRefreshFromMonthChange: (value: string) => void
    onRefreshSourcesChange: (value: string[]) => void
    onChange: (next: Filters) => void
    onReset: () => void
    onRefresh: (payload: RefreshPayload) => void
}

function MultiSelect({
    id,
    label,
    values,
    selected,
    onPick
}: {
    id: string
    label: string
    values: string[]
    selected: string[]
    onPick: (v: string[]) => void
}) {
    return (
        <label className="field" htmlFor={id}>
            <span id={`${id}-label`}>{label}</span>
            <select
                id={id}
                multiple
                value={selected}
                aria-labelledby={`${id}-label`}
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
    refreshSources,
    availableRefreshSources,
    defaultRefreshMonths,
    showConsulateGroups,
    onRefreshFromMonthChange,
    onRefreshSourcesChange,
    onChange,
    onReset,
    onRefresh
}: Props) {
    const { t } = useTranslation()

    const chips = [
        ...filters.visa_types.map((v) => ({ field: 'visa_types' as const, value: v, label: t('filter.chipVisa', { value: v }) })),
        ...filters.months.map((v) => ({ field: 'months' as const, value: v, label: t('filter.chipMonth', { value: v }) })),
        ...filters.consulates.map((v) => ({ field: 'consulates' as const, value: v, label: t('filter.chipConsulate', { value: v }) })),
        ...filters.statuses.map((v) => ({ field: 'statuses' as const, value: v, label: t('filter.chipStatus', { value: v }) })),
        ...filters.entries.map((v) => ({ field: 'entries' as const, value: v, label: t('filter.chipEntry', { value: v }) }))
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
        <section className="filter-card" role="region" aria-labelledby="filters-title">
            <h3 id="filters-title">{t('filter.title')}</h3>
            <p className="hint" id="filters-hint">{t('filter.hint')}</p>

            <div className="refresh-row">
                <label className="field field-inline" htmlFor="refresh-from-month">
                    <span>{t('filter.refreshFromMonth')}</span>
                    <input
                        id="refresh-from-month"
                        type="month"
                        value={refreshFromMonth}
                        aria-describedby="filters-hint"
                        onChange={(e) => onRefreshFromMonthChange(e.currentTarget.value)}
                    />
                </label>
                <label className="field field-inline" htmlFor="refresh-sources">
                    <span>{t('filter.refreshSources')}</span>
                    <select
                        id="refresh-sources"
                        multiple
                        value={refreshSources}
                        onChange={(e) => {
                            const next = Array.from(e.currentTarget.selectedOptions).map((o) => o.value)
                            onRefreshSourcesChange(next)
                        }}
                    >
                        {availableRefreshSources.map((source) => (
                            <option key={source} value={source}>{source}</option>
                        ))}
                    </select>
                </label>
                <div className="actions compact">
                    <button
                        type="button"
                        disabled={refreshSources.length === 0}
                        onClick={() =>
                            onRefresh({
                                all_months: false,
                                months: defaultRefreshMonths,
                                from_month: refreshFromMonth || null,
                                sources: refreshSources
                            })
                        }
                    >
                        {t('filter.refresh')}
                    </button>
                    <button type="button" className="ghost" onClick={onReset}>{t('filter.reset')}</button>
                </div>
            </div>

            <div className="chip-row" aria-live="polite">
                {chips.length === 0 ? <span className="chip empty" role="status">{t('filter.noChips')}</span> : null}
                {chips.map((chip) => (
                    <button
                        type="button"
                        key={`${chip.field}-${chip.value}`}
                        className="chip"
                        onClick={() => removeChip(chip.field, chip.value)}
                        aria-label={`${t('filter.removeChip')}: ${chip.label}`}
                        title={t('filter.removeChip')}
                    >
                        {chip.label} ×
                    </button>
                ))}
            </div>

            <div className="filter-grid">
                <MultiSelect
                    id="filter-visa-types"
                    label={t('filter.visaTypes')}
                    values={options.visa_types}
                    selected={filters.visa_types}
                    onPick={(v) => onChange({ ...filters, visa_types: v })}
                />
                <label className="field" htmlFor="filter-months">
                    <span id="filter-months-label">{t('filter.months')}</span>
                    <select
                        id="filter-months"
                        multiple
                        value={filters.months}
                        aria-labelledby="filter-months-label"
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
                        <button type="button" className="ghost" onClick={() => applyRecentMonths(3)}>{t('filter.quick3')}</button>
                        <button type="button" className="ghost" onClick={() => applyRecentMonths(6)}>{t('filter.quick6')}</button>
                        <button type="button" className="ghost" onClick={() => applyRecentMonths(12)}>{t('filter.quick12')}</button>
                    </div>
                </label>
                <MultiSelect
                    id="filter-statuses"
                    label={t('filter.statuses')}
                    values={options.statuses}
                    selected={filters.statuses}
                    onPick={(v) => onChange({ ...filters, statuses: v })}
                />
                <MultiSelect
                    id="filter-entries"
                    label={t('filter.entries')}
                    values={options.entries}
                    selected={filters.entries}
                    onPick={(v) => onChange({ ...filters, entries: v })}
                />
                {!showConsulateGroups ? (
                    <MultiSelect
                        id="filter-consulates"
                        label={t('filter.consulates')}
                        values={options.consulates}
                        selected={filters.consulates}
                        onPick={(v) => onChange({ ...filters, consulates: v })}
                    />
                ) : null}
            </div>

            {showConsulateGroups ? (
                <div className="consulate-section">
                    <h4>{t('filter.groupedConsulates')}</h4>
                    <div className="consulate-groups">
                        {consulateGroups.map((group) => (
                            <fieldset className="consulate-group" key={group.key}>
                                <div className="consulate-group-title">
                                    <legend>{group.label}</legend>
                                    <button type="button" className="ghost" onClick={() => toggleConsulateGroup(group)}>
                                        {t('filter.toggleGroup')}
                                    </button>
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
                            </fieldset>
                        ))}
                    </div>
                </div>
            ) : null}
        </section>
    )
}
