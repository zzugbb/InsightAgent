#!/usr/bin/env python3
"""Published HTTP search evidence through actual requests, tasks and PostgreSQL."""

from contextlib import contextmanager
import json
import os
import unittest
from unittest.mock import patch

from task_postgres_fixture import run_isolated_postgres
from test_agent_feedback_postgres import AgentFeedbackPostgresTests, calc
from tool_http_fixture import ReadService
from app.config import get_settings
from app.providers.base import ProviderResponse, ProviderUsage
from app.providers.mock_provider import MockLLMProvider


class SearchEvidenceProvider(MockLLMProvider):
    def __init__(self):
        super().__init__(provider="offline-search-evidence")
        self.prompts, self.final_prompts = [], []

    def generate(self, prompt):
        self.prompts.append(prompt)
        if len(self.prompts) == 1:
            tools = [{"name": "provider_search", "input": {"query": "budget"}}]
        elif len(self.prompts) == 2:
            observations = json.loads(prompt.split("Completed tool observations (JSON):\n", 1)[1])
            tools = [calc("7*2" if "budget: 7" in " ".join(observations) else "5*2")]
        else:
            tools = []
        return ProviderResponse(json.dumps({"tools": tools}), self.model, self.provider, ProviderUsage(10, 2, 12))

    def stream_generate(self, prompt):
        self.final_prompts.append(prompt)
        yield "fixture answer with evidence" if "budget:" in prompt else "fixture answer without evidence"


class AgentToolContextPostgresTests(unittest.TestCase):
    setUp = AgentFeedbackPostgresTests.setUp
    create = AgentFeedbackPostgresTests.create
    task = AgentFeedbackPostgresTests.task
    steps = AgentFeedbackPostgresTests.steps

    @contextmanager
    def client(self, service, provider, *, rounds=3):
        spec = {"provider_search": {
            "template": "task_retrieve", "kind": "provider_retrieval", "runtime_semantic_kind": "provider_search",
            "label": "Provider Search", "result_preview_keys": ["hit_count"], "result_output_keys": ["hit_count", "results"],
            "execution": {"kind": "http_json", "url": f"{service.url}/search", "method": "GET",
                          "headers": {"Authorization": "Bearer request-fixture-secret", "X-User": "$user_id"},
                          "query_params": {"q": "$query"}, "result_fields": {"hit_count": "total", "results": "items"}}}}
        with patch.dict(os.environ, {"INSIGHT_AGENT_TOOL_REGISTRY_EXTRA_TOOLS_JSON": json.dumps(spec), "AGENT_MAX_ROUNDS": str(rounds)}):
            get_settings.cache_clear()
            try:
                with AgentFeedbackPostgresTests.client(self, provider) as client:
                    yield client
            finally:
                get_settings.cache_clear()

    def run_scenario(self, budget, *, rounds=3, canonical_mock=False):
        response = {"total": 1, "items": [{"title": "Budget guide", "snippet": f"budget: {budget}",
                    "url": "https://docs.example.com/guide?api_key=query-fixture-secret", "password": "nested-fixture-secret"}],
                    "unpublished": "raw-fixture-private", "api_key": "response-fixture-secret"}
        provider = MockLLMProvider() if canonical_mock else SearchEvidenceProvider()
        with ReadService(response_payload=response) as service, self.client(service, provider, rounds=rounds) as client:
            task = self.create(client)
            stream = client.get(f"/api/tasks/{task}/stream").text
            self.assertIn("event: done", stream)
            steps = self.steps(client, task)
            self.assertEqual(self.task(client, task)["status_normalized"], "completed")
            if canonical_mock:
                self.assertNotIn("Published tool results", stream)
                return
            self.assertEqual(len(service.calls), 1)
            self.assertEqual(service.calls[0]["user"], "owner")
            search = next(step for step in steps if (step["meta"].get("tool") or {}).get("name") == "provider_search")
            self.assertIn("1", search["meta"]["tool"]["result_summary"])
            self.assertNotIn("budget:", search["meta"]["tool"]["result_summary"])
            final_prompt = provider.final_prompts[-1]
            self.assertIn(f"budget: {budget}", final_prompt)
            self.assertIn("https://docs.example.com/guide", final_prompt)
            self.assertIn(search["id"], final_prompt)
            self.assertEqual(steps[-1]["content"], "fixture answer with evidence")
            if rounds > 1:
                calculations = [step["meta"]["tool"]["input"]["expression"] for step in steps
                                if (step["meta"].get("tool") or {}).get("name") == "calc_eval"]
                self.assertEqual(calculations, [f"{budget}*2"])
                self.assertIn(f"budget: {budget}", provider.prompts[1])
            self.assertEqual(client.get(f"/api/tasks/{task}/trace/delta?after_seq=0&limit=100").json()["steps"], steps)
            exported = client.get(f"/api/tasks/{task}/export/json").json()["trace"]["steps"]
            self.assertEqual(exported, steps)
            for private in ("query-fixture-secret", "nested-fixture-secret", "raw-fixture-private",
                            "response-fixture-secret", "request-fixture-secret"):
                self.assertNotIn(private, str((provider.prompts, provider.final_prompts, stream, exported)))

    def test_same_hit_count_different_details_drive_distinct_feedback_actions(self):
        for budget in (5, 7):
            with self.subTest(budget=budget):
                self.run_scenario(budget)

    def test_single_round_final_answer_receives_search_details(self):
        self.run_scenario(7, rounds=1)

    def test_canonical_mock_demo_does_not_receive_model_evidence_extension(self):
        self.run_scenario(7, canonical_mock=True)


if __name__ == "__main__":
    raise SystemExit(run_isolated_postgres(AgentToolContextPostgresTests))
