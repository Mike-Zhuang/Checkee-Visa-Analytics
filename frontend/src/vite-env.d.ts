/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_API_BASE_URL?: string
	readonly VITE_DEFAULT_PAGE_SIZE?: string
	readonly VITE_DEFAULT_REFRESH_MONTHS?: string
	readonly VITE_PAGE_SIZE_OPTIONS?: string
	readonly VITE_ENABLE_LANGUAGE_SWITCH?: string
	readonly VITE_ENABLE_SENSITIVITY?: string
	readonly VITE_ENABLE_CONSULATE_GROUPS?: string
}

interface ImportMeta {
	readonly env: ImportMetaEnv
}
