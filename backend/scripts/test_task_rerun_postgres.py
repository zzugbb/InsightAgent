#!/usr/bin/env python3
"""Task branch transactions, ownership and existing stream/export against isolated PostgreSQL."""

import json
from pathlib import Path
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db import get_db_connection
from app.services import chat_persistence_service as persistence
from app.services import task_rerun_service as reruns
from task_postgres_fixture import run_isolated_postgres


class TaskRerunPostgresTests(unittest.TestCase):
    def setUp(self):
        with get_db_connection() as connection:
            connection.execute("TRUNCATE sessions, tasks, messages, task_reruns, audit_logs CASCADE")
            connection.commit()
        self.session = persistence.ensure_session("original input", "owner")
        self.parent = persistence.create_task(self.session, "original input", "owner", status="completed")
        persistence.create_message(self.session, "owner", "user", "original input", self.parent)

    def create(self, *, key=None, user="owner", task=None, prompt=None):
        return reruns.create_task_rerun(user_id=user, parent_task_id=task or self.parent,
                                       user_input=prompt, idempotency_key=key or str(uuid4()))

    def lineage(self, task=None, limit=20, offset=0):
        return reruns.get_task_reruns(user_id="owner", task_id=task or self.parent, limit=limit, offset=offset)

    def test_create_copies_input_into_independent_session_and_preserves_parent(self):
        before = persistence.get_task(self.parent, "owner")
        branch = self.create()
        self.assertNotEqual(branch["session_id"], self.session)
        child = persistence.get_task(branch["task_id"], "owner")
        self.assertEqual(child["prompt"], "original input")
        self.assertEqual(child["status"], "queued")
        self.assertIsNone(child["trace_json"])
        self.assertIsNone(child["usage_json"])
        self.assertEqual(persistence.get_task(self.parent, "owner"), before)
        messages = persistence.get_session_messages(branch["session_id"], "owner")
        self.assertEqual([(row["role"], row["content"]) for row in messages], [("user", "original input")])
        self.assertEqual(self.lineage(branch["task_id"])["parent_task_id"], self.parent)

    def test_edit_and_rerun_from_failed_cancelled_or_timeout(self):
        for status in ["failed", "cancelled", "timeout", "success", "error", "canceled"]:
            persistence.update_task_status(self.parent, status, "owner")
            branch = self.create(prompt=" edited input ")
            self.assertEqual(persistence.get_task(branch["task_id"], "owner")["prompt"], "edited input")

    def test_active_and_unknown_parents_rejected_without_creating_rows(self):
        for status in ["queued", "pending", "running", "unknown"]:
            persistence.update_task_status(self.parent, status, "owner")
            with self.assertRaises(reruns.TaskRerunError) as raised:
                self.create()
            self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(self.lineage()["total"], 0)
        self.assertEqual(persistence.count_sessions("owner"), 1)

    def test_create_and_lineage_hide_other_users_tasks(self):
        with self.assertRaises(reruns.TaskRerunError) as raised:
            self.create(user="other")
        self.assertEqual(raised.exception.status_code, 404)
        with self.assertRaises(reruns.TaskRerunError) as raised:
            reruns.get_task_reruns(user_id="other", task_id=self.parent, limit=20, offset=0)
        self.assertEqual(raised.exception.status_code, 404)

    def test_concurrent_same_key_creates_one_session_message_and_audit(self):
        key = str(uuid4())
        with ThreadPoolExecutor(max_workers=8) as pool:
            branches = list(pool.map(lambda _: self.create(key=key), range(8)))
        self.assertEqual(len({branch["task_id"] for branch in branches}), 1)
        self.assertEqual(self.lineage()["total"], 1)
        self.assertEqual(persistence.count_sessions("owner"), 2)
        with get_db_connection() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) AS n FROM audit_logs WHERE event_type = 'task_rerun_created'").fetchone()["n"], 1)
        self.assertEqual(len(persistence.get_task_messages(branches[0]["task_id"], "owner")), 1)

    def test_same_key_changed_input_or_parent_conflicts(self):
        key = str(uuid4())
        self.create(key=key)
        second = persistence.create_task(self.session, "other input", "owner", status="completed")
        for kwargs in [{"prompt": "different"}, {"task": second}]:
            with self.assertRaises(reruns.TaskRerunError) as raised:
                self.create(key=key, **kwargs)
            self.assertEqual(raised.exception.status_code, 409)

    def test_retry_returns_current_child_status_and_stays_private(self):
        key = str(uuid4())
        branch = self.create(key=key)
        persistence.update_task_status(branch["task_id"], "completed", "owner")
        retry = self.create(key=key)
        self.assertEqual(retry["status"], "completed")
        self.assertEqual(branch["task_id"], retry["task_id"])
        self.assertNotIn("idempotency_key", json.dumps(self.lineage()))

    def test_branch_creation_rolls_back_all_rows_when_lineage_insert_fails(self):
        with get_db_connection() as connection:
            connection.execute("""CREATE FUNCTION reject_branch_fixture() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'fixture'; END; $$""")
            connection.execute("CREATE TRIGGER reject_branch BEFORE INSERT ON task_reruns FOR EACH ROW EXECUTE FUNCTION reject_branch_fixture()")
            connection.commit()
        try:
            with self.assertRaises(Exception):
                self.create()
            self.assertEqual(persistence.count_sessions("owner"), 1)
            self.assertEqual(persistence.count_tasks("owner"), 1)
            self.assertEqual(len(persistence.get_session_messages(self.session, "owner")), 1)
        finally:
            with get_db_connection() as connection:
                connection.execute("DROP TRIGGER reject_branch ON task_reruns")
                connection.execute("DROP FUNCTION reject_branch_fixture()")
                connection.commit()

    def test_parent_session_deletion_preserves_branch_and_marks_source_removed(self):
        key = str(uuid4())
        branch = self.create(key=key)
        self.assertTrue(persistence.delete_session(self.session, "owner"))
        history = self.lineage(branch["task_id"])
        self.assertTrue(history["is_rerun"])
        self.assertIsNone(history["parent_task_id"])
        self.assertEqual(self.create(key=key)["task_id"], branch["task_id"])

    def test_lineage_pagination_is_stable_and_child_deletion_cleans_link(self):
        branches = [self.create() for _ in range(4)]
        first, second = self.lineage(limit=2), self.lineage(limit=2, offset=2)
        self.assertTrue(first["has_more"])
        self.assertFalse(second["has_more"])
        self.assertEqual({row["task_id"] for row in first["items"] + second["items"]}, {row["task_id"] for row in branches})
        persistence.delete_session(branches[0]["session_id"], "owner")
        self.assertEqual(self.lineage()["total"], 3)

    def test_http_branch_uses_existing_stream_trace_and_export(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.api.deps import get_current_user
        original = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: {"id": "owner", "role": "user"}
        try:
            client = TestClient(app)
            response = client.post(f"/api/tasks/{self.parent}/reruns", json={"user_input": "calculate 2 + 3"})
            self.assertEqual(response.status_code, 201)
            child = response.json()["task_id"]
            with patch("app.services.chat_execution_service.try_append_task_memory"):
                stream = client.get(f"/api/tasks/{child}/stream")
            self.assertIn("event: done", stream.text)
            self.assertEqual(client.get(f"/api/tasks/{child}").json()["status_normalized"], "completed")
            self.assertTrue(client.get(f"/api/tasks/{child}/trace").json()["steps"])
            self.assertEqual(client.get(f"/api/tasks/{child}/export/json").json()["version"], "1.0")
            self.assertEqual(client.get(f"/api/tasks/{child}/export/markdown").status_code, 200)
            self.assertEqual(client.get(f"/api/tasks/{self.parent}/reruns").json()["total"], 1)
            self.assertEqual(client.post(f"/api/tasks/{self.parent}/reruns", json={"user_input": "  "}).status_code, 422)
            app.dependency_overrides[get_current_user] = lambda: {"id": "other", "role": "user"}
            self.assertEqual(client.post(f"/api/tasks/{self.parent}/reruns", json={}).status_code, 404)
            self.assertEqual(client.get(f"/api/tasks/{child}/reruns").status_code, 404)
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original)


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(TaskRerunPostgresTests))
