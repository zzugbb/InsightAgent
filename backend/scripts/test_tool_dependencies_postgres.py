#!/usr/bin/env python3
"""Dependency planner and lifecycle through real HTTP/Trace with isolated PostgreSQL; no remote LLM."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from threading import Barrier, Event, Lock
import unittest
from unittest.mock import patch

from task_postgres_fixture import run_isolated_postgres
from test_task_parallel_postgres import TaskParallelPostgresTests
from app.config import get_settings
from app.db import get_db_connection
from app.providers.base import ProviderResponse
from app.providers.mock_provider import MockLLMProvider
from app.services import chat_persistence_service as persistence
from app.services import tool_runtime as runtime


def calc(node_id, expression="2+3", *, depends_on=(), binding=None):
    node = {"id": node_id, "name": "calc_eval", "input": {"expression": expression},
            "depends_on": list(depends_on)}
    if binding is not None:
        node["input_bindings"] = {"expression": binding}
    return node


def ref(*, path=None, template="{value} * 2"):
    return {"node": "root", "path": ["result"] if path is None else path, "template": template}


class OfflineDependencyProvider(MockLLMProvider):
    def __init__(self, plan):
        super().__init__(provider="offline-fixture")
        self.plan, self.planned = plan, False

    def generate(self, prompt):
        if not self.planned:
            self.planned = True
            return ProviderResponse(content=json.dumps({"tools": self.plan}), model=self.model, provider=self.provider)
        return super().generate(prompt)


class ToolDependenciesPostgresTests(unittest.TestCase):
    setUp = TaskParallelPostgresTests.setUp
    create = TaskParallelPostgresTests.create
    task = TaskParallelPostgresTests.task
    steps = TaskParallelPostgresTests.steps

    @contextmanager
    def client(self, plan, runner=None):
        with patch("app.services.chat_execution_service.get_llm_provider", return_value=OfflineDependencyProvider(plan)), \
             TaskParallelPostgresTests.client(self, runner) as client:
            yield client

    def test_chain_repeated_calculator_query_binding_trace_delta_and_exports(self):
        plan = [calc("root"), calc("scaled", binding=ref()),
                {"id": "search", "name": "task_retrieve", "depends_on": [],
                 "input": {"query": "fixture", "knowledge_base_id": "default"},
                 "input_bindings": {"query": {"node": "scaled", "path": ["result"], "template": "value {value}"}}}]
        original, calls = runtime.run_tool, []
        def runner(**kwargs):
            calls.append(kwargs)
            return original(**kwargs)
        with self.client(plan, runner) as client:
            child = self.create(client)
            stream = client.get(f"/api/tasks/{child}/stream")
            self.assertIn("event: done", stream.text)
            self.assertEqual(self.task(client, child)["status_normalized"], "completed")
            steps = self.steps(client, child)
            actions = [step for step in steps if step["meta"].get("plan_node_id")]
            self.assertEqual([step["meta"]["plan_node_id"] for step in actions], ["root", "scaled", "search"])
            self.assertEqual(actions[1]["meta"]["tool"]["input"]["expression"], "5.0 * 2")
            self.assertEqual(actions[2]["meta"]["tool"]["input"]["query"], "value 10.0")
            self.assertEqual(actions[2]["meta"]["depends_on"], ["scaled"])
            self.assertEqual(calls[-1]["tool_input"]["knowledge_base_id"], "default")
            self.assertEqual({call["user_id"] for call in calls}, {"owner"})
            self.assertEqual([step["seq"] for step in steps], sorted({step["seq"] for step in steps}))
            delta = client.get(f"/api/tasks/{child}/trace/delta?after_seq=0&limit=100").json()["steps"]
            exported = client.get(f"/api/tasks/{child}/export/json").json()
            for source in (delta, exported["trace"]["steps"]):
                self.assertEqual([(step["id"], step["seq"], step["meta"].get("plan_node_id"), step["meta"].get("depends_on"))
                                  for step in source],
                                 [(step["id"], step["seq"], step["meta"].get("plan_node_id"), step["meta"].get("depends_on"))
                                  for step in steps])
            self.assertEqual(exported["version"], "1.0")
            self.assertEqual(client.get(f"/api/tasks/{child}/export/markdown").status_code, 200)
            self.assertIn("10", steps[-1]["content"])

    def test_ready_fanout_overlaps_after_root_and_keeps_trace_order(self):
        barrier, original, calls = Barrier(2), runtime.run_tool, []
        def runner(**kwargs):
            expression = kwargs["tool_input"].get("expression")
            calls.append(expression)
            if expression in {"5.0 * 2", "5.0 * 3"}:
                self.assertIn("2+3", calls)
                barrier.wait(timeout=3)
            return original(**kwargs)
        plan = [calc("right", binding=ref(template="{value} * 3")), calc("root"), calc("left", binding=ref())]
        with self.client(plan, runner) as client:
            child = self.create(client)
            self.assertIn("event: done", client.get(f"/api/tasks/{child}/stream").text)
            actions = [step for step in self.steps(client, child) if step["meta"].get("plan_node_id")]
            self.assertEqual([step["meta"]["plan_node_id"] for step in actions], ["root", "right", "left"])
            parallel = [step for step in actions if step["meta"].get("execution_mode") == "parallel"]
            self.assertEqual(len(parallel), 2)
            self.assertEqual(len({step["meta"]["parallel_group_id"] for step in parallel}), 1)

    def test_invalid_graph_fails_before_tools_with_fixed_sse_and_audit(self):
        calls = []
        with self.client([calc("root", depends_on=["private-fixture-reference"])], lambda **kw: calls.append(kw)) as client:
            child = self.create(client)
            stream = client.get(f"/api/tasks/{child}/stream")
            self.assertIn("tool_dependency_plan_invalid", stream.text)
            self.assertNotIn("private-fixture-reference", stream.text)
            self.assertEqual(self.task(client, child)["status_normalized"], "failed")
            self.assertEqual(calls, [])
            self.assertEqual(len(persistence.get_task_messages(child, "owner")), 1)
            with get_db_connection() as connection:
                audit = connection.execute("SELECT * FROM audit_logs WHERE event_type = 'task_failed'").fetchall()
            self.assertTrue(audit)
            self.assertNotIn("private-fixture-reference", str(audit))

    def test_missing_projected_result_stops_dependent_and_preserves_upstream_trace(self):
        original, calls = runtime.run_tool, []
        def runner(**kwargs):
            calls.append(kwargs["tool_input"].get("expression"))
            return original(**kwargs)
        with self.client([calc("root"), calc("child", binding=ref(path=["raw-secret"]))], runner) as client:
            child = self.create(client)
            stream = client.get(f"/api/tasks/{child}/stream")
            self.assertIn("tool_dependency_input_unavailable", stream.text)
            self.assertNotIn("raw-secret", stream.text)
            self.assertEqual(self.task(client, child)["status_normalized"], "failed")
            self.assertEqual(calls, [None, "2+3"])
            self.assertEqual([step["meta"]["plan_node_id"] for step in self.steps(client, child)
                              if step["meta"].get("plan_node_id")], ["root"])
            self.assertEqual(len(persistence.get_task_messages(child, "owner")), 1)

    def test_serial_switch_retry_only_upstream_then_binds_success(self):
        original, calls = runtime.run_tool, []
        def runner(*, attempt, **kwargs):
            expression = kwargs["tool_input"].get("expression")
            calls.append((expression, attempt))
            if expression == "2+3" and attempt == 0:
                raise runtime.MockToolExecutionError("retry fixture", fatal=False)
            return original(attempt=attempt, **kwargs)
        with patch.dict(os.environ, {"TASK_TOOL_MAX_CONCURRENT": "1"}):
            get_settings.cache_clear()
            try:
                with self.client([calc("root"), calc("child", binding=ref())], runner) as client:
                    child = self.create(client)
                    self.assertIn("event: done", client.get(f"/api/tasks/{child}/stream").text)
                    self.assertEqual(calls, [(None, 0), ("2+3", 0), ("2+3", 1), ("5.0 * 2", 0)])
                    self.assertFalse(any("execution_mode" in step["meta"] for step in self.steps(client, child)))
            finally:
                get_settings.cache_clear()

    def lifecycle(self, *, timeout=False):
        started, release, finished, lock = Event(), Event(), Event(), Lock()
        entered, exited, calls = [0], [0], []
        original = runtime.run_tool
        def runner(**kwargs):
            expression = kwargs["tool_input"].get("expression")
            calls.append(expression)
            if expression in {"2+3", "3+4"}:
                with lock:
                    entered[0] += 1
                    if entered[0] == 2:
                        started.set()
                release.wait(5)
                try:
                    return original(**kwargs)
                finally:
                    with lock:
                        exited[0] += 1
                        if exited[0] == 2:
                            finished.set()
            return original(**kwargs)
        plan = [calc("root"), calc("sibling", "3+4"), calc("child", binding=ref())]
        with patch.dict(os.environ, {"TASK_TIMEOUT_SEC": "1"} if timeout else {}):
            get_settings.cache_clear()
            try:
                with self.client(plan, runner) as client, ThreadPoolExecutor(max_workers=1) as pool:
                    child = self.create(client)
                    response = pool.submit(client.get, f"/api/tasks/{child}/stream")
                    try:
                        self.assertTrue(started.wait(3))
                        if not timeout:
                            self.assertEqual(client.post(f"/api/tasks/{child}/cancel").status_code, 200)
                        stream = response.result(timeout=3)
                        expected = "timeout" if timeout else "cancelled"
                        self.assertIn(f"event: {expected}", stream.text)
                        before = self.steps(client, child)
                        release.set()
                        self.assertTrue(finished.wait(3))
                        self.assertEqual(self.steps(client, child), before)
                        self.assertNotIn("5.0 * 2", calls)
                        self.assertEqual(len(persistence.get_task_messages(child, "owner")), 1)
                    finally:
                        release.set()
                        finished.wait(3)
            finally:
                get_settings.cache_clear()

    def test_cancel_root_window_stops_dependents_and_late_writes(self):
        self.lifecycle()

    def test_timeout_root_window_stops_dependents_and_late_writes(self):
        self.lifecycle(timeout=True)


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(ToolDependenciesPostgresTests, settings={"TASK_TOOL_MAX_CONCURRENT": "2"}))
