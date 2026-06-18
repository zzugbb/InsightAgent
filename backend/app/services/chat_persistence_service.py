from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from uuid import uuid4

from app.db import get_db_connection
from app.schemas.trace import TraceStep, parse_trace_steps


def _now_iso() -> str:
    return datetime.now().isoformat()


def _build_session_title(prompt: str) -> str:
    normalized = " ".join(prompt.strip().split())
    return normalized[:60] or "New Session"


def _is_placeholder_session_title(title: object) -> bool:
    if not isinstance(title, str):
        return True
    raw = title.strip()
    if not raw:
        return True
    lowered = raw.lower()
    if lowered in {"新会话", "new session"}:
        return True
    if lowered.startswith("会话 ") or lowered.startswith("session "):
        return True
    return False


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


def _load_trace_steps_from_trace_json(trace_json: object) -> list[dict]:
    if not isinstance(trace_json, str) or not trace_json.strip():
        return []
    try:
        loaded = json.loads(trace_json)
    except Exception:
        return []
    if not isinstance(loaded, list):
        return []
    return _normalize_trace_steps([item for item in loaded if isinstance(item, dict)])


def _load_parsed_trace_steps_from_trace_json(trace_json: object) -> list[TraceStep]:
    return parse_trace_steps(_load_trace_steps_from_trace_json(trace_json))


def _parse_usage_json_blob(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _extract_task_governance_from_trace_steps(
    trace_steps: list[dict],
) -> dict[str, object] | None:
    for item in trace_steps:
        if not isinstance(item, dict):
            continue
        meta = item.get("meta")
        if not isinstance(meta, dict):
            continue

        profile = (
            meta.get("tool_registry_profile")
            if isinstance(meta.get("tool_registry_profile"), str)
            else None
        )
        provider_source = (
            meta.get("tool_registry_provider_source")
            if isinstance(meta.get("tool_registry_provider_source"), str)
            else None
        )
        allowed_tool_names = [
            value
            for value in meta.get("allowed_tool_names", [])
            if isinstance(value, str)
        ]
        allowed_tool_labels = [
            value
            for value in meta.get("allowed_tool_labels", [])
            if isinstance(value, str)
        ]
        normalized = _normalize_task_governance_dict(
            {
                "profile": profile,
                "provider_source": provider_source,
                "allowed_tool_names": allowed_tool_names,
                "allowed_tool_labels": allowed_tool_labels,
            }
        )
        if normalized is None or not _has_task_governance_values(normalized):
            continue
        return normalized
    return None

def _serialize_task_governance_columns(
    trace_steps: list[dict],
) -> tuple[str | None, str | None, str | None, str | None]:
    governance = _extract_task_governance_from_trace_steps(trace_steps)
    if governance is None:
        return None, None, None, None
    allowed_tool_names = governance["allowed_tool_names"]
    allowed_tool_labels = governance["allowed_tool_labels"]
    return (
        governance["profile"] if isinstance(governance["profile"], str) else None,
        governance["provider_source"]
        if isinstance(governance["provider_source"], str)
        else None,
        json.dumps(allowed_tool_names, ensure_ascii=False)
        if isinstance(allowed_tool_names, list)
        else None,
        json.dumps(allowed_tool_labels, ensure_ascii=False)
        if isinstance(allowed_tool_labels, list)
        else None,
    )


def _parse_task_governance_json_list_blob(value: object) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, str)]


def _normalize_governance_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _normalize_governance_summary_string_list(value: object) -> list[str]:
    return sorted(set(_normalize_governance_string_list(value)))


def _normalize_governance_filter_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized_values = {
        normalized
        for item in value
        if isinstance(item, str)
        for normalized in [_normalize_governance_filter(item)]
        if normalized is not None
    }
    return sorted(normalized_values)


def _has_task_governance_values(governance: object) -> bool:
    if not isinstance(governance, dict):
        return False
    if isinstance(governance.get("profile"), str):
        return True
    if isinstance(governance.get("provider_source"), str):
        return True
    if isinstance(governance.get("allowed_tool_names"), list) and bool(
        governance.get("allowed_tool_names")
    ):
        return True
    if isinstance(governance.get("allowed_tool_labels"), list) and bool(
        governance.get("allowed_tool_labels")
    ):
        return True
    return False


def _has_session_governance_values(governance: object) -> bool:
    if not isinstance(governance, dict):
        return False
    if isinstance(governance.get("profiles"), list) and bool(governance.get("profiles")):
        return True
    if isinstance(governance.get("provider_sources"), list) and bool(
        governance.get("provider_sources")
    ):
        return True
    if isinstance(governance.get("allowed_tool_names"), list) and bool(
        governance.get("allowed_tool_names")
    ):
        return True
    if isinstance(governance.get("allowed_tool_labels"), list) and bool(
        governance.get("allowed_tool_labels")
    ):
        return True
    return False


def _extract_task_governance_from_task_row(
    task: dict[str, object],
) -> dict[str, object] | None:
    raw_profile = task.get("tool_registry_profile")
    raw_provider_source = task.get("tool_registry_provider_source")
    profile = raw_profile if isinstance(raw_profile, str) else None
    provider_source = raw_provider_source if isinstance(raw_provider_source, str) else None
    allowed_tool_names = _parse_task_governance_json_list_blob(
        task.get("allowed_tool_names_json")
    )
    allowed_tool_labels = _parse_task_governance_json_list_blob(
        task.get("allowed_tool_labels_json")
    )
    normalized = _normalize_task_governance_dict(
        {
            "profile": profile,
            "provider_source": provider_source,
            "allowed_tool_names": allowed_tool_names,
            "allowed_tool_labels": allowed_tool_labels,
        }
    )
    if normalized is not None:
        return normalized
    trace_steps = _load_trace_steps_from_trace_json(task.get("trace_json"))
    if not trace_steps:
        return None
    return _extract_task_governance_from_trace_steps(trace_steps)


def _with_task_governance(task: dict[str, object]) -> dict[str, object]:
    governance = _extract_task_governance_from_task_row(task)
    return {
        **{
            key: value
            for key, value in task.items()
            if key
            not in {
                "tool_registry_profile",
                "tool_registry_provider_source",
                "allowed_tool_names_json",
                "allowed_tool_labels_json",
            }
        },
        "governance": governance,
    }


def _normalize_task_governance_dict(
    governance: object,
) -> dict[str, object] | None:
    if not isinstance(governance, dict):
        return None
    normalized = {
        "profile": _normalize_governance_filter(governance.get("profile"))
        if isinstance(governance.get("profile"), str)
        else None,
        "provider_source": _normalize_governance_filter(
            governance.get("provider_source")
        )
        if isinstance(governance.get("provider_source"), str)
        else None,
        "allowed_tool_names": _normalize_governance_string_list(
            governance.get("allowed_tool_names")
        ),
        "allowed_tool_labels": _normalize_governance_string_list(
            governance.get("allowed_tool_labels")
        ),
    }
    if not _has_task_governance_values(normalized):
        return None
    return normalized


def _normalize_session_governance_summary_dict(
    governance: object,
) -> dict[str, object] | None:
    if not isinstance(governance, dict):
        return None
    normalized = {
        "profiles": _normalize_governance_filter_list(governance.get("profiles")),
        "provider_sources": _normalize_governance_filter_list(
            governance.get("provider_sources")
        ),
        "allowed_tool_names": _normalize_governance_summary_string_list(
            governance.get("allowed_tool_names")
        ),
        "allowed_tool_labels": _normalize_governance_summary_string_list(
            governance.get("allowed_tool_labels")
        ),
    }
    if not _has_session_governance_values(normalized):
        return None
    return normalized


def ensure_session(prompt: str, user_id: str, session_id: str | None = None) -> str:
    current_time = _now_iso()
    resolved_session_id = session_id or str(uuid4())
    title = _build_session_title(prompt)

    with get_db_connection() as connection:
        existing = connection.execute(
            "SELECT id, user_id, title FROM sessions WHERE id = ?",
            (resolved_session_id,),
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO sessions(id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (resolved_session_id, user_id, title, current_time, current_time),
            )
        else:
            owner = existing["user_id"]
            if owner and owner != user_id:
                raise ValueError("session does not belong to current user")
            message_count_row = connection.execute(
                """
                SELECT COUNT(*) AS n
                FROM messages
                WHERE session_id = ? AND user_id = ?
                """,
                (resolved_session_id, user_id),
            ).fetchone()
            message_count = int(message_count_row["n"]) if message_count_row else 0
            should_autofill_title = (
                message_count == 0
                and _is_placeholder_session_title(existing["title"])
            )
            connection.execute(
                """
                UPDATE sessions
                SET
                    user_id = COALESCE(user_id, ?),
                    title = CASE
                        WHEN ? THEN ?
                        ELSE title
                    END,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    user_id,
                    should_autofill_title,
                    title,
                    current_time,
                    resolved_session_id,
                ),
            )
        connection.commit()

    return resolved_session_id


def create_task(
    session_id: str,
    prompt: str,
    user_id: str,
    task_id: str | None = None,
    status: str = "running",
) -> str:
    current_time = _now_iso()
    resolved_task_id = task_id or str(uuid4())

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO tasks(id, user_id, session_id, prompt, status, trace_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_task_id,
                user_id,
                session_id,
                prompt,
                status,
                None,
                current_time,
                current_time,
            ),
        )
        connection.commit()

    return resolved_task_id


def create_message(
    session_id: str,
    user_id: str,
    role: str,
    content: str,
    task_id: str | None = None,
) -> str:
    message_id = str(uuid4())
    current_time = _now_iso()

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO messages(id, user_id, session_id, task_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (message_id, user_id, session_id, task_id, role, content, current_time),
        )
        connection.execute(
            """
            UPDATE sessions
            SET updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (current_time, session_id, user_id),
        )
        connection.commit()

    return message_id


def update_task_status(task_id: str, status: str, user_id: str) -> None:
    current_time = _now_iso()

    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET status = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (status, current_time, task_id, user_id),
        )
        connection.commit()


def update_task_trace_steps(task_id: str, trace_steps: list[dict], user_id: str) -> None:
    """流式执行过程中写入部分 trace（不改变任务状态）。"""
    current_time = _now_iso()
    normalized_trace_steps = _normalize_trace_steps(trace_steps)
    (
        tool_registry_profile,
        tool_registry_provider_source,
        allowed_tool_names_json,
        allowed_tool_labels_json,
    ) = _serialize_task_governance_columns(normalized_trace_steps)

    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET
                trace_json = ?,
                updated_at = ?,
                tool_registry_profile = ?,
                tool_registry_provider_source = ?,
                allowed_tool_names_json = ?,
                allowed_tool_labels_json = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                json.dumps(normalized_trace_steps, ensure_ascii=False),
                current_time,
                tool_registry_profile,
                tool_registry_provider_source,
                allowed_tool_names_json,
                allowed_tool_labels_json,
                task_id,
                user_id,
            ),
        )
        connection.commit()


def complete_task(
    task_id: str,
    trace_steps: list[dict],
    user_id: str,
    status: str = "completed",
    usage: dict[str, object] | None = None,
) -> None:
    current_time = _now_iso()
    normalized_trace_steps = _normalize_trace_steps(trace_steps)
    usage_blob = json.dumps(usage, ensure_ascii=False) if usage is not None else None
    (
        tool_registry_profile,
        tool_registry_provider_source,
        allowed_tool_names_json,
        allowed_tool_labels_json,
    ) = _serialize_task_governance_columns(normalized_trace_steps)

    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET
                status = ?,
                trace_json = ?,
                usage_json = ?,
                updated_at = ?,
                tool_registry_profile = ?,
                tool_registry_provider_source = ?,
                allowed_tool_names_json = ?,
                allowed_tool_labels_json = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                status,
                json.dumps(normalized_trace_steps, ensure_ascii=False),
                usage_blob,
                current_time,
                tool_registry_profile,
                tool_registry_provider_source,
                allowed_tool_names_json,
                allowed_tool_labels_json,
                task_id,
                user_id,
            ),
        )
        connection.commit()


def create_session_record(title: str | None = None, user_id: str = "") -> dict:
    """Insert an empty session row (no messages yet)."""
    if not user_id.strip():
        raise ValueError("user_id is required")
    session_id = str(uuid4())
    current_time = _now_iso()
    raw = (title or "新会话").strip()
    resolved_title = raw[:120] if raw else "新会话"

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO sessions(id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, user_id, resolved_title, current_time, current_time),
        )
        connection.commit()

    row = get_session(session_id, user_id)
    if row is None:
        raise RuntimeError("failed to read session after insert")
    return row


def get_session(session_id: str, user_id: str) -> dict | None:
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM sessions
            WHERE id = ? AND user_id = ?
            """,
            (session_id, user_id),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def update_session_title(session_id: str, title: str, user_id: str) -> dict | None:
    """更新会话标题；title 为空则保持「未命名」式占位。"""
    raw = title.strip()
    resolved = raw[:120] if raw else "新会话"
    current_time = _now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE sessions
            SET title = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (resolved, current_time, session_id, user_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    return get_session(session_id, user_id)


def delete_session(session_id: str, user_id: str) -> bool:
    """删除会话；关联 tasks / messages 由外键 ON DELETE CASCADE 清理。"""
    with get_db_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def count_sessions(user_id: str) -> int:
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS n FROM sessions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return int(row["n"]) if row else 0


def _build_task_search_clause(
    query: str | None,
    params: list[object],
) -> str:
    normalized = (query or "").strip().lower()
    if not normalized:
        return ""
    like = f"%{normalized}%"
    params.extend((like, like, like))
    return """
        AND (
            LOWER(prompt) LIKE ?
            OR LOWER(id) LIKE ?
            OR LOWER(COALESCE(trace_json, '')) LIKE ?
        )
    """


def _build_task_governance_filter_clause(
    tool_registry_profile_filter: str | None,
    tool_registry_provider_source_filter: str | None,
    params: list[object],
) -> str:
    clauses: list[str] = []
    normalized_profile = _normalize_governance_filter(tool_registry_profile_filter)
    if normalized_profile:
        clauses.append("LOWER(COALESCE(tool_registry_profile, '')) = ?")
        params.append(normalized_profile)
    normalized_provider_source = _normalize_governance_filter(
        tool_registry_provider_source_filter
    )
    if normalized_provider_source:
        clauses.append("LOWER(COALESCE(tool_registry_provider_source, '')) = ?")
        params.append(normalized_provider_source)
    if not clauses:
        return ""
    return "\n        AND (" + " AND ".join(clauses) + ")"


def count_tasks(
    user_id: str,
    session_id: str | None = None,
    query: str | None = None,
    tool_registry_profile_filter: str | None = None,
    tool_registry_provider_source_filter: str | None = None,
) -> int:
    with get_db_connection() as connection:
        params: list[object] = [user_id]
        session_clause = ""
        if session_id:
            session_clause = " AND session_id = ?"
            params.append(session_id)
        search_clause = _build_task_search_clause(query, params)
        governance_clause = _build_task_governance_filter_clause(
            tool_registry_profile_filter,
            tool_registry_provider_source_filter,
            params,
        )
        row = connection.execute(
            f"SELECT COUNT(*) AS n FROM tasks WHERE user_id = ?{session_clause}{search_clause}{governance_clause}",
            tuple(params),
        ).fetchone()
    return int(row["n"]) if row else 0


def list_sessions(user_id: str, limit: int = 20, offset: int = 0) -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        ).fetchall()

    return [dict(row) for row in rows]


def get_session_messages(session_id: str, user_id: str) -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, task_id, role, content, created_at
            FROM messages
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at ASC
            """,
            (session_id, user_id),
        ).fetchall()

    return [dict(row) for row in rows]


def get_task_messages(task_id: str, user_id: str) -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, task_id, role, content, created_at
            FROM messages
            WHERE task_id = ? AND user_id = ?
            ORDER BY created_at ASC
            """,
            (task_id, user_id),
        ).fetchall()

    return [dict(row) for row in rows]


def get_task(task_id: str, user_id: str) -> dict | None:
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                session_id,
                prompt,
                status,
                trace_json,
                usage_json,
                tool_registry_profile,
                tool_registry_provider_source,
                allowed_tool_names_json,
                allowed_tool_labels_json,
                created_at,
                updated_at
            FROM tasks
            WHERE id = ? AND user_id = ?
            """,
            (task_id, user_id),
        ).fetchone()

    if row is None:
        return None

    return _with_task_governance(dict(row))


def list_tasks(
    user_id: str,
    limit: int = 20,
    session_id: str | None = None,
    offset: int = 0,
    query: str | None = None,
    tool_registry_profile_filter: str | None = None,
    tool_registry_provider_source_filter: str | None = None,
) -> list[dict]:
    with get_db_connection() as connection:
        params: list[object] = [user_id]
        session_clause = ""
        if session_id:
            session_clause = " AND session_id = ?"
            params.append(session_id)
        search_clause = _build_task_search_clause(query, params)
        governance_clause = _build_task_governance_filter_clause(
            tool_registry_profile_filter,
            tool_registry_provider_source_filter,
            params,
        )
        params.extend((limit, offset))
        rows = connection.execute(
            f"""
                SELECT
                    id,
                    session_id,
                    prompt,
                    status,
                    trace_json,
                    usage_json,
                    tool_registry_profile,
                    tool_registry_provider_source,
                    allowed_tool_names_json,
                    allowed_tool_labels_json,
                    created_at,
                    updated_at
                FROM tasks
                WHERE user_id = ?{session_clause}{search_clause}{governance_clause}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """,
            tuple(params),
        ).fetchall()

    return [_with_task_governance(dict(row)) for row in rows]


def get_session_tasks(session_id: str, user_id: str) -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                session_id,
                prompt,
                status,
                trace_json,
                usage_json,
                tool_registry_profile,
                tool_registry_provider_source,
                allowed_tool_names_json,
                allowed_tool_labels_json,
                created_at,
                updated_at
            FROM tasks
            WHERE user_id = ? AND session_id = ?
            ORDER BY created_at ASC
            """,
            (user_id, session_id),
        ).fetchall()

    return [_with_task_governance(dict(row)) for row in rows]


def get_task_trace_steps_from_task(task: dict) -> list[TraceStep]:
    if not task.get("trace_json"):
        return []
    return _load_parsed_trace_steps_from_trace_json(task["trace_json"])


def get_task_usage_from_task(task: dict) -> dict[str, object] | None:
    return _parse_usage_json_blob(task.get("usage_json"))


def _normalize_trace_preview_excerpt(text: str, limit: int = 120) -> str:
    normalized = " ".join((text or "").strip().split())
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def _trace_preview_title(step: TraceStep) -> str:
    meta = getattr(step, "meta", None)
    label = getattr(meta, "label", None) if meta is not None else None
    if isinstance(label, str) and label.strip():
        return label.strip()
    step_type = getattr(meta, "step_type", None) if meta is not None else None
    if isinstance(step_type, str) and step_type.strip():
        return step_type.strip().replace("_", " ")
    raw_type = getattr(step, "type", None)
    if isinstance(raw_type, str) and raw_type.strip():
        return raw_type.strip().replace("_", " ")
    return "step"


def get_task_trace_preview_summary_from_task(
    task: dict,
    *,
    preview_limit: int = 3,
) -> dict[str, object]:
    trace_summary = get_task_trace_export_summary_from_task(task)
    trace_steps = [
        step for step in trace_summary.get("steps", []) if isinstance(step, TraceStep)
    ]
    trace_step_count = int(trace_summary.get("step_count", len(trace_steps)) or 0)
    rag_hit_count = int(trace_summary.get("rag_hit_count", 0) or 0)

    preview_steps: list[dict[str, object]] = []
    bounded_limit = max(0, int(preview_limit))
    for step in trace_steps[-bounded_limit:] if bounded_limit else []:
        content = getattr(step, "content", "") or ""
        preview_steps.append(
            {
                "id": str(getattr(step, "id", "")),
                "seq": getattr(step, "seq", None),
                "type": str(getattr(step, "type", "")),
                "title": _trace_preview_title(step),
                "content_excerpt": _normalize_trace_preview_excerpt(
                    str(content),
                    limit=120,
                ),
            }
        )

    return {
        "trace_step_count": trace_step_count,
        "rag_hit_count": rag_hit_count,
        "trace_preview": preview_steps,
    }


def get_trace_rag_export_summary(
    trace_steps: list[TraceStep],
) -> dict[str, object]:
    rag_hit_count = 0
    rag_knowledge_base_ids: list[str] = []
    rag_chunks: list[dict[str, object]] = []
    seen_kb_ids: set[str] = set()

    for step in trace_steps:
        rag_meta = step.meta.rag if step.meta else None
        if not isinstance(rag_meta, dict):
            continue
        raw_chunks = rag_meta.get("chunks")
        kb_id = rag_meta.get("knowledge_base_id")
        kb_id_text = kb_id.strip() if isinstance(kb_id, str) and kb_id.strip() else None
        if kb_id_text and kb_id_text not in seen_kb_ids:
            seen_kb_ids.add(kb_id_text)
            rag_knowledge_base_ids.append(kb_id_text)
        if isinstance(raw_chunks, list):
            for chunk in raw_chunks:
                if not isinstance(chunk, str):
                    continue
                chunk_text = chunk.strip()
                if not chunk_text:
                    continue
                rag_hit_count += 1
                rag_chunks.append(
                    {
                        "step_id": step.id,
                        "knowledge_base_id": kb_id_text,
                        "content": chunk_text,
                    }
                )

    return {
        "rag_hit_count": rag_hit_count,
        "rag_knowledge_base_ids": rag_knowledge_base_ids,
        "rag_chunks": rag_chunks,
    }


def get_task_trace_export_summary_from_task(task: dict) -> dict[str, object]:
    trace_steps = get_task_trace_steps_from_task(task)
    rag_summary = get_trace_rag_export_summary(trace_steps)
    rag_knowledge_base_ids = [
        str(item)
        for item in rag_summary.get("rag_knowledge_base_ids", [])
        if isinstance(item, str)
    ]
    rag_chunks = [
        row for row in rag_summary.get("rag_chunks", []) if isinstance(row, dict)
    ]
    return {
        "steps": trace_steps,
        "step_count": len(trace_steps),
        "rag_hit_count": int(rag_summary.get("rag_hit_count", 0) or 0),
        "rag_knowledge_base_ids": rag_knowledge_base_ids,
        "rag_chunks": rag_chunks,
    }


def get_task_export_summary_from_task(task: dict) -> dict[str, object]:
    trace_summary = get_task_trace_export_summary_from_task(task)
    return {
        "usage": get_task_usage_from_task(task),
        "governance": task.get("governance")
        if isinstance(task.get("governance"), dict)
        else None,
        "steps": [
            step for step in trace_summary.get("steps", []) if isinstance(step, TraceStep)
        ],
        "step_count": int(trace_summary.get("step_count", 0) or 0),
        "rag_hit_count": int(trace_summary.get("rag_hit_count", 0) or 0),
        "rag_knowledge_base_ids": [
            str(item)
            for item in trace_summary.get("rag_knowledge_base_ids", [])
            if isinstance(item, str)
        ],
        "rag_chunks": [
            row for row in trace_summary.get("rag_chunks", []) if isinstance(row, dict)
        ],
    }


def get_task_trace_delta_snapshot_from_task(
    task: dict,
    *,
    after_seq: int = 0,
    limit: int = 200,
) -> tuple[list[TraceStep], int, bool, int, str | None]:
    bounded_limit = max(1, int(limit))
    trace_steps = get_task_trace_steps_from_task(task)
    latest_seq = max((int(step.seq or 0) for step in trace_steps), default=0)
    latest_step_id = trace_steps[-1].id if trace_steps else None
    all_delta_steps = [step for step in trace_steps if int(step.seq or 0) > after_seq]
    delta_steps = all_delta_steps[:bounded_limit]
    next_cursor = after_seq if not delta_steps else int(delta_steps[-1].seq or 0)
    status = str(task.get("status", ""))
    still_running = status in ("pending", "running")
    has_more = len(all_delta_steps) > len(delta_steps) or still_running
    return delta_steps, next_cursor, has_more, latest_seq, latest_step_id


def get_tasks_usage_summary(
    user_id: str,
    session_id: str | None = None,
) -> dict[str, int | float | None]:
    """聚合 tasks.usage_json（可选按 session_id 过滤）。"""

    def _to_float(v: object) -> float | None:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            raw = v.strip()
            if not raw:
                return None
            try:
                return float(raw)
            except ValueError:
                return None
        return None

    with get_db_connection() as connection:
        if session_id:
            rows = connection.execute(
                """
                SELECT usage_json
                FROM tasks
                WHERE user_id = ? AND session_id = ?
                """,
                (user_id, session_id),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT usage_json
                FROM tasks
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchall()

    tasks_total = len(rows)
    tasks_with_usage = 0
    source_provider_tasks = 0
    source_estimated_tasks = 0
    source_mixed_tasks = 0
    source_legacy_tasks = 0
    prompt_sum = 0.0
    completion_sum = 0.0
    cost_sum = 0.0
    token_task_count = 0
    cost_task_count = 0

    for row in rows:
        payload = _parse_usage_json_blob(row["usage_json"])
        if not isinstance(payload, dict):
            continue

        tasks_with_usage += 1
        source_kind = _classify_usage_source(payload)
        if source_kind == "provider":
            source_provider_tasks += 1
        elif source_kind == "estimated":
            source_estimated_tasks += 1
        elif source_kind == "mixed":
            source_mixed_tasks += 1
        else:
            source_legacy_tasks += 1
        prompt_raw = payload.get("prompt_tokens")
        completion_raw = payload.get("completion_tokens")
        cost_raw = payload.get("cost_estimate")

        prompt_num = _to_float(prompt_raw)
        completion_num = _to_float(completion_raw)
        cost_num = _to_float(cost_raw)

        has_token = False
        if prompt_num is not None:
            prompt_sum += prompt_num
            has_token = True
        if completion_num is not None:
            completion_sum += completion_num
            has_token = True
        if has_token:
            token_task_count += 1
        if cost_num is not None:
            cost_sum += cost_num
            cost_task_count += 1

    total_tokens = prompt_sum + completion_sum
    avg_total_tokens = total_tokens / token_task_count if token_task_count > 0 else None
    avg_cost_estimate = cost_sum / cost_task_count if cost_task_count > 0 else None

    return {
        "tasks_total": tasks_total,
        "tasks_with_usage": tasks_with_usage,
        "source_tasks_provider": source_provider_tasks,
        "source_tasks_estimated": source_estimated_tasks,
        "source_tasks_mixed": source_mixed_tasks,
        "source_tasks_legacy": source_legacy_tasks,
        "prompt_tokens": int(prompt_sum) if prompt_sum > 0 else 0,
        "completion_tokens": int(completion_sum) if completion_sum > 0 else 0,
        "total_tokens": int(total_tokens) if total_tokens > 0 else 0,
        "cost_estimate": cost_sum if cost_sum > 0 else 0.0,
        "avg_total_tokens": avg_total_tokens,
        "avg_cost_estimate": avg_cost_estimate,
    }


def get_session_usage_summary(
    session_id: str,
    user_id: str,
) -> dict[str, int | float | None]:
    """兼容保留：按会话聚合 usage。"""
    return get_tasks_usage_summary(user_id, session_id)


def _parse_usage_float(v: object) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        raw = v.strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def _parse_usage_source(v: object) -> str | None:
    if not isinstance(v, str):
        return None
    raw = v.strip().lower()
    if raw in {"provider", "estimated"}:
        return raw
    return None


def _classify_usage_source(payload: dict[str, object]) -> str:
    """Classify per-task usage source for summary/dashboard statistics."""
    usage_source = _parse_usage_source(payload.get("usage_source"))
    prompt_source = _parse_usage_source(payload.get("prompt_tokens_source"))
    completion_source = _parse_usage_source(payload.get("completion_tokens_source"))

    if (
        prompt_source is not None
        and completion_source is not None
        and prompt_source != completion_source
    ):
        return "mixed"

    for source in (usage_source, prompt_source, completion_source):
        if source is not None:
            return source
    return "legacy"


def _extract_iso_day(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if len(raw) < 10:
        return None
    prefix = raw[:10]
    try:
        return date.fromisoformat(prefix)
    except ValueError:
        return None


def _excerpt_prompt(value: object, limit: int = 90) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.strip().split())
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _normalize_governance_filter(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _task_governance_matches_filters(
    governance: object,
    tool_registry_profile_filter: str | None,
    tool_registry_provider_source_filter: str | None,
) -> bool:
    normalized_governance = _normalize_task_governance_dict(governance)
    if tool_registry_profile_filter is not None:
        if not isinstance(normalized_governance, dict):
            return False
        normalized_profile = normalized_governance.get("profile")
        if normalized_profile != tool_registry_profile_filter:
            return False
    if tool_registry_provider_source_filter is not None:
        if not isinstance(normalized_governance, dict):
            return False
        normalized_provider_source = normalized_governance.get("provider_source")
        if normalized_provider_source != tool_registry_provider_source_filter:
            return False
    return True


def _merge_session_governance_summary(
    current: dict[str, object] | None,
    task_governance: dict[str, object] | None,
) -> dict[str, object] | None:
    normalized_current = _normalize_session_governance_summary_dict(current)
    normalized_task = _normalize_task_governance_dict(task_governance)
    if normalized_task is None:
        return normalized_current

    profiles = set(
        normalized_current.get("profiles", [])
        if isinstance(normalized_current, dict)
        else []
    )
    allowed_tool_names = set(
        normalized_current.get("allowed_tool_names", [])
        if isinstance(normalized_current, dict)
        else []
    )
    allowed_tool_labels = set(
        normalized_current.get("allowed_tool_labels", [])
        if isinstance(normalized_current, dict)
        else []
    )
    provider_sources = set(
        normalized_current.get("provider_sources", [])
        if isinstance(normalized_current, dict)
        else []
    )

    profile = normalized_task.get("profile")
    if isinstance(profile, str):
        normalized_profile = _normalize_governance_filter(profile)
        if normalized_profile is not None:
            profiles.add(normalized_profile)

    provider_source = normalized_task.get("provider_source")
    if isinstance(provider_source, str):
        normalized_provider_source = _normalize_governance_filter(provider_source)
        if normalized_provider_source is not None:
            provider_sources.add(normalized_provider_source)

    for item in _normalize_governance_string_list(
        normalized_task.get("allowed_tool_names")
    ):
        allowed_tool_names.add(item)

    for item in _normalize_governance_string_list(
        normalized_task.get("allowed_tool_labels")
    ):
        allowed_tool_labels.add(item)

    if not profiles and not provider_sources and not allowed_tool_names and not allowed_tool_labels:
        return normalized_current

    return {
        "profiles": sorted(profiles),
        "provider_sources": sorted(provider_sources),
        "allowed_tool_names": _normalize_governance_summary_string_list(
            list(allowed_tool_names)
        ),
        "allowed_tool_labels": _normalize_governance_summary_string_list(
            list(allowed_tool_labels)
        ),
    }


def get_task_rows_governance_summary(
    task_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
) -> dict[str, object] | None:
    governance_summary: dict[str, object] | None = None
    for task_row in task_rows:
        task_governance = task_row.get("governance")
        if not isinstance(task_governance, dict):
            continue
        governance_summary = _merge_session_governance_summary(
            governance_summary,
            task_governance,
        )
    return governance_summary


def get_task_rows_trace_preview_summary(
    task_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    preview_limit: int = 3,
) -> dict[str, object]:
    task_summaries: list[dict[str, object]] = []
    trace_step_total = 0
    rag_hit_total = 0
    for task_row in task_rows:
        preview_summary = get_task_trace_preview_summary_from_task(
            task_row,
            preview_limit=preview_limit,
        )
        trace_step_count = int(preview_summary.get("trace_step_count", 0) or 0)
        rag_hit_count = int(preview_summary.get("rag_hit_count", 0) or 0)
        task_summaries.append(
            {
                "task_id": str(task_row.get("id", "")),
                "trace_step_count": trace_step_count,
                "rag_hit_count": rag_hit_count,
                "trace_preview": [
                    row
                    for row in preview_summary.get("trace_preview", [])
                    if isinstance(row, dict)
                ],
            }
        )
        trace_step_total += trace_step_count
        rag_hit_total += rag_hit_count

    return {
        "tasks": task_summaries,
        "trace_step_count": trace_step_total,
        "rag_hit_count": rag_hit_total,
    }


def get_task_rows_export_summary(
    task_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    preview_limit: int = 3,
) -> dict[str, object]:
    trace_summary = get_task_rows_trace_preview_summary(
        task_rows,
        preview_limit=preview_limit,
    )
    return {
        "tasks": [
            row for row in trace_summary.get("tasks", []) if isinstance(row, dict)
        ],
        "trace_step_count": int(trace_summary.get("trace_step_count", 0) or 0),
        "rag_hit_count": int(trace_summary.get("rag_hit_count", 0) or 0),
        "governance": get_task_rows_governance_summary(task_rows),
    }


def get_task_rows_session_export_summary(
    task_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    preview_limit: int = 3,
) -> dict[str, object]:
    export_summary = get_task_rows_export_summary(task_rows, preview_limit=preview_limit)
    trace_summary_by_task_id = {
        str(row.get("task_id", "")): row
        for row in export_summary.get("tasks", [])
        if isinstance(row, dict)
    }
    task_summaries: list[dict[str, object]] = []
    for task_row in task_rows:
        task_id = str(task_row.get("id", ""))
        trace_summary = trace_summary_by_task_id.get(task_id, {})
        task_summaries.append(
            {
                "task_id": task_id,
                "usage": get_task_usage_from_task(task_row),
                "governance": task_row.get("governance")
                if isinstance(task_row.get("governance"), dict)
                else None,
                "trace_step_count": int(trace_summary.get("trace_step_count", 0) or 0),
                "rag_hit_count": int(trace_summary.get("rag_hit_count", 0) or 0),
                "trace_preview": [
                    row
                    for row in trace_summary.get("trace_preview", [])
                    if isinstance(row, dict)
                ],
            }
        )

    return {
        "tasks": task_summaries,
        "trace_step_count": int(export_summary.get("trace_step_count", 0) or 0),
        "rag_hit_count": int(export_summary.get("rag_hit_count", 0) or 0),
        "governance": export_summary.get("governance"),
    }


def get_tasks_usage_dashboard(
    user_id: str,
    *,
    session_id: str | None = None,
    source_filter: str | None = None,
    tool_registry_profile_filter: str | None = None,
    tool_registry_provider_source_filter: str | None = None,
    window_days: int = 14,
    top_sessions: int = 8,
    top_tasks: int = 12,
) -> dict[str, object]:
    """按用户聚合 usage 仪表盘：汇总、趋势、会话榜、任务榜。"""
    safe_source_filter = source_filter if source_filter in {
        "provider",
        "estimated",
        "mixed",
        "legacy",
    } else None
    safe_window_days = max(1, min(int(window_days), 90))
    safe_top_sessions = max(1, min(int(top_sessions), 30))
    safe_top_tasks = max(1, min(int(top_tasks), 50))
    safe_profile_filter = _normalize_governance_filter(tool_registry_profile_filter)
    safe_provider_source_filter = _normalize_governance_filter(
        tool_registry_provider_source_filter
    )

    with get_db_connection() as connection:
        if session_id:
            rows = connection.execute(
                """
                SELECT
                    t.id,
                    t.session_id,
                    t.prompt,
                    t.usage_json,
                    t.trace_json,
                    t.tool_registry_profile,
                    t.tool_registry_provider_source,
                    t.allowed_tool_names_json,
                    t.allowed_tool_labels_json,
                    t.created_at,
                    t.updated_at,
                    s.title AS session_title
                FROM tasks AS t
                LEFT JOIN sessions AS s
                  ON s.id = t.session_id AND s.user_id = t.user_id
                WHERE t.user_id = ? AND t.session_id = ?
                ORDER BY t.updated_at DESC
                """,
                (user_id, session_id),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT
                    t.id,
                    t.session_id,
                    t.prompt,
                    t.usage_json,
                    t.trace_json,
                    t.tool_registry_profile,
                    t.tool_registry_provider_source,
                    t.allowed_tool_names_json,
                    t.allowed_tool_labels_json,
                    t.created_at,
                    t.updated_at,
                    s.title AS session_title
                FROM tasks AS t
                LEFT JOIN sessions AS s
                  ON s.id = t.session_id AND s.user_id = t.user_id
                WHERE t.user_id = ?
                ORDER BY t.updated_at DESC
                """,
                (user_id,),
            ).fetchall()

    tasks_total = len(rows)
    tasks_with_usage = 0
    source_provider_tasks = 0
    source_estimated_tasks = 0
    source_mixed_tasks = 0
    source_legacy_tasks = 0
    prompt_sum = 0.0
    completion_sum = 0.0
    cost_sum = 0.0
    token_task_count = 0
    cost_task_count = 0

    today = datetime.now().date()
    trend_start = today - timedelta(days=safe_window_days - 1)
    trend_map: dict[str, dict[str, int | float]] = {}
    for idx in range(safe_window_days):
        key = (trend_start + timedelta(days=idx)).isoformat()
        trend_map[key] = {
            "tasks_with_usage": 0,
            "source_tasks_provider": 0,
            "source_tasks_estimated": 0,
            "source_tasks_mixed": 0,
            "source_tasks_legacy": 0,
            "total_tokens": 0,
            "cost_estimate": 0.0,
        }

    session_map: dict[str, dict[str, object]] = {}
    top_task_rows: list[dict[str, object]] = []

    for row in rows:
        task_row = _with_task_governance(dict(row))
        payload = _parse_usage_json_blob(task_row.get("usage_json"))
        if not isinstance(payload, dict):
            continue

        source_kind = _classify_usage_source(payload)
        if safe_source_filter is not None and source_kind != safe_source_filter:
            continue
        task_governance = (
            task_row.get("governance") if isinstance(task_row.get("governance"), dict) else None
        )
        if not _task_governance_matches_filters(
            task_governance,
            safe_profile_filter,
            safe_provider_source_filter,
        ):
            continue

        tasks_with_usage += 1
        if source_kind == "provider":
            source_provider_tasks += 1
        elif source_kind == "estimated":
            source_estimated_tasks += 1
        elif source_kind == "mixed":
            source_mixed_tasks += 1
        else:
            source_legacy_tasks += 1
        prompt_num = _parse_usage_float(payload.get("prompt_tokens"))
        completion_num = _parse_usage_float(payload.get("completion_tokens"))
        cost_num = _parse_usage_float(payload.get("cost_estimate"))
        total_tokens_num = (prompt_num or 0.0) + (completion_num or 0.0)
        total_tokens_int = int(total_tokens_num) if total_tokens_num > 0 else 0
        cost_value = cost_num if cost_num is not None and cost_num > 0 else 0.0

        has_token = False
        if prompt_num is not None:
            prompt_sum += prompt_num
            has_token = True
        if completion_num is not None:
            completion_sum += completion_num
            has_token = True
        if has_token:
            token_task_count += 1
        if cost_num is not None:
            cost_sum += cost_num
            cost_task_count += 1

        created_day = _extract_iso_day(task_row.get("created_at"))
        if created_day is not None and trend_start <= created_day <= today:
            bucket = trend_map[created_day.isoformat()]
            bucket["tasks_with_usage"] = int(bucket["tasks_with_usage"]) + 1
            if source_kind == "provider":
                bucket["source_tasks_provider"] = int(bucket["source_tasks_provider"]) + 1
            elif source_kind == "estimated":
                bucket["source_tasks_estimated"] = int(bucket["source_tasks_estimated"]) + 1
            elif source_kind == "mixed":
                bucket["source_tasks_mixed"] = int(bucket["source_tasks_mixed"]) + 1
            else:
                bucket["source_tasks_legacy"] = int(bucket["source_tasks_legacy"]) + 1
            bucket["total_tokens"] = int(bucket["total_tokens"]) + total_tokens_int
            bucket["cost_estimate"] = float(bucket["cost_estimate"]) + cost_value

        sid = str(task_row["session_id"])
        bucket = session_map.get(sid)
        if bucket is None:
            bucket = {
                "session_id": sid,
                "session_title": task_row.get("session_title"),
                "tasks_with_usage": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "last_task_at": task_row.get("updated_at"),
                "governance": None,
            }
            session_map[sid] = bucket
        bucket["tasks_with_usage"] = int(bucket["tasks_with_usage"]) + 1
        bucket["total_tokens"] = int(bucket["total_tokens"]) + total_tokens_int
        bucket["cost_estimate"] = float(bucket["cost_estimate"]) + cost_value
        bucket["governance"] = _merge_session_governance_summary(
            bucket.get("governance") if isinstance(bucket, dict) else None,
            task_governance,
        )
        last_task_at = bucket.get("last_task_at")
        if isinstance(task_row.get("updated_at"), str) and (
            not isinstance(last_task_at, str)
            or task_row["updated_at"] > last_task_at
        ):
            bucket["last_task_at"] = task_row["updated_at"]

        top_task_rows.append(
            {
                "task_id": str(task_row["id"]),
                "session_id": sid,
                "session_title": task_row.get("session_title"),
                "prompt_excerpt": _excerpt_prompt(task_row.get("prompt")),
                "total_tokens": total_tokens_int,
                "cost_estimate": cost_value,
                "created_at": str(task_row["created_at"]),
                "updated_at": str(task_row["updated_at"]),
                "source_kind": source_kind,
                "governance": task_governance,
            },
        )

    total_tokens = prompt_sum + completion_sum
    avg_total_tokens = total_tokens / token_task_count if token_task_count > 0 else None
    avg_cost_estimate = cost_sum / cost_task_count if cost_task_count > 0 else None

    trend = [
        {
            "day": day,
            "tasks_with_usage": int(item["tasks_with_usage"]),
            "source_tasks_provider": int(item["source_tasks_provider"]),
            "source_tasks_estimated": int(item["source_tasks_estimated"]),
            "source_tasks_mixed": int(item["source_tasks_mixed"]),
            "source_tasks_legacy": int(item["source_tasks_legacy"]),
            "total_tokens": int(item["total_tokens"]),
            "cost_estimate": float(item["cost_estimate"]),
        }
        for day, item in sorted(trend_map.items(), key=lambda kv: kv[0])
    ]

    by_session = sorted(
        session_map.values(),
        key=lambda item: (
            int(item["total_tokens"]),
            float(item["cost_estimate"]),
            str(item["last_task_at"] or ""),
        ),
        reverse=True,
    )[:safe_top_sessions]

    top_tasks_sorted = sorted(
        top_task_rows,
        key=lambda item: (
            int(item["total_tokens"]),
            float(item["cost_estimate"]),
            str(item["updated_at"] or ""),
        ),
        reverse=True,
    )[:safe_top_tasks]

    summary: dict[str, int | float | None] = {
        "tasks_total": tasks_total,
        "tasks_with_usage": tasks_with_usage,
        "source_tasks_provider": source_provider_tasks,
        "source_tasks_estimated": source_estimated_tasks,
        "source_tasks_mixed": source_mixed_tasks,
        "source_tasks_legacy": source_legacy_tasks,
        "prompt_tokens": int(prompt_sum) if prompt_sum > 0 else 0,
        "completion_tokens": int(completion_sum) if completion_sum > 0 else 0,
        "total_tokens": int(total_tokens) if total_tokens > 0 else 0,
        "cost_estimate": cost_sum if cost_sum > 0 else 0.0,
        "avg_total_tokens": avg_total_tokens,
        "avg_cost_estimate": avg_cost_estimate,
    }

    return {
        "window_days": safe_window_days,
        "summary": summary,
        "trend": trend,
        "by_session": by_session,
        "top_tasks": top_tasks_sorted,
    }
