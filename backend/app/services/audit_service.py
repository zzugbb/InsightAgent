from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from app.db import get_db_connection
from app.services.tool_runtime import (
    _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE,
    _redact_http_json_raw_fallback_value,
)

SUPPORTED_AUDIT_EVENT_TYPES = frozenset(
    {
        "login",
        "logout",
        "refresh",
        "settings_update",
        "settings_validate",
        "task_create",
        "task_cancel",
        "task_timeout",
        "task_failed",
        "rag_ingest",
        "rag_kb_clear",
        "rag_kb_delete",
    }
)


def _now_iso() -> str:
    return datetime.now().isoformat()


def normalize_audit_event_type(event_type: str) -> str:
    normalized = event_type.strip().lower()
    if not normalized:
        raise ValueError("event_type is required")
    if len(normalized) > 80:
        raise ValueError("event_type is too long (max 80)")
    return normalized


def is_supported_audit_event_type(event_type: str) -> bool:
    return normalize_audit_event_type(event_type) in SUPPORTED_AUDIT_EVENT_TYPES


def _redact_sensitive_event_detail_keys(value: object) -> object:
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            safe_key = (
                "[redacted]"
                if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(str(key))
                else str(key)
            )
            redacted[safe_key] = (
                "[redacted]"
                if safe_key == "[redacted]"
                else _redact_sensitive_event_detail_keys(item)
            )
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive_event_detail_keys(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_sensitive_event_detail_keys(item) for item in value)
    return value


def sanitize_audit_event_detail(
    detail: dict[str, object] | None,
) -> dict[str, object] | None:
    if not detail:
        return None
    redacted = _redact_http_json_raw_fallback_value(detail)
    if not isinstance(redacted, dict):
        return None
    safe_detail = _redact_sensitive_event_detail_keys(redacted)
    if isinstance(safe_detail, dict):
        return safe_detail
    return None


def record_audit_event(
    *,
    user_id: str | None,
    event_type: str,
    detail: dict[str, object] | None = None,
) -> None:
    normalized_event_type = normalize_audit_event_type(event_type)

    detail_json: str | None = None
    if detail:
        safe_detail = sanitize_audit_event_detail(detail)
        if safe_detail:
            detail_json = json.dumps(safe_detail, ensure_ascii=True, separators=(",", ":"))

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


def safe_record_audit_event(
    *,
    user_id: str | None,
    event_type: str,
    detail: dict[str, object] | None = None,
) -> None:
    try:
        record_audit_event(user_id=user_id, event_type=event_type, detail=detail)
    except Exception:
        # 审计日志采用 best-effort，不影响主流程
        return


def list_audit_logs(
    *,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    event_type: str | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
) -> list[dict]:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]

    normalized_event_type = event_type.strip().lower() if isinstance(event_type, str) else ""
    if normalized_event_type:
        conditions.append("event_type = ?")
        params.append(normalized_event_type)

    normalized_session_id = session_id.strip() if isinstance(session_id, str) else ""
    if normalized_session_id:
        conditions.append("event_detail_json IS NOT NULL")
        conditions.append("(event_detail_json::jsonb ->> 'session_id') = ?")
        params.append(normalized_session_id)

    normalized_task_id = task_id.strip() if isinstance(task_id, str) else ""
    if normalized_task_id:
        conditions.append("event_detail_json IS NOT NULL")
        conditions.append("(event_detail_json::jsonb ->> 'task_id') = ?")
        params.append(normalized_task_id)

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
    session_id: str | None = None,
    task_id: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
) -> int:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]

    normalized_event_type = event_type.strip().lower() if isinstance(event_type, str) else ""
    if normalized_event_type:
        conditions.append("event_type = ?")
        params.append(normalized_event_type)

    normalized_session_id = session_id.strip() if isinstance(session_id, str) else ""
    if normalized_session_id:
        conditions.append("event_detail_json IS NOT NULL")
        conditions.append("(event_detail_json::jsonb ->> 'session_id') = ?")
        params.append(normalized_session_id)

    normalized_task_id = task_id.strip() if isinstance(task_id, str) else ""
    if normalized_task_id:
        conditions.append("event_detail_json IS NOT NULL")
        conditions.append("(event_detail_json::jsonb ->> 'task_id') = ?")
        params.append(normalized_task_id)

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
