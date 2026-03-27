import { describe, expect, it } from 'vitest'

import { paramsFromFilters } from '../api'
import type { Filters } from '../types'

describe('api paramsFromFilters', () => {
    it('应拼接多值筛选参数', () => {
        const filters: Filters = {
            visa_types: ['F1', 'H1B'],
            consulates: ['BeiJing'],
            statuses: ['Pending'],
            entries: ['I20'],
            months: ['2026-03', '2026-02']
        }

        const params = paramsFromFilters(filters)
        expect(params.get('visa_types')).toBe('F1,H1B')
        expect(params.get('consulates')).toBe('BeiJing')
        expect(params.get('months')).toBe('2026-03,2026-02')
    })

    it('应忽略空数组字段', () => {
        const filters: Filters = {
            visa_types: [],
            consulates: [],
            statuses: [],
            entries: [],
            months: []
        }

        const params = paramsFromFilters(filters)
        expect(params.toString()).toBe('')
    })
})
