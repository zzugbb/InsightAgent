#!/usr/bin/env python3
"""Real task/SSE/persistence with local conditional planning, never a remote model."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from threading import Event
import unittest
from unittest.mock import patch

from task_postgres_fixture import run_isolated_postgres
from test_task_parallel_postgres import TaskParallelPostgresTests
from app.config import get_settings
from app.providers.base import ProviderCallError, ProviderResponse, ProviderUsage
from app.providers.mock_provider import MockLLMProvider
from app.services import task_queue_service as queue


def calc(expression):
    return {"name": "calc_eval", "input": {"expression": expression}}


class ConditionalProvider(MockLLMProvider):
    def __init__(self, *, stop="empty", started=None, release=None):
        super().__init__(provider="offline-feedback-fixture")
        self.planning_prompts = []
        self.stop, self.started, self.release = stop, started, release

    def generate(self, prompt):
        if not prompt.startswith("You are the Task Planner for InsightAgent."):
            result = super().generate(prompt)
            result.usage = ProviderUsage(30, 5, 35)
            return result
        self.planning_prompts.append(prompt)
        count = len(self.planning_prompts)
        if count == 1:
            tools = [calc("2+3")]
        else:
            if self.started is not None:
                self.started.set()
                self.release.wait(5)
            if self.stop == "error":
                raise ProviderCallError(code="rate_limit", user_message="Fixture provider unavailable.", status_code=429)
            if self.stop == "invalid":
                return ProviderResponse("not a tool decision", self.model, self.provider, ProviderUsage(10, 2, 12))
            if self.stop == "repeat":
                tools = [calc("2+3")]
            elif count == 2:
                # The next action changes if the actual first observation is different.
                observations = json.loads(prompt.split("Completed tool observations (JSON):\n", 1)[1])
                tools = [calc("5*2" if any('"result": 5' in text for text in observations) else "4*2")]
            else:
                tools = []
        return ProviderResponse(json.dumps({"tools": tools}), self.model, self.provider, ProviderUsage(10, 2, 12))


class AgentFeedbackPostgresTests(unittest.TestCase):
    setUp = TaskParallelPostgresTests.setUp
    create = TaskParallelPostgresTests.create
    task = TaskParallelPostgresTests.task
    steps = TaskParallelPostgresTests.steps

    @contextmanager
    def client(self, provider):
        with patch("app.services.chat_execution_service.get_llm_provider", return_value=provider), \
             TaskParallelPostgresTests.client(self) as client:
            yield client

    def test_observation_changes_next_action_and_usage_trace_exports_agree(self):
        provider = ConditionalProvider()
        with self.client(provider) as client:
            task = self.create(client)
            self.assertIn("event: done", client.get(f"/api/tasks/{task}/stream").text)
            steps = self.steps(client, task)
            actions = [step for step in steps if step.get("type") == "action" and (step["meta"].get("tool") or {}).get("name") == "calc_eval"]
            self.assertEqual([step["meta"]["tool"]["input"]["expression"] for step in actions], ["2+3", "5*2"])
            self.assertEqual([step["meta"]["agent_round"] for step in actions], [1, 2])
            decisions = [step for step in steps if step["meta"].get("label") == "agent_decision"]
            self.assertEqual([step["meta"]["agent_decision"] for step in decisions], ["continue", "no_tools"])
            self.assertIn(actions[0]["id"], decisions[0]["meta"]["agent_from_step_ids"])
            self.assertEqual(len(provider.planning_prompts), 3)
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertEqual(usage["planning_total_tokens"], 36)
            self.assertEqual(usage["overall_total_tokens"], 71)
            self.assertEqual([step["seq"] for step in steps], sorted({step["seq"] for step in steps}))
            delta = client.get(f"/api/tasks/{task}/trace/delta?after_seq=0&limit=100").json()["steps"]
            export = client.get(f"/api/tasks/{task}/export/json").json()
            self.assertEqual(delta, steps)
            self.assertEqual(export["trace"]["steps"], steps)
            self.assertEqual(export["version"], "1.0")
            self.assertEqual(client.get(f"/api/tasks/{task}/export/markdown").status_code, 200)
            self.assertFalse(any("checkpoint_plan" in step["meta"] for step in steps))

    def test_stop_reasons_do_not_repeat_tools(self):
        for mode, reason in (("repeat", "repeated_action"), ("invalid", "invalid_decision")):
            with self.subTest(mode=mode), self.client(ConditionalProvider(stop=mode)) as client:
                task = self.create(client)
                self.assertIn("event: done", client.get(f"/api/tasks/{task}/stream").text)
                steps = self.steps(client, task)
                self.assertEqual(sum((step["meta"].get("tool") or {}).get("name") == "calc_eval" for step in steps), 1)
                self.assertEqual([step["meta"]["agent_decision"] for step in steps if "agent_decision" in step["meta"]], [reason])

    def test_round_limit_stops_without_another_model_decision(self):
        with patch.dict(os.environ, {"AGENT_MAX_ROUNDS": "2"}):
            get_settings.cache_clear()
            try:
                provider = ConditionalProvider()
                with self.client(provider) as client:
                    task = self.create(client)
                    self.assertIn("event: done", client.get(f"/api/tasks/{task}/stream").text)
                    self.assertEqual(len(provider.planning_prompts), 2)
                    self.assertEqual([step["meta"]["agent_decision"] for step in self.steps(client, task) if "agent_decision" in step["meta"]], ["continue", "max_rounds"])
            finally:
                get_settings.cache_clear()

    def test_single_round_setting_keeps_checkpoint_eligibility(self):
        with patch.dict(os.environ, {"AGENT_MAX_ROUNDS": "1"}):
            get_settings.cache_clear()
            try:
                provider = ConditionalProvider()
                with self.client(provider) as client:
                    task = self.create(client)
                    self.assertIn("event: done", client.get(f"/api/tasks/{task}/stream").text)
                    self.assertEqual(len(provider.planning_prompts), 1)
                    self.assertTrue(any("checkpoint_plan" in step["meta"] for step in self.steps(client, task)))
            finally:
                get_settings.cache_clear()

    def test_feedback_provider_error_fails_task_and_releases_slot(self):
        with self.client(ConditionalProvider(stop="error")) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assertIn("event: error", stream)
            self.assertNotIn("event: done", stream)
            self.assertEqual(self.task(client, task)["status_normalized"], "failed")
            self.assertEqual(queue.get_task_queue_snapshot(max_concurrent=32)["active_count"], 0)

    def test_cancel_during_feedback_discards_late_plan(self):
        started, release = Event(), Event()
        provider = ConditionalProvider(started=started, release=release)
        with self.client(provider) as client, ThreadPoolExecutor(max_workers=1) as pool:
            task = self.create(client)
            response = pool.submit(client.get, f"/api/tasks/{task}/stream")
            try:
                self.assertTrue(started.wait(3))
                self.assertEqual(client.post(f"/api/tasks/{task}/cancel").status_code, 200)
                release.set()
                stream = response.result(timeout=3).text
                self.assertIn("event: cancelled", stream)
                self.assertNotIn("event: done", stream)
                self.assertEqual(self.task(client, task)["status_normalized"], "cancelled")
                self.assertEqual(sum((step["meta"].get("tool") or {}).get("name") == "calc_eval" for step in self.steps(client, task)), 1)
                self.assertEqual(queue.get_task_queue_snapshot(max_concurrent=32)["active_count"], 0)
            finally:
                release.set()


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(AgentFeedbackPostgresTests))
