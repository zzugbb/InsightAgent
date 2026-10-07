#!/usr/bin/env python3
"""Real local HTTP reads, task stream/exports and cancellation with isolated PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from threading import Event, Lock
import unittest
from unittest.mock import patch

from task_postgres_fixture import run_isolated_postgres
from test_task_parallel_postgres import TaskParallelPostgresTests
from test_tool_dependencies_postgres import OfflineDependencyProvider
from tool_http_fixture import ReadService
from app.config import get_settings
from app.services import chat_persistence_service as persistence
from app.services import tool_runtime as runtime

PLAN = [{"id": name, "name": name, "input": {"expression": "1+2"}, "depends_on": []}
        for name in ("read_a", "read_b")]


class HttpParallelPostgresTests(unittest.TestCase):
    setUp = TaskParallelPostgresTests.setUp
    create = TaskParallelPostgresTests.create
    task = TaskParallelPostgresTests.task
    steps = TaskParallelPostgresTests.steps

    @contextmanager
    def client(self, service, *, plan=None, cap=2, opted=True, method="GET", timeout=120, runner=None):
        env = {"INSIGHT_AGENT_TOOL_REGISTRY_EXTRA_TOOLS_JSON": json.dumps(service.tool_specs(opted=opted, method=method)),
               "TASK_TOOL_MAX_CONCURRENT": str(cap), "TASK_TIMEOUT_SEC": str(timeout)}
        with patch.dict(os.environ, env), \
             patch("app.services.chat_execution_service.get_llm_provider", return_value=OfflineDependencyProvider(plan or PLAN)):
            get_settings.cache_clear()
            try:
                with TaskParallelPostgresTests.client(self, runner) as client:
                    yield client
            finally:
                get_settings.cache_clear()

    def test_actual_http_overlap_identity_trace_delta_exports_and_redaction(self):
        with ReadService(overlap=True) as service, self.client(service) as client:
            child = self.create(client)
            stream = client.get(f"/api/tasks/{child}/stream")
            self.assertIn("event: done", stream.text)
            self.assertEqual(service.max_active, 2)
            self.assertEqual([call["user"] for call in service.calls], ["owner", "owner"])
            self.assertTrue(all(call["authorization"] == "Bearer request-fixture-secret" for call in service.calls))
            steps = self.steps(client, child)
            parallel = [step for step in steps if step["meta"].get("execution_mode") == "parallel"]
            self.assertEqual([step["meta"]["plan_node_id"] for step in parallel], ["read_a", "read_b"])
            self.assertEqual(len({step["meta"]["parallel_group_id"] for step in parallel}), 1)
            self.assertEqual([step["seq"] for step in steps], sorted({step["seq"] for step in steps}))
            exported = client.get(f"/api/tasks/{child}/export/json").json()
            delta = client.get(f"/api/tasks/{child}/trace/delta?after_seq=0&limit=100").json()["steps"]
            self.assertEqual([step["id"] for step in delta], [step["id"] for step in steps])
            self.assertEqual([step["meta"].get("parallel_group_id") for step in exported["trace"]["steps"]],
                             [step["meta"].get("parallel_group_id") for step in steps])
            markdown = client.get(f"/api/tasks/{child}/export/markdown").text
            for secret in ("request-fixture-secret", "response-fixture-secret"):
                self.assertNotIn(secret, str((stream.text, exported, markdown, delta)))
            self.assertEqual(self.task(client, child)["status_normalized"], "completed")

    def test_serial_switch_and_unopted_get_both_preserve_serial_execution(self):
        for cap, opted in ((1, True), (2, False)):
            with self.subTest(cap=cap, opted=opted), ReadService() as service, self.client(service, cap=cap, opted=opted) as client:
                child = self.create(client)
                self.assertIn("event: done", client.get(f"/api/tasks/{child}/stream").text)
                self.assertEqual(service.max_active, 1)
                self.assertEqual([call["path"] for call in service.calls], ["/read_a", "/read_b"])
                self.assertFalse(any("execution_mode" in step["meta"] for step in self.steps(client, child)))

    def test_http_503_retries_only_failed_tool(self):
        with ReadService(retry=True) as service, self.client(service) as client:
            child = self.create(client)
            self.assertIn("event: done", client.get(f"/api/tasks/{child}/stream").text)
            self.assertEqual(sum(call["path"] == "/read_a" for call in service.calls), 2)
            self.assertEqual(sum(call["path"] == "/read_b" for call in service.calls), 1)

    def test_projected_http_result_binds_downstream_calculator(self):
        plan = [*PLAN, {"id": "scaled", "name": "calc_eval", "input": {},
                       "input_bindings": {"expression": {"node": "read_a", "path": ["result"], "template": "{value} * 2"}}}]
        with ReadService(overlap=True) as service, self.client(service, plan=plan) as client:
            child = self.create(client)
            self.assertIn("event: done", client.get(f"/api/tasks/{child}/stream").text)
            steps = [step for step in self.steps(client, child) if step["meta"].get("plan_node_id")]
            self.assertEqual([step["meta"]["plan_node_id"] for step in steps], ["read_a", "read_b", "scaled"])
            self.assertEqual(steps[-1]["meta"]["tool"]["input"]["expression"], "5 * 2")
            self.assertEqual(steps[-1]["meta"]["tool"]["output_preview"]["result"], 10)

    def lifecycle(self, *, timeout=False):
        returned, lock, count = Event(), Lock(), [0]
        original = runtime.run_tool
        def runner(**kwargs):
            try:
                return original(**kwargs)
            finally:
                if kwargs["name"] in {"read_a", "read_b"}:
                    with lock:
                        count[0] += 1
                        if count[0] == 2:
                            returned.set()
        plan = [*PLAN, {"id": "child", "name": "calc_eval", "input": {"expression": "8+9"}, "depends_on": ["read_a"]}]
        with ReadService(blocked=True) as service, self.client(service, plan=plan, timeout=1 if timeout else 120,
                                                               runner=runner) as client, ThreadPoolExecutor(max_workers=1) as pool:
            child = self.create(client)
            response = pool.submit(client.get, f"/api/tasks/{child}/stream")
            try:
                self.assertTrue(service.started.wait(3))
                if not timeout:
                    self.assertEqual(client.post(f"/api/tasks/{child}/cancel").status_code, 200)
                stream = response.result(timeout=3)
                event = "timeout" if timeout else "cancelled"
                self.assertIn(f"event: {event}", stream.text)
                self.assertNotIn("event: done", stream.text)
                before = self.steps(client, child)
                service.release.set()
                self.assertTrue(returned.wait(3))
                self.assertEqual(self.steps(client, child), before)
                self.assertFalse(any(step["meta"].get("plan_node_id") == "child" for step in before))
                self.assertEqual(len(persistence.get_task_messages(child, "owner")), 1)
            finally:
                service.release.set()
                returned.wait(3)

    def test_cancel_returns_before_inflight_http_and_drops_late_results(self):
        self.lifecycle()

    def test_timeout_returns_before_inflight_http_and_stops_dependents(self):
        self.lifecycle(timeout=True)

    def test_unsafe_opt_in_rejected_without_http_request(self):
        with ReadService() as service, self.client(service, method="POST") as client:
            child = self.create(client)
            stream = client.get(f"/api/tasks/{child}/stream")
            self.assertNotIn("event: done", stream.text)
            self.assertEqual(self.task(client, child)["status_normalized"], "failed")
            self.assertEqual(service.calls, [])


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(HttpParallelPostgresTests, settings={"TASK_TOOL_MAX_CONCURRENT": "2"}))
