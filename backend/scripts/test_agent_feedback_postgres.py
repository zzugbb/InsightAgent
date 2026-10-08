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


class GraphFeedbackProvider(ConditionalProvider):
    def __init__(self, plans, *, usages=None):
        super().__init__()
        self.plans, self.answer_prompts = plans, []
        self.usages = usages

    def generate(self, prompt):
        if not prompt.startswith("You are the Task Planner for InsightAgent."):
            return super().generate(prompt)
        self.planning_prompts.append(prompt)
        index = len(self.planning_prompts) - 1
        plan = self.plans[index] if index < len(self.plans) else []
        usage = self.usages[index] if self.usages is not None else ProviderUsage(10, 2, 12)
        return ProviderResponse(json.dumps({"tools": plan}), self.model, self.provider, usage)

    def stream_generate(self, prompt):
        self.answer_prompts.append(prompt)
        yield "fixture answer"


def bound_graph(expression, *, template="{value}*2", fanout=False):
    graph = [{**calc(expression), "id": "root", "depends_on": []},
             {**calc("0"), "id": "scaled", "depends_on": ["root"],
              "input_bindings": {"expression": {"node": "root", "path": ["result"], "template": template}}}]
    if fanout:
        graph.insert(1, {**calc("0"), "id": "new_sibling", "depends_on": ["root"],
              "input_bindings": {"expression": {"node": "root", "path": ["result"], "template": "{value}*3"}}})
    return graph


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

    def assert_invalid_graph_usage(self, *, followup=False, usage=ProviderUsage(10, 2, 12)):
        invalid = [{**calc("3*2"), "id": "broken", "depends_on": ["missing"]}]
        plans = [[calc("2+3")], invalid] if followup else [invalid]
        usages = [ProviderUsage(10, 2, 12), usage] if followup else [usage]
        provider = GraphFeedbackProvider(plans, usages=usages)
        with self.client(provider) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assertIn("tool_dependency_plan_invalid", stream)
            self.assertNotIn("event: done", stream)
            result = self.task(client, task)
            self.assertEqual(result["status_normalized"], "failed")
            steps = self.steps(client, task)
            self.assertEqual(sum((step["meta"].get("tool") or {}).get("name") == "calc_eval"
                                 for step in steps), int(followup))
            self.assertEqual(provider.answer_prompts, [])
            self.assertEqual(queue.get_task_queue_snapshot(max_concurrent=32)["active_count"], 0)
            self.assertEqual(client.get(f"/api/tasks/{task}/trace/delta?after_seq=0&limit=100").json()["steps"], steps)
            exported = client.get(f"/api/tasks/{task}/export/json").json()
            self.assertEqual(exported["trace"]["steps"], steps)
            payload = json.loads(result["usage_json"]) if result["usage_json"] else None
            return payload

    def test_initial_invalid_graph_keeps_returned_planning_usage(self):
        payload = self.assert_invalid_graph_usage()
        self.assertEqual(payload["planning_total_tokens"], 12)
        self.assertEqual(payload["planning_provider_total_tokens"], 12)
        self.assertEqual(payload["overall_total_tokens"], 12)
        self.assertNotIn("completion_tokens", payload)

    def test_feedback_invalid_graph_counts_both_planning_calls_once(self):
        payload = self.assert_invalid_graph_usage(followup=True)
        self.assertEqual(payload["planning_prompt_tokens"], 20)
        self.assertEqual(payload["planning_completion_tokens"], 4)
        self.assertEqual(payload["planning_total_tokens"], 24)
        self.assertEqual(payload["planning_provider_total_tokens"], 24)
        self.assertEqual(payload["overall_total_tokens"], 24)
        self.assertNotIn("completion_tokens", payload)

    def test_invalid_graph_partial_or_missing_usage_never_estimates_consumption(self):
        for followup in (False, True):
            with self.subTest(followup=followup):
                payload = self.assert_invalid_graph_usage(followup=followup, usage=ProviderUsage(7, None, 9))
                self.assertEqual(payload["planning_prompt_tokens"], 17 if followup else 7)
                self.assertIsNone(payload["planning_completion_tokens"])
                self.assertIsNone(payload["planning_total_tokens"])
                self.assertIsNone(payload["planning_cost_estimate"])
                self.assertEqual(payload["planning_provider_total_tokens"], 21 if followup else 9)
                self.assertIsNone(payload["overall_total_tokens"])
        self.assertIsNone(self.assert_invalid_graph_usage(usage=None))
        payload = self.assert_invalid_graph_usage(followup=True, usage=None)
        self.assertEqual(payload["planning_total_tokens"], 12)

    def assert_graph_feedback(self, plans, expressions, reason, *, decision_calls=2):
        provider, calls = GraphFeedbackProvider(plans), []
        from app.services import tool_runtime as runtime
        runner = runtime.run_tool

        def capture(**kwargs):
            if kwargs["name"] == "calc_eval":
                calls.append(kwargs["tool_input"]["expression"])
            return runner(**kwargs)

        with patch.object(runtime, "run_tool", side_effect=capture), self.client(provider) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assertIn("event: done", stream)
            steps = self.steps(client, task)
            self.assertEqual(calls, expressions)
            actions = [step for step in steps if step.get("type") == "action"
                       and (step["meta"].get("tool") or {}).get("name") == "calc_eval"]
            self.assertEqual([step["meta"]["tool"]["input"]["expression"] for step in actions], expressions)
            self.assertEqual(len(provider.planning_prompts), decision_calls)
            self.assertEqual(steps[-1]["meta"]["agent_stop_reason"], reason)
            self.assertIn(f"Runtime tool-stage stop reason: {reason}", provider.answer_prompts[-1])
            self.assertEqual([step["seq"] for step in steps], sorted({step["seq"] for step in steps}))
            self.assertEqual(client.get(f"/api/tasks/{task}/trace/delta?after_seq=0&limit=100").json()["steps"], steps)
            self.assertEqual(client.get(f"/api/tasks/{task}/export/json").json()["trace"]["steps"], steps)
            self.assertEqual(client.get(f"/api/tasks/{task}/export/markdown").status_code, 200)
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertEqual(usage["planning_total_tokens"], decision_calls * 12)

    def test_bound_action_cannot_be_replayed_as_flat_input(self):
        self.assert_graph_feedback([bound_graph("2+3"), [calc("5.0*2")]], ["2+3", "5.0*2"], "repeated_action")

    def test_bound_action_is_checked_after_new_root_without_an_extra_provider_decision(self):
        self.assert_graph_feedback([[calc("5.0*2")], bound_graph("3+2")], ["5.0*2", "3+2"], "repeated_action")

    def test_new_upstream_result_can_use_the_same_binding_template(self):
        self.assert_graph_feedback([bound_graph("2+3"), bound_graph("3+4")],
                                   ["2+3", "5.0*2", "3+4", "7.0*2"], "no_tools", decision_calls=3)

    def test_parallel_batch_repeat_is_rejected_before_any_sibling_starts(self):
        with patch.dict(os.environ, {"TASK_TOOL_MAX_CONCURRENT": "2"}):
            get_settings.cache_clear()
            try:
                self.assert_graph_feedback([[calc("5.0*2")], bound_graph("3+2", fanout=True)],
                                           ["5.0*2", "3+2"], "repeated_action")
            finally:
                get_settings.cache_clear()

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
