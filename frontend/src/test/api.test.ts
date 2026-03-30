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
            months: ['2026-03', '2026-02'],
            major_categories_l1: ['STEM'],
            major_categories_l2: ['Engineering'],
            majors: ['CS'],
            employers: ['Google'],
            detail_cities: ['Beijing'],
            detail_states: ['Beijing'],
            has_note: true,
            search_text: 'stem case'
        }

        const params = paramsFromFilters(filters)
        expect(params.get('visa_types')).toBe('F1,H1B')
        expect(params.get('consulates')).toBe('BeiJing')
        expect(params.get('months')).toBe('2026-03,2026-02')
        expect(params.get('major_categories_l1')).toBe('STEM')
        expect(params.get('major_categories_l2')).toBe('Engineering')
        expect(params.get('majors')).toBe('CS')
        expect(params.get('employers')).toBe('Google')
        expect(params.get('has_note')).toBe('true')
        expect(params.get('search_text')).toBe('stem case')
    })

    it('应忽略空数组字段', () => {
        const filters: Filters = {
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
            has_note: false,
            search_text: ''
        }

        const params = paramsFromFilters(filters)
        expect(params.toString()).toBe('')
    })
})
