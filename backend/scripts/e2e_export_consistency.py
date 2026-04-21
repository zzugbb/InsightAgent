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
    headers: dict[str, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run InsightAgent export consistency e2e checks: "
            "task/session export json+markdown consistency and download headers."
        ),
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--password",
        default="ExportCheckPwd#2026",
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
            return HttpResult(
                status=int(response.status),
                text=raw,
                json_body=parsed,
                headers={k.lower(): v for k, v in response.headers.items()},
            )
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed: Any | None = None
        try:
            parsed = json.loads(raw) if raw.strip() else None
        except json.JSONDecodeError:
            parsed = None
        return HttpResult(
            status=int(exc.code),
            text=raw,
            json_body=parsed,
            headers={k.lower(): v for k, v in exc.headers.items()},
        )
    except URLError as exc:
        raise RuntimeError(f"request failed (network): {method} {url}: {exc}") from exc


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _register(base_url: str, email: str, password: str) -> dict[str, Any]:
    response = _request(
        method="POST",
        url=f"{base_url}/api/auth/register",
        payload={"email": email, "password": password},
    )
    _assert(
        response.status == 200 and isinstance(response.json_body, dict),
        f"register failed: {response.status} {response.text}",
    )
    return response.json_body


def _extract_sse_event_names(raw: str) -> list[str]:
    names: list[str] = []
    for line in raw.splitlines():
        if line.startswith("event:"):
            names.append(line[6:].strip())
    return names


def _require_attachment_header(result: HttpResult, expected_ext: str) -> None:
    content_disposition = result.headers.get("content-disposition", "")
    _assert(
        "attachment;" in content_disposition.lower(),
        f"missing attachment Content-Disposition header: {result.headers}",
    )
    _assert(
        expected_ext.lower() in content_disposition.lower(),
        f"attachment filename should include {expected_ext}: {content_disposition}",
    )


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    password = str(args.password)

    suffix = secrets.token_hex(4)
    email = f"e2e_export_{suffix}@example.com"

    print("[1/5] 注册并保存 mock 设置")
    register = _register(base_url, email, password)
    access_token = str(register["access_token"])

    mock_payload = {
        "mode": "mock",
        "provider": "mock",
        "model": "mock-gpt",
        "base_url": None,
        "api_key": None,
    }
    save_mock = _request(
        method="PUT",
        url=f"{base_url}/api/settings",
        token=access_token,
        payload=mock_payload,
    )
    _assert(save_mock.status == 200, f"save mock settings failed: {save_mock.text}")
    print("  - OK: auth + settings")

    print("[2/5] 创建任务并跑完整流")
    create_task = _request(
        method="POST",
        url=f"{base_url}/api/tasks",
        token=access_token,
        payload={"user_input": "e2e export consistency [calc:12*8]"},
    )
    _assert(
        create_task.status == 200 and isinstance(create_task.json_body, dict),
        f"create task failed: {create_task.status} {create_task.text}",
    )
    task_id = str(create_task.json_body["task_id"])
    session_id = str(create_task.json_body["session_id"])

    stream = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}/stream",
        token=access_token,
        accept="text/event-stream",
        timeout_sec=float(args.stream_timeout),
    )
    _assert(stream.status == 200, f"task stream failed: {stream.status} {stream.text}")
    _assert("done" in _extract_sse_event_names(stream.text), "task stream missing done")
    print("  - OK: task stream done")

    print("[3/5] 任务导出一致性")
    task_export_json = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}/export/json",
        token=access_token,
    )
    _assert(
        task_export_json.status == 200 and isinstance(task_export_json.json_body, dict),
        f"task export json failed: {task_export_json.status} {task_export_json.text}",
    )
    task_payload = task_export_json.json_body
    task_obj = task_payload.get("task")
    trace_obj = task_payload.get("trace")
    messages = task_payload.get("messages")
    _assert(isinstance(task_obj, dict), "task export json missing task")
    _assert(isinstance(trace_obj, dict), "task export json missing trace")
    _assert(isinstance(messages, list), "task export json missing messages")
    _assert(str(task_obj.get("id", "")) == task_id, "task export task.id mismatch")
    _assert(str(task_obj.get("session_id", "")) == session_id, "task export session_id mismatch")

    trace_steps = trace_obj.get("steps")
    rag_chunks = trace_obj.get("rag_chunks")
    _assert(isinstance(trace_steps, list), "task export trace.steps must be list")
    _assert(isinstance(rag_chunks, list), "task export trace.rag_chunks must be list")
    _assert(
        int(trace_obj.get("step_count", -1)) == len(trace_steps),
        f"task export trace.step_count mismatch: {trace_obj}",
    )
    _assert(
        int(trace_obj.get("rag_hit_count", -1)) == len(rag_chunks),
        f"task export trace.rag_hit_count mismatch: {trace_obj}",
    )

    task_export_md = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}/export/markdown",
        token=access_token,
    )
    _assert(task_export_md.status == 200, "task export markdown failed")
    _assert("# InsightAgent Task Export" in task_export_md.text, "task export markdown header missing")
    _assert("## Trace Summary" in task_export_md.text, "task export markdown summary missing")
    _assert(
        f"- Step Count: {len(trace_steps)}" in task_export_md.text,
        "task export markdown step count mismatch",
    )

    task_export_json_download = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}/export/json?download=true",
        token=access_token,
    )
    _assert(task_export_json_download.status == 200, "task export json download failed")
    _require_attachment_header(task_export_json_download, ".json")

    task_export_md_download = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}/export/markdown?download=true",
        token=access_token,
    )
    _assert(task_export_md_download.status == 200, "task export markdown download failed")
    _require_attachment_header(task_export_md_download, ".md")
    print("  - OK: task export json/markdown consistency + download")

    print("[4/5] 会话导出一致性")
    session_export_json = _request(
        method="GET",
        url=f"{base_url}/api/sessions/{session_id}/export/json",
        token=access_token,
    )
    _assert(
        session_export_json.status == 200 and isinstance(session_export_json.json_body, dict),
        f"session export json failed: {session_export_json.status} {session_export_json.text}",
    )
    session_payload = session_export_json.json_body
    session_obj = session_payload.get("session")
    stats_obj = session_payload.get("stats")
    usage_summary_obj = session_payload.get("usage_summary")
    session_messages = session_payload.get("messages")
    session_tasks = session_payload.get("tasks")
    _assert(isinstance(session_obj, dict), "session export json missing session")
    _assert(isinstance(stats_obj, dict), "session export json missing stats")
    _assert(isinstance(usage_summary_obj, dict), "session export json missing usage_summary")
    _assert(isinstance(session_messages, list), "session export json missing messages")
    _assert(isinstance(session_tasks, list), "session export json missing tasks")
    _assert(str(session_obj.get("id", "")) == session_id, "session export session.id mismatch")

    task_count = len(session_tasks)
    message_count = len(session_messages)
    trace_step_total = 0
    rag_hit_total = 0
    for item in session_tasks:
        _assert(isinstance(item, dict), f"session task item invalid: {item}")
        trace_step_total += int(item.get("trace_step_count", 0) or 0)
        rag_hit_total += int(item.get("rag_hit_count", 0) or 0)
        preview = item.get("trace_preview")
        _assert(isinstance(preview, list), f"session task trace_preview invalid: {item}")
        _assert(len(preview) <= 3, f"trace_preview should be <= 3: {item}")

    _assert(
        int(stats_obj.get("task_count", -1)) == task_count,
        f"session export stats.task_count mismatch: {stats_obj}",
    )
    _assert(
        int(stats_obj.get("message_count", -1)) == message_count,
        f"session export stats.message_count mismatch: {stats_obj}",
    )
    _assert(
        int(stats_obj.get("trace_step_count", -1)) == trace_step_total,
        f"session export stats.trace_step_count mismatch: stats={stats_obj}, total={trace_step_total}",
    )
    _assert(
        int(stats_obj.get("rag_hit_count", -1)) == rag_hit_total,
        f"session export stats.rag_hit_count mismatch: stats={stats_obj}, total={rag_hit_total}",
    )
    _assert(
        int(usage_summary_obj.get("tasks_total", -1)) == task_count,
        f"session export usage_summary.tasks_total mismatch: usage={usage_summary_obj}, task_count={task_count}",
    )

    session_export_md = _request(
        method="GET",
        url=f"{base_url}/api/sessions/{session_id}/export/markdown",
        token=access_token,
    )
    _assert(session_export_md.status == 200, "session export markdown failed")
    _assert(
        "# InsightAgent Session Export" in session_export_md.text,
        "session export markdown header missing",
    )
    _assert("## Usage Summary" in session_export_md.text, "session export markdown usage summary missing")
    _assert("## Tasks" in session_export_md.text, "session export markdown tasks section missing")
    _assert(
        f"- Task Count: {task_count}" in session_export_md.text,
        "session export markdown task count mismatch",
    )

    session_export_json_download = _request(
        method="GET",
        url=f"{base_url}/api/sessions/{session_id}/export/json?download=true",
        token=access_token,
    )
    _assert(session_export_json_download.status == 200, "session export json download failed")
    _require_attachment_header(session_export_json_download, ".json")

    session_export_md_download = _request(
        method="GET",
        url=f"{base_url}/api/sessions/{session_id}/export/markdown?download=true",
        token=access_token,
    )
    _assert(session_export_md_download.status == 200, "session export markdown download failed")
    _require_attachment_header(session_export_md_download, ".md")
    print("  - OK: session export json/markdown consistency + download")

    print("[5/5] 负例：跨资源不存在检查")
    task_not_found = _request(
        method="GET",
        url=f"{base_url}/api/tasks/not-exists/export/json",
        token=access_token,
    )
    _assert(task_not_found.status == 404, "task not-found export should return 404")
    session_not_found = _request(
        method="GET",
        url=f"{base_url}/api/sessions/not-exists/export/json",
        token=access_token,
    )
    _assert(session_not_found.status == 404, "session not-found export should return 404")
    print("  - OK: not-found checks")

    print("")
    print("E2E export consistency passed:")
    print("- task export json/markdown schema and summary consistency")
    print("- session export json/markdown stats consistency")
    print("- download=true content-disposition headers")
    print("- export not-found responses")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"[e2e-export-consistency] FAILED: {exc}", file=sys.stderr)
        raise
