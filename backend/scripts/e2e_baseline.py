from __future__ import annotations

import argparse
import json
import secrets
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@dataclass
class HttpResult:
    status: int
    text: str
    json_body: Any | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run minimal auth/task e2e baseline against a running InsightAgent backend.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--password",
        default="BaselinePwd#2026",
        help="Password used for auto-generated e2e users.",
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


def _login(base_url: str, email: str, password: str) -> dict[str, Any]:
    res = _request(
        method="POST",
        url=f"{base_url}/api/auth/login",
        payload={"email": email, "password": password},
    )
    _assert(res.status == 200, f"login failed ({email}): {res.status} {res.text}")
    _assert(isinstance(res.json_body, dict), "login response must be json object")
    return res.json_body


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    suffix = secrets.token_hex(4)
    user_a_email = f"e2e_user_a_{suffix}@example.com"
    user_b_email = f"e2e_user_b_{suffix}@example.com"
    password = str(args.password)

    print("[1/5] 登录（register/login）基线")
    register_a = _register(base_url, user_a_email, password)
    register_b = _register(base_url, user_b_email, password)
    _assert("access_token" in register_a, "register_a missing access_token")
    _assert("refresh_token" in register_a, "register_a missing refresh_token")
    _assert("access_token" in register_b, "register_b missing access_token")
    login_a = _login(base_url, user_a_email, password)
    access_a = str(login_a["access_token"])
    refresh_a = str(login_a["refresh_token"])
    print("  - OK: register/login")

    print("[2/5] 过期（无效 access）与 refresh 轮换基线")
    expired_like = _request(
        method="GET",
        url=f"{base_url}/api/auth/me",
        token="expired.invalid.token",
    )
    _assert(expired_like.status == 401, f"invalid access should be 401, got {expired_like.status}")
    refreshed = _request(
        method="POST",
        url=f"{base_url}/api/auth/refresh",
        payload={"refresh_token": refresh_a},
    )
    _assert(refreshed.status == 200, f"refresh failed: {refreshed.status} {refreshed.text}")
    _assert(isinstance(refreshed.json_body, dict), "refresh response must be json object")
    access_a = str(refreshed.json_body["access_token"])
    refresh_a = str(refreshed.json_body["refresh_token"])
    print("  - OK: invalid access blocked + refresh rotated")

    print("[3/5] 发送流（create task + stream done）基线")
    create_task = _request(
        method="POST",
        url=f"{base_url}/api/tasks",
        token=access_a,
        payload={"user_input": "e2e baseline: stream check"},
    )
    _assert(create_task.status == 200, f"create task failed: {create_task.status} {create_task.text}")
    _assert(isinstance(create_task.json_body, dict), "task create response must be json object")
    task_id = str(create_task.json_body["task_id"])
    session_id = str(create_task.json_body["session_id"])
    stream_res = _request(
        method="GET",
        url=f"{base_url}/api/tasks/{task_id}/stream",
        token=access_a,
        accept="text/event-stream",
        timeout_sec=45.0,
    )
    _assert(stream_res.status == 200, f"task stream failed: {stream_res.status} {stream_res.text}")
    _assert("event: done" in stream_res.text, "task stream missing done event")
    print("  - OK: task stream completed")

    print("[4/5] 跨账号隔离基线")
    login_b = _login(base_url, user_b_email, password)
    access_b = str(login_b["access_token"])
    cross_read = _request(
        method="GET",
        url=f"{base_url}/api/sessions/{session_id}/messages",
        token=access_b,
    )
    _assert(
        cross_read.status == 404,
        f"cross-account read should be 404, got {cross_read.status} {cross_read.text}",
    )
    print("  - OK: account B cannot read account A session")

    print("[5/5] 登出基线（logout + refresh invalid）")
    logout = _request(
        method="POST",
        url=f"{base_url}/api/auth/logout",
        token=access_a,
        payload={"refresh_token": refresh_a},
    )
    _assert(logout.status == 200, f"logout failed: {logout.status} {logout.text}")
    refresh_after_logout = _request(
        method="POST",
        url=f"{base_url}/api/auth/refresh",
        payload={"refresh_token": refresh_a},
    )
    _assert(
        refresh_after_logout.status == 401,
        f"refresh after logout should be 401, got {refresh_after_logout.status}",
    )
    print("  - OK: logout revoked refresh token")

    print("")
    print("E2E baseline passed:")
    print("- login")
    print("- expiration-like access rejection + refresh")
    print("- send stream")
    print("- cross-account isolation")
    print("- logout")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"E2E baseline failed: {exc}", file=sys.stderr)
        raise
