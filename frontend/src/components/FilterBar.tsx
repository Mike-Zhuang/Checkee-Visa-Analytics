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
    isRefreshing: boolean
    refreshFeedback: { kind: 'success' | 'error'; message: string } | null
    onRefreshFromMonthChange: (value: string) => void
    onRefreshSourcesChange: (value: string[]) => void
    onChange: (next: Filters) => void
    onReset: () => void
    onRefresh: (payload: RefreshPayload) => void
}

function MultiSelect({
    id,
    label,
    hint,
    values,
    selected,
    onPick
}: {
    id: string
    label: string
    hint?: string
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
            {hint ? <small className="field-help">{hint}</small> : null}
        </label>
    )
}

function CheckboxGroup({
    title,
    hint,
    values,
    selected,
    onPick,
    onClear,
    clearText
}: {
    title: string
    hint?: string
    values: string[]
    selected: string[]
    onPick: (v: string[]) => void
    onClear?: () => void
    clearText?: string
}) {
    return (
        <div className="field checkbox-group">
            <div className="checkbox-group-head">
                <span>{title}</span>
                {onClear ? (
                    <button type="button" className="ghost mini" onClick={onClear} disabled={selected.length === 0}>
                        {clearText ?? 'Clear'}
                    </button>
                ) : null}
            </div>
            <div className="checkbox-list">
                {values.map((value) => {
                    const checked = selected.includes(value)
                    return (
                        <label key={value} className="checkbox-item">
                            <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => {
                                    if (checked) {
                                        onPick(selected.filter((item) => item !== value))
                                    } else {
                                        onPick([...selected, value])
                                    }
                                }}
                            />
                            <span>{value}</span>
                        </label>
                    )
                })}
            </div>
            {hint ? <small className="field-help">{hint}</small> : null}
        </div>
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
    isRefreshing,
    refreshFeedback,
    onRefreshFromMonthChange,
    onRefreshSourcesChange,
    onChange,
    onReset,
    onRefresh
}: Props) {
    const { t } = useTranslation()

    const sourceMeta = availableRefreshSources.map((source) => {
        if (source === 'monthly_track') {
            return {
                key: source,
                label: t('filter.sourceMonthlyLabel'),
                desc: t('filter.sourceMonthlyDesc')
            }
        }
        if (source === 'latest_snapshot') {
            return {
                key: source,
                label: t('filter.sourceLatestLabel'),
                desc: t('filter.sourceLatestDesc')
            }
        }
        return {
            key: source,
            label: source,
            desc: t('filter.sourceUnknownDesc')
        }
    })

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

    const clearConsulateGroup = (group: ConsulateGroup) => {
        onChange({
            ...filters,
            consulates: filters.consulates.filter((city) => !group.consulates.includes(city))
        })
    }

    const toggleRefreshSource = (source: string) => {
        const next = refreshSources.includes(source)
            ? refreshSources.filter((item) => item !== source)
            : [...refreshSources, source]
        onRefreshSourcesChange(next)
    }

    return (
        <section className="filter-card" role="region" aria-labelledby="filters-title">
            <h3 id="filters-title">{t('filter.title')}</h3>
            <div className="hint-list" id="filters-hint">
                <p>{t('filter.hintSelect')}</p>
                <p>{t('filter.hintEmptyMeansAll')}</p>
                <p>{t('filter.hintHistory')}</p>
            </div>

            <div className="refresh-row">
                <label className="field field-inline" htmlFor="refresh-from-month">
                    <span>{t('filter.refreshFromMonth')}</span>
                    <input
                        id="refresh-from-month"
                        type="month"
                        value={refreshFromMonth}
                        aria-describedby="filters-hint"
                        disabled={isRefreshing}
                        onChange={(e) => onRefreshFromMonthChange(e.currentTarget.value)}
                    />
                    <small className="field-help">
                        {t('filter.refreshFromMonthHelp', { months: defaultRefreshMonths })}
                    </small>
                </label>

                <fieldset className="refresh-sources-panel" aria-describedby="filters-hint">
                    <span>{t('filter.refreshSources')}</span>
                    <small className="field-help">{t('filter.refreshSourcesHelp')}</small>
                    <div className="source-options">
                        {sourceMeta.map((source) => (
                            <label className="source-option" key={source.key}>
                                <input
                                    type="checkbox"
                                    checked={refreshSources.includes(source.key)}
                                    disabled={isRefreshing}
                                    onChange={() => toggleRefreshSource(source.key)}
                                />
                                <span className="source-title">{source.label}</span>
                                <small className="source-desc">{source.desc}</small>
                            </label>
                        ))}
                    </div>
                </fieldset>

                <div className="actions compact">
                    <button
                        type="button"
                        disabled={isRefreshing || refreshSources.length === 0}
                        onClick={() =>
                            onRefresh({
                                all_months: false,
                                months: defaultRefreshMonths,
                                from_month: refreshFromMonth || null,
                                sources: refreshSources
                            })
                        }
                    >
                        {isRefreshing ? t('filter.refreshing') : t('filter.refresh')}
                    </button>
                    <button type="button" className="ghost" disabled={isRefreshing} onClick={onReset}>{t('filter.reset')}</button>
                </div>
            </div>

            {refreshFeedback ? (
                <div className={`refresh-feedback ${refreshFeedback.kind}`} role="status" aria-live="polite">
                    {refreshFeedback.message}
                </div>
            ) : null}

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
                {!showConsulateGroups ? (
                    <CheckboxGroup
                        title={t('filter.visaTypes')}
                        hint={t('filter.visaTypesHint')}
                        values={options.visa_types}
                        selected={filters.visa_types}
                        onPick={(v) => onChange({ ...filters, visa_types: v })}
                        onClear={() => onChange({ ...filters, visa_types: [] })}
                        clearText={t('filter.clearOne')}
                    />
                ) : null}
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
                    <small className="field-help">{t('filter.monthsHint')}</small>
                </label>
                <CheckboxGroup
                    title={t('filter.statuses')}
                    hint={t('filter.statusesHint')}
                    values={options.statuses}
                    selected={filters.statuses}
                    onPick={(v) => onChange({ ...filters, statuses: v })}
                    onClear={() => onChange({ ...filters, statuses: [] })}
                    clearText={t('filter.clearOne')}
                />
                <CheckboxGroup
                    title={t('filter.entries')}
                    hint={t('filter.entriesHint')}
                    values={options.entries}
                    selected={filters.entries}
                    onPick={(v) => onChange({ ...filters, entries: v })}
                    onClear={() => onChange({ ...filters, entries: [] })}
                    clearText={t('filter.clearOne')}
                />
                {!showConsulateGroups ? (
                    <CheckboxGroup
                        title={t('filter.consulates')}
                        hint={t('filter.consulatesHint')}
                        values={options.consulates}
                        selected={filters.consulates}
                        onPick={(v) => onChange({ ...filters, consulates: v })}
                        onClear={() => onChange({ ...filters, consulates: [] })}
                        clearText={t('filter.clearOne')}
                    />
                ) : null}
            </div>

            {showConsulateGroups ? (
                <div className="consulate-section">
                    <h4>{t('filter.groupedConsulates')}</h4>
                    <CheckboxGroup
                        title={t('filter.visaTypes')}
                        hint={t('filter.visaTypesHint')}
                        values={options.visa_types}
                        selected={filters.visa_types}
                        onPick={(v) => onChange({ ...filters, visa_types: v })}
                        onClear={() => onChange({ ...filters, visa_types: [] })}
                        clearText={t('filter.clearOne')}
                    />
                    <div className="consulate-groups">
                        {consulateGroups.map((group) => (
                            <fieldset className="consulate-group" key={group.key}>
                                <div className="consulate-group-title">
                                    <legend>{t(`filter.groupName.${group.key}`, { defaultValue: group.label })}</legend>
                                    <div className="consulate-group-actions">
                                        <button type="button" className="ghost mini" onClick={() => toggleConsulateGroup(group)}>
                                            {t('filter.toggleGroup')}
                                        </button>
                                        <button type="button" className="ghost mini" onClick={() => clearConsulateGroup(group)}>
                                            {t('filter.clearGroup')}
                                        </button>
                                    </div>
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
