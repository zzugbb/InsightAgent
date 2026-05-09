from __future__ import annotations

import re
from datetime import datetime
from uuid import uuid4

from app.db import get_db_connection
from app.security import hash_password, verify_password


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
USER_ROLE_ADMIN = "admin"
USER_ROLE_USER = "user"
ALLOWED_USER_ROLES = {USER_ROLE_ADMIN, USER_ROLE_USER}


def _now_iso() -> str:
    return datetime.now().isoformat()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def normalize_user_role(role: str | None) -> str:
    value = (role or USER_ROLE_USER).strip().lower()
    if value not in ALLOWED_USER_ROLES:
        return USER_ROLE_USER
    return value


def create_user(
    *,
    email: str,
    password: str,
    display_name: str | None = None,
    role: str | None = None,
) -> dict:
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
        count_row = connection.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
        user_count = int((count_row or {}).get("cnt") or 0)
        resolved_role = normalize_user_role(role)
        # 首个注册用户自动授予 admin，作为最小 RBAC 引导入口。
        if user_count == 0:
            resolved_role = USER_ROLE_ADMIN

        connection.execute(
            """
            INSERT INTO users(id, email, display_name, role, password_salt, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, normalized, name, resolved_role, salt, digest, now, now),
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
            SELECT id, email, display_name, role, created_at, updated_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return None
    record = dict(row)
    record["role"] = normalize_user_role(record.get("role"))
    return record


def get_user_auth_row_by_email(email: str) -> dict | None:
    normalized = normalize_email(email)
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, display_name, role, password_salt, password_hash, created_at, updated_at
            FROM users
            WHERE email = ?
            """,
            (normalized,),
        ).fetchone()
    if not row:
        return None
    record = dict(row)
    record["role"] = normalize_user_role(record.get("role"))
    return record


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
        "role": normalize_user_role(row.get("role")),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def list_users(*, limit: int, offset: int) -> tuple[list[dict], int]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, email, display_name, role, created_at, updated_at
            FROM users
            ORDER BY created_at DESC
            LIMIT ?
            OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        total_row = connection.execute("SELECT COUNT(*) AS cnt FROM users").fetchone() or {}
    total = int(total_row.get("cnt") or 0)
    items: list[dict] = []
    for row in rows:
        record = dict(row)
        record["role"] = normalize_user_role(record.get("role"))
        items.append(record)
    return items, total
