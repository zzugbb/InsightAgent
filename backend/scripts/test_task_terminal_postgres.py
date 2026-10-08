#!/usr/bin/env python3
"""Final-response deadline boundaries and failed usage in isolated PostgreSQL."""

import json
import unittest
from unittest.mock import patch

from task_postgres_fixture import run_isolated_postgres
from test_agent_feedback_postgres import AgentFeedbackPostgresTests, ConditionalProvider
from test_usage_accounting_postgres import UsageAccountingPostgresTests
from test_provider_stream_postgres import local_provider
from test_task_completion_postgres import reject_assistant_insert
from app.providers.base import ProviderCallError, ProviderUsage
from app.services import chat_persistence_service as persistence
from app.services import task_queue_service as queue
from app.services import tool_runtime as runtime


class TerminalProvider(ConditionalProvider):
    def __init__(self, *, clock=None, fallback=False, known_usage=False, fail=False):
        super().__init__()
        self.clock, self.fallback = clock, fallback
        self.known_usage, self.fail = known_usage, fail
        self.tail = None
        self.stream_calls = 0
        self._last_usage = None

    def stream_generate(self, prompt):
        self.stream_calls += 1
        self._last_usage = None
        if self.fallback:
            return
        yield "fixture partial answer"
        if self.known_usage:
            self._last_usage = ProviderUsage(5, 2, 7)
        if self.clock is not None:
            self.clock[0] += 100_000
        if self.tail is not None:
            self.tail()
        if self.fail:
            raise ProviderCallError(code="fixture_interrupted", user_message="Fixture stream interrupted.")

    def generate(self, prompt):
        result = super().generate(prompt)
        if not prompt.startswith("You are the Task Planner for InsightAgent.") and self.clock is not None:
            self.clock[0] += 100_000
        return result


class TaskTerminalPostgresTests(unittest.TestCase):
    setUp = AgentFeedbackPostgresTests.setUp
    create = AgentFeedbackPostgresTests.create
    task = AgentFeedbackPostgresTests.task
    steps = AgentFeedbackPostgresTests.steps
    client = AgentFeedbackPostgresTests.client
    assert_views = UsageAccountingPostgresTests.assert_views

    def assert_terminal(self, client, task, stream, *, status, event):
        self.assertEqual(self.task(client, task)["status_normalized"], status)
        self.assertIn(f"event: {event}", stream)
        self.assertNotIn("event: done", stream)
        self.assertEqual([m["role"] for m in persistence.get_task_messages(task, "owner")], ["user"])
        self.assertEqual(queue.get_task_queue_snapshot(max_concurrent=32)["active_count"], 0)
        steps = self.steps(client, task)
        self.assertEqual(client.get(f"/api/tasks/{task}/trace/delta?after_seq=0&limit=100").json()["steps"], steps)
        self.assertEqual(client.get(f"/api/tasks/{task}/export/json").json()["trace"]["steps"], steps)

    def test_deadline_after_last_text_before_stream_end_never_completes(self):
        clock = [100.0]
        provider = TerminalProvider(clock=clock, known_usage=True)
        with self.client(provider) as client, patch("app.services.chat_execution_service.monotonic", side_effect=lambda: clock[0]):
            task = self.create(client)
            with patch("app.services.chat_execution_service.try_append_task_memory") as memory:
                stream = client.get(f"/api/tasks/{task}/stream").text
            memory.assert_not_called()
            self.assert_terminal(client, task, stream, status="timed_out", event="timeout")
            self.assertEqual(self.steps(client, task)[-1]["content"], "fixture partial answer")
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertEqual(usage["overall_total_tokens"], 43)
            self.assert_views(client, task, usage, "provider")

    def test_deadline_during_empty_stream_fallback_never_completes(self):
        clock = [100.0]
        with self.client(TerminalProvider(clock=clock, fallback=True)) as client, \
             patch("app.services.chat_execution_service.monotonic", side_effect=lambda: clock[0]):
            task = self.create(client)
            with patch("app.services.chat_execution_service.try_append_task_memory") as memory:
                stream = client.get(f"/api/tasks/{task}/stream").text
            memory.assert_not_called()
            self.assert_terminal(client, task, stream, status="timed_out", event="timeout")
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertEqual(usage["overall_total_tokens"], 71)

    def test_cancel_during_stream_tail_preserves_cancel_and_never_writes_answer(self):
        provider = TerminalProvider(known_usage=True)
        with self.client(provider) as client:
            task = self.create(client)
            def cancel():
                self.assertEqual(client.post(f"/api/tasks/{task}/cancel").status_code, 200)
            provider.tail = cancel
            with patch("app.services.chat_execution_service.try_append_task_memory") as memory:
                stream = client.get(f"/api/tasks/{task}/stream").text
            memory.assert_not_called()
            self.assert_terminal(client, task, stream, status="cancelled", event="cancelled")

    def test_deadline_during_final_trace_save_is_checked_before_success_transaction(self):
        clock = [100.0]
        original = persistence.update_task_trace_steps

        def save(task, steps, user):
            result = original(task, steps, user)
            if steps and steps[-1]["meta"].get("step_type") == "final_answer" and steps[-1]["meta"].get("tokens") is not None:
                clock[0] += 100_000
            return result

        with self.client(TerminalProvider(known_usage=True)) as client, \
             patch("app.services.chat_execution_service.monotonic", side_effect=lambda: clock[0]), \
             patch("app.services.chat_execution_service.update_task_trace_steps", side_effect=save):
            task = self.create(client)
            with patch("app.services.chat_execution_service.try_append_task_memory") as memory:
                stream = client.get(f"/api/tasks/{task}/stream").text
            memory.assert_not_called()
            self.assert_terminal(client, task, stream, status="timed_out", event="timeout")
            self.assertEqual(json.loads(self.task(client, task)["usage_json"])["overall_total_tokens"], 43)

    def test_failed_final_without_usage_keeps_planning_and_unknown_final(self):
        with self.client(TerminalProvider(fail=True)) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assert_terminal(client, task, stream, status="failed", event="error")
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertIsNone(usage.get("prompt_tokens"))
            self.assertIsNone(usage.get("completion_tokens"))
            self.assertEqual(usage["overall_total_tokens"], 36)
            self.assert_views(client, task, usage, "provider")

    def test_failed_decision_keeps_previous_planning_without_reusing_last_call_usage(self):
        with self.client(ConditionalProvider(stop="error")) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assert_terminal(client, task, stream, status="failed", event="error")
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertEqual(usage["overall_total_tokens"], 12)
            self.assertNotIn("prompt_tokens", usage)
            self.assert_views(client, task, usage, "provider")

    def test_failed_tool_keeps_initial_planning_usage(self):
        original = runtime.run_tool

        def runner(*, name, **kwargs):
            if name == "calc_eval":
                raise runtime.MockToolExecutionError("fatal calculation fixture", fatal=True)
            return original(name=name, **kwargs)

        with self.client(ConditionalProvider()) as client, patch.object(runtime, "run_tool", side_effect=runner):
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assert_terminal(client, task, stream, status="failed", event="error")
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertEqual(usage["overall_total_tokens"], 12)
            self.assert_views(client, task, usage, "provider")

    def test_deadline_during_feedback_keeps_returned_usage_without_late_action(self):
        clock = [100.0]

        class LateDecisionProvider(ConditionalProvider):
            def generate(self, prompt):
                result = super().generate(prompt)
                if len(self.planning_prompts) == 2:
                    clock[0] += 100_000
                return result

        with self.client(LateDecisionProvider()) as client, \
             patch("app.services.chat_execution_service.monotonic", side_effect=lambda: clock[0]):
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assert_terminal(client, task, stream, status="timed_out", event="timeout")
            steps = self.steps(client, task)
            self.assertEqual(sum((step["meta"].get("tool") or {}).get("name") == "calc_eval" for step in steps), 1)
            self.assertFalse(any("agent_decision" in step["meta"] for step in steps))
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertEqual(usage["overall_total_tokens"], 24)
            self.assert_views(client, task, usage, "provider")

    def test_real_http_usage_before_unfinished_eof_is_kept_without_replay(self):
        with local_provider("partial_usage") as (provider, calls), self.client(provider) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assert_terminal(client, task, stream, status="failed", event="error")
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertEqual(usage["total_tokens"], 7)
            self.assertEqual(usage["prompt_tokens_source"], "provider")
            self.assert_views(client, task, usage, "mixed")
            self.assertNotIn("event: done", client.get(f"/api/tasks/{task}/stream").text)
            self.assertEqual(calls, [False, True])

    def test_success_write_failure_keeps_completed_call_usage(self):
        with reject_assistant_insert(), self.client(ConditionalProvider()) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assert_terminal(client, task, stream, status="failed", event="error")
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertEqual(usage["overall_total_tokens"], 71)
            self.assert_views(client, task, usage, "provider")


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(TaskTerminalPostgresTests, settings={
        "USAGE_PROMPT_TOKEN_PRICE_PER_1K": "0.001", "USAGE_COMPLETION_TOKEN_PRICE_PER_1K": "0.002",
    }))
