from __future__ import annotations

from typing import Any


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _normalize_non_empty_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _normalize_session_task_governance(
    governance: Any,
) -> dict[str, str | list[str]]:
    _assert(isinstance(governance, dict), f"session task governance must be dict: {governance}")
    profile = governance.get("profile")
    provider_source = governance.get("provider_source")
    allowed_tool_names = _normalize_non_empty_str_list(governance.get("allowed_tool_names"))
    allowed_tool_labels = _normalize_non_empty_str_list(governance.get("allowed_tool_labels"))
    _assert(
        isinstance(profile, str) and bool(profile.strip()),
        f"session task governance.profile missing: {governance}",
    )
    _assert(
        isinstance(provider_source, str) and bool(provider_source.strip()),
        f"session task governance.provider_source missing: {governance}",
    )
    _assert(
        isinstance(governance.get("allowed_tool_names"), list),
        f"session task governance.allowed_tool_names invalid: {governance}",
    )
    _assert(
        isinstance(governance.get("allowed_tool_labels"), list),
        f"session task governance.allowed_tool_labels invalid: {governance}",
    )
    _assert(
        bool(allowed_tool_names or allowed_tool_labels),
        f"session task governance should include at least one allowed tool: {governance}",
    )
    return {
        "profile": profile.strip(),
        "provider_source": provider_source.strip(),
        "allowed_tool_names": allowed_tool_names,
        "allowed_tool_labels": allowed_tool_labels,
    }


def _normalize_task_governance(governance: Any) -> dict[str, str | list[str]]:
    return _normalize_session_task_governance(governance)


def assert_task_export_governance_json(
    task_payload: dict[str, Any],
) -> dict[str, str | list[str]]:
    trace = task_payload.get("trace")
    _assert(isinstance(trace, dict), f"task export json missing trace: {task_payload}")
    governance = trace.get("governance")
    return _normalize_task_governance(governance)


def assert_task_export_governance_markdown(
    markdown: str,
    governance: dict[str, Any],
) -> None:
    _assert(bool(markdown.strip()), "task export markdown should not be empty")
    normalized = _normalize_task_governance(governance)
    _assert(
        f"- Tool Registry Profile: {normalized['profile']}" in markdown,
        "task export markdown governance profile missing",
    )
    _assert(
        f"- Tool Registry Source: {normalized['provider_source']}" in markdown,
        "task export markdown governance source missing",
    )
    _assert(
        "- Allowed Tools: " in markdown,
        "task export markdown governance allowed tools missing",
    )
    allowed_tools = list(normalized["allowed_tool_labels"]) or list(
        normalized["allowed_tool_names"]
    )
    for tool in allowed_tools:
        _assert(
            tool in markdown,
            f"task export markdown missing allowed tool '{tool}'",
        )


def assert_session_export_task_level_governance_json(
    session_payload: dict[str, Any],
) -> tuple[str, dict[str, str | list[str]]]:
    tasks = session_payload.get("tasks")
    _assert(isinstance(tasks, list), f"session export json missing tasks: {session_payload}")
    for item in tasks:
        _assert(isinstance(item, dict), f"session task item invalid: {item}")
        governance = item.get("governance")
        if governance is None:
            continue
        task_id = str(item.get("id", "")).strip()
        _assert(task_id, f"session task with governance missing id: {item}")
        return task_id, _normalize_session_task_governance(governance)
    raise RuntimeError(f"session export tasks missing task-level governance: {tasks}")


def assert_session_export_task_level_governance_markdown(
    markdown: str,
    governance: dict[str, Any],
) -> None:
    _assert(bool(markdown.strip()), "session export markdown should not be empty")
    normalized = _normalize_session_task_governance(governance)
    _assert(
        f"- Tool Registry Profile: {normalized['profile']}" in markdown,
        "session export markdown task-level governance profile missing",
    )
    _assert(
        f"- Tool Registry Source: {normalized['provider_source']}" in markdown,
        "session export markdown task-level governance source missing",
    )
    _assert(
        "- Allowed Tools: " in markdown,
        "session export markdown task-level governance allowed tools missing",
    )
    allowed_tools = list(normalized["allowed_tool_labels"]) or list(
        normalized["allowed_tool_names"]
    )
    for tool in allowed_tools:
        _assert(
            tool in markdown,
            f"session export markdown missing task-level allowed tool '{tool}'",
        )
