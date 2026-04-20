from __future__ import annotations

import argparse
import json
import secrets
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class HttpResult:
    status: int
    text: str
    json_body: Any | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run InsightAgent main-path e2e checks: "
            "auth -> settings validate/save -> task stream/trace -> RAG ingest/query -> exports."
        ),
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--password",
        default="MainPathPwd#2026",
        help="Password used for auto-generated e2e users.",
    )
    parser.add_argument(
        "--stream-timeout",
        type=float,
        default=60.0,
        help="Timeout seconds for task SSE stream (default: 60).",
    )
    return parser.parse_args()


def _request(
    *,
    method: str,
    url: str,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    accept: str | None = None,
    timeout_sec: float = 20.0,
) -> HttpResult:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if accept:
        headers["Accept"] = accept
    body: bytes | None = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")

    req = Request(url=url, method=method, data=body, headers=headers)
    try:
        with urlopen(req, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8", errors="replace")
            parsed: Any | None = None
            try:
                parsed = json.loads(raw) if raw.strip() else None
            except json.JSONDecodeError:
                parsed = None
            return HttpResult(status=int(response.status), text=raw, json_body=parsed)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed: Any | None = None
        try:
            parsed = json.loads(raw) if raw.strip() else None
        except json.JSONDecodeError:
            parsed = None
        return HttpResult(status=int(exc.code), text=raw, json_body=parsed)
    except URLError as exc:
        raise RuntimeError(f"request failed (network): {method} {url}: {exc}") from exc


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _register(base_url: str, email: str, password: str) -> dict[str, Any]:
    res = _request(
        method="POST",
        url=f"{base_url}/api/auth/register",
        payload={"email": email, "password": password},
    )
    _assert(res.status == 200, f"register failed ({email}): {res.status} {res.text}")
    _assert(isinstance(res.json_body, dict), "register response must be json object")
    return res.json_body


def _extract_sse_event_names(raw: str) -> list[str]:
    names: list[str] = []
    for line in raw.splitlines():
        if line.startswith("event:"):
            names.append(line[6:].strip())
    return names


def _extract_sse_error_codes(raw: str) -> list[str]:
    lines = raw.splitlines()
    codes: list[str] = []
    last_event: str | None = None
    for line in lines:
        if line.startswith("event:"):
            last_event = line[6:].strip()
            continue
        if last_event != "error":
            continue
        if not line.startswith("data:"):
            continue
        payload_raw = line[5:].strip()
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            code = payload.get("code")
            if isinstance(code, str) and code.strip():
                codes.append(code.strip())
    return codes


def _extract_sse_done_payload(raw: str) -> dict[str, Any] | None:
    lines = raw.splitlines()
    last_event: str | None = None
    done_payload: dict[str, Any] | None = None
    for line in lines:
        if line.startswith("event:"):
            last_event = line[6:].strip()
            continue
        if last_event != "done":
            continue
        if not line.startswith("data:"):
            continue
        payload_raw = line[5:].strip()
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            done_payload = payload
    return done_payload


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    password = str(args.password)

    suffix = secrets.token_hex(4)
    email = f"e2e_main_{suffix}@example.com"
    kb_id = f"kb-main-{suffix}"

    print("[1/7] 登录")
    register = _register(base_url, email, password)
    _assert("access_token" in register, "register missing access_token")
    access_token = str(register["access_token"])
    print("  - OK: register + access token")

    print("[2/7] 模型配置校验与保存（mock）")
    mock_payload = {
        "mode": "mock",
        "provider": "mock",
        "model": "mock-gpt",
        "base_url": None,
        "api_key": None,
    }
    validate_mock = _request(
        method="POST",
        url=f"{base_url}/api/settings/validate",
        token=access_token,
        payload=mock_payload,
    )
    _assert(
        validate_mock.status == 200,
        f"settings validate failed: {validate_mock.status} {validate_mock.text}",
    )
    _assert(
        isinstance(validate_mock.json_body, dict) and bool(validate_mock.json_body.get("ok")),
        f"settings validate should pass in mock mode: {validate_mock.text}",
    )
    save_mock = _request(
        method="PUT",
        url=f"{base_url}/api/settings",
        token=access_token,
        payload=mock_payload,
    )
    _assert(
        save_mock.status == 200,
        f"settings save failed: {save_mock.status} {save_mock.text}",
    )
    print("  - OK: validate + save mock mode")

    print("[3/7] 发送消息并校验任务流/Trace")
    create_task = _request(
        method="POST",
        url=f"{base_url}/api/tasks",
        token=access_token,
        payload={"user_input": "e2e main path task [calc:1+2*3]"},
    )
    _assert(
        create_task.status == 200 and isinstance(create_task.json_body, dict),
        f"create task failed: {create_task.status} {create_task.text}",
    )
    task_id = str(create_task.json_body["task_id"])
    session_id = str(create_task.json_body["session_id"])
    stream_task = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}/stream",
        token=access_token,
        accept="text/event-stream",
        timeout_sec=float(args.stream_timeout),
    )
    _assert(
        stream_task.status == 200,
        f"task stream failed: {stream_task.status} {stream_task.text}",
    )
    event_names = _extract_sse_event_names(stream_task.text)
    _assert("done" in event_names, "task stream missing done event")
    error_codes = _extract_sse_error_codes(stream_task.text)
    _assert(not error_codes, f"task stream has error events: {error_codes}")
    done_payload = _extract_sse_done_payload(stream_task.text)
    _assert(done_payload is not None, "task stream missing done payload body")
    usage_payload = done_payload.get("usage") if isinstance(done_payload, dict) else None
    _assert(isinstance(usage_payload, dict), "done payload missing usage object")
    prompt_tokens = usage_payload.get("prompt_tokens")
    completion_tokens = usage_payload.get("completion_tokens")
    _assert(
        isinstance(prompt_tokens, int | float) and float(prompt_tokens) >= 0,
        f"done usage prompt_tokens invalid: {usage_payload}",
    )
    _assert(
        isinstance(completion_tokens, int | float) and float(completion_tokens) >= 0,
        f"done usage completion_tokens invalid: {usage_payload}",
    )
    prompt_source = usage_payload.get("prompt_tokens_source")
    completion_source = usage_payload.get("completion_tokens_source")
    usage_source = usage_payload.get("usage_source")
    allowed_sources = {"provider", "estimated"}
    _assert(
        isinstance(prompt_source, str) and prompt_source in allowed_sources,
        f"prompt_tokens_source invalid: {usage_payload}",
    )
    _assert(
        isinstance(completion_source, str) and completion_source in allowed_sources,
        f"completion_tokens_source invalid: {usage_payload}",
    )
    _assert(
        isinstance(usage_source, str) and usage_source in allowed_sources,
        f"usage_source invalid: {usage_payload}",
    )

    trace = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}/trace",
        token=access_token,
    )
    _assert(trace.status == 200 and isinstance(trace.json_body, dict), "task trace read failed")
    trace_steps = trace.json_body.get("steps")
    _assert(isinstance(trace_steps, list) and len(trace_steps) > 0, "task trace should not be empty")

    trace_delta = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}/trace/delta?after_seq=0&limit=200",
        token=access_token,
    )
    _assert(
        trace_delta.status == 200 and isinstance(trace_delta.json_body, dict),
        "task trace delta read failed",
    )
    print("  - OK: task stream done + trace/trace-delta available")

    print("[4/7] RAG ingest/query")
    ingest = _request(
        method="POST",
        url=f"{base_url}/api/rag/ingest",
        token=access_token,
        payload={
            "knowledge_base_id": kb_id,
            "documents": [
                {
                    "text": "InsightAgent e2e main path document for retrieval checks.",
                    "source": "e2e_main_path",
                },
            ],
            "chunk_size": 180,
            "chunk_overlap": 40,
        },
    )
    _assert(
        ingest.status == 200 and isinstance(ingest.json_body, dict),
        f"rag ingest failed: {ingest.status} {ingest.text}",
    )
    query = _request(
        method="POST",
        url=f"{base_url}/api/rag/query",
        token=access_token,
        payload={
            "knowledge_base_id": kb_id,
            "query": "main path retrieval checks",
            "top_k": 3,
        },
    )
    _assert(
        query.status == 200 and isinstance(query.json_body, dict),
        f"rag query failed: {query.status} {query.text}",
    )
    hit_count = int(query.json_body.get("hit_count", 0) or 0)
    _assert(hit_count >= 1, f"rag query should return at least 1 hit, got {hit_count}")
    print("  - OK: rag ingest + rag query")

    print("[5/7] 任务导出（JSON/Markdown）")
    export_task_json = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}/export/json",
        token=access_token,
    )
    _assert(
        export_task_json.status == 200 and isinstance(export_task_json.json_body, dict),
        (
            "task export json failed: "
            f"status={export_task_json.status}, body={export_task_json.text[:300]}"
        ),
    )
    _assert(
        str(export_task_json.json_body.get("task", {}).get("id", "")) == task_id,
        "task export json task.id mismatch",
    )
    export_task_md = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}/export/markdown",
        token=access_token,
    )
    _assert(export_task_md.status == 200, "task export markdown failed")
    _assert(
        "InsightAgent Task Export" in export_task_md.text,
        "task export markdown missing header",
    )
    print("  - OK: task exports")

    print("[6/7] 会话导出（JSON/Markdown）")
    export_session_json = _request(
        method="GET",
        url=f"{base_url}/api/sessions/{session_id}/export/json",
        token=access_token,
    )
    _assert(
        export_session_json.status == 200 and isinstance(export_session_json.json_body, dict),
        (
            "session export json failed: "
            f"status={export_session_json.status}, body={export_session_json.text[:300]}"
        ),
    )
    _assert(
        str(export_session_json.json_body.get("session", {}).get("id", "")) == session_id,
        "session export json session.id mismatch",
    )
    export_session_md = _request(
        method="GET",
        url=f"{base_url}/api/sessions/{session_id}/export/markdown",
        token=access_token,
    )
    _assert(export_session_md.status == 200, "session export markdown failed")
    _assert(
        "InsightAgent Session Export" in export_session_md.text,
        "session export markdown missing header",
    )
    print("  - OK: session exports")

    print("[7/7] usage 汇总检查")
    usage_global = _request(
        method="GET",
        url=f"{base_url}/api/tasks/usage/summary",
        token=access_token,
    )
    _assert(usage_global.status == 200, "global usage summary failed")
    usage_session = _request(
        method="GET",
        url=f"{base_url}/api/sessions/{session_id}/usage/summary",
        token=access_token,
    )
    _assert(usage_session.status == 200, "session usage summary failed")
    _assert(isinstance(usage_global.json_body, dict), "global usage summary must be object")
    _assert(isinstance(usage_session.json_body, dict), "session usage summary must be object")
    for name, payload in (
        ("global", usage_global.json_body),
        ("session", usage_session.json_body),
    ):
        provider_count = payload.get("source_tasks_provider")
        estimated_count = payload.get("source_tasks_estimated")
        mixed_count = payload.get("source_tasks_mixed")
        legacy_count = payload.get("source_tasks_legacy")
        tasks_with_usage = payload.get("tasks_with_usage")
        _assert(
            isinstance(provider_count, int) and provider_count >= 0,
            f"{name} usage summary source_tasks_provider invalid: {payload}",
        )
        _assert(
            isinstance(estimated_count, int) and estimated_count >= 0,
            f"{name} usage summary source_tasks_estimated invalid: {payload}",
        )
        _assert(
            isinstance(mixed_count, int) and mixed_count >= 0,
            f"{name} usage summary source_tasks_mixed invalid: {payload}",
        )
        _assert(
            isinstance(legacy_count, int) and legacy_count >= 0,
            f"{name} usage summary source_tasks_legacy invalid: {payload}",
        )
        _assert(
            isinstance(tasks_with_usage, int) and tasks_with_usage >= 0,
            f"{name} usage summary tasks_with_usage invalid: {payload}",
        )
        _assert(
            provider_count + estimated_count + mixed_count + legacy_count == tasks_with_usage,
            f"{name} usage summary source counts mismatch: {payload}",
        )

    session_payload = usage_session.json_body
    session_provider = int(session_payload.get("source_tasks_provider", 0) or 0)
    session_estimated = int(session_payload.get("source_tasks_estimated", 0) or 0)
    session_mixed = int(session_payload.get("source_tasks_mixed", 0) or 0)
    session_legacy = int(session_payload.get("source_tasks_legacy", 0) or 0)
    selected_source = "provider"
    selected_count = session_provider
    if selected_count <= 0 and session_estimated > 0:
        selected_source = "estimated"
        selected_count = session_estimated
    if selected_count <= 0 and session_mixed > 0:
        selected_source = "mixed"
        selected_count = session_mixed
    if selected_count <= 0 and session_legacy > 0:
        selected_source = "legacy"
        selected_count = session_legacy
    _assert(
        selected_count > 0,
        f"session usage summary has no source counts to validate: {session_payload}",
    )

    usage_dashboard_filtered = _request(
        method="GET",
        url=(
            f"{base_url}/api/tasks/usage/dashboard?source_kind={selected_source}"
            f"&session_id={session_id}"
        ),
        token=access_token,
    )
    _assert(
        usage_dashboard_filtered.status == 200,
        f"usage dashboard {selected_source} filter failed",
    )
    _assert(
        isinstance(usage_dashboard_filtered.json_body, dict),
        f"usage dashboard {selected_source} payload must be object",
    )
    dashboard_summary = usage_dashboard_filtered.json_body.get("summary")
    _assert(
        isinstance(dashboard_summary, dict),
        f"usage dashboard {selected_source} summary missing",
    )
    filtered_tasks_with_usage = dashboard_summary.get("tasks_with_usage")
    _assert(
        isinstance(filtered_tasks_with_usage, int) and filtered_tasks_with_usage >= 1,
        f"usage dashboard {selected_source} should include at least one task: {dashboard_summary}",
    )
    key_map = {
        "provider": "source_tasks_provider",
        "estimated": "source_tasks_estimated",
        "mixed": "source_tasks_mixed",
        "legacy": "source_tasks_legacy",
    }
    selected_key = key_map[selected_source]
    selected_count_filtered = int(dashboard_summary.get(selected_key, 0) or 0)
    _assert(
        selected_count_filtered == filtered_tasks_with_usage,
        (
            f"usage dashboard {selected_source} filter mismatch: "
            f"summary={dashboard_summary}"
        ),
    )
    for key in (
        "source_tasks_provider",
        "source_tasks_estimated",
        "source_tasks_mixed",
        "source_tasks_legacy",
    ):
        if key == selected_key:
            continue
        _assert(
            int(dashboard_summary.get(key, 0) or 0) == 0,
            (
                f"usage dashboard {selected_source} filter should exclude {key}: "
                f"summary={dashboard_summary}"
            ),
        )
    _assert(
        dashboard_summary.get("tasks_total") == session_payload.get("tasks_total"),
        (
                f"usage dashboard {selected_source} should keep same tasks_total "
            f"within session scope: summary={dashboard_summary}, session={session_payload}"
        ),
    )
    dashboard_trend = usage_dashboard_filtered.json_body.get("trend")
    _assert(
        isinstance(dashboard_trend, list),
        f"usage dashboard {selected_source} trend missing",
    )
    for point in dashboard_trend:
        _assert(
            isinstance(point, dict),
            f"usage dashboard {selected_source} trend point invalid: {point}",
        )
        day_tasks_with_usage = point.get("tasks_with_usage")
        _assert(
            isinstance(day_tasks_with_usage, int) and day_tasks_with_usage >= 0,
            (
                f"usage dashboard {selected_source} trend tasks_with_usage invalid: "
                f"{point}"
            ),
        )
        day_source_sum = 0
        for key in (
            "source_tasks_provider",
            "source_tasks_estimated",
            "source_tasks_mixed",
            "source_tasks_legacy",
        ):
            value = point.get(key)
            _assert(
                isinstance(value, int) and value >= 0,
                (
                    f"usage dashboard {selected_source} trend {key} invalid: "
                    f"{point}"
                ),
            )
            day_source_sum += value
        _assert(
            day_source_sum == day_tasks_with_usage,
            (
                f"usage dashboard {selected_source} trend source sum mismatch: "
                f"{point}"
            ),
        )
        _assert(
            int(point.get(selected_key, 0) or 0) == day_tasks_with_usage,
            (
                f"usage dashboard {selected_source} trend selected source mismatch: "
                f"{point}"
            ),
        )
        for key in (
            "source_tasks_provider",
            "source_tasks_estimated",
            "source_tasks_mixed",
            "source_tasks_legacy",
        ):
            if key == selected_key:
                continue
            _assert(
                int(point.get(key, 0) or 0) == 0,
                (
                    f"usage dashboard {selected_source} trend should exclude {key}: "
                    f"{point}"
                ),
            )
    print("  - OK: usage summaries")

    print("")
    print("E2E main path passed:")
    print("- auth register")
    print("- settings validate/save (mock)")
    print("- task stream + trace + delta")
    print("- rag ingest/query")
    print("- task export json/markdown")
    print("- session export json/markdown")
    print("- usage summaries")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"E2E main path failed: {exc}", file=sys.stderr)
        raise
