#!/usr/bin/env python3
"""Fail-closed checks for disposable pilot task smoke evidence; no services required."""

import unittest
from unittest.mock import patch

from pilot_task_smoke import check_task_contracts
from smoke_pilot_images import read_stream


class ApiFixture:
    def __init__(self, failure=None):
        self.failure = failure
        self.branch_created = False
        self.export_reads = 0

    def steps(self, task):
        steps = []
        for index, name in enumerate(("task_plan", "task_retrieve", "calc_eval"), 1):
            meta = {"tool": {"name": name, "output_preview": {"result": 5, "hit_count": 1}},
                    "cost_estimate": 0, "tokens": 0}
            if task == "branch" and index < 3:
                meta["checkpoint_reused"] = True
                if self.failure == "usage":
                    meta["cost_estimate"] = 1
            steps.append({"id": f"{task}-{index}", "seq": index, "type": "action", "meta": meta})
        steps.append({"id": task + "-rag", "seq": 4, "type": "observation", "meta": {"step_type": "rag_retrieval"}})
        if self.failure == "cursor":
            steps[-1]["seq"] = 1
        return steps

    def api(self, url, *, payload=None, token=None):
        assert token == "temporary-token"
        path = url.removeprefix("http://fixture/api/")
        if path == "rag/ingest-jobs":
            return {"id": "job"}
        if path == "rag/ingest-jobs/job":
            return {"status": "failed" if self.failure == "ingest" else "completed",
                    "progress": {"documents_processed": 1, "chunks_written": 1, "chunk_total": 1}}
        if path == "rag/query":
            return {"hit_count": 1, "hits": [{"content": "blue telescope"}]}
        if path == "tasks":
            return {"task_id": "source", "session_id": "source-session"}
        if path == "tasks/source/checkpoints":
            return {"items": [{"tool_name": "calc_eval", "step_id": "source-3", "reused_steps": 2}]}
        if path == "tasks/source/reruns":
            if payload is None:
                return {"total": 2}
            task = "branch" if "checkpoint_step_id" in payload else "cancelled"
            self.branch_created = True
            return {"task_id": task, "session_id": task + "-session"}
        if path == "tasks/branch/reruns":
            return {"parent_task_id": "source"}
        parts = path.split("/")
        task = parts[1]
        if len(parts) == 2:
            return {"status_normalized": "cancelled" if task == "cancelled" else "completed"}
        if parts[2] == "cancel":
            return {}
        if parts[2] == "trace":
            steps = self.steps(task)
            return {"steps": steps[:-1] if self.failure == "delta" and len(parts) > 3 else steps}
        if parts[2] == "export":
            self.export_reads += task == "source"
            return {"version": "1.0", "task": {"id": task}, "trace": {"steps": self.steps(task)},
                    "messages": ["changed"] if self.failure == "source" and self.export_reads > 1 else []}
        raise AssertionError(path)

    def stream(self, url, token):
        if "/cancelled/" in url and self.failure != "restart":
            return [("error", {"reason": "cancelled"})]
        return [("done", {})]

    def run(self):
        return check_task_contracts("http://fixture", "temporary-token", request_json=self.api,
                                    request_text=lambda *_: "# Export", read_stream=self.stream,
                                    wait_until=lambda _, probe, **__: probe())


class PilotTaskSmokeTests(unittest.TestCase):
    def test_successful_fixture_reports_limited_mock_scope(self):
        result = ApiFixture().run()
        self.assertEqual(result["completed_tasks"], 2)
        self.assertEqual(result["checkpoint_reused_tools"], 2)
        self.assertEqual(result["cancelled_tasks"], 1)

    def test_regressions_fail_before_a_success_report(self):
        for failure, code in {
            "ingest": "pilot_ingest_failed", "cursor": "pilot_trace_cursor_failed",
            "delta": "pilot_trace_delta_failed", "usage": "pilot_checkpoint_usage_failed",
            "source": "pilot_checkpoint_source_changed", "restart": "pilot_cancelled_task_restarted",
        }.items():
            with self.subTest(failure=failure), self.assertRaisesRegex(RuntimeError, "^" + code + "$"):
                ApiFixture(failure).run()

    def test_sse_parser_accepts_crlf_comments_and_multiline_data(self):
        stream = ': keepalive\r\n\r\nevent: done\r\ndata: {"ok":\r\ndata: true}\r\n\r\n'
        with patch("smoke_pilot_images.request_text", return_value=stream):
            self.assertEqual(read_stream("http://fixture", "temporary-token"), [("done", {"ok": True})])

    def test_sse_parser_rejects_invalid_shapes_with_fixed_code(self):
        for data in ('["private-text"]', '{"private-text":'):
            with self.subTest(data=data), patch("smoke_pilot_images.request_text", return_value="data: " + data):
                with self.assertRaisesRegex(RuntimeError, "^pilot_stream_payload_invalid$"):
                    read_stream("http://fixture", "temporary-token")

    def test_sse_parser_rejects_over_budget(self):
        with patch("smoke_pilot_images.request_text", return_value="x" * 2_000_001):
            with self.assertRaisesRegex(RuntimeError, "^pilot_stream_budget_exceeded$"):
                read_stream("http://fixture", "temporary-token")


if __name__ == "__main__":
    unittest.main()
