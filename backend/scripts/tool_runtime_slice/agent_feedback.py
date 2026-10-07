"""Boundaries of observation-driven planning; no services or provider requests."""

import json
from dataclasses import replace
from unittest.mock import patch

from app.providers.base import ProviderResponse, ProviderUsage
from app.services.agent_feedback import AgentFeedbackLoop, feedback_enabled, sum_planning_usage
from app.services import tool_runtime as runtime


def calc(expression):
    return {"name": "calc_eval", "input": {"expression": expression}}


class FixtureProvider:
    provider = "offline-feedback"

    def __init__(self, content):
        self.content, self.prompts = content, []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return ProviderResponse(self.content, "fixture", self.provider, ProviderUsage(10, 2, 12))


class AgentFeedbackMixin:
    def feedback_fixture(self, content, rounds=3):
        registry = runtime.get_default_tool_registry_provider()
        return AgentFeedbackLoop(initial_plan=[calc("2+3")], max_rounds=rounds,
                                 registry_provider=registry), FixtureProvider(content)

    def test_agent_feedback_plans_from_observation_and_stops_on_empty(self):
        loop, provider = self.feedback_fixture(json.dumps({"tools": [calc("5*2")]}))
        result = loop.decide(prompt="double result", observations=["Calculator result: 5"], provider=provider)
        self.assertEqual(result.reason, "continue")
        self.assertEqual(result.plan, [calc("5*2")])
        self.assertIn("Calculator result: 5", provider.prompts[0])
        self.assertEqual(loop.round, 2)
        provider.content = '{"tools": []}'
        self.assertEqual(loop.decide(prompt="done", observations=[], provider=provider).reason, "no_tools")

    def test_agent_feedback_invalid_partial_and_repeated_plans_never_fallback(self):
        for content, expected in [("plain answer", "invalid_decision"),
                                  (json.dumps({"tools": [calc("5*2"), {"name": "unknown"}]}), "invalid_decision"),
                                  (json.dumps({"tools": [calc("2+3")]}), "repeated_action")]:
            loop, provider = self.feedback_fixture(content)
            result = loop.decide(prompt="[calc:2+3]", observations=["5"], provider=provider)
            self.assertEqual(result.reason, expected)
            self.assertEqual(result.plan, [])
            self.assertEqual(loop.round, 1)

    def test_agent_feedback_limits_do_not_call_provider(self):
        for reason in ("max_rounds", "max_tool_calls", "observation_limit"):
            loop, provider = self.feedback_fixture('{"tools": []}')
            observations = []
            if reason == "max_rounds":
                loop.round = loop.max_rounds
            elif reason == "max_tool_calls":
                loop.calls = 32
            else:
                observations = ["x" * 24_001]
            self.assertEqual(loop.decide(prompt="task", observations=observations, provider=provider).reason, reason)
            self.assertEqual(provider.prompts, [])

    def test_agent_feedback_total_budget_rejects_next_plan_before_execution(self):
        loop, provider = self.feedback_fixture(json.dumps({"tools": [
            {**calc("5*2"), "id": "a", "depends_on": []},
            {**calc("5*3"), "id": "b", "depends_on": []}]}))
        loop.calls = 31
        self.assertEqual(loop.decide(prompt="task", observations=[], provider=provider).reason, "max_tool_calls")
        self.assertEqual(loop.calls, 31)

    def test_agent_feedback_checkpoint_and_mock_keep_single_pass(self):
        artifacts = runtime.ToolPlanArtifacts(tool_plan=[calc("2+3")], planning_provider_used=True)
        kwargs = dict(artifacts=artifacts, registry_provider=runtime.get_default_tool_registry_provider(), checkpoint_seed=None, max_rounds=3)
        self.assertTrue(feedback_enabled(**kwargs))
        self.assertFalse(feedback_enabled(**{**kwargs, "checkpoint_seed": {"plan": []}}))
        self.assertFalse(feedback_enabled(**{**kwargs, "max_rounds": 1}))
        self.assertFalse(feedback_enabled(**{**kwargs, "artifacts": replace(artifacts, planning_provider_used=False)}))

    def test_agent_feedback_usage_sums_calls_and_never_invents_provider_total(self):
        left = {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12,
                "prompt_tokens_source": "provider", "completion_tokens_source": "provider",
                "usage_source": "provider", "provider_total_tokens": 12, "cost_estimate": 0.01}
        result = sum_planning_usage(left, left)
        self.assertEqual(result["total_tokens"], 24)
        self.assertEqual(result["provider_total_tokens"], 24)
        self.assertEqual(result["cost_estimate"], 0.02)
        result = sum_planning_usage(result, {**left, "provider_total_tokens": None})
        self.assertNotIn("provider_total_tokens", result)
        self.assertEqual(result["prompt_tokens"], 30)
