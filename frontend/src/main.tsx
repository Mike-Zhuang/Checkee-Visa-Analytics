import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import AdminPage from './AdminPage'
import { frontendConfig } from './config'
import './locales/i18n'
import './styles.css'

function normalizePath(pathname: string): string {
    const normalized = pathname.replace(/\/+$/, '')
    return normalized || '/'
}

const adminRoutePath = normalizePath(
    frontendConfig.adminRoutePath.startsWith('/')
        ? frontendConfig.adminRoutePath
        : `/${frontendConfig.adminRoutePath}`
)

const isAdminRoute = normalizePath(window.location.pathname) === adminRoutePath
const RootPage = isAdminRoute && frontendConfig.enableAdminPage ? AdminPage : App

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <RootPage />
    </React.StrictMode>
)
