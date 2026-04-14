from __future__ import annotations

import re
from datetime import datetime
from uuid import uuid4

from app.db import get_db_connection
from app.security import hash_password, verify_password


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _now_iso() -> str:
    return datetime.now().isoformat()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def create_user(*, email: str, password: str, display_name: str | None = None) -> dict:
    normalized = normalize_email(email)
    if not is_valid_email(normalized):
        raise ValueError("invalid email format")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")

    salt, digest = hash_password(password)
    user_id = str(uuid4())
    now = _now_iso()
    name = (display_name or "").strip()[:80] or None

    with get_db_connection() as connection:
        exists = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (normalized,),
        ).fetchone()
        if exists is not None:
            raise ValueError("email already exists")

        connection.execute(
            """
            INSERT INTO users(id, email, display_name, password_salt, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, normalized, name, salt, digest, now, now),
        )
        connection.commit()

    user = get_user_by_id(user_id)
    if user is None:
        raise RuntimeError("failed to read user after insert")
    return user


def get_user_by_id(user_id: str) -> dict | None:
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, display_name, created_at, updated_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def get_user_auth_row_by_email(email: str) -> dict | None:
    normalized = normalize_email(email)
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, display_name, password_salt, password_hash, created_at, updated_at
            FROM users
            WHERE email = ?
            """,
            (normalized,),
        ).fetchone()
    return dict(row) if row else None


def authenticate_user(*, email: str, password: str) -> dict | None:
    row = get_user_auth_row_by_email(email)
    if row is None:
        return None
    if not verify_password(
        password,
        salt_hex=str(row.get("password_salt") or ""),
        digest_hex=str(row.get("password_hash") or ""),
    ):
        return None
    return {
        "id": str(row["id"]),
        "email": str(row["email"]),
        "display_name": row["display_name"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }
