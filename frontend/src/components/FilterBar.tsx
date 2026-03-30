import { useEffect, useMemo } from 'react'
import type { ReactNode } from 'react'
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
    showRefreshControls?: boolean
    isRefreshing: boolean
    refreshFeedback: { kind: 'success' | 'error'; message: string } | null
    onRefreshFromMonthChange: (value: string) => void
    onRefreshSourcesChange: (value: string[]) => void
    onChange: (next: Filters) => void
    onApply: () => void
    hasPendingChanges: boolean
    onReset: () => void
    onRefresh: (payload: RefreshPayload) => void
}

function PillMultiSelect({
    id,
    label,
    hint,
    values,
    selected,
    onPick,
    onClear,
    clearText,
    className,
    emptyLabel,
    listClassName,
    footer
}: {
    id: string
    label: string
    hint?: string
    values: string[]
    selected: string[]
    onPick: (v: string[]) => void
    onClear?: () => void
    clearText?: string
    className?: string
    emptyLabel?: string
    listClassName?: string
    footer?: ReactNode
}) {
    const selectedSet = new Set(selected)
    return (
        <div className={`field pill-multi ${className ?? ''}`.trim()} role="group" aria-labelledby={`${id}-label`}>
            <div className="field-head">
                <span id={`${id}-label`}>{label}</span>
                <div className="field-head-meta">
                    <small>{selected.length}/{values.length}</small>
                    {onClear ? (
                        <button type="button" className="ghost mini" onClick={onClear} disabled={selected.length === 0}>
                            {clearText ?? 'Clear'}
                        </button>
                    ) : null}
                </div>
            </div>
            <div className={`pill-list ${listClassName ?? ''}`.trim()} role="listbox" aria-multiselectable="true" aria-labelledby={`${id}-label`}>
                {values.length === 0 ? (
                    <span className="pill-empty">{emptyLabel ?? '-'}</span>
                ) : (
                    values.map((value) => {
                        const isActive = selectedSet.has(value)
                        return (
                            <button
                                key={value}
                                type="button"
                                className={`pill-item ${isActive ? 'active' : ''}`}
                                aria-pressed={isActive}
                                onClick={() => onPick(toggleValue(selected, value))}
                            >
                                {value}
                            </button>
                        )
                    })
                )}
            </div>
            {footer ? <div className="pill-footer">{footer}</div> : null}
            {hint ? <small className="field-help">{hint}</small> : null}
        </div>
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
    showRefreshControls = true,
    isRefreshing,
    refreshFeedback,
    onRefreshFromMonthChange,
    onRefreshSourcesChange,
    onChange,
    onApply,
    hasPendingChanges,
    onReset,
    onRefresh
}: Props) {
    const { t } = useTranslation()
    const titleText = showRefreshControls ? t('filter.title') : t('filter.titleReadonly')

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

    const resolveLinkedMajorCategoryL2 = (selectedL1: string[]): string[] => {
        if (selectedL1.length === 0) {
            return options.major_categories_l2
        }

        const merged = new Set<string>()
        let hasUnmapped = false

        for (const categoryL1 of selectedL1) {
            const mapped = options.major_category_mapping[categoryL1] ?? []
            if (mapped.length === 0) {
                hasUnmapped = true
                continue
            }
            for (const categoryL2 of mapped) {
                merged.add(categoryL2)
            }
        }

        if (hasUnmapped || merged.size === 0) {
            return options.major_categories_l2
        }

        return options.major_categories_l2.filter((categoryL2) => merged.has(categoryL2))
    }

    const majorCategoryL2Options = useMemo(
        () => resolveLinkedMajorCategoryL2(filters.major_categories_l1),
        [filters.major_categories_l1, options.major_categories_l2, options.major_category_mapping]
    )
    const majorCategoryL2OptionSet = useMemo(() => new Set(majorCategoryL2Options), [majorCategoryL2Options])
    const majorCategoryL2Hint =
        filters.major_categories_l1.length === 0
            ? t('filter.majorCategoryL2Hint')
            : majorCategoryL2Options.length === 0
                ? t('filter.majorCategoryL2Empty')
                : t('filter.majorCategoryL2LinkedHint', {
                    l1Count: filters.major_categories_l1.length,
                    l2Count: majorCategoryL2Options.length
                })

    useEffect(() => {
        const nextL2 = filters.major_categories_l2.filter((value) => majorCategoryL2OptionSet.has(value))
        if (nextL2.length === filters.major_categories_l2.length) {
            return
        }

        onChange({ ...filters, major_categories_l2: nextL2 })
    }, [filters, majorCategoryL2OptionSet, onChange])

    const chips = [
        ...filters.visa_types.map((v) => ({ field: 'visa_types' as const, value: v, label: t('filter.chipVisa', { value: v }) })),
        ...filters.months.map((v) => ({ field: 'months' as const, value: v, label: t('filter.chipMonth', { value: v }) })),
        ...filters.consulates.map((v) => ({ field: 'consulates' as const, value: v, label: t('filter.chipConsulate', { value: v }) })),
        ...filters.statuses.map((v) => ({ field: 'statuses' as const, value: v, label: t('filter.chipStatus', { value: v }) })),
        ...filters.entries.map((v) => ({ field: 'entries' as const, value: v, label: t('filter.chipEntry', { value: v }) })),
        ...filters.major_categories_l1.map((v) => ({
            field: 'major_categories_l1' as const,
            value: v,
            label: t('filter.chipMajorCategoryL1', { value: v })
        })),
        ...filters.major_categories_l2.map((v) => ({
            field: 'major_categories_l2' as const,
            value: v,
            label: t('filter.chipMajorCategoryL2', { value: v })
        })),
        ...filters.majors.map((v) => ({ field: 'majors' as const, value: v, label: t('filter.chipMajor', { value: v }) })),
        ...filters.employers.map((v) => ({ field: 'employers' as const, value: v, label: t('filter.chipEmployer', { value: v }) })),
        ...filters.detail_cities.map((v) => ({ field: 'detail_cities' as const, value: v, label: t('filter.chipDetailCity', { value: v }) })),
        ...filters.detail_states.map((v) => ({ field: 'detail_states' as const, value: v, label: t('filter.chipDetailState', { value: v }) })),
        ...(filters.has_note
            ? [{ field: 'has_note' as const, value: 'true', label: t('filter.chipHasNote') }]
            : []),
        ...(filters.search_text
            ? [{ field: 'search_text' as const, value: filters.search_text, label: t('filter.chipSearch', { value: filters.search_text }) }]
            : [])
    ]

    const removeChip = (field: keyof Filters, value: string) => {
        if (field === 'has_note') {
            onChange({ ...filters, has_note: false })
            return
        }
        if (field === 'search_text') {
            onChange({ ...filters, search_text: '' })
            return
        }

        const current = filters[field]
        if (!Array.isArray(current)) {
            return
        }

        onChange({ ...filters, [field]: current.filter((x) => x !== value) })
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
        <section className="filter-card motion-ready" role="region" aria-labelledby="filters-title">
            <div className="filter-top filter-motion-item motion-0">
                <h3 id="filters-title">{titleText}</h3>
                <div className="hint-list" id="filters-hint">
                    <p>{t('filter.hintSelect')}</p>
                    <p>{t('filter.hintEmptyMeansAll')}</p>
                    {showRefreshControls ? <p>{t('filter.hintHistory')}</p> : null}
                </div>
            </div>

            {showRefreshControls ? (
                <div className="refresh-shell filter-motion-item motion-1">
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

                        <div className="actions compact refresh-actions">
                            <button type="button" className="ghost" disabled={!hasPendingChanges || isRefreshing} onClick={onApply}>
                                {t('filter.apply')}
                            </button>
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
                </div>
            ) : (
                <div className="actions compact filter-only-actions filter-motion-item motion-1">
                    <button type="button" disabled={!hasPendingChanges} onClick={onApply}>{t('filter.apply')}</button>
                    <button type="button" className="ghost" onClick={onReset}>{t('filter.reset')}</button>
                </div>
            )}

            <div className="filter-search-card filter-motion-item motion-2">
                <label className="field" htmlFor="filter-search-text">
                    <span id="filter-search-text-label">{t('filter.searchText')}</span>
                    <input
                        id="filter-search-text"
                        type="text"
                        value={filters.search_text}
                        placeholder={t('filter.searchTextPlaceholder')}
                        aria-labelledby="filter-search-text-label"
                        onChange={(e) => onChange({ ...filters, search_text: e.currentTarget.value })}
                    />
                    <small className="field-help">{t('filter.searchTextHint')}</small>
                </label>
                <label className="checkbox-item note-filter-toggle">
                    <input
                        type="checkbox"
                        checked={filters.has_note}
                        onChange={(e) => onChange({ ...filters, has_note: e.currentTarget.checked })}
                    />
                    <span>{t('filter.hasNoteOnly')}</span>
                </label>
                <small className="field-help">{t('filter.hasNoteOnlyHint')}</small>
            </div>

            <div className="chip-row filter-motion-item motion-3" aria-live="polite">
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

            <div className="filter-zones filter-motion-item motion-4">
                <section className="filter-zone" aria-label={t('filter.coreFiltersTitle')}>
                    <div className="filter-zone-head">
                        <h4>{t('filter.coreFiltersTitle')}</h4>
                        <p>{t('filter.coreFiltersHint')}</p>
                    </div>
                    <div className="filter-grid filter-grid-core">
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
                        <PillMultiSelect
                            id="filter-months"
                            label={t('filter.months')}
                            hint={t('filter.monthsHint')}
                            values={options.months}
                            selected={filters.months}
                            onPick={(v) => onChange({ ...filters, months: v })}
                            onClear={() => onChange({ ...filters, months: [] })}
                            clearText={t('filter.clearOne')}
                            className="filter-months"
                            emptyLabel={t('filter.emptyOptions')}
                            footer={(
                                <div className="quick-actions">
                                    <button type="button" className="ghost" onClick={() => applyRecentMonths(3)}>{t('filter.quick3')}</button>
                                    <button type="button" className="ghost" onClick={() => applyRecentMonths(6)}>{t('filter.quick6')}</button>
                                    <button type="button" className="ghost" onClick={() => applyRecentMonths(12)}>{t('filter.quick12')}</button>
                                </div>
                            )}
                        />
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
                        <PillMultiSelect
                            id="filter-major-category-l1"
                            label={t('filter.majorCategoryL1')}
                            hint={t('filter.majorCategoryL1Hint')}
                            values={options.major_categories_l1}
                            selected={filters.major_categories_l1}
                            onPick={(v) => {
                                const linkedL2Set = new Set(resolveLinkedMajorCategoryL2(v))
                                onChange({
                                    ...filters,
                                    major_categories_l1: v,
                                    major_categories_l2: filters.major_categories_l2.filter((item) => linkedL2Set.has(item))
                                })
                            }}
                            onClear={() => onChange({ ...filters, major_categories_l1: [], major_categories_l2: [] })}
                            clearText={t('filter.clearOne')}
                            className="filter-major-l1"
                            emptyLabel={t('filter.emptyOptions')}
                        />
                        <PillMultiSelect
                            id="filter-major-category-l2"
                            label={t('filter.majorCategoryL2')}
                            hint={majorCategoryL2Hint}
                            values={majorCategoryL2Options}
                            selected={filters.major_categories_l2}
                            onPick={(v) => onChange({
                                ...filters,
                                major_categories_l2: v.filter((item) => majorCategoryL2OptionSet.has(item))
                            })}
                            onClear={() => onChange({ ...filters, major_categories_l2: [] })}
                            clearText={t('filter.clearOne')}
                            className="filter-major-l2"
                            emptyLabel={t('filter.emptyOptions')}
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
                </section>

                <section className="filter-zone" aria-label={t('filter.detailFiltersTitle')}>
                    <div className="filter-zone-head">
                        <h4>{t('filter.detailFiltersTitle')}</h4>
                        <p>{t('filter.detailFiltersHint')}</p>
                    </div>
                    <div className="filter-grid filter-grid-detail">
                        <PillMultiSelect
                            id="filter-majors"
                            label={t('filter.majors')}
                            hint={t('filter.majorsHint')}
                            values={options.majors}
                            selected={filters.majors}
                            onPick={(v) => onChange({ ...filters, majors: v })}
                            onClear={() => onChange({ ...filters, majors: [] })}
                            clearText={t('filter.clearOne')}
                            className="filter-detail-pill"
                            emptyLabel={t('filter.emptyOptions')}
                        />
                        <PillMultiSelect
                            id="filter-employers"
                            label={t('filter.employers')}
                            hint={t('filter.employersHint')}
                            values={options.employers}
                            selected={filters.employers}
                            onPick={(v) => onChange({ ...filters, employers: v })}
                            onClear={() => onChange({ ...filters, employers: [] })}
                            clearText={t('filter.clearOne')}
                            className="filter-detail-pill"
                            emptyLabel={t('filter.emptyOptions')}
                        />
                        <PillMultiSelect
                            id="filter-detail-cities"
                            label={t('filter.detailCities')}
                            hint={t('filter.detailCitiesHint')}
                            values={options.detail_cities}
                            selected={filters.detail_cities}
                            onPick={(v) => onChange({ ...filters, detail_cities: v })}
                            onClear={() => onChange({ ...filters, detail_cities: [] })}
                            clearText={t('filter.clearOne')}
                            className="filter-detail-pill"
                            emptyLabel={t('filter.emptyOptions')}
                        />
                        <PillMultiSelect
                            id="filter-detail-states"
                            label={t('filter.detailStates')}
                            hint={t('filter.detailStatesHint')}
                            values={options.detail_states}
                            selected={filters.detail_states}
                            onPick={(v) => onChange({ ...filters, detail_states: v })}
                            onClear={() => onChange({ ...filters, detail_states: [] })}
                            clearText={t('filter.clearOne')}
                            className="filter-detail-pill"
                            emptyLabel={t('filter.emptyOptions')}
                        />
                    </div>
                </section>
            </div>

            {showConsulateGroups ? (
                <div className="consulate-section filter-motion-item motion-5">
                    <h4>{t('filter.groupedConsulates')}</h4>
                    <div className="consulate-visa-block">
                        <p className="consulate-subtitle">{t('filter.visaPrefilterTitle')}</p>
                        <CheckboxGroup
                            title={t('filter.visaTypes')}
                            hint={t('filter.visaTypesHint')}
                            values={options.visa_types}
                            selected={filters.visa_types}
                            onPick={(v) => onChange({ ...filters, visa_types: v })}
                            onClear={() => onChange({ ...filters, visa_types: [] })}
                            clearText={t('filter.clearOne')}
                        />
                    </div>
                    <div className="consulate-country-block">
                        <p className="consulate-subtitle">{t('filter.consulateGroupTitle')}</p>
                        <p className="consulate-subhint">{t('filter.consulateGroupHint')}</p>
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
                </div>
            ) : null}
        </section>
    )
}
