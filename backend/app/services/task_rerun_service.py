"""Create an isolated full-task branch in one transaction, without starting execution."""

import hashlib
import json
from datetime import datetime
from uuid import uuid4

from app.db import get_db_connection
from app.services.audit_service import safe_record_audit_event
from app.services.task_status_service import normalize_task_status

TERMINAL_STATUSES = {"completed", "failed", "cancelled", "timed_out"}


class TaskRerunError(Exception):
    def __init__(self, status_code: int, code: str):
        super().__init__(code)
        self.status_code, self.code = status_code, code


def create_task_rerun(*, user_id: str, parent_task_id: str, user_input: str | None,
                      idempotency_key: str) -> dict:
    edited = user_input.strip() if user_input is not None else None
    if edited is not None and (not edited or len(edited) > 64_000):
        raise TaskRerunError(422, "rerun_input_invalid")
    request_hash = hashlib.sha256(json.dumps(
        {"parent_task_id": parent_task_id, "user_input": edited}, sort_keys=True,
    ).encode()).hexdigest()
    with get_db_connection() as connection:
        lock_key = int.from_bytes(hashlib.sha256(f"task-rerun:{user_id}".encode()).digest()[:8], "big", signed=True)
        connection.execute("SELECT pg_advisory_xact_lock(?)", (lock_key,))
        existing = connection.execute(
            """SELECT r.request_hash, r.parent_task_id, t.id AS task_id, t.session_id, t.status
               FROM task_reruns r JOIN tasks t ON t.id = r.task_id
               WHERE r.user_id = ? AND t.user_id = ? AND r.idempotency_key = ?""",
            (user_id, user_id, idempotency_key),
        ).fetchone()
        if existing:
            if existing["request_hash"] != request_hash:
                raise TaskRerunError(409, "rerun_idempotency_conflict")
            return {key: existing[key] for key in ("task_id", "session_id", "status", "parent_task_id")}
        parent = connection.execute(
            "SELECT prompt, status FROM tasks WHERE id = ? AND user_id = ? FOR SHARE",
            (parent_task_id, user_id),
        ).fetchone()
        if not parent:
            raise TaskRerunError(404, "task_not_found")
        if normalize_task_status(parent["status"]) not in TERMINAL_STATUSES:
            raise TaskRerunError(409, "rerun_parent_not_terminal")
        prompt = edited if edited is not None else parent["prompt"]
        if not prompt.strip() or len(prompt) > 64_000:
            raise TaskRerunError(422, "rerun_input_invalid")
        # Use the existing task/session timestamp convention so recent-item sorting stays consistent.
        now, task_id, session_id = datetime.now().isoformat(), str(uuid4()), str(uuid4())
        connection.execute(
            "INSERT INTO sessions(id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, prompt.strip()[:40], now, now),
        )
        connection.execute(
            """INSERT INTO tasks(id, user_id, session_id, prompt, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'queued', ?, ?)""",
            (task_id, user_id, session_id, prompt, now, now),
        )
        connection.execute(
            """INSERT INTO messages(id, user_id, session_id, task_id, role, content, created_at)
               VALUES (?, ?, ?, ?, 'user', ?, ?)""",
            (str(uuid4()), user_id, session_id, task_id, prompt, now),
        )
        connection.execute(
            """INSERT INTO task_reruns(task_id, user_id, parent_task_id, idempotency_key, request_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (task_id, user_id, parent_task_id, idempotency_key, request_hash, now),
        )
        connection.commit()
    safe_record_audit_event(user_id=user_id, event_type="task_rerun_created", detail={
        "task_id": task_id, "session_id": session_id, "parent_task_id": parent_task_id,
        "input_edited": edited is not None, "prompt_length": len(prompt),
    })
    return {"task_id": task_id, "session_id": session_id, "status": "queued", "parent_task_id": parent_task_id}


def get_task_reruns(*, user_id: str, task_id: str, limit: int, offset: int) -> dict:
    with get_db_connection() as connection:
        if not connection.execute("SELECT id FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)).fetchone():
            raise TaskRerunError(404, "task_not_found")
        parent = connection.execute(
            "SELECT parent_task_id FROM task_reruns WHERE task_id = ? AND user_id = ?",
            (task_id, user_id),
        ).fetchone()
        rows = connection.execute(
            """SELECT t.id AS task_id, t.session_id, t.status, r.created_at
               FROM task_reruns r JOIN tasks t ON t.id = r.task_id
               WHERE r.parent_task_id = ? AND r.user_id = ? AND t.user_id = ?
               ORDER BY r.created_at DESC, t.id DESC LIMIT ? OFFSET ?""",
            (task_id, user_id, user_id, limit, offset),
        ).fetchall()
        total = connection.execute(
            """SELECT COUNT(*) AS total FROM task_reruns r JOIN tasks t ON t.id = r.task_id
               WHERE r.parent_task_id = ? AND r.user_id = ? AND t.user_id = ?""",
            (task_id, user_id, user_id),
        ).fetchone()["total"]
    return {"task_id": task_id, "is_rerun": parent is not None,
            "parent_task_id": parent["parent_task_id"] if parent else None,
            "items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset,
            "has_more": offset + len(rows) < total}
