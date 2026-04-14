from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from app.config import get_settings
from app.db import get_db_connection
from app.security import create_refresh_token, hash_refresh_token
from app.services.auth_service import get_user_by_id


def _now_iso() -> str:
    return datetime.now().isoformat()


def _parse_iso(raw: object) -> datetime | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _build_expire_at_iso(now: datetime) -> str:
    ttl_days = int(get_settings().auth_refresh_token_ttl_days)
    return (now + timedelta(days=ttl_days)).isoformat()


def _load_session_by_hash(refresh_token_hash: str) -> dict | None:
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                user_id,
                refresh_token_hash,
                user_agent,
                ip_address,
                created_at,
                updated_at,
                expires_at,
                last_used_at,
                revoked_at
            FROM auth_sessions
            WHERE refresh_token_hash = ?
            LIMIT 1
            """,
            (refresh_token_hash,),
        ).fetchone()
    return dict(row) if row else None


def _is_active_session(row: dict, now: datetime) -> bool:
    revoked_at = row.get("revoked_at")
    if isinstance(revoked_at, str) and revoked_at.strip():
        return False
    expires_at = _parse_iso(row.get("expires_at"))
    if expires_at is None:
        return False
    return expires_at > now


def issue_auth_tokens(
    *,
    user: dict,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> dict[str, object]:
    from app.security import create_access_token

    now = datetime.now()
    now_iso = now.isoformat()
    session_id = str(uuid4())
    refresh_token = create_refresh_token()
    refresh_token_hash = hash_refresh_token(refresh_token)
    expires_at = _build_expire_at_iso(now)

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO auth_sessions(
                id,
                user_id,
                refresh_token_hash,
                user_agent,
                ip_address,
                created_at,
                updated_at,
                expires_at,
                last_used_at,
                revoked_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                str(user["id"]),
                refresh_token_hash,
                user_agent,
                ip_address,
                now_iso,
                now_iso,
                expires_at,
                now_iso,
                None,
            ),
        )
        connection.commit()

    access_token = create_access_token(user_id=str(user["id"]), email=str(user["email"]))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "session_id": session_id,
        "user": user,
    }


def refresh_auth_tokens(
    *,
    refresh_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> dict[str, object] | None:
    incoming_hash = hash_refresh_token(refresh_token)
    session = _load_session_by_hash(incoming_hash)
    now = datetime.now()
    now_iso = now.isoformat()
    if session is None or not _is_active_session(session, now):
        return None

    user_id = str(session["user_id"])
    user = get_user_by_id(user_id)
    if user is None:
        return None

    next_refresh_token = create_refresh_token()
    next_refresh_hash = hash_refresh_token(next_refresh_token)
    expires_at = _build_expire_at_iso(now)
    session_id = str(session["id"])

    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE auth_sessions
            SET
                refresh_token_hash = ?,
                user_agent = COALESCE(?, user_agent),
                ip_address = COALESCE(?, ip_address),
                expires_at = ?,
                last_used_at = ?,
                updated_at = ?
            WHERE id = ? AND user_id = ? AND refresh_token_hash = ? AND revoked_at IS NULL
            """,
            (
                next_refresh_hash,
                user_agent,
                ip_address,
                expires_at,
                now_iso,
                now_iso,
                session_id,
                user_id,
                incoming_hash,
            ),
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return None
        connection.commit()

    from app.security import create_access_token

    access_token = create_access_token(user_id=user_id, email=str(user["email"]))
    return {
        "access_token": access_token,
        "refresh_token": next_refresh_token,
        "session_id": session_id,
        "user": user,
    }


def revoke_auth_session_by_refresh_token(*, user_id: str, refresh_token: str) -> bool:
    now_iso = _now_iso()
    refresh_hash = hash_refresh_token(refresh_token)
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = COALESCE(revoked_at, ?), updated_at = ?
            WHERE user_id = ? AND refresh_token_hash = ? AND revoked_at IS NULL
            """,
            (now_iso, now_iso, user_id, refresh_hash),
        )
        connection.commit()
        return cursor.rowcount > 0


def revoke_auth_session_by_id(*, user_id: str, session_id: str) -> bool:
    now_iso = _now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = COALESCE(revoked_at, ?), updated_at = ?
            WHERE user_id = ? AND id = ? AND revoked_at IS NULL
            """,
            (now_iso, now_iso, user_id, session_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def revoke_all_auth_sessions(*, user_id: str) -> int:
    now_iso = _now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = COALESCE(revoked_at, ?), updated_at = ?
            WHERE user_id = ? AND revoked_at IS NULL
            """,
            (now_iso, now_iso, user_id),
        )
        connection.commit()
        return cursor.rowcount


def list_auth_sessions(*, user_id: str) -> list[dict]:
    now_iso = _now_iso()
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                created_at,
                updated_at,
                expires_at,
                last_used_at,
                revoked_at,
                user_agent,
                ip_address,
                CASE
                    WHEN revoked_at IS NULL AND expires_at > ? THEN true
                    ELSE false
                END AS active
            FROM auth_sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (now_iso, user_id),
        ).fetchall()
    return [dict(row) for row in rows]
