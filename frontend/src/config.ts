function getNumberEnv(key: string, fallback: number, minimum = 0): number {
    const raw = import.meta.env[key] as string | undefined
    if (!raw) return fallback
    const parsed = Number(raw)
    if (!Number.isFinite(parsed)) return fallback
    return Math.max(minimum, Math.floor(parsed))
}

function getBooleanEnv(key: string, fallback: boolean): boolean {
    const raw = import.meta.env[key] as string | undefined
    if (!raw) return fallback
    return ['1', 'true', 'yes', 'on'].includes(raw.trim().toLowerCase())
}

function getStringEnv(key: string, fallback: string): string {
    const raw = import.meta.env[key] as string | undefined
    if (!raw) return fallback
    const value = raw.trim()
    return value || fallback
}

function getNumberArrayEnv(key: string, fallback: number[]): number[] {
    const raw = import.meta.env[key] as string | undefined
    if (!raw) return fallback
    const parsed = raw
        .split(',')
        .map((item) => Number(item.trim()))
        .filter((item) => Number.isFinite(item) && item > 0)
        .map((item) => Math.floor(item))
    return parsed.length ? parsed : fallback
}

const defaultApiBaseUrl = 'http://127.0.0.1:8000/api/v1'
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || defaultApiBaseUrl

export const frontendConfig = {
    apiBaseUrl,
    defaultPageSize: getNumberEnv('VITE_DEFAULT_PAGE_SIZE', 50, 1),
    defaultRefreshMonths: getNumberEnv('VITE_DEFAULT_REFRESH_MONTHS', 6, 1),
    pageSizeOptions: getNumberArrayEnv('VITE_PAGE_SIZE_OPTIONS', [50, 100, 200]),
    enableLanguageSwitch: getBooleanEnv('VITE_ENABLE_LANGUAGE_SWITCH', true),
    enableSensitivity: getBooleanEnv('VITE_ENABLE_SENSITIVITY', true),
    enableConsulateGroups: getBooleanEnv('VITE_ENABLE_CONSULATE_GROUPS', true),
    enablePublicRefresh: getBooleanEnv('VITE_ENABLE_PUBLIC_REFRESH', false),
    enableUserAuth: getBooleanEnv('VITE_ENABLE_USER_AUTH', false),
    enableAdminPage: getBooleanEnv('VITE_ENABLE_ADMIN_PAGE', true),
    adminRoutePath: getStringEnv('VITE_ADMIN_ROUTE_PATH', '/admin-ops'),
    adminRequireAccessCode: getBooleanEnv('VITE_ADMIN_REQUIRE_ACCESS_CODE', false),
    adminAccessCode: getStringEnv('VITE_ADMIN_ACCESS_CODE', ''),
    appVersion: getStringEnv('VITE_APP_VERSION', __APP_VERSION__),
    githubRepoUrl: getStringEnv('VITE_GITHUB_REPO_URL', 'https://github.com/Mike-Zhuang/Checkee-Visa-Analytics'),
    maintainerName: getStringEnv('VITE_MAINTAINER_NAME', 'Zhuang Chengbo'),
    maintainerUrl: getStringEnv('VITE_MAINTAINER_URL', 'https://github.com/Mike-Zhuang'),
    buyMeCoffeeUrl: getStringEnv('VITE_BUY_ME_COFFEE_URL', 'https://www.buymeacoffee.com/mikezhuang')
}
