import json
from datetime import datetime
from uuid import uuid4

from app.db import get_db_connection


def _now_iso() -> str:
    return datetime.now().isoformat()


def _build_session_title(prompt: str) -> str:
    normalized = " ".join(prompt.strip().split())
    return normalized[:60] or "New Session"


def _normalize_trace_steps(trace_steps: list[dict]) -> list[dict]:
    normalized_steps: list[dict] = []
    for index, step in enumerate(trace_steps, start=1):
        normalized_step = dict(step)
        normalized_step["seq"] = (
            normalized_step["seq"]
            if isinstance(normalized_step.get("seq"), int)
            else index
        )
        normalized_steps.append(normalized_step)
    return normalized_steps


def ensure_session(prompt: str, session_id: str | None = None) -> str:
    current_time = _now_iso()
    resolved_session_id = session_id or str(uuid4())
    title = _build_session_title(prompt)

    with get_db_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM sessions WHERE id = ?",
            (resolved_session_id,),
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO sessions(id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (resolved_session_id, title, current_time, current_time),
            )
        else:
            connection.execute(
                """
                UPDATE sessions
                SET updated_at = ?
                WHERE id = ?
                """,
                (current_time, resolved_session_id),
            )
        connection.commit()

    return resolved_session_id


def create_task(
    session_id: str,
    prompt: str,
    task_id: str | None = None,
    status: str = "running",
) -> str:
    current_time = _now_iso()
    resolved_task_id = task_id or str(uuid4())

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO tasks(id, session_id, prompt, status, trace_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (resolved_task_id, session_id, prompt, status, None, current_time, current_time),
        )
        connection.commit()

    return resolved_task_id


def create_message(
    session_id: str,
    role: str,
    content: str,
    task_id: str | None = None,
) -> str:
    message_id = str(uuid4())
    current_time = _now_iso()

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO messages(id, session_id, task_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (message_id, session_id, task_id, role, content, current_time),
        )
        connection.execute(
            """
            UPDATE sessions
            SET updated_at = ?
            WHERE id = ?
            """,
            (current_time, session_id),
        )
        connection.commit()

    return message_id


def update_task_status(task_id: str, status: str) -> None:
    current_time = _now_iso()

    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, current_time, task_id),
        )
        connection.commit()


def complete_task(
    task_id: str,
    trace_steps: list[dict],
    status: str = "completed",
) -> None:
    current_time = _now_iso()
    normalized_trace_steps = _normalize_trace_steps(trace_steps)

    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET status = ?, trace_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                json.dumps(normalized_trace_steps, ensure_ascii=False),
                current_time,
                task_id,
            ),
        )
        connection.commit()


def create_session_record(title: str | None = None) -> dict:
    """Insert an empty session row (no messages yet)."""
    session_id = str(uuid4())
    current_time = _now_iso()
    raw = (title or "新会话").strip()
    resolved_title = raw[:120] if raw else "新会话"

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO sessions(id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, resolved_title, current_time, current_time),
        )
        connection.commit()

    row = get_session(session_id)
    if row is None:
        raise RuntimeError("Failed to read session after insert")
    return row


def get_session(session_id: str) -> dict | None:
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM sessions
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def update_session_title(session_id: str, title: str) -> dict | None:
    """更新会话标题；title 为空则保持「未命名」式占位。"""
    raw = title.strip()
    resolved = raw[:120] if raw else "新会话"
    current_time = _now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE sessions
            SET title = ?, updated_at = ?
            WHERE id = ?
            """,
            (resolved, current_time, session_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    return get_session(session_id)


def delete_session(session_id: str) -> bool:
    """删除会话；关联 tasks / messages 由外键 ON DELETE CASCADE 清理。"""
    with get_db_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,),
        )
        connection.commit()
        return cursor.rowcount > 0


def count_sessions() -> int:
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS n FROM sessions",
        ).fetchone()
    return int(row["n"]) if row else 0


def count_tasks(session_id: str | None = None) -> int:
    with get_db_connection() as connection:
        if session_id:
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM tasks",
            ).fetchone()
    return int(row["n"]) if row else 0


def list_sessions(limit: int = 20, offset: int = 0) -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM sessions
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return [dict(row) for row in rows]


def get_session_messages(session_id: str) -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, task_id, role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_task(task_id: str) -> dict | None:
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT id, session_id, prompt, status, trace_json, created_at, updated_at
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def list_tasks(
    limit: int = 20,
    session_id: str | None = None,
    offset: int = 0,
) -> list[dict]:
    with get_db_connection() as connection:
        if session_id:
            rows = connection.execute(
                """
                SELECT id, session_id, prompt, status, trace_json, created_at, updated_at
                FROM tasks
                WHERE session_id = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (session_id, limit, offset),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, session_id, prompt, status, trace_json, created_at, updated_at
                FROM tasks
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

    return [dict(row) for row in rows]


def get_task_trace(task_id: str) -> list[dict]:
    task = get_task(task_id)
    if task is None or not task["trace_json"]:
        return []
    return _normalize_trace_steps(json.loads(task["trace_json"]))


def get_task_trace_delta(task_id: str, after_seq: int = 0) -> tuple[list[dict], int, bool]:
    trace_steps = get_task_trace(task_id)
    delta_steps = [
        step for step in trace_steps if int(step.get("seq", 0)) > after_seq
    ]
    next_cursor = after_seq if not delta_steps else int(delta_steps[-1]["seq"])
    has_more = False
    return delta_steps, next_cursor, has_more
