#!/usr/bin/env python3
"""Export a single acceptance session to a low-sensitivity evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REDACT_KEYS = {"authorization", "api_key", "password", "secret", "token"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def sanitize_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, val in obj.items():
            lower = str(key).lower()
            if lower in REDACT_KEYS:
                out[key] = "[redacted]"
            elif lower in {"content", "prompt", "user_input", "body"} and isinstance(val, str):
                out[key] = {"fingerprint": fingerprint(val), "length": len(val)}
            else:
                out[key] = sanitize_obj(val)
        return out
    if isinstance(obj, list):
        return [sanitize_obj(item) for item in obj]
    return obj


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export acceptance evidence for one session")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--task-id", action="append", default=[], help="Repeat to limit exported tasks")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.environ.get("INSIGHT_AGENT_ACCESS_TOKEN", "").strip()
    if not token:
        print("INSIGHT_AGENT_ACCESS_TOKEN is required", file=sys.stderr)
        return 2
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Bearer {token}"}
    base = args.api_base_url.rstrip("/")
    with httpx.Client(base_url=base, headers=headers, timeout=60.0) as client:
        session_resp = client.get(f"/api/sessions/{args.session_id}/export/json")
        if session_resp.status_code != 200:
            print(f"session export failed: {session_resp.status_code}", file=sys.stderr)
            return 1
        session_payload = session_resp.json()
        allowed_tasks = set(args.task_id) if args.task_id else None
        task_ids: list[str] = []
        for task in session_payload.get("tasks") or []:
            if isinstance(task, dict) and task.get("task_id"):
                tid = str(task["task_id"])
                if allowed_tasks is None or tid in allowed_tasks:
                    task_ids.append(tid)
        sanitized_session = sanitize_obj(session_payload)
        (out_dir / "session-export.sanitized.json").write_text(
            json.dumps(sanitized_session, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        manifest = {
            "generated_at": utc_now(),
            "session_id": args.session_id,
            "task_ids": task_ids,
            "files": ["session-export.sanitized.json", "manifest.json"],
        }
        for tid in task_ids:
            task_resp = client.get(f"/api/tasks/{tid}/export/json")
            if task_resp.status_code != 200:
                manifest.setdefault("errors", []).append({"task_id": tid, "status": task_resp.status_code})
                continue
            name = f"task-{tid}.sanitized.json"
            (out_dir / name).write_text(
                json.dumps(sanitize_obj(task_resp.json()), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            manifest["files"].append(name)
        (out_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_dir / "README.txt").write_text(
            "Low-sensitivity acceptance evidence. No secrets or message bodies.\n",
            encoding="utf-8",
        )
    print(json.dumps({"output_dir": str(out_dir), "task_count": len(task_ids)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
