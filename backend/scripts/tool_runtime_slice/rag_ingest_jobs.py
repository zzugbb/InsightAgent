from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routes import rag_ingest as routes
from app.services import rag_ingest_jobs as jobs, rag_ingest_worker as worker
from app.services.rag_ingest_runner import run_ingest_worker


def row(status="queued", **overrides):
    return {"id": str(uuid4()), "knowledge_base_id": "default", "document_total": 1,
            "status": status, "result_json": None, "error_code": None,
            "created_at": "2026-10-06T00:00:00+00:00", "started_at": None,
            "finished_at": None, **overrides}


def connection_patch(module, responses):
    connection = MagicMock()
    connection.execute.side_effect = [MagicMock(**response) for response in responses]
    context = MagicMock()
    context.__enter__.return_value = connection
    return connection, patch.object(module, "get_db_connection", return_value=context)


class RagIngestJobsMixin:
    def test_rag_ingest_job_request_rejects_blank_and_invalid_overlap(self):
        for documents, overlap in [([{"text": "  "}], 80), ([{"text": "ok"}], 500)]:
            with self.assertRaises(ValidationError):
                routes.RagIngestJobRequest(documents=documents, chunk_overlap=overlap)

    def test_rag_ingest_job_request_limits_aggregate_text(self):
        with self.assertRaises(ValidationError):
            routes.RagIngestJobRequest(documents=[{"text": "x" * 64_000}] * 9)

    def test_rag_ingest_job_request_generates_unique_idempotency_keys(self):
        a = routes.RagIngestJobRequest(documents=[{"text": "ok"}])
        b = routes.RagIngestJobRequest(documents=[{"text": "ok"}])
        self.assertNotEqual(a.idempotency_key, b.idempotency_key)

    def test_rag_ingest_job_shared_write_requires_admin(self):
        with patch.object(routes, "create_ingest_job") as create:
            with self.assertRaises(HTTPException) as raised:
                routes.post_ingest_job(routes.RagIngestJobRequest(
                    knowledge_base_id="Shared-Handbook", documents=[{"text": "hello"}],
                ), {"id": "user-a", "role": "user"})
            self.assertEqual(raised.exception.status_code, 403)
            create.assert_not_called()

    def test_rag_ingest_job_admin_routes_to_shared_owner(self):
        with patch.object(routes, "create_ingest_job", return_value=jobs.public_job(row())) as create:
            routes.post_ingest_job(routes.RagIngestJobRequest(
                knowledge_base_id="shared-handbook", documents=[{"text": "hello"}],
            ), {"id": "admin-a", "role": "admin"})
            self.assertEqual(create.call_args.kwargs["owner_user_id"], "__shared__")
            self.assertNotIn("idempotency_key", create.call_args.kwargs["payload"])

    def test_rag_ingest_job_projection_excludes_documents_and_internal_identity(self):
        view = jobs.public_job(row(payload_json="private document", user_id="other-user",
                                   payload_hash="hash", idempotency_key="key"))
        self.assertNotIn("private document", json.dumps(view))
        self.assertEqual(set(view), {"id", "knowledge_base_id", "document_total", "status",
                                    "result", "error_code", "created_at", "started_at", "finished_at"})

    def test_rag_ingest_job_queue_quota_blocks_insert(self):
        conn, patched = connection_patch(jobs, [{}, {"fetchone.return_value": None},
                                               {"fetchone.return_value": {"total": 3}}])
        with patched, self.assertRaises(jobs.IngestJobError) as raised:
            jobs.create_ingest_job(user_id="user", owner_user_id="user",
                                   payload={"knowledge_base_id": "default", "documents": []},
                                   idempotency_key="key")
        self.assertEqual(raised.exception.status_code, 429)
        self.assertFalse(any("INSERT" in call.args[0] for call in conn.execute.call_args_list))

    def test_rag_ingest_job_same_idempotency_key_different_payload_conflicts(self):
        _, patched = connection_patch(jobs, [{}, {"fetchone.return_value": row(payload_hash="different")}])
        with patched, self.assertRaises(jobs.IngestJobError) as raised:
            jobs.create_ingest_job(user_id="user", owner_user_id="user",
                                   payload={"knowledge_base_id": "default", "documents": []},
                                   idempotency_key="key")
        self.assertEqual(raised.exception.status_code, 409)

    def test_rag_ingest_job_oversized_metadata_rejected_before_database(self):
        with patch.object(jobs, "get_db_connection") as db, self.assertRaises(jobs.IngestJobError) as raised:
            jobs.create_ingest_job(user_id="user", owner_user_id="user",
                payload={"knowledge_base_id": "default", "documents": [], "metadata": "x" * 1_000_001},
                idempotency_key="key")
        self.assertEqual(raised.exception.status_code, 413)
        db.assert_not_called()

    def test_rag_ingest_job_cancel_rejects_running_job(self):
        _, patched = connection_patch(jobs, [{"fetchone.return_value": row(status="running")}])
        with patched, self.assertRaises(jobs.IngestJobError) as raised:
            jobs.cancel_ingest_job(user_id="user", job_id="job")
        self.assertEqual(raised.exception.status_code, 409)

    def test_rag_ingest_job_detail_is_owner_scoped(self):
        conn, patched = connection_patch(jobs, [{"fetchone.return_value": None}])
        with patched, self.assertRaises(jobs.IngestJobError) as raised:
            jobs.get_ingest_job(user_id="user-a", job_id="job-b")
        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(conn.execute.call_args.args[1], ("job-b", "user-a"))

    def test_rag_ingest_job_recovery_preserves_live_worker(self):
        conn, patched = connection_patch(worker, [{"fetchall.return_value": [{"id": "job"}]},
                                                  {"fetchone.return_value": {"acquired": False}}])
        with patched:
            self.assertEqual(worker.recover_interrupted_jobs(), 0)
        self.assertFalse(any("UPDATE" in call.args[0] for call in conn.execute.call_args_list))

    def test_rag_ingest_job_recovery_clears_orphan_payload_without_replay(self):
        conn, patched = connection_patch(worker, [{"fetchall.return_value": [{"id": "job"}]},
            {"fetchone.return_value": {"acquired": True}}, {"rowcount": 1}, {}])
        with patched, patch.object(worker, "ingest_knowledge_documents") as ingest:
            self.assertEqual(worker.recover_interrupted_jobs(), 1)
            ingest.assert_not_called()
        sql = conn.execute.call_args_list[2].args[0]
        self.assertIn("payload_json = NULL", sql)
        self.assertIn("'interrupted'", sql)

    def _rag_ingest_worker_case(self, *, shared=False, role="user", error=None):
        queued = row(user_id="user", owner_user_id="__shared__" if shared else "user",
                     payload_json=json.dumps({"knowledge_base_id": "default", "documents": [{"text": "private"}],
                                              "chunk_size": 500, "chunk_overlap": 80}))
        conn, patched = connection_patch(worker, [{"fetchone.return_value": queued},
            {"fetchone.return_value": {"acquired": True}}, {}, {"fetchone.return_value": {"role": role}}, {}, {}])
        raw = {"documents_ingested": 1, "chunks_added": 2, "document_count": 2,
               "chunk_size": 500, "chunk_overlap": 80, "text": "private", "error": "token=secret"}
        with patched, patch.object(worker, "ingest_knowledge_documents", return_value=raw, side_effect=error) as ingest, \
             patch.object(worker, "safe_record_audit_event"):
            self.assertTrue(worker.process_next_job())
        terminal_call = conn.execute.call_args_list[-2]
        self.assertIn("payload_json = NULL", terminal_call.args[0])
        return terminal_call.args[1], ingest

    def test_rag_ingest_job_worker_success_only_returns_safe_counts(self):
        params, ingest = self._rag_ingest_worker_case()
        self.assertEqual(params[0], "completed")
        self.assertEqual(json.loads(params[1])["chunks_added"], 2)
        self.assertNotIn("private", params[1])
        self.assertNotIn("secret", params[1])
        ingest.assert_called_once()

    def test_rag_ingest_job_worker_shared_permission_revoked(self):
        params, ingest = self._rag_ingest_worker_case(shared=True)
        self.assertEqual(params[2], "permission_revoked")
        ingest.assert_not_called()

    def test_rag_ingest_job_worker_failure_hides_raw_exception(self):
        params, _ = self._rag_ingest_worker_case(error=RuntimeError("Bearer private-secret"))
        self.assertEqual(params[0], "failed")
        self.assertEqual(params[2], "chroma_unavailable")
        self.assertNotIn("private-secret", repr(params))

    def test_rag_ingest_job_runner_kills_worker_on_shutdown(self):
        async def scenario():
            stop = asyncio.Event()
            exited = asyncio.Event()
            process = MagicMock(returncode=None)
            async def wait():
                await exited.wait()
                return 0
            async def readline():
                await exited.wait()
                return b""
            process.stdout.readline = readline
            def kill():
                process.returncode = -9
                exited.set()
            process.wait = wait
            process.kill = MagicMock(side_effect=kill)
            with patch("app.services.rag_ingest_runner.asyncio.create_subprocess_exec", AsyncMock(return_value=process)):
                task = asyncio.create_task(run_ingest_worker(stop))
                await asyncio.sleep(0.01)
                stop.set()
                await asyncio.wait_for(task, 1)
                process.kill.assert_called_once()
        asyncio.run(scenario())

    def test_rag_ingest_job_runner_kills_timed_out_worker(self):
        async def scenario():
            stop = asyncio.Event()
            process = MagicMock(returncode=None)
            exited = asyncio.Event()
            async def wait():
                await exited.wait()
                return -9
            async def readline():
                await exited.wait()
                return b""
            process.stdout.readline = readline
            def kill():
                process.returncode = -9
                exited.set()
                stop.set()
            process.wait = wait
            process.kill = MagicMock(side_effect=kill)
            with patch("app.services.rag_ingest_runner.asyncio.create_subprocess_exec", AsyncMock(return_value=process)):
                await asyncio.wait_for(run_ingest_worker(stop, timeout_sec=0.01), 1)
                process.kill.assert_called_once()
        asyncio.run(scenario())
