from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.config import get_settings
from app.db import get_db_connection
from app.schemas.trace import TraceStep, parse_trace_steps
from app.services.task_status_service import (
    normalize_task_status,
    task_status_label,
    task_status_rank,
)
from app.services.tool_runtime import (
    get_configured_tool_registry_provider,
    get_tool_display_name,
    normalize_tool_registry_name,
)


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
        json.dumps(list(allowed_tool_names), ensure_ascii=False)
        if isinstance(allowed_tool_names, (list, tuple))
        else None,
        json.dumps(list(allowed_tool_labels), ensure_ascii=False)
        if isinstance(allowed_tool_labels, (list, tuple))
        else None,
    )


def _parse_task_governance_json_list_blob(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
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
    if not isinstance(value, (list, tuple)):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _normalize_governance_summary_string_list(value: object) -> list[str]:
    return sorted(set(_normalize_governance_string_list(value)))


def _normalize_governance_filter_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized_values = {
        normalized
        for item in value
        if isinstance(item, str)
        for normalized in [_normalize_governance_filter(item)]
        if normalized is not None
    }
    return sorted(normalized_values)


def _build_governance_registry_provider(
    *,
    profile: object,
    provider_source: object,
):
    normalized_profile = (
        profile.strip().lower() if isinstance(profile, str) and profile.strip() else None
    )
    normalized_provider_source = (
        provider_source.strip().lower()
        if isinstance(provider_source, str) and provider_source.strip()
        else None
    )
    if normalized_profile is None and normalized_provider_source is None:
        return None

    runtime_settings = get_settings()
    model_copy = getattr(runtime_settings, "model_copy", None)
    if callable(model_copy):
        effective_settings = model_copy(
            update={
                "tool_registry_profile": (
                    normalized_profile
                    if normalized_profile is not None
                    else getattr(runtime_settings, "tool_registry_profile", None)
                ),
                "tool_registry_provider_source": (
                    normalized_provider_source
                    if normalized_provider_source is not None
                    else getattr(runtime_settings, "tool_registry_provider_source", None)
                ),
            }
        )
    else:
        effective_settings = SimpleNamespace(
            tool_registry_profile=(
                normalized_profile
                if normalized_profile is not None
                else getattr(runtime_settings, "tool_registry_profile", None)
            ),
            tool_registry_provider_source=(
                normalized_provider_source
                if normalized_provider_source is not None
                else getattr(runtime_settings, "tool_registry_provider_source", None)
            ),
            tool_registry_overrides_json=getattr(
                runtime_settings, "tool_registry_overrides_json", None
            ),
            tool_registry_extra_tools_json=getattr(
                runtime_settings, "tool_registry_extra_tools_json", None
            ),
            tool_registry_loaders_json=getattr(
                runtime_settings, "tool_registry_loaders_json", None
            ),
            tool_registry_loader_factories_json=getattr(
                runtime_settings, "tool_registry_loader_factories_json", None
            ),
            tool_registry_providers_json=getattr(
                runtime_settings, "tool_registry_providers_json", None
            ),
            tool_registry_provider_factories_json=getattr(
                runtime_settings, "tool_registry_provider_factories_json", None
            ),
            tool_registry_provider_sources_json=getattr(
                runtime_settings, "tool_registry_provider_sources_json", None
            ),
        )
    return get_configured_tool_registry_provider(settings=effective_settings)


def _normalize_governance_allowed_tool_labels(
    allowed_tool_names: object,
    allowed_tool_labels: object,
    *,
    profile: object = None,
    provider_source: object = None,
) -> list[str]:
    normalized_names = _normalize_governance_string_list(allowed_tool_names)
    normalized_labels = _normalize_governance_string_list(allowed_tool_labels)
    if not normalized_names:
        return normalized_labels

    registry_provider = _build_governance_registry_provider(
        profile=profile,
        provider_source=provider_source,
    )
    resolved_labels: list[str] = []
    for index, tool_name in enumerate(normalized_names):
        current_label = (
            normalized_labels[index] if index < len(normalized_labels) else None
        )
        canonical_label = get_tool_display_name(
            tool_name,
            registry_provider=registry_provider,
        )
        if current_label is None:
            resolved_labels.append(canonical_label)
            continue
        if normalize_tool_registry_name(current_label) == tool_name:
            resolved_labels.append(canonical_label)
            continue
        if normalize_tool_registry_name(current_label) == normalize_tool_registry_name(
            canonical_label
        ):
            resolved_labels.append(canonical_label)
            continue
        resolved_labels.append(current_label)

    if len(normalized_labels) > len(normalized_names):
        resolved_labels.extend(normalized_labels[len(normalized_names) :])
    return _normalize_governance_string_list(resolved_labels)


def _has_task_governance_values(governance: object) -> bool:
    if not isinstance(governance, dict):
        return False
    if isinstance(governance.get("profile"), str):
        return True
    if isinstance(governance.get("provider_source"), str):
        return True
    if isinstance(governance.get("allowed_tool_names"), (list, tuple)) and bool(
        governance.get("allowed_tool_names")
    ):
        return True
    if isinstance(governance.get("allowed_tool_labels"), (list, tuple)) and bool(
        governance.get("allowed_tool_labels")
    ):
        return True
    return False


def _has_session_governance_values(governance: object) -> bool:
    if not isinstance(governance, dict):
        return False
    if isinstance(governance.get("profiles"), (list, tuple)) and bool(
        governance.get("profiles")
    ):
        return True
    if isinstance(governance.get("provider_sources"), (list, tuple)) and bool(
        governance.get("provider_sources")
    ):
        return True
    if isinstance(governance.get("allowed_tool_names"), (list, tuple)) and bool(
        governance.get("allowed_tool_names")
    ):
        return True
    if isinstance(governance.get("allowed_tool_labels"), (list, tuple)) and bool(
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
    normalized_profile = (
        _normalize_governance_filter(governance.get("profile"))
        if isinstance(governance.get("profile"), str)
        else None
    )
    normalized_provider_source = (
        _normalize_governance_filter(governance.get("provider_source"))
        if isinstance(governance.get("provider_source"), str)
        else None
    )
    normalized = {
        "profile": normalized_profile,
        "provider_source": normalized_provider_source,
        "allowed_tool_names": _normalize_governance_string_list(
            governance.get("allowed_tool_names")
        ),
        "allowed_tool_labels": _normalize_governance_allowed_tool_labels(
            governance.get("allowed_tool_names"),
            governance.get("allowed_tool_labels"),
            profile=normalized_profile,
            provider_source=normalized_provider_source,
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
    normalized_profiles = _normalize_governance_filter_list(governance.get("profiles"))
    normalized_provider_sources = _normalize_governance_filter_list(
        governance.get("provider_sources")
    )
    normalized = {
        "profiles": normalized_profiles,
        "provider_sources": normalized_provider_sources,
        "allowed_tool_names": _normalize_governance_summary_string_list(
            governance.get("allowed_tool_names")
        ),
        "allowed_tool_labels": _normalize_governance_summary_string_list(
            _normalize_governance_allowed_tool_labels(
                governance.get("allowed_tool_names"),
                governance.get("allowed_tool_labels"),
                profile=normalized_profiles[0] if len(normalized_profiles) == 1 else None,
                provider_source=(
                    normalized_provider_sources[0]
                    if len(normalized_provider_sources) == 1
                    else None
                ),
            )
        ),
    }
    if not _has_session_governance_values(normalized):
        return None
    return normalized


def _normalize_task_governance_payload(value: object) -> dict[str, object] | None:
    coerced = _coerce_payload_mapping_or_none(value)
    if coerced is None:
        return None
    normalized = _normalize_task_governance_dict(coerced)
    if normalized is None:
        return coerced
    compact: dict[str, object] = {}
    if isinstance(normalized.get("profile"), str):
        compact["profile"] = normalized["profile"]
    if isinstance(normalized.get("provider_source"), str):
        compact["provider_source"] = normalized["provider_source"]
    if isinstance(normalized.get("allowed_tool_names"), list) and normalized.get(
        "allowed_tool_names"
    ):
        compact["allowed_tool_names"] = list(normalized["allowed_tool_names"])
    if isinstance(normalized.get("allowed_tool_labels"), list) and normalized.get(
        "allowed_tool_labels"
    ):
        compact["allowed_tool_labels"] = list(normalized["allowed_tool_labels"])
    return compact


def _normalize_task_governance_payload_or_original(value: object) -> object:
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return _normalize_task_governance_payload(dumped)
    return value


def _normalize_session_governance_payload_or_original(value: object) -> object:
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return _normalize_session_governance_summary_dict(dumped) or dict(dumped)
    return value


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
    task = _coerce_export_payload_block_to_dict(task)
    if not task.get("trace_json"):
        return []
    return _load_parsed_trace_steps_from_trace_json(task["trace_json"])


def get_task_usage_from_task(task: dict) -> dict[str, object] | None:
    task = _coerce_export_payload_block_to_dict(task)
    return _parse_usage_json_blob(task.get("usage_json"))


def _normalize_trace_preview_excerpt(text: str, limit: int = 160) -> str:
    normalized = " ".join((text or "").strip().split())
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def _stringify_trace_tool_output_preview(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        parsed_mapping = _parse_trace_tool_json_mapping_string(value)
        if isinstance(parsed_mapping, dict):
            return json.dumps(parsed_mapping, ensure_ascii=False, separators=(",", ":"))
        return value.strip()
    if isinstance(value, tuple):
        value = list(value)
    if isinstance(value, (dict, list, int, float, bool)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return ""


def _parse_trace_tool_json_mapping_string(value: str) -> dict[str, object] | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, str):
        nested = parsed.strip()
        if not nested.startswith("{"):
            return None
        try:
            parsed = json.loads(nested)
        except json.JSONDecodeError:
            return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _coerce_trace_tool_output_preview_mapping(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    return _parse_trace_tool_json_mapping_string(value)


def _coerce_trace_tool_output_mapping(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    return _parse_trace_tool_json_mapping_string(value)


def _resolve_trace_safe_tool_output(tool_meta: dict[str, object]) -> object | None:
    output_keys = tool_meta.get("effective_result_output_keys")
    if not isinstance(output_keys, (list, tuple)):
        return None
    normalized_keys = [
        key.strip()
        for key in output_keys
        if isinstance(key, str) and key.strip()
    ]
    if not normalized_keys:
        return None
    output = tool_meta.get("output")
    output_mapping = _coerce_trace_tool_output_mapping(output)
    if not isinstance(output_mapping, dict):
        return output
    return {
        key: output_mapping[key]
        for key in normalized_keys
        if key in output_mapping
    }


def _stringify_trace_safe_tool_output(tool_meta: dict[str, object]) -> str:
    return _stringify_trace_tool_output_preview(
        _resolve_trace_safe_tool_output(tool_meta)
    )


def _resolve_trace_tool_result_summary_input(
    tool_meta: dict[str, object],
) -> dict[str, object] | None:
    safe_output = _resolve_trace_safe_tool_output(tool_meta)
    if isinstance(safe_output, dict):
        return safe_output
    preview_output = _coerce_trace_tool_output_preview_mapping(
        tool_meta.get("output_preview")
    )
    if isinstance(preview_output, dict):
        return preview_output
    return None


def _normalize_trace_tool_semantic_kind(raw_value: object) -> str | None:
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip().lower()
    if not normalized:
        return None
    if normalized == "retrieval":
        return "knowledge_retrieval"
    if (
        normalized == "knowledge_retrieval"
        or normalized.endswith("knowledge_retrieval")
        or normalized.endswith("_retrieval")
    ):
        return "knowledge_retrieval"
    if normalized == "planner":
        return "task_planner"
    if normalized == "task_planner" or normalized.endswith("_planner"):
        return "task_planner"
    if normalized == "calculator":
        return "local_calculator"
    if (
        normalized == "local_calculator"
        or normalized.endswith("_calculator")
        or normalized.endswith("_calc")
    ):
        return "local_calculator"
    return normalized


def _normalize_trace_tool_label(raw_value: object) -> str:
    if not isinstance(raw_value, str):
        return ""
    normalized = raw_value.strip()
    normalized = re.sub(r"\s*\[[^\[\]]+\]\s*$", "", normalized)
    return " ".join(normalized.lower().replace("_", " ").split())


def _trace_tool_label_implies_local_knowledge_retrieval(raw_value: object) -> bool:
    normalized = _normalize_trace_tool_label(raw_value)
    return normalized in {
        "knowledge retrieval",
        "hot retrieval",
        "task retrieve",
        "task retrieve hot",
        "mock retrieve",
    }


def _trace_tool_label_implies_real_retrieval_summary(raw_value: object) -> bool:
    normalized = _normalize_trace_tool_label(raw_value)
    return normalized in {
        "provider search",
        "hosted search",
        "provider retrieval",
    }


def _trace_tool_label_implies_real_calc_summary(raw_value: object) -> bool:
    normalized = _normalize_trace_tool_label(raw_value)
    return normalized in {
        "provider math",
        "hosted math",
        "provider calc",
        "provider calculator",
        "hosted calc",
        "hosted calculator",
    }


def _trace_tool_label_implies_planner_summary(raw_value: object) -> bool:
    normalized = _normalize_trace_tool_label(raw_value)
    return normalized in {
        "task planner",
        "provider planner",
        "hosted planner",
        "mock planner",
    }


def _normalize_trace_tool_result_plan_steps(raw_steps: object) -> list[str]:
    if not isinstance(raw_steps, (list, tuple)):
        return []
    normalized_steps: list[str] = []
    for raw_step in raw_steps:
        if not isinstance(raw_step, str):
            continue
        step = raw_step.strip()
        if step:
            normalized_steps.append(step)
    return normalized_steps


def _infer_trace_tool_result_summary(tool_meta: dict[str, object]) -> str:
    output = _resolve_trace_tool_result_summary_input(tool_meta)
    if not isinstance(output, dict):
        return ""
    raw_output = tool_meta.get("output") if isinstance(tool_meta.get("output"), dict) else None
    raw_preview_output = (
        _coerce_trace_tool_output_preview_mapping(tool_meta.get("output_preview"))
    )

    explicit_semantic_kind = _normalize_trace_tool_semantic_kind(
        tool_meta.get("semantic_kind")
    )
    fallback_runtime_kind = _normalize_trace_tool_semantic_kind(
        tool_meta.get("kind")
        or output.get("tool_kind")
        or output.get("kind")
        or (raw_output or {}).get("tool_kind")
        or (raw_output or {}).get("kind")
        or (raw_preview_output or {}).get("tool_kind")
        or (raw_preview_output or {}).get("kind")
    )
    runtime_semantic_kind = explicit_semantic_kind or fallback_runtime_kind
    semantic_family = _normalize_trace_tool_semantic_kind(
        tool_meta.get("semantic_family") or output.get("tool_family")
    )
    label_implies_real_calc = (
        _trace_tool_label_implies_real_calc_summary(tool_meta.get("label"))
        or _trace_tool_label_implies_real_calc_summary(tool_meta.get("name"))
    )

    plan = output.get("plan")
    if isinstance(plan, str) and plan.strip():
        return f"Planned steps - {plan.strip()}."
    steps = _normalize_trace_tool_result_plan_steps(output.get("steps"))
    if steps:
        return f"Planned steps - {' -> '.join(steps)}."

    expression = output.get("expression")
    result = output.get("result")
    request_id = output.get("request_id")
    if isinstance(expression, str) and expression.strip() and result is not None:
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Calculated {expression.strip()} = {result} "
                f"(request id {request_id.strip()})."
            )
        return f"Calculated {expression.strip()} = {result}."
    if (
        semantic_family == "local_calculator"
        or runtime_semantic_kind == "local_calculator"
        or (
            result is not None
            and semantic_family is None
            and runtime_semantic_kind is None
            and label_implies_real_calc
        )
    ) and result is not None:
        if isinstance(request_id, str) and request_id.strip():
            return f"Calculated result = {result} (request id {request_id.strip()})."
        return f"Calculated result = {result}."

    hit_count = output.get("hit_count")
    knowledge_base_id = output.get("knowledge_base_id")
    if isinstance(hit_count, int) and hit_count >= 0:
        hit_label = "hit" if hit_count == 1 else "hits"
        label_implies_local_retrieval = (
            _trace_tool_label_implies_local_knowledge_retrieval(tool_meta.get("label"))
            or _trace_tool_label_implies_local_knowledge_retrieval(tool_meta.get("name"))
        )
        if (
            (
                explicit_semantic_kind == "knowledge_retrieval"
                or (
                    explicit_semantic_kind is None
                    and (
                        semantic_family == "knowledge_retrieval"
                        or (
                            semantic_family is None
                            and label_implies_local_retrieval
                        )
                    )
                )
            )
            and isinstance(knowledge_base_id, str)
            and knowledge_base_id.strip()
        ):
            if isinstance(request_id, str) and request_id.strip():
                return (
                    f"Retrieved {hit_count} {hit_label} from knowledge base "
                    f"{knowledge_base_id.strip()} (request id {request_id.strip()})."
                )
            return (
                f"Retrieved {hit_count} {hit_label} from knowledge base "
                f"{knowledge_base_id.strip()}."
            )
        if (
            runtime_semantic_kind != "knowledge_retrieval"
            and semantic_family == "knowledge_retrieval"
        ):
            if isinstance(request_id, str) and request_id.strip():
                return f"Retrieved {hit_count} {hit_label} (request id {request_id.strip()})."
            return f"Retrieved {hit_count} {hit_label}."
        if isinstance(request_id, str) and request_id.strip():
            return f"Retrieved {hit_count} {hit_label} (request id {request_id.strip()})."
        return f"Retrieved {hit_count} {hit_label}."

    documents_total = output.get("documents_total")
    if isinstance(documents_total, int) and documents_total >= 0:
        document_label = "document" if documents_total == 1 else "documents"
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Retrieved {documents_total} {document_label} "
                f"(request id {request_id.strip()})."
            )
        return f"Retrieved {documents_total} {document_label}."
    return ""


def _resolve_trace_tool_semantic_category(
    tool_meta: dict[str, object],
) -> str | None:
    semantic = _normalize_trace_tool_semantic_kind(
        tool_meta.get("semantic_family")
        or tool_meta.get("semantic_kind")
        or tool_meta.get("kind")
    )
    if semantic:
        if semantic == "knowledge_retrieval" or semantic.endswith("_retrieval"):
            return "retrieval"
        if (
            semantic == "local_calculator"
            or semantic.endswith("_calculator")
            or semantic.endswith("_calc")
        ):
            return "calculator"
        if semantic == "task_planner" or semantic.endswith("_planner"):
            return "planner"
    output = _resolve_trace_tool_result_summary_input(tool_meta)
    if not isinstance(output, dict):
        return None
    label_implies_retrieval = (
        _trace_tool_label_implies_local_knowledge_retrieval(tool_meta.get("label"))
        or _trace_tool_label_implies_local_knowledge_retrieval(tool_meta.get("name"))
        or _trace_tool_label_implies_real_retrieval_summary(tool_meta.get("label"))
        or _trace_tool_label_implies_real_retrieval_summary(tool_meta.get("name"))
    )
    if label_implies_retrieval and (
        (isinstance(output.get("hit_count"), int) and output.get("hit_count") >= 0)
        or (
            isinstance(output.get("documents_total"), int)
            and output.get("documents_total") >= 0
        )
    ):
        return "retrieval"
    label_implies_calc = (
        _trace_tool_label_implies_real_calc_summary(tool_meta.get("label"))
        or _trace_tool_label_implies_real_calc_summary(tool_meta.get("name"))
    )
    if label_implies_calc and output.get("result") is not None:
        return "calculator"
    label_implies_planner = (
        _trace_tool_label_implies_planner_summary(tool_meta.get("label"))
        or _trace_tool_label_implies_planner_summary(tool_meta.get("name"))
    )
    plan = output.get("plan")
    steps = _normalize_trace_tool_result_plan_steps(output.get("steps"))
    if label_implies_planner and (
        (isinstance(plan, str) and plan.strip()) or steps
    ):
        return "planner"
    return None


def _format_trace_tool_semantic_descriptor(tool_meta: dict[str, object]) -> str:
    semantic_kind = str(tool_meta.get("semantic_kind") or tool_meta.get("kind") or "").strip()
    semantic_family = str(tool_meta.get("semantic_family") or "").strip()
    if not semantic_kind:
        return semantic_family or (_resolve_trace_tool_semantic_category(tool_meta) or "")
    if not semantic_family or semantic_family == semantic_kind:
        return semantic_kind
    return f"{semantic_kind} · {semantic_family}"


def _resolve_trace_tool_display_label(tool_meta: dict[str, object]) -> str:
    tool_name = str(tool_meta.get("name") or "").strip()
    tool_label = str(tool_meta.get("label") or "").strip()
    if not tool_name:
        return tool_label
    canonical_label = get_tool_display_name(tool_name)
    if not tool_label:
        return canonical_label
    if normalize_tool_registry_name(tool_label) == normalize_tool_registry_name(
        tool_name
    ):
        return canonical_label
    return tool_label


def get_trace_step_display_title(step: TraceStep) -> str:
    meta = getattr(step, "meta", None)
    tool_meta = getattr(meta, "tool", None) if meta is not None else None
    if isinstance(tool_meta, dict):
        tool_label = _resolve_trace_tool_display_label(tool_meta)
        semantic_descriptor = _format_trace_tool_semantic_descriptor(tool_meta)
        if tool_label:
            return (
                f"{tool_label} [{semantic_descriptor}]"
                if semantic_descriptor
                else tool_label
            )
    rag_meta = getattr(meta, "rag", None) if meta is not None else None
    if isinstance(rag_meta, dict):
        return "Knowledge Retrieval Snippets"
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


def get_trace_step_display_content(step: TraceStep) -> str:
    content = str(getattr(step, "content", "") or "")
    meta = getattr(step, "meta", None)
    tool_registry_meta = getattr(meta, "tool_registry", None) if meta is not None else None
    tool_meta = getattr(meta, "tool", None) if meta is not None else None
    tool_registry_lines: list[str] = []
    if isinstance(tool_registry_meta, dict):
        raw_entries = tool_registry_meta.get("entries", ())
        if isinstance(raw_entries, (list, tuple)):
            for entry in raw_entries:
                if not isinstance(entry, dict):
                    continue
                kind = str(entry.get("kind", "")).strip().lower()
                target = str(entry.get("target", "")).strip().lower().replace("_", " ")
                label = f"{kind} {target}".strip()
                raw_values = entry.get("values", ())
                values = (
                    [
                        str(value).strip()
                        for value in raw_values
                        if str(value).strip()
                    ]
                    if isinstance(raw_values, (list, tuple))
                    else []
                )
                if values:
                    tool_registry_lines.append(f"{label}: {', '.join(values)}")
                    continue
                count = int(entry.get("count", 0) or 0)
                if label:
                    tool_registry_lines.append(f"{label}: {count}")
    if not isinstance(tool_meta, dict):
        if not tool_registry_lines:
            return content
        base_lines = [content] if content else []
        diagnostics_lines = [
            line for line in tool_registry_lines if line not in base_lines
        ]
        return "\n".join([*base_lines, *diagnostics_lines])
    result_summary = tool_meta.get("result_summary")
    normalized_result_summary = (
        result_summary.strip()
        if isinstance(result_summary, str) and result_summary.strip()
        else ""
    )
    if not normalized_result_summary:
        normalized_result_summary = _infer_trace_tool_result_summary(tool_meta)
    primary_content = content
    if normalized_result_summary:
        stripped_content = content.strip()
        if not stripped_content or stripped_content.startswith("Tool done:"):
            primary_content = normalized_result_summary
        elif normalized_result_summary not in stripped_content:
            primary_content = "\n".join(
                part for part in (content, normalized_result_summary) if part
            )
    preview_text = _stringify_trace_tool_output_preview(
        tool_meta.get("output_preview")
    )
    safe_output_text = _stringify_trace_safe_tool_output(tool_meta)
    preview_line = (
        f"Preview: {preview_text}"
        if preview_text and preview_text not in primary_content
        else ""
    )
    output_line = (
        f"Output: {safe_output_text}"
        if safe_output_text and safe_output_text != preview_text
        else ""
    )
    base_lines = [
        part for part in (primary_content, preview_line, output_line) if part
    ]
    diagnostics_lines = [
        line
        for line in tool_registry_lines
        if not any(line in existing for existing in base_lines)
    ]
    if not base_lines:
        if diagnostics_lines:
            return "\n".join(diagnostics_lines)
        return primary_content or preview_text or safe_output_text
    return "\n".join([*base_lines, *diagnostics_lines])


def get_trace_step_markdown_meta(step: TraceStep) -> dict[str, object] | None:
    meta = getattr(step, "meta", None)
    if meta is None:
        return None
    payload = (
        meta.model_dump(exclude_none=True)
        if hasattr(meta, "model_dump")
        else dict(meta)
        if isinstance(meta, dict)
        else None
    )
    if not isinstance(payload, dict):
        return None
    tool_meta = payload.get("tool")
    if isinstance(tool_meta, dict):
        sanitized_tool_meta = dict(tool_meta)
        preview_value = sanitized_tool_meta.get("output_preview")
        safe_output_value = _resolve_trace_safe_tool_output(sanitized_tool_meta)
        if preview_value is not None and safe_output_value is None:
            sanitized_tool_meta["output"] = preview_value
        elif safe_output_value is not None:
            sanitized_tool_meta["output"] = safe_output_value
        payload["tool"] = sanitized_tool_meta
    return payload


def _trace_preview_title(step: TraceStep) -> str:
    return get_trace_step_display_title(step)


def get_task_trace_preview_summary_from_task(
    task: dict,
    *,
    preview_limit: int = 3,
) -> dict[str, object]:
    trace_summary = get_task_trace_export_summary_from_task(task)
    trace_steps = _coerce_export_trace_steps(trace_summary.get("steps"))
    trace_step_count = int(trace_summary.get("step_count", len(trace_steps)) or 0)
    rag_hit_count = int(trace_summary.get("rag_hit_count", 0) or 0)

    preview_steps: list[dict[str, object]] = []
    bounded_limit = max(0, int(preview_limit))
    for step in trace_steps[-bounded_limit:] if bounded_limit else []:
        preview_steps.append(
            {
                "id": str(getattr(step, "id", "")),
                "seq": getattr(step, "seq", None),
                "type": str(getattr(step, "type", "")),
                "title": _trace_preview_title(step),
                "content_excerpt": _normalize_trace_preview_excerpt(
                    get_trace_step_display_content(step),
                    limit=160,
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
        if isinstance(raw_chunks, (list, tuple)):
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
    rag_chunks = _coerce_export_payload_block_list_to_dicts(
        rag_summary.get("rag_chunks")
    )
    return {
        "steps": trace_steps,
        "step_count": len(trace_steps),
        "rag_hit_count": int(rag_summary.get("rag_hit_count", 0) or 0),
        "rag_knowledge_base_ids": rag_knowledge_base_ids,
        "rag_chunks": rag_chunks,
    }


def _get_task_status_summary_from_task(task: dict) -> dict[str, object]:
    task = _coerce_export_payload_block_to_dict(task)
    status = str(task.get("status", ""))
    return {
        "status": status,
        "status_normalized": normalize_task_status(status),
        "status_label": task_status_label(status),
        "status_rank": task_status_rank(status),
    }


def get_task_trace_response_summary_from_task(task: dict) -> dict[str, object]:
    trace_summary = get_task_trace_export_summary_from_task(task)
    return {
        "steps": _coerce_export_trace_steps(trace_summary.get("steps")),
        **_get_task_status_summary_from_task(task),
    }


def get_task_trace_delta_response_summary_from_task(
    task: dict,
    *,
    after_seq: int = 0,
    limit: int = 200,
) -> dict[str, object]:
    parsed_steps, next_cursor, has_more, latest_seq, _latest_step_id = (
        get_task_trace_delta_snapshot_from_task(
            task,
            after_seq=after_seq,
            limit=limit,
        )
    )
    return {
        "steps": parsed_steps,
        "next_cursor": next_cursor,
        "has_more": has_more,
        "lag_seq": max(0, latest_seq - next_cursor),
        "dropped": False,
    }


def get_task_response_summary_from_task(task: dict) -> dict[str, object]:
    task = _coerce_export_payload_block_to_dict(task)
    return {
        "id": str(task.get("id", "")),
        "session_id": str(task.get("session_id", "")),
        "prompt": str(task.get("prompt", "")),
        **_get_task_status_summary_from_task(task),
        "governance": _normalize_task_governance_payload(task.get("governance")),
        "trace_json": task.get("trace_json"),
        "usage_json": task.get("usage_json"),
        "created_at": str(task.get("created_at", "")),
        "updated_at": str(task.get("updated_at", "")),
    }


def get_task_cancel_response_summary_from_task(
    task: dict,
    *,
    previous_status: str,
    already_terminal: bool,
) -> dict[str, object]:
    task = _coerce_export_payload_block_to_dict(task)
    return {
        "task_id": str(task.get("id", "")),
        "previous_status": previous_status,
        **_get_task_status_summary_from_task(task),
        "already_terminal": already_terminal,
    }


def get_task_create_response_summary(
    *,
    task_id: str,
    session_id: str,
    status: str,
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "session_id": session_id,
        **_get_task_status_summary_from_task({"status": status}),
    }


def get_task_export_summary_from_task(task: dict) -> dict[str, object]:
    task = _coerce_export_payload_block_to_dict(task)
    trace_summary = get_task_trace_export_summary_from_task(task)
    trace_steps = _coerce_export_trace_steps(trace_summary.get("steps"))
    return {
        "task": {
            "id": str(task.get("id", "")),
            "session_id": str(task.get("session_id", "")),
            "prompt": str(task.get("prompt", "")),
            **_get_task_status_summary_from_task(task),
            "created_at": str(task.get("created_at", "")),
            "updated_at": str(task.get("updated_at", "")),
        },
        "usage": get_task_usage_from_task(task),
        "trace": {
            "governance": _normalize_task_governance_payload(task.get("governance")),
            "steps": trace_steps,
            "step_count": int(trace_summary.get("step_count", 0) or 0),
            "rag_hit_count": int(trace_summary.get("rag_hit_count", 0) or 0),
            "rag_knowledge_base_ids": [
                str(item)
                for item in trace_summary.get("rag_knowledge_base_ids", [])
                if isinstance(item, str)
            ],
            "rag_chunks": _coerce_export_payload_block_list_to_dicts(
                trace_summary.get("rag_chunks")
            ),
        },
    }


def get_task_export_payload_summary(
    task: dict,
    message_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
) -> dict[str, object]:
    export_summary = get_task_export_summary_from_task(task)
    export_message_rows = _coerce_export_payload_block_list_to_dicts(message_rows)
    return {
        "task": export_summary.get("task"),
        "usage": export_summary.get("usage"),
        "trace": export_summary.get("trace"),
        "messages": [
            {
                "id": str(row.get("id", "")),
                "role": str(row.get("role", "")),
                "content": str(row.get("content", "")),
                "created_at": str(row.get("created_at", "")),
            }
            for row in export_message_rows
        ],
    }


def _coerce_export_payload_block_to_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped
    return {}


def _coerce_export_payload_block_list_to_dicts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, (list, tuple)):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        row = _coerce_export_payload_block_to_dict(item)
        if row:
            rows.append(row)
    return rows


def _coerce_payload_mapping_or_original(value: object) -> object:
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dict(dumped)
    return value


def _coerce_payload_mapping_or_none(value: object) -> dict[str, object] | None:
    mapped = _coerce_payload_mapping_or_original(value)
    return mapped if isinstance(mapped, dict) else None


def _coerce_export_trace_steps(value: object) -> list[TraceStep]:
    if not isinstance(value, (list, tuple)):
        return []
    steps: list[TraceStep] = []
    for item in value:
        if isinstance(item, TraceStep):
            steps.append(item)
            continue
        row = _coerce_export_payload_block_to_dict(item)
        if row:
            steps.append(TraceStep.model_validate(row))
    return steps


def get_task_export_response_summary(
    task: dict,
    message_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
) -> dict[str, object]:
    payload_summary = _coerce_export_payload_block_to_dict(
        get_task_export_payload_summary(task, message_rows)
    )
    trace_summary = _coerce_export_payload_block_to_dict(payload_summary.get("trace"))
    trace_steps = _coerce_export_trace_steps(trace_summary.get("steps"))
    return {
        "task": payload_summary.get("task"),
        "usage": payload_summary.get("usage"),
        "messages": payload_summary.get("messages", []),
        "trace": {
            "governance": _normalize_task_governance_payload(
                trace_summary.get("governance")
            ),
            "step_count": int(trace_summary.get("step_count", len(trace_steps)) or 0),
            "rag_hit_count": int(trace_summary.get("rag_hit_count", 0) or 0),
            "rag_knowledge_base_ids": [
                str(item)
                for item in trace_summary.get("rag_knowledge_base_ids", [])
                if isinstance(item, str)
            ],
            "rag_chunks": _coerce_export_payload_block_list_to_dicts(
                trace_summary.get("rag_chunks")
            ),
            "steps": trace_steps,
        },
    }


def get_task_trace_delta_snapshot_from_task(
    task: dict,
    *,
    after_seq: int = 0,
    limit: int = 200,
) -> tuple[list[TraceStep], int, bool, int, str | None]:
    task = _coerce_export_payload_block_to_dict(task)
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

    resolved_allowed_tool_labels = list(allowed_tool_labels)
    merged_allowed_tool_names = list(allowed_tool_names)
    merged_profile = next(iter(profiles)) if len(profiles) == 1 else None
    merged_provider_source = (
        next(iter(provider_sources)) if len(provider_sources) == 1 else None
    )
    if merged_allowed_tool_names and resolved_allowed_tool_labels:
        registry_provider = _build_governance_registry_provider(
            profile=merged_profile,
            provider_source=merged_provider_source,
        )
        canonical_labels_by_normalized_value = {
            normalize_tool_registry_name(
                get_tool_display_name(tool_name, registry_provider=registry_provider)
            ): get_tool_display_name(tool_name, registry_provider=registry_provider)
            for tool_name in merged_allowed_tool_names
        }
        resolved_allowed_tool_labels = [
            canonical_labels_by_normalized_value.get(
                normalize_tool_registry_name(label),
                label,
            )
            for label in resolved_allowed_tool_labels
        ]

    return {
        "profiles": sorted(profiles),
        "provider_sources": sorted(provider_sources),
        "allowed_tool_names": _normalize_governance_summary_string_list(
            merged_allowed_tool_names
        ),
        "allowed_tool_labels": _normalize_governance_summary_string_list(
            resolved_allowed_tool_labels
        ),
    }


def get_task_rows_governance_summary(
    task_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
) -> dict[str, object] | None:
    task_rows = _coerce_export_payload_block_list_to_dicts(task_rows)
    governance_summary: dict[str, object] | None = None
    for task_row in task_rows:
        raw_task_governance = _coerce_payload_mapping_or_none(task_row.get("governance"))
        if raw_task_governance is None:
            continue
        task_governance = (
            _normalize_task_governance_dict(raw_task_governance) or raw_task_governance
        )
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
    task_rows = _coerce_export_payload_block_list_to_dicts(task_rows)
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
                "trace_preview": _coerce_export_payload_block_list_to_dicts(
                    preview_summary.get("trace_preview")
                ),
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
    task_rows = _coerce_export_payload_block_list_to_dicts(task_rows)
    trace_summary = get_task_rows_trace_preview_summary(
        task_rows,
        preview_limit=preview_limit,
    )
    return {
        "tasks": _coerce_export_payload_block_list_to_dicts(trace_summary.get("tasks")),
        "trace_step_count": int(trace_summary.get("trace_step_count", 0) or 0),
        "rag_hit_count": int(trace_summary.get("rag_hit_count", 0) or 0),
        "governance": get_task_rows_governance_summary(task_rows),
    }


def get_task_rows_session_export_summary(
    task_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    preview_limit: int = 3,
) -> dict[str, object]:
    task_rows = _coerce_export_payload_block_list_to_dicts(task_rows)
    export_summary = get_task_rows_export_summary(task_rows, preview_limit=preview_limit)
    export_task_rows = _coerce_export_payload_block_list_to_dicts(export_summary.get("tasks"))
    trace_summary_by_task_id = {
        str(row.get("task_id", "")): row
        for row in export_task_rows
    }
    task_summaries: list[dict[str, object]] = []
    for task_row in task_rows:
        task_id = str(task_row.get("id", ""))
        trace_summary = trace_summary_by_task_id.get(task_id, {})
        raw_governance = task_row.get("governance")
        task_summaries.append(
            {
                "task": {
                    "id": task_id,
                    "prompt": str(task_row.get("prompt", "")),
                    **_get_task_status_summary_from_task(task_row),
                    "created_at": str(task_row.get("created_at", "")),
                    "updated_at": str(task_row.get("updated_at", "")),
                },
                "usage": get_task_usage_from_task(task_row),
                "trace": {
                    "governance": (
                        _normalize_task_governance_dict(
                            _coerce_payload_mapping_or_none(raw_governance)
                        )
                        or _coerce_payload_mapping_or_none(raw_governance)
                    ),
                    "step_count": int(trace_summary.get("trace_step_count", 0) or 0),
                    "rag_hit_count": int(trace_summary.get("rag_hit_count", 0) or 0),
                    "preview": _coerce_export_payload_block_list_to_dicts(
                        trace_summary.get("trace_preview")
                    ),
                },
            }
        )

    trace_step_count = int(export_summary.get("trace_step_count", 0) or 0)
    rag_hit_count = int(export_summary.get("rag_hit_count", 0) or 0)
    return {
        "tasks": task_summaries,
        "stats": {
            "task_count": len(task_summaries),
            "trace_step_count": trace_step_count,
            "rag_hit_count": rag_hit_count,
        },
        "governance": export_summary.get("governance"),
    }


def get_session_export_payload_summary(
    *,
    usage_summary: dict[str, object],
    task_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
    message_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
    preview_limit: int = 3,
) -> dict[str, object]:
    export_summary = get_task_rows_session_export_summary(
        task_rows,
        preview_limit=preview_limit,
    )
    task_summaries = _coerce_export_payload_block_list_to_dicts(export_summary.get("tasks"))
    stats_summary = _coerce_export_payload_block_to_dict(export_summary.get("stats"))
    export_message_rows = _coerce_export_payload_block_list_to_dicts(message_rows)
    message_summaries = [
        {
            "id": str(row.get("id", "")),
            "task_id": str(row.get("task_id", ""))
            if row.get("task_id") is not None
            else None,
            "role": str(row.get("role", "")),
            "content": str(row.get("content", "")),
            "created_at": str(row.get("created_at", "")),
        }
        for row in export_message_rows
    ]
    return {
        "usage_summary": usage_summary,
        "tasks": task_summaries,
        "stats": {
            "task_count": int(stats_summary.get("task_count", len(task_summaries)) or 0),
            "message_count": len(message_summaries),
            "trace_step_count": int(stats_summary.get("trace_step_count", 0) or 0),
            "rag_hit_count": int(stats_summary.get("rag_hit_count", 0) or 0),
        },
        "governance": export_summary.get("governance"),
        "messages": message_summaries,
    }


def _get_session_export_task_response_summary_from_payload_row(
    row: dict[str, object],
) -> dict[str, object]:
    if "task" not in row and "trace" not in row:
        return {
            "id": str(row.get("id", "")),
            "prompt": str(row.get("prompt", "")),
            "status": str(row.get("status", "")),
            "status_normalized": str(row.get("status_normalized", "")),
            "status_label": str(row.get("status_label", "")),
            "status_rank": int(row.get("status_rank", 0) or 0),
            "created_at": str(row.get("created_at", "")),
            "updated_at": str(row.get("updated_at", "")),
            "usage": row.get("usage"),
            "trace_step_count": int(row.get("trace_step_count", 0) or 0),
            "rag_hit_count": int(row.get("rag_hit_count", 0) or 0),
            "trace_preview": _coerce_export_payload_block_list_to_dicts(
                row.get("trace_preview")
            ),
            "governance": _normalize_task_governance_payload(row.get("governance")),
        }
    task_summary = _coerce_export_payload_block_to_dict(row.get("task"))
    trace_summary = _coerce_export_payload_block_to_dict(row.get("trace"))
    return {
        "id": str(task_summary.get("id", "")),
        "prompt": str(task_summary.get("prompt", "")),
        "status": str(task_summary.get("status", "")),
        "status_normalized": str(task_summary.get("status_normalized", "")),
        "status_label": str(task_summary.get("status_label", "")),
        "status_rank": int(task_summary.get("status_rank", 0) or 0),
        "created_at": str(task_summary.get("created_at", "")),
        "updated_at": str(task_summary.get("updated_at", "")),
        "usage": row.get("usage"),
        "trace_step_count": int(trace_summary.get("step_count", 0) or 0),
        "rag_hit_count": int(trace_summary.get("rag_hit_count", 0) or 0),
        "trace_preview": _coerce_export_payload_block_list_to_dicts(
            trace_summary.get("preview")
        ),
        "governance": _normalize_task_governance_payload(
            trace_summary.get("governance")
        ),
    }


def get_session_export_response_summary(
    *,
    usage_summary: dict[str, object],
    task_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
    message_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
    preview_limit: int = 3,
) -> dict[str, object]:
    payload_summary = _coerce_export_payload_block_to_dict(
        get_session_export_payload_summary(
            usage_summary=usage_summary,
            task_rows=task_rows,
            message_rows=message_rows,
            preview_limit=preview_limit,
        )
    )
    task_summaries: list[dict[str, object]] = []
    for row in payload_summary.get("tasks", []):
        row_summary = _coerce_export_payload_block_to_dict(row)
        if not row_summary:
            continue
        task_summaries.append(
            _get_session_export_task_response_summary_from_payload_row(row_summary)
        )
    stats_summary = _coerce_export_payload_block_to_dict(payload_summary.get("stats"))
    return {
        "usage_summary": payload_summary.get("usage_summary"),
        "tasks": task_summaries,
        "stats": {
            "task_count": int(stats_summary.get("task_count", len(task_summaries)) or 0),
            "message_count": int(stats_summary.get("message_count", 0) or 0),
            "trace_step_count": int(stats_summary.get("trace_step_count", 0) or 0),
            "rag_hit_count": int(stats_summary.get("rag_hit_count", 0) or 0),
        },
        "governance": _normalize_session_governance_payload_or_original(
            payload_summary.get("governance")
        ),
        "messages": payload_summary.get("messages", []),
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


def get_tasks_usage_dashboard_response_summary(
    payload: dict[str, object],
) -> dict[str, object]:
    trend_rows = _coerce_export_payload_block_list_to_dicts(payload.get("trend"))
    session_rows = _coerce_export_payload_block_list_to_dicts(payload.get("by_session"))
    top_task_rows = _coerce_export_payload_block_list_to_dicts(payload.get("top_tasks"))
    return {
        "window_days": int(payload.get("window_days", 0) or 0),
        "summary": _coerce_export_payload_block_to_dict(payload.get("summary")),
        "trend": trend_rows,
        "by_session": [
            {
                "session_id": str(row.get("session_id", "")),
                "session_title": (
                    row.get("session_title")
                    if isinstance(row.get("session_title"), str)
                    else None
                ),
                "tasks_with_usage": int(row.get("tasks_with_usage", 0) or 0),
                "total_tokens": int(row.get("total_tokens", 0) or 0),
                "cost_estimate": float(row.get("cost_estimate", 0.0) or 0.0),
                "last_task_at": (
                    str(row.get("last_task_at"))
                    if isinstance(row.get("last_task_at"), str)
                    else None
                ),
                "governance": _normalize_session_governance_payload_or_original(
                    row.get("governance")
                ),
            }
            for row in session_rows
        ],
        "top_tasks": [
            {
                "task_id": str(row.get("task_id", "")),
                "session_id": str(row.get("session_id", "")),
                "session_title": (
                    row.get("session_title")
                    if isinstance(row.get("session_title"), str)
                    else None
                ),
                "prompt_excerpt": str(row.get("prompt_excerpt", "")),
                "total_tokens": int(row.get("total_tokens", 0) or 0),
                "cost_estimate": float(row.get("cost_estimate", 0.0) or 0.0),
                "created_at": str(row.get("created_at", "")),
                "updated_at": str(row.get("updated_at", "")),
                "source_kind": str(row.get("source_kind", "legacy") or "legacy"),
                "governance": _normalize_task_governance_payload_or_original(
                    row.get("governance")
                ),
            }
            for row in top_task_rows
        ],
    }
