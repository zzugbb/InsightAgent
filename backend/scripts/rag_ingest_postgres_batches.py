"""Batch progress fixtures; SQL remains real, selected Chroma calls can fail deterministically."""

import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.db import get_db_connection
from app.services import chroma_rag_service as rag, rag_ingest_worker as worker
from app.services.rag_ingest_schema import initialize_ingest_schema
from app.services import rag_ingest_jobs as jobs

BATCH_PAYLOAD = {"knowledge_base_id": "default", "chunk_size": 120, "chunk_overlap": 0,
                 "documents": [{"text": "A" * 360, "document_id": "a"},
                               {"text": "B" * 240, "document_id": "b"}]}


def fixture_client():
    client = MagicMock()
    client.get_max_batch_size.return_value = 2
    client.get_or_create_collection.return_value.count.return_value = 5
    return client


class IngestPostgresBatchesMixin:
    def test_batch_progress_is_visible_during_live_worker_and_kept_on_completion(self):
        job = self.create(payload=BATCH_PAYLOAD)
        client = fixture_client()
        second_batch = threading.Event()
        release = threading.Event()
        calls = 0
        def add(**_):
            nonlocal calls
            calls += 1
            if calls == 2:
                second_batch.set()
                if not release.wait(10):
                    raise RuntimeError("fixture timed out")
        client.get_or_create_collection.return_value.add.side_effect = add
        with patch.object(rag, "_http_client", return_value=client), ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(worker.process_next_job)
            try:
                self.assertTrue(second_batch.wait(5))
                view = jobs.get_ingest_job(user_id="user-a", job_id=job["id"])
                self.assertEqual(view["status"], "running")
                self.assertEqual(view["progress"], {"documents_processed": 0, "chunks_written": 2, "chunk_total": 5})
                self.assertEqual(worker.recover_interrupted_jobs(), 0)
            finally:
                release.set()
            self.assertTrue(future.result(5))
        view = jobs.get_ingest_job(user_id="user-a", job_id=job["id"])
        self.assertEqual(view["progress"], {"documents_processed": 2, "chunks_written": 5, "chunk_total": 5})
        self.assertEqual(view["status"], "completed")
        self.assertIsNone(self.stored(job["id"])["payload_json"])

    def test_batch_failure_retains_only_confirmed_progress_without_replay(self):
        job = self.create(payload=BATCH_PAYLOAD)
        client = fixture_client()
        client.get_or_create_collection.return_value.add.side_effect = [None, RuntimeError("Bearer secret")]
        with patch.object(rag, "_http_client", return_value=client):
            self.assertTrue(worker.process_next_job())
            self.assertFalse(worker.process_next_job())
        view = jobs.get_ingest_job(user_id="user-a", job_id=job["id"])
        self.assertEqual(view["status"], "failed")
        self.assertEqual(view["progress"]["chunks_written"], 2)
        self.assertEqual(view["progress"]["documents_processed"], 0)
        self.assertEqual(view["error_code"], "chroma_unavailable")
        self.assertNotIn("secret", json.dumps(view))
        self.assertIsNone(self.stored(job["id"])["payload_json"])

    def test_batch_shared_role_revoked_mid_import_stops_next_write(self):
        job = self.create(user="admin", owner="__shared__",
                          payload={**BATCH_PAYLOAD, "knowledge_base_id": "shared-handbook"})
        client = fixture_client()
        def revoke(**_):
            with get_db_connection() as connection:
                connection.execute("UPDATE users SET role = 'user' WHERE id = 'admin'")
                connection.commit()
        client.get_or_create_collection.return_value.add.side_effect = revoke
        with patch.object(rag, "_http_client", return_value=client):
            self.assertTrue(worker.process_next_job())
        client.get_or_create_collection.return_value.add.assert_called_once()
        view = jobs.get_ingest_job(user_id="admin", job_id=job["id"])
        self.assertEqual(view["error_code"], "permission_revoked")
        self.assertEqual(view["progress"]["chunks_written"], 2)

    def test_batch_worker_kill_recovery_preserves_confirmed_progress(self):
        job = self.create(payload=BATCH_PAYLOAD)
        code = """import time
from app.services import rag_ingest_worker as w
def ingest(**kw):
    kw['on_progress']({'documents_processed': 0, 'chunks_written': 2, 'chunk_total': 5})
    time.sleep(60)
w.ingest_knowledge_documents = ingest
w.process_next_job()
"""
        process = subprocess.Popen([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if self.stored(job["id"])["progress_json"]:
                    break
                time.sleep(0.1)
            self.assertIsNotNone(self.stored(job["id"])["progress_json"])
        finally:
            process.kill()
            process.wait(timeout=5)
        self.assertEqual(worker.recover_interrupted_jobs(), 1)
        view = jobs.get_ingest_job(user_id="user-a", job_id=job["id"])
        self.assertEqual(view["error_code"], "interrupted")
        self.assertEqual(view["progress"]["chunks_written"], 2)
        self.assertIsNone(self.stored(job["id"])["payload_json"])

    def test_batch_existing_schema_upgrade_preserves_queued_payload_and_history(self):
        job = self.create()
        with get_db_connection() as connection:
            connection.execute("ALTER TABLE rag_ingest_jobs DROP COLUMN progress_json")
            initialize_ingest_schema(connection)
            initialize_ingest_schema(connection)
            connection.commit()
        self.assertEqual(self.stored(job["id"])["status"], "queued")
        self.assertIsNotNone(self.stored(job["id"])["payload_json"])
        self.assertIsNone(jobs.get_ingest_job(user_id="user-a", job_id=job["id"])["progress"])

    def test_batch_legacy_queued_expansion_is_rejected_before_chroma(self):
        job = self.create(payload={**BATCH_PAYLOAD, "documents": [{"text": "a" * 6000}], "chunk_overlap": 119})
        with patch.object(rag, "_http_client") as client:
            self.assertTrue(worker.process_next_job())
            client.assert_not_called()
        self.assertEqual(self.stored(job["id"])["error_code"], "invalid_input")


class RealChromaBatchesMixin:
    def test_real_batch_scale_writes_400_chunks_and_preserves_document_versions(self):
        payload = {"knowledge_base_id": "batch-scale", "chunk_size": 120, "chunk_overlap": 0,
                   "documents": [{"text": (f"Batch fixture document {index:02d}. " * 60)[:1200],
                                  "document_id": f"document-{index}", "source": "batch-fixture"}
                                 for index in range(40)]}
        from app.api.routes.rag_ingest import RagIngestJobRequest
        request = RagIngestJobRequest(**payload)
        job = self.create(payload=request.model_dump(exclude={"idempotency_key"}, exclude_none=True))
        started = time.monotonic()
        self.assertTrue(worker.process_next_job())
        view = jobs.get_ingest_job(user_id="user-a", job_id=job["id"])
        self.assertEqual(view["status"], "completed", view["error_code"])
        self.assertEqual(view["progress"], {"documents_processed": 40, "chunks_written": 400, "chunk_total": 400})
        self.assertEqual(view["result"]["chunks_added"], 400)
        collection = rag._http_client().get_collection(rag.rag_collection_name("user-a", "batch-scale"))
        try:
            records = collection.get(include=["metadatas"])
            self.assertEqual(len(records["ids"]), 400)
            for index in range(40):
                rows = [meta for meta in records["metadatas"] if meta["document_id"] == f"document-{index}"]
                self.assertEqual(sorted(meta["chunk_index"] for meta in rows), list(range(1, 11)))
                self.assertEqual({meta["chunk_total"] for meta in rows}, {10})
                self.assertEqual(len({meta["document_version"] for meta in rows}), 1)
            print(f"batch_scale documents=40 chunks=400 elapsed_sec={time.monotonic() - started:.2f}", flush=True)
        finally:
            rag._http_client().delete_collection(collection.name)

    def test_real_batch_failure_keeps_confirmed_chroma_records_for_review(self):
        job = self.create(payload={**BATCH_PAYLOAD, "knowledge_base_id": "batch-partial"})
        actual = worker.persist_progress
        def fail_after_write(connection, job_id, progress):
            actual(connection, job_id, progress)
            if progress["chunks_written"]:
                raise RuntimeError("fixture interruption after confirmed batch")
        with patch.dict(os.environ, {"RAG_INGEST_BATCH_SIZE": "2"}):
            from app.config import get_settings
            get_settings.cache_clear()
            try:
                with patch.object(worker, "persist_progress", side_effect=fail_after_write):
                    self.assertTrue(worker.process_next_job())
            finally:
                get_settings.cache_clear()
        view = jobs.get_ingest_job(user_id="user-a", job_id=job["id"])
        self.assertEqual(view["status"], "failed")
        self.assertEqual(view["progress"]["chunks_written"], 2)
        collection = rag._http_client().get_collection(rag.rag_collection_name("user-a", "batch-partial"))
        try:
            self.assertEqual(collection.count(), 2)
            self.assertFalse(worker.process_next_job())
        finally:
            rag._http_client().delete_collection(collection.name)
