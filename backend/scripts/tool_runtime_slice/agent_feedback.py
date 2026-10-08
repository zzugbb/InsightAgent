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
    def test_agent_feedback_missing_required_input_never_falls_back_to_the_prompt(self):
        for node in ({"name": "calc_eval", "input": {}}, {"name": "task_retrieve", "input": {}},
                     calc(""), {"name": "task_retrieve", "input": {"query": "  "}},
                     {"name": "task_retrieve", "input": {"query": ["not text"]}}):
            with self.subTest(node=node):
                loop, provider = self.feedback_fixture(json.dumps({"tools": [node]}))
                result = loop.decide(prompt="user request [calc:5*2]", observations=["actual result 5"], provider=provider)
                self.assertEqual(result.reason, "invalid_decision")
                self.assertEqual(result.plan, [])
                self.assertEqual(result.artifacts.provider_usage.total_tokens, 12)

    def test_agent_feedback_bound_query_can_omit_a_literal_without_using_prompt_defaults(self):
        from app.services.tool_plan_dependencies import bind_node_input

        graph = [{**calc("3+4"), "id": "root", "depends_on": []},
                 {"name": "task_retrieve", "id": "search", "input": {},
                  "input_bindings": {"query": {"node": "root", "path": ["result"], "template": "result {value}"}}}]
        loop, provider = self.feedback_fixture(json.dumps({"tools": graph}))
        result = loop.decide(prompt="user request", observations=[], provider=provider)
        self.assertEqual(result.reason, "continue")
        self.assertEqual(bind_node_input(result.plan[-1], {"root": {"result": 7.0}})["input"]["query"], "result 7.0")

    def test_agent_feedback_initial_planning_keeps_legacy_missing_input_defaults(self):
        from app.services.tool_runtime_planning import _build_provider_tool_plan

        provider = FixtureProvider(json.dumps({"tools": [{"name": "calc_eval"}, {"name": "task_retrieve"}]}))
        result = _build_provider_tool_plan("rag [calc:5*2]", provider=provider)
        self.assertTrue(result.planning_provider_used)
        self.assertEqual(result.tool_plan[1]["input"]["expression"], "5*2")
        self.assertEqual(result.tool_plan[2]["input"]["query"], "rag [calc:5*2]")

    def test_agent_feedback_graph_missing_input_keeps_graph_error_and_returned_usage(self):
        from app.services.tool_plan_dependencies import ToolDependencyError

        graph = [{"name": "calc_eval", "id": "incomplete", "depends_on": [], "input": {}}]
        loop, provider = self.feedback_fixture(json.dumps({"tools": graph}))
        with self.assertRaises(ToolDependencyError) as caught:
            loop.decide(prompt="request [calc:5*2]", observations=[], provider=provider)
        self.assertEqual(caught.exception.code, "tool_dependency_plan_invalid")
        self.assertEqual(caught.exception.planning_provider_usage.total_tokens, 12)

    def test_agent_feedback_resolved_binding_is_remembered_for_a_later_flat_plan(self):
        loop, provider = self.feedback_fixture(json.dumps({"tools": [calc("5.0*2")]}))
        self.assertTrue(loop.allow_resolved_input(calc("5.0*2")))
        self.assertEqual(loop.decide(prompt="next", observations=[], provider=provider).reason, "repeated_action")

    def test_agent_feedback_binding_identity_waits_for_effective_input_not_node_labels(self):
        loop, provider = self.feedback_fixture(json.dumps({"tools": [calc("3+4")]}))
        self.assertTrue(loop.allow_resolved_input(calc("2+3")))
        self.assertEqual(loop.decide(prompt="next", observations=[], provider=provider).reason, "continue")
        self.assertFalse(loop.allow_resolved_input({**calc("2+3"), "id": "renamed",
            "input_bindings": {"expression": {"node": "new_source", "path": ["result"]}}}))
        self.assertTrue(loop.allow_resolved_input(calc("7.0*2")))

    def test_agent_feedback_same_round_duplicates_and_planner_steps_keep_existing_semantics(self):
        loop, _ = self.feedback_fixture('{"tools": []}')
        self.assertTrue(loop.allow_resolved_input(calc("2+3")))
        self.assertTrue(loop.allow_resolved_input(calc("2+3")))
        loop.round = 2
        self.assertFalse(loop.allow_resolved_input(calc("2+3")))
        planner = {"name": "task_plan", "input": {"prompt": "plan"}}
        self.assertTrue(loop.allow_resolved_input(planner))
        loop.round = 3
        self.assertTrue(loop.allow_resolved_input(planner))

    def test_agent_feedback_same_binding_template_with_new_upstream_result_is_not_a_repeat(self):
        from app.services.tool_plan_dependencies import bind_node_input

        def graph(root_expression):
            return [{**calc(root_expression), "id": "root", "depends_on": []},
                    {**calc("0"), "id": "scaled", "depends_on": ["root"],
                     "input_bindings": {"expression": {"node": "root", "path": ["result"], "template": "{value}*2"}}}]
        registry = runtime.get_default_tool_registry_provider()
        initial = graph("2+3")
        loop = AgentFeedbackLoop(initial_plan=initial, max_rounds=3, registry_provider=registry)
        self.assertTrue(loop.allow_resolved_input(initial[0]))
        self.assertTrue(loop.allow_resolved_input(bind_node_input(initial[1], {"root": {"result": 5.0}})))
        provider = FixtureProvider(json.dumps({"tools": graph("3+4")}))
        decision = loop.decide(prompt="next", observations=[], provider=provider)
        self.assertEqual(decision.reason, "continue")
        self.assertTrue(loop.allow_resolved_input(decision.plan[0]))
        self.assertTrue(loop.allow_resolved_input(bind_node_input(decision.plan[1], {"root": {"result": 7.0}})))

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

    def test_agent_feedback_partial_planning_usage_keeps_unknown_totals(self):
        left = {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12,
                "prompt_tokens_source": "provider", "completion_tokens_source": "provider",
                "usage_source": "provider", "provider_total_tokens": 12, "cost_estimate": 0.01}
        right = {**left, "prompt_tokens": 7, "completion_tokens": None, "total_tokens": None,
                 "completion_tokens_source": None, "provider_total_tokens": 9, "cost_estimate": None}
        result = sum_planning_usage(left, right)
        self.assertEqual(result["prompt_tokens"], 17)
        self.assertEqual(result["provider_total_tokens"], 21)
        self.assertEqual(result["prompt_tokens_source"], "provider")
        for field in ("completion_tokens", "total_tokens", "completion_tokens_source", "cost_estimate"):
            self.assertIsNone(result[field])
