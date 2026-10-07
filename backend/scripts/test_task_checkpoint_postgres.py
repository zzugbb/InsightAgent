#!/usr/bin/env python3
"""Experimental checkpoints on real isolated PostgreSQL; local providers only."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from unittest.mock import patch
from uuid import uuid4

from task_postgres_fixture import run_isolated_postgres
from test_task_parallel_postgres import TaskParallelPostgresTests
from app.config import get_settings
from app.services import chat_execution_service as execution
from app.services import chat_persistence_service as persistence
from app.services import task_rerun_service as reruns
from app.services import tool_runtime as runtime


class TaskCheckpointPostgresTests(unittest.TestCase):
    setUp = TaskParallelPostgresTests.setUp
    client = TaskParallelPostgresTests.client
    steps = TaskParallelPostgresTests.steps
    task = TaskParallelPostgresTests.task

    def source(self, client, prompt="rag [calc:2+3]"):
        task = client.post(f"/api/tasks/{self.parent}/reruns", json={"user_input": prompt}).json()["task_id"]
        self.assertIn("event: done", client.get(f"/api/tasks/{task}/stream").text)
        return task

    def resume(self, client, source, step_id, key=None):
        response = client.post(f"/api/tasks/{source}/reruns", json={"checkpoint_step_id": step_id,
                               "idempotency_key": key or str(uuid4())})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["task_id"]

    def candidates(self, client, task):
        response = client.get(f"/api/tasks/{task}/checkpoints")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["items"]

    def test_resume_reuses_rag_and_plan_without_replanning_or_double_usage(self):
        with self.client() as client:
            source = self.source(client)
            before = client.get(f"/api/tasks/{source}/export/json").json()
            candidates = self.candidates(client, source)
            self.assertEqual([item["tool_name"] for item in candidates], ["task_plan", "task_retrieve", "calc_eval"])
            branch = self.resume(client, source, candidates[-1]["step_id"])
            called = []
            original = runtime.run_tool
            def runner(*, name, **kwargs):
                called.append(name)
                return original(name=name, **kwargs)
            with patch.object(runtime, "run_tool", runner), patch.object(execution, "build_tool_plan_artifacts", side_effect=AssertionError("must not replan")):
                stream = client.get(f"/api/tasks/{branch}/stream")
            self.assertIn("event: done", stream.text)
            self.assertEqual(called, ["calc_eval"])
            steps = self.steps(client, branch)
            reused = [step for step in steps if step["meta"].get("checkpoint_reused")]
            self.assertGreaterEqual(len(reused), 2)
            self.assertTrue(all(step["meta"].get("cost_estimate") == 0 for step in reused))
            self.assertTrue(all(step["meta"].get("tokens", 0) == 0 for step in reused))
            self.assertIn("Retrieved 1 hit", steps[-1]["content"])
            self.assertIn("5", steps[-1]["content"])
            self.assertFalse(set(step["id"] for step in steps) & set(step["id"] for step in before["trace"]["steps"]))
            self.assertEqual([step["seq"] for step in steps], sorted(set(step["seq"] for step in steps)))
            delta = client.get(f"/api/tasks/{branch}/trace/delta?after_seq=0&limit=100").json()
            self.assertEqual(delta["steps"], steps)
            after = client.get(f"/api/tasks/{source}/export/json").json()
            for field in ("task", "trace", "messages"):
                self.assertEqual(before[field], after[field])
            self.assertEqual(client.get(f"/api/tasks/{branch}/export/json").json()["version"], "1.0")
            self.assertEqual(client.get(f"/api/tasks/{branch}/export/markdown").status_code, 200)
            self.assertEqual(len(self.candidates(client, branch)), 3)

    def test_resume_snapshot_survives_parent_deletion(self):
        with self.client() as client:
            source = self.source(client, "[calc:2+3]")
            branch = self.resume(client, source, self.candidates(client, source)[-1]["step_id"])
            source_session = self.task(client, source)["session_id"]
            persistence.delete_session(source_session, "owner")
            self.assertIn("event: done", client.get(f"/api/tasks/{branch}/stream").text)
            self.assertIsNone(client.get(f"/api/tasks/{branch}/reruns").json()["parent_task_id"])

    def test_concurrent_resume_idempotency_and_changed_step_conflict(self):
        with self.client() as client:
            source = self.source(client)
            candidates = self.candidates(client, source)
            key, step = str(uuid4()), candidates[-1]["step_id"]
            def create(_):
                return reruns.create_task_rerun(user_id="owner", parent_task_id=source, user_input=None,
                                               idempotency_key=key, checkpoint_step_id=step)
            with ThreadPoolExecutor(max_workers=4) as pool:
                branches = list(pool.map(create, range(4)))
            self.assertEqual(len({item["task_id"] for item in branches}), 1)
            changed = client.post(f"/api/tasks/{source}/reruns", json={"idempotency_key": key,
                                  "checkpoint_step_id": candidates[0]["step_id"]})
            self.assertEqual(changed.status_code, 409)
            self.assertEqual(changed.json()["detail"], "rerun_idempotency_conflict")

    def test_owner_terminal_and_immutable_input_validation(self):
        with self.client() as client:
            source = self.source(client)
            step = self.candidates(client, source)[-1]["step_id"]
            edited = client.post(f"/api/tasks/{source}/reruns", json={"checkpoint_step_id": step, "user_input": "edit"})
            self.assertEqual(edited.status_code, 422)
            for foreign in [str(uuid4()), self.parent]:
                self.assertEqual(client.post(f"/api/tasks/{foreign}/reruns", json={"checkpoint_step_id": step}).status_code,
                                 404 if foreign != self.parent else 409)
            with self.assertRaises(reruns.TaskRerunError) as error:
                reruns.create_task_rerun(user_id="other", parent_task_id=source, user_input=None,
                                        idempotency_key=str(uuid4()), checkpoint_step_id=step)
            self.assertEqual(error.exception.status_code, 404)
            persistence.update_task_status(source, "running", "owner")
            self.assertEqual(client.post(f"/api/tasks/{source}/reruns", json={"checkpoint_step_id": step}).status_code, 409)

    def test_current_disabled_tool_rejects_before_any_reused_trace_or_call(self):
        with self.client() as client:
            source = self.source(client, "[calc:2+3]")
            branch = self.resume(client, source, self.candidates(client, source)[-1]["step_id"])
            provider = runtime.StaticToolRegistryProvider({})
            with patch.object(execution, "get_configured_tool_registry_provider", return_value=provider), \
                 patch.object(runtime, "run_tool") as calls:
                response = client.get(f"/api/tasks/{branch}/stream")
            self.assertIn("checkpoint_unavailable", response.text)
            self.assertEqual(self.task(client, branch)["status_normalized"], "failed")
            calls.assert_not_called()

    def test_cancelled_queued_resume_never_executes(self):
        with self.client() as client:
            source = self.source(client)
            branch = self.resume(client, source, self.candidates(client, source)[-1]["step_id"])
            self.assertEqual(client.post(f"/api/tasks/{branch}/cancel").status_code, 200)
            with patch.object(runtime, "run_tool") as calls:
                client.get(f"/api/tasks/{branch}/stream")
            calls.assert_not_called()
            self.assertEqual(self.task(client, branch)["status_normalized"], "cancelled")


    def test_failed_selected_step_can_resume_after_successful_prefix(self):
        original = runtime.run_tool
        def fail(*, name, **kwargs):
            if name == "calc_eval":
                raise runtime.MockToolExecutionError("fixture failure", fatal=True)
            return original(name=name, **kwargs)
        with self.client(fail) as client:
            source = client.post(f"/api/tasks/{self.parent}/reruns", json={"user_input": "rag [calc:2+3]"}).json()["task_id"]
            settings = get_settings().model_copy(update={"task_tool_max_concurrent": 1})
            with patch.object(execution, "get_settings", return_value=settings):
                self.assertNotIn("event: done", client.get(f"/api/tasks/{source}/stream").text)
            self.assertEqual(self.task(client, source)["status_normalized"], "failed")
            candidate = self.candidates(client, source)[-1]
            self.assertEqual(candidate["tool_name"], "calc_eval")
            branch = self.resume(client, source, candidate["step_id"])
            with patch.object(runtime, "run_tool", original):
                self.assertIn("event: done", client.get(f"/api/tasks/{branch}/stream").text)

    def lifecycle_resume(self, timeout=False):
        started, release = Event(), Event()
        original = runtime.run_tool
        with self.client() as client:
            source = self.source(client, "[calc:2+3]")
            branch = self.resume(client, source, self.candidates(client, source)[-1]["step_id"])
            def runner(*, name, **kwargs):
                if name == "calc_eval":
                    started.set()
                    release.wait(4)
                return original(name=name, **kwargs)
            settings = get_settings().model_copy(update={"task_timeout_sec": 1.0 if timeout else 30.0})
            with patch.object(runtime, "run_tool", runner), patch.object(execution, "get_settings", return_value=settings):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(client.get, f"/api/tasks/{branch}/stream")
                    try:
                        self.assertTrue(started.wait(3))
                        if timeout:
                            # The serial call checks the task deadline after it finishes.
                            self.assertFalse(release.wait(1.1))
                        else:
                            self.assertEqual(client.post(f"/api/tasks/{branch}/cancel").status_code, 200)
                    finally:
                        release.set()
                    response = future.result(timeout=5)
            expected = "timed_out" if timeout else "cancelled"
            self.assertEqual(self.task(client, branch)["status_normalized"], expected, response.text)
            self.assertNotIn("event: done", response.text)
            self.assertFalse(any(step["meta"].get("step_type") == "final_answer" for step in self.steps(client, branch)))
            snapshot = self.task(client, branch)
            client.get(f"/api/tasks/{branch}/stream")
            self.assertEqual(self.task(client, branch), snapshot)

    def test_cancel_running_resume_does_not_complete_or_restart(self):
        self.lifecycle_resume()

    def test_timeout_running_resume_does_not_complete_or_restart(self):
        self.lifecycle_resume(timeout=True)

if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(TaskCheckpointPostgresTests, settings={"TASK_TOOL_MAX_CONCURRENT": "2"}))
