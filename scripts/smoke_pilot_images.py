#!/usr/bin/env python3
"""Smoke test local pilot images with disposable PostgreSQL and Chroma containers."""

from __future__ import annotations

import argparse
import json
import re
import secrets
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def docker(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=False,
    )
    if check and result.returncode:
        raise RuntimeError(f"docker {args[0]} failed (exit {result.returncode})")
    return result.stdout.strip()


def docker_exists(*args: str) -> bool:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=False,
    ).returncode == 0


def write_env(path: Path, values: dict[str, str]) -> None:
    path.touch(mode=0o600)
    path.chmod(0o600)
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()))


def host_port(container: str, port: int) -> int:
    template = '{{(index (index .NetworkSettings.Ports "' + str(port) + '/tcp") 0).HostPort}}'
    return int(docker("inspect", "--format", template, container))


def request_json(url: str, *, payload: dict | None = None, token: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urlopen(request, timeout=5) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise RuntimeError("unexpected JSON response")
    return value


def wait_until(label: str, probe, *, timeout: float = 75) -> dict | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = probe()
            if value:
                return value if isinstance(value, dict) else None
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError(f"{label} did not become ready")


def check_frontend(port: int) -> None:
    base = f"http://127.0.0.1:{port}"
    with urlopen(base, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError("frontend homepage failed")
        html = response.read().decode("utf-8")
    match = re.search(r'href="(/_next/static/[^\"]+\.css)"', html)
    if not match:
        raise RuntimeError("frontend stylesheet missing")
    with urlopen(base + match.group(1), timeout=5) as response:
        if response.status != 200 or "text/css" not in response.headers.get("Content-Type", ""):
            raise RuntimeError("frontend stylesheet failed")


def check_cors(base: str) -> None:
    for origin, allowed in (
        ("https://pilot.example.test", True),
        ("https://untrusted.example.test", False),
    ):
        request = Request(base + "/health", headers={"Origin": origin})
        with urlopen(request, timeout=5) as response:
            actual = response.headers.get("Access-Control-Allow-Origin")
        if (actual == origin) != allowed:
            raise RuntimeError("production CORS policy check failed")


def run_smoke(backend_image: str, frontend_image: str, postgres_image: str, chroma_image: str) -> None:
    for image in (backend_image, frontend_image, postgres_image, chroma_image):
        docker("image", "inspect", image)
    suffix = secrets.token_hex(5)
    network = f"ia-pilot-smoke-{suffix}"
    containers = [f"{network}-{service}" for service in ("postgres", "chroma", "backend", "frontend")]
    postgres, chroma, backend, frontend = containers
    password = secrets.token_urlsafe(36)
    created_network = False
    started: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ia-pilot-smoke-") as temp_dir:
        temp = Path(temp_dir)
        write_env(temp / "postgres.env", {
            "POSTGRES_USER": "pilot", "POSTGRES_PASSWORD": password, "POSTGRES_DB": "pilot",
        })
        write_env(temp / "backend.env", {
            "INSIGHT_AGENT_ENV": "production",
            "INSIGHT_AGENT_MODE": "mock",
            "INSIGHT_AGENT_PROVIDER": "mock",
            "INSIGHT_AGENT_DATABASE_URL": f"postgresql://pilot:{password}@postgres:5432/pilot",
            "INSIGHT_AGENT_CORS_ORIGINS": '["https://pilot.example.test"]',
            "INSIGHT_AGENT_JWT_SECRET": secrets.token_urlsafe(48),
            "INSIGHT_AGENT_SECRET_KEY": secrets.token_urlsafe(48),
            "CHROMA_HOST": "chroma", "CHROMA_PORT": "8000",
            "ANONYMIZED_TELEMETRY": "FALSE",
        })
        try:
            docker("network", "create", network)
            created_network = True
            docker("run", "--rm", "-d", "--name", postgres, "--network", network,
                   "--network-alias", "postgres", "--env-file", str(temp / "postgres.env"), postgres_image)
            started.append(postgres)
            wait_until("PostgreSQL", lambda: docker_exists(
                "exec", postgres, "pg_isready", "-U", "pilot", "-d", "pilot",
            ))
            docker("run", "--rm", "-d", "--name", chroma, "--network", network,
                   "--network-alias", "chroma", "-e", "IS_PERSISTENT=FALSE",
                   "-e", "ANONYMIZED_TELEMETRY=FALSE", chroma_image)
            started.append(chroma)
            docker("run", "--rm", "-d", "--name", backend, "--network", network,
                   "--env-file", str(temp / "backend.env"), "-p", "127.0.0.1::8000", backend_image)
            started.append(backend)
            backend_base = f"http://127.0.0.1:{host_port(backend, 8000)}"

            def backend_ready() -> dict | None:
                health = request_json(backend_base + "/health")
                if health.get("status") == "ok" and health.get("chroma", {}).get("reachable") is True:
                    return health
                return None

            health = wait_until("backend/Chroma", backend_ready)
            if not health or health.get("environment") != "production":
                raise RuntimeError("backend production environment check failed")
            if password in json.dumps(health):
                raise RuntimeError("backend health exposed database credentials")
            check_cors(backend_base)

            docker("run", "--rm", "-d", "--name", frontend, "--network", network,
                   "-p", "127.0.0.1::3001", frontend_image)
            started.append(frontend)
            frontend_port = host_port(frontend, 3001)
            wait_until("frontend", lambda: _frontend_ready(frontend_port))
            check_frontend(frontend_port)

            email = f"smoke-{suffix}@example.test"
            auth = request_json(backend_base + "/api/auth/register", payload={
                "email": email, "password": secrets.token_urlsafe(24),
            })
            token = auth.get("access_token")
            if not isinstance(token, str) or not token:
                raise RuntimeError("registration did not return access token")
            session = request_json(backend_base + "/api/sessions", payload={"title": "pilot smoke"}, token=token)
            session_id = session.get("id")
            if not isinstance(session_id, str) or not session_id:
                raise RuntimeError("session creation failed")
            fetched = request_json(backend_base + f"/api/sessions/{session_id}", token=token)
            if fetched.get("id") != session_id:
                raise RuntimeError("session readback failed")
            print("PASS: pilot images, production backend/CORS, PostgreSQL write/read, Chroma probe, frontend HTML/CSS")
        finally:
            for container in reversed(started):
                docker("rm", "-f", container, check=False)
            if created_network:
                docker("network", "rm", network, check=False)
            deadline = time.monotonic() + 10
            while True:
                remaining_containers = [
                    container for container in started if docker_exists("container", "inspect", container)
                ]
                remaining_network = created_network and docker_exists("network", "inspect", network)
                if not remaining_containers and not remaining_network:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "temporary Docker resources could not be removed "
                        f"(containers={len(remaining_containers)}, network={remaining_network})"
                    )
                time.sleep(0.2)


def _frontend_ready(port: int) -> bool:
    with urlopen(f"http://127.0.0.1:{port}", timeout=5) as response:
        return response.status == 200


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--frontend-image", required=True)
    parser.add_argument("--postgres-image", default="postgres:16-alpine")
    parser.add_argument("--chroma-image", default="chromadb/chroma:latest")
    args = parser.parse_args()
    def terminate(*_: object) -> None:
        raise SystemExit(143)

    signal.signal(signal.SIGTERM, terminate)
    try:
        run_smoke(args.backend_image, args.frontend_image, args.postgres_image, args.chroma_image)
    except (RuntimeError, subprocess.SubprocessError, HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
