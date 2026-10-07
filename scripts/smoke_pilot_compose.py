#!/usr/bin/env python3
"""Disposable pilot Compose fixture: mock tasks and persistence across container recreation."""

import argparse
import json
from pathlib import Path
import secrets
import signal
import tempfile
from urllib.parse import quote

from check_pilot_deploy_config import IMAGE_FIELDS
from pilot_compose import check_compose_config, compose
from pilot_task_smoke import check_task_contracts, require
from smoke_pilot_images import (check_browser_api, check_cors, check_frontend, docker,
                               host_port, read_stream, request_json, request_text, wait_until)


def fixture_config():
    password = secrets.token_urlsafe(36)
    return {
        "INSIGHT_AGENT_ENV": "production", "INSIGHT_AGENT_MODE": "remote",
        "INSIGHT_AGENT_PROVIDER": "openai", "INSIGHT_AGENT_MODEL": "fixture-unused",
        "INSIGHT_AGENT_BASE_URL": "https://provider.example.invalid/v1", "INSIGHT_AGENT_API_KEY": "fixture-unused",
        "PILOT_FRONTEND_URL": "https://pilot.example.test", "NEXT_PUBLIC_API_BASE_URL": "https://api.pilot.example.com",
        "PILOT_FRONTEND_BUILD_API_BASE_URL": "https://api.pilot.example.com",
        "INSIGHT_AGENT_CORS_ORIGINS": '["https://pilot.example.test"]',
        "INSIGHT_AGENT_JWT_SECRET": secrets.token_urlsafe(48), "INSIGHT_AGENT_SECRET_KEY": secrets.token_urlsafe(48),
        "PILOT_POSTGRES_USER": "pilot", "PILOT_POSTGRES_DB": "pilot", "PILOT_POSTGRES_PASSWORD": password,
        "INSIGHT_AGENT_DATABASE_URL": f"postgresql://pilot:{quote(password, safe='')}@postgres:5432/pilot",
        **{field: "fixture.invalid/image@sha256:" + "a" * 64 for field in IMAGE_FIELDS},
    }


def run(args):
    images = dict(zip(("backend", "frontend", "postgres", "chroma"),
                      (args.backend_image, args.frontend_image, args.postgres_image, args.chroma_image)))
    for image in images.values():
        docker("image", "inspect", image)
    project = "ia-pilot-compose-" + secrets.token_hex(6)
    values = fixture_config()
    require(not check_compose_config(values), "pilot_fixture_config_invalid")
    production = json.loads(compose(values, project, "config", "--format", "json"))
    services = production["services"]
    require(services["backend"]["environment"]["INSIGHT_AGENT_MODE"] == "remote", "pilot_production_remote_failed")
    require(all(not service.get("build") and not service.get("command") for service in services.values()), "pilot_immutable_images_failed")
    require(not services["frontend"].get("environment"), "pilot_frontend_secret_isolation_failed")
    require(all(volume["type"] == "volume" for service in services.values()
                for volume in service.get("volumes", [])), "pilot_source_mount_failed")
    # These overrides belong only to this isolated fixture. Production CLI rejects mock/port 0/tags.
    values.update(PILOT_BACKEND_PORT="0", PILOT_FRONTEND_PORT="0")
    with tempfile.TemporaryDirectory(prefix=project) as directory:
        override = Path(directory) / "fixture.json"
        override.write_text(json.dumps({"services": {
            service: {"image": image, **({"environment": {"INSIGHT_AGENT_MODE": "mock",
                       "INSIGHT_AGENT_PROVIDER": "mock", "TASK_TOOL_MAX_CONCURRENT": "2"}} if service == "backend" else {})}
            for service, image in images.items()
        }}))
        override.chmod(0o600)

        def command(*arguments):
            return compose(values, project, *arguments, extra_files=(override,))

        def ports():
            backend = command("ps", "-q", "backend").strip()
            frontend = command("ps", "-q", "frontend").strip()
            return f"http://127.0.0.1:{host_port(backend, 8000)}", host_port(frontend, 3001)

        try:
            resolved = json.loads(command("config", "--format", "json"))
            services = resolved["services"]
            require(not services["postgres"].get("ports") and not services["chroma"].get("ports"), "pilot_private_storage_ports_failed")
            require(all(port.get("host_ip") == "127.0.0.1" for service in ("backend", "frontend")
                        for port in services[service]["ports"]), "pilot_loopback_ports_failed")
            command("up", "-d", "--wait", "--wait-timeout", "120", "--pull", "never")
            base, frontend_port = ports()
            require(request_json(base + "/health").get("mode") == "mock", "pilot_fixture_mock_required")
            check_cors(base)
            check_frontend(frontend_port)
            check_browser_api(frontend_port, args.expected_api_base_url)
            credentials = {"email": project + "@example.test", "password": secrets.token_urlsafe(24)}
            token = request_json(base + "/api/auth/register", payload=credentials)["access_token"]
            session = request_json(base + "/api/sessions", payload={"title": "persistent fixture"}, token=token)
            created = []

            def api(url, **kwargs):
                result = request_json(url, **kwargs)
                if url.endswith("/api/tasks") and kwargs.get("payload") is not None:
                    created.append(result["task_id"])
                return result

            checks = check_task_contracts(base, token, request_json=api, request_text=request_text,
                                         read_stream=read_stream, wait_until=wait_until)
            source_path = f"/api/tasks/{created[0]}/export/json"
            before = request_json(base + source_path, token=token)
            command("down")  # Keep the two fixture volumes; recreate every container next.
            command("up", "-d", "--wait", "--wait-timeout", "120", "--pull", "never")
            base, _ = ports()
            require(request_json(base + "/health").get("mode") == "mock", "pilot_fixture_mock_required")
            token = request_json(base + "/api/auth/login", payload=credentials)["access_token"]
            require(request_json(base + f"/api/sessions/{session['id']}", token=token)["id"] == session["id"], "pilot_session_persistence_failed")
            after = request_json(base + source_path, token=token)
            require(all(after[field] == before[field] for field in ("task", "trace", "messages")), "pilot_task_persistence_failed")
            recall = request_json(base + "/api/rag/query", token=token,
                                  payload={"knowledge_base_id": "default", "query": "blue telescope", "top_k": 3})
            require(recall.get("hit_count") == 1, "pilot_chroma_persistence_failed")
        finally:
            command("down", "--volumes", "--remove-orphans")
            for resource in ("container", "volume", "network"):
                listing = docker(resource, "ls", "--filter", "label=com.docker.compose.project=" + project, "-q")
                require(not listing, "pilot_compose_cleanup_failed")
        print(json.dumps({"result": "PASS", "scope": "local_compose_mock_recreate",
                          "checks": checks, "persistent_login_session_task_rag": True}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--frontend-image", required=True)
    parser.add_argument("--expected-api-base-url", required=True)
    parser.add_argument("--postgres-image", default="postgres:16-alpine")
    parser.add_argument("--chroma-image", default="chromadb/chroma:latest")
    args = parser.parse_args()
    def terminate(*_):
        raise SystemExit(143)
    signal.signal(signal.SIGTERM, terminate)
    try:
        run(args)
        return 0
    except Exception:
        # Compose config/stdout, URLs, provider credentials and API payloads are never echoed.
        print(json.dumps({"result": "FAIL", "failed_checks": ["pilot_compose_smoke_failed"]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
