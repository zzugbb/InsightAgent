"""Shared isolated Docker PostgreSQL fixture for task integration scripts."""

import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.db import get_db_connection, initialize_database


def run_isolated_postgres(test_case, *, settings=None):
    name = f"insightagent-task-test-{uuid4().hex[:12]}"
    overrides = {"INSIGHT_AGENT_MODE": "mock", "INSIGHT_AGENT_PROVIDER": "mock",
                 "TASK_TOOL_MAX_CONCURRENT": "1", **(settings or {})}
    previous = {key: os.environ.get(key) for key in (*overrides, "INSIGHT_AGENT_DATABASE_URL")}

    def docker(*args):
        result = subprocess.run(["docker", *args], capture_output=True, text=True)
        if result.returncode:
            # docker run contains an ephemeral password; never echo its argv/stderr.
            raise RuntimeError(f"isolated PostgreSQL Docker {args[0]} failed")
        return result.stdout.strip()

    try:
        password = secrets.token_hex(20)
        docker("run", "--rm", "-d", "--name", name, "-e", f"POSTGRES_PASSWORD={password}",
               "-p", "127.0.0.1::5432", "postgres:16")
        port = docker("port", name, "5432/tcp").rsplit(":", 1)[1]
        os.environ.update({**overrides,
                           "INSIGHT_AGENT_DATABASE_URL": f"postgresql://postgres:{password}@127.0.0.1:{port}/postgres"})
        get_settings.cache_clear()
        for _ in range(100):
            try:
                initialize_database()
                break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("isolated PostgreSQL did not become ready")
        with get_db_connection() as connection:
            for user in ("owner", "other"):
                connection.execute("""INSERT INTO users(id,email,role,password_salt,password_hash,created_at,updated_at)
                    VALUES (?,?,'user','fixture','fixture','fixture','fixture')""", (user, f"{user}@example.com"))
            connection.commit()
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_case)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    finally:
        subprocess.run(["docker", "rm", "-f", "-v", name], capture_output=True)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()
