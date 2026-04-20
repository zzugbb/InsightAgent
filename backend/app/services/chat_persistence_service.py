from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from uuid import uuid4

from app.db import get_db_connection


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

    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET trace_json = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                json.dumps(normalized_trace_steps, ensure_ascii=False),
                current_time,
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

    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET status = ?, trace_json = ?, usage_json = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                status,
                json.dumps(normalized_trace_steps, ensure_ascii=False),
                usage_blob,
                current_time,
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


def count_tasks(user_id: str, session_id: str | None = None) -> int:
    with get_db_connection() as connection:
        if session_id:
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE user_id = ? AND session_id = ?",
                (user_id, session_id),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE user_id = ?",
                (user_id,),
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
            SELECT id, session_id, prompt, status, trace_json, usage_json, created_at, updated_at
            FROM tasks
            WHERE id = ? AND user_id = ?
            """,
            (task_id, user_id),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def list_tasks(
    user_id: str,
    limit: int = 20,
    session_id: str | None = None,
    offset: int = 0,
) -> list[dict]:
    with get_db_connection() as connection:
        if session_id:
            rows = connection.execute(
                """
                SELECT id, session_id, prompt, status, trace_json, usage_json, created_at, updated_at
                FROM tasks
                WHERE user_id = ? AND session_id = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, session_id, limit, offset),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, session_id, prompt, status, trace_json, usage_json, created_at, updated_at
                FROM tasks
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            ).fetchall()

    return [dict(row) for row in rows]


def get_session_tasks(session_id: str, user_id: str) -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, prompt, status, trace_json, usage_json, created_at, updated_at
            FROM tasks
            WHERE user_id = ? AND session_id = ?
            ORDER BY created_at ASC
            """,
            (user_id, session_id),
        ).fetchall()

    return [dict(row) for row in rows]


def get_task_trace(task_id: str, user_id: str) -> list[dict]:
    task = get_task(task_id, user_id)
    if task is None or not task["trace_json"]:
        return []
    return _normalize_trace_steps(json.loads(task["trace_json"]))


def get_task_trace_delta_from_task(
    task: dict,
    *,
    after_seq: int = 0,
    limit: int = 200,
) -> tuple[list[dict], int, bool]:
    bounded_limit = max(1, int(limit))
    trace_json = task.get("trace_json")
    raw_steps: list[dict] = []
    if isinstance(trace_json, str) and trace_json.strip():
        try:
            loaded = json.loads(trace_json)
            if isinstance(loaded, list):
                raw_steps = [x for x in loaded if isinstance(x, dict)]
        except Exception:
            raw_steps = []
    trace_steps = _normalize_trace_steps(raw_steps)
    all_delta_steps = [
        step for step in trace_steps if int(step.get("seq", 0)) > after_seq
    ]
    delta_steps = all_delta_steps[:bounded_limit]
    next_cursor = after_seq if not delta_steps else int(delta_steps[-1]["seq"])
    status = str(task.get("status", ""))
    still_running = status in ("pending", "running")
    has_more = len(all_delta_steps) > len(delta_steps) or still_running
    return delta_steps, next_cursor, has_more


def get_task_trace_delta(
    task_id: str,
    user_id: str,
    after_seq: int = 0,
    limit: int = 200,
) -> tuple[list[dict], int, bool]:
    task = get_task(task_id, user_id)
    if task is None:
        return [], after_seq, False
    return get_task_trace_delta_from_task(
        task,
        after_seq=after_seq,
        limit=limit,
    )


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
        usage_json = row["usage_json"]
        if not usage_json or not str(usage_json).strip():
            continue
        try:
            payload = json.loads(usage_json)
        except Exception:  # noqa: BLE001
            continue
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


def get_tasks_usage_dashboard(
    user_id: str,
    *,
    session_id: str | None = None,
    window_days: int = 14,
    top_sessions: int = 8,
    top_tasks: int = 12,
) -> dict[str, object]:
    """按用户聚合 usage 仪表盘：汇总、趋势、会话榜、任务榜。"""
    safe_window_days = max(1, min(int(window_days), 90))
    safe_top_sessions = max(1, min(int(top_sessions), 30))
    safe_top_tasks = max(1, min(int(top_tasks), 50))

    with get_db_connection() as connection:
        if session_id:
            rows = connection.execute(
                """
                SELECT
                    t.id,
                    t.session_id,
                    t.prompt,
                    t.usage_json,
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
            "total_tokens": 0,
            "cost_estimate": 0.0,
        }

    session_map: dict[str, dict[str, object]] = {}
    top_task_rows: list[dict[str, object]] = []

    for row in rows:
        usage_json = row["usage_json"]
        if not usage_json or not str(usage_json).strip():
            continue
        try:
            payload = json.loads(usage_json)
        except Exception:  # noqa: BLE001
            continue
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

        created_day = _extract_iso_day(row["created_at"])
        if created_day is not None and trend_start <= created_day <= today:
            bucket = trend_map[created_day.isoformat()]
            bucket["tasks_with_usage"] = int(bucket["tasks_with_usage"]) + 1
            bucket["total_tokens"] = int(bucket["total_tokens"]) + total_tokens_int
            bucket["cost_estimate"] = float(bucket["cost_estimate"]) + cost_value

        sid = str(row["session_id"])
        bucket = session_map.get(sid)
        if bucket is None:
            bucket = {
                "session_id": sid,
                "session_title": row["session_title"],
                "tasks_with_usage": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "last_task_at": row["updated_at"],
            }
            session_map[sid] = bucket
        bucket["tasks_with_usage"] = int(bucket["tasks_with_usage"]) + 1
        bucket["total_tokens"] = int(bucket["total_tokens"]) + total_tokens_int
        bucket["cost_estimate"] = float(bucket["cost_estimate"]) + cost_value
        last_task_at = bucket.get("last_task_at")
        if isinstance(row["updated_at"], str) and (
            not isinstance(last_task_at, str) or row["updated_at"] > last_task_at
        ):
            bucket["last_task_at"] = row["updated_at"]

        top_task_rows.append(
            {
                "task_id": str(row["id"]),
                "session_id": sid,
                "session_title": row["session_title"],
                "prompt_excerpt": _excerpt_prompt(row["prompt"]),
                "total_tokens": total_tokens_int,
                "cost_estimate": cost_value,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
        )

    total_tokens = prompt_sum + completion_sum
    avg_total_tokens = total_tokens / token_task_count if token_task_count > 0 else None
    avg_cost_estimate = cost_sum / cost_task_count if cost_task_count > 0 else None

    trend = [
        {
            "day": day,
            "tasks_with_usage": int(item["tasks_with_usage"]),
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
