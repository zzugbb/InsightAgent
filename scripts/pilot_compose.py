#!/usr/bin/env python3
"""Preflight and operate the single-host pilot without echoing resolved secrets."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

from check_pilot_deploy_config import check_config, read_env_file

ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


def check_compose_config(values):
    failures = check_config(values)
    try:
        database = urlsplit(values.get("INSIGHT_AGENT_DATABASE_URL", ""))
        matches = (database.hostname == "postgres" and database.port in {None, 5432}
                   and not database.query and not database.fragment
                   and unquote(database.username or "") == values.get("PILOT_POSTGRES_USER")
                   and unquote(database.password or "") == values.get("PILOT_POSTGRES_PASSWORD")
                   and unquote(database.path.lstrip("/")) == values.get("PILOT_POSTGRES_DB"))
    except ValueError:
        matches = False
    if not matches or any(not values.get(key) for key in (
        "PILOT_POSTGRES_USER", "PILOT_POSTGRES_PASSWORD", "PILOT_POSTGRES_DB",
    )):
        failures.append("compose_database_mismatch")
    if values.get("INSIGHT_AGENT_MODE") != "remote" or any(
        not values.get(key, "").strip() for key in (
            "INSIGHT_AGENT_PROVIDER", "INSIGHT_AGENT_MODEL", "INSIGHT_AGENT_BASE_URL", "INSIGHT_AGENT_API_KEY",
        )
    ) or values.get("INSIGHT_AGENT_PROVIDER", "").strip().lower() == "mock":
        failures.append("compose_remote_provider_required")
    try:
        remote = urlsplit(values.get("INSIGHT_AGENT_BASE_URL", ""))
        remote_valid = remote.scheme in {"http", "https"} and remote.hostname and not remote.username and not remote.password
        remote.port
    except ValueError:
        remote_valid = False
    if not remote_valid:
        failures.append("compose_provider_url_invalid")
    for key in ("PILOT_BACKEND_PORT", "PILOT_FRONTEND_PORT"):
        raw = values.get(key, "8000" if key == "PILOT_BACKEND_PORT" else "3001")
        if not raw.isascii() or not raw.isdigit() or not 1 <= int(raw) <= 65535:
            failures.append("compose_host_port_invalid:" + key)
    if values.get("PILOT_BACKEND_PORT", "8000") == values.get("PILOT_FRONTEND_PORT", "3001"):
        failures.append("compose_host_ports_conflict")
    return failures


def compose(values, project, *args, extra_files=()):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("PILOT_", "INSIGHT_AGENT_", "NEXT_PUBLIC_", "COMPOSE_"))}
    environment.update(values)
    # Explicit empty env-file prevents the repository's development .env from participating.
    command = ["docker", "compose", "--env-file", os.devnull, "-p", project, "-f", str(ROOT / "compose.pilot.yml")]
    for path in extra_files:
        command.extend(["-f", str(path)])
    result = subprocess.run([*command, *args], env=environment, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("pilot_compose_command_failed")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "up", "stop", "restart", "down"))
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--project", default="insightagent-pilot")
    args = parser.parse_args()
    try:
        if not PROJECT_NAME.fullmatch(args.project):
            raise RuntimeError("pilot_project_name_invalid")
        values = read_env_file(args.env_file)
        failures = check_compose_config(values)
        if failures:
            print(json.dumps({"result": "FAIL", "failed_checks": failures}, sort_keys=True))
            return 1
        compose(values, args.project, "config", "--quiet")
        actions = {"up": ("up", "-d", "--wait", "--wait-timeout", "120"),
                   "stop": ("stop",), "restart": ("restart",), "down": ("down",)}
        if args.action != "check":
            compose(values, args.project, *actions[args.action])
        print(json.dumps({"result": "PASS", "action": args.action}, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        print(json.dumps({"result": "FAIL", "failed_checks": ["pilot_compose_operation_failed"]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
