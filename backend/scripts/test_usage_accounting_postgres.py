#!/usr/bin/env python3
"""Task decisions, API usage aggregates and exports against isolated PostgreSQL."""

import json
import unittest

from task_postgres_fixture import run_isolated_postgres
from test_agent_feedback_postgres import AgentFeedbackPostgresTests, ConditionalProvider
from app.services import chat_persistence_service as persistence


class EstimatedPlanningProvider(ConditionalProvider):
    def generate(self, prompt):
        result = super().generate(prompt)
        if prompt.startswith("You are the Task Planner for InsightAgent."):
            result.usage = None
        return result


class UsageAccountingPostgresTests(unittest.TestCase):
    setUp = AgentFeedbackPostgresTests.setUp
    create = AgentFeedbackPostgresTests.create
    task = AgentFeedbackPostgresTests.task
    client = AgentFeedbackPostgresTests.client

    def assert_views(self, client, task, expected, source):
        sid = self.task(client, task)["session_id"]
        for path in ("/api/tasks/usage/summary", f"/api/tasks/usage/summary?session_id={sid}",
                     f"/api/sessions/{sid}/usage/summary"):
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            summary = response.json()
            self.assertEqual(summary["total_tokens"], expected["overall_total_tokens"])
            self.assertEqual(summary["prompt_tokens"], expected["overall_prompt_tokens"])
            self.assertEqual(summary["completion_tokens"], expected["overall_completion_tokens"])
            self.assertAlmostEqual(summary["cost_estimate"], expected["overall_cost_estimate"])
            self.assertEqual(summary[f"source_tasks_{source}"], 1)
        response = client.get(f"/api/tasks/usage/dashboard?session_id={sid}&source_kind={source}")
        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertEqual(report["summary"]["total_tokens"], expected["overall_total_tokens"])
        self.assertEqual(report["summary"][f"source_tasks_{source}"], 1)
        for view in (report["by_session"], report["top_tasks"]):
            self.assertEqual(view[0]["total_tokens"], expected["overall_total_tokens"])
            self.assertAlmostEqual(view[0]["cost_estimate"], expected["overall_cost_estimate"])
        self.assertEqual(sum(day["total_tokens"] for day in report["trend"]), expected["overall_total_tokens"])
        export = client.get(f"/api/sessions/{sid}/export/json").json()
        self.assertEqual(export["usage_summary"]["total_tokens"], expected["overall_total_tokens"])
        self.assertEqual(export["version"], "1.0")

    def test_three_decision_calls_and_final_answer_match_usage_apis_and_session_export(self):
        with self.client(ConditionalProvider()) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assertIn("event: done", stream)
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertEqual((usage["total_tokens"], usage["planning_total_tokens"], usage["overall_total_tokens"]),
                             (35, 36, 71))
            self.assertAlmostEqual(usage["overall_cost_estimate"], 0.000082)
            done = json.loads(stream.split("event: done\ndata: ", 1)[1].split("\n\n", 1)[0])
            self.assertEqual(done["usage"], usage)
            self.assert_views(client, task, usage, "provider")

    def test_estimated_planning_and_provider_answer_appear_under_mixed_source_filter(self):
        with self.client(EstimatedPlanningProvider()) as client:
            task = self.create(client)
            self.assertIn("event: done", client.get(f"/api/tasks/{task}/stream").text)
            usage = json.loads(self.task(client, task)["usage_json"])
            self.assertEqual(usage["planning_usage_source"], "estimated")
            self.assertEqual(usage["usage_source"], "provider")
            self.assert_views(client, task, usage, "mixed")
            sid = self.task(client, task)["session_id"]
            filtered = client.get(f"/api/tasks/usage/dashboard?session_id={sid}&source_kind=provider").json()
            self.assertEqual(filtered["summary"]["tasks_with_usage"], 0)
            self.assertEqual(filtered["top_tasks"], [])

    def seed_usage(self, session, payload, *, user="owner"):
        task = persistence.create_task(session, "usage fixture", user)
        self.assertEqual(persistence.complete_task(task, [], user, usage=payload), 1)
        return task

    def test_legacy_fallback_rank_and_owner_isolation_keep_existing_response_shapes(self):
        legacy = self.seed_usage(self.session, {"prompt_tokens": 10, "completion_tokens": 4,
                                               "cost_estimate": 0.1, "usage_source": "provider"})
        planning = self.seed_usage(self.session, {"prompt_tokens": 2, "completion_tokens": 1,
            "planning_prompt_tokens": 20, "planning_completion_tokens": 3, "planning_cost_estimate": 0.2})
        other = persistence.ensure_session("other user's usage", "other")
        self.seed_usage(other, {"prompt_tokens": 99_999, "completion_tokens": 99_999}, user="other")
        with self.client(ConditionalProvider()) as client:
            summary = client.get("/api/tasks/usage/summary").json()
            self.assertEqual(summary["total_tokens"], 40)
            self.assertAlmostEqual(summary["cost_estimate"], 0.3)
            report = client.get("/api/tasks/usage/dashboard").json()
            self.assertEqual(report["summary"], summary)
            self.assertEqual([row["task_id"] for row in report["top_tasks"]], [planning, legacy])
            self.assertEqual(report["by_session"][0]["total_tokens"], 40)
            self.assertEqual(client.get(f"/api/tasks/usage/summary?session_id={other}").status_code, 404)
            self.assertEqual(client.get(f"/api/sessions/{other}/usage/summary").status_code, 404)


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(UsageAccountingPostgresTests, settings={
        "USAGE_PROMPT_TOKEN_PRICE_PER_1K": "0.001", "USAGE_COMPLETION_TOKEN_PRICE_PER_1K": "0.002",
    }))
