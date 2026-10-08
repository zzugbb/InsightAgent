#!/usr/bin/env python3
"""Fail-closed protocol fixture checks; no Docker, ports or provider credentials."""

import json
import unittest
from unittest.mock import patch

from pilot_model_fixture import FEEDBACK, HISTORY, KNOWLEDGE, respond
from smoke_pilot_images import request_json


def history():
    return HISTORY + json.dumps([
        {"role": "user", "content": "Record mission code: blue telescope."},
        {"role": "assistant", "content": "blue telescope"},
    ]) + "\n\nCurrent user request:\nRetrieve the budget and double it."


def evidence(budget=7):
    return KNOWLEDGE + json.dumps({"chunks": [{"content": f"budget: {budget}",
        "source": "guide.md", "document_id": "guide.md", "document_version": "sha256:" + "a" * 16,
        "knowledge_base_id": f"pilot-budget-{budget}"}], "truncated": False})


def request(model, *, planning=True, prompt=None, rows=None):
    prompt = history() if prompt is None else prompt
    if planning:
        prompt = "You are the Task Planner for InsightAgent.\n" + prompt
        if rows is not None:
            prompt += "\n" + FEEDBACK + json.dumps(rows)
    elif rows:
        prompt += "\n\nTool observations:\n" + "\n".join(rows)
    return {"model": model, "stream": not planning, "messages": [{"role": "user", "content": prompt}]}


def json_response(payload):
    status, _, body, _ = respond(payload)
    return status, json.loads(body)


class PilotAgentFixtureTests(unittest.TestCase):
    def test_equal_hit_count_different_bodies_drive_different_next_tools(self):
        for budget in (7, 5):
            with self.subTest(budget=budget):
                # Same model, history, source and KB; only the retrieved body changes.
                row = evidence(budget).replace(f"pilot-budget-{budget}", "pilot-budget-7")
                _, payload = json_response(request("pilot-budget-7", rows=[row]))
                tools = json.loads(payload["choices"][0]["message"]["content"])["tools"]
                self.assertEqual(tools, [{"name": "calc_eval", "input": {"expression": f"{budget}*2"}}])

    def test_missing_history_body_source_version_or_wrong_scope_cannot_answer(self):
        bad_evidence = [
            evidence().replace("budget: 7", "hit_count: 1"),
            evidence().replace("guide.md", "unknown.md"),
            evidence().replace("sha256:" + "a" * 16, "unknown"),
            evidence().replace("pilot-budget-7", "other-owner"),
        ]
        invalid = [request("pilot-budget-7", prompt="new request", rows=[evidence()])]
        invalid += [request("pilot-budget-7", rows=[row]) for row in bad_evidence]
        invalid += [request("pilot-budget-7", rows=[evidence().replace("budget: 7", "budget: unknown")])]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "^pilot_fixture_evidence_missing$"):
                respond(payload)

    def test_final_answer_requires_the_actual_calculator_observation(self):
        with self.assertRaisesRegex(ValueError, "^pilot_fixture_evidence_missing$"):
            respond(request("pilot-budget-7", planning=False, rows=[evidence()]))
        status, content_type, body, stage = respond(request("pilot-budget-7", planning=False,
            rows=[evidence(), 'Calculator: {"result": 14.0}']))
        self.assertEqual((status, content_type, stage), (200, "text/event-stream", "answer"))
        self.assertIn(b"blue telescope: 14; guide.md sha256:", body)
        self.assertIn(b'"total_tokens": 7', body)
        self.assertTrue(body.endswith(b"data: [DONE]\n\n"))

    def test_tool_loop_stops_after_calculator_evidence(self):
        _, payload = json_response(request("pilot-budget-7", rows=[evidence(), '{"result": 14}']))
        self.assertEqual(json.loads(payload["choices"][0]["message"]["content"]), {"tools": []})

    def test_new_session_must_not_receive_history(self):
        for model in ("pilot-seed", "pilot-isolated"):
            with self.subTest(model=model), self.assertRaisesRegex(ValueError, "^pilot_fixture_evidence_missing$"):
                respond(request(model))
        _, payload = json_response(request("pilot-isolated", prompt="new request"))
        self.assertEqual(json.loads(payload["choices"][0]["message"]["content"]), {"tools": []})

    def test_empty_planning_retains_usage_while_429_does_not_invent_it(self):
        for model, rows in (("pilot-empty-initial", None), ("pilot-empty-feedback", ['{"result": 5}'])):
            with self.subTest(model=model):
                status, payload = json_response(request(model, prompt="fixture request", rows=rows))
                self.assertEqual(status, 200)
                self.assertEqual(payload["choices"][0]["message"]["content"], "")
                self.assertEqual(payload["usage"]["total_tokens"], 12)
        status, payload = json_response(request("pilot-rate-feedback", rows=['{"result": 5}']))
        self.assertEqual(status, 429)
        self.assertNotIn("usage", payload)

    def test_failed_planning_scenarios_forbid_answer_calls(self):
        for model in ("pilot-empty-feedback", "pilot-rate-feedback"):
            with self.subTest(model=model), self.assertRaisesRegex(ValueError, "^pilot_fixture_evidence_missing$"):
                respond(request(model, planning=False))

    def test_invalid_protocol_is_rejected(self):
        for payload in ({}, request("unexpected-model"),
                        {**request("pilot-budget-7"), "messages": []},
                        {**request("pilot-budget-7"), "stream": None}):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "^pilot_fixture_evidence_missing$"):
                respond(payload)

    def test_settings_request_uses_put_and_preserves_existing_post_default(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def read(self):
                return b'{"mode":"remote"}'

        with patch("smoke_pilot_images.urlopen", return_value=Response()) as opened:
            request_json("http://fixture/api/settings", payload={"mode": "remote"}, token="fixture", method="PUT")
            req = opened.call_args.args[0]
            self.assertEqual(req.get_method(), "PUT")
            self.assertEqual(req.get_header("Authorization"), "Bearer fixture")
            request_json("http://fixture/api/tasks", payload={"user_input": "fixture"})
            self.assertEqual(opened.call_args.args[0].get_method(), "POST")


if __name__ == "__main__":
    unittest.main()
