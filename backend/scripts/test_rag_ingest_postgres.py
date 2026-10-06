#!/usr/bin/env python3
"""Exercise queue SQL and restart behavior against a disposable Docker PostgreSQL."""

from __future__ import annotations

import json
import argparse
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import get_settings
from app.db import get_db_connection, initialize_database
from app.services import rag_ingest_jobs as jobs, rag_ingest_worker as worker
from rag_ingest_postgres_batches import IngestPostgresBatchesMixin, RealChromaBatchesMixin

PAYLOAD = {"knowledge_base_id": "default", "documents": [{"text": "private fixture text"}],
           "chunk_size": 500, "chunk_overlap": 80}
RESULT = {"documents_ingested": 1, "chunks_added": 1, "document_count": 1,
          "chunk_size": 500, "chunk_overlap": 80}


class IngestPostgresTests(IngestPostgresBatchesMixin, RealChromaBatchesMixin, unittest.TestCase):
    def setUp(self):
        with get_db_connection() as connection:
            connection.execute("TRUNCATE rag_ingest_jobs, audit_logs")
            connection.execute("UPDATE users SET role = 'admin' WHERE id = 'admin'")
            connection.commit()

    def create(self, key=None, user="user-a", owner=None, payload=None):
        return jobs.create_ingest_job(user_id=user, owner_user_id=owner or user,
                                     payload=payload or PAYLOAD, idempotency_key=key or str(uuid4()))

    def stored(self, job_id):
        with get_db_connection() as connection:
            return connection.execute("SELECT * FROM rag_ingest_jobs WHERE id = ?", (job_id,)).fetchone()

    def test_concurrent_idempotent_submissions_create_one_row(self):
        key = str(uuid4())
        with ThreadPoolExecutor(max_workers=8) as pool:
            submitted = list(pool.map(lambda _: self.create(key), range(8)))
        self.assertEqual(len({job["id"] for job in submitted}), 1)
        self.assertEqual(len(jobs.list_ingest_jobs(user_id="user-a", knowledge_base_id=None, limit=100)), 1)
        with self.assertRaises(jobs.IngestJobError) as raised:
            self.create(key, payload={**PAYLOAD, "documents": [{"text": "changed"}]})
        self.assertEqual(raised.exception.status_code, 409)

    def test_concurrent_submissions_enforce_three_active_job_limit(self):
        def submit(_):
            try:
                return self.create()["status"]
            except jobs.IngestJobError as exc:
                return exc.status_code
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(submit, range(10)))
        self.assertEqual(outcomes.count("queued"), 3)
        self.assertEqual(outcomes.count(429), 7)

    def test_list_and_detail_and_cancel_are_user_isolated(self):
        job = self.create()
        self.assertEqual(jobs.list_ingest_jobs(user_id="user-b", knowledge_base_id=None, limit=20), [])
        for action in (jobs.get_ingest_job, jobs.cancel_ingest_job):
            with self.assertRaises(jobs.IngestJobError) as raised:
                action(user_id="user-b", job_id=job["id"])
            self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(self.stored(job["id"])["status"], "queued")

    def test_cancel_is_idempotent_clears_text_and_releases_quota(self):
        job = self.create()
        self.create()
        self.create()
        for _ in range(2):
            self.assertEqual(jobs.cancel_ingest_job(user_id="user-a", job_id=job["id"])["status"], "cancelled")
        self.assertIsNone(self.stored(job["id"])["payload_json"])
        self.assertEqual(self.create()["status"], "queued")

    def test_worker_success_is_persisted_and_documents_are_removed(self):
        job = self.create()
        with patch.object(worker, "ingest_knowledge_documents", return_value=RESULT) as ingest:
            self.assertTrue(worker.process_next_job())
            self.assertFalse(worker.process_next_job())
            ingest.assert_called_once()
        result = jobs.get_ingest_job(user_id="user-a", job_id=job["id"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"]["chunks_added"], 1)
        self.assertIsNotNone(result["started_at"])
        self.assertIsNotNone(result["finished_at"])
        self.assertIsNone(self.stored(job["id"])["payload_json"])
        self.assertNotIn("private fixture text", json.dumps(result))

    def test_worker_failure_is_not_replayed_and_exception_is_not_exposed(self):
        job = self.create()
        with patch.object(worker, "ingest_knowledge_documents", side_effect=RuntimeError("Bearer secret")) as ingest:
            self.assertTrue(worker.process_next_job())
            self.assertFalse(worker.process_next_job())
            ingest.assert_called_once()
        view = jobs.get_ingest_job(user_id="user-a", job_id=job["id"])
        self.assertEqual(view["error_code"], "chroma_unavailable")
        self.assertNotIn("secret", json.dumps(view))
        self.assertIsNone(self.stored(job["id"])["payload_json"])

    def test_live_worker_lock_blocks_duplicate_claim_and_orphan_recovery(self):
        job = self.create()
        started = threading.Event()
        release = threading.Event()
        def ingest(**_):
            started.set()
            if not release.wait(10):
                raise RuntimeError("fixture timed out")
            return RESULT
        with patch.object(worker, "ingest_knowledge_documents", side_effect=ingest) as action:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(worker.process_next_job)
                try:
                    self.assertTrue(started.wait(5))
                    self.assertEqual(worker.recover_interrupted_jobs(), 0)
                    self.assertFalse(worker.process_next_job())
                    self.assertEqual(self.stored(job["id"])["status"], "running")
                    with self.assertRaises(jobs.IngestJobError) as raised:
                        jobs.cancel_ingest_job(user_id="user-a", job_id=job["id"])
                    self.assertEqual(raised.exception.status_code, 409)
                finally:
                    release.set()
                self.assertTrue(future.result(5))
            action.assert_called_once()

    def test_two_workers_claim_different_jobs(self):
        self.create()
        self.create()
        barrier = threading.Barrier(2)
        def ingest(**_):
            barrier.wait(timeout=10)
            return RESULT
        with patch.object(worker, "ingest_knowledge_documents", side_effect=ingest) as action:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(worker.process_next_job) for _ in range(2)]
                self.assertTrue(all(future.result(15) for future in futures))
            self.assertEqual(action.call_count, 2)
        self.assertTrue(all(job["status"] == "completed" for job in
                            jobs.list_ingest_jobs(user_id="user-a", knowledge_base_id=None, limit=20)))

    def test_shared_import_checks_current_admin_role(self):
        job = self.create(user="admin", owner="__shared__", payload={**PAYLOAD, "knowledge_base_id": "shared-handbook"})
        with get_db_connection() as connection:
            connection.execute("UPDATE users SET role = 'user' WHERE id = 'admin'")
            connection.commit()
        with patch.object(worker, "ingest_knowledge_documents") as ingest:
            self.assertTrue(worker.process_next_job())
            ingest.assert_not_called()
        self.assertEqual(self.stored(job["id"])["error_code"], "permission_revoked")

    def test_killed_worker_is_recovered_without_replaying_chroma(self):
        job = self.create()
        code = ("import time; from app.services import rag_ingest_worker as w; "
                "w.ingest_knowledge_documents=lambda **kw: time.sleep(60); w.process_next_job()")
        process = subprocess.Popen([sys.executable, "-c", code], cwd=BACKEND,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and self.stored(job["id"])["status"] != "running":
                time.sleep(0.1)
            self.assertEqual(self.stored(job["id"])["status"], "running")
            self.assertEqual(worker.recover_interrupted_jobs(), 0)
        finally:
            process.kill()
            process.wait(timeout=5)
        with patch.object(worker, "ingest_knowledge_documents") as ingest:
            self.assertEqual(worker.recover_interrupted_jobs(), 1)
            self.assertFalse(worker.process_next_job())
            ingest.assert_not_called()
        self.assertEqual(self.stored(job["id"])["error_code"], "interrupted")
        self.assertIsNone(self.stored(job["id"])["payload_json"])

    def test_queued_job_survives_fresh_worker_process(self):
        job = self.create()
        code = ("from app.services import rag_ingest_worker as w; "
                f"w.ingest_knowledge_documents=lambda **kw: {RESULT!r}; raise SystemExit(w.main())")
        completed = subprocess.run([sys.executable, "-c", code], cwd=BACKEND,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(self.stored(job["id"])["status"], "completed")

    def test_worker_exits_when_api_parent_is_killed(self):
        job = self.create()
        child_code = ("from app.services import rag_ingest_worker as w; import os,time; "
                      "w.ingest_knowledge_documents=lambda **kw: time.sleep(60); "
                      "w.run_loop(parent_pid=os.getppid())")
        parent_code = ("import subprocess,sys,time; "
                       f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                       "print(p.pid,flush=True); time.sleep(60)")
        parent = subprocess.Popen([sys.executable, "-c", parent_code], cwd=BACKEND,
                                  text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        child_pid = None
        try:
            child_pid = int(parent.stdout.readline())
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and self.stored(job["id"])["status"] != "running":
                time.sleep(0.1)
            self.assertEqual(self.stored(job["id"])["status"], "running")
            parent.kill()
            parent.wait(timeout=5)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not worker.recover_interrupted_jobs():
                time.sleep(0.1)
            self.assertEqual(self.stored(job["id"])["error_code"], "interrupted")
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=5)
            parent.stdout.close()
            if child_pid:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_http_routes_return_202_and_validate_inputs_and_owner_scope(self):
        from fastapi.testclient import TestClient
        from app.api.deps import get_current_user
        from app.main import app
        original = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: {"id": "user-a", "role": "user"}
        try:
            client = TestClient(app)  # No lifespan: control workers explicitly in this SQL fixture.
            response = client.post("/api/rag/ingest-jobs", json=PAYLOAD)
            self.assertEqual(response.status_code, 202)
            job_id = response.json()["id"]
            self.assertNotIn("private fixture text", response.text)
            self.assertEqual(client.get(f"/api/rag/ingest-jobs/{job_id}").status_code, 200)
            self.assertEqual(len(client.get("/api/rag/ingest-jobs").json()["items"]), 1)
            self.assertEqual(client.post("/api/rag/ingest-jobs", json={**PAYLOAD, "chunk_overlap": 500}).status_code, 422)
            self.assertEqual(client.post("/api/rag/ingest-jobs", json={**PAYLOAD, "knowledge_base_id": "shared-handbook"}).status_code, 403)
            app.dependency_overrides[get_current_user] = lambda: {"id": "user-b", "role": "user"}
            self.assertEqual(client.get(f"/api/rag/ingest-jobs/{job_id}").status_code, 404)
            self.assertEqual(client.post(f"/api/rag/ingest-jobs/{job_id}/cancel").status_code, 404)
            self.assertEqual(client.get("/api/rag/ingest-jobs").json()["items"], [])
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original)


def docker(*args):
    return subprocess.run(["docker", *args], check=True, text=True, capture_output=True).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-chroma", action="store_true", help="Include isolated real Chroma batch fixtures")
    args = parser.parse_args()
    name = f"insightagent-ingest-test-{uuid4().hex[:12]}"
    chroma_name = name + "-chroma"
    password = secrets.token_hex(20)
    keys = ("INSIGHT_AGENT_DATABASE_URL", "CHROMA_HOST", "CHROMA_PORT")
    previous = {key: os.environ.get(key) for key in keys}
    try:
        docker("run", "--rm", "-d", "--name", name, "-e", f"POSTGRES_PASSWORD={password}",
               "-p", "127.0.0.1::5432", "postgres:16")
        port = docker("port", name, "5432/tcp").rsplit(":", 1)[1]
        os.environ["INSIGHT_AGENT_DATABASE_URL"] = f"postgresql://postgres:{password}@127.0.0.1:{port}/postgres"
        if args.with_chroma:
            docker("run", "--rm", "-d", "--name", chroma_name, "-e", "ANONYMIZED_TELEMETRY=FALSE",
                   "-p", "127.0.0.1::8000", "chromadb/chroma:latest")
            os.environ["CHROMA_HOST"] = "127.0.0.1"
            os.environ["CHROMA_PORT"] = docker("port", chroma_name, "8000/tcp").rsplit(":", 1)[1]
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
            for user, role in [("user-a", "user"), ("user-b", "user"), ("admin", "admin")]:
                connection.execute("""INSERT INTO users
                    (id, email, role, password_salt, password_hash, created_at, updated_at)
                    VALUES (?, ?, ?, 'fixture', 'fixture', ?, ?)""",
                    (user, f"{user}@example.com", role, jobs.utc_now(), jobs.utc_now()))
            connection.commit()
        if args.with_chroma:
            from app.services.chroma_rag_service import _http_client
            for _ in range(100):
                try:
                    _http_client()
                    break
                except Exception:
                    time.sleep(0.1)
            else:
                raise RuntimeError("isolated Chroma did not become ready")
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(IngestPostgresTests)
        suite = unittest.TestSuite(test for test in suite if args.with_chroma or not test._testMethodName.startswith("test_real_"))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    finally:
        subprocess.run(["docker", "rm", "-f", "-v", name], capture_output=True)
        if args.with_chroma:
            subprocess.run(["docker", "rm", "-f", "-v", chroma_name], capture_output=True)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()


if __name__ == "__main__":
    raise SystemExit(main())
