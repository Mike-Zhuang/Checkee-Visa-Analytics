import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AdminPage from '../AdminPage'

const apiMock = vi.hoisted(() => ({
    getOptions: vi.fn(),
    getMetaState: vi.fn(),
    loginAdmin: vi.fn(),
    getAdminSession: vi.fn(),
    getAdminMajorClassifications: vi.fn(),
    saveAdminMajorOverrides: vi.fn(),
    deleteAdminMajorOverride: vi.fn(),
    logoutAdmin: vi.fn(),
    refreshDataWithSession: vi.fn(),
    triggerAdminStaleRefresh: vi.fn()
}))

vi.mock('../api', () => ({
    getOptions: apiMock.getOptions,
    getMetaState: apiMock.getMetaState,
    loginAdmin: apiMock.loginAdmin,
    getAdminSession: apiMock.getAdminSession,
    getAdminMajorClassifications: apiMock.getAdminMajorClassifications,
    saveAdminMajorOverrides: apiMock.saveAdminMajorOverrides,
    deleteAdminMajorOverride: apiMock.deleteAdminMajorOverride,
    logoutAdmin: apiMock.logoutAdmin,
    refreshDataWithSession: apiMock.refreshDataWithSession,
    triggerAdminStaleRefresh: apiMock.triggerAdminStaleRefresh
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
            major_categories_l1: ['STEM'],
            major_categories_l2: ['AI & Data'],
            major_category_mapping: {
                STEM: ['AI & Data']
            },
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
        apiMock.getAdminMajorClassifications.mockResolvedValue({
            total: 4,
            category_l1_options: ['STEM', 'Business', 'Other'],
            category_l2_options: ['AI & Data', 'Engineering', 'Not Applicable'],
            items: [
                {
                    major: 'CS',
                    major_normalized: 'cs',
                    count: 10,
                    auto_category_l1: 'STEM',
                    auto_category_l2: 'AI & Data',
                    effective_category_l1: 'STEM',
                    effective_category_l2: 'AI & Data',
                    source: 'auto',
                    has_manual_override: false,
                    override_updated_at: null
                },
                {
                    major: 'N/A',
                    major_normalized: 'n a',
                    count: 3,
                    auto_category_l1: 'Other',
                    auto_category_l2: 'Not Applicable',
                    effective_category_l1: 'Other',
                    effective_category_l2: 'Not Applicable',
                    source: 'not_applicable',
                    has_manual_override: false,
                    override_updated_at: null
                },
                {
                    major: 'Unknown Major',
                    major_normalized: 'unknown major',
                    count: 2,
                    auto_category_l1: 'Other',
                    auto_category_l2: 'Unspecified',
                    effective_category_l1: 'Other',
                    effective_category_l2: 'Unspecified',
                    source: 'unknown',
                    has_manual_override: false,
                    override_updated_at: null
                },
                {
                    major: 'Finance',
                    major_normalized: 'finance',
                    count: 2,
                    auto_category_l1: 'Business',
                    auto_category_l2: 'Finance & Accounting',
                    effective_category_l1: 'Business',
                    effective_category_l2: 'Finance & Accounting',
                    source: 'manual',
                    has_manual_override: true,
                    override_updated_at: '2026-03-28T10:00:00Z'
                }
            ]
        })
        apiMock.saveAdminMajorOverrides.mockResolvedValue(undefined)
        apiMock.deleteAdminMajorOverride.mockResolvedValue(undefined)
        apiMock.logoutAdmin.mockResolvedValue(undefined)
        apiMock.refreshDataWithSession.mockResolvedValue(undefined)
        apiMock.triggerAdminStaleRefresh.mockResolvedValue({
            triggered: false,
            reason: 'fresh_enough',
            updated_at: '2026-03-28T15:20:00Z',
            message: 'data is fresh enough'
        })
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
            expect(apiMock.getAdminMajorClassifications).toHaveBeenCalledWith('session-token', '', 600)
            expect(apiMock.triggerAdminStaleRefresh).not.toHaveBeenCalled()
        })

        const expiryHint = screen.getByText(/会话有效期至：/)
        expect(expiryHint.textContent ?? '').not.toMatch(/T\d{2}:\d{2}:\d{2}/)
    })

    it('应按来源分区展示且 N/A 行只读', async () => {
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
            expect(screen.getByText('待人工处理（未命中）')).toBeInTheDocument()
            expect(screen.getByText('人工已覆盖')).toBeInTheDocument()
            expect(screen.getByText('自动命中')).toBeInTheDocument()
            expect(screen.getByText('无专业信息（只读）')).toBeInTheDocument()
        })

        const naRow = screen.getByText('N/A').closest('tr')
        expect(naRow).toBeTruthy()
        if (!naRow) {
            throw new Error('N/A row not found')
        }

        expect(within(naRow).getByRole('button', { name: '保存' })).toBeDisabled()
        expect(within(naRow).getByRole('button', { name: '重置' })).toBeDisabled()
        expect(within(naRow).getByRole('button', { name: '删除覆盖' })).toBeDisabled()
    })

    it('应保留移动端列隐藏所需 class 挂点', async () => {
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
            expect(screen.getByRole('columnheader', { name: '自动归类' })).toBeInTheDocument()
            expect(screen.getByRole('columnheader', { name: '来源' })).toBeInTheDocument()
        })

        expect(screen.getByRole('columnheader', { name: '自动归类' })).toHaveClass('admin-col-secondary')
        expect(screen.getByRole('columnheader', { name: '来源' })).toHaveClass('admin-col-tertiary')
    })

    it('数据过旧时应触发管理员兜底刷新', async () => {
        const user = userEvent.setup()
        apiMock.getMetaState.mockResolvedValue({
            fetched_months: ['2026-03'],
            fetched_month_count: 1,
            total_cases: 100,
            all_months: false,
            months_arg: 6,
            from_month: null,
            truncated_by_limit: false,
            month_limit: 120,
            updated_at: '2026-03-28T00:00:00Z',
            has_data: true,
            current_case_count: 100,
            data_freshness_seconds: 99999,
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
        apiMock.loginAdmin.mockResolvedValue({
            token: 'session-token',
            expires_at: '2026-03-28T15:58:21.837314Z'
        })
        apiMock.triggerAdminStaleRefresh.mockResolvedValue({
            triggered: true,
            reason: 'stale_triggered',
            updated_at: '2026-03-29T12:00:00Z',
            message: 'stale refresh triggered'
        })

        render(<AdminPage />)

        await waitFor(() => {
            expect(apiMock.getOptions).toHaveBeenCalledTimes(1)
            expect(apiMock.getMetaState).toHaveBeenCalledTimes(1)
        })

        await user.type(screen.getByPlaceholderText('请输入管理员密码'), 'Zcb070920!')
        await user.click(screen.getByRole('button', { name: '登录' }))

        await waitFor(() => {
            expect(apiMock.triggerAdminStaleRefresh).toHaveBeenCalledWith('session-token')
            expect(screen.getByText(/检测到数据过旧，已触发兜底刷新/)).toBeInTheDocument()
        })
    })
})
