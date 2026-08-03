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
            "Run InsightAgent queue/concurrency e2e checks. "
            "This expects backend TASK_QUEUE_MAX_CONCURRENT=1 so the second "
            "stream stays queued while the first stream holds the execution slot."
        ),
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--password",
        default="QueueConcurrencyPwd#2026",
        help="Password used for auto-generated e2e users.",
    )
    parser.add_argument(
        "--stream-timeout",
        type=float,
        default=90.0,
        help="Timeout seconds for task SSE stream requests (default: 90).",
    )
    parser.add_argument(
        "--queue-delay-sec",
        type=float,
        default=0.8,
        help="Delay after opening the queued stream before cancelling it.",
    )
    parser.add_argument(
        "--active-prompt-words",
        type=int,
        default=420,
        help="Filler words used to keep the active stream open.",
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
    _assert(save.status == 200, f"settings save (mock) failed: {save.status} {save.text}")


def assert_safe_queue_settings_diagnostics(
    diagnostics: dict[str, Any],
    *,
    expected_max_concurrent: int,
    expected_active_count: int | None = None,
    expected_waiting_count: int | None = None,
    expected_available_slots: int | None = None,
    expected_pressure_state: str | None = None,
) -> dict[str, Any]:
    _assert(
        isinstance(diagnostics, dict),
        f"settings summary missing task_queue_diagnostics: {diagnostics}",
    )
    _assert(
        diagnostics.get("max_concurrent") == expected_max_concurrent,
        (
            "queue phase settings diagnostics max_concurrent mismatch; "
            f"got {diagnostics}"
        ),
    )
    _assert(
        "active_task_ids" not in diagnostics,
        "task_queue_diagnostics leaked active_task_ids",
    )
    _assert(
        "waiting_task_ids" not in diagnostics,
        "task_queue_diagnostics leaked waiting_task_ids",
    )
    active_count = int(diagnostics.get("active_count") or 0)
    waiting_count = int(diagnostics.get("waiting_count") or 0)
    available_slots = int(diagnostics.get("available_slots") or 0)
    _assert(active_count >= 0, f"active_count should be non-negative: {diagnostics}")
    _assert(waiting_count >= 0, f"waiting_count should be non-negative: {diagnostics}")
    _assert(
        available_slots == max(0, expected_max_concurrent - active_count),
        f"available_slots should match max-active: {diagnostics}",
    )
    if expected_active_count is not None:
        _assert(
            active_count == expected_active_count,
            f"active_count should be {expected_active_count}: {diagnostics}",
        )
    if expected_waiting_count is not None:
        _assert(
            waiting_count == expected_waiting_count,
            f"waiting_count should be {expected_waiting_count}: {diagnostics}",
        )
    if expected_available_slots is not None:
        _assert(
            available_slots == expected_available_slots,
            f"available_slots should be {expected_available_slots}: {diagnostics}",
        )
    pressure_state = str(diagnostics.get("pressure_state") or "").strip()
    if expected_pressure_state is not None:
        _assert(
            pressure_state == expected_pressure_state,
            f"pressure_state should be {expected_pressure_state}: {diagnostics}",
        )
    per_user_limit = int(diagnostics.get("max_concurrent_per_user") or 0)
    per_session_limit = int(diagnostics.get("max_concurrent_per_session") or 0)
    if "current_user_available_slots" in diagnostics:
        current_user_available_slots = int(
            diagnostics.get("current_user_available_slots") or 0
        )
        current_user_active_count = int(
            diagnostics.get("current_user_active_count") or 0
        )
        _assert(
            current_user_available_slots >= 0,
            f"current_user_available_slots should be non-negative: {diagnostics}",
        )
        _assert(
            current_user_available_slots <= available_slots,
            (
                "current_user_available_slots should not exceed "
                f"available_slots: {diagnostics}"
            ),
        )
        if per_user_limit > 0:
            _assert(
                current_user_available_slots
                == min(
                    available_slots,
                    max(0, per_user_limit - current_user_active_count),
                ),
                (
                    "current_user_available_slots should match per-user "
                    f"limit-active and global capacity: {diagnostics}"
                ),
            )
    _assert(
        bool(diagnostics.get("per_user_limit_enabled")) == (per_user_limit > 0),
        f"per-user fairness flag does not match limit: {diagnostics}",
    )
    _assert(
        bool(diagnostics.get("per_session_limit_enabled")) == (per_session_limit > 0),
        f"per-session fairness flag does not match limit: {diagnostics}",
    )
    _assert(
        bool(diagnostics.get("fairness_limits_enabled"))
        == (per_user_limit > 0 or per_session_limit > 0),
        f"fairness aggregate flag does not match limits: {diagnostics}",
    )
    poll_interval_sec = float(diagnostics.get("poll_interval_sec") or 0)
    _assert(
        0 < poll_interval_sec <= 5,
        f"queue poll interval diagnostic should be positive: {diagnostics}",
    )
    _assert(
        diagnostics.get("waiting_policy") == "capacity_aware_oldest_eligible_fifo",
        f"queue waiting policy diagnostic mismatch: {diagnostics}",
    )
    _assert(
        bool(diagnostics.get("capacity_aware_fifo_enabled")),
        f"capacity-aware FIFO diagnostic should be enabled: {diagnostics}",
    )
    return diagnostics


def _assert_queue_settings_diagnostics(
    base_url: str,
    token: str,
    *,
    expected_active_count: int | None = None,
    expected_waiting_count: int | None = None,
    expected_available_slots: int | None = None,
    expected_pressure_state: str | None = None,
) -> None:
    settings = _request(
        method="GET",
        url=f"{base_url}/api/settings",
        token=token,
    )
    _assert(
        settings.status == 200 and isinstance(settings.json_body, dict),
        f"settings summary failed: {settings.status} {settings.text}",
    )
    diagnostics = settings.json_body.get("task_queue_diagnostics")
    assert_safe_queue_settings_diagnostics(
        diagnostics,
        expected_max_concurrent=1,
        expected_active_count=expected_active_count,
        expected_waiting_count=expected_waiting_count,
        expected_available_slots=expected_available_slots,
        expected_pressure_state=expected_pressure_state,
    )


def _long_prompt(prefix: str, words: int) -> str:
    safe_words = max(1, int(words))
    return f"{prefix} " + ("stream " * safe_words).strip()


def _create_task(base_url: str, token: str, user_input: str) -> str:
    create_task = _request(
        method="POST",
        url=f"{base_url}/api/tasks",
        token=token,
        payload={"user_input": user_input},
        timeout_sec=30.0,
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


def _wait_for_status(
    *,
    base_url: str,
    token: str,
    task_id: str,
    expected: set[str],
    timeout_sec: float,
    failure_hint: str,
) -> str:
    deadline = time.monotonic() + timeout_sec
    last_status = ""
    while time.monotonic() < deadline:
        last_status = _get_task_status_normalized(base_url, token, task_id)
        if last_status in expected:
            return last_status
        time.sleep(0.2)
    raise RuntimeError(f"{failure_hint}; last status={last_status or '(empty)'}")


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


def _extract_sse_state_payloads(raw: str) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    last_event: str | None = None
    for line in raw.splitlines():
        if line.startswith("event:"):
            last_event = line[6:].strip()
            continue
        if last_event != "state" or not line.startswith("data:"):
            continue
        try:
            payload = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            states.append(payload)
    return states


def assert_safe_queued_state_payload(
    queued_states: list[dict[str, Any]],
    *,
    task_id: str,
    expected_wait_position: int,
) -> dict[str, Any]:
    queued_state_payloads = [
        state
        for state in queued_states
        if state.get("phase") == "queued" and state.get("task_id") == task_id
    ]
    _assert(queued_state_payloads, "queued stream missing queued state payload")
    queue_payload = queued_state_payloads[0].get("queue")
    _assert(isinstance(queue_payload, dict), "queued state missing queue snapshot")
    _assert(
        queue_payload.get("wait_position") == expected_wait_position,
        (
            f"queued wait_position should be {expected_wait_position}: "
            f"{queue_payload}"
        ),
    )
    _assert(
        "active_task_ids" not in queue_payload,
        "queue snapshot leaked active_task_ids",
    )
    _assert(
        "waiting_task_ids" not in queue_payload,
        "queue snapshot leaked waiting_task_ids",
    )
    return queue_payload


def _start_stream_worker(
    *,
    base_url: str,
    token: str,
    task_id: str,
    timeout_sec: float,
) -> tuple[Thread, Queue[HttpResult | Exception]]:
    queue: Queue[HttpResult | Exception] = Queue(maxsize=1)

    def _worker() -> None:
        try:
            stream_res = _request(
                method="GET",
                url=f"{base_url}/api/tasks/{task_id}/stream",
                token=token,
                accept="text/event-stream",
                timeout_sec=timeout_sec,
            )
            queue.put(stream_res)
        except Exception as exc:  # noqa: BLE001
            queue.put(exc)

    thread = Thread(target=_worker, daemon=True)
    thread.start()
    return thread, queue


def _join_stream(
    thread: Thread,
    queue: Queue[HttpResult | Exception],
    *,
    timeout_sec: float,
    label: str,
) -> HttpResult:
    thread.join(timeout_sec + 10.0)
    _assert(not thread.is_alive(), f"{label} stream did not finish in expected time")
    try:
        worker_result = queue.get_nowait()
    except Empty as exc:
        raise RuntimeError(f"{label} stream result missing") from exc
    if isinstance(worker_result, Exception):
        raise worker_result
    _assert(
        worker_result.status == 200,
        f"{label} stream failed: {worker_result.status} {worker_result.text[:300]}",
    )
    return worker_result


def _run_queue_cancel_case(args: argparse.Namespace, base_url: str, token: str) -> None:
    print("[4/5] queue 场景：低并发下 queued 任务可取消并释放等待位")
    stream_timeout = float(args.stream_timeout)
    active_task_id = _create_task(
        base_url,
        token,
        _long_prompt(
            f"[mock-slow-ms=25] queue-active-{secrets.token_hex(3)}",
            int(args.active_prompt_words),
        ),
    )
    active_thread, active_queue = _start_stream_worker(
        base_url=base_url,
        token=token,
        task_id=active_task_id,
        timeout_sec=stream_timeout,
    )
    _wait_for_status(
        base_url=base_url,
        token=token,
        task_id=active_task_id,
        expected={"running"},
        timeout_sec=15.0,
        failure_hint="active task did not enter running before queue test",
    )

    queued_task_id = _create_task(
        base_url,
        token,
        f"queue-cancel-{secrets.token_hex(3)}",
    )
    queued_thread, queued_queue = _start_stream_worker(
        base_url=base_url,
        token=token,
        task_id=queued_task_id,
        timeout_sec=stream_timeout,
    )
    _wait_for_status(
        base_url=base_url,
        token=token,
        task_id=queued_task_id,
        expected={"queued"},
        timeout_sec=6.0,
        failure_hint=(
            "queued task did not stay queued. Restart backend with "
            "TASK_QUEUE_MAX_CONCURRENT=1 for this e2e phase"
        ),
    )
    _assert_queue_settings_diagnostics(
        base_url,
        token,
        expected_active_count=1,
        expected_waiting_count=1,
        expected_available_slots=0,
        expected_pressure_state="saturated",
    )
    time.sleep(max(0.0, float(args.queue_delay_sec)))

    cancel = _request(
        method="POST",
        url=f"{base_url}/api/tasks/{queued_task_id}/cancel",
        token=token,
    )
    _assert(cancel.status == 200, f"queued cancel failed: {cancel.status} {cancel.text}")
    _assert(isinstance(cancel.json_body, dict), "queued cancel response must be json object")
    cancel_status = str(cancel.json_body.get("status_normalized", "")).strip().lower()
    _assert(cancel_status == "cancelled", f"queued cancel status should be cancelled, got {cancel_status}")

    queued_stream = _join_stream(
        queued_thread,
        queued_queue,
        timeout_sec=stream_timeout,
        label="queued cancel",
    )
    queued_events = _extract_sse_event_names(queued_stream.text)
    queued_errors = _extract_sse_error_codes(queued_stream.text)
    queued_states = _extract_sse_state_payloads(queued_stream.text)
    assert_safe_queued_state_payload(
        queued_states,
        task_id=queued_task_id,
        expected_wait_position=1,
    )
    _assert("cancelled" in queued_events, "queued stream missing cancelled event")
    _assert("task_cancelled" in queued_errors, f"queued stream missing task_cancelled code: {queued_errors}")
    _assert("done" not in queued_events, "queued cancel stream should not emit done")

    queued_status = _get_task_status_normalized(base_url, token, queued_task_id)
    _assert(queued_status == "cancelled", f"queued task status should be cancelled, got {queued_status}")

    active_cancel = _request(
        method="POST",
        url=f"{base_url}/api/tasks/{active_task_id}/cancel",
        token=token,
    )
    _assert(active_cancel.status == 200, f"active cleanup cancel failed: {active_cancel.status}")
    _join_stream(
        active_thread,
        active_queue,
        timeout_sec=stream_timeout,
        label="active cleanup",
    )

    followup_task_id = _create_task(
        base_url,
        token,
        f"queue-followup-{secrets.token_hex(3)}",
    )
    followup = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{followup_task_id}/stream",
        token=token,
        accept="text/event-stream",
        timeout_sec=stream_timeout,
    )
    _assert(followup.status == 200, f"followup stream failed: {followup.status} {followup.text[:300]}")
    followup_events = _extract_sse_event_names(followup.text)
    _assert("done" in followup_events, "followup task should complete after queued cancel")
    print("  - OK: queued state + safe wait_position + cancel + followup completion")


def main() -> None:
    args = parse_args()
    base_url = str(args.base_url).rstrip("/")
    password = str(args.password)

    suffix = secrets.token_hex(4)
    email = f"e2e_queue_{suffix}@example.com"

    print("[1/5] 登录")
    register = _register(base_url, email, password)
    _assert("access_token" in register, "register missing access_token")
    token = str(register["access_token"])
    print("  - OK: register + access token")

    print("[2/5] 模型配置切换到 mock")
    _save_mock_settings(base_url, token)
    print("  - OK: validate + save mock mode")

    print("[3/5] settings 诊断暴露低并发队列配置")
    _assert_queue_settings_diagnostics(
        base_url,
        token,
        expected_active_count=0,
        expected_waiting_count=0,
        expected_available_slots=1,
        expected_pressure_state="idle",
    )
    print("  - OK: task_queue_diagnostics matches queue phase")

    _run_queue_cancel_case(args, base_url, token)

    print("[5/5] 最终状态检查")
    me = _request(
        method="GET",
        url=f"{base_url}/api/auth/me",
        token=token,
    )
    _assert(me.status == 200, "auth/me should still be available")
    print("  - OK: auth context still valid")

    print("")
    print("E2E queue-concurrency passed:")
    print("- auth register")
    print("- settings validate/save (mock)")
    print("- settings task_queue_diagnostics")
    print("- queued SSE wait_position + safe snapshot")
    print("- queued cancel + terminal status")
    print("- followup task completion after cancel cleanup")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"E2E queue-concurrency failed: {exc}", file=sys.stderr)
        sys.exit(1)
