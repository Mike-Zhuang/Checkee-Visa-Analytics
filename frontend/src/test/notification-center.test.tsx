import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import NotificationCenter from '../components/NotificationCenter'
import type { UserNotificationItem } from '../types'

const notificationsFixture: UserNotificationItem[] = [
    {
        id: 'n1',
        subscription_id: 's1',
        level: 'warning',
        title: '筛选【F1】出现波动',
        body: 'Pending 比率上升到 30%。',
        read_at: null,
        created_at: '2026-04-01T10:00:00+00:00'
    }
]

describe('NotificationCenter', () => {
    it('空态时应显示占位文案', () => {
        render(
            <NotificationCenter
                notifications={[]}
                unreadCount={0}
                loading={false}
                error={null}
                onRefresh={vi.fn()}
                onMarkRead={vi.fn()}
                onMarkAllRead={vi.fn()}
            />
        )

        expect(screen.getByText('暂无提醒。')).toBeInTheDocument()
    })

    it('可渲染提醒并触发标记已读', async () => {
        const user = userEvent.setup()
        const onMarkRead = vi.fn()

        render(
            <NotificationCenter
                notifications={notificationsFixture}
                unreadCount={1}
                loading={false}
                error={null}
                onRefresh={vi.fn()}
                onMarkRead={onMarkRead}
                onMarkAllRead={vi.fn()}
            />
        )

        expect(screen.getByText('未读 1')).toBeInTheDocument()
        expect(screen.getByText('筛选【F1】出现波动')).toBeInTheDocument()

        await user.click(screen.getByRole('button', { name: '标记已读' }))
        expect(onMarkRead).toHaveBeenCalledWith('n1')
    })
})
