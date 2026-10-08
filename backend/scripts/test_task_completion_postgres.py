#!/usr/bin/env python3
"""Atomic answer persistence, terminal races and task replay in isolated PostgreSQL."""

from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Event
import unittest
from unittest.mock import patch

from task_postgres_fixture import run_isolated_postgres
from test_agent_feedback_postgres import AgentFeedbackPostgresTests
from app.db import get_db_connection
from app.providers.mock_provider import MockLLMProvider
from app.services import chat_persistence_service as persistence
from app.services import task_queue_service as queue
from app.services.conversation_context import load_conversation_context


class AnswerProvider(MockLLMProvider):
    def __init__(self):
        super().__init__()
        self.stream_calls = 0

    def stream_generate(self, prompt):
        self.stream_calls += 1
        yield "fixture completed answer"


@contextmanager
def reject_assistant_insert():
    with get_db_connection() as connection:
        connection.execute("""CREATE FUNCTION reject_assistant_fixture() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.role = 'assistant' THEN RAISE EXCEPTION 'assistant insert fixture'; END IF;
            RETURN NEW; END; $$""")
        connection.execute("CREATE TRIGGER reject_assistant BEFORE INSERT ON messages FOR EACH ROW EXECUTE FUNCTION reject_assistant_fixture()")
        connection.commit()
    try:
        yield
    finally:
        with get_db_connection() as connection:
            connection.execute("DROP TRIGGER reject_assistant ON messages")
            connection.execute("DROP FUNCTION reject_assistant_fixture()")
            connection.commit()


class TaskCompletionPostgresTests(unittest.TestCase):
    setUp = AgentFeedbackPostgresTests.setUp
    create = AgentFeedbackPostgresTests.create
    task = AgentFeedbackPostgresTests.task
    steps = AgentFeedbackPostgresTests.steps
    client = AgentFeedbackPostgresTests.client

    def test_assistant_insert_failure_never_leaves_completed_task_or_success_replay(self):
        provider = AnswerProvider()
        with reject_assistant_insert(), self.client(provider) as client:
            task = self.create(client)
            with patch("app.services.chat_execution_service.try_append_task_memory") as memory:
                stream = client.get(f"/api/tasks/{task}/stream").text
            self.assertEqual(self.task(client, task)["status_normalized"], "failed")
            self.assertNotIn("event: done", stream)
            self.assertIn("event: error", stream)
            self.assertIn("task_stream_failure", stream)
            memory.assert_not_called()
            self.assertEqual([message["role"] for message in persistence.get_task_messages(task, "owner")], ["user"])
            steps = self.steps(client, task)
            self.assertEqual(steps[-1]["content"], "fixture completed answer")
            self.assertEqual(client.get(f"/api/tasks/{task}/trace/delta?after_seq=0&limit=100").json()["steps"], steps)
            self.assertEqual(client.get(f"/api/tasks/{task}/export/json").json()["trace"]["steps"], steps)
            replay = client.get(f"/api/tasks/{task}/stream").text
            self.assertNotIn("event: done", replay)
            self.assertIn("task_stream_failure", replay)
            self.assertEqual(provider.stream_calls, 1)
            self.assertEqual(queue.get_task_queue_snapshot(max_concurrent=32)["active_count"], 0)

    def test_session_touch_failure_rolls_back_answer_and_success_status(self):
        with self.client(AnswerProvider()) as client:
            task = self.create(client)
            sid = self.task(client, task)["session_id"]
            before = persistence.get_session(sid, "owner")["updated_at"]
            with get_db_connection() as connection:
                connection.execute("""CREATE FUNCTION reject_session_fixture() RETURNS trigger LANGUAGE plpgsql AS $$
                    BEGIN IF EXISTS (SELECT 1 FROM messages WHERE session_id = NEW.id AND role = 'assistant')
                    THEN RAISE EXCEPTION 'session touch fixture'; END IF; RETURN NEW; END; $$""")
                connection.execute("CREATE TRIGGER reject_session BEFORE UPDATE ON sessions FOR EACH ROW EXECUTE FUNCTION reject_session_fixture()")
                connection.commit()
            try:
                stream = client.get(f"/api/tasks/{task}/stream").text
                self.assertNotIn("event: done", stream)
                self.assertEqual(self.task(client, task)["status_normalized"], "failed")
                self.assertEqual([row["role"] for row in persistence.get_task_messages(task, "owner")], ["user"])
                self.assertEqual(persistence.get_session(sid, "owner")["updated_at"], before)
            finally:
                with get_db_connection() as connection:
                    connection.execute("DROP TRIGGER reject_session ON sessions")
                    connection.execute("DROP FUNCTION reject_session_fixture()")
                    connection.commit()

    def test_concurrent_completion_saves_exactly_one_answer(self):
        task = persistence.create_task(self.session, "fixture", "owner")
        with ThreadPoolExecutor(max_workers=2) as pool:
            writes = list(pool.map(lambda _: persistence.complete_task(task, [], "owner",
                usage={"total_tokens": 3}, assistant_content="single answer"), range(2)))
        self.assertEqual(sorted(writes), [0, 1])
        self.assertEqual(persistence.get_task(task, "owner")["status"], "completed")
        self.assertEqual([row["content"] for row in persistence.get_task_messages(task, "owner")], ["single answer"])

    def test_cancelled_other_owner_and_other_user_completions_do_not_insert(self):
        for mode in ("cancelled", "other_owner", "other_user"):
            with self.subTest(mode=mode):
                task = persistence.create_task(self.session, "fixture", "owner", status="pending")
                if mode == "cancelled":
                    persistence.mark_task_cancel_requested(task_id=task, user_id="owner")
                elif mode == "other_owner":
                    self.assertEqual(persistence.mark_task_running_started(
                        task_id=task, user_id="owner", execution_owner_id="instance-a"), 1)
                before = persistence.get_task(task, "owner")
                self.assertEqual(persistence.complete_task(task, [], "other" if mode == "other_user" else "owner",
                    execution_owner_id="instance-b", assistant_content="must not be stored"), 0)
                self.assertEqual(persistence.get_task(task, "owner"), before)
                self.assertEqual(persistence.get_task_messages(task, "owner"), [])

    def test_reader_cannot_observe_completed_status_before_answer_commit(self):
        task = persistence.create_task(self.session, "fixture", "owner")
        started, release = Event(), Event()
        original = persistence._insert_chat_message

        def insert(*args, **kwargs):
            result = original(*args, **kwargs)
            started.set()
            if not release.wait(5):
                raise RuntimeError("completion fixture timeout")
            return result

        with patch.object(persistence, "_insert_chat_message", side_effect=insert), ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(persistence.complete_task, task, [], "owner", assistant_content="visible together")
            try:
                self.assertTrue(started.wait(3))
                self.assertEqual(persistence.get_task(task, "owner")["status"], "running")
                self.assertEqual(persistence.get_task_messages(task, "owner"), [])
                release.set()
                self.assertEqual(future.result(timeout=3), 1)
            finally:
                release.set()
        self.assertEqual(persistence.get_task(task, "owner")["status"], "completed")
        self.assertEqual([row["content"] for row in persistence.get_task_messages(task, "owner")], ["visible together"])

    def test_success_replay_exports_and_next_turn_context_have_one_saved_answer(self):
        provider = AnswerProvider()
        with self.client(provider) as client:
            task = self.create(client)
            self.assertIn("event: done", client.get(f"/api/tasks/{task}/stream").text)
            saved = self.task(client, task)
            self.assertEqual(saved["status_normalized"], "completed")
            self.assertIsNotNone(saved["usage_json"])
            messages = persistence.get_task_messages(task, "owner")
            self.assertEqual([row["role"] for row in messages], ["user", "assistant"])
            self.assertEqual(messages[-1]["content"], self.steps(client, task)[-1]["content"])
            self.assertIn("event: done", client.get(f"/api/tasks/{task}/stream").text)
            self.assertEqual(provider.stream_calls, 1)
            self.assertEqual(persistence.get_task_messages(task, "owner"), messages)
            export = client.get(f"/api/sessions/{saved['session_id']}/export/json").json()
            self.assertEqual([row["role"] for row in export["messages"]], ["user", "assistant"])
            following = persistence.create_task(saved["session_id"], "next turn", "owner")
            context = load_conversation_context(task_id=following, session_id=saved["session_id"], user_id="owner")
            self.assertEqual(context.messages[-1], {"role": "assistant", "content": messages[-1]["content"]})
            self.assertGreater(json.loads(saved["usage_json"])["total_tokens"], 0)


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(TaskCompletionPostgresTests))
