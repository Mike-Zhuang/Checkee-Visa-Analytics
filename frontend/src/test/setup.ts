import '@testing-library/jest-dom/vitest'
import i18n from '../locales/i18n'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

void i18n.changeLanguage('zh')

afterEach(() => {
    cleanup()
})
