import '@testing-library/jest-dom/vitest'
import i18n from '../locales/i18n'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

if (!window.matchMedia) {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
            matches: false,
            media: query,
            onchange: null,
            addListener: vi.fn(),
            removeListener: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn()
        }))
    })
}

void i18n.changeLanguage('zh')

afterEach(() => {
    cleanup()
})
