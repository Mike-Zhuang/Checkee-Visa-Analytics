import i18next from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import en from './resources/en.json'
import zh from './resources/zh.json'

i18next
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
        resources: {
            zh: { translation: zh },
            en: { translation: en }
        },
        fallbackLng: 'zh',
        supportedLngs: ['zh', 'en'],
        detection: {
            order: ['localStorage', 'navigator'],
            caches: ['localStorage'],
            lookupLocalStorage: 'checkee-locale'
        },
        interpolation: {
            escapeValue: false
        }
    })

export default i18next
