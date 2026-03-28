/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_BASE_URL?: string
    readonly VITE_DEFAULT_PAGE_SIZE?: string
    readonly VITE_DEFAULT_REFRESH_MONTHS?: string
    readonly VITE_PAGE_SIZE_OPTIONS?: string
    readonly VITE_ENABLE_LANGUAGE_SWITCH?: string
    readonly VITE_ENABLE_SENSITIVITY?: string
    readonly VITE_ENABLE_CONSULATE_GROUPS?: string
    readonly VITE_ENABLE_PUBLIC_REFRESH?: string
    readonly VITE_ENABLE_ADMIN_PAGE?: string
    readonly VITE_ADMIN_ROUTE_PATH?: string
    readonly VITE_ADMIN_REQUIRE_ACCESS_CODE?: string
    readonly VITE_ADMIN_ACCESS_CODE?: string
    readonly VITE_APP_VERSION?: string
    readonly VITE_GITHUB_REPO_URL?: string
    readonly VITE_MAINTAINER_NAME?: string
    readonly VITE_MAINTAINER_URL?: string
    readonly VITE_BUY_ME_COFFEE_URL?: string
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}

declare const __APP_VERSION__: string
