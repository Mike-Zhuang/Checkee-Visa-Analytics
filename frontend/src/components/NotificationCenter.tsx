import { useTranslation } from 'react-i18next'

import type { UserNotificationItem } from '../types'

type NotificationCenterProps = {
    notifications: UserNotificationItem[]
    unreadCount: number
    loading: boolean
    error: string | null
    onRefresh: () => void
    onMarkRead: (notificationId: string) => void
    onMarkAllRead: () => void
}

export default function NotificationCenter({
    notifications,
    unreadCount,
    loading,
    error,
    onRefresh,
    onMarkRead,
    onMarkAllRead,
}: NotificationCenterProps) {
    const { t } = useTranslation()

    return (
        <section className="notification-center" aria-label={t('notify.title')}>
            <div className="panel-head">
                <h4>{t('notify.title')}</h4>
                <div className="actions compact">
                    <span className="notify-badge">{t('notify.unreadCount', { count: unreadCount })}</span>
                    <button type="button" className="ghost" onClick={onRefresh}>
                        {t('notify.refresh')}
                    </button>
                    <button type="button" className="ghost" onClick={onMarkAllRead} disabled={unreadCount <= 0}>
                        {t('notify.markAllRead')}
                    </button>
                </div>
            </div>

            {loading ? <p className="empty-copy">{t('notify.loading')}</p> : null}
            {error ? <p className="error-inline">{error}</p> : null}

            {!loading && !error && notifications.length === 0 ? (
                <p className="empty-copy">{t('notify.empty')}</p>
            ) : null}

            {notifications.length > 0 ? (
                <div className="notify-list">
                    {notifications.map((item) => (
                        <article key={item.id} className={`notify-item level-${item.level}`}>
                            <div className="notify-head">
                                <strong>{item.title}</strong>
                                <span>{item.created_at}</span>
                            </div>
                            <p>{item.body}</p>
                            <div className="notify-actions">
                                {item.read_at ? (
                                    <span className="notify-read-tag">{t('notify.read')}</span>
                                ) : (
                                    <button type="button" className="ghost" onClick={() => onMarkRead(item.id)}>
                                        {t('notify.markRead')}
                                    </button>
                                )}
                            </div>
                        </article>
                    ))}
                </div>
            ) : null}
        </section>
    )
}
