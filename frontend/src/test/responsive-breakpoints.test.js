import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const stylesCss = readFileSync(`${process.cwd()}/src/styles.css`, 'utf8')

describe('responsive breakpoints guard', () => {
    it('560 breakpoint should hide secondary columns and shrink table width', () => {
        expect(stylesCss).toMatch(/@media \(max-width: 560px\)[\s\S]*\.case-col-optional,\s*\.admin-col-secondary\s*\{\s*display:\s*none;/)
        expect(stylesCss).toMatch(/@media \(max-width: 560px\)[\s\S]*table\s*\{\s*min-width:\s*680px;/)
        expect(stylesCss).toMatch(/@media \(max-width: 560px\)[\s\S]*\.admin-major-table-wrap table\s*\{\s*min-width:\s*640px;/)
    })

    it('420 breakpoint should hide tertiary columns and further shrink widths', () => {
        expect(stylesCss).toMatch(/@media \(max-width: 420px\)[\s\S]*\.case-col-tertiary,\s*\.admin-col-tertiary\s*\{\s*display:\s*none;/)
        expect(stylesCss).toMatch(/@media \(max-width: 420px\)[\s\S]*table\s*\{\s*min-width:\s*560px;/)
        expect(stylesCss).toMatch(/@media \(max-width: 420px\)[\s\S]*\.admin-major-table-wrap table\s*\{\s*min-width:\s*540px;/)
    })

    it('table wrapper should keep touch-friendly scrolling properties', () => {
        expect(stylesCss).toContain('-webkit-overflow-scrolling: touch;')
        expect(stylesCss).toContain('overscroll-behavior: contain;')
    })
})
