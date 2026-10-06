#!/usr/bin/env python3
"""Real task stream, lifecycle and exports with concurrent builtin reads and isolated PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import os
from threading import Barrier, Event, Lock, get_ident
import unittest
from unittest.mock import patch

from task_postgres_fixture import run_isolated_postgres
from test_task_rerun_postgres import TaskRerunPostgresTests
from app.api.deps import get_current_user
from app.config import get_settings
from app.main import app
from app.services import chat_persistence_service as persistence
from app.services import task_queue_service as queue
from app.services import tool_runtime as runtime
from fastapi.testclient import TestClient


class TaskParallelPostgresTests(unittest.TestCase):
    setUp = TaskRerunPostgresTests.setUp

    @contextmanager
    def client(self, runner=None):
        original = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: {"id": "owner", "role": "user"}
        try:
            with patch("app.services.chat_execution_service.try_append_task_memory"), \
                 patch.object(runtime, "query_knowledge_base", return_value={"hits": [
                     {"content": "parallel context fixture", "metadata": {"source": "fixture"}}],
                     "hit_count": 1, "knowledge_base_id": "default"}), \
                 patch.object(runtime, "run_tool", runner or runtime.run_tool):
                yield TestClient(app)
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original)

    def create(self, client):
        response = client.post(f"/api/tasks/{self.parent}/reruns", json={"user_input": "rag [calc:2+3]"})
        self.assertEqual(response.status_code, 201)
        return response.json()["task_id"]

    def task(self, client, task_id):
        return client.get(f"/api/tasks/{task_id}").json()

    def steps(self, client, task_id):
        return client.get(f"/api/tasks/{task_id}/trace").json()["steps"]

    def test_parallel_actual_stream_overlap_trace_delta_and_export(self):
        barrier, threads, owners = Barrier(2), [], []
        original = runtime.run_tool
        def runner(*, name, **kwargs):
            if name in {"task_retrieve", "calc_eval"}:
                threads.append(get_ident())
                owners.append(kwargs["user_id"])
                barrier.wait(timeout=3)
            return original(name=name, **kwargs)
        with self.client(runner) as client:
            child = self.create(client)
            stream = client.get(f"/api/tasks/{child}/stream")
            self.assertIn("event: done", stream.text)
            self.assertEqual(self.task(client, child)["status_normalized"], "completed")
            self.assertEqual(len(set(threads)), 2)
            self.assertEqual(owners, ["owner", "owner"])
            steps = self.steps(client, child)
            sequences = [step["seq"] for step in steps]
            self.assertEqual(sequences, sorted(set(sequences)))
            actions = [step for step in steps if step["type"] == "action"]
            parallel = [step for step in actions if step["meta"].get("execution_mode") == "parallel"]
            self.assertEqual(len(parallel), 2)
            self.assertEqual(len({step["meta"]["parallel_group_id"] for step in parallel}), 1)
            self.assertTrue(any(step["meta"].get("step_type") == "rag_retrieval" for step in steps))
            final = steps[-1]["content"]
            self.assertIn("Retrieved 1 hit", final)
            self.assertIn("5", final)
            delta = client.get(f"/api/tasks/{child}/trace/delta?after_seq=0&limit=100").json()
            self.assertEqual([step["id"] for step in delta["steps"]], [step["id"] for step in steps])
            exported = client.get(f"/api/tasks/{child}/export/json").json()
            self.assertEqual([(step["id"], step["seq"]) for step in exported["trace"]["steps"]],
                             [(step["id"], step["seq"]) for step in steps])
            self.assertEqual([step["meta"].get("parallel_group_id") for step in exported["trace"]["steps"]],
                             [step["meta"].get("parallel_group_id") for step in steps])
            self.assertEqual(exported["version"], "1.0")
            self.assertEqual(client.get(f"/api/tasks/{child}/export/markdown").status_code, 200)

    def test_serial_setting_keeps_tools_on_one_owner_thread(self):
        original, threads = runtime.run_tool, []
        def runner(*, name, **kwargs):
            threads.append(get_ident())
            return original(name=name, **kwargs)
        with patch.dict(os.environ, {"TASK_TOOL_MAX_CONCURRENT": "1"}):
            get_settings.cache_clear()
            try:
                with self.client(runner) as client:
                    child = self.create(client)
                    self.assertIn("event: done", client.get(f"/api/tasks/{child}/stream").text)
                    self.assertEqual(len(set(threads)), 1)
                    self.assertFalse(any("execution_mode" in step["meta"] for step in self.steps(client, child)))
            finally:
                get_settings.cache_clear()

    def lifecycle_fixture(self, *, timeout=False):
        started, release, all_done, lock = Event(), Event(), Event(), Lock()
        count, finished = [0], [0]
        original = runtime.run_tool
        def runner(*, name, **kwargs):
            if name in {"task_retrieve", "calc_eval"}:
                with lock:
                    count[0] += 1
                    if count[0] == 2:
                        started.set()
                release.wait(5)
                try:
                    return original(name=name, **kwargs)
                finally:
                    with lock:
                        finished[0] += 1
                        if finished[0] == 2:
                            all_done.set()
            return original(name=name, **kwargs)
        overrides = {"TASK_TIMEOUT_SEC": "1"} if timeout else {}
        with patch.dict(os.environ, overrides):
            get_settings.cache_clear()
            try:
                with self.client(runner) as client, ThreadPoolExecutor(max_workers=1) as pool:
                    child = self.create(client)
                    response = pool.submit(client.get, f"/api/tasks/{child}/stream")
                    try:
                        self.assertTrue(started.wait(3))
                        if not timeout:
                            self.assertEqual(client.post(f"/api/tasks/{child}/cancel").status_code, 200)
                        stream = response.result(timeout=3)
                        event, status = ("timeout", "timed_out") if timeout else ("cancelled", "cancelled")
                        self.assertIn(f"event: {event}", stream.text)
                        self.assertNotIn("event: done", stream.text)
                        self.assertEqual(self.task(client, child)["status_normalized"], status)
                        before = self.steps(client, child)
                        self.assertFalse(any(step["meta"].get("execution_mode") == "parallel" for step in before))
                        release.set()
                        self.assertTrue(all_done.wait(3))
                        self.assertEqual(self.steps(client, child), before)
                        self.assertEqual(len(persistence.get_task_messages(child, "owner")), 1)
                        self.assertEqual(queue.get_task_queue_snapshot(max_concurrent=32)["active_count"], 0)
                    finally:
                        release.set()
                        all_done.wait(3)
            finally:
                get_settings.cache_clear()

    def test_cancelled_stream_returns_before_inflight_reads_and_drops_late_writes(self):
        self.lifecycle_fixture()

    def test_timeout_stream_returns_before_inflight_reads_and_drops_late_writes(self):
        self.lifecycle_fixture(timeout=True)

    def test_fatal_tool_failure_retains_failing_trace_and_no_assistant(self):
        original, sibling_started, release, done = runtime.run_tool, Event(), Event(), Event()
        def runner(*, name, **kwargs):
            if name == "calc_eval":
                sibling_started.set()
                release.wait(3)
                try:
                    return original(name=name, **kwargs)
                finally:
                    done.set()
            if name == "task_retrieve":
                self.assertTrue(sibling_started.wait(3))
                raise runtime.MockToolExecutionError("fatal read fixture", fatal=True)
            return original(name=name, **kwargs)
        with self.client(runner) as client:
            try:
                child = self.create(client)
                stream = client.get(f"/api/tasks/{child}/stream")
                self.assertNotIn("event: done", stream.text)
                self.assertEqual(self.task(client, child)["status_normalized"], "failed")
                before = self.steps(client, child)
                self.assertTrue(any(step["meta"].get("execution_mode") == "parallel" for step in before))
                self.assertTrue(any("fatal read fixture" in str((step["meta"].get("tool") or {}).get("error", "")) for step in before))
                release.set()
                self.assertTrue(done.wait(3))
                self.assertEqual(self.steps(client, child), before)
                self.assertEqual(len(persistence.get_task_messages(child, "owner")), 1)
            finally:
                release.set()
                done.wait(3)

    def test_retry_reexecutes_only_failed_read(self):
        original, calls, lock = runtime.run_tool, [], Lock()
        def runner(*, name, attempt, **kwargs):
            with lock:
                calls.append((name, attempt))
            if name == "task_retrieve" and attempt == 0:
                raise runtime.MockToolExecutionError("retry read fixture", fatal=False)
            return original(name=name, attempt=attempt, **kwargs)
        with self.client(runner) as client:
            child = self.create(client)
            self.assertIn("event: done", client.get(f"/api/tasks/{child}/stream").text)
            self.assertEqual(calls.count(("calc_eval", 0)), 1)
            self.assertEqual(calls.count(("task_retrieve", 0)), 1)
            self.assertEqual(calls.count(("task_retrieve", 1)), 1)


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(TaskParallelPostgresTests, settings={"TASK_TOOL_MAX_CONCURRENT": "2"}))
