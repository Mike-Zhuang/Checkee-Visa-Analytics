from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Iterator
from uuid import uuid4

from app.core.config import (
    USER_DB_PATH,
    USER_MAX_FILTER_PRESETS,
    USER_PASSWORD_MIN_LENGTH,
    USER_SESSION_TTL_SECONDS,
)
from app.services import analytics


class UserAuthError(ValueError):
    pass


class UserAuthValidationError(UserAuthError):
    pass


class UserAuthConflictError(UserAuthError):
    pass


class UserAuthUnauthorizedError(UserAuthError):
    pass


class UserAuthNotFoundError(UserAuthError):
    pass


class UserAuthLimitError(UserAuthError):
    pass


@dataclass(frozen=True)
class UserSession:
    user_id: int
    username: str
    token: str
    expires_at: datetime


class UserAuthService:
    _USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]{3,32}$")
    _PASSWORD_HASH_ITERATIONS = 120_000
    _DEFAULT_SUBSCRIPTION_RULE = {
        "pending_ratio_delta_ge": 0.08,
        "median_days_delta_ge": 10.0,
        "p90_days_delta_ge": 15.0,
        "long_tail_ratio_delta_ge": 0.08,
        "min_sample_size": 20,
        "cooldown_hours": 24,
    }

    def __init__(self) -> None:
        self._lock = RLock()

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    def _normalize_username(self, username: str) -> str:
        normalized = (username or "").strip().lower()
        if not self._USERNAME_PATTERN.fullmatch(normalized):
            raise UserAuthValidationError(
                "username must match ^[a-z0-9_.-]{3,32}$"
            )
        return normalized

    @staticmethod
    def _normalize_token(token: str) -> str:
        return (token or "").strip()

    @staticmethod
    def _normalize_preset_name(name: str) -> str:
        normalized = (name or "").strip()
        if len(normalized) < 1 or len(normalized) > 80:
            raise UserAuthValidationError("preset name length must be between 1 and 80")
        return normalized

    @staticmethod
    def _normalize_subscription_channel(channel: str) -> str:
        normalized = (channel or "").strip().lower()
        if normalized != "in_app":
            raise UserAuthValidationError("subscription channel must be in_app")
        return normalized

    @classmethod
    def _normalize_subscription_rule(cls, rule: dict[str, Any] | None) -> dict[str, Any]:
        payload = dict(cls._DEFAULT_SUBSCRIPTION_RULE)
        if rule is None:
            return payload
        if not isinstance(rule, dict):
            raise UserAuthValidationError("subscription rule must be an object")

        def _read_float(key: str, minimum: float, maximum: float) -> float:
            raw = rule.get(key)
            if raw is None:
                return float(payload[key])
            try:
                parsed = float(raw)
            except (TypeError, ValueError):
                raise UserAuthValidationError(f"subscription rule {key} must be a number")
            return max(minimum, min(maximum, parsed))

        def _read_int(key: str, minimum: int, maximum: int) -> int:
            raw = rule.get(key)
            if raw is None:
                return int(payload[key])
            try:
                parsed = int(raw)
            except (TypeError, ValueError):
                raise UserAuthValidationError(f"subscription rule {key} must be an integer")
            return max(minimum, min(maximum, parsed))

        payload["pending_ratio_delta_ge"] = _read_float("pending_ratio_delta_ge", 0.0, 1.0)
        payload["median_days_delta_ge"] = _read_float("median_days_delta_ge", 0.0, 365.0)
        payload["p90_days_delta_ge"] = _read_float("p90_days_delta_ge", 0.0, 730.0)
        payload["long_tail_ratio_delta_ge"] = _read_float("long_tail_ratio_delta_ge", 0.0, 1.0)
        payload["min_sample_size"] = _read_int("min_sample_size", 1, 5000)
        payload["cooldown_hours"] = _read_int("cooldown_hours", 1, 168)
        return payload

    def _validate_password(self, password: str) -> str:
        normalized = password or ""
        if len(normalized) < USER_PASSWORD_MIN_LENGTH:
            raise UserAuthValidationError(
                f"password length must be >= {USER_PASSWORD_MIN_LENGTH}"
            )
        return normalized

    @staticmethod
    def _serialize_filters(filters: dict[str, Any]) -> str:
        if not isinstance(filters, dict):
            raise UserAuthValidationError("filters must be an object")
        return json.dumps(filters, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _parse_filters(raw: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    @classmethod
    def _hash_password(cls, password: str, salt: bytes | None = None) -> str:
        salt_bytes = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt_bytes,
            cls._PASSWORD_HASH_ITERATIONS,
        )
        return (
            f"pbkdf2_sha256${cls._PASSWORD_HASH_ITERATIONS}$"
            f"{salt_bytes.hex()}${digest.hex()}"
        )

    @classmethod
    def _verify_password(cls, password: str, encoded_hash: str) -> bool:
        try:
            algorithm, iterations_raw, salt_hex, digest_hex = encoded_hash.split("$", maxsplit=3)
            if algorithm != "pbkdf2_sha256":
                return False
            iterations = int(iterations_raw)
            salt = bytes.fromhex(salt_hex)
        except (ValueError, TypeError):
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return secrets.compare_digest(digest.hex(), digest_hex)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db_path = USER_DB_PATH
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with self._lock:
                self._ensure_schema(conn)
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id
                ON user_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at
                ON user_sessions(expires_at);

            CREATE TABLE IF NOT EXISTS user_filter_presets (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                filters_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, name)
            );

            CREATE INDEX IF NOT EXISTS idx_user_filter_presets_user_id
                ON user_filter_presets(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_filter_presets_updated_at
                ON user_filter_presets(updated_at DESC);

            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                preset_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                rule_json TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(preset_id) REFERENCES user_filter_presets(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_enabled
                ON user_subscriptions(user_id, enabled, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_user_subscriptions_preset
                ON user_subscriptions(preset_id);

            CREATE TABLE IF NOT EXISTS user_notifications (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                subscription_id TEXT,
                level TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                read_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(subscription_id) REFERENCES user_subscriptions(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_user_notifications_user_created
                ON user_notifications(user_id, created_at DESC);
            """
        )

    def _prune_expired_sessions(self, conn: sqlite3.Connection) -> None:
        now_iso = self._now_utc().isoformat(timespec="seconds")
        conn.execute(
            "DELETE FROM user_sessions WHERE expires_at <= ?",
            (now_iso,),
        )

    def _create_session(self, conn: sqlite3.Connection, *, user_id: int, username: str) -> UserSession:
        now = self._now_utc()
        expires_at = now + timedelta(seconds=USER_SESSION_TTL_SECONDS)
        token = secrets.token_urlsafe(32)
        conn.execute(
            """
            INSERT INTO user_sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                token,
                user_id,
                now.isoformat(timespec="seconds"),
                expires_at.isoformat(timespec="seconds"),
            ),
        )
        return UserSession(
            user_id=user_id,
            username=username,
            token=token,
            expires_at=expires_at,
        )

    def register(self, username: str, password: str) -> UserSession:
        normalized_username = self._normalize_username(username)
        normalized_password = self._validate_password(password)
        now_iso = self._now_utc().isoformat(timespec="seconds")
        password_hash = self._hash_password(normalized_password)

        with self._connect() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO users (username, password_hash, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (normalized_username, password_hash, now_iso, now_iso),
                )
            except sqlite3.IntegrityError as exc:
                raise UserAuthConflictError("username already exists") from exc

            user_id = int(cursor.lastrowid)
            return self._create_session(conn, user_id=user_id, username=normalized_username)

    def login(self, username: str, password: str) -> UserSession:
        normalized_username = self._normalize_username(username)
        normalized_password = self._validate_password(password)

        with self._connect() as conn:
            self._prune_expired_sessions(conn)
            row = conn.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (normalized_username,),
            ).fetchone()
            if row is None:
                raise UserAuthUnauthorizedError("username or password invalid")

            if not self._verify_password(normalized_password, str(row["password_hash"])):
                raise UserAuthUnauthorizedError("username or password invalid")

            return self._create_session(
                conn,
                user_id=int(row["id"]),
                username=str(row["username"]),
            )

    def get_session(self, token: str) -> dict[str, Any] | None:
        normalized_token = self._normalize_token(token)
        if not normalized_token:
            return None

        with self._connect() as conn:
            self._prune_expired_sessions(conn)
            row = conn.execute(
                """
                SELECT u.id AS user_id, u.username AS username, s.token AS token, s.expires_at AS expires_at
                FROM user_sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ?
                """,
                (normalized_token,),
            ).fetchone()
            if row is None:
                return None
            return {
                "user_id": int(row["user_id"]),
                "username": str(row["username"]),
                "token": str(row["token"]),
                "expires_at": str(row["expires_at"]),
            }

    def logout(self, token: str) -> bool:
        normalized_token = self._normalize_token(token)
        if not normalized_token:
            return False

        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM user_sessions WHERE token = ?",
                (normalized_token,),
            )
            return cursor.rowcount > 0

    def _preset_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "name": str(row["name"]),
            "filters": self._parse_filters(str(row["filters_json"])),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def list_filter_presets(self, user_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, filters_json, created_at, updated_at
                FROM user_filter_presets
                WHERE user_id = ?
                ORDER BY updated_at DESC, created_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [self._preset_from_row(row) for row in rows]

    def create_filter_preset(self, user_id: int, name: str, filters: dict[str, Any]) -> dict[str, Any]:
        normalized_name = self._normalize_preset_name(name)
        filters_json = self._serialize_filters(filters)
        preset_id = uuid4().hex
        now_iso = self._now_utc().isoformat(timespec="seconds")

        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(1) AS total FROM user_filter_presets WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            total = int(row["total"]) if row is not None else 0
            if total >= USER_MAX_FILTER_PRESETS:
                raise UserAuthLimitError(
                    f"preset limit reached ({USER_MAX_FILTER_PRESETS})"
                )

            try:
                conn.execute(
                    """
                    INSERT INTO user_filter_presets (id, user_id, name, filters_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (preset_id, user_id, normalized_name, filters_json, now_iso, now_iso),
                )
            except sqlite3.IntegrityError as exc:
                raise UserAuthConflictError("preset name already exists") from exc

            created_row = conn.execute(
                """
                SELECT id, name, filters_json, created_at, updated_at
                FROM user_filter_presets
                WHERE user_id = ? AND id = ?
                """,
                (user_id, preset_id),
            ).fetchone()
            if created_row is None:
                raise UserAuthError("preset create failed")
            return self._preset_from_row(created_row)

    def update_filter_preset(
        self,
        user_id: int,
        preset_id: str,
        *,
        name: str | None,
        filters: dict[str, Any] | None,
    ) -> dict[str, Any]:
        normalized_id = (preset_id or "").strip()
        if not normalized_id:
            raise UserAuthValidationError("preset id is required")

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, name, filters_json, created_at, updated_at
                FROM user_filter_presets
                WHERE user_id = ? AND id = ?
                """,
                (user_id, normalized_id),
            ).fetchone()
            if row is None:
                raise UserAuthNotFoundError("preset not found")

            next_name = self._normalize_preset_name(name) if name is not None else str(row["name"])
            next_filters_json = self._serialize_filters(filters) if filters is not None else str(row["filters_json"])
            if name is None and filters is None:
                raise UserAuthValidationError("name or filters is required")

            try:
                conn.execute(
                    """
                    UPDATE user_filter_presets
                    SET name = ?, filters_json = ?, updated_at = ?
                    WHERE user_id = ? AND id = ?
                    """,
                    (
                        next_name,
                        next_filters_json,
                        self._now_utc().isoformat(timespec="seconds"),
                        user_id,
                        normalized_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise UserAuthConflictError("preset name already exists") from exc

            updated_row = conn.execute(
                """
                SELECT id, name, filters_json, created_at, updated_at
                FROM user_filter_presets
                WHERE user_id = ? AND id = ?
                """,
                (user_id, normalized_id),
            ).fetchone()
            if updated_row is None:
                raise UserAuthNotFoundError("preset not found")
            return self._preset_from_row(updated_row)

    def delete_filter_preset(self, user_id: int, preset_id: str) -> bool:
        normalized_id = (preset_id or "").strip()
        if not normalized_id:
            raise UserAuthValidationError("preset id is required")

        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM user_filter_presets WHERE user_id = ? AND id = ?",
                (user_id, normalized_id),
            )
            return cursor.rowcount > 0

    def _subscription_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "preset_id": str(row["preset_id"]),
            "preset_name": str(row["preset_name"]),
            "channel": str(row["channel"]),
            "rule": self._parse_filters(str(row["rule_json"])),
            "enabled": bool(int(row["enabled"])),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def list_subscriptions(self, user_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.id, s.preset_id, p.name AS preset_name, s.channel, s.rule_json,
                       s.enabled, s.created_at, s.updated_at
                FROM user_subscriptions s
                JOIN user_filter_presets p ON p.id = s.preset_id AND p.user_id = s.user_id
                WHERE s.user_id = ?
                ORDER BY s.updated_at DESC, s.created_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [self._subscription_from_row(row) for row in rows]

    def create_subscription(
        self,
        user_id: int,
        *,
        preset_id: str,
        channel: str = "in_app",
        rule: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        normalized_preset_id = (preset_id or "").strip()
        if not normalized_preset_id:
            raise UserAuthValidationError("preset id is required")

        normalized_channel = self._normalize_subscription_channel(channel)
        normalized_rule = self._normalize_subscription_rule(rule)
        now_iso = self._now_utc().isoformat(timespec="seconds")
        subscription_id = uuid4().hex

        with self._connect() as conn:
            preset_row = conn.execute(
                "SELECT id FROM user_filter_presets WHERE user_id = ? AND id = ?",
                (user_id, normalized_preset_id),
            ).fetchone()
            if preset_row is None:
                raise UserAuthNotFoundError("preset not found")

            duplicate = conn.execute(
                """
                SELECT id
                FROM user_subscriptions
                WHERE user_id = ? AND preset_id = ? AND channel = ?
                """,
                (user_id, normalized_preset_id, normalized_channel),
            ).fetchone()
            if duplicate is not None:
                raise UserAuthConflictError("subscription already exists")

            conn.execute(
                """
                INSERT INTO user_subscriptions (
                    id, user_id, preset_id, channel, rule_json, enabled, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    subscription_id,
                    user_id,
                    normalized_preset_id,
                    normalized_channel,
                    json.dumps(normalized_rule, ensure_ascii=False, separators=(",", ":")),
                    1 if enabled else 0,
                    now_iso,
                    now_iso,
                ),
            )

            created = conn.execute(
                """
                SELECT s.id, s.preset_id, p.name AS preset_name, s.channel, s.rule_json,
                       s.enabled, s.created_at, s.updated_at
                FROM user_subscriptions s
                JOIN user_filter_presets p ON p.id = s.preset_id AND p.user_id = s.user_id
                WHERE s.user_id = ? AND s.id = ?
                """,
                (user_id, subscription_id),
            ).fetchone()
            if created is None:
                raise UserAuthError("subscription create failed")
            return self._subscription_from_row(created)

    def update_subscription(
        self,
        user_id: int,
        subscription_id: str,
        *,
        preset_id: str | None = None,
        channel: str | None = None,
        rule: dict[str, Any] | None = None,
        enabled: bool | None = None,
    ) -> dict[str, Any]:
        normalized_subscription_id = (subscription_id or "").strip()
        if not normalized_subscription_id:
            raise UserAuthValidationError("subscription id is required")

        with self._connect() as conn:
            current = conn.execute(
                """
                SELECT s.id, s.preset_id, p.name AS preset_name, s.channel, s.rule_json,
                       s.enabled, s.created_at, s.updated_at
                FROM user_subscriptions s
                JOIN user_filter_presets p ON p.id = s.preset_id AND p.user_id = s.user_id
                WHERE s.user_id = ? AND s.id = ?
                """,
                (user_id, normalized_subscription_id),
            ).fetchone()
            if current is None:
                raise UserAuthNotFoundError("subscription not found")

            next_preset_id = str(current["preset_id"])
            if preset_id is not None:
                next_preset_id = (preset_id or "").strip()
                if not next_preset_id:
                    raise UserAuthValidationError("preset id is required")
                preset_row = conn.execute(
                    "SELECT id FROM user_filter_presets WHERE user_id = ? AND id = ?",
                    (user_id, next_preset_id),
                ).fetchone()
                if preset_row is None:
                    raise UserAuthNotFoundError("preset not found")

            next_channel = str(current["channel"])
            if channel is not None:
                next_channel = self._normalize_subscription_channel(channel)

            next_rule = self._parse_filters(str(current["rule_json"]))
            if rule is not None:
                next_rule = self._normalize_subscription_rule(rule)

            next_enabled = bool(int(current["enabled"])) if enabled is None else bool(enabled)

            if (
                preset_id is None
                and channel is None
                and rule is None
                and enabled is None
            ):
                raise UserAuthValidationError("at least one field must be provided")

            duplicate = conn.execute(
                """
                SELECT id
                FROM user_subscriptions
                WHERE user_id = ? AND preset_id = ? AND channel = ? AND id != ?
                """,
                (user_id, next_preset_id, next_channel, normalized_subscription_id),
            ).fetchone()
            if duplicate is not None:
                raise UserAuthConflictError("subscription already exists")

            conn.execute(
                """
                UPDATE user_subscriptions
                SET preset_id = ?, channel = ?, rule_json = ?, enabled = ?, updated_at = ?
                WHERE user_id = ? AND id = ?
                """,
                (
                    next_preset_id,
                    next_channel,
                    json.dumps(next_rule, ensure_ascii=False, separators=(",", ":")),
                    1 if next_enabled else 0,
                    self._now_utc().isoformat(timespec="seconds"),
                    user_id,
                    normalized_subscription_id,
                ),
            )

            updated = conn.execute(
                """
                SELECT s.id, s.preset_id, p.name AS preset_name, s.channel, s.rule_json,
                       s.enabled, s.created_at, s.updated_at
                FROM user_subscriptions s
                JOIN user_filter_presets p ON p.id = s.preset_id AND p.user_id = s.user_id
                WHERE s.user_id = ? AND s.id = ?
                """,
                (user_id, normalized_subscription_id),
            ).fetchone()
            if updated is None:
                raise UserAuthNotFoundError("subscription not found")
            return self._subscription_from_row(updated)

    def delete_subscription(self, user_id: int, subscription_id: str) -> bool:
        normalized_subscription_id = (subscription_id or "").strip()
        if not normalized_subscription_id:
            raise UserAuthValidationError("subscription id is required")

        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM user_subscriptions WHERE user_id = ? AND id = ?",
                (user_id, normalized_subscription_id),
            )
            return cursor.rowcount > 0

    def _notification_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "subscription_id": str(row["subscription_id"]) if row["subscription_id"] else None,
            "level": str(row["level"]),
            "title": str(row["title"]),
            "body": str(row["body"]),
            "read_at": str(row["read_at"]) if row["read_at"] else None,
            "created_at": str(row["created_at"]),
        }

    def list_notifications(
        self,
        user_id: int,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        safe_limit = max(1, min(200, int(limit)))
        safe_offset = max(0, int(offset))

        with self._connect() as conn:
            where_sql = "WHERE user_id = ?"
            args: list[Any] = [user_id]
            if unread_only:
                where_sql += " AND read_at IS NULL"

            total_row = conn.execute(
                f"SELECT COUNT(1) AS total FROM user_notifications {where_sql}",
                tuple(args),
            ).fetchone()
            total = int(total_row["total"]) if total_row is not None else 0

            unread_row = conn.execute(
                "SELECT COUNT(1) AS total FROM user_notifications WHERE user_id = ? AND read_at IS NULL",
                (user_id,),
            ).fetchone()
            unread_count = int(unread_row["total"]) if unread_row is not None else 0

            rows = conn.execute(
                f"""
                SELECT id, subscription_id, level, title, body, read_at, created_at
                FROM user_notifications
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (*args, safe_limit, safe_offset),
            ).fetchall()

            return {
                "total": total,
                "unread_count": unread_count,
                "items": [self._notification_from_row(row) for row in rows],
            }

    def mark_notification_read(self, user_id: int, notification_id: str) -> dict[str, Any]:
        normalized_notification_id = (notification_id or "").strip()
        if not normalized_notification_id:
            raise UserAuthValidationError("notification id is required")

        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT id, subscription_id, level, title, body, read_at, created_at
                FROM user_notifications
                WHERE user_id = ? AND id = ?
                """,
                (user_id, normalized_notification_id),
            ).fetchone()
            if existing is None:
                raise UserAuthNotFoundError("notification not found")

            if existing["read_at"] is None:
                conn.execute(
                    """
                    UPDATE user_notifications
                    SET read_at = ?
                    WHERE user_id = ? AND id = ?
                    """,
                    (
                        self._now_utc().isoformat(timespec="seconds"),
                        user_id,
                        normalized_notification_id,
                    ),
                )

            updated = conn.execute(
                """
                SELECT id, subscription_id, level, title, body, read_at, created_at
                FROM user_notifications
                WHERE user_id = ? AND id = ?
                """,
                (user_id, normalized_notification_id),
            ).fetchone()
            if updated is None:
                raise UserAuthNotFoundError("notification not found")
            return self._notification_from_row(updated)

    def mark_all_notifications_read(self, user_id: int) -> int:
        with self._connect() as conn:
            now_iso = self._now_utc().isoformat(timespec="seconds")
            cursor = conn.execute(
                """
                UPDATE user_notifications
                SET read_at = ?
                WHERE user_id = ? AND read_at IS NULL
                """,
                (now_iso, user_id),
            )
            return int(cursor.rowcount)

    @staticmethod
    def _filters_as_values(filters: dict[str, Any], key: str, *, upper: bool = False) -> set[str] | None:
        raw = filters.get(key)
        values: set[str] = set()

        if isinstance(raw, str):
            values = {item.strip() for item in raw.split(",") if item.strip()}
        elif isinstance(raw, list):
            values = {str(item).strip() for item in raw if str(item).strip()}

        if not values:
            return None
        if upper:
            return {item.upper() for item in values}
        return values

    def _apply_preset_filters(self, rows: list[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
        has_note_raw = filters.get("has_note")
        has_note = has_note_raw if isinstance(has_note_raw, bool) else None
        search_text_raw = filters.get("search_text")
        search_text = str(search_text_raw or "").strip() or None

        return analytics.filter_rows(
            rows,
            visa_types=self._filters_as_values(filters, "visa_types", upper=True),
            consulates=self._filters_as_values(filters, "consulates"),
            statuses=self._filters_as_values(filters, "statuses"),
            entries=self._filters_as_values(filters, "entries"),
            months=self._filters_as_values(filters, "months"),
            majors=self._filters_as_values(filters, "majors"),
            major_categories_l1=self._filters_as_values(filters, "major_categories_l1"),
            major_categories_l2=self._filters_as_values(filters, "major_categories_l2"),
            employers=self._filters_as_values(filters, "employers"),
            detail_cities=self._filters_as_values(filters, "detail_cities"),
            detail_states=self._filters_as_values(filters, "detail_states"),
            has_note=has_note,
            search_text=search_text,
        )

    def evaluate_subscriptions(
        self,
        *,
        rows: list[dict[str, Any]],
        previous_rows: list[dict[str, Any]] | None,
    ) -> int:
        if not rows:
            return 0

        baseline_rows = previous_rows or []
        if not baseline_rows:
            return 0

        created_count = 0
        with self._connect() as conn:
            subscriptions = conn.execute(
                """
                SELECT s.id, s.user_id, s.preset_id, p.name AS preset_name, p.filters_json, s.rule_json,
                       s.enabled, s.channel
                FROM user_subscriptions s
                JOIN user_filter_presets p ON p.id = s.preset_id AND p.user_id = s.user_id
                WHERE s.enabled = 1 AND s.channel = 'in_app'
                """
            ).fetchall()

            for subscription in subscriptions:
                try:
                    preset_filters = self._parse_filters(str(subscription["filters_json"]))
                    current_subset = self._apply_preset_filters(rows, preset_filters)
                    previous_subset = self._apply_preset_filters(baseline_rows, preset_filters)

                    current_overview = analytics.overview_stats(current_subset)
                    previous_overview = analytics.overview_stats(previous_subset)
                    current_total = int(current_overview.get("total_cases") or 0)
                    previous_total = int(previous_overview.get("total_cases") or 0)

                    rule_payload = self._parse_filters(str(subscription["rule_json"]))
                    rule = self._normalize_subscription_rule(rule_payload)
                    min_sample_size = int(rule["min_sample_size"])
                    if current_total < min_sample_size or previous_total < min_sample_size:
                        continue

                    current_pending_ratio = (
                        float(current_overview.get("pending_cases") or 0) / current_total
                        if current_total
                        else 0.0
                    )
                    previous_pending_ratio = (
                        float(previous_overview.get("pending_cases") or 0) / previous_total
                        if previous_total
                        else 0.0
                    )

                    current_median = float(current_overview.get("median_days") or 0.0)
                    previous_median = float(previous_overview.get("median_days") or 0.0)
                    current_p90 = float(current_overview.get("p90_days") or 0.0)
                    previous_p90 = float(previous_overview.get("p90_days") or 0.0)
                    current_tail = float(current_overview.get("long_tail_90plus_ratio") or 0.0)
                    previous_tail = float(previous_overview.get("long_tail_90plus_ratio") or 0.0)

                    reasons: list[str] = []
                    if current_pending_ratio - previous_pending_ratio >= float(rule["pending_ratio_delta_ge"]):
                        reasons.append(
                            f"Pending 比率上升到 {current_pending_ratio:.1%}（之前 {previous_pending_ratio:.1%}）"
                        )
                    if current_median - previous_median >= float(rule["median_days_delta_ge"]):
                        reasons.append(
                            f"中位耗时上升到 {current_median:.1f} 天（之前 {previous_median:.1f} 天）"
                        )
                    if current_p90 - previous_p90 >= float(rule["p90_days_delta_ge"]):
                        reasons.append(
                            f"P90 上升到 {current_p90:.1f} 天（之前 {previous_p90:.1f} 天）"
                        )
                    if current_tail - previous_tail >= float(rule["long_tail_ratio_delta_ge"]):
                        reasons.append(
                            f"长尾占比上升到 {current_tail:.1%}（之前 {previous_tail:.1%}）"
                        )

                    if not reasons:
                        continue

                    now = self._now_utc()
                    cooldown_hours = int(rule["cooldown_hours"])
                    window_start = (now - timedelta(hours=cooldown_hours)).isoformat(timespec="seconds")
                    title = f"筛选【{subscription['preset_name']}】出现波动"
                    body = "；".join(reasons)

                    duplicate = conn.execute(
                        """
                        SELECT id
                        FROM user_notifications
                        WHERE user_id = ?
                          AND subscription_id = ?
                          AND title = ?
                          AND body = ?
                          AND read_at IS NULL
                          AND created_at >= ?
                        LIMIT 1
                        """,
                        (
                            int(subscription["user_id"]),
                            str(subscription["id"]),
                            title,
                            body,
                            window_start,
                        ),
                    ).fetchone()
                    if duplicate is not None:
                        continue

                    conn.execute(
                        """
                        INSERT INTO user_notifications (
                            id, user_id, subscription_id, level, title, body, read_at, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            uuid4().hex,
                            int(subscription["user_id"]),
                            str(subscription["id"]),
                            "warning" if len(reasons) >= 2 else "info",
                            title,
                            body,
                            None,
                            now.isoformat(timespec="seconds"),
                        ),
                    )
                    created_count += 1
                except UserAuthValidationError:
                    continue

        return created_count


user_auth_service = UserAuthService()
