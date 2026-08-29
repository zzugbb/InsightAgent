from __future__ import annotations


def bind_chat_persistence_usage_public_names(namespace: dict[str, object]) -> None:
    globals().update(namespace)


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


def _normalize_governance_provider_source_filter(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return _normalize_governance_filter(value)
    try:
        value = resolve_unique_tool_registry_provider_source_alias(
            settings=get_settings(),
            tool_registry_provider_source=value,
        )
    except Exception:
        pass
    return _normalize_governance_filter(value)


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
                "trace_preview": _sanitize_session_export_trace_preview_rows(
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
        "tasks": _sanitize_task_rows_trace_summary_rows(trace_summary.get("tasks")),
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
                    "preview": _sanitize_session_export_trace_preview_rows(
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
    task_summaries = _sanitize_session_export_payload_task_rows(
        export_summary.get("tasks")
    )
    stats_summary = _coerce_export_payload_block_to_dict(export_summary.get("stats"))
    export_message_rows = _coerce_export_payload_block_list_to_dicts(message_rows)
    message_summaries = [
        {
            "id": str(row.get("id", "")),
            "task_id": str(row.get("task_id", ""))
            if row.get("task_id") is not None
            else None,
            "role": str(row.get("role", "")),
            "content": _sanitize_export_message_content(row.get("content", "")),
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


def _trace_preview_title_implies_provider_or_hosted_tool(title: object) -> bool:
    if not isinstance(title, str):
        return False
    normalized = " ".join(title.strip().lower().replace("_", " ").split())
    if not normalized:
        return False
    label, _, descriptor = normalized.partition("[")
    label = label.strip()
    descriptor = descriptor.strip(" ]")
    if label.startswith(("provider ", "hosted ")):
        return True
    if "http json" in descriptor:
        return True
    return "provider " in descriptor or "hosted " in descriptor


def _sanitize_session_export_trace_preview_title(title: object) -> object:
    if not (
        isinstance(title, str)
        and _trace_preview_title_implies_provider_or_hosted_tool(title)
        and _trace_http_json_export_content_needs_sanitization(title)
    ):
        return title
    return _redact_trace_http_json_export_content_fallback(title)


def _sanitize_session_export_trace_preview_rows(raw_preview: object) -> list[dict[str, object]]:
    rows = _coerce_export_payload_block_list_to_dicts(raw_preview)
    sanitized_rows: list[dict[str, object]] = []
    for row in rows:
        sanitized_row = _normalize_trace_json_compatible_value(dict(row))
        if not isinstance(sanitized_row, dict):
            continue
        title = sanitized_row.get("title")
        excerpt = sanitized_row.get("content_excerpt")
        sanitized_title = _sanitize_session_export_trace_preview_title(title)
        if sanitized_title is not title:
            sanitized_row["title"] = sanitized_title
        if (
            _trace_preview_title_implies_provider_or_hosted_tool(title)
            and isinstance(excerpt, str)
            and _trace_http_json_export_content_needs_sanitization(excerpt)
        ):
            sanitized_row["content_excerpt"] = _redact_trace_http_json_export_content_fallback(
                excerpt
            )
        sanitized_rows.append(sanitized_row)
    return sanitized_rows


def _get_session_export_task_response_summary_from_payload_row(
    row: dict[str, object],
    *,
    provider_source_aliases: dict[str, str] | None = None,
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
            "trace_preview": _sanitize_session_export_trace_preview_rows(
                row.get("trace_preview")
            ),
            "governance": _normalize_task_governance_payload_for_response(
                row.get("governance"),
                provider_source_aliases=provider_source_aliases,
            ),
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
        "trace_preview": _sanitize_session_export_trace_preview_rows(
            trace_summary.get("preview")
        ),
        "governance": _normalize_task_governance_payload_for_response(
            trace_summary.get("governance"),
            provider_source_aliases=provider_source_aliases,
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
    provider_source_aliases = build_session_export_provider_source_aliases(
        payload_summary
    )
    task_summaries: list[dict[str, object]] = []
    for row in payload_summary.get("tasks", []):
        row_summary = _coerce_export_payload_block_to_dict(row)
        if not row_summary:
            continue
        task_summaries.append(
            _get_session_export_task_response_summary_from_payload_row(
                row_summary,
                provider_source_aliases=provider_source_aliases,
            )
        )
    stats_summary = _coerce_export_payload_block_to_dict(payload_summary.get("stats"))
    response_summary = {
        "usage_summary": payload_summary.get("usage_summary"),
        "tasks": task_summaries,
        "stats": {
            "task_count": int(stats_summary.get("task_count", len(task_summaries)) or 0),
            "message_count": int(stats_summary.get("message_count", 0) or 0),
            "trace_step_count": int(stats_summary.get("trace_step_count", 0) or 0),
            "rag_hit_count": int(stats_summary.get("rag_hit_count", 0) or 0),
        },
        "governance": _normalize_session_governance_payload_for_response(
            payload_summary.get("governance"),
            provider_source_aliases=provider_source_aliases,
        ),
        "messages": _sanitize_export_message_rows(payload_summary.get("messages", [])),
    }
    sanitized_response_summary = sanitize_session_export_governance_provider_source_values(
        response_summary
    )
    return (
        sanitized_response_summary
        if isinstance(sanitized_response_summary, dict)
        else response_summary
    )


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
    safe_provider_source_filter = _normalize_governance_provider_source_filter(
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
                    t.status,
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
                    t.status,
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

        top_task_row = {
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
        }
        failure_insight = _extract_task_failure_insight_from_trace_json(
            status=task_row.get("status"),
            trace_json=task_row.get("trace_json"),
        )
        if failure_insight is not None:
            top_task_row.update(failure_insight)
        top_task_rows.append(top_task_row)

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
    trend_rows = _normalize_export_payload_block_list_to_dicts(payload.get("trend"))
    session_rows = _normalize_export_payload_block_list_to_dicts(
        payload.get("by_session")
    )
    top_task_rows = _normalize_export_payload_block_list_to_dicts(
        payload.get("top_tasks")
    )
    provider_source_aliases = _build_usage_dashboard_provider_source_aliases(
        session_rows=session_rows,
        top_task_rows=top_task_rows,
    )
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
                "governance": _normalize_session_governance_payload_for_response(
                    row.get("governance"),
                    provider_source_aliases=provider_source_aliases,
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
                **(
                    {
                        "failure_hint": failure_hint,
                        "failure_source": failure_source,
                    }
                    if (failure_hint := _normalize_task_failure_hint(row.get("failure_hint")))
                    and (
                        failure_source := _normalize_task_failure_source(
                            row.get("failure_source")
                        )
                    )
                    else {}
                ),
                "governance": _sanitize_task_governance_provider_source_values_for_export(
                    _normalize_task_governance_payload_or_original(
                        row.get("governance")
                    ),
                    provider_source_aliases=provider_source_aliases,
                ),
            }
            for row in top_task_rows
        ],
    }

_CHAT_PERSISTENCE_USAGE_EXPORTS = (
    'get_tasks_usage_summary',
    'get_session_usage_summary',
    '_parse_usage_float',
    '_parse_usage_source',
    '_classify_usage_source',
    '_extract_iso_day',
    '_excerpt_prompt',
    '_normalize_governance_filter',
    '_normalize_governance_provider_source_filter',
    '_task_governance_matches_filters',
    '_merge_session_governance_summary',
    'get_task_rows_governance_summary',
    'get_task_rows_trace_preview_summary',
    'get_task_rows_export_summary',
    'get_task_rows_session_export_summary',
    'get_session_export_payload_summary',
    '_trace_preview_title_implies_provider_or_hosted_tool',
    '_sanitize_session_export_trace_preview_title',
    '_sanitize_session_export_trace_preview_rows',
    '_get_session_export_task_response_summary_from_payload_row',
    'get_session_export_response_summary',
    'get_tasks_usage_dashboard',
    'get_tasks_usage_dashboard_response_summary',
)
