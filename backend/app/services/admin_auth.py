from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock


@dataclass(frozen=True)
class AdminSession:
    token: str
    expires_at: datetime


_sessions: dict[str, datetime] = {}
_session_lock = Lock()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _prune_expired_sessions(now: datetime | None = None) -> None:
    current = now or _now_utc()
    expired_tokens = [token for token, expires_at in _sessions.items() if expires_at <= current]
    for token in expired_tokens:
        _sessions.pop(token, None)


def create_admin_session(ttl_seconds: int) -> AdminSession:
    expires_at = _now_utc() + timedelta(seconds=ttl_seconds)
    token = secrets.token_urlsafe(32)
    with _session_lock:
        _prune_expired_sessions()
        _sessions[token] = expires_at
    return AdminSession(token=token, expires_at=expires_at)


def get_session_expiry(token: str) -> datetime | None:
    normalized = token.strip()
    if not normalized:
        return None
    with _session_lock:
        _prune_expired_sessions()
        expires_at = _sessions.get(normalized)
        if expires_at is None:
            return None
        if expires_at <= _now_utc():
            _sessions.pop(normalized, None)
            return None
        return expires_at


def revoke_admin_session(token: str) -> bool:
    normalized = token.strip()
    if not normalized:
        return False
    with _session_lock:
        return _sessions.pop(normalized, None) is not None


def reset_sessions() -> None:
    with _session_lock:
        _sessions.clear()
