#!/usr/bin/env python3
"""Planning wait heartbeats, cancel probes, timeout fallback, and branch reruns (local fixtures only)."""

from concurrent.futures import ThreadPoolExecutor
import json
import re
import time
from threading import Event
import unittest
from unittest.mock import patch
from uuid import uuid4

from task_postgres_fixture import run_isolated_postgres
from test_agent_feedback_postgres import AgentFeedbackPostgresTests, calc
from test_provider_stream_postgres import local_provider
from app.providers.base import ProviderResponse, ProviderUsage
from app.providers.mock_provider import MockLLMProvider
from app.services import chat_persistence_service as persistence
from app.services import task_rerun_service as reruns
from test_agent_feedback_postgres import ConditionalProvider


class SlowInitialPlanningProvider(MockLLMProvider):
    def __init__(self, *, delay_sec: float = 0.0, started: Event | None = None, release: Event | None = None):
        super().__init__(provider="offline-planning-wait-fixture")
        self.delay_sec = delay_sec
        self.started = started
        self.release = release
        self.planning_prompts: list[str] = []
        self.planning_completions = 0

    def generate(self, prompt: str) -> ProviderResponse:
        if not prompt.startswith("You are the Task Planner for InsightAgent."):
            return super().generate(prompt)
        self.planning_prompts.append(prompt)
        if self.started is not None:
            self.started.set()
        if self.release is not None:
            self.release.wait(15)
        if self.delay_sec > 0:
            time.sleep(self.delay_sec)
        self.planning_completions += 1
        return ProviderResponse(
            json.dumps({"tools": [calc("2+3")]}),
            self.model,
            self.provider,
            ProviderUsage(10, 2, 12),
        )


def sse_events(stream_text: str) -> list[tuple[str, float]]:
    events: list[tuple[str, float]] = []
    started = time.monotonic()
    for block in stream_text.split("\n\n"):
        if not block.strip():
            continue
        match = re.match(r"event: (\w+)", block)
        if match:
            events.append((match.group(1), time.monotonic() - started))
    return events


class ProviderPlanningWaitPostgresTests(unittest.TestCase):
    setUp = AgentFeedbackPostgresTests.setUp
    create = AgentFeedbackPostgresTests.create
    task = AgentFeedbackPostgresTests.task
    steps = AgentFeedbackPostgresTests.steps
    client = AgentFeedbackPostgresTests.client

    def test_slow_initial_planning_emits_heartbeat_before_plan_trace(self):
        provider = SlowInitialPlanningProvider(delay_sec=2.6)
        with self.client(provider) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
        events = sse_events(stream)
        trace_idx = next(i for i, (name, _) in enumerate(events) if name == "trace")
        self.assertTrue(any(name == "heartbeat" for name, _ in events[:trace_idx]))
        self.assertIn("event: done", stream)

    def test_cancel_during_initial_planning_aborts_without_tool_steps(self):
        started, release = Event(), Event()
        provider = SlowInitialPlanningProvider(started=started, release=release)
        with self.client(provider) as client, ThreadPoolExecutor(max_workers=1) as pool:
            task = self.create(client)
            response = pool.submit(client.get, f"/api/tasks/{task}/stream")
            self.assertTrue(started.wait(5))
            cancel_started = time.monotonic()
            self.assertEqual(client.post(f"/api/tasks/{task}/cancel").status_code, 200)
            try:
                stream = response.result(timeout=8).text
            finally:
                release.set()
            cancel_elapsed = time.monotonic() - cancel_started
            self.assertIn("event: cancelled", stream)
            self.assertNotIn("event: done", stream)
            self.assertLess(cancel_elapsed, 3.0)
            self.assertEqual(self.task(client, task)["status_normalized"], "cancelled")
            self.assertEqual(self.steps(client, task), [])

    def test_late_planning_return_after_cancel_does_not_mutate_task(self):
        started, release = Event(), Event()
        provider = SlowInitialPlanningProvider(started=started, release=release)
        with self.client(provider) as client, ThreadPoolExecutor(max_workers=1) as pool:
            task = self.create(client)
            response = pool.submit(client.get, f"/api/tasks/{task}/stream")
            self.assertTrue(started.wait(5))
            self.assertEqual(client.post(f"/api/tasks/{task}/cancel").status_code, 200)
            stream = response.result(timeout=8).text
            self.assertIn("event: cancelled", stream)
            snapshot = self.task(client, task)
            trace_before = self.steps(client, task)
            messages_before = persistence.get_task_messages(task, "owner")
            release.set()
            for _ in range(30):
                if provider.planning_completions >= 1:
                    break
                time.sleep(0.1)
            self.assertEqual(provider.planning_completions, 1)
            time.sleep(0.2)
            after = self.task(client, task)
            self.assertEqual(after["status_normalized"], "cancelled")
            self.assertEqual(snapshot["status_normalized"], after["status_normalized"])
            self.assertEqual(snapshot.get("usage_json"), after.get("usage_json"))
            self.assertIsNone(after.get("usage_json"))
            self.assertEqual(self.steps(client, task), trace_before)
            self.assertEqual(trace_before, [])
            self.assertEqual(persistence.get_task_messages(task, "owner"), messages_before)
            self.assertEqual([row["role"] for row in messages_before], ["user"])

    def test_http_planning_timeout_keeps_rule_fallback_trace_and_usage(self):
        with local_provider("planning_empty_initial") as (provider, calls), self.client(provider) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            result = self.task(client, task)
            self.assertIn("event: done", stream)
            self.assertEqual(result["status_normalized"], "completed")
            self.assertEqual(calls, [False, True])
            usage = json.loads(result["usage_json"])
            self.assertEqual(usage.get("planning_total_tokens"), 12)
            steps = self.steps(client, task)
            self.assertTrue(steps[0]["meta"].get("planning_provider_attempted"))
            self.assertFalse(steps[0]["meta"].get("planning_provider_used"))

    def test_branch_rerun_after_failed_planning_task(self):
        with self.client(ConditionalProvider(stop="error")) as client:
            task = self.create(client)
            self.assertIn("event: error", client.get(f"/api/tasks/{task}/stream").text)
            self.assertEqual(self.task(client, task)["status_normalized"], "failed")
        branch = reruns.create_task_rerun(
            user_id="owner",
            parent_task_id=task,
            user_input="calculate 4+5",
            idempotency_key=str(uuid4()),
        )
        with self.client(SlowInitialPlanningProvider()) as client, patch(
            "app.services.chat_execution_service.try_append_task_memory"
        ):
            child_stream = client.get(f"/api/tasks/{branch['task_id']}/stream").text
            self.assertIn("event: done", child_stream)
            self.assertEqual(self.task(client, branch["task_id"])["status_normalized"], "completed")


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(ProviderPlanningWaitPostgresTests))
