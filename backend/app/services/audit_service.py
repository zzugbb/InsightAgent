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
