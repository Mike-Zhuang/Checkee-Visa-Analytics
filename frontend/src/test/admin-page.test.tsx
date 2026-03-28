import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AdminPage from '../AdminPage'

const apiMock = vi.hoisted(() => ({
    getOptions: vi.fn(),
    getMetaState: vi.fn(),
    loginAdmin: vi.fn(),
    getAdminSession: vi.fn(),
    logoutAdmin: vi.fn(),
    refreshDataWithSession: vi.fn()
}))

vi.mock('../api', () => ({
    getOptions: apiMock.getOptions,
    getMetaState: apiMock.getMetaState,
    loginAdmin: apiMock.loginAdmin,
    getAdminSession: apiMock.getAdminSession,
    logoutAdmin: apiMock.logoutAdmin,
    refreshDataWithSession: apiMock.refreshDataWithSession
}))

describe('AdminPage', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        window.sessionStorage.clear()

        apiMock.getOptions.mockResolvedValue({
            months: ['2026-03'],
            visa_types: ['F1'],
            consulates: ['BeiJing'],
            statuses: ['Pending'],
            entries: ['I20'],
            majors: ['CS'],
            employers: ['Google'],
            detail_cities: ['Beijing'],
            detail_states: ['Beijing'],
            fetch_sources: ['monthly_track']
        })

        apiMock.getMetaState.mockResolvedValue({
            fetched_months: ['2026-03'],
            fetched_month_count: 1,
            total_cases: 100,
            all_months: false,
            months_arg: 6,
            from_month: null,
            truncated_by_limit: false,
            month_limit: 120,
            updated_at: '2026-03-28T15:20:00Z',
            has_data: true,
            current_case_count: 100,
            data_freshness_seconds: 120,
            refresh_min_interval_seconds: 300,
            refresh_available_in_seconds: 0,
            refresh_history: [],
            fetched_month_range: {
                latest: '2026-03',
                earliest: '2026-03'
            },
            selected_sources: ['monthly_track'],
            supported_sources: ['monthly_track']
        })

        apiMock.getAdminSession.mockResolvedValue({
            authenticated: true,
            expires_at: '2026-03-28T15:58:21.837314Z'
        })
        apiMock.logoutAdmin.mockResolvedValue(undefined)
        apiMock.refreshDataWithSession.mockResolvedValue(undefined)
    })

    it('应显示管理员登录入口', async () => {
        render(<AdminPage />)

        expect(screen.getByRole('heading', { name: '管理员登录' })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument()

        await waitFor(() => {
            expect(apiMock.getOptions).toHaveBeenCalledTimes(1)
            expect(apiMock.getMetaState).toHaveBeenCalledTimes(1)
        })
    })

    it('登录后应展示本地化会话有效期', async () => {
        const user = userEvent.setup()
        apiMock.loginAdmin.mockResolvedValue({
            token: 'session-token',
            expires_at: '2026-03-28T15:58:21.837314Z'
        })

        render(<AdminPage />)

        await waitFor(() => {
            expect(apiMock.getOptions).toHaveBeenCalledTimes(1)
            expect(apiMock.getMetaState).toHaveBeenCalledTimes(1)
        })

        await user.type(screen.getByPlaceholderText('请输入管理员密码'), 'Zcb070920!')
        await user.click(screen.getByRole('button', { name: '登录' }))

        await waitFor(() => {
            expect(screen.getByText('已登录')).toBeInTheDocument()
            expect(apiMock.loginAdmin).toHaveBeenCalledWith('Zcb070920!')
            expect(apiMock.getAdminSession).toHaveBeenCalledWith('session-token')
        })

        const expiryHint = screen.getByText(/会话有效期至：/)
        expect(expiryHint.textContent ?? '').not.toMatch(/T\d{2}:\d{2}:\d{2}/)
    })
})
