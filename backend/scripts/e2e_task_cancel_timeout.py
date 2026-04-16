from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Thread
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
            "Run InsightAgent cancel/timeout e2e checks. "
            "Timeout check expects backend TASK_TIMEOUT_SEC to be small (for example 1-3s)."
        ),
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--password",
        default="CancelTimeoutPwd#2026",
        help="Password used for auto-generated e2e users.",
    )
    parser.add_argument(
        "--stream-timeout",
        type=float,
        default=120.0,
        help="Timeout seconds for task SSE stream requests (default: 120).",
    )
    parser.add_argument(
        "--cancel-delay-sec",
        type=float,
        default=0.25,
        help="Delay between opening stream and issuing cancel request (default: 0.25).",
    )
    parser.add_argument(
        "--cancel-prompt-words",
        type=int,
        default=220000,
        help="Filler words used for cancel scenario prompt (default: 220000).",
    )
    parser.add_argument(
        "--timeout-prompt-words",
        type=int,
        default=300000,
        help="Filler words used for timeout scenario prompt (default: 300000).",
    )
    parser.add_argument(
        "--skip-timeout",
        action="store_true",
        help="Skip timeout scenario (useful when backend TASK_TIMEOUT_SEC is large).",
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


def _save_mock_settings(base_url: str, token: str) -> None:
    mock_payload = {
        "mode": "mock",
        "provider": "mock",
        "model": "mock-gpt",
        "base_url": None,
        "api_key": None,
    }
    validate = _request(
        method="POST",
        url=f"{base_url}/api/settings/validate",
        token=token,
        payload=mock_payload,
    )
    _assert(
        validate.status == 200
        and isinstance(validate.json_body, dict)
        and bool(validate.json_body.get("ok")),
        f"settings validate (mock) failed: {validate.status} {validate.text}",
    )
    save = _request(
        method="PUT",
        url=f"{base_url}/api/settings",
        token=token,
        payload=mock_payload,
    )
    _assert(
        save.status == 200,
        f"settings save (mock) failed: {save.status} {save.text}",
    )


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


def _long_prompt(prefix: str, words: int) -> str:
    safe_words = max(1, int(words))
    return f"{prefix} " + ("word " * safe_words).strip()


def _create_task(base_url: str, token: str, user_input: str) -> str:
    create_task = _request(
        method="POST",
        url=f"{base_url}/api/tasks",
        token=token,
        payload={"user_input": user_input},
        timeout_sec=60.0,
    )
    _assert(
        create_task.status == 200 and isinstance(create_task.json_body, dict),
        f"create task failed: {create_task.status} {create_task.text[:300]}",
    )
    task_id = str(create_task.json_body.get("task_id", "")).strip()
    _assert(bool(task_id), f"create task missing task_id: {create_task.text[:300]}")
    return task_id


def _get_task_status_normalized(base_url: str, token: str, task_id: str) -> str:
    detail = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}",
        token=token,
    )
    _assert(detail.status == 200 and isinstance(detail.json_body, dict), "task detail read failed")
    return str(detail.json_body.get("status_normalized", "")).strip().lower()


def _run_cancel_case(args: argparse.Namespace, base_url: str, token: str) -> None:
    print("[3/5] cancel 场景：流式中取消任务")
    cancel_task_id = _create_task(
        base_url,
        token,
        _long_prompt("cancel e2e case", int(args.cancel_prompt_words)),
    )

    queue: Queue[HttpResult | Exception] = Queue(maxsize=1)

    def _worker() -> None:
        try:
            stream_res = _request(
                method="GET",
                url=f"{base_url}/api/tasks/{cancel_task_id}/stream",
                token=token,
                accept="text/event-stream",
                timeout_sec=float(args.stream_timeout),
            )
            queue.put(stream_res)
        except Exception as exc:  # noqa: BLE001
            queue.put(exc)

    stream_thread = Thread(target=_worker, daemon=True)
    stream_thread.start()

    time.sleep(max(0.0, float(args.cancel_delay_sec)))
    cancel = _request(
        method="POST",
        url=f"{base_url}/api/tasks/{cancel_task_id}/cancel",
        token=token,
    )
    _assert(cancel.status == 200, f"cancel request failed: {cancel.status} {cancel.text}")
    _assert(isinstance(cancel.json_body, dict), "cancel response must be json object")
    cancel_status = str(cancel.json_body.get("status_normalized", "")).strip().lower()
    _assert(cancel_status == "cancelled", f"cancel status should be cancelled, got {cancel_status}")

    stream_thread.join(float(args.stream_timeout) + 10.0)
    _assert(not stream_thread.is_alive(), "cancel stream did not finish in expected time")
    try:
        worker_result = queue.get_nowait()
    except Empty as exc:
        raise RuntimeError("cancel stream result missing") from exc
    if isinstance(worker_result, Exception):
        raise worker_result
    stream_res = worker_result
    _assert(
        stream_res.status == 200,
        f"cancel stream failed: {stream_res.status} {stream_res.text[:300]}",
    )
    event_names = _extract_sse_event_names(stream_res.text)
    error_codes = _extract_sse_error_codes(stream_res.text)
    _assert("cancelled" in event_names, "cancel stream missing cancelled event")
    _assert("task_cancelled" in error_codes, f"cancel stream missing task_cancelled code: {error_codes}")
    _assert("done" not in event_names, "cancel stream should not emit done event")

    task_status = _get_task_status_normalized(base_url, token, cancel_task_id)
    _assert(task_status == "cancelled", f"task status should be cancelled, got {task_status}")

    cancel_again = _request(
        method="POST",
        url=f"{base_url}/api/tasks/{cancel_task_id}/cancel",
        token=token,
    )
    _assert(cancel_again.status == 200, "second cancel should succeed")
    _assert(
        isinstance(cancel_again.json_body, dict) and bool(cancel_again.json_body.get("already_terminal")),
        "second cancel should be already_terminal",
    )
    print("  - OK: cancel endpoint + cancelled SSE/error + terminal status")


def _run_timeout_case(args: argparse.Namespace, base_url: str, token: str) -> None:
    print("[4/5] timeout 场景：超时事件与状态")
    timeout_task_id = _create_task(
        base_url,
        token,
        _long_prompt("timeout e2e case", int(args.timeout_prompt_words)),
    )
    stream_timeout = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{timeout_task_id}/stream",
        token=token,
        accept="text/event-stream",
        timeout_sec=float(args.stream_timeout),
    )
    _assert(
        stream_timeout.status == 200,
        f"timeout stream failed: {stream_timeout.status} {stream_timeout.text[:300]}",
    )
    event_names = _extract_sse_event_names(stream_timeout.text)
    error_codes = _extract_sse_error_codes(stream_timeout.text)
    if "timeout" not in event_names:
        raise RuntimeError(
            "timeout scenario did not trigger. "
            "Please restart backend with a small TASK_TIMEOUT_SEC (suggest 1~3) "
            "or run this script with --skip-timeout."
        )
    _assert("task_timeout" in error_codes, f"timeout stream missing task_timeout code: {error_codes}")
    _assert("done" not in event_names, "timeout stream should not emit done event")

    task_status = _get_task_status_normalized(base_url, token, timeout_task_id)
    _assert(task_status == "timed_out", f"task status should be timed_out, got {task_status}")
    print("  - OK: timeout SSE/error + timed_out status")


def main() -> None:
    args = parse_args()
    base_url = str(args.base_url).rstrip("/")
    password = str(args.password)

    suffix = secrets.token_hex(4)
    email = f"e2e_cancel_timeout_{suffix}@example.com"

    print("[1/5] 登录")
    register = _register(base_url, email, password)
    _assert("access_token" in register, "register missing access_token")
    token = str(register["access_token"])
    print("  - OK: register + access token")

    print("[2/5] 模型配置切换到 mock")
    _save_mock_settings(base_url, token)
    print("  - OK: validate + save mock mode")

    _run_cancel_case(args, base_url, token)

    if bool(args.skip_timeout):
        print("[4/5] timeout 场景：已跳过（--skip-timeout）")
    else:
        _run_timeout_case(args, base_url, token)

    print("[5/5] 最终状态检查")
    me = _request(
        method="GET",
        url=f"{base_url}/api/auth/me",
        token=token,
    )
    _assert(me.status == 200, "auth/me should still be available")
    print("  - OK: auth context still valid")

    print("")
    print("E2E cancel-timeout passed:")
    print("- auth register")
    print("- settings validate/save (mock)")
    print("- cancel in stream + terminal status")
    if bool(args.skip_timeout):
        print("- timeout scenario skipped")
    else:
        print("- timeout stream + timed_out status")
    print("- auth context health")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"E2E cancel-timeout failed: {exc}", file=sys.stderr)
        raise
