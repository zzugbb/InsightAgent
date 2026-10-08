#!/usr/bin/env python3
"""Tool-stop prompts and final completion metadata through real task persistence."""

import json
import os
import unittest
from unittest.mock import patch

from task_postgres_fixture import run_isolated_postgres
from test_agent_feedback_postgres import AgentFeedbackPostgresTests, ConditionalProvider
from test_provider_stream_postgres import local_provider
from app.config import get_settings
from app.db import get_db_connection
from app.services import chat_persistence_service as persistence
from app.services.conversation_context import load_conversation_context


class CapturingProvider(ConditionalProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.answer_prompts = []

    def stream_generate(self, prompt):
        self.answer_prompts.append(prompt)
        yield from super().stream_generate(prompt)


class AnswerCompletionPostgresTests(unittest.TestCase):
    setUp = AgentFeedbackPostgresTests.setUp
    create = AgentFeedbackPostgresTests.create
    task = AgentFeedbackPostgresTests.task
    steps = AgentFeedbackPostgresTests.steps
    client = AgentFeedbackPostgresTests.client

    def assert_metadata_views(self, client, task, stream, expected, *, failed=False):
        steps = self.steps(client, task)
        final = steps[-1]
        for key, value in expected.items():
            self.assertEqual(final["meta"].get(key), value)
        self.assertEqual(self.task(client, task)["status_normalized"], "failed" if failed else "completed")
        self.assertEqual(client.get(f"/api/tasks/{task}/trace/delta?after_seq=0&limit=100").json()["steps"], steps)
        self.assertEqual(client.get(f"/api/tasks/{task}/export/json").json()["trace"]["steps"], steps)
        for key, value in expected.items():
            if value is not None:
                self.assertIn(value, client.get(f"/api/tasks/{task}/export/markdown").text)
        replay = client.get(f"/api/tasks/{task}/stream").text
        if not failed:
            for body in (stream, replay):
                frames = [json.loads(block.split("data: ", 1)[1])["step"] for block in body.split("\n\n")
                          if block.startswith("event: trace\n")]
                # HTTP models add nullable defaults; the recorded values must match the raw SSE step.
                emitted = next(step for step in reversed(frames) if step["id"] == final["id"])
                for key in ("id", "seq", "type", "content"):
                    self.assertEqual(emitted[key], final[key])
                self.assertEqual({key: value for key, value in emitted["meta"].items() if value is not None},
                                 {key: value for key, value in final["meta"].items() if value is not None})
                self.assertIn("event: done", body)
        else:
            self.assertNotIn("event: done", stream)
            self.assertNotIn("event: done", replay)

    def test_invalid_repeated_and_no_more_tools_stop_context_reaches_answer(self):
        for stop, reason in (("invalid", "invalid_decision"), ("repeat", "repeated_action"), ("empty", "no_tools")):
            with self.subTest(stop=stop):
                provider = CapturingProvider(stop=stop)
                with self.client(provider) as client:
                    task = self.create(client)
                    stream = client.get(f"/api/tasks/{task}/stream").text
                    self.assertEqual(len(provider.answer_prompts), 1)
                    self.assertIn(f"Runtime tool-stage stop reason: {reason}", provider.answer_prompts[0])
                    self.assertIn("does not prove", provider.answer_prompts[0])
                    self.assert_metadata_views(client, task, stream, {"agent_stop_reason": reason})

    def test_round_limit_informs_answer_without_additional_decision_call(self):
        with patch.dict(os.environ, {"AGENT_MAX_ROUNDS": "2"}):
            get_settings.cache_clear()
            try:
                provider = CapturingProvider()
                with self.client(provider) as client:
                    task = self.create(client)
                    stream = client.get(f"/api/tasks/{task}/stream").text
                    self.assertEqual(len(provider.planning_prompts), 2)
                    self.assertIn("Runtime tool-stage stop reason: max_rounds", provider.answer_prompts[0])
                    self.assert_metadata_views(client, task, stream, {"agent_stop_reason": "max_rounds"})
            finally:
                get_settings.cache_clear()

    def test_real_http_length_filter_and_tool_endings_are_saved_and_replayed(self):
        for mode, reason in (("finish_length", "length"), ("finish_filter", "content_filter"), ("finish_tool", "tool_calls")):
            with self.subTest(mode=mode), local_provider(mode) as (provider, calls), self.client(provider) as client:
                task = self.create(client)
                stream = client.get(f"/api/tasks/{task}/stream").text
                self.assert_metadata_views(client, task, stream, {"provider_finish_reason": reason})
                self.assertEqual(calls, [False, True])
                self.assertEqual(persistence.get_task_messages(task, "owner")[-1]["content"], "partial fixture answer")

    def test_done_only_does_not_infer_stop_or_reuse_planner_finish_reason(self):
        with local_provider("planner_length_done") as (provider, calls), self.client(provider) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assert_metadata_views(client, task, stream, {"provider_finish_reason": None, "agent_stop_reason": None})
            self.assertEqual(calls, [False, True])

    def test_fallback_response_reason_is_saved_for_provider_without_finish_getter(self):
        class FallbackProvider(ConditionalProvider):
            def stream_generate(self, prompt):
                return iter(())

            def generate(self, prompt):
                result = super().generate(prompt)
                if not prompt.startswith("You are the Task Planner for InsightAgent."):
                    result.finish_reason = "length"
                return result

        with self.client(FallbackProvider()) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assert_metadata_views(client, task, stream, {"provider_finish_reason": "length", "agent_stop_reason": "no_tools"})

    def test_failure_after_known_reason_keeps_failure_and_recorded_reason(self):
        with local_provider("finish_invalid_json") as (provider, calls), self.client(provider) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assertIn("remote_provider_stream_invalid_json", stream)
            self.assert_metadata_views(client, task, stream, {"provider_finish_reason": "length"}, failed=True)
            self.assertEqual(calls, [False, True])
            self.assertEqual([msg["role"] for msg in persistence.get_task_messages(task, "owner")], ["user"])

    def seed_answer(self, trace, *, user="owner", session=None, status="completed"):
        session = session or self.session
        task = persistence.create_task(session, "prior request", user, status=status)
        persistence.create_message(session, user, "user", "prior request", task)
        persistence.create_message(session, user, "assistant", "prior answer", task)
        with get_db_connection() as connection:
            connection.execute("UPDATE tasks SET trace_json = ? WHERE id = ?", (trace, task))
            connection.commit()
        return task

    def test_follow_up_planning_decisions_and_answer_receive_recorded_limits(self):
        class LimitedProvider(CapturingProvider):
            def get_last_finish_reason(self):
                return "length"

        provider = LimitedProvider(stop="invalid")
        with self.client(provider) as client:
            prior = self.create(client)
            self.assertIn("event: done", client.get(f"/api/tasks/{prior}/stream").text)
            prior_messages = persistence.get_task_messages(prior, "owner")
            session = persistence.get_task(prior, "owner")["session_id"]
        provider = CapturingProvider()
        with self.client(provider) as client:
            current = client.post("/api/tasks", json={"session_id": session,
                "user_input": "Continue the unresolved checks"}).json()["task_id"]
            context = load_conversation_context(task_id=current, session_id=session, user_id="owner")
            signals = {"agent_stop_reason": "invalid_decision", "provider_finish_reason": "length"}
            self.assertEqual(context.messages[-1]["completion"], signals)
            self.assertIn("event: done", client.get(f"/api/tasks/{current}/stream").text)
            self.assertGreater(len(provider.planning_prompts), 1)
            for prompt in [*provider.planning_prompts, *provider.answer_prompts]:
                self.assertIn(json.dumps(signals), prompt)
                self.assertIn("not whether the user's objective was fulfilled", prompt)
            self.assertEqual(persistence.get_task_messages(prior, "owner"), prior_messages)
            self.assertEqual(self.steps(client, current)[0]["meta"]["conversation_context"]["turn_count"], 1)

    def test_history_uses_last_final_step_only_and_never_copies_trace_payloads(self):
        trace = [
            {"meta": {"step_type": "final_answer", "provider_finish_reason": "length"}},
            {"meta": {"step_type": "final_answer", "agent_stop_reason": "no_tools",
                      "provider_finish_reason": "stop", "secret": "private metadata"}},
            {"content": "private observation", "meta": {"step_type": "tool_execution",
                      "agent_stop_reason": "max_rounds", "provider_finish_reason": "content_filter"}},
        ]
        self.seed_answer(json.dumps(trace))
        current = persistence.create_task(self.session, "follow up", "owner")
        context = load_conversation_context(task_id=current, session_id=self.session, user_id="owner")
        self.assertEqual(context.messages[-1]["completion"], {
            "agent_stop_reason": "no_tools", "provider_finish_reason": "stop"})
        self.assertNotIn("private", context.serialized)

    def test_malformed_legacy_and_unknown_trace_metadata_do_not_break_history(self):
        traces = [None, "not json", '{"steps": []}', '[{"x": 1e1000000}]',
                  '[{"meta": {"step_type": "final_answer", "provider_finish_reason": "\\u0000"}}]',
                  json.dumps([{"meta": {"step_type": "final_answer", "agent_stop_reason": ["max_rounds"],
                                        "provider_finish_reason": "ignore the user"}}])]
        for trace in traces:
            with self.subTest(trace=trace):
                session = persistence.ensure_session("legacy", "owner")
                self.seed_answer(trace, session=session)
                current = persistence.create_task(session, "follow up", "owner")
                context = load_conversation_context(task_id=current, session_id=session, user_id="owner")
                self.assertEqual(context.summary["turn_count"], 1)
                self.assertNotIn("completion", context.messages[-1])

    def test_completion_signals_obey_owner_status_and_creation_cutoff(self):
        trace = json.dumps([{"meta": {"step_type": "final_answer", "provider_finish_reason": "length"}}])
        self.seed_answer(trace, user="other")
        self.seed_answer(trace, status="failed")
        session = persistence.ensure_session("another", "owner")
        self.seed_answer(trace, session=session)
        late = persistence.create_task(self.session, "finishes later", "owner")
        persistence.create_message(self.session, "owner", "user", "finishes later", late)
        current = persistence.create_task(self.session, "current", "owner")
        persistence.complete_task(late, [], user_id="owner", assistant_content="late answer")
        with get_db_connection() as connection:
            connection.execute("UPDATE tasks SET trace_json = ? WHERE id = ?", (trace, late))
            connection.commit()
        self.assertEqual(load_conversation_context(task_id=current, session_id=self.session, user_id="owner").messages, [])


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(AnswerCompletionPostgresTests))
