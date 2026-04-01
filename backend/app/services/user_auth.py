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


user_auth_service = UserAuthService()
