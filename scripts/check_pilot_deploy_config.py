#!/usr/bin/env python3
"""Check a proposed pilot deployment environment without exposing secret values."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

IMAGE_FIELDS = (
    "PILOT_BACKEND_IMAGE", "PILOT_FRONTEND_IMAGE",
    "PILOT_CHROMA_IMAGE", "PILOT_POSTGRES_IMAGE",
)
IMAGE_DIGEST = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
DEFAULT_SECRET = "change-me-in-production"


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("invalid deployment env line")
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or key in values:
            raise ValueError("invalid or duplicate deployment env key")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def _https_origin(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https" or not host or parsed.username or parsed.password
        or parsed.query or parsed.fragment
        or host in {"localhost", "127.0.0.1", "::1"}
    ):
        return None
    return f"https://{host.lower()}{f':{port}' if port else ''}"


def check_config(values: dict[str, str | None]) -> list[str]:
    failures: list[str] = []

    if (values.get("INSIGHT_AGENT_ENV") or "").strip().lower() != "production":
        failures.append("production_environment_required")

    frontend_url = (values.get("PILOT_FRONTEND_URL") or "").strip()
    api_url = (values.get("NEXT_PUBLIC_API_BASE_URL") or "").strip()
    build_api_url = (values.get("PILOT_FRONTEND_BUILD_API_BASE_URL") or "").strip()
    frontend_origin = _https_origin(frontend_url)
    if frontend_origin is None:
        failures.append("frontend_https_url_required")
    if _https_origin(api_url) is None:
        failures.append("api_https_url_required")
    if not build_api_url or build_api_url != api_url:
        failures.append("frontend_build_api_url_mismatch")

    try:
        cors_origins = json.loads(values.get("INSIGHT_AGENT_CORS_ORIGINS") or "")
    except json.JSONDecodeError:
        cors_origins = None
    if (
        not isinstance(cors_origins, list) or not cors_origins
        or any(not isinstance(item, str) or _https_origin(item) != item for item in cors_origins)
        or frontend_origin not in cors_origins
    ):
        failures.append("cors_origins_invalid")

    for key, code in (
        ("INSIGHT_AGENT_JWT_SECRET", "jwt_secret_invalid"),
        ("INSIGHT_AGENT_SECRET_KEY", "encryption_key_invalid"),
    ):
        value = values.get(key) or ""
        if len(value.strip()) < 32 or value.strip() == DEFAULT_SECRET:
            failures.append(code)
    jwt_secret = (values.get("INSIGHT_AGENT_JWT_SECRET") or "").strip()
    encryption_key = (values.get("INSIGHT_AGENT_SECRET_KEY") or "").strip()
    if jwt_secret and jwt_secret == encryption_key:
        failures.append("separate_secrets_required")

    database_url = (values.get("INSIGHT_AGENT_DATABASE_URL") or "").strip()
    try:
        database = urlsplit(database_url)
        database_valid = (
            database.scheme in {"postgresql", "postgres"}
            and bool(database.hostname)
            and database.hostname not in {"localhost", "127.0.0.1", "::1"}
            and bool(database.username)
            and bool(database.password)
            and unquote(database.password) != "insight"
            and bool(database.path.strip("/"))
        )
    except ValueError:
        database_valid = False
    if not database_valid:
        failures.append("database_credentials_invalid")

    for key in IMAGE_FIELDS:
        if not IMAGE_DIGEST.fullmatch((values.get(key) or "").strip()):
            failures.append(f"image_digest_required:{key}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True, type=Path)
    args = parser.parse_args()
    if not args.env_file.is_file():
        parser.error("deployment env file not found")
    try:
        values = read_env_file(args.env_file)
    except (OSError, UnicodeError, ValueError):
        print(json.dumps({"result": "FAIL", "failed_checks": ["env_file_invalid"]}))
        return 1
    failures = check_config(values)
    if failures:
        print(json.dumps({"result": "FAIL", "failed_checks": failures}, sort_keys=True))
        return 1
    print(json.dumps({"result": "PASS", "failed_checks": []}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
