from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from app.db import get_db_connection


def _now_iso() -> str:
    return datetime.now().isoformat()


def record_audit_event(
    *,
    user_id: str | None,
    event_type: str,
    detail: dict[str, object] | None = None,
) -> None:
    normalized_event_type = event_type.strip().lower()
    if not normalized_event_type:
        raise ValueError("event_type is required")
    if len(normalized_event_type) > 80:
        raise ValueError("event_type is too long (max 80)")

    detail_json: str | None = None
    if detail:
        detail_json = json.dumps(detail, ensure_ascii=True, separators=(",", ":"))

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit_logs(id, user_id, event_type, event_detail_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                user_id.strip() if isinstance(user_id, str) and user_id.strip() else None,
                normalized_event_type,
                detail_json,
                _now_iso(),
            ),
        )
        connection.commit()


def list_audit_logs(
    *,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    event_type: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
) -> list[dict]:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]

    normalized_event_type = event_type.strip().lower() if isinstance(event_type, str) else ""
    if normalized_event_type:
        conditions.append("event_type = ?")
        params.append(normalized_event_type)

    if isinstance(start_at, str) and start_at.strip():
        conditions.append("created_at >= ?")
        params.append(start_at.strip())
    if isinstance(end_at, str) and end_at.strip():
        conditions.append("created_at <= ?")
        params.append(end_at.strip())

    where_sql = " AND ".join(conditions)
    with get_db_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT id, event_type, event_detail_json, created_at
            FROM audit_logs
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple([*params, limit, offset]),
        ).fetchall()
    return [dict(row) for row in rows]


def count_audit_logs(
    *,
    user_id: str,
    event_type: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
) -> int:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]

    normalized_event_type = event_type.strip().lower() if isinstance(event_type, str) else ""
    if normalized_event_type:
        conditions.append("event_type = ?")
        params.append(normalized_event_type)

    if isinstance(start_at, str) and start_at.strip():
        conditions.append("created_at >= ?")
        params.append(start_at.strip())
    if isinstance(end_at, str) and end_at.strip():
        conditions.append("created_at <= ?")
        params.append(end_at.strip())

    where_sql = " AND ".join(conditions)
    with get_db_connection() as connection:
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS n
            FROM audit_logs
            WHERE {where_sql}
            """,
            tuple(params),
        ).fetchone()
    return int(row["n"]) if row else 0
