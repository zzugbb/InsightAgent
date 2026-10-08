#!/usr/bin/env python3
"""Actual compatible HTTP streaming and task failure persistence in isolated PostgreSQL."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import unittest
from unittest.mock import patch

from task_postgres_fixture import run_isolated_postgres
from test_agent_feedback_postgres import AgentFeedbackPostgresTests
from app.providers.openai_compatible_provider import OpenAICompatibleLLMProvider
from app.services import chat_persistence_service as persistence
from app.services import task_queue_service as queue


@contextmanager
def local_provider(mode):
    calls = []

    def event(**fields):
        return "data: " + json.dumps(fields) + "\n\n"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            streaming = payload.get("stream", False)
            calls.append(streaming)
            status, content_type = 200, "application/json"
            if not streaming:
                body = json.dumps({"choices": [{"message": {"content": '{"tools": []}'},
                    **({"finish_reason": "length"} if mode == "planner_length_done" else {})}]})
            elif mode == "compat_partial" and "stream_options" in payload:
                status, body = 400, '{"error": {"message": "stream_options unsupported"}}'
            else:
                content_type = "text/event-stream"
                body = event(choices=[{"delta": {"role": "assistant", "content": ""}, "finish_reason": None}])
                if mode == "partial_tail":
                    body += event(choices=[{"delta": {"content": "x"}, "finish_reason": None}]) * 10
                elif mode != "empty":
                    body += event(choices=[{"delta": {"content": "partial fixture answer"}, "finish_reason": None}])
                reason = {"finish": "stop", "finish_length": "length", "finish_filter": "content_filter",
                          "finish_tool": "tool_calls", "finish_invalid_json": "length"}.get(mode)
                if reason:
                    body += event(choices=[{"delta": {}, "finish_reason": reason}])
                if mode in {"finish", "done", "partial_usage", "planner_length_done", "finish_length", "finish_filter", "finish_tool"}:
                    body += event(choices=[], usage={"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7})
                if mode == "finish_invalid_json":
                    body += "data: invalid JSON\n\n"
                if mode in {"done", "empty", "planner_length_done"}:
                    body += "data: [DONE]\n\n"
            encoded = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider = OpenAICompatibleLLMProvider(
            model="offline-fixture", provider="offline-fixture",
            base_url=f"http://127.0.0.1:{server.server_port}/v1", api_key="fixture-only",
        )
        yield provider, calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class ProviderStreamPostgresTests(unittest.TestCase):
    setUp = AgentFeedbackPostgresTests.setUp
    create = AgentFeedbackPostgresTests.create
    task = AgentFeedbackPostgresTests.task
    steps = AgentFeedbackPostgresTests.steps
    client = AgentFeedbackPostgresTests.client

    def assert_failed_stream(self, mode, *, empty=False):
        with local_provider(mode) as (provider, calls), self.client(provider) as client:
            task = self.create(client)
            with self.assertLogs("insightagent.llm", level="INFO") as logs, \
                 patch("app.services.chat_execution_service.try_append_task_memory") as memory:
                stream = client.get(f"/api/tasks/{task}/stream").text
            memory.assert_not_called()
            code = "remote_provider_empty_response" if empty else "remote_provider_stream_interrupted"
            self.assertIn("event: error", stream)
            self.assertIn(code, stream)
            self.assertNotIn("event: done", stream)
            self.assertEqual(self.task(client, task)["status_normalized"], "failed")
            self.assertEqual([message["role"] for message in persistence.get_task_messages(task, "owner")], ["user"])
            self.assertEqual(queue.get_task_queue_snapshot(max_concurrent=32)["active_count"], 0)
            steps = self.steps(client, task)
            if not empty:
                self.assertIn("event: token", stream)
                self.assertEqual(steps[-1]["content"], "x" * 10 if mode == "partial_tail" else "partial fixture answer")
                initial = [json.loads(block.split("data: ", 1)[1])["step"]
                           for block in stream.split("\n\n") if block.startswith("event: trace\n")]
                initial_final = next(step for step in initial if step["id"] == steps[-1]["id"])
                self.assertGreater(steps[-1]["seq"], initial_final["seq"])
                delta = client.get(f"/api/tasks/{task}/trace/delta?after_seq={initial_final['seq']}&limit=100").json()
                self.assertIn(steps[-1], delta["steps"])
            self.assertEqual(client.get(f"/api/tasks/{task}/trace/delta?after_seq=0&limit=100").json()["steps"], steps)
            self.assertEqual(client.get(f"/api/tasks/{task}/export/json").json()["trace"]["steps"], steps)
            self.assertEqual(client.get(f"/api/tasks/{task}/export/markdown").status_code, 200)
            expected_calls = [False, True, True] if mode == "compat_partial" else [False, True]
            self.assertEqual(calls, expected_calls)
            attempts = [json.loads(line.split(":", 2)[2]) for line in logs.output]
            streaming = [attempt["outcome"] for attempt in attempts if attempt["mode"] == "stream"]
            self.assertEqual(streaming, ["compat_retry", "interrupted"] if mode == "compat_partial"
                             else ["empty_response" if empty else "interrupted"])
            replay = client.get(f"/api/tasks/{task}/stream").text
            self.assertIn(code, replay)
            self.assertNotIn("event: done", replay)
            self.assertEqual(calls, expected_calls)
            self.assertEqual(self.steps(client, task), steps)

    def test_partial_eof_persists_failure_and_reconnect_does_not_replay(self):
        self.assert_failed_stream("partial")

    def test_compat_retry_then_partial_eof_does_not_retry_output(self):
        self.assert_failed_stream("compat_partial")

    def test_partial_eof_preserves_tail_after_trace_batch_boundary(self):
        self.assert_failed_stream("partial_tail")

    def test_completed_empty_stream_fails_without_generate_fallback(self):
        self.assert_failed_stream("empty", empty=True)

    def assert_completed_stream(self, mode):
        with local_provider(mode) as (provider, calls), self.client(provider) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assertIn("event: done", stream)
            self.assertNotIn("event: error", stream)
            self.assertEqual(self.task(client, task)["status_normalized"], "completed")
            self.assertEqual(self.steps(client, task)[-1]["content"], "partial fixture answer")
            messages = persistence.get_task_messages(task, "owner")
            self.assertEqual([message["role"] for message in messages], ["user", "assistant"])
            self.assertEqual(messages[-1]["content"], "partial fixture answer")
            self.assertEqual(provider.get_last_usage().total_tokens, 7)
            self.assertEqual(calls, [False, True])
            self.assertEqual(queue.get_task_queue_snapshot(max_concurrent=32)["active_count"], 0)

    def test_done_marker_completes_with_empty_metadata_frames(self):
        self.assert_completed_stream("done")

    def test_terminal_finish_reason_completes_without_done_marker(self):
        self.assert_completed_stream("finish")


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(ProviderStreamPostgresTests))
