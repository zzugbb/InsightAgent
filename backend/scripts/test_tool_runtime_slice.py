#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.services.tool_runtime as tool_runtime_module  # type: ignore[import-not-found]
import app.services.chat_execution_service as chat_execution_module  # type: ignore[import-not-found]
import app.services.chat_persistence_service as chat_persistence_module  # type: ignore[import-not-found]
import app.api.routes.settings as settings_routes_module  # type: ignore[import-not-found]
import app.api.routes.tasks as task_routes_module  # type: ignore[import-not-found]
import app.api.routes.sessions as session_routes_module  # type: ignore[import-not-found]
import app.db as db_module  # type: ignore[import-not-found]
from app.api.routes.settings import (  # type: ignore[import-not-found]
    _apply_tool_registry_preview_to_validate_response,
    _build_settings_summary_response,
    SettingsValidateResponse,
)
from app.providers.base import ProviderUsage  # type: ignore[import-not-found]
from app.services.settings_service import StoredSettings  # type: ignore[import-not-found]
from app.services.tool_runtime import (  # type: ignore[import-not-found]
    ConfiguredToolRegistryProvider,
    DefaultToolRegistryProvider,
    MockToolExecutionError,
    StaticToolRegistryProvider,
    ToolRegistration,
    build_action_step_initial_meta,
    build_action_step_initial_step,
    build_tool_plan,
    build_tool_plan_artifacts,
    build_tool_attempt_bundle,
    build_tool_attempt_error_events,
    build_tool_attempt_start_events,
    build_tool_attempt_success_events,
    build_tool_attempt_execution,
    build_tool_attempt_loop_result,
    build_tool_attempt_loop_terminal_result,
    build_tool_plan_item_retry_loop_result,
    build_tool_attempt_error_transition,
    build_tool_attempt_outcome,
    build_tool_attempt_result,
    build_tool_iteration_context,
    build_tool_iteration_execution,
    build_tool_plan_item_postprocess,
    build_tool_plan_item_execution,
    build_tool_plan_item_execution_result,
    build_tool_plan_item_stream_effects,
    build_tool_plan_item_continue_action,
    build_tool_plan_item_continue_service_action,
    build_tool_plan_item_next_action_execution,
    build_tool_plan_item_return_service_actions,
    build_tool_plan_item_service_actions,
    build_tool_plan_item_service_execution,
    build_tool_plan_item_service_effects_execution,
    build_tool_plan_item_return_action,
    build_tool_plan_item_trace_write_service_action,
    build_tool_plan_item_trace_write_action,
    execute_tool_plan_item_service_actions,
    execute_tool_plan_item_service_execution,
    execute_tool_plan_item_retry_loop,
    build_tool_registry_provider,
    build_tool_registry_loaders_from_settings,
    build_tool_registry_loader_factories_from_settings,
    build_tool_registry_providers_from_settings,
    build_tool_registry_provider_factories_from_settings,
    build_tool_plan_item_result,
    build_tool_plan_item_success_effects,
    build_tool_plan_item_service_effects,
    build_tool_plan_item_terminal_return_effects,
    build_tool_plan_item_terminal_effects,
    build_tool_plan_item_success_bundle,
    build_tool_iteration_success_artifacts,
    build_tool_rag_followup,
    build_tool_attempt_success_transition,
    build_tool_prompt_with_observations,
    build_tool_rag_step,
    build_tool_end_payload,
    build_tool_error_meta,
    build_tool_error_payload,
    build_tool_execution_policy,
    build_tool_observation_entry,
    build_tool_terminal_failure_transition,
    build_tool_phase,
    build_tool_plan_summary,
    build_tool_start_payload,
    build_tool_step_output,
    build_tool_step_error_update,
    build_tool_step_success_update,
    build_tool_success_meta,
    build_tool_trace_event,
    compute_tool_retry_decision,
    execute_tool_spec,
    get_disabled_tool_names_from_settings,
    get_configured_tool_registry_provider,
    get_default_tool_registry_provider,
    get_default_tool_registry,
    get_tool_registry_provider_source_name_from_settings,
    get_tool_registry_profile_name_from_settings,
    load_tool_registry,
    get_registered_tool_names,
    build_tool_registry,
    build_tool_registry_extra_tools_from_settings,
    build_tool_registry_from_file_artifacts,
    build_tool_registry_from_file,
    build_tool_registry_loader_from_file_artifacts,
    build_tool_registry_loader_from_file,
    build_tool_registry_loaders_from_settings_artifacts,
    build_tool_registry_provider_from_file_artifacts,
    build_tool_registry_provider_sources_from_settings_artifacts,
    build_tool_registry_provider_sources_from_settings,
    build_tool_registry_provider_from_file,
    build_tool_registry_providers_from_settings_artifacts,
    build_tool_registry_overrides_from_settings,
    build_tool_registry_profile_settings_config,
    build_tool_registry_settings_config,
    build_tool_registry_diagnostics_runtime_artifacts,
    build_tool_registry_diagnostics_summary,
    build_tool_registry_diagnostics_runtime_artifacts_model,
    build_tool_registry_diagnostics_summary_model,
    build_tool_registry_diagnostics_trace_service_action_model,
    build_tool_registry_diagnostics_audit_service_action_model,
    build_configured_tool_registry_provider_runtime_service_action_model_from_dict,
    build_configured_tool_registry_provider_runtime_artifacts_model_from_dict,
    build_configured_tool_registry_provider_runtime_artifacts_model,
    build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts,
    build_configured_tool_registry_provider_runtime_service_actions_model,
    build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model,
    build_configured_tool_registry_provider_runtime_service_actions_outputs,
    build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict,
    build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models,
    build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts,
    build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models,
    build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model,
    build_configured_tool_registry_provider_runtime_service_actions_result_model,
    build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict,
    build_configured_tool_registry_provider_service_execution_model_from_dict,
    build_configured_tool_registry_provider_preflight_service_execution_model_from_dict,
    build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict,
    build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model,
    build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload,
    build_configured_tool_registry_provider_preflight_execution_models_from_dict,
    build_configured_tool_registry_provider_preflight_models_from_service_execution_payload,
    build_configured_tool_registry_provider_preflight_models,
    build_configured_tool_registry_provider_preflight_models_from_dict,
    build_configured_tool_registry_provider_preflight_models_from_service_execution_model,
    build_configured_tool_registry_provider_preflight_outputs_from_dict,
    build_configured_tool_registry_provider_preflight_outputs,
    build_configured_tool_registry_provider_preflight_outputs_from_models,
    build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload,
    build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model,
    build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model,
    build_configured_tool_registry_provider_service_execution_model,
    build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model,
    build_configured_tool_registry_provider_service_execution_result_model_from_models,
    build_configured_tool_registry_provider_service_execution_result_model,
    build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model,
    build_configured_tool_registry_provider_service_execution_outputs,
    build_tool_registry_diagnostics_audit_event,
    build_tool_registry_diagnostics_audit_service_action,
    build_tool_registry_diagnostics_trace_service_action,
    build_configured_tool_registry_provider_runtime_service_actions,
    execute_configured_tool_registry_provider_runtime_service_actions_model,
    execute_configured_tool_registry_provider_runtime_service_actions_outputs,
    execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models,
    execute_configured_tool_registry_provider_runtime_service_actions,
    build_configured_tool_registry_provider_service_execution,
    execute_configured_tool_registry_provider_service_execution_model,
    execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model,
    execute_configured_tool_registry_provider_service_execution,
    execute_configured_tool_registry_provider_preflight_models,
    execute_configured_tool_registry_provider_preflight_dicts,
    execute_configured_tool_registry_provider_preflight_outputs,
    execute_configured_tool_registry_provider_preflight_model,
    execute_configured_tool_registry_provider_preflight_summary_model,
    execute_configured_tool_registry_provider_preflight_summary,
    execute_configured_tool_registry_provider_preflight,
    build_configured_tool_registry_provider_preflight_summary_model_from_parts,
    build_configured_tool_registry_provider_preflight_result,
    build_configured_tool_registry_provider_preflight_result_model_from_dict,
    build_configured_tool_registry_provider_preflight_summary,
    build_configured_tool_registry_provider_preflight_dicts,
    build_configured_tool_registry_provider_preflight_summary_model_from_dict,
    build_configured_tool_registry_provider_preflight_summary_model_from_models,
    build_configured_tool_registry_provider_preflight_summary_model_from_result_model,
    build_configured_tool_registry_provider_preflight_models_from_models,
    build_configured_tool_registry_provider_preflight_result_model_from_models,
    build_configured_tool_registry_provider_preflight_result_model,
    build_configured_tool_registry_provider_preflight_summary_model,
    build_tool_result_preview,
    build_tool_runtime_context,
    build_configured_tool_registry_provider_runtime_artifacts,
    ensure_tool_registration,
    get_configured_tool_registry_provider_artifacts,
    get_tool_default_timeout_ms,
    is_tool_retryable_by_default,
    maybe_raise_tool_execution_error,
    maybe_raise_mock_tool_execution_error,
    tool_requires_user_context,
    normalize_tool_spec,
    resolve_tool_registry_provider,
    resolve_tool_registration,
    run_tool,
)


class ToolRuntimeSliceTests(unittest.TestCase):
    def test_build_tool_plan_keeps_calc_and_retrieve_behavior(self) -> None:
        plan = build_tool_plan("请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]")

        self.assertEqual(plan[0]["name"], "task_plan")
        self.assertEqual(plan[1]["name"], "task_retrieve")
        self.assertEqual(plan[1]["input"]["knowledge_base_id"], "demo")
        self.assertEqual(plan[2]["name"], "calc_eval")
        self.assertEqual(plan[2]["input"]["expression"], "1+2*3")

    def test_build_tool_plan_supports_generic_multi_tool_marker(self) -> None:
        plan = build_tool_plan("请先规划再执行 [multi-tool]")

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "task_retrieve"],
        )

    def test_build_tool_plan_respects_registry_provider_when_retrieve_disabled(self) -> None:
        provider = StaticToolRegistryProvider(
            {
                "task_plan": get_default_tool_registry()["task_plan"],
                "calc_eval": get_default_tool_registry()["calc_eval"],
            }
        )

        plan = build_tool_plan(
            "请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]",
            registry_provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "calc_eval"],
        )

    def test_build_tool_plan_respects_planning_only_registry_provider(self) -> None:
        provider = StaticToolRegistryProvider(
            {
                "task_plan": get_default_tool_registry()["task_plan"],
            }
        )

        plan = build_tool_plan(
            "请帮我检索知识库并计算 [calc:1+2*3] [kb:demo] [multi-tool]",
            registry_provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan"],
        )

    def test_build_tool_plan_accepts_provider_generated_json_tools(self) -> None:
        class FakeProvider:
            provider = "openai"
            last_prompt = ""

            def generate(self, prompt: str) -> SimpleNamespace:
                self.last_prompt = prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "task_retrieve",
                                    "input": {
                                        "query": "深入检索并整理背景",
                                        "top_k": 5,
                                        "knowledge_base_id": "kb-provider",
                                    },
                                },
                                {
                                    "name": "calc_eval",
                                    "input": {"expression": "6/2"},
                                },
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

        provider = FakeProvider()
        plan = build_tool_plan(
            "请先检索再计算 [calc:1+2] [kb:demo]",
            provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "task_retrieve", "calc_eval"],
        )
        self.assertEqual(plan[1]["input"]["query"], "深入检索并整理背景")
        self.assertEqual(plan[1]["input"]["top_k"], 5)
        self.assertEqual(plan[1]["input"]["knowledge_base_id"], "kb-provider")
        self.assertEqual(plan[2]["input"]["expression"], "6/2")
        self.assertIn("JSON", provider.last_prompt)

    def test_build_tool_plan_provider_branch_respects_registry_provider(self) -> None:
        class FakeProvider:
            provider = "openai"
            last_prompt = ""

            def generate(self, prompt: str) -> SimpleNamespace:
                self.last_prompt = prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "task_retrieve",
                                    "input": {"query": "应被过滤"},
                                },
                                {
                                    "name": "calc_eval",
                                    "input": {"expression": "6/2"},
                                },
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

        registry_provider = StaticToolRegistryProvider(
            {
                "task_plan": get_default_tool_registry()["task_plan"],
                "calc_eval": get_default_tool_registry()["calc_eval"],
            }
        )
        provider = FakeProvider()
        plan = build_tool_plan(
            "请先检索再计算 [calc:1+2] [kb:demo]",
            provider=provider,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "calc_eval"],
        )
        self.assertNotIn("task_retrieve", provider.last_prompt)
        self.assertIn("Allowed tool names: calc_eval.", provider.last_prompt)

    def test_build_tool_plan_artifacts_capture_provider_usage_for_planning(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "task_retrieve",
                                    "input": {"query": "检索", "top_k": 4},
                                }
                            ]
                        },
                        ensure_ascii=False,
                    ),
                    usage=ProviderUsage(
                        prompt_tokens=21,
                        completion_tokens=7,
                        total_tokens=28,
                    ),
                )

        artifacts = build_tool_plan_artifacts(
            "请先检索",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertIsNotNone(artifacts.provider_usage)
        self.assertEqual(
            artifacts.allowed_tool_names,
            ("task_plan", "task_retrieve", "calc_eval"),
        )
        self.assertEqual(
            artifacts.allowed_tool_labels,
            ("Task Planner", "Knowledge Retrieval", "calc_eval"),
        )
        assert artifacts.provider_usage is not None
        self.assertEqual(artifacts.provider_usage.prompt_tokens, 21)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve"],
        )
        self.assertIn("Allowed tool names", artifacts.planning_prompt or "")

    def test_build_tool_plan_falls_back_when_provider_plan_is_invalid(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                return SimpleNamespace(content="not-json-at-all")

        plan = build_tool_plan(
            "请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]",
            provider=FakeProvider(),
        )

        self.assertEqual(plan[0]["name"], "task_plan")
        self.assertEqual(plan[1]["name"], "task_retrieve")
        self.assertEqual(plan[1]["input"]["knowledge_base_id"], "demo")
        self.assertEqual(plan[2]["name"], "calc_eval")
        self.assertEqual(plan[2]["input"]["expression"], "1+2*3")

    def test_build_tool_plan_artifacts_keep_provider_attempt_metadata_on_fallback(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                return SimpleNamespace(
                    content="not-json-at-all",
                    usage=ProviderUsage(
                        prompt_tokens=13,
                        completion_tokens=5,
                        total_tokens=18,
                    ),
                )

        artifacts = build_tool_plan_artifacts(
            "请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertFalse(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve", "calc_eval"],
        )
        self.assertEqual(
            artifacts.allowed_tool_names,
            ("task_plan", "task_retrieve", "calc_eval"),
        )
        self.assertIsNotNone(artifacts.provider_usage)
        assert artifacts.provider_usage is not None
        self.assertEqual(artifacts.provider_usage.total_tokens, 18)

    def test_build_tool_plan_artifacts_capture_registry_allowed_tools_metadata(self) -> None:
        registry_provider = StaticToolRegistryProvider(
            {
                "task_plan": get_default_tool_registry()["task_plan"],
                "calc_eval": get_default_tool_registry()["calc_eval"],
            }
        )

        artifacts = build_tool_plan_artifacts(
            "请先检索再计算 [calc:1+2]",
            registry_provider=registry_provider,
        )

        self.assertEqual(
            artifacts.allowed_tool_names,
            ("task_plan", "calc_eval"),
        )
        self.assertEqual(
            artifacts.allowed_tool_labels,
            ("Task Planner", "calc_eval"),
        )
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )

    def test_build_settings_summary_response_captures_registry_profile_source_and_enabled_tools(
        self,
    ) -> None:
        summary = _build_settings_summary_response(
            settings=StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile="planning_only",
                tool_registry_provider_source="suite_a",
            ),
            runtime_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_a": {
                            "profile": "planning_only",
                        },
                        "suite_b": {
                            "profile": "calculator_only",
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
            database_locator="postgresql://demo",
        )

        self.assertEqual(summary.mode, "remote")
        self.assertEqual(summary.provider, "openai")
        self.assertEqual(summary.model, "gpt-4.1-mini")
        self.assertEqual(summary.tool_registry_profile, "planning_only")
        self.assertEqual(summary.tool_registry_provider_source, "suite_a")
        self.assertEqual(summary.enabled_tool_names, ["task_plan"])
        self.assertEqual(summary.enabled_tool_labels, ["Task Planner"])
        self.assertEqual(
            summary.available_tool_registry_profiles,
            ["default", "planning_only", "retrieval_only", "calculator_only"],
        )
        self.assertEqual(
            summary.available_tool_registry_provider_sources,
            ["default", "suite_a", "suite_b"],
        )
        self.assertEqual(
            [
                (
                    detail.name,
                    tuple(detail.enabled_tool_labels),
                )
                for detail in summary.available_tool_registry_profile_details
            ],
            [
                ("default", ("Task Planner", "Knowledge Retrieval", "calc_eval")),
                ("planning_only", ("Task Planner",)),
                ("retrieval_only", ("Knowledge Retrieval",)),
                ("calculator_only", ("calc_eval",)),
            ],
        )
        self.assertEqual(
            [
                (
                    detail.name,
                    detail.base_profile,
                    tuple(detail.enabled_tool_labels),
                )
                for detail in summary.available_tool_registry_provider_source_details
            ],
            [
                (
                    "default",
                    "default",
                    ("Task Planner",),
                ),
                (
                    "suite_a",
                    "planning_only",
                    ("Task Planner",),
                ),
                (
                    "suite_b",
                    "calculator_only",
                    ("Calculator",),
                ),
            ],
        )
        self.assertEqual(summary.database_locator, "postgresql://demo")

    def test_apply_tool_registry_preview_to_validate_response_uses_effective_settings(
        self,
    ) -> None:
        response = _apply_tool_registry_preview_to_validate_response(
            result=SettingsValidateResponse(
                ok=True,
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                message="ok",
            ),
            effective_settings=SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_provider_source="suite_a",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_a": {
                            "profile": "planning_only",
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
        )

        self.assertEqual(response.tool_registry_profile, "planning_only")
        self.assertEqual(response.tool_registry_provider_source, "suite_a")
        self.assertEqual(response.enabled_tool_names, ["task_plan"])
        self.assertEqual(response.enabled_tool_labels, ["Task Planner"])
        self.assertEqual(
            [
                (detail.name, tuple(detail.enabled_tool_labels))
                for detail in response.available_tool_registry_profile_details
            ],
            [
                ("default", ("Task Planner", "Knowledge Retrieval", "calc_eval")),
                ("planning_only", ("Task Planner",)),
                ("retrieval_only", ("Knowledge Retrieval",)),
                ("calculator_only", ("calc_eval",)),
            ],
        )
        self.assertEqual(
            [
                (
                    detail.name,
                    detail.base_profile,
                    tuple(detail.enabled_tool_labels),
                )
                for detail in response.available_tool_registry_provider_source_details
            ],
            [
                ("default", "default", ("Task Planner",)),
                ("suite_a", "planning_only", ("Task Planner",)),
            ],
        )

    def test_settings_update_request_reuses_shared_governance_filter_normalizer(
        self,
    ) -> None:
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter
        )
        captured: list[object] = []
        try:
            def fake_normalize_governance_filter(value):
                captured.append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "provider::normalized"
                return None

            chat_persistence_module._normalize_governance_filter = (
                fake_normalize_governance_filter
            )
            payload = settings_routes_module.SettingsUpdateRequest(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url=" https://example.invalid/v1 ",
                api_key=" secret ",
                tool_registry_profile=" Planning_Only ",
                tool_registry_provider_source=" Planning_Suite ",
            )
        finally:
            chat_persistence_module._normalize_governance_filter = (
                original_normalize_governance_filter
            )

        self.assertEqual(captured, [" Planning_Only ", " Planning_Suite "])
        self.assertEqual(payload.tool_registry_profile, "profile::normalized")
        self.assertEqual(
            payload.tool_registry_provider_source,
            "provider::normalized",
        )

    def test_update_settings_reuses_shared_registry_helpers_for_default_fallbacks(
        self,
    ) -> None:
        payload = settings_routes_module.SettingsUpdateRequest(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://example.invalid/v1",
            api_key="secret",
        )
        original_get_stored_settings = settings_routes_module.get_stored_settings
        original_get_settings = settings_routes_module.get_settings
        original_get_tool_registry_profile_name_from_settings = (
            settings_routes_module.get_tool_registry_profile_name_from_settings
        )
        original_get_tool_registry_provider_source_name_from_settings = (
            settings_routes_module.get_tool_registry_provider_source_name_from_settings
        )
        original_get_available_tool_registry_profile_names = (
            settings_routes_module.get_available_tool_registry_profile_names
        )
        original_get_available_tool_registry_provider_source_names = (
            settings_routes_module.get_available_tool_registry_provider_source_names
        )
        original_save_settings = settings_routes_module.save_settings
        original_build_settings_summary_response = (
            settings_routes_module._build_settings_summary_response
        )
        original_safe_record_audit_event = settings_routes_module.safe_record_audit_event
        captured_profiles: list[object] = []
        captured_sources: list[object] = []
        saved_settings: list[StoredSettings] = []
        try:
            settings_routes_module.get_stored_settings = lambda _user_id: StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile=None,
                tool_registry_provider_source=None,
            )
            settings_routes_module.get_settings = lambda: SimpleNamespace(
                tool_registry_profile=" Planning_Only ",
                tool_registry_provider_source=" Planning_Suite ",
            )

            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured_profiles.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "profile::normalized"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            def fake_get_tool_registry_provider_source_name_from_settings(
                *,
                settings=None,
            ):
                captured_sources.append(
                    getattr(settings, "tool_registry_provider_source", None)
                )
                if (
                    getattr(settings, "tool_registry_provider_source", None)
                    == " Planning_Suite "
                ):
                    return "source::normalized"
                return original_get_tool_registry_provider_source_name_from_settings(
                    settings=settings
                )

            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            settings_routes_module.get_tool_registry_provider_source_name_from_settings = (
                fake_get_tool_registry_provider_source_name_from_settings
            )
            settings_routes_module.get_available_tool_registry_profile_names = (
                lambda: ("default", "profile::normalized")
            )
            settings_routes_module.get_available_tool_registry_provider_source_names = (
                lambda *, settings=None: ("default", "source::normalized")
            )
            settings_routes_module.save_settings = lambda _user_id, settings: (
                saved_settings.append(settings) or settings
            )
            settings_routes_module._build_settings_summary_response = (
                lambda *, settings, runtime_settings=None, database_locator=None: settings
            )
            settings_routes_module.safe_record_audit_event = lambda **_kwargs: None

            result = settings_routes_module.update_settings(
                payload,
                current_user={"id": "user-1"},
            )
        finally:
            settings_routes_module.get_stored_settings = original_get_stored_settings
            settings_routes_module.get_settings = original_get_settings
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )
            settings_routes_module.get_tool_registry_provider_source_name_from_settings = (
                original_get_tool_registry_provider_source_name_from_settings
            )
            settings_routes_module.get_available_tool_registry_profile_names = (
                original_get_available_tool_registry_profile_names
            )
            settings_routes_module.get_available_tool_registry_provider_source_names = (
                original_get_available_tool_registry_provider_source_names
            )
            settings_routes_module.save_settings = original_save_settings
            settings_routes_module._build_settings_summary_response = (
                original_build_settings_summary_response
            )
            settings_routes_module.safe_record_audit_event = (
                original_safe_record_audit_event
            )

        self.assertIn(" Planning_Only ", captured_profiles)
        self.assertIn(" Planning_Suite ", captured_sources)
        self.assertEqual(len(saved_settings), 1)
        self.assertEqual(saved_settings[0].tool_registry_profile, "profile::normalized")
        self.assertEqual(
            saved_settings[0].tool_registry_provider_source,
            "source::normalized",
        )
        self.assertEqual(result.tool_registry_profile, "profile::normalized")
        self.assertEqual(result.tool_registry_provider_source, "source::normalized")

    def test_provider_source_option_details_reuse_shared_profile_name_helper(
        self,
    ) -> None:
        original_get_tool_registry_profile_name_from_settings = (
            settings_routes_module.get_tool_registry_profile_name_from_settings
        )
        captured: list[object] = []
        try:
            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "profile::normalized"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            details = settings_routes_module._build_tool_registry_provider_source_option_details(
                effective_settings=SimpleNamespace(
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "suite_a": {
                                "provider": "default",
                                "profile": " Planning_Only ",
                            }
                        }
                    )
                )
            )
        finally:
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )

        suite_a = next(detail for detail in details if detail.name == "suite_a")
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(suite_a.base_profile, "profile::normalized")

    def test_provider_source_option_details_reuse_shared_provider_source_name_helper_for_spec_lookup(
        self,
    ) -> None:
        original_get_tool_registry_provider_source_name_from_settings = (
            settings_routes_module.get_tool_registry_provider_source_name_from_settings
        )
        original_get_tool_registry_profile_name_from_settings = (
            settings_routes_module.get_tool_registry_profile_name_from_settings
        )
        captured_sources: list[object] = []
        captured_profiles: list[object] = []
        try:
            def fake_get_tool_registry_provider_source_name_from_settings(
                *,
                settings=None,
            ):
                captured_sources.append(
                    getattr(settings, "tool_registry_provider_source", None)
                )
                if (
                    getattr(settings, "tool_registry_provider_source", None)
                    == " Suite_A "
                ):
                    return "suite_a"
                return original_get_tool_registry_provider_source_name_from_settings(
                    settings=settings
                )

            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured_profiles.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "profile::normalized"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            settings_routes_module.get_tool_registry_provider_source_name_from_settings = (
                fake_get_tool_registry_provider_source_name_from_settings
            )
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            details = settings_routes_module._build_tool_registry_provider_source_option_details(
                effective_settings=SimpleNamespace(
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            " Suite_A ": {
                                "provider": "default",
                                "profile": " Planning_Only ",
                            }
                        }
                    )
                )
            )
        finally:
            settings_routes_module.get_tool_registry_provider_source_name_from_settings = (
                original_get_tool_registry_provider_source_name_from_settings
            )
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )

        suite_a = next(detail for detail in details if detail.name == "suite_a")
        self.assertIn(" Suite_A ", captured_sources)
        self.assertIn(" Planning_Only ", captured_profiles)
        self.assertEqual(suite_a.base_profile, "profile::normalized")

    def test_build_task_export_payload_surfaces_registry_governance_summary(self) -> None:
        task = {
            "id": "task-export-governance",
            "session_id": "session-export-governance",
            "prompt": "export governance summary",
            "status": "completed",
            "created_at": "2026-06-05T10:00:00",
            "updated_at": "2026-06-05T10:05:00",
            "trace_json": None,
            "usage_json": None,
        }
        original_get_task_trace = task_routes_module.get_task_trace
        original_get_task_messages = task_routes_module.get_task_messages
        try:
            task_routes_module.get_task_trace = lambda *_args, **_kwargs: [
                {
                    "id": "trace-plan-1",
                    "type": "thought",
                    "content": "Planner constrained the tool set.",
                    "seq": 1,
                    "meta": {
                        "tool_registry_profile": "planning_only",
                        "tool_registry_provider_source": "default",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                },
            ]
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []

            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-governance",
            )
        finally:
            task_routes_module.get_task_trace = original_get_task_trace
            task_routes_module.get_task_messages = original_get_task_messages

        self.assertIsNotNone(payload.trace.governance)
        assert payload.trace.governance is not None
        self.assertEqual(payload.trace.governance.profile, "planning_only")
        self.assertEqual(payload.trace.governance.provider_source, "default")
        self.assertEqual(payload.trace.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(
            payload.trace.governance.allowed_tool_labels,
            ["Task Planner"],
        )

    def test_build_task_response_surfaces_registry_governance_summary(self) -> None:
        task = {
            "id": "task-response-governance",
            "session_id": "session-response-governance",
            "prompt": "task response governance summary",
            "status": "completed",
            "created_at": "2026-06-09T10:00:00",
            "updated_at": "2026-06-09T10:05:00",
            "trace_json": json.dumps(
                [
                    {
                        "id": "trace-response-1",
                        "type": "thought",
                        "content": "Planner constrained the tool set.",
                        "seq": 1,
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    },
                ]
            ),
            "usage_json": None,
        }

        payload = task_routes_module._build_task_response(  # type: ignore[attr-defined]
            task,
        )

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(payload.governance.profile, "planning_only")
        self.assertEqual(payload.governance.provider_source, "planning_suite")
        self.assertEqual(payload.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(
            payload.governance.allowed_tool_labels,
            ["Task Planner Suite"],
        )

    def test_build_task_response_prefers_persisted_governance_columns(self) -> None:
        task = {
            "id": "task-response-governance-columns",
            "session_id": "session-response-governance-columns",
            "prompt": "task response governance columns summary",
            "status": "completed",
            "created_at": "2026-06-09T10:00:00",
            "updated_at": "2026-06-09T10:05:00",
            "tool_registry_profile": "planning_only",
            "tool_registry_provider_source": "planning_suite",
            "allowed_tool_names_json": json.dumps(["task_plan"]),
            "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
            "trace_json": None,
            "usage_json": None,
        }

        payload = task_routes_module._build_task_response(  # type: ignore[attr-defined]
            task,
        )

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(payload.governance.profile, "planning_only")
        self.assertEqual(payload.governance.provider_source, "planning_suite")
        self.assertEqual(payload.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(
            payload.governance.allowed_tool_labels,
            ["Task Planner Suite"],
        )

    def test_extract_task_governance_from_trace_steps_reuses_shared_normalizer(self) -> None:
        original_normalizer = chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        try:
            chat_persistence_module._normalize_task_governance_dict = lambda _governance: {  # type: ignore[attr-defined]
                "profile": "normalized_profile",
                "provider_source": "normalized_source",
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            }
            payload = chat_persistence_module._extract_task_governance_from_trace_steps(  # type: ignore[attr-defined]
                [
                    {
                        "id": "trace-normalized-1",
                        "type": "thought",
                        "content": "normalized governance",
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ]
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            payload,
            {
                "profile": "normalized_profile",
                "provider_source": "normalized_source",
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            },
        )

    def test_extract_task_governance_from_trace_steps_forwards_raw_governance_values_to_shared_normalizer(
        self,
    ) -> None:
        original_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_task_governance_dict(governance):
                captured.append(governance)
                return {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }

            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                fake_normalize_task_governance_dict
            )
            chat_persistence_module._extract_task_governance_from_trace_steps(  # type: ignore[attr-defined]
                [
                    {
                        "id": "trace-normalized-raw-1",
                        "type": "thought",
                        "content": "normalized governance",
                        "meta": {
                            "tool_registry_profile": " Planning_Only ",
                            "tool_registry_provider_source": " Planning_Suite ",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ]
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Planning_Suite ",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            ],
        )

    def test_extract_task_governance_from_trace_steps_forwards_raw_allowed_tool_values_to_shared_normalizer(
        self,
    ) -> None:
        original_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_task_governance_dict(governance):
                captured.append(governance)
                return {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }

            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                fake_normalize_task_governance_dict
            )
            chat_persistence_module._extract_task_governance_from_trace_steps(  # type: ignore[attr-defined]
                [
                    {
                        "id": "trace-normalized-raw-tools-1",
                        "type": "thought",
                        "content": "normalized governance",
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": [" task_plan "],
                            "allowed_tool_labels": [" Task Planner Suite "],
                        },
                    }
                ]
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": "planning_only",
                    "provider_source": "planning_suite",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner Suite "],
                }
            ],
        )

    def test_extract_task_governance_from_task_row_reuses_shared_normalizer(self) -> None:
        original_normalizer = chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        try:
            chat_persistence_module._normalize_task_governance_dict = lambda _governance: {  # type: ignore[attr-defined]
                "profile": "normalized_profile",
                "provider_source": "normalized_source",
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            }
            payload = chat_persistence_module._extract_task_governance_from_task_row(  # type: ignore[attr-defined]
                {
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "planning_suite",
                    "allowed_tool_names_json": json.dumps(["task_plan"]),
                    "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                    "trace_json": None,
                }
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            payload,
            {
                "profile": "normalized_profile",
                "provider_source": "normalized_source",
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            },
        )

    def test_extract_task_governance_from_task_row_forwards_raw_governance_values_to_shared_normalizer(
        self,
    ) -> None:
        original_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_task_governance_dict(governance):
                captured.append(governance)
                return {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }

            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                fake_normalize_task_governance_dict
            )
            chat_persistence_module._extract_task_governance_from_task_row(  # type: ignore[attr-defined]
                {
                    "tool_registry_profile": " Planning_Only ",
                    "tool_registry_provider_source": " Planning_Suite ",
                    "allowed_tool_names_json": json.dumps(["task_plan"]),
                    "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                    "trace_json": None,
                }
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Planning_Suite ",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            ],
        )

    def test_extract_task_governance_from_task_row_forwards_raw_allowed_tool_values_to_shared_normalizer(
        self,
    ) -> None:
        original_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_task_governance_dict(governance):
                captured.append(governance)
                return {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }

            chat_persistence_module._normalize_task_governance_dict = (  # type: ignore[attr-defined]
                fake_normalize_task_governance_dict
            )
            chat_persistence_module._extract_task_governance_from_task_row(  # type: ignore[attr-defined]
                {
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "planning_suite",
                    "allowed_tool_names_json": json.dumps([" task_plan "]),
                    "allowed_tool_labels_json": json.dumps([" Task Planner Suite "]),
                    "trace_json": None,
                }
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": "planning_only",
                    "provider_source": "planning_suite",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner Suite "],
                }
            ],
        )

    def test_normalize_task_governance_dict_reuses_shared_governance_filter_normalizer(
        self,
    ) -> None:
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_governance_filter(value):
                captured.append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "source::normalized"
                if not isinstance(value, str):
                    return None
                normalized = value.strip().lower()
                return normalized or None

            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                fake_normalize_governance_filter
            )
            payload = chat_persistence_module._normalize_task_governance_dict(  # type: ignore[attr-defined]
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Planning_Suite ",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner"],
                }
            )
        finally:
            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                original_normalize_governance_filter
            )

        self.assertEqual(captured, [" Planning_Only ", " Planning_Suite "])
        self.assertEqual(
            payload,
            {
                "profile": "profile::normalized",
                "provider_source": "source::normalized",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            },
        )

    def test_normalize_session_governance_summary_reuses_shared_governance_filter_normalizer(
        self,
    ) -> None:
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            def fake_normalize_governance_filter(value):
                captured.append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "source::normalized"
                if not isinstance(value, str):
                    return None
                normalized = value.strip().lower()
                return normalized or None

            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                fake_normalize_governance_filter
            )
            payload = chat_persistence_module._normalize_session_governance_summary_dict(  # type: ignore[attr-defined]
                {
                    "profiles": [" Planning_Only "],
                    "provider_sources": [" Planning_Suite "],
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner"],
                }
            )
        finally:
            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                original_normalize_governance_filter
            )

        self.assertEqual(captured, [" Planning_Only ", " Planning_Suite "])
        self.assertEqual(
            payload,
            {
                "profiles": ["profile::normalized"],
                "provider_sources": ["source::normalized"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            },
        )

    def test_normalize_session_governance_summary_deduplicates_and_sorts_list_fields(
        self,
    ) -> None:
        payload = chat_persistence_module._normalize_session_governance_summary_dict(  # type: ignore[attr-defined]
            {
                "profiles": [" Planning_Only ", "analysis_only", "planning_only"],
                "provider_sources": [
                    " Retrieval_Suite ",
                    "analysis_suite",
                    "retrieval_suite",
                ],
                "allowed_tool_names": [" task_plan ", "calc_eval", "task_plan"],
                "allowed_tool_labels": [
                    " Task Planner ",
                    "Calculator",
                    "Task Planner",
                ],
            }
        )

        self.assertEqual(
            payload,
            {
                "profiles": ["analysis_only", "planning_only"],
                "provider_sources": ["analysis_suite", "retrieval_suite"],
                "allowed_tool_names": ["calc_eval", "task_plan"],
                "allowed_tool_labels": ["Calculator", "Task Planner"],
            },
        )

    def test_merge_session_governance_summary_reuses_shared_task_normalizer(self) -> None:
        original_task_normalizer = chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        try:
            chat_persistence_module._normalize_task_governance_dict = lambda _governance: {  # type: ignore[attr-defined]
                "profile": "normalized_profile",
                "provider_source": "normalized_source",
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            }
            payload = chat_persistence_module._merge_session_governance_summary(  # type: ignore[attr-defined]
                None,
                {
                    "profile": "planning_only",
                    "provider_source": "planning_suite",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                },
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_task_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            payload,
            {
                "profiles": ["normalized_profile"],
                "provider_sources": ["normalized_source"],
                "allowed_tool_names": ["normalized_tool"],
                "allowed_tool_labels": ["Normalized Tool"],
            },
        )

    def test_merge_session_governance_summary_reuses_shared_governance_filter_normalizer(
        self,
    ) -> None:
        original_task_normalizer = (
            chat_persistence_module._normalize_task_governance_dict  # type: ignore[attr-defined]
        )
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter  # type: ignore[attr-defined]
        )
        captured: list[object] = []
        try:
            chat_persistence_module._normalize_task_governance_dict = lambda _governance: {  # type: ignore[attr-defined]
                "profile": " Planning_Only ",
                "provider_source": " Planning_Suite ",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            }

            def fake_normalize_governance_filter(value):
                captured.append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "source::normalized"
                if not isinstance(value, str):
                    return None
                normalized = value.strip().lower()
                return normalized or None

            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                fake_normalize_governance_filter
            )
            payload = chat_persistence_module._merge_session_governance_summary(  # type: ignore[attr-defined]
                None,
                {
                    "profile": "ignored",
                    "provider_source": "ignored",
                    "allowed_tool_names": ["ignored"],
                    "allowed_tool_labels": ["ignored"],
                },
            )
        finally:
            chat_persistence_module._normalize_task_governance_dict = original_task_normalizer  # type: ignore[attr-defined]
            chat_persistence_module._normalize_governance_filter = (  # type: ignore[attr-defined]
                original_normalize_governance_filter
            )

        self.assertEqual(captured, [" Planning_Only ", " Planning_Suite "])
        self.assertEqual(
            payload,
            {
                "profiles": ["profile::normalized"],
                "provider_sources": ["source::normalized"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            },
        )

    def test_merge_session_governance_summary_reuses_shared_session_normalizer(self) -> None:
        original_session_normalizer = chat_persistence_module._normalize_session_governance_summary_dict  # type: ignore[attr-defined]
        try:
            chat_persistence_module._normalize_session_governance_summary_dict = (
                lambda _governance: {
                    "profiles": ["normalized_current_profile"],
                    "provider_sources": ["normalized_current_source"],
                    "allowed_tool_names": ["normalized_current_tool"],
                    "allowed_tool_labels": ["Normalized Current Tool"],
                }
            )
            payload = chat_persistence_module._merge_session_governance_summary(  # type: ignore[attr-defined]
                {
                    "profiles": ["planning_only"],
                    "provider_sources": ["planning_suite"],
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                },
                None,
            )
        finally:
            chat_persistence_module._normalize_session_governance_summary_dict = original_session_normalizer  # type: ignore[attr-defined]

        self.assertEqual(
            payload,
            {
                "profiles": ["normalized_current_profile"],
                "provider_sources": ["normalized_current_source"],
                "allowed_tool_names": ["normalized_current_tool"],
                "allowed_tool_labels": ["Normalized Current Tool"],
            },
        )

    def test_get_tasks_forwards_query_to_list_and_count(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        calls: list[tuple[str, str | None]] = []
        try:
            task_routes_module.get_session = (
                lambda session_id, user_id: {
                    "id": session_id,
                    "user_id": user_id,
                    "title": "Query Session",
                }
            )

            def fake_list_tasks(
                *,
                user_id,
                limit,
                session_id=None,
                offset=0,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                calls.append(("list", query))
                return [
                    {
                        "id": "task-query-1",
                        "session_id": session_id or "session-query",
                        "prompt": "query matched task",
                        "status": "completed",
                        "trace_json": None,
                        "usage_json": None,
                        "created_at": "2026-06-09T11:00:00",
                        "updated_at": "2026-06-09T11:05:00",
                    }
                ]

            def fake_count_tasks(
                user_id,
                session_id=None,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                calls.append(("count", query))
                return 1

            task_routes_module.list_tasks = fake_list_tasks
            task_routes_module.count_tasks = fake_count_tasks

            payload = task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-query",
                query="planning_suite",
                current_user={"id": "user-query"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks

        self.assertEqual(calls, [("list", "planning_suite"), ("count", "planning_suite")])
        self.assertEqual(payload.total, 1)
        self.assertEqual(len(payload.items), 1)

    def test_get_tasks_forwards_governance_filters_to_list_and_count(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        captured: dict[str, object] = {}
        try:
            task_routes_module.get_session = (
                lambda session_id, user_id: {
                    "id": session_id,
                    "user_id": user_id,
                    "title": "Governance Session",
                }
            )

            def fake_list_tasks(
                *,
                user_id,
                limit,
                session_id=None,
                offset=0,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["list"] = {
                    "user_id": user_id,
                    "limit": limit,
                    "session_id": session_id,
                    "offset": offset,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return []

            def fake_count_tasks(
                user_id,
                session_id=None,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["count"] = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return 0

            task_routes_module.list_tasks = fake_list_tasks
            task_routes_module.count_tasks = fake_count_tasks

            task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-governance",
                query=None,
                tool_registry_profile="planning_only",
                tool_registry_provider_source="planning_suite",
                current_user={"id": "user-governance"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks

        self.assertEqual(
            captured["list"],
            {
                "user_id": "user-governance",
                "limit": 20,
                "session_id": "session-governance",
                "offset": 0,
                "query": None,
                "tool_registry_profile_filter": "planning_only",
                "tool_registry_provider_source_filter": "planning_suite",
            },
        )
        self.assertEqual(
            captured["count"],
            {
                "user_id": "user-governance",
                "session_id": "session-governance",
                "query": None,
                "tool_registry_profile_filter": "planning_only",
                "tool_registry_provider_source_filter": "planning_suite",
            },
        )

    def test_get_tasks_reuses_shared_governance_filter_normalizer(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter
        )
        captured: dict[str, object] = {"normalize_inputs": []}
        try:
            task_routes_module.get_session = (
                lambda session_id, user_id: {
                    "id": session_id,
                    "user_id": user_id,
                    "title": "Governance Session",
                }
            )

            def fake_normalize_governance_filter(value):
                captured["normalize_inputs"].append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "provider::normalized"
                return None

            def fake_list_tasks(
                *,
                user_id,
                limit,
                session_id=None,
                offset=0,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["list"] = {
                    "user_id": user_id,
                    "limit": limit,
                    "session_id": session_id,
                    "offset": offset,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return []

            def fake_count_tasks(
                user_id,
                session_id=None,
                query=None,
                tool_registry_profile_filter=None,
                tool_registry_provider_source_filter=None,
            ):
                captured["count"] = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "query": query,
                    "tool_registry_profile_filter": tool_registry_profile_filter,
                    "tool_registry_provider_source_filter": tool_registry_provider_source_filter,
                }
                return 0

            chat_persistence_module._normalize_governance_filter = (
                fake_normalize_governance_filter
            )
            task_routes_module.list_tasks = fake_list_tasks
            task_routes_module.count_tasks = fake_count_tasks

            task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-governance",
                query=None,
                tool_registry_profile=" Planning_Only ",
                tool_registry_provider_source=" Planning_Suite ",
                current_user={"id": "user-governance"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks
            chat_persistence_module._normalize_governance_filter = (
                original_normalize_governance_filter
            )

        self.assertEqual(
            captured["normalize_inputs"],
            [" Planning_Only ", " Planning_Suite "],
        )
        self.assertEqual(
            captured["list"],
            {
                "user_id": "user-governance",
                "limit": 20,
                "session_id": "session-governance",
                "offset": 0,
                "query": None,
                "tool_registry_profile_filter": "profile::normalized",
                "tool_registry_provider_source_filter": "provider::normalized",
            },
        )
        self.assertEqual(
            captured["count"],
            {
                "user_id": "user-governance",
                "session_id": "session-governance",
                "query": None,
                "tool_registry_profile_filter": "profile::normalized",
                "tool_registry_provider_source_filter": "provider::normalized",
            },
        )

    def test_list_tasks_applies_query_to_prompt_id_and_trace_json(self) -> None:
        captured: dict[str, object] = {}

        class FakeCursor:
            def fetchall(self) -> list[dict]:
                return []

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.list_tasks(
                user_id="user-query",
                limit=20,
                session_id="session-query",
                offset=40,
                query="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("LOWER(prompt) LIKE ?", rendered_query)
        self.assertIn("LOWER(id) LIKE ?", rendered_query)
        self.assertIn("LOWER(COALESCE(trace_json, '')) LIKE ?", rendered_query)
        self.assertEqual(
            rendered_params,
            (
                "user-query",
                "session-query",
                "%planning_suite%",
                "%planning_suite%",
                "%planning_suite%",
                20,
                40,
            ),
        )

    def test_list_tasks_applies_governance_filters_to_persisted_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeCursor:
            def fetchall(self) -> list[dict]:
                return []

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.list_tasks(
                user_id="user-governance",
                limit=20,
                session_id="session-governance",
                offset=0,
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", rendered_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            rendered_query,
        )
        self.assertEqual(
            rendered_params,
            (
                "user-governance",
                "session-governance",
                "planning_only",
                "planning_suite",
                20,
                0,
            ),
        )

    def test_count_tasks_applies_governance_filters_to_persisted_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeCursor:
            def fetchone(self) -> dict[str, int]:
                return {"n": 0}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.count_tasks(
                user_id="user-governance",
                session_id="session-governance",
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", rendered_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            rendered_query,
        )
        self.assertEqual(
            rendered_params,
            (
                "user-governance",
                "session-governance",
                "planning_only",
                "planning_suite",
            ),
        )

    def test_task_list_queries_reuse_shared_governance_filter_normalizer(self) -> None:
        original_get_db_connection = chat_persistence_module.get_db_connection
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter
        )
        captured: dict[str, object] = {
            "normalize_inputs": [],
            "queries": [],
        }

        class FakeListCursor:
            def fetchall(self) -> list[dict]:
                return []

        class FakeCountCursor:
            def fetchone(self) -> dict[str, int]:
                return {"n": 0}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["queries"].append((str(query), tuple(params)))
                if "COUNT(*) AS n" in str(query):
                    return FakeCountCursor()
                return FakeListCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        try:
            def fake_normalize_governance_filter(value):
                captured["normalize_inputs"].append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "provider::normalized"
                return None

            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._normalize_governance_filter = (
                fake_normalize_governance_filter
            )

            chat_persistence_module.list_tasks(
                user_id="user-governance",
                limit=20,
                session_id="session-governance",
                offset=0,
                tool_registry_profile_filter=" Planning_Only ",
                tool_registry_provider_source_filter=" Planning_Suite ",
            )
            chat_persistence_module.count_tasks(
                user_id="user-governance",
                session_id="session-governance",
                tool_registry_profile_filter=" Planning_Only ",
                tool_registry_provider_source_filter=" Planning_Suite ",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._normalize_governance_filter = (
                original_normalize_governance_filter
            )

        self.assertEqual(
            captured["normalize_inputs"],
            [
                " Planning_Only ",
                " Planning_Suite ",
                " Planning_Only ",
                " Planning_Suite ",
            ],
        )
        self.assertEqual(len(captured["queries"]), 2)
        list_query, list_params = captured["queries"][0]
        count_query, count_params = captured["queries"][1]
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", list_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            list_query,
        )
        self.assertEqual(
            list_params,
            (
                "user-governance",
                "session-governance",
                "profile::normalized",
                "provider::normalized",
                20,
                0,
            ),
        )
        self.assertIn("LOWER(COALESCE(tool_registry_profile, '')) = ?", count_query)
        self.assertIn(
            "LOWER(COALESCE(tool_registry_provider_source, '')) = ?",
            count_query,
        )
        self.assertEqual(
            count_params,
            (
                "user-governance",
                "session-governance",
                "profile::normalized",
                "provider::normalized",
            ),
        )

    def test_update_task_trace_steps_persists_governance_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return SimpleNamespace(rowcount=1)

            def commit(self) -> None:
                captured["committed"] = True

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.update_task_trace_steps(
                "task-governance-columns",
                [
                    {
                        "id": "trace-1",
                        "type": "thought",
                        "content": "planner constrained tools",
                        "seq": 1,
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "user-governance-columns",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("tool_registry_profile = ?", rendered_query)
        self.assertIn("tool_registry_provider_source = ?", rendered_query)
        self.assertIn("allowed_tool_names_json = ?", rendered_query)
        self.assertIn("allowed_tool_labels_json = ?", rendered_query)
        self.assertEqual(rendered_params[2], "planning_only")
        self.assertEqual(rendered_params[3], "planning_suite")
        self.assertEqual(json.loads(str(rendered_params[4])), ["task_plan"])
        self.assertEqual(json.loads(str(rendered_params[5])), ["Task Planner Suite"])

    def test_complete_task_persists_governance_columns(self) -> None:
        captured: dict[str, object] = {}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["query"] = query
                captured["params"] = tuple(params)
                return SimpleNamespace(rowcount=1)

            def commit(self) -> None:
                captured["committed"] = True

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.complete_task(
                "task-complete-governance-columns",
                [
                    {
                        "id": "trace-1",
                        "type": "thought",
                        "content": "planner constrained tools",
                        "seq": 1,
                        "meta": {
                            "tool_registry_profile": "planning_only",
                            "tool_registry_provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "user-governance-columns",
                usage={"prompt_tokens": 1, "completion_tokens": 2},
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        rendered_query = str(captured.get("query", ""))
        rendered_params = tuple(captured.get("params", ()))
        self.assertIn("tool_registry_profile = ?", rendered_query)
        self.assertIn("tool_registry_provider_source = ?", rendered_query)
        self.assertIn("allowed_tool_names_json = ?", rendered_query)
        self.assertIn("allowed_tool_labels_json = ?", rendered_query)
        self.assertEqual(rendered_params[4], "planning_only")
        self.assertEqual(rendered_params[5], "planning_suite")
        self.assertEqual(json.loads(str(rendered_params[6])), ["task_plan"])
        self.assertEqual(json.loads(str(rendered_params[7])), ["Task Planner Suite"])

    def test_initialize_postgres_database_ensures_task_governance_columns(self) -> None:
        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return SimpleNamespace(rowcount=0)

            def commit(self) -> None:
                return None

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = db_module.get_db_connection
        original_ensure_column = db_module._ensure_postgres_column
        original_ensure_indexes = db_module._ensure_common_indexes
        calls: list[tuple[str, str, str]] = []
        try:
            db_module.get_db_connection = lambda: FakeContextManager()
            db_module._ensure_postgres_column = (
                lambda connection, table, column, definition: calls.append(
                    (table, column, definition)
                )
            )
            db_module._ensure_common_indexes = lambda connection: None
            db_module.initialize_postgres_database()
        finally:
            db_module.get_db_connection = original_get_db_connection
            db_module._ensure_postgres_column = original_ensure_column
            db_module._ensure_common_indexes = original_ensure_indexes

        self.assertIn(("tasks", "tool_registry_profile", "TEXT"), calls)
        self.assertIn(("tasks", "tool_registry_provider_source", "TEXT"), calls)
        self.assertIn(("tasks", "allowed_tool_names_json", "TEXT"), calls)
        self.assertIn(("tasks", "allowed_tool_labels_json", "TEXT"), calls)

    def test_collect_task_governance_from_trace_json_returns_summary(self) -> None:
        trace_json = json.dumps(
            [
                {
                    "id": "trace-governance-1",
                    "type": "thought",
                    "content": "planner constrained tools",
                    "seq": 1,
                    "meta": {
                        "tool_registry_profile": "planning_only",
                        "tool_registry_provider_source": "planning_suite",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner Suite"],
                    },
                }
            ]
        )

        payload = task_routes_module._collect_task_governance_from_trace_json(  # type: ignore[attr-defined]
            trace_json,
        )

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profile, "planning_only")
        self.assertEqual(payload.provider_source, "planning_suite")
        self.assertEqual(payload.allowed_tool_names, ["task_plan"])
        self.assertEqual(payload.allowed_tool_labels, ["Task Planner Suite"])

    def test_collect_task_governance_from_trace_json_reuses_shared_service_parser(self) -> None:
        original_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_trace_json
        )
        try:
            task_routes_module.chat_persistence_service._extract_task_governance_from_trace_json = (
                lambda _trace_json: {
                    "profile": "shared_trace_profile",
                    "provider_source": "shared_trace_source",
                    "allowed_tool_names": ["shared_trace_tool"],
                    "allowed_tool_labels": ["Shared Trace Tool"],
                }
            )
            payload = task_routes_module._collect_task_governance_from_trace_json(  # type: ignore[attr-defined]
                "[]"
            )
        finally:
            task_routes_module.chat_persistence_service._extract_task_governance_from_trace_json = (
                original_parser
            )

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profile, "shared_trace_profile")
        self.assertEqual(payload.provider_source, "shared_trace_source")
        self.assertEqual(payload.allowed_tool_names, ["shared_trace_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Shared Trace Tool"])

    def test_collect_task_governance_from_trace_json_reuses_clone_builder(self) -> None:
        original_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_trace_json
        )
        original_dict_builder = task_routes_module._build_task_governance_summary_from_dict  # type: ignore[attr-defined]
        original_clone_builder = task_routes_module._build_task_governance_summary_from_clone  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            task_routes_module.chat_persistence_service._extract_task_governance_from_trace_json = (
                lambda _trace_json: {
                    "profile": "shared_trace_profile",
                    "provider_source": "shared_trace_source",
                    "allowed_tool_names": ["shared_trace_tool"],
                    "allowed_tool_labels": ["Shared Trace Tool"],
                }
            )
            task_routes_module._build_task_governance_summary_from_dict = lambda _governance: task_routes_module.TaskGovernanceSummary(  # type: ignore[attr-defined]
                profile="dict_profile",
                provider_source="dict_source",
                allowed_tool_names=["dict_tool"],
                allowed_tool_labels=["Dict Tool"],
            )
            task_routes_module._build_task_governance_summary_from_clone = lambda governance: captured.append(  # type: ignore[attr-defined]
                governance
            ) or task_routes_module.TaskGovernanceSummary(
                profile="clone_profile",
                provider_source="clone_source",
                allowed_tool_names=["clone_tool"],
                allowed_tool_labels=["Clone Tool"],
            )
            payload = task_routes_module._collect_task_governance_from_trace_json(  # type: ignore[attr-defined]
                "[]"
            )
        finally:
            task_routes_module.chat_persistence_service._extract_task_governance_from_trace_json = (
                original_parser
            )
            task_routes_module._build_task_governance_summary_from_dict = original_dict_builder  # type: ignore[attr-defined]
            task_routes_module._build_task_governance_summary_from_clone = original_clone_builder  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": "shared_trace_profile",
                    "provider_source": "shared_trace_source",
                    "allowed_tool_names": ["shared_trace_tool"],
                    "allowed_tool_labels": ["Shared Trace Tool"],
                }
            ],
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profile, "clone_profile")
        self.assertEqual(payload.provider_source, "clone_source")
        self.assertEqual(payload.allowed_tool_names, ["clone_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Clone Tool"])

    def test_build_task_response_reuses_governance_summary_builder(self) -> None:
        original_builder = task_routes_module._build_task_governance_summary_from_clone  # type: ignore[attr-defined]
        try:
            task_routes_module._build_task_governance_summary_from_clone = lambda _governance: task_routes_module.TaskGovernanceSummary(  # type: ignore[attr-defined]
                profile="builder_profile",
                provider_source="builder_source",
                allowed_tool_names=["builder_tool"],
                allowed_tool_labels=["Builder Tool"],
            )
            response = task_routes_module._build_task_response(  # type: ignore[attr-defined]
                {
                    "id": "task-builder-governance-route",
                    "session_id": "session-builder-governance-route",
                    "prompt": "builder governance route task",
                    "status": "completed",
                    "trace_json": None,
                    "usage_json": None,
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "default",
                    "allowed_tool_names_json": json.dumps(["task_plan"]),
                    "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                    "created_at": "2026-06-11T15:00:00",
                    "updated_at": "2026-06-11T15:01:00",
                }
            )
        finally:
            task_routes_module._build_task_governance_summary_from_clone = original_builder  # type: ignore[attr-defined]

        self.assertIsNotNone(response.governance)
        assert response.governance is not None
        self.assertEqual(response.governance.profile, "builder_profile")
        self.assertEqual(response.governance.provider_source, "builder_source")
        self.assertEqual(response.governance.allowed_tool_names, ["builder_tool"])
        self.assertEqual(response.governance.allowed_tool_labels, ["Builder Tool"])

    def test_collect_task_governance_from_task_reuses_clone_builder(self) -> None:
        original_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        original_dict_builder = task_routes_module._build_task_governance_summary_from_dict  # type: ignore[attr-defined]
        original_clone_builder = task_routes_module._build_task_governance_summary_from_clone  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: {
                    "profile": "shared_profile",
                    "provider_source": "shared_source",
                    "allowed_tool_names": ["shared_tool"],
                    "allowed_tool_labels": ["Shared Tool"],
                }
            )
            task_routes_module._build_task_governance_summary_from_dict = lambda _governance: task_routes_module.TaskGovernanceSummary(  # type: ignore[attr-defined]
                profile="dict_profile",
                provider_source="dict_source",
                allowed_tool_names=["dict_tool"],
                allowed_tool_labels=["Dict Tool"],
            )
            task_routes_module._build_task_governance_summary_from_clone = lambda governance: captured.append(  # type: ignore[attr-defined]
                governance
            ) or task_routes_module.TaskGovernanceSummary(
                profile="clone_profile",
                provider_source="clone_source",
                allowed_tool_names=["clone_tool"],
                allowed_tool_labels=["Clone Tool"],
            )
            payload = task_routes_module._collect_task_governance_from_task(  # type: ignore[attr-defined]
                {
                    "id": "task-collect-governance-clone-route",
                    "session_id": "session-collect-governance-clone-route",
                    "prompt": "shared governance route task",
                    "status": "completed",
                    "trace_json": None,
                    "usage_json": None,
                    "created_at": "2026-06-11T12:00:00",
                    "updated_at": "2026-06-11T12:01:00",
                }
            )
        finally:
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_parser
            )
            task_routes_module._build_task_governance_summary_from_dict = original_dict_builder  # type: ignore[attr-defined]
            task_routes_module._build_task_governance_summary_from_clone = original_clone_builder  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": "shared_profile",
                    "provider_source": "shared_source",
                    "allowed_tool_names": ["shared_tool"],
                    "allowed_tool_labels": ["Shared Tool"],
                }
            ],
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profile, "clone_profile")
        self.assertEqual(payload.provider_source, "clone_source")
        self.assertEqual(payload.allowed_tool_names, ["clone_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Clone Tool"])

    def test_build_task_response_reuses_shared_task_governance_normalizer(self) -> None:
        original_normalizer = task_routes_module.chat_persistence_service._normalize_task_governance_dict  # type: ignore[attr-defined]
        try:
            task_routes_module.chat_persistence_service._normalize_task_governance_dict = (
                lambda _governance: {
                    "profile": "normalized_profile",
                    "provider_source": "normalized_source",
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }
            )
            response = task_routes_module._build_task_response(  # type: ignore[attr-defined]
                {
                    "id": "task-normalized-governance-route",
                    "session_id": "session-normalized-governance-route",
                    "prompt": "normalized governance route task",
                    "status": "completed",
                    "trace_json": None,
                    "usage_json": None,
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "default",
                    "allowed_tool_names_json": json.dumps(["task_plan"]),
                    "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                    "created_at": "2026-06-11T16:00:00",
                    "updated_at": "2026-06-11T16:01:00",
                }
            )
        finally:
            task_routes_module.chat_persistence_service._normalize_task_governance_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertIsNotNone(response.governance)
        assert response.governance is not None
        self.assertEqual(response.governance.profile, "normalized_profile")
        self.assertEqual(response.governance.provider_source, "normalized_source")
        self.assertEqual(response.governance.allowed_tool_names, ["normalized_tool"])
        self.assertEqual(response.governance.allowed_tool_labels, ["Normalized Tool"])

    def test_build_task_governance_summary_from_dict_reuses_shared_clone_helper(
        self,
    ) -> None:
        original_cloner = task_routes_module.chat_persistence_service._clone_task_governance_dict  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            task_routes_module.chat_persistence_service._clone_task_governance_dict = (
                lambda governance: captured.append(governance)
                or {
                    "profile": "shared_profile",
                    "provider_source": "shared_source",
                    "allowed_tool_names": ["shared_tool"],
                    "allowed_tool_labels": ["Shared Tool"],
                }
            )
            payload = task_routes_module._build_task_governance_summary_from_dict(  # type: ignore[attr-defined]
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Default ",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner "],
                }
            )
        finally:
            task_routes_module.chat_persistence_service._clone_task_governance_dict = (
                original_cloner
            )

        self.assertEqual(
            captured,
            [
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Default ",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner "],
                }
            ],
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profile, "shared_profile")
        self.assertEqual(payload.provider_source, "shared_source")
        self.assertEqual(payload.allowed_tool_names, ["shared_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Shared Tool"])

    def test_get_tasks_usage_dashboard_top_task_surfaces_governance_summary(self) -> None:
        rows = [
            {
                "id": "task-usage-governance-1",
                "session_id": "session-usage-governance",
                "prompt": "usage dashboard governance task",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 12,
                        "completion_tokens": 34,
                        "cost_estimate": 0.12,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-governance-1",
                            "type": "thought",
                            "content": "Planner constrained the task.",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "planning_only",
                                "tool_registry_provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T10:00:00",
                "updated_at": "2026-06-09T10:05:00",
                "session_title": "Usage Governance Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-governance",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        top_tasks = payload["top_tasks"]
        self.assertEqual(len(top_tasks), 1)
        row = top_tasks[0]
        self.assertEqual(row["task_id"], "task-usage-governance-1")
        self.assertEqual(row["source_kind"], "provider")
        self.assertEqual(
            row["governance"],
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_top_task_prefers_persisted_governance_columns(self) -> None:
        rows = [
            {
                "id": "task-usage-governance-columns-1",
                "session_id": "session-usage-governance-columns",
                "prompt": "usage dashboard governance task with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 12,
                        "completion_tokens": 34,
                        "cost_estimate": 0.12,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Usage Governance Columns Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-governance-columns",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        top_tasks = payload["top_tasks"]
        self.assertEqual(len(top_tasks), 1)
        row = top_tasks[0]
        self.assertEqual(
            row["governance"],
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_route_surfaces_top_task_governance_summary(self) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [],
                "top_tasks": [
                    {
                        "task_id": "task-usage-governance-1",
                        "session_id": "session-usage-governance",
                        "session_title": "Usage Governance Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-09T10:00:00",
                        "updated_at": "2026-06-09T10:05:00",
                        "source_kind": "provider",
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
            }

            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-governance"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard

        self.assertEqual(len(payload.top_tasks), 1)
        row = payload.top_tasks[0]
        self.assertEqual(row.source_kind, "provider")
        self.assertIsNotNone(row.governance)
        assert row.governance is not None
        self.assertEqual(row.governance.profile, "planning_only")
        self.assertEqual(row.governance.provider_source, "planning_suite")
        self.assertEqual(row.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(row.governance.allowed_tool_labels, ["Task Planner Suite"])

    def test_build_task_usage_top_task_row_prefers_persisted_governance_columns(self) -> None:
        row = task_routes_module._build_task_usage_top_task_row(  # type: ignore[attr-defined]
            {
                "task_id": "task-usage-top-columns-1",
                "session_id": "session-usage-top-columns",
                "session_title": "Usage Governance Columns Session",
                "prompt_excerpt": "usage dashboard governance task",
                "total_tokens": 46,
                "cost_estimate": 0.12,
                "created_at": "2026-06-11T10:00:00",
                "updated_at": "2026-06-11T10:05:00",
                "source_kind": "provider",
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "trace_json": None,
            }
        )

        self.assertIsNotNone(row.governance)
        assert row.governance is not None
        self.assertEqual(row.governance.profile, "planning_only")
        self.assertEqual(row.governance.provider_source, "planning_suite")
        self.assertEqual(row.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(row.governance.allowed_tool_labels, ["Task Planner Suite"])

    def test_build_task_usage_top_task_row_reuses_governance_summary_builder(self) -> None:
        original_builder = task_routes_module._build_task_governance_summary_from_clone  # type: ignore[attr-defined]
        try:
            task_routes_module._build_task_governance_summary_from_clone = lambda _governance: task_routes_module.TaskGovernanceSummary(  # type: ignore[attr-defined]
                profile="builder_profile",
                provider_source="builder_source",
                allowed_tool_names=["builder_tool"],
                allowed_tool_labels=["Builder Tool"],
            )
            row = task_routes_module._build_task_usage_top_task_row(  # type: ignore[attr-defined]
                {
                    "task_id": "task-usage-top-builder-1",
                    "session_id": "session-usage-top-builder",
                    "session_title": "Usage Governance Builder Session",
                    "prompt_excerpt": "usage dashboard governance task",
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "created_at": "2026-06-11T10:00:00",
                    "updated_at": "2026-06-11T10:05:00",
                    "source_kind": "provider",
                    "governance": {
                        "profile": "planning_only",
                        "provider_source": "planning_suite",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner Suite"],
                    },
                    "trace_json": None,
                }
            )
        finally:
            task_routes_module._build_task_governance_summary_from_clone = original_builder  # type: ignore[attr-defined]

        self.assertIsNotNone(row.governance)
        assert row.governance is not None
        self.assertEqual(row.governance.profile, "builder_profile")
        self.assertEqual(row.governance.provider_source, "builder_source")
        self.assertEqual(row.governance.allowed_tool_names, ["builder_tool"])
        self.assertEqual(row.governance.allowed_tool_labels, ["Builder Tool"])

    def test_build_task_usage_top_task_row_reuses_clone_builder(self) -> None:
        original_builder = task_routes_module._build_task_governance_summary_from_clone  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            task_routes_module._build_task_governance_summary_from_clone = lambda governance: captured.append(  # type: ignore[attr-defined]
                governance
            ) or task_routes_module.TaskGovernanceSummary(
                profile="builder_profile",
                provider_source="builder_source",
                allowed_tool_names=["builder_tool"],
                allowed_tool_labels=["Builder Tool"],
            )
            row = task_routes_module._build_task_usage_top_task_row(  # type: ignore[attr-defined]
                {
                    "task_id": "task-usage-top-clone-builder-1",
                    "session_id": "session-usage-top-clone-builder",
                    "session_title": "Usage Governance Clone Builder Session",
                    "prompt_excerpt": "usage dashboard governance task",
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "created_at": "2026-06-11T10:00:00",
                    "updated_at": "2026-06-11T10:05:00",
                    "source_kind": "provider",
                    "governance": {
                        "profile": "planning_only",
                        "provider_source": "planning_suite",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner Suite"],
                    },
                    "trace_json": None,
                }
            )
        finally:
            task_routes_module._build_task_governance_summary_from_clone = original_builder  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": "planning_only",
                    "provider_source": "planning_suite",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            ],
        )
        self.assertIsNotNone(row.governance)
        assert row.governance is not None
        self.assertEqual(row.governance.profile, "builder_profile")
        self.assertEqual(row.governance.provider_source, "builder_source")
        self.assertEqual(row.governance.allowed_tool_names, ["builder_tool"])
        self.assertEqual(row.governance.allowed_tool_labels, ["Builder Tool"])

    def test_get_tasks_usage_dashboard_by_session_surfaces_governance_summary(self) -> None:
        rows = [
            {
                "id": "task-usage-session-governance-1",
                "session_id": "session-usage-governance",
                "prompt": "usage session governance task",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 20,
                        "completion_tokens": 30,
                        "cost_estimate": 0.15,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-session-governance-1",
                            "type": "thought",
                            "content": "Planner constrained the task.",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "planning_only",
                                "tool_registry_provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T10:00:00",
                "updated_at": "2026-06-09T10:05:00",
                "session_title": "Usage Governance Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-session-governance",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        by_session = payload["by_session"]
        self.assertEqual(len(by_session), 1)
        row = by_session[0]
        self.assertEqual(row["session_id"], "session-usage-governance")
        self.assertEqual(
            row["governance"],
            {
                "profiles": ["planning_only"],
                "provider_sources": ["planning_suite"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_by_session_prefers_persisted_governance_columns(self) -> None:
        rows = [
            {
                "id": "task-usage-session-governance-columns-1",
                "session_id": "session-usage-governance-columns",
                "prompt": "usage session governance task with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 20,
                        "completion_tokens": 30,
                        "cost_estimate": 0.15,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Usage Governance Columns Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-session-governance-columns",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        by_session = payload["by_session"]
        self.assertEqual(len(by_session), 1)
        row = by_session[0]
        self.assertEqual(
            row["governance"],
            {
                "profiles": ["planning_only"],
                "provider_sources": ["planning_suite"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_route_surfaces_session_governance_summary(self) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 20,
                    "completion_tokens": 30,
                    "total_tokens": 50,
                    "cost_estimate": 0.15,
                    "avg_total_tokens": 50.0,
                    "avg_cost_estimate": 0.15,
                },
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-governance",
                        "session_title": "Usage Governance Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 50,
                        "cost_estimate": 0.15,
                        "last_task_at": "2026-06-09T10:05:00",
                        "governance": {
                            "profiles": ["planning_only"],
                            "provider_sources": ["planning_suite"],
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "top_tasks": [],
            }

            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-session-governance"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard

        self.assertEqual(len(payload.by_session), 1)
        row = payload.by_session[0]
        self.assertIsNotNone(row.governance)
        assert row.governance is not None
        self.assertEqual(row.governance.profiles, ["planning_only"])
        self.assertEqual(row.governance.provider_sources, ["planning_suite"])
        self.assertEqual(row.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(row.governance.allowed_tool_labels, ["Task Planner Suite"])

    def test_build_task_usage_by_session_row_reuses_governance_summary_builder(self) -> None:
        original_builder = task_routes_module._build_task_usage_session_governance_summary_from_clone  # type: ignore[attr-defined]
        try:
            task_routes_module._build_task_usage_session_governance_summary_from_clone = lambda _governance: task_routes_module.TaskUsageSessionGovernanceSummary(  # type: ignore[attr-defined]
                profiles=["builder_profile"],
                provider_sources=["builder_source"],
                allowed_tool_names=["builder_tool"],
                allowed_tool_labels=["Builder Tool"],
            )
            row = task_routes_module._build_task_usage_by_session_row(  # type: ignore[attr-defined]
                {
                    "session_id": "session-usage-builder",
                    "session_title": "Usage Governance Builder Session",
                    "tasks_with_usage": 1,
                    "total_tokens": 50,
                    "cost_estimate": 0.15,
                    "last_task_at": "2026-06-09T10:05:00",
                    "governance": {
                        "profiles": ["planning_only"],
                        "provider_sources": ["planning_suite"],
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner Suite"],
                    },
                }
            )
        finally:
            task_routes_module._build_task_usage_session_governance_summary_from_clone = original_builder  # type: ignore[attr-defined]

        self.assertIsNotNone(row.governance)
        assert row.governance is not None
        self.assertEqual(row.governance.profiles, ["builder_profile"])
        self.assertEqual(row.governance.provider_sources, ["builder_source"])
        self.assertEqual(row.governance.allowed_tool_names, ["builder_tool"])
        self.assertEqual(row.governance.allowed_tool_labels, ["Builder Tool"])

    def test_build_task_usage_session_governance_summary_from_dict_reuses_shared_clone_helper(
        self,
    ) -> None:
        original_clone_helper = getattr(
            task_routes_module.chat_persistence_service,
            "_clone_session_governance_summary_dict",
            None,
        )
        captured: list[object] = []
        try:
            task_routes_module.chat_persistence_service._clone_session_governance_summary_dict = (  # type: ignore[attr-defined]
                lambda governance: captured.append(governance) or {
                    "profiles": ["clone_profile"],
                    "provider_sources": ["clone_source"],
                    "allowed_tool_names": ["clone_tool"],
                    "allowed_tool_labels": ["Clone Tool"],
                }
            )
            payload = task_routes_module._build_task_usage_session_governance_summary_from_dict(  # type: ignore[attr-defined]
                {
                    "profiles": ["planning_only"],
                    "provider_sources": ["planning_suite"],
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            )
        finally:
            if original_clone_helper is None:
                delattr(
                    task_routes_module.chat_persistence_service,
                    "_clone_session_governance_summary_dict",
                )
            else:
                task_routes_module.chat_persistence_service._clone_session_governance_summary_dict = original_clone_helper  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profiles": ["planning_only"],
                    "provider_sources": ["planning_suite"],
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            ],
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profiles, ["clone_profile"])
        self.assertEqual(payload.provider_sources, ["clone_source"])
        self.assertEqual(payload.allowed_tool_names, ["clone_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Clone Tool"])

    def test_build_task_usage_by_session_row_reuses_clone_builder(self) -> None:
        original_builder = task_routes_module._build_task_usage_session_governance_summary_from_clone  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            task_routes_module._build_task_usage_session_governance_summary_from_clone = lambda governance: captured.append(  # type: ignore[attr-defined]
                governance
            ) or task_routes_module.TaskUsageSessionGovernanceSummary(
                profiles=["builder_profile"],
                provider_sources=["builder_source"],
                allowed_tool_names=["builder_tool"],
                allowed_tool_labels=["Builder Tool"],
            )
            row = task_routes_module._build_task_usage_by_session_row(  # type: ignore[attr-defined]
                {
                    "session_id": "session-usage-clone-builder",
                    "session_title": "Usage Governance Clone Builder Session",
                    "tasks_with_usage": 1,
                    "total_tokens": 50,
                    "cost_estimate": 0.15,
                    "last_task_at": "2026-06-09T10:05:00",
                    "governance": {
                        "profiles": ["planning_only"],
                        "provider_sources": ["planning_suite"],
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner Suite"],
                    },
                }
            )
        finally:
            task_routes_module._build_task_usage_session_governance_summary_from_clone = original_builder  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profiles": ["planning_only"],
                    "provider_sources": ["planning_suite"],
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            ],
        )
        self.assertIsNotNone(row.governance)
        assert row.governance is not None
        self.assertEqual(row.governance.profiles, ["builder_profile"])
        self.assertEqual(row.governance.provider_sources, ["builder_source"])
        self.assertEqual(row.governance.allowed_tool_names, ["builder_tool"])
        self.assertEqual(row.governance.allowed_tool_labels, ["Builder Tool"])

    def test_build_task_usage_session_governance_summary_from_dict_reuses_shared_session_governance_normalizer(
        self,
    ) -> None:
        original_normalizer = task_routes_module.chat_persistence_service._normalize_session_governance_summary_dict  # type: ignore[attr-defined]
        try:
            task_routes_module.chat_persistence_service._normalize_session_governance_summary_dict = (
                lambda _governance: {
                    "profiles": ["normalized_profile"],
                    "provider_sources": ["normalized_source"],
                    "allowed_tool_names": ["normalized_tool"],
                    "allowed_tool_labels": ["Normalized Tool"],
                }
            )
            payload = task_routes_module._build_task_usage_session_governance_summary_from_dict(  # type: ignore[attr-defined]
                {
                    "profiles": ["planning_only"],
                    "provider_sources": ["planning_suite"],
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            )
        finally:
            task_routes_module.chat_persistence_service._normalize_session_governance_summary_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profiles, ["normalized_profile"])
        self.assertEqual(payload.provider_sources, ["normalized_source"])
        self.assertEqual(payload.allowed_tool_names, ["normalized_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Normalized Tool"])

    def test_get_tasks_usage_dashboard_filters_by_profile_and_provider_source(self) -> None:
        rows = [
            {
                "id": "task-usage-filtered-1",
                "session_id": "session-usage-filtered-1",
                "prompt": "planning suite dashboard row",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-filtered-1",
                            "type": "thought",
                            "content": "planner constrained task",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "planning_only",
                                "tool_registry_provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T10:00:00",
                "updated_at": "2026-06-09T10:05:00",
                "session_title": "Planning Session",
            },
            {
                "id": "task-usage-filtered-2",
                "session_id": "session-usage-filtered-2",
                "prompt": "retrieval suite dashboard row",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 8,
                        "completion_tokens": 12,
                        "cost_estimate": 0.03,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-filtered-2",
                            "type": "thought",
                            "content": "retrieval constrained task",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "retrieval_only",
                                "tool_registry_provider_source": "retrieval_suite",
                                "allowed_tool_names": ["task_retrieve"],
                                "allowed_tool_labels": ["Knowledge Retrieval Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T11:00:00",
                "updated_at": "2026-06-09T11:05:00",
                "session_title": "Retrieval Session",
            },
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered",
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(payload["by_session"][0]["session_id"], "session-usage-filtered-1")
        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertEqual(payload["top_tasks"][0]["task_id"], "task-usage-filtered-1")

    def test_get_tasks_usage_dashboard_filters_by_persisted_profile_and_provider_source(self) -> None:
        rows = [
            {
                "id": "task-usage-filtered-columns-1",
                "session_id": "session-usage-filtered-columns-1",
                "prompt": "planning suite dashboard row with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Planning Session",
            },
            {
                "id": "task-usage-filtered-columns-2",
                "session_id": "session-usage-filtered-columns-2",
                "prompt": "retrieval suite dashboard row with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 8,
                        "completion_tokens": 12,
                        "cost_estimate": 0.03,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "retrieval_only",
                "tool_registry_provider_source": "retrieval_suite",
                "allowed_tool_names_json": json.dumps(["task_retrieve"]),
                "allowed_tool_labels_json": json.dumps(["Knowledge Retrieval Suite"]),
                "created_at": "2026-06-10T11:00:00",
                "updated_at": "2026-06-10T11:05:00",
                "session_title": "Retrieval Session",
            },
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered-columns",
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(
            payload["by_session"][0]["session_id"],
            "session-usage-filtered-columns-1",
        )
        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertEqual(
            payload["top_tasks"][0]["task_id"],
            "task-usage-filtered-columns-1",
        )

    def test_get_tasks_usage_dashboard_reuses_shared_governance_filter_normalizer_for_task_match(
        self,
    ) -> None:
        rows = [
            {
                "id": "task-usage-filtered-normalizer-1",
                "session_id": "session-usage-filtered-normalizer-1",
                "prompt": "planning suite dashboard row with shared normalizer",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Planning Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter
        )
        captured: dict[str, object] = {"normalize_inputs": []}
        try:
            def fake_normalize_governance_filter(value):
                captured["normalize_inputs"].append(value)
                if value in {
                    " Planning_Only ",
                    "planning_only",
                    "profile::normalized",
                }:
                    return "profile::normalized"
                if value in {
                    " Planning_Suite ",
                    "planning_suite",
                    "provider::normalized",
                }:
                    return "provider::normalized"
                return None

            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._normalize_governance_filter = (
                fake_normalize_governance_filter
            )
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered-normalizer",
                tool_registry_profile_filter=" Planning_Only ",
                tool_registry_provider_source_filter=" Planning_Suite ",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._normalize_governance_filter = (
                original_normalize_governance_filter
            )

        normalize_inputs = list(captured["normalize_inputs"])
        self.assertEqual(
            normalize_inputs[:4],
            [
                " Planning_Only ",
                " Planning_Suite ",
                "planning_only",
                "planning_suite",
            ],
        )
        self.assertGreaterEqual(normalize_inputs.count("profile::normalized"), 1)
        self.assertGreaterEqual(normalize_inputs.count("provider::normalized"), 1)
        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(len(payload["top_tasks"]), 1)

    def test_get_tasks_usage_dashboard_route_forwards_governance_filters(self) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_normalize_governance_filter = (
            task_routes_module.chat_persistence_service._normalize_governance_filter  # type: ignore[attr-defined]
        )
        captured: dict[str, object] = {}
        captured_normalize_inputs: list[object] = []
        try:
            def fake_get_tasks_usage_dashboard(user_id, **kwargs):
                captured["user_id"] = user_id
                captured.update(kwargs)
                return {
                    "window_days": 14,
                    "summary": {
                        "tasks_total": 0,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "trend": [],
                    "by_session": [],
                    "top_tasks": [],
                }

            def fake_normalize_governance_filter(value):
                captured_normalize_inputs.append(value)
                if value == " Planning_Only ":
                    return "profile::normalized"
                if value == " Planning_Suite ":
                    return "source::normalized"
                if not isinstance(value, str):
                    return None
                normalized = value.strip().lower()
                return normalized or None

            task_routes_module.get_tasks_usage_dashboard = fake_get_tasks_usage_dashboard
            task_routes_module.chat_persistence_service._normalize_governance_filter = (  # type: ignore[attr-defined]
                fake_normalize_governance_filter
            )

            task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                tool_registry_profile=" Planning_Only ",
                tool_registry_provider_source=" Planning_Suite ",
                current_user={"id": "user-usage-filtered"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            task_routes_module.chat_persistence_service._normalize_governance_filter = (  # type: ignore[attr-defined]
                original_normalize_governance_filter
            )

        self.assertEqual(captured["user_id"], "user-usage-filtered")
        self.assertEqual(
            captured_normalize_inputs,
            [" Planning_Only ", " Planning_Suite "],
        )
        self.assertEqual(captured["tool_registry_profile_filter"], "profile::normalized")
        self.assertEqual(
            captured["tool_registry_provider_source_filter"],
            "source::normalized",
        )

    def test_build_task_export_markdown_includes_registry_governance_summary(self) -> None:
        task = {
            "id": "task-export-governance-md",
            "session_id": "session-export-governance-md",
            "prompt": "export markdown governance summary",
            "status": "completed",
            "created_at": "2026-06-05T10:00:00",
            "updated_at": "2026-06-05T10:05:00",
            "trace_json": None,
            "usage_json": None,
        }
        original_get_task_trace = task_routes_module.get_task_trace
        original_get_task_messages = task_routes_module.get_task_messages
        try:
            task_routes_module.get_task_trace = lambda *_args, **_kwargs: [
                {
                    "id": "trace-plan-2",
                    "type": "thought",
                    "content": "Planner constrained the tool set.",
                    "seq": 1,
                    "meta": {
                        "tool_registry_profile": "retrieval_only",
                        "tool_registry_provider_source": "default",
                        "allowed_tool_names": ["task_retrieve"],
                        "allowed_tool_labels": ["Knowledge Retrieval"],
                    },
                },
            ]
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []

            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-governance",
            )
            markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
                payload,
            )
        finally:
            task_routes_module.get_task_trace = original_get_task_trace
            task_routes_module.get_task_messages = original_get_task_messages

        self.assertIn("- Tool Registry Profile: retrieval_only", markdown)
        self.assertIn("- Tool Registry Source: default", markdown)
        self.assertIn("- Allowed Tools: Knowledge Retrieval", markdown)

    def test_build_task_export_payload_prefers_persisted_governance_columns(self) -> None:
        task = {
            "id": "task-export-governance-columns",
            "session_id": "session-export-governance-columns",
            "prompt": "export governance summary from persisted columns",
            "status": "completed",
            "created_at": "2026-06-11T10:00:00",
            "updated_at": "2026-06-11T10:05:00",
            "tool_registry_profile": "planning_only",
            "tool_registry_provider_source": "planning_suite",
            "allowed_tool_names_json": json.dumps(["task_plan"]),
            "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
            "trace_json": None,
            "usage_json": None,
        }
        original_get_task_trace = task_routes_module.get_task_trace
        original_get_task_messages = task_routes_module.get_task_messages
        try:
            task_routes_module.get_task_trace = lambda *_args, **_kwargs: []
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []

            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-governance-columns",
            )
        finally:
            task_routes_module.get_task_trace = original_get_task_trace
            task_routes_module.get_task_messages = original_get_task_messages

        self.assertIsNotNone(payload.trace.governance)
        assert payload.trace.governance is not None
        self.assertEqual(payload.trace.governance.profile, "planning_only")
        self.assertEqual(payload.trace.governance.provider_source, "planning_suite")
        self.assertEqual(payload.trace.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(
            payload.trace.governance.allowed_tool_labels,
            ["Task Planner Suite"],
        )

    def test_build_task_export_governance_from_dict_reuses_shared_clone_helper(
        self,
    ) -> None:
        original_cloner = task_routes_module.chat_persistence_service._clone_task_governance_dict  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            task_routes_module.chat_persistence_service._clone_task_governance_dict = (
                lambda governance: captured.append(governance)
                or {
                    "profile": "shared_export_profile",
                    "provider_source": "shared_export_source",
                    "allowed_tool_names": ["shared_export_tool"],
                    "allowed_tool_labels": ["Shared Export Tool"],
                }
            )
            payload = task_routes_module._build_task_export_governance_from_dict(  # type: ignore[attr-defined]
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Planning_Suite ",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner Suite "],
                }
            )
        finally:
            task_routes_module.chat_persistence_service._clone_task_governance_dict = (
                original_cloner
            )

        self.assertEqual(
            captured,
            [
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Planning_Suite ",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner Suite "],
                }
            ],
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profile, "shared_export_profile")
        self.assertEqual(payload.provider_source, "shared_export_source")
        self.assertEqual(payload.allowed_tool_names, ["shared_export_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Shared Export Tool"])

    def test_build_task_export_governance_from_dict_reuses_task_governance_summary_builder(
        self,
    ) -> None:
        original_builder = task_routes_module._build_task_governance_summary_from_dict  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            task_routes_module._build_task_governance_summary_from_dict = lambda governance: captured.append(  # type: ignore[attr-defined]
                governance
            ) or task_routes_module.TaskGovernanceSummary(
                profile="builder_export_profile",
                provider_source="builder_export_source",
                allowed_tool_names=["builder_export_tool"],
                allowed_tool_labels=["Builder Export Tool"],
            )
            payload = task_routes_module._build_task_export_governance_from_dict(  # type: ignore[attr-defined]
                {
                    "profile": " planning_only ",
                    "provider_source": " planning_suite ",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner Suite "],
                }
            )
        finally:
            task_routes_module._build_task_governance_summary_from_dict = original_builder  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": " planning_only ",
                    "provider_source": " planning_suite ",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner Suite "],
                }
            ],
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profile, "builder_export_profile")
        self.assertEqual(payload.provider_source, "builder_export_source")
        self.assertEqual(payload.allowed_tool_names, ["builder_export_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Builder Export Tool"])

    def test_build_task_export_markdown_includes_persisted_governance_summary(self) -> None:
        task = {
            "id": "task-export-governance-columns-md",
            "session_id": "session-export-governance-columns-md",
            "prompt": "export markdown governance summary from persisted columns",
            "status": "completed",
            "created_at": "2026-06-11T10:00:00",
            "updated_at": "2026-06-11T10:05:00",
            "tool_registry_profile": "retrieval_only",
            "tool_registry_provider_source": "default",
            "allowed_tool_names_json": json.dumps(["task_retrieve"]),
            "allowed_tool_labels_json": json.dumps(["Knowledge Retrieval"]),
            "trace_json": None,
            "usage_json": None,
        }
        original_get_task_trace = task_routes_module.get_task_trace
        original_get_task_messages = task_routes_module.get_task_messages
        try:
            task_routes_module.get_task_trace = lambda *_args, **_kwargs: []
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []

            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-governance-columns",
            )
            markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
                payload,
            )
        finally:
            task_routes_module.get_task_trace = original_get_task_trace
            task_routes_module.get_task_messages = original_get_task_messages

        self.assertIn("- Tool Registry Profile: retrieval_only", markdown)
        self.assertIn("- Tool Registry Source: default", markdown)
        self.assertIn("- Allowed Tools: Knowledge Retrieval", markdown)

    def test_build_task_export_payload_reuses_task_export_governance_summary_helper_for_persisted_fallback(
        self,
    ) -> None:
        task = {
            "id": "task-export-governance-fallback-helper",
            "session_id": "session-export-governance-fallback-helper",
            "prompt": "export governance summary helper fallback",
            "status": "completed",
            "created_at": "2026-06-15T10:00:00",
            "updated_at": "2026-06-15T10:05:00",
            "trace_json": None,
            "usage_json": None,
        }
        original_get_task_trace = task_routes_module.get_task_trace
        original_get_task_messages = task_routes_module.get_task_messages
        original_collect_trace_governance_export = task_routes_module._collect_trace_governance_export  # type: ignore[attr-defined]
        original_collect_task_governance_from_task = task_routes_module._collect_task_governance_from_task  # type: ignore[attr-defined]
        original_build_from_summary = task_routes_module._build_task_export_governance_from_summary  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            task_routes_module.get_task_trace = lambda *_args, **_kwargs: []
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []
            task_routes_module._collect_trace_governance_export = lambda _steps: None  # type: ignore[attr-defined]
            task_routes_module._collect_task_governance_from_task = lambda _task: task_routes_module.TaskGovernanceSummary(  # type: ignore[attr-defined]
                profile="summary_profile",
                provider_source="summary_source",
                allowed_tool_names=["summary_tool"],
                allowed_tool_labels=["Summary Tool"],
            )
            task_routes_module._build_task_export_governance_from_summary = lambda summary: captured.append(  # type: ignore[attr-defined]
                summary
            ) or task_routes_module.TaskExportGovernance(
                profile="export_profile",
                provider_source="export_source",
                allowed_tool_names=["export_tool"],
                allowed_tool_labels=["Export Tool"],
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-governance-fallback-helper",
            )
        finally:
            task_routes_module.get_task_trace = original_get_task_trace
            task_routes_module.get_task_messages = original_get_task_messages
            task_routes_module._collect_trace_governance_export = original_collect_trace_governance_export  # type: ignore[attr-defined]
            task_routes_module._collect_task_governance_from_task = original_collect_task_governance_from_task  # type: ignore[attr-defined]
            task_routes_module._build_task_export_governance_from_summary = original_build_from_summary  # type: ignore[attr-defined]

        self.assertEqual(len(captured), 1)
        summary = captured[0]
        self.assertIsInstance(summary, task_routes_module.TaskGovernanceSummary)
        assert isinstance(summary, task_routes_module.TaskGovernanceSummary)
        self.assertEqual(summary.profile, "summary_profile")
        self.assertEqual(summary.provider_source, "summary_source")
        self.assertEqual(summary.allowed_tool_names, ["summary_tool"])
        self.assertEqual(summary.allowed_tool_labels, ["Summary Tool"])
        self.assertIsNotNone(payload.trace.governance)
        assert payload.trace.governance is not None
        self.assertEqual(payload.trace.governance.profile, "export_profile")
        self.assertEqual(payload.trace.governance.provider_source, "export_source")
        self.assertEqual(payload.trace.governance.allowed_tool_names, ["export_tool"])
        self.assertEqual(payload.trace.governance.allowed_tool_labels, ["Export Tool"])

    def test_collect_trace_governance_export_reuses_trace_summary_helper(self) -> None:
        original_collect_summary = task_routes_module._collect_task_governance_summary_from_trace_steps  # type: ignore[attr-defined]
        original_build_from_summary = task_routes_module._build_task_export_governance_from_summary  # type: ignore[attr-defined]
        captured_steps: list[object] = []
        captured_summary: list[object] = []
        fake_step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="trace-export-helper-step",
            type="thought",
            content="trace helper",
            seq=1,
        )
        try:
            task_routes_module._collect_task_governance_summary_from_trace_steps = lambda steps: captured_steps.append(  # type: ignore[attr-defined]
                steps
            ) or task_routes_module.TaskGovernanceSummary(
                profile="trace_summary_profile",
                provider_source="trace_summary_source",
                allowed_tool_names=["trace_summary_tool"],
                allowed_tool_labels=["Trace Summary Tool"],
            )
            task_routes_module._build_task_export_governance_from_summary = lambda summary: captured_summary.append(  # type: ignore[attr-defined]
                summary
            ) or task_routes_module.TaskExportGovernance(
                profile="trace_export_profile",
                provider_source="trace_export_source",
                allowed_tool_names=["trace_export_tool"],
                allowed_tool_labels=["Trace Export Tool"],
            )
            payload = task_routes_module._collect_trace_governance_export(  # type: ignore[attr-defined]
                [fake_step]
            )
        finally:
            task_routes_module._collect_task_governance_summary_from_trace_steps = original_collect_summary  # type: ignore[attr-defined]
            task_routes_module._build_task_export_governance_from_summary = original_build_from_summary  # type: ignore[attr-defined]

        self.assertEqual(captured_steps, [[fake_step]])
        self.assertEqual(len(captured_summary), 1)
        summary = captured_summary[0]
        self.assertIsInstance(summary, task_routes_module.TaskGovernanceSummary)
        assert isinstance(summary, task_routes_module.TaskGovernanceSummary)
        self.assertEqual(summary.profile, "trace_summary_profile")
        self.assertEqual(summary.provider_source, "trace_summary_source")
        self.assertEqual(summary.allowed_tool_names, ["trace_summary_tool"])
        self.assertEqual(summary.allowed_tool_labels, ["Trace Summary Tool"])
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profile, "trace_export_profile")
        self.assertEqual(payload.provider_source, "trace_export_source")
        self.assertEqual(payload.allowed_tool_names, ["trace_export_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Trace Export Tool"])

    def test_collect_task_governance_summary_from_trace_steps_reuses_clone_builder(
        self,
    ) -> None:
        original_extractor = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_trace_steps
        )
        original_dict_builder = task_routes_module._build_task_governance_summary_from_dict  # type: ignore[attr-defined]
        original_clone_builder = task_routes_module._build_task_governance_summary_from_clone  # type: ignore[attr-defined]
        captured_steps: list[object] = []
        captured_governance: list[object] = []
        fake_step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="trace-governance-clone-step",
            type="thought",
            content="trace helper",
            seq=1,
        )
        try:
            task_routes_module.chat_persistence_service._extract_task_governance_from_trace_steps = (
                lambda steps: captured_steps.append(steps)
                or {
                    "profile": "shared_trace_profile",
                    "provider_source": "shared_trace_source",
                    "allowed_tool_names": ["shared_trace_tool"],
                    "allowed_tool_labels": ["Shared Trace Tool"],
                }
            )
            task_routes_module._build_task_governance_summary_from_dict = lambda _governance: task_routes_module.TaskGovernanceSummary(  # type: ignore[attr-defined]
                profile="dict_profile",
                provider_source="dict_source",
                allowed_tool_names=["dict_tool"],
                allowed_tool_labels=["Dict Tool"],
            )
            task_routes_module._build_task_governance_summary_from_clone = lambda governance: captured_governance.append(  # type: ignore[attr-defined]
                governance
            ) or task_routes_module.TaskGovernanceSummary(
                profile="clone_profile",
                provider_source="clone_source",
                allowed_tool_names=["clone_tool"],
                allowed_tool_labels=["Clone Tool"],
            )
            payload = task_routes_module._collect_task_governance_summary_from_trace_steps(  # type: ignore[attr-defined]
                [fake_step]
            )
        finally:
            task_routes_module.chat_persistence_service._extract_task_governance_from_trace_steps = (  # type: ignore[attr-defined]
                original_extractor
            )
            task_routes_module._build_task_governance_summary_from_dict = original_dict_builder  # type: ignore[attr-defined]
            task_routes_module._build_task_governance_summary_from_clone = original_clone_builder  # type: ignore[attr-defined]

        self.assertEqual(
            captured_steps,
            [[fake_step.model_dump(exclude_none=True)]],
        )
        self.assertEqual(
            captured_governance,
            [
                {
                    "profile": "shared_trace_profile",
                    "provider_source": "shared_trace_source",
                    "allowed_tool_names": ["shared_trace_tool"],
                    "allowed_tool_labels": ["Shared Trace Tool"],
                }
            ],
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profile, "clone_profile")
        self.assertEqual(payload.provider_source, "clone_source")
        self.assertEqual(payload.allowed_tool_names, ["clone_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Clone Tool"])

    def test_build_task_response_reuses_shared_task_governance_row_parser(self) -> None:
        self.assertTrue(hasattr(task_routes_module, "chat_persistence_service"))
        original_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: {
                    "profile": "shared_profile",
                    "provider_source": "shared_source",
                    "allowed_tool_names": ["shared_tool"],
                    "allowed_tool_labels": ["Shared Tool"],
                }
            )
            response = task_routes_module._build_task_response(  # type: ignore[attr-defined]
                {
                    "id": "task-shared-governance-route",
                    "session_id": "session-shared-governance-route",
                    "prompt": "shared governance route task",
                    "status": "completed",
                    "trace_json": None,
                    "usage_json": None,
                    "created_at": "2026-06-11T12:00:00",
                    "updated_at": "2026-06-11T12:01:00",
                }
            )
        finally:
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_parser
            )

        self.assertIsNotNone(response.governance)
        assert response.governance is not None
        self.assertEqual(response.governance.profile, "shared_profile")
        self.assertEqual(response.governance.provider_source, "shared_source")
        self.assertEqual(response.governance.allowed_tool_names, ["shared_tool"])
        self.assertEqual(response.governance.allowed_tool_labels, ["Shared Tool"])

    def test_build_session_export_governance_summary_from_dict_reuses_shared_clone_helper(
        self,
    ) -> None:
        original_clone_helper = getattr(
            session_routes_module.chat_persistence_service,
            "_clone_session_governance_summary_dict",
            None,
        )
        captured: list[object] = []
        try:
            session_routes_module.chat_persistence_service._clone_session_governance_summary_dict = (  # type: ignore[attr-defined]
                lambda governance: captured.append(governance) or {
                    "profiles": ["clone_profile"],
                    "provider_sources": ["clone_source"],
                    "allowed_tool_names": ["clone_tool"],
                    "allowed_tool_labels": ["Clone Tool"],
                }
            )
            payload = session_routes_module._build_session_export_governance_summary_from_dict(  # type: ignore[attr-defined]
                {
                    "profiles": ["planning_only"],
                    "provider_sources": ["planning_suite"],
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            )
        finally:
            if original_clone_helper is None:
                delattr(
                    session_routes_module.chat_persistence_service,
                    "_clone_session_governance_summary_dict",
                )
            else:
                session_routes_module.chat_persistence_service._clone_session_governance_summary_dict = original_clone_helper  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profiles": ["planning_only"],
                    "provider_sources": ["planning_suite"],
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            ],
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profiles, ["clone_profile"])
        self.assertEqual(payload.provider_sources, ["clone_source"])
        self.assertEqual(payload.allowed_tool_names, ["clone_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Clone Tool"])

    def test_build_session_export_payload_surfaces_governance_summary(self) -> None:
        session = {
            "id": "session-export-governance",
            "title": "Governance Session",
            "created_at": "2026-06-05T10:00:00",
            "updated_at": "2026-06-05T10:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-1",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-05T10:00:00",
                    "updated_at": "2026-06-05T10:01:00",
                    "usage_json": None,
                    "trace_json": json.dumps(
                        [
                            {
                                "id": "trace-1",
                                "type": "thought",
                                "content": "planning only",
                                "seq": 1,
                                "meta": {
                                    "tool_registry_profile": "planning_only",
                                    "tool_registry_provider_source": "default",
                                    "allowed_tool_names": ["task_plan"],
                                    "allowed_tool_labels": ["Task Planner"],
                                },
                            }
                        ]
                    ),
                },
                {
                    "id": "task-2",
                    "prompt": "task two",
                    "status": "completed",
                    "created_at": "2026-06-05T10:02:00",
                    "updated_at": "2026-06-05T10:03:00",
                    "usage_json": None,
                    "trace_json": json.dumps(
                        [
                            {
                                "id": "trace-2",
                                "type": "thought",
                                "content": "retrieval only",
                                "seq": 1,
                                "meta": {
                                    "tool_registry_profile": "retrieval_only",
                                    "tool_registry_provider_source": "suite_a",
                                    "allowed_tool_names": ["task_retrieve"],
                                    "allowed_tool_labels": ["Knowledge Retrieval"],
                                },
                            }
                        ]
                    ),
                },
            ]
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-governance",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(
            payload.governance.profiles,
            ["planning_only", "retrieval_only"],
        )
        self.assertEqual(payload.governance.provider_sources, ["default", "suite_a"])
        self.assertEqual(
            payload.governance.allowed_tool_labels,
            ["Knowledge Retrieval", "Task Planner"],
        )

    def test_build_session_export_payload_reuses_shared_trace_governance_parser(self) -> None:
        session = {
            "id": "session-shared-trace-governance",
            "title": "Shared Trace Governance Session",
            "created_at": "2026-06-11T13:00:00",
            "updated_at": "2026-06-11T13:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_parser = (
            session_routes_module.chat_persistence_service._extract_task_governance_from_trace_steps
        )
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-shared-trace-governance",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-11T13:00:00",
                    "updated_at": "2026-06-11T13:01:00",
                    "usage_json": None,
                    "trace_json": json.dumps(
                        [
                            {
                                "id": "trace-shared-governance-1",
                                "type": "thought",
                                "content": "trace governance",
                                "seq": 1,
                                "meta": {},
                            }
                        ]
                    ),
                },
            ]
            session_routes_module.chat_persistence_service._extract_task_governance_from_trace_steps = (
                lambda _trace_steps: {
                    "profile": "shared_trace_profile",
                    "provider_source": "shared_trace_source",
                    "allowed_tool_names": ["shared_trace_tool"],
                    "allowed_tool_labels": ["Shared Trace Tool"],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-shared-trace-governance",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.chat_persistence_service._extract_task_governance_from_trace_steps = (
                original_parser
            )

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(payload.governance.profiles, ["shared_trace_profile"])
        self.assertEqual(payload.governance.provider_sources, ["shared_trace_source"])
        self.assertEqual(payload.governance.allowed_tool_names, ["shared_trace_tool"])
        self.assertEqual(payload.governance.allowed_tool_labels, ["Shared Trace Tool"])
        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(payload.tasks[0].governance.profile, "shared_trace_profile")
        self.assertEqual(payload.tasks[0].governance.provider_source, "shared_trace_source")
        self.assertEqual(payload.tasks[0].governance.allowed_tool_names, ["shared_trace_tool"])
        self.assertEqual(payload.tasks[0].governance.allowed_tool_labels, ["Shared Trace Tool"])

    def test_build_session_export_payload_reuses_shared_governance_summary_merger(self) -> None:
        session = {
            "id": "session-shared-governance-summary",
            "title": "Shared Governance Summary Session",
            "created_at": "2026-06-11T14:00:00",
            "updated_at": "2026-06-11T14:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_merge = session_routes_module.chat_persistence_service._merge_session_governance_summary
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-shared-governance-summary",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-11T14:00:00",
                    "updated_at": "2026-06-11T14:01:00",
                    "usage_json": None,
                    "trace_json": None,
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "default",
                    "allowed_tool_names_json": json.dumps(["task_plan"]),
                    "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                },
            ]
            session_routes_module.chat_persistence_service._merge_session_governance_summary = (
                lambda _current, _task_governance: {
                    "profiles": ["shared_summary_profile"],
                    "provider_sources": ["shared_summary_source"],
                    "allowed_tool_names": ["shared_summary_tool"],
                    "allowed_tool_labels": ["Shared Summary Tool"],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-shared-governance-summary",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.chat_persistence_service._merge_session_governance_summary = (
                original_merge
            )

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(payload.governance.profiles, ["shared_summary_profile"])
        self.assertEqual(payload.governance.provider_sources, ["shared_summary_source"])
        self.assertEqual(payload.governance.allowed_tool_names, ["shared_summary_tool"])
        self.assertEqual(payload.governance.allowed_tool_labels, ["Shared Summary Tool"])

    def test_collect_session_governance_summary_reuses_clone_builder(self) -> None:
        original_collect = session_routes_module._collect_task_governance_from_task  # type: ignore[attr-defined]
        original_merge = session_routes_module.chat_persistence_service._merge_session_governance_summary
        original_builder = session_routes_module._build_session_export_governance_summary_from_clone  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            session_routes_module._collect_task_governance_from_task = lambda _task, _parsed_steps=None: {  # type: ignore[attr-defined]
                "profile": "task_profile",
                "provider_source": "task_source",
                "allowed_tool_names": ["task_tool"],
                "allowed_tool_labels": ["Task Tool"],
            }
            session_routes_module.chat_persistence_service._merge_session_governance_summary = (
                lambda _current, _task_governance: {
                    "profiles": ["merged_profile"],
                    "provider_sources": ["merged_source"],
                    "allowed_tool_names": ["merged_tool"],
                    "allowed_tool_labels": ["Merged Tool"],
                }
            )
            session_routes_module._build_session_export_governance_summary_from_clone = lambda governance: captured.append(  # type: ignore[attr-defined]
                governance
            ) or session_routes_module.SessionExportGovernanceSummary(
                profiles=["builder_profile"],
                provider_sources=["builder_source"],
                allowed_tool_names=["builder_tool"],
                allowed_tool_labels=["Builder Tool"],
            )
            payload = session_routes_module._collect_session_governance_summary(  # type: ignore[attr-defined]
                [{"id": "task-1"}]
            )
        finally:
            session_routes_module._collect_task_governance_from_task = original_collect  # type: ignore[attr-defined]
            session_routes_module.chat_persistence_service._merge_session_governance_summary = original_merge
            session_routes_module._build_session_export_governance_summary_from_clone = original_builder  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profiles": ["merged_profile"],
                    "provider_sources": ["merged_source"],
                    "allowed_tool_names": ["merged_tool"],
                    "allowed_tool_labels": ["Merged Tool"],
                }
            ],
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profiles, ["builder_profile"])
        self.assertEqual(payload.provider_sources, ["builder_source"])
        self.assertEqual(payload.allowed_tool_names, ["builder_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Builder Tool"])

    def test_build_session_export_payload_reuses_task_governance_summary_builder(self) -> None:
        session = {
            "id": "session-builder-governance-summary",
            "title": "Builder Governance Summary Session",
            "created_at": "2026-06-11T15:00:00",
            "updated_at": "2026-06-11T15:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_builder = session_routes_module._build_session_export_task_governance_summary_from_clone  # type: ignore[attr-defined]
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-builder-governance-session",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-11T15:00:00",
                    "updated_at": "2026-06-11T15:01:00",
                    "usage_json": None,
                    "trace_json": None,
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "default",
                    "allowed_tool_names_json": json.dumps(["task_plan"]),
                    "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                },
            ]
            session_routes_module._build_session_export_task_governance_summary_from_clone = lambda _governance: session_routes_module.SessionExportTaskGovernanceSummary(  # type: ignore[attr-defined]
                profile="builder_profile",
                provider_source="builder_source",
                allowed_tool_names=["builder_tool"],
                allowed_tool_labels=["Builder Tool"],
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-builder-governance-session",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module._build_session_export_task_governance_summary_from_clone = original_builder  # type: ignore[attr-defined]

        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(payload.tasks[0].governance.profile, "builder_profile")
        self.assertEqual(payload.tasks[0].governance.provider_source, "builder_source")
        self.assertEqual(payload.tasks[0].governance.allowed_tool_names, ["builder_tool"])
        self.assertEqual(payload.tasks[0].governance.allowed_tool_labels, ["Builder Tool"])

    def test_build_session_export_task_governance_summary_from_dict_reuses_shared_clone_helper(
        self,
    ) -> None:
        original_cloner = session_routes_module.chat_persistence_service._clone_task_governance_dict  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            session_routes_module.chat_persistence_service._clone_task_governance_dict = (
                lambda governance: captured.append(governance)
                or {
                    "profile": "shared_session_profile",
                    "provider_source": "shared_session_source",
                    "allowed_tool_names": ["shared_session_tool"],
                    "allowed_tool_labels": ["Shared Session Tool"],
                }
            )
            payload = session_routes_module._build_session_export_task_governance_summary_from_dict(  # type: ignore[attr-defined]
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Default ",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner "],
                }
            )
        finally:
            session_routes_module.chat_persistence_service._clone_task_governance_dict = (
                original_cloner
            )

        self.assertEqual(
            captured,
            [
                {
                    "profile": " Planning_Only ",
                    "provider_source": " Default ",
                    "allowed_tool_names": [" task_plan "],
                    "allowed_tool_labels": [" Task Planner "],
                }
            ],
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.profile, "shared_session_profile")
        self.assertEqual(payload.provider_source, "shared_session_source")
        self.assertEqual(payload.allowed_tool_names, ["shared_session_tool"])
        self.assertEqual(payload.allowed_tool_labels, ["Shared Session Tool"])

    def test_build_session_task_summary_reuses_task_governance_clone_builder(
        self,
    ) -> None:
        original_collect = session_routes_module._collect_task_governance_from_task  # type: ignore[attr-defined]
        original_builder = session_routes_module._build_session_export_task_governance_summary_from_clone  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            session_routes_module._collect_task_governance_from_task = lambda _task, _parsed_steps=None: {  # type: ignore[attr-defined]
                "profile": "clone_profile",
                "provider_source": "clone_source",
                "allowed_tool_names": ["clone_tool"],
                "allowed_tool_labels": ["Clone Tool"],
            }
            session_routes_module._build_session_export_task_governance_summary_from_clone = lambda governance: captured.append(  # type: ignore[attr-defined]
                governance
            ) or session_routes_module.SessionExportTaskGovernanceSummary(
                profile="builder_profile",
                provider_source="builder_source",
                allowed_tool_names=["builder_tool"],
                allowed_tool_labels=["Builder Tool"],
            )
            summary, trace_step_count, rag_hit_count = session_routes_module._build_session_task_summary(  # type: ignore[attr-defined]
                {
                    "id": "task-session-clone-builder",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-15T11:00:00",
                    "updated_at": "2026-06-15T11:01:00",
                    "usage_json": None,
                    "trace_json": None,
                }
            )
        finally:
            session_routes_module._collect_task_governance_from_task = original_collect  # type: ignore[attr-defined]
            session_routes_module._build_session_export_task_governance_summary_from_clone = original_builder  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                {
                    "profile": "clone_profile",
                    "provider_source": "clone_source",
                    "allowed_tool_names": ["clone_tool"],
                    "allowed_tool_labels": ["Clone Tool"],
                }
            ],
        )
        self.assertEqual(trace_step_count, 0)
        self.assertEqual(rag_hit_count, 0)
        self.assertIsNotNone(summary.governance)
        assert summary.governance is not None
        self.assertEqual(summary.governance.profile, "builder_profile")
        self.assertEqual(summary.governance.provider_source, "builder_source")
        self.assertEqual(summary.governance.allowed_tool_names, ["builder_tool"])
        self.assertEqual(summary.governance.allowed_tool_labels, ["Builder Tool"])

    def test_build_session_export_payload_prefers_persisted_governance_columns(self) -> None:
        session = {
            "id": "session-export-governance-columns",
            "title": "Governance Columns Session",
            "created_at": "2026-06-10T10:00:00",
            "updated_at": "2026-06-10T10:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 2,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-columns-1",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-10T10:00:00",
                    "updated_at": "2026-06-10T10:01:00",
                    "usage_json": None,
                    "trace_json": None,
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "default",
                    "allowed_tool_names_json": json.dumps(["task_plan"]),
                    "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                },
                {
                    "id": "task-columns-2",
                    "prompt": "task two",
                    "status": "completed",
                    "created_at": "2026-06-10T10:02:00",
                    "updated_at": "2026-06-10T10:03:00",
                    "usage_json": None,
                    "trace_json": None,
                    "tool_registry_profile": "retrieval_only",
                    "tool_registry_provider_source": "suite_a",
                    "allowed_tool_names_json": json.dumps(["task_retrieve"]),
                    "allowed_tool_labels_json": json.dumps(["Knowledge Retrieval"]),
                },
            ]
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-governance-columns",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(
            payload.governance.profiles,
            ["planning_only", "retrieval_only"],
        )
        self.assertEqual(payload.governance.provider_sources, ["default", "suite_a"])
        self.assertEqual(
            payload.governance.allowed_tool_labels,
            ["Knowledge Retrieval", "Task Planner"],
        )
        self.assertEqual(len(payload.tasks), 2)
        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(payload.tasks[0].governance.profile, "planning_only")
        self.assertEqual(payload.tasks[0].governance.provider_source, "default")
        self.assertEqual(payload.tasks[0].governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(payload.tasks[0].governance.allowed_tool_labels, ["Task Planner"])
        self.assertIsNotNone(payload.tasks[1].governance)
        assert payload.tasks[1].governance is not None
        self.assertEqual(payload.tasks[1].governance.profile, "retrieval_only")
        self.assertEqual(payload.tasks[1].governance.provider_source, "suite_a")
        self.assertEqual(payload.tasks[1].governance.allowed_tool_names, ["task_retrieve"])
        self.assertEqual(
            payload.tasks[1].governance.allowed_tool_labels,
            ["Knowledge Retrieval"],
        )

    def test_build_session_export_markdown_includes_governance_summary(self) -> None:
        session = {
            "id": "session-export-governance-md",
            "title": "Governance Session",
            "created_at": "2026-06-05T10:00:00",
            "updated_at": "2026-06-05T10:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-md-1",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-05T10:00:00",
                    "updated_at": "2026-06-05T10:01:00",
                    "usage_json": None,
                    "trace_json": json.dumps(
                        [
                            {
                                "id": "trace-md-1",
                                "type": "thought",
                                "content": "calc only",
                                "seq": 1,
                                "meta": {
                                    "tool_registry_profile": "calculator_only",
                                    "tool_registry_provider_source": "default",
                                    "allowed_tool_names": ["calc_eval"],
                                    "allowed_tool_labels": ["calc_eval"],
                                },
                            }
                        ]
                    ),
                },
            ]
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-governance",
            )
            markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
                payload,
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks

        self.assertIn("## Tool Registry Governance", markdown)
        self.assertIn("- Profiles: calculator_only", markdown)
        self.assertIn("- Provider Sources: default", markdown)
        self.assertIn("- Allowed Tools: calc_eval", markdown)

    def test_build_session_export_markdown_includes_persisted_governance_summary(self) -> None:
        session = {
            "id": "session-export-governance-columns-md",
            "title": "Governance Columns Session",
            "created_at": "2026-06-10T10:00:00",
            "updated_at": "2026-06-10T10:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-columns-md-1",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-10T10:00:00",
                    "updated_at": "2026-06-10T10:01:00",
                    "usage_json": None,
                    "trace_json": None,
                    "tool_registry_profile": "calculator_only",
                    "tool_registry_provider_source": "default",
                    "allowed_tool_names_json": json.dumps(["calc_eval"]),
                    "allowed_tool_labels_json": json.dumps(["calc_eval"]),
                },
            ]
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-governance-columns",
            )
            markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
                payload,
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks

        self.assertIn("## Tool Registry Governance", markdown)
        self.assertIn("- Profiles: calculator_only", markdown)
        self.assertIn("- Provider Sources: default", markdown)
        self.assertIn("- Allowed Tools: calc_eval", markdown)
        self.assertIn("- Tool Registry Profile: calculator_only", markdown)
        self.assertIn("- Tool Registry Source: default", markdown)

    def test_build_session_export_payload_reuses_shared_task_governance_row_parser(self) -> None:
        self.assertTrue(hasattr(session_routes_module, "chat_persistence_service"))
        session = {
            "id": "session-shared-governance-columns",
            "title": "Shared Governance Session",
            "created_at": "2026-06-11T12:00:00",
            "updated_at": "2026-06-11T12:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_parser = (
            session_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-shared-governance-session",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-11T12:00:00",
                    "updated_at": "2026-06-11T12:01:00",
                    "usage_json": None,
                    "trace_json": None,
                },
            ]
            session_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: {
                    "profile": "shared_profile",
                    "provider_source": "shared_source",
                    "allowed_tool_names": ["shared_tool"],
                    "allowed_tool_labels": ["Shared Tool"],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-shared-governance-session",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_parser
            )

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(payload.governance.profiles, ["shared_profile"])
        self.assertEqual(payload.governance.provider_sources, ["shared_source"])
        self.assertEqual(payload.governance.allowed_tool_names, ["shared_tool"])
        self.assertEqual(payload.governance.allowed_tool_labels, ["Shared Tool"])
        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(payload.tasks[0].governance.profile, "shared_profile")
        self.assertEqual(payload.tasks[0].governance.provider_source, "shared_source")
        self.assertEqual(payload.tasks[0].governance.allowed_tool_names, ["shared_tool"])
        self.assertEqual(payload.tasks[0].governance.allowed_tool_labels, ["Shared Tool"])

    def test_build_session_export_payload_reuses_shared_task_governance_trace_json_parser(
        self,
    ) -> None:
        self.assertTrue(hasattr(session_routes_module, "chat_persistence_service"))
        session = {
            "id": "session-shared-governance-trace",
            "title": "Shared Trace Governance Session",
            "created_at": "2026-06-12T12:00:00",
            "updated_at": "2026-06-12T12:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_row_parser = (
            session_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        original_trace_json_parser = (
            session_routes_module.chat_persistence_service._extract_task_governance_from_trace_json
        )
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-shared-governance-trace",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-12T12:00:00",
                    "updated_at": "2026-06-12T12:01:00",
                    "usage_json": None,
                    "trace_json": "[]",
                },
            ]
            session_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: None
            )
            session_routes_module.chat_persistence_service._extract_task_governance_from_trace_json = (
                lambda _trace_json: {
                    "profile": "shared_trace_profile",
                    "provider_source": "shared_trace_source",
                    "allowed_tool_names": ["shared_trace_tool"],
                    "allowed_tool_labels": ["Shared Trace Tool"],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-shared-governance-trace",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )
            session_routes_module.chat_persistence_service._extract_task_governance_from_trace_json = (
                original_trace_json_parser
            )

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(payload.governance.profiles, ["shared_trace_profile"])
        self.assertEqual(payload.governance.provider_sources, ["shared_trace_source"])
        self.assertEqual(payload.governance.allowed_tool_names, ["shared_trace_tool"])
        self.assertEqual(payload.governance.allowed_tool_labels, ["Shared Trace Tool"])
        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(payload.tasks[0].governance.profile, "shared_trace_profile")
        self.assertEqual(payload.tasks[0].governance.provider_source, "shared_trace_source")
        self.assertEqual(payload.tasks[0].governance.allowed_tool_names, ["shared_trace_tool"])
        self.assertEqual(payload.tasks[0].governance.allowed_tool_labels, ["Shared Trace Tool"])

    def test_collect_session_task_governance_reuses_trace_json_helper(self) -> None:
        original_row_helper = session_routes_module._collect_task_governance_from_task_row  # type: ignore[attr-defined]
        original_trace_json_helper = session_routes_module._collect_task_governance_from_trace_json  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            session_routes_module._collect_task_governance_from_task_row = lambda _task: None  # type: ignore[attr-defined]
            session_routes_module._collect_task_governance_from_trace_json = lambda trace_json: captured.append(  # type: ignore[attr-defined]
                trace_json
            ) or {
                "profile": "trace_clone_profile",
                "provider_source": "trace_clone_source",
                "allowed_tool_names": ["trace_clone_tool"],
                "allowed_tool_labels": ["Trace Clone Tool"],
            }
            payload = session_routes_module._collect_task_governance_from_task(  # type: ignore[attr-defined]
                {
                    "id": "task-session-trace-helper",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-15T12:00:00",
                    "updated_at": "2026-06-15T12:01:00",
                    "usage_json": None,
                    "trace_json": "[]",
                }
            )
        finally:
            session_routes_module._collect_task_governance_from_task_row = original_row_helper  # type: ignore[attr-defined]
            session_routes_module._collect_task_governance_from_trace_json = original_trace_json_helper  # type: ignore[attr-defined]

        self.assertEqual(captured, ["[]"])
        self.assertEqual(
            payload,
            {
                "profile": "trace_clone_profile",
                "provider_source": "trace_clone_source",
                "allowed_tool_names": ["trace_clone_tool"],
                "allowed_tool_labels": ["Trace Clone Tool"],
            },
        )

    def test_collect_session_task_governance_from_trace_steps_reuses_clone_helper(
        self,
    ) -> None:
        original_extractor = (
            session_routes_module.chat_persistence_service._extract_task_governance_from_trace_steps
        )
        original_clone_helper = session_routes_module._clone_task_governance  # type: ignore[attr-defined]
        captured_steps: list[object] = []
        captured_governance: list[object] = []

        class FakeStep:
            def model_dump(self, *, exclude_none: bool = False) -> dict[str, object]:
                self_exclude_none = exclude_none
                return {
                    "id": "session-trace-step-clone",
                    "type": "thought",
                    "content": "trace helper",
                    "seq": 1,
                    "exclude_none": self_exclude_none,
                }

        fake_step = FakeStep()
        try:
            session_routes_module.chat_persistence_service._extract_task_governance_from_trace_steps = (
                lambda steps: captured_steps.append(steps)
                or {
                    "profile": "shared_trace_profile",
                    "provider_source": "shared_trace_source",
                    "allowed_tool_names": ["shared_trace_tool"],
                    "allowed_tool_labels": ["Shared Trace Tool"],
                }
            )
            session_routes_module._clone_task_governance = lambda governance: captured_governance.append(  # type: ignore[attr-defined]
                governance
            ) or {
                "profile": "clone_profile",
                "provider_source": "clone_source",
                "allowed_tool_names": ["clone_tool"],
                "allowed_tool_labels": ["Clone Tool"],
            }
            payload = session_routes_module._collect_task_governance_from_trace_steps(  # type: ignore[attr-defined]
                [fake_step]
            )
        finally:
            session_routes_module.chat_persistence_service._extract_task_governance_from_trace_steps = (  # type: ignore[attr-defined]
                original_extractor
            )
            session_routes_module._clone_task_governance = original_clone_helper  # type: ignore[attr-defined]

        self.assertEqual(
            captured_steps,
            [[fake_step.model_dump(exclude_none=True)]],
        )
        self.assertEqual(
            captured_governance,
            [
                {
                    "profile": "shared_trace_profile",
                    "provider_source": "shared_trace_source",
                    "allowed_tool_names": ["shared_trace_tool"],
                    "allowed_tool_labels": ["Shared Trace Tool"],
                }
            ],
        )
        self.assertEqual(
            payload,
            {
                "profile": "clone_profile",
                "provider_source": "clone_source",
                "allowed_tool_names": ["clone_tool"],
                "allowed_tool_labels": ["Clone Tool"],
            },
        )

    def test_export_assertions_require_session_task_level_governance_json(self) -> None:
        import importlib

        export_assertions_module = importlib.import_module("scripts.e2e_export_assertions")
        payload = {
            "session": {"id": "session-e2e-governance"},
            "tasks": [
                {
                    "id": "task-e2e-governance",
                    "governance": {
                        "profile": "planning_only",
                        "provider_source": "suite_a",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                },
            ],
        }

        task_id, governance = (
            export_assertions_module.assert_session_export_task_level_governance_json(payload)
        )

        self.assertEqual(task_id, "task-e2e-governance")
        self.assertEqual(governance["profile"], "planning_only")
        self.assertEqual(governance["provider_source"], "suite_a")
        self.assertEqual(governance["allowed_tool_names"], ["task_plan"])
        self.assertEqual(governance["allowed_tool_labels"], ["Task Planner"])

    def test_export_assertions_require_session_task_level_governance_markdown(self) -> None:
        import importlib

        export_assertions_module = importlib.import_module("scripts.e2e_export_assertions")
        governance = {
            "profile": "planning_only",
            "provider_source": "suite_a",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner"],
        }
        markdown = "\n".join(
            [
                "# InsightAgent Session Export",
                "## Tasks",
                "### Task 1: task-e2e-governance",
                "- Tool Registry Profile: planning_only",
                "- Tool Registry Source: suite_a",
                "- Allowed Tools: Task Planner",
            ]
        )

        export_assertions_module.assert_session_export_task_level_governance_markdown(
            markdown,
            governance,
        )

    def test_export_assertions_require_task_export_governance_json(self) -> None:
        import importlib

        export_assertions_module = importlib.import_module("scripts.e2e_export_assertions")
        payload = {
            "trace": {
                "governance": {
                    "profile": "calculator_only",
                    "provider_source": "default",
                    "allowed_tool_names": ["calc_eval"],
                    "allowed_tool_labels": ["Calculator"],
                }
            }
        }

        governance = export_assertions_module.assert_task_export_governance_json(payload)

        self.assertEqual(governance["profile"], "calculator_only")
        self.assertEqual(governance["provider_source"], "default")
        self.assertEqual(governance["allowed_tool_names"], ["calc_eval"])
        self.assertEqual(governance["allowed_tool_labels"], ["Calculator"])

    def test_export_assertions_require_task_export_governance_markdown(self) -> None:
        import importlib

        export_assertions_module = importlib.import_module("scripts.e2e_export_assertions")
        governance = {
            "profile": "calculator_only",
            "provider_source": "default",
            "allowed_tool_names": ["calc_eval"],
            "allowed_tool_labels": ["Calculator"],
        }
        markdown = "\n".join(
            [
                "# InsightAgent Task Export",
                "## Trace Summary",
                "- Tool Registry Profile: calculator_only",
                "- Tool Registry Source: default",
                "- Allowed Tools: Calculator",
            ]
        )

        export_assertions_module.assert_task_export_governance_markdown(
            markdown,
            governance,
        )

    def test_stream_task_execution_uses_stored_registry_settings_for_planning_and_preflight(
        self,
    ) -> None:
        runtime_settings = StoredSettings(
            mode="mock",
            provider="mock",
            model="mock-gpt",
            tool_registry_profile="planning_only",
            tool_registry_provider_source="suite_a",
        )
        planning_settings_seen: list[object | None] = []
        preflight_settings_seen: list[object | None] = []

        class FakeProvider:
            provider = "mock"
            model = "mock-gpt"

            def stream_generate(self, prompt: str):
                del prompt
                yield "This is a mock response from InsightAgent"

        original_get_stored_settings = getattr(
            chat_execution_module,
            "get_stored_settings",
            None,
        )
        original_get_llm_provider = chat_execution_module.get_llm_provider
        original_get_configured_tool_registry_provider = (
            chat_execution_module.get_configured_tool_registry_provider
        )
        original_build_tool_plan_artifacts = chat_execution_module.build_tool_plan_artifacts
        original_execute_preflight = (
            chat_execution_module.execute_configured_tool_registry_provider_preflight
        )
        original_update_task_status = chat_execution_module.update_task_status
        original_get_task = chat_execution_module.get_task
        original_update_task_trace_steps = chat_execution_module.update_task_trace_steps
        original_complete_task = chat_execution_module.complete_task
        original_create_message = chat_execution_module.create_message
        original_try_append_task_memory = chat_execution_module.try_append_task_memory
        original_safe_record_audit_event = chat_execution_module.safe_record_audit_event

        def fake_get_stored_settings(user_id: str) -> StoredSettings:
            self.assertEqual(user_id, "user-1")
            return runtime_settings

        def fake_get_llm_provider(user_id: str) -> FakeProvider:
            self.assertEqual(user_id, "user-1")
            return FakeProvider()

        def fake_get_configured_tool_registry_provider(*, settings=None):
            planning_settings_seen.append(settings)
            return StaticToolRegistryProvider(
                {"task_plan": get_default_tool_registry()["task_plan"]}
            )

        def fake_build_tool_plan_artifacts(
            prompt: str,
            *,
            provider: object | None = None,
            registry_provider: object | None = None,
        ) -> SimpleNamespace:
            del prompt, provider, registry_provider
            return SimpleNamespace(
                tool_plan=[],
                planning_prompt=None,
                provider_usage=None,
                planning_provider_attempted=False,
                planning_provider_used=False,
                allowed_tool_names=("task_plan",),
                allowed_tool_labels=("Task Planner",),
            )

        def fake_execute_preflight(
            *,
            task_id: str,
            step_id: str,
            seq: int,
            model: str,
            trace_steps: list[dict[str, object]],
            persist_trace_fn,
            record_audit_event_fn,
            settings=None,
        ) -> dict[str, object]:
            del task_id, step_id, seq, model, trace_steps, persist_trace_fn, record_audit_event_fn
            preflight_settings_seen.append(settings)
            return {
                "provider": StaticToolRegistryProvider({}),
                "provider_source_name": "suite_a",
            }

        try:
            chat_execution_module.get_stored_settings = fake_get_stored_settings
            chat_execution_module.get_llm_provider = fake_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                fake_get_configured_tool_registry_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                fake_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                fake_execute_preflight
            )
            chat_execution_module.update_task_status = lambda *args, **kwargs: None
            chat_execution_module.get_task = lambda *args, **kwargs: {"status": "running"}
            chat_execution_module.update_task_trace_steps = lambda *args, **kwargs: None
            chat_execution_module.complete_task = lambda *args, **kwargs: None
            chat_execution_module.create_message = lambda *args, **kwargs: None
            chat_execution_module.try_append_task_memory = lambda *args, **kwargs: None
            chat_execution_module.safe_record_audit_event = lambda *args, **kwargs: None

            events = list(
                chat_execution_module.stream_task_execution(
                    task_id="task-1",
                    session_id="session-1",
                    user_id="user-1",
                    prompt="please plan with user-scoped registry settings",
                )
            )
        finally:
            if original_get_stored_settings is not None:
                chat_execution_module.get_stored_settings = original_get_stored_settings
            chat_execution_module.get_llm_provider = original_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                original_get_configured_tool_registry_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                original_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                original_execute_preflight
            )
            chat_execution_module.update_task_status = original_update_task_status
            chat_execution_module.get_task = original_get_task
            chat_execution_module.update_task_trace_steps = original_update_task_trace_steps
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.create_message = original_create_message
            chat_execution_module.try_append_task_memory = original_try_append_task_memory
            chat_execution_module.safe_record_audit_event = original_safe_record_audit_event

        self.assertEqual(planning_settings_seen, [runtime_settings])
        self.assertEqual(preflight_settings_seen, [runtime_settings])
        trace_payload = next(
            json.loads(event.split("data: ", 1)[1])
            for event in events
            if event.startswith("event: trace\n")
        )
        meta = trace_payload["step"]["meta"]
        self.assertEqual(meta["tool_registry_profile"], "planning_only")
        self.assertEqual(meta["tool_registry_provider_source"], "suite_a")
        self.assertEqual(meta["allowed_tool_labels"], ["Task Planner"])

    def test_build_tool_plan_summary_uses_display_labels(self) -> None:
        plan = build_tool_plan("请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]")

        self.assertEqual(
            build_tool_plan_summary(plan),
            "Planned tools: Task Planner, Knowledge Retrieval, calc_eval",
        )

    def test_build_usage_payload_supports_overall_and_planning_fields(self) -> None:
        planning_usage = chat_execution_module._build_usage_payload(  # type: ignore[attr-defined]
            prompt_text="planner prompt",
            completion_text="Planned tools: Task Planner, Knowledge Retrieval",
            provider_usage=ProviderUsage(
                prompt_tokens=10,
                completion_tokens=6,
                total_tokens=16,
            ),
        )
        final_usage = chat_execution_module._build_usage_payload(  # type: ignore[attr-defined]
            prompt_text="final prompt",
            completion_text="final answer",
            provider_usage=ProviderUsage(
                prompt_tokens=20,
                completion_tokens=8,
                total_tokens=28,
            ),
        )

        merged = chat_execution_module._merge_usage_payloads(  # type: ignore[attr-defined]
            final_usage=final_usage,
            planning_usage=planning_usage,
        )

        self.assertEqual(merged["prompt_tokens"], 20)
        self.assertEqual(merged["completion_tokens"], 8)
        self.assertEqual(merged["planning_prompt_tokens"], 10)
        self.assertEqual(merged["planning_completion_tokens"], 6)
        self.assertEqual(merged["overall_prompt_tokens"], 30)
        self.assertEqual(merged["overall_completion_tokens"], 14)
        self.assertEqual(merged["overall_total_tokens"], 44)
        self.assertEqual(merged["planning_usage_source"], "provider")

    def test_run_tool_keeps_calc_output_shape(self) -> None:
        output = run_tool(
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(
            output,
            {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            },
        )

    def test_run_tool_supports_task_plan_alias(self) -> None:
        output = run_tool(
            name="task_plan",
            tool_input={"prompt_preview": "请帮我规划"},
            prompt="请帮我检索知识库并计算 [calc:1+2*3]",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Retrieve supporting context -> Evaluate calculation -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Retrieve supporting context",
                    "Evaluate calculation",
                    "Synthesize final answer",
                ],
                "prompt_preview": "请帮我规划",
                "echo": True,
            },
        )

    def test_run_tool_supports_task_retrieve_alias(self) -> None:
        original_query = tool_runtime_module.query_knowledge_base

        def fake_query_knowledge_base(
            *,
            user_id: str,
            knowledge_base_id: str,
            query_text: str,
            top_k: int,
        ) -> dict[str, object]:
            self.assertEqual(user_id, "user-1")
            self.assertEqual(knowledge_base_id, "demo-kb")
            self.assertEqual(query_text, "检索 demo")
            self.assertEqual(top_k, 2)
            return {
                "hits": [{"content": "alpha"}],
                "hit_count": 1,
                "knowledge_base_id": knowledge_base_id,
                "collection": "kb_demo-kb",
            }

        tool_runtime_module.query_knowledge_base = fake_query_knowledge_base
        try:
            output = run_tool(
                name="task_retrieve",
                tool_input={
                    "query": "检索 demo",
                    "knowledge_base_id": "demo-kb",
                    "top_k": 2,
                },
                prompt="检索 demo",
                user_id="user-1",
                attempt=0,
            )
        finally:
            tool_runtime_module.query_knowledge_base = original_query

        self.assertEqual(
            output,
            {
                "chunks": ["alpha"],
                "hits": [{"content": "alpha"}],
                "hit_count": 1,
                "knowledge_base_id": "demo-kb",
                "collection": "kb_demo-kb",
            },
        )

    def test_run_tool_accepts_custom_registry_override(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "custom-ok",
                "tool_kind": "custom_calc",
            }

        registry = {
            "calc_eval": ToolRegistration(
                name="calc_eval",
                kind="custom_calc",
                label="Custom Calculator",
                retryable_by_default=False,
                default_timeout_ms=9_000,
                requires_user_context=False,
                supports_result_preview=True,
                runner=custom_runner,
            )
        }

        output = run_tool(
            name="calc_eval",
            tool_input={"expression": "ignored"},
            prompt="custom-calc",
            user_id="user-1",
            attempt=0,
            registry=registry,
        )

        self.assertEqual(
            output,
            {
                "result": "custom-ok",
                "tool_kind": "custom_calc",
            },
        )
        self.assertEqual(
            runner_calls,
            [({"expression": "ignored"}, "custom-calc", "")],
        )

    def test_run_tool_accepts_custom_registry_loader_override(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "loader-ok",
                "tool_kind": "loader_calc",
            }

        def custom_loader() -> dict[str, ToolRegistration]:
            return {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }

        output = run_tool(
            name="calc_eval",
            tool_input={"expression": "ignored"},
            prompt="loader-calc",
            user_id="user-1",
            attempt=0,
            registry_loader=custom_loader,
        )

        self.assertEqual(
            output,
            {
                "result": "loader-ok",
                "tool_kind": "loader_calc",
            },
        )
        self.assertEqual(
            runner_calls,
            [({"expression": "ignored"}, "loader-calc", "")],
        )

    def test_run_tool_accepts_custom_registry_provider_override(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "provider-ok",
                "tool_kind": "provider_calc",
            }

        provider = StaticToolRegistryProvider(
            registry={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="provider_calc",
                    label="Provider Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=13_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }
        )

        output = run_tool(
            name="calc_eval",
            tool_input={"expression": "ignored"},
            prompt="provider-calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )

        self.assertEqual(
            output,
            {
                "result": "provider-ok",
                "tool_kind": "provider_calc",
            },
        )
        self.assertEqual(
            runner_calls,
            [({"expression": "ignored"}, "provider-calc", "")],
        )

    def test_run_tool_keeps_transient_error_semantics(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            run_tool(
                name="mock_plan",
                tool_input={"prompt_preview": "x"},
                prompt="[mock-tool-error]",
                user_id="user-1",
                attempt=0,
            )

        self.assertFalse(ctx.exception.fatal)
        self.assertIn("transient error", str(ctx.exception).lower())

    def test_execute_tool_spec_keeps_calc_behavior(self) -> None:
        output = execute_tool_spec(
            tool_spec={
                "name": "calc_eval",
                "input": {"expression": "2**3"},
            },
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(
            output,
            {
                "expression": "2**3",
                "result": 8.0,
                "tool_kind": "local_calculator",
            },
        )

    def test_execute_tool_spec_accepts_custom_registry_override(self) -> None:
        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            return {
                "echo_input": tool_input,
                "tool_kind": "custom_calc",
                "prompt": prompt,
                "user_id": user_id,
            }

        registry = {
            "calc_eval": ToolRegistration(
                name="calc_eval",
                kind="custom_calc",
                label="Custom Calculator",
                retryable_by_default=False,
                default_timeout_ms=9_000,
                requires_user_context=False,
                supports_result_preview=True,
                runner=custom_runner,
            )
        }

        output = execute_tool_spec(
            tool_spec={"name": "calc_eval", "input": {"expression": "9*9"}},
            prompt="custom-calc",
            user_id="user-1",
            attempt=0,
            registry=registry,
        )

        self.assertEqual(
            output,
            {
                "echo_input": {"expression": "9*9"},
                "tool_kind": "custom_calc",
                "prompt": "custom-calc",
                "user_id": "",
            },
        )

    def test_execute_tool_spec_unknown_tool_remains_fatal(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            execute_tool_spec(
                tool_spec={"name": "does_not_exist", "input": {}},
                prompt="noop",
                user_id="user-1",
                attempt=0,
            )

        self.assertTrue(ctx.exception.fatal)
        self.assertIn("unknown tool", str(ctx.exception).lower())

    def test_registered_tool_names_cover_current_mock_tools(self) -> None:
        self.assertEqual(
            get_registered_tool_names(),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_get_default_tool_registry_returns_copy_of_current_entries(self) -> None:
        registry = get_default_tool_registry()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_plan", "task_retrieve"),
        )
        registry.pop("calc_eval")
        self.assertEqual(
            get_registered_tool_names(),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_get_default_tool_registry_provider_returns_isolated_snapshot(self) -> None:
        provider = get_default_tool_registry_provider()
        registry = provider.load_tool_registry()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_plan", "task_retrieve"),
        )
        registry.pop("calc_eval")
        self.assertEqual(
            tuple(sorted(provider.load_tool_registry())),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_get_default_tool_registry_provider_returns_default_provider_impl(self) -> None:
        provider = get_default_tool_registry_provider()

        self.assertIsInstance(provider, DefaultToolRegistryProvider)

    def test_build_tool_registry_provider_without_args_returns_default_provider(self) -> None:
        provider = build_tool_registry_provider()

        self.assertIsInstance(provider, DefaultToolRegistryProvider)
        self.assertEqual(
            tuple(sorted(provider.load_tool_registry())),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_default_tool_registry_provider_loads_fresh_snapshot_per_call(self) -> None:
        provider = DefaultToolRegistryProvider()
        first = provider.load_tool_registry()
        second = provider.load_tool_registry()

        self.assertEqual(
            tuple(sorted(first)),
            ("calc_eval", "task_plan", "task_retrieve"),
        )
        self.assertEqual(
            tuple(sorted(second)),
            ("calc_eval", "task_plan", "task_retrieve"),
        )
        self.assertIsNot(first, second)

    def test_build_tool_registry_provider_with_loader_and_overrides_returns_configured_provider(self) -> None:
        def custom_loader() -> dict[str, ToolRegistration]:
            return {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            }

        provider = build_tool_registry_provider(
            loader=custom_loader,
            overrides={
                "custom_lookup": ToolRegistration(
                    name="custom_lookup",
                    kind="custom_lookup",
                    label="Custom Lookup",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=False,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            },
        )

        self.assertIsInstance(provider, ConfiguredToolRegistryProvider)
        self.assertEqual(
            tuple(sorted(provider.load_tool_registry())),
            ("calc_eval", "custom_lookup"),
        )
        self.assertEqual(
            provider.load_tool_registry()["calc_eval"].kind,
            "loader_calc",
        )

    def test_resolve_tool_registry_provider_wraps_explicit_registry(self) -> None:
        provider = resolve_tool_registry_provider(
            registry={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="wrapped_calc",
                    label="Wrapped Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=8_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            }
        )

        self.assertIsInstance(provider, StaticToolRegistryProvider)
        self.assertEqual(
            provider.load_tool_registry()["calc_eval"].kind,
            "wrapped_calc",
        )

    def test_build_tool_registry_provider_prefers_explicit_provider_over_loader(self) -> None:
        provider = build_tool_registry_provider(
            provider=StaticToolRegistryProvider(
                registry={
                    "calc_eval": ToolRegistration(
                        name="calc_eval",
                        kind="provider_calc",
                        label="Provider Calculator",
                        retryable_by_default=False,
                        default_timeout_ms=13_000,
                        requires_user_context=False,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "tool_input": tool_input,
                            "prompt": prompt,
                            "user_id": user_id,
                        },
                    )
                }
            ),
            loader=lambda: {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            },
        )

        self.assertIsInstance(provider, StaticToolRegistryProvider)
        self.assertEqual(
            provider.load_tool_registry()["calc_eval"].kind,
            "provider_calc",
        )

    def test_resolve_tool_registry_provider_prefers_explicit_registry_over_provider_and_loader(self) -> None:
        provider = resolve_tool_registry_provider(
            registry={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="registry_calc",
                    label="Registry Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=8_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            },
            registry_provider=StaticToolRegistryProvider(
                registry={
                    "calc_eval": ToolRegistration(
                        name="calc_eval",
                        kind="provider_calc",
                        label="Provider Calculator",
                        retryable_by_default=False,
                        default_timeout_ms=13_000,
                        requires_user_context=False,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "tool_input": tool_input,
                            "prompt": prompt,
                            "user_id": user_id,
                        },
                    )
                }
            ),
            registry_loader=lambda: {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            },
        )

        self.assertIsInstance(provider, StaticToolRegistryProvider)
        self.assertEqual(
            provider.load_tool_registry()["calc_eval"].kind,
            "registry_calc",
        )

    def test_get_configured_tool_registry_provider_returns_default_provider_stack(self) -> None:
        provider = get_configured_tool_registry_provider()

        self.assertIsInstance(provider, DefaultToolRegistryProvider)
        self.assertEqual(
            tuple(sorted(provider.load_tool_registry())),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_build_tool_registry_overrides_from_settings_updates_known_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "label": "Configured Calculator",
                        "default_timeout_ms": 9_999,
                        "retryable_by_default": False,
                    }
                }
            )
        )

        overrides = build_tool_registry_overrides_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(overrides)), ("calc_eval",))
        self.assertEqual(overrides["calc_eval"].label, "Configured Calculator")
        self.assertEqual(overrides["calc_eval"].default_timeout_ms, 9_999)
        self.assertFalse(overrides["calc_eval"].retryable_by_default)
        self.assertEqual(overrides["calc_eval"].kind, "local_calculator")

    def test_build_tool_registry_settings_config_supports_disabled_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "label": "Configured Calculator",
                        "enabled": False,
                    },
                    "mock_retrieve": {
                        "enabled": False,
                    },
                }
            )
        )

        config = build_tool_registry_settings_config(settings=settings)

        self.assertEqual(tuple(sorted(config.overrides)), ("calc_eval",))
        self.assertEqual(
            config.disabled_tool_names,
            ("calc_eval", "task_retrieve"),
        )
        self.assertEqual(
            get_disabled_tool_names_from_settings(settings=settings),
            ("calc_eval", "task_retrieve"),
        )

    def test_build_tool_registry_profile_settings_config_supports_planning_only_profile(self) -> None:
        config = build_tool_registry_profile_settings_config(profile_name="planning_only")

        self.assertEqual(config.overrides, {})
        self.assertEqual(
            config.disabled_tool_names,
            ("calc_eval", "task_retrieve"),
        )

    def test_build_tool_registry_settings_config_allows_reenable_over_profile_disable(self) -> None:
        settings = SimpleNamespace(
            tool_registry_profile="planning_only",
            tool_registry_overrides_json=json.dumps(
                {
                    "mock_retrieve": {
                        "enabled": True,
                        "label": "Profile Reenabled Retrieve",
                    }
                }
            ),
        )

        config = build_tool_registry_settings_config(settings=settings)

        self.assertEqual(
            config.disabled_tool_names,
            ("calc_eval",),
        )
        self.assertEqual(
            config.overrides["task_retrieve"].label,
            "Profile Reenabled Retrieve",
        )

    def test_build_tool_registry_extra_tools_from_settings_clones_template_registration(self) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "template": "calc_eval",
                        "label": "Fast Calculator",
                        "default_timeout_ms": 1_500,
                        "retryable_by_default": False,
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(extra_tools)), ("calc_eval_fast",))
        self.assertEqual(extra_tools["calc_eval_fast"].name, "calc_eval_fast")
        self.assertEqual(extra_tools["calc_eval_fast"].label, "Fast Calculator")
        self.assertEqual(extra_tools["calc_eval_fast"].default_timeout_ms, 1_500)
        self.assertFalse(extra_tools["calc_eval_fast"].retryable_by_default)
        self.assertEqual(extra_tools["calc_eval_fast"].kind, "local_calculator")

    def test_build_tool_registry_extra_tools_from_settings_ignores_unknown_template_and_existing_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval": {
                        "template": "calc_eval",
                        "label": "Should Ignore Existing Name",
                    },
                    "custom_unknown": {
                        "template": "missing_tool",
                        "label": "Should Ignore Unknown Template",
                    },
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(extra_tools, {})

    def test_build_tool_registry_provider_sources_from_settings_groups_named_sources(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "analytics_suite": {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                            "default_timeout_ms": 1_500,
                        }
                    },
                    "retrieval_suite": {
                        "mock_retrieve_hot": {
                            "template": "mock_retrieve",
                            "label": "Hot Retrieval",
                        }
                    },
                }
            )
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(sources)), ("analytics_suite", "retrieval_suite"))
        self.assertEqual(
            tuple(sorted(sources["analytics_suite"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            sources["analytics_suite"].load_tool_registry()["calc_eval_fast"].label,
            "Fast Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_supports_adapter_shape(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "provider": "default",
                        "profile": "planning_only",
                        "disabled_tool_names": ["mock_plan"],
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(sources)), ("planning_suite",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            sources["planning_suite"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_ignores_bad_shapes(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "broken": "bad-shape",
                    "also_broken": {
                        "calc_eval": {
                            "template": "missing_template",
                        }
                    },
                }
            )
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(sources, {})

    def test_build_tool_registry_provider_sources_from_settings_ignores_unknown_provider_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "broken_suite": {
                        "provider": "missing",
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                            }
                        },
                    }
                }
            )
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(sources, {})

    def test_build_tool_registry_providers_from_settings_supports_loader_adapter_shape(self) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "loader": "default",
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(
            providers["planning_provider"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_loaders_from_settings_supports_adapter_shape(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader": "default",
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        loaders = build_tool_registry_loaders_from_settings(settings=settings)
        planning_registry = loaders["planning_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("planning_loader",))
        self.assertEqual(
            tuple(sorted(planning_registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(planning_registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loaders_from_settings_supports_loader_factory_shape(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader_factory": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        loaders = build_tool_registry_loaders_from_settings(settings=settings)
        planning_registry = loaders["planning_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("planning_loader",))
        self.assertEqual(
            tuple(sorted(planning_registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(planning_registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loaders_from_settings_reuses_shared_profile_name_helper(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "profile": " Planning_Only ",
                    }
                }
            )
        )
        original_get_tool_registry_profile_name_from_settings = (
            tool_runtime_module.get_tool_registry_profile_name_from_settings
        )
        captured: list[object] = []
        try:
            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "calculator_only"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            loaders = build_tool_registry_loaders_from_settings(settings=settings)
        finally:
            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )

        self.assertEqual(tuple(sorted(loaders)), ("planning_loader",))
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(
            tuple(sorted(loaders["planning_loader"]())),
            ("calc_eval",),
        )

    def test_build_tool_registry_loaders_from_settings_reuses_shared_profile_name_helper_for_factory_hint(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader_factory": "custom_factory",
                    }
                }
            )
        )
        original_get_tool_registry_profile_name_from_settings = (
            tool_runtime_module.get_tool_registry_profile_name_from_settings
        )
        original_build_tool_registry_loader_factories_from_settings = (
            tool_runtime_module.build_tool_registry_loader_factories_from_settings
        )
        captured: list[object] = []
        try:
            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "calculator_only"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            def fake_build_tool_registry_loader_factories_from_settings(*, settings=None):
                def factory(_settings=None):
                    return tool_runtime_module.get_default_tool_registry

                setattr(factory, "_tool_registry_profile_name", " Planning_Only ")
                return {"custom_factory": factory}

            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            tool_runtime_module.build_tool_registry_loader_factories_from_settings = (
                fake_build_tool_registry_loader_factories_from_settings
            )
            loaders = build_tool_registry_loaders_from_settings(settings=settings)
        finally:
            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )
            tool_runtime_module.build_tool_registry_loader_factories_from_settings = (
                original_build_tool_registry_loader_factories_from_settings
            )

        self.assertEqual(tuple(sorted(loaders)), ("planning_loader",))
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(
            tuple(sorted(loaders["planning_loader"]())),
            ("calc_eval",),
        )

    def test_build_tool_registry_loader_factories_from_settings_supports_named_factory_alias(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loader_factories_json=json.dumps(
                {
                    "planning_factory": {
                        "factory": "planning_only",
                    }
                }
            )
        )

        factories = build_tool_registry_loader_factories_from_settings(settings=settings)
        planning_registry = factories["planning_factory"](settings)()

        self.assertEqual(tuple(sorted(factories)), ("planning_factory",))
        self.assertEqual(
            tuple(sorted(planning_registry)),
            ("task_plan",),
        )

    def test_build_tool_registry_loader_factories_from_settings_reuse_shared_reference_normalizer_for_factory_key(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loader_factories_json=json.dumps(
                {
                    " Planning_Factory ": {
                        "factory": "planning_only",
                    }
                }
            )
        )
        original_normalize_named_tool_registry_component_name = getattr(
            tool_runtime_module,
            "_normalize_named_tool_registry_component_name",
        )
        captured: list[object] = []
        try:
            def fake_normalize_named_tool_registry_component_name(
                name: object | None,
            ) -> str | None:
                captured.append(name)
                if name == " Planning_Factory ":
                    return "planning_factory_shadow"
                if not isinstance(name, str):
                    return None
                normalized = name.strip().lower()
                return normalized or None

            tool_runtime_module._normalize_named_tool_registry_component_name = (
                fake_normalize_named_tool_registry_component_name
            )
            factories = build_tool_registry_loader_factories_from_settings(settings=settings)
        finally:
            tool_runtime_module._normalize_named_tool_registry_component_name = (
                original_normalize_named_tool_registry_component_name
            )

        self.assertIn(" Planning_Factory ", captured)
        self.assertEqual(tuple(sorted(factories)), ("planning_factory_shadow",))
        self.assertEqual(
            tuple(sorted(factories["planning_factory_shadow"](settings)())),
            ("task_plan",),
        )

    def test_build_tool_registry_provider_factories_from_settings_supports_named_factory_alias(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_factories_json=json.dumps(
                {
                    "planning_factory": {
                        "factory": "planning_only",
                    }
                }
            )
        )

        factories = build_tool_registry_provider_factories_from_settings(settings=settings)
        planning_registry = factories["planning_factory"](settings).load_tool_registry()

        self.assertEqual(tuple(sorted(factories)), ("planning_factory",))
        self.assertEqual(
            tuple(sorted(planning_registry)),
            ("task_plan",),
        )

    def test_build_tool_registry_loader_factories_from_settings_supports_registry_file_factory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(registry_file),
                        }
                    }
                )
            )

            factories = build_tool_registry_loader_factories_from_settings(settings=settings)
            file_registry = factories["file_factory"](settings)()

        self.assertEqual(tuple(sorted(factories)), ("file_factory",))
        self.assertEqual(tuple(sorted(file_registry)), ("calc_eval_fast",))
        self.assertEqual(file_registry["calc_eval_fast"].label, "Fast Calculator")

    def test_build_tool_registry_provider_factories_from_settings_supports_registry_file_factory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(registry_file),
                        }
                    }
                )
            )

            factories = build_tool_registry_provider_factories_from_settings(settings=settings)
            file_registry = factories["file_factory"](settings).load_tool_registry()

        self.assertEqual(tuple(sorted(factories)), ("file_factory",))
        self.assertEqual(tuple(sorted(file_registry)), ("calc_eval_fast",))
        self.assertEqual(file_registry["calc_eval_fast"].label, "Fast Calculator")

    def test_build_tool_registry_loader_from_file_supports_manifest_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry-manifest.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            loader = build_tool_registry_loader_from_file(registry_file=str(registry_file))
            self.assertIsNotNone(loader)
            registry = loader()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_provider_from_file_supports_manifest_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry-manifest.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "profile": "retrieval_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Retrieval Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            provider = build_tool_registry_provider_from_file(registry_file=str(registry_file))
            self.assertIsNotNone(provider)
            registry = provider.load_tool_registry()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_retrieve"),
        )
        self.assertEqual(registry["calc_eval"].label, "Retrieval Calculator")

    def test_build_tool_registry_from_file_supports_registry_files_composition(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = Path(tmpdir) / "base-registry.json"
            base_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            overlay_file = Path(tmpdir) / "overlay-manifest.json"
            overlay_file.write_text(
                json.dumps(
                    {
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "mock_plan_brief": {
                                "template": "mock_plan",
                                "label": "Brief Planner",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [
                            str(base_file),
                            str(overlay_file),
                        ]
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "mock_plan_brief", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_resolves_relative_registry_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixtures_dir = Path(tmpdir) / "fixtures"
            fixtures_dir.mkdir()
            nested_dir = fixtures_dir / "nested"
            nested_dir.mkdir()

            base_file = fixtures_dir / "base-registry.json"
            base_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            overlay_file = fixtures_dir / "overlay-manifest.json"
            overlay_file.write_text(
                json.dumps(
                    {
                        "profile": "retrieval_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Retrieval Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            root_file = nested_dir / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [
                            "../base-registry.json",
                            "../overlay-manifest.json",
                        ]
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_retrieve"),
        )
        self.assertEqual(registry["calc_eval"].label, "Retrieval Calculator")

    def test_build_tool_registry_from_file_supports_registry_dirs_composition(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_dir = Path(tmpdir) / "registry-parts"
            registry_dir.mkdir()
            (registry_dir / "10-base.json").write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            (registry_dir / "20-overlay.json").write_text(
                json.dumps(
                    {
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "mock_plan_brief": {
                                "template": "mock_plan",
                                "label": "Brief Planner",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_dirs": [str(registry_dir)],
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "mock_plan_brief", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_resolves_relative_registry_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixtures_dir = Path(tmpdir) / "fixtures"
            fixtures_dir.mkdir()
            nested_dir = fixtures_dir / "nested"
            nested_dir.mkdir()
            registry_dir = fixtures_dir / "registry-parts"
            registry_dir.mkdir()
            (registry_dir / "10-base.json").write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            (registry_dir / "20-overlay.json").write_text(
                json.dumps(
                    {
                        "profile": "retrieval_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Retrieval Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            root_file = nested_dir / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_dirs": ["../registry-parts"],
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_retrieve"),
        )
        self.assertEqual(registry["calc_eval"].label, "Retrieval Calculator")

    def test_build_tool_registry_from_file_supports_registry_sources_from_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = Path(tmpdir) / "base-registry.json"
            base_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["planning_suite"],
                        "registry_files": [str(base_file)],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider_factory": "planning_only",
                            "overrides": {
                                "calc_eval": {
                                    "enabled": True,
                                    "label": "Planning Calculator",
                                }
                            },
                        }
                    }
                )
            )

            registry = build_tool_registry_from_file(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_reuses_shared_provider_source_name_helper_for_registry_sources(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": [" Planning_Suite "],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite_shadow": {
                            "provider_factory": "planning_only",
                            "overrides": {
                                "calc_eval": {
                                    "enabled": True,
                                    "label": "Planning Calculator",
                                }
                            },
                        }
                    }
                )
            )
            original_get_tool_registry_provider_source_name_from_settings = (
                tool_runtime_module.get_tool_registry_provider_source_name_from_settings
            )
            captured: list[object] = []
            try:
                def fake_get_tool_registry_provider_source_name_from_settings(
                    *,
                    settings=None,
                ):
                    captured.append(
                        getattr(settings, "tool_registry_provider_source", None)
                    )
                    if (
                        getattr(settings, "tool_registry_provider_source", None)
                        == " Planning_Suite "
                    ):
                        return "planning_suite_shadow"
                    return original_get_tool_registry_provider_source_name_from_settings(
                        settings=settings
                    )

                tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                    fake_get_tool_registry_provider_source_name_from_settings
                )
                registry = build_tool_registry_from_file(
                    registry_file=str(root_file),
                    settings=settings,
                )
            finally:
                tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                    original_get_tool_registry_provider_source_name_from_settings
                )

        self.assertIn(" Planning_Suite ", captured)
        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loader_from_file_supports_registry_sources_from_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["planning_suite"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider_factory": "planning_only",
                            "overrides": {
                                "calc_eval": {
                                    "enabled": True,
                                    "label": "Planning Calculator",
                                }
                            },
                        }
                    }
                )
            )

            loader = build_tool_registry_loader_from_file(
                registry_file=str(root_file),
                settings=settings,
            )
            self.assertIsNotNone(loader)
            registry = loader()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_providers_from_settings_accepts_registry_file_with_registry_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["planning_suite"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider_factory": "planning_only",
                            "overrides": {
                                "calc_eval": {
                                    "enabled": True,
                                    "label": "Planning Calculator",
                                }
                            },
                        }
                    }
                ),
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            providers = build_tool_registry_providers_from_settings(settings=settings)
            registry = providers["file_provider"].load_tool_registry()

        self.assertEqual(tuple(sorted(providers)), ("file_provider",))
        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_ignores_duplicate_registry_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": [
                            "planning_suite",
                            "planning_suite",
                        ],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider_factory": "planning_only",
                            "overrides": {
                                "calc_eval": {
                                    "enabled": True,
                                    "label": "Planning Calculator",
                                }
                            },
                        }
                    }
                )
            )

            registry = build_tool_registry_from_file(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_ignores_duplicate_registry_files_and_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = Path(tmpdir) / "base-registry.json"
            base_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_dir = Path(tmpdir) / "registry-parts"
            registry_dir.mkdir()
            (registry_dir / "10-overlay.json").write_text(
                json.dumps(
                    {
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(base_file), str(base_file)],
                        "registry_dirs": [str(registry_dir), str(registry_dir)],
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_ignores_registry_file_self_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = Path(tmpdir) / "base-registry.json"
            base_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [
                            str(root_file),
                            str(base_file),
                        ],
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(tuple(sorted(registry)), ("calc_eval_fast",))

    def test_build_tool_registry_from_file_ignores_registry_dir_replayed_via_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixtures_dir = Path(tmpdir) / "fixtures"
            fixtures_dir.mkdir()
            nested_dir = fixtures_dir / "nested"
            nested_dir.mkdir()
            registry_dir = fixtures_dir / "registry-parts"
            registry_dir.mkdir()
            (registry_dir / "10-overlay.json").write_text(
                json.dumps(
                    {
                        "profile": "retrieval_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Retrieval Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            root_file = nested_dir / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_dirs": [
                            str(registry_dir),
                            "../registry-parts",
                        ],
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_retrieve"),
        )
        self.assertEqual(registry["calc_eval"].label, "Retrieval Calculator")

    def test_build_tool_registry_from_file_artifacts_reports_skipped_duplicate_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = Path(tmpdir) / "base-registry.json"
            base_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_dir = Path(tmpdir) / "registry-parts"
            registry_dir.mkdir()
            (registry_dir / "10-overlay.json").write_text(
                json.dumps(
                    {
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["planning_suite", "planning_suite"],
                        "registry_files": [str(base_file), str(base_file), str(root_file)],
                        "registry_dirs": [str(registry_dir), str(registry_dir)],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider_factory": "planning_only",
                        }
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(
            tuple(sorted(artifacts["registry"])),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        diagnostics = artifacts["diagnostics"]
        self.assertEqual(diagnostics["skipped_registry_sources"], ("planning_suite",))
        self.assertEqual(
            diagnostics["skipped_registry_files"],
            (str(base_file.resolve()), str(root_file.resolve())),
        )
        self.assertEqual(diagnostics["skipped_registry_dirs"], (str(registry_dir.resolve()),))

    def test_build_tool_registry_from_file_artifacts_reports_missing_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            missing_dir = Path(tmpdir) / "missing-registry-dir"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["missing_suite"],
                        "registry_files": [str(missing_file)],
                        "registry_dirs": [str(missing_dir)],
                    }
                ),
                encoding="utf-8",
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=SimpleNamespace(tool_registry_provider_sources_json=json.dumps({})),
            )

        self.assertEqual(artifacts["registry"], {})
        diagnostics = artifacts["diagnostics"]
        self.assertEqual(diagnostics["missing_registry_sources"], ("missing_suite",))
        self.assertEqual(
            diagnostics["missing_registry_files"],
            (str(missing_file.resolve()),),
        )
        self.assertEqual(diagnostics["missing_registry_dirs"], (str(missing_dir.resolve()),))

    def test_build_tool_registry_loader_from_file_artifacts_exposes_loader_and_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            artifacts = build_tool_registry_loader_from_file_artifacts(
                registry_file=str(root_file)
            )

        self.assertIsNotNone(artifacts["loader"])
        self.assertEqual(tuple(sorted(artifacts["registry"])), ("calc_eval_fast",))
        self.assertEqual(
            artifacts["loader"](),
            artifacts["registry"],
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_provider_from_file_artifacts_exposes_provider_and_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_dir = Path(tmpdir) / "missing-registry-dir"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_dirs": [str(missing_dir)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            artifacts = build_tool_registry_provider_from_file_artifacts(
                registry_file=str(root_file)
            )

        self.assertIsNotNone(artifacts["provider"])
        self.assertEqual(tuple(sorted(artifacts["registry"])), ("calc_eval_fast",))
        self.assertEqual(
            artifacts["provider"].load_tool_registry(),
            artifacts["registry"],
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_dirs"],
            (str(missing_dir.resolve()),),
        )

    def test_build_tool_registry_loaders_from_settings_artifacts_tracks_file_loader_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "registry_file": str(root_file),
                        }
                    }
                )
            )

            artifacts = build_tool_registry_loaders_from_settings_artifacts(settings=settings)

        self.assertEqual(tuple(sorted(artifacts["loaders"])), ("file_loader",))
        self.assertEqual(
            artifacts["loader_diagnostics"]["file_loader"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )
        self.assertEqual(
            tuple(sorted(artifacts["loaders"]["file_loader"]())),
            ("calc_eval_fast",),
        )

    def test_build_tool_registry_provider_sources_from_settings_artifacts_tracks_named_provider_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_dir = Path(tmpdir) / "missing-registry-dir"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_dirs": [str(missing_dir)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "provider": "file_provider",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(tuple(sorted(artifacts["sources"])), ("file_source",))
        self.assertEqual(
            artifacts["source_diagnostics"]["file_source"]["missing_registry_dirs"],
            (str(missing_dir.resolve()),),
        )
        self.assertEqual(
            tuple(sorted(artifacts["sources"]["file_source"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_build_tool_registry_provider_sources_from_settings_artifacts_reuse_shared_reference_normalizer_for_named_provider_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_dir = Path(tmpdir) / "missing-registry-dir"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_dirs": [str(missing_dir)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_providers_json=json.dumps(
                    {
                        "planning_provider_shadow": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider": " Planning_Provider ",
                        }
                    }
                ),
            )
            original_resolve_named_tool_registry_provider_reference = (
                tool_runtime_module.resolve_named_tool_registry_provider_reference
            )
            original_normalize_named_tool_registry_component_name = getattr(
                tool_runtime_module,
                "_normalize_named_tool_registry_component_name",
                None,
            )
            captured: list[object] = []
            try:
                def fake_normalize_named_tool_registry_component_name(
                    name: object | None,
                ) -> str | None:
                    captured.append(name)
                    if name == " Planning_Provider ":
                        return "planning_provider_shadow"
                    if not isinstance(name, str):
                        return None
                    normalized = name.strip().lower()
                    return normalized or None

                def fake_resolve_named_tool_registry_provider_reference(
                    name: str,
                    *,
                    named_providers=None,
                    named_sources=None,
                ):
                    if name == " Planning_Provider " and named_providers is not None:
                        return named_providers.get("planning_provider_shadow")
                    return original_resolve_named_tool_registry_provider_reference(
                        name,
                        named_providers=named_providers,
                        named_sources=named_sources,
                    )

                tool_runtime_module._normalize_named_tool_registry_component_name = (
                    fake_normalize_named_tool_registry_component_name
                )
                tool_runtime_module.resolve_named_tool_registry_provider_reference = (
                    fake_resolve_named_tool_registry_provider_reference
                )
                artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
                    settings=settings
                )
            finally:
                tool_runtime_module.resolve_named_tool_registry_provider_reference = (
                    original_resolve_named_tool_registry_provider_reference
                )
                if original_normalize_named_tool_registry_component_name is None:
                    delattr(
                        tool_runtime_module,
                        "_normalize_named_tool_registry_component_name",
                    )
                else:
                    tool_runtime_module._normalize_named_tool_registry_component_name = (
                        original_normalize_named_tool_registry_component_name
                    )

        self.assertIn(" Planning_Provider ", captured)
        self.assertEqual(tuple(sorted(artifacts["sources"])), ("planning_suite",))
        self.assertEqual(
            artifacts["source_diagnostics"]["planning_suite"]["missing_registry_dirs"],
            (str(missing_dir.resolve()),),
        )
        self.assertEqual(
            tuple(sorted(artifacts["sources"]["planning_suite"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_get_configured_tool_registry_provider_artifacts_exposes_selected_source_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            artifacts = get_configured_tool_registry_provider_artifacts(settings=settings)

        self.assertEqual(artifacts["provider_source_name"], "file_source")
        self.assertEqual(
            artifacts["selected_source_diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )
        self.assertEqual(
            tuple(sorted(artifacts["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_build_tool_registry_diagnostics_summary_keeps_shape(self) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": ("/tmp/base.json",),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": ("/tmp/missing-dir",),
        }

        result = build_tool_registry_diagnostics_summary(diagnostics=diagnostics)

        self.assertTrue(result["has_diagnostics"])
        self.assertEqual(result["skipped_total"], 2)
        self.assertEqual(result["missing_total"], 2)
        self.assertEqual(result["total"], 4)
        self.assertEqual(
            result["entries"],
            (
                {
                    "kind": "skipped",
                    "target": "registry_sources",
                    "count": 1,
                    "values": ("planning_suite",),
                },
                {
                    "kind": "skipped",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/base.json",),
                },
                {
                    "kind": "missing",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/missing.json",),
                },
                {
                    "kind": "missing",
                    "target": "registry_dirs",
                    "count": 1,
                    "values": ("/tmp/missing-dir",),
                },
            ),
        )

    def test_build_tool_registry_diagnostics_summary_model_keeps_fields(self) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_summary_model(diagnostics=diagnostics)

        self.assertTrue(result.has_diagnostics)
        self.assertEqual(result.skipped_total, 1)
        self.assertEqual(result.missing_total, 1)
        self.assertEqual(result.total, 2)
        self.assertEqual(result.entries[0]["kind"], "skipped")
        self.assertEqual(result.entries[1]["kind"], "missing")

    def test_build_tool_registry_diagnostics_runtime_artifacts_keep_shape(self) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="file_source",
            diagnostics=diagnostics,
        )

        self.assertTrue(result["summary"]["has_diagnostics"])
        self.assertEqual(
            result["trace_step"],
            {
                "id": "step-1",
                "seq": 4,
                "type": "observation",
                "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                "meta": {
                    "model": "mock-gpt",
                    "step_type": "tool_registry_diagnostics",
                    "tokens": None,
                    "cost_estimate": None,
                    "tool_registry": {
                        "provider_source": "file_source",
                        "has_diagnostics": True,
                        "skipped_total": 1,
                        "missing_total": 1,
                        "total": 2,
                        "entries": (
                            {
                                "kind": "skipped",
                                "target": "registry_sources",
                                "count": 1,
                                "values": ("planning_suite",),
                            },
                            {
                                "kind": "missing",
                                "target": "registry_files",
                                "count": 1,
                                "values": ("/tmp/missing.json",),
                            },
                        ),
                    },
                },
            },
        )
        self.assertEqual(
            result["trace_event"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": result["trace_step"],
            },
        )
        self.assertEqual(
            result["audit_detail"],
            {
                "provider_source": "file_source",
                "has_diagnostics": True,
                "skipped_total": 1,
                "missing_total": 1,
                "total": 2,
                "entries": (
                    {
                        "kind": "skipped",
                        "target": "registry_sources",
                        "count": 1,
                        "values": ("planning_suite",),
                    },
                    {
                        "kind": "missing",
                        "target": "registry_files",
                        "count": 1,
                        "values": ("/tmp/missing.json",),
                    },
                ),
            },
        )

    def test_build_tool_registry_diagnostics_runtime_artifacts_model_keeps_fields(
        self,
    ) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="file_source",
            diagnostics=diagnostics,
        )

        self.assertEqual(result.summary.total, 2)
        self.assertEqual(result.trace_step["id"], "step-1")
        self.assertEqual(result.trace_event["step_id"], "step-1")
        self.assertEqual(result.audit_detail["provider_source"], "file_source")

    def test_build_tool_registry_diagnostics_runtime_artifacts_keeps_empty_shape(self) -> None:
        diagnostics = {
            "skipped_registry_sources": (),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": (),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="default",
            diagnostics=diagnostics,
        )

        self.assertEqual(
            result["summary"],
            {
                "has_diagnostics": False,
                "skipped_total": 0,
                "missing_total": 0,
                "total": 0,
                "entries": (),
            },
        )
        self.assertIsNone(result["trace_step"])
        self.assertIsNone(result["trace_event"])
        self.assertIsNone(result["audit_detail"])

    def test_build_tool_registry_diagnostics_audit_event_keeps_shape(self) -> None:
        diagnostics_runtime = {
            "summary": {
                "has_diagnostics": True,
                "skipped_total": 1,
                "missing_total": 1,
                "total": 2,
                "entries": (
                    {
                        "kind": "skipped",
                        "target": "registry_sources",
                        "count": 1,
                        "values": ("planning_suite",),
                    },
                    {
                        "kind": "missing",
                        "target": "registry_files",
                        "count": 1,
                        "values": ("/tmp/missing.json",),
                    },
                ),
            },
            "trace_step": None,
            "trace_event": None,
            "audit_detail": {
                "provider_source": "file_source",
                "has_diagnostics": True,
                "skipped_total": 1,
                "missing_total": 1,
                "total": 2,
                "entries": (
                    {
                        "kind": "skipped",
                        "target": "registry_sources",
                        "count": 1,
                        "values": ("planning_suite",),
                    },
                    {
                        "kind": "missing",
                        "target": "registry_files",
                        "count": 1,
                        "values": ("/tmp/missing.json",),
                    },
                ),
            },
        }

        result = build_tool_registry_diagnostics_audit_event(
            diagnostics_runtime=diagnostics_runtime
        )

        self.assertEqual(
            result,
            {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": diagnostics_runtime["audit_detail"],
            },
        )

    def test_build_tool_registry_diagnostics_audit_event_returns_none_without_audit_detail(
        self,
    ) -> None:
        result = build_tool_registry_diagnostics_audit_event(
            diagnostics_runtime={
                "summary": {
                    "has_diagnostics": False,
                    "skipped_total": 0,
                    "missing_total": 0,
                    "total": 0,
                    "entries": (),
                },
                "trace_step": None,
                "trace_event": None,
                "audit_detail": None,
            }
        )

        self.assertIsNone(result)

    def test_build_tool_registry_diagnostics_audit_service_action_keeps_shape(self) -> None:
        audit_event = {
            "event_type": "tool_registry_diagnostics",
            "code": "tool_registry_diagnostics",
            "message": "Tool registry diagnostics detected during configured provider resolution.",
            "detail": {
                "provider_source": "file_source",
                "missing_total": 1,
            },
        }

        result = build_tool_registry_diagnostics_audit_service_action(
            audit_event=audit_event
        )

        self.assertEqual(
            result,
            {
                "kind": "record_audit_event",
                "kwargs": audit_event,
            },
        )

    def test_build_tool_registry_diagnostics_trace_service_action_keeps_shape(
        self,
    ) -> None:
        trace_step = {
            "id": "step-registry",
            "seq": 2,
            "type": "thought",
            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
        }
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-registry",
            "step": trace_step,
        }

        result = build_tool_registry_diagnostics_trace_service_action(
            trace_step=trace_step,
            trace_event=trace_event,
        )

        self.assertEqual(
            result,
            {
                "kind": "internal_trace_write",
                "trace_step": trace_step,
                "trace_event": trace_event,
                "persist_force": True,
            },
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_keeps_shape(
        self,
    ) -> None:
        runtime_artifacts = {
            "diagnostics_runtime": {
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
            },
            "audit_event": {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": {
                    "provider_source": "file_source",
                    "missing_total": 1,
                },
            }
        }

        result = build_configured_tool_registry_provider_runtime_service_actions(
            runtime_artifacts=runtime_artifacts
        )

        self.assertEqual(
            result,
            [
                {
                    "kind": "internal_trace_write",
                    "trace_step": runtime_artifacts["diagnostics_runtime"]["trace_step"],
                    "trace_event": runtime_artifacts["diagnostics_runtime"]["trace_event"],
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": runtime_artifacts["audit_event"],
                },
            ],
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_uses_model_helper(
        self,
    ) -> None:
        runtime_artifacts = {
            "diagnostics_runtime": {
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
            },
            "audit_event": {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": {
                    "provider_source": "file_source",
                    "missing_total": 1,
                },
            },
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model
        )
        captured: list[tuple[bool, bool]] = []

        def record_helper(
            *,
            runtime_artifacts: dict[str, object],
        ) -> object:
            captured.append(
                (
                    isinstance(runtime_artifacts.get("diagnostics_runtime"), dict),
                    isinstance(runtime_artifacts.get("audit_event"), dict),
                )
            )
            return original_helper(runtime_artifacts=runtime_artifacts)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions(
                runtime_artifacts=runtime_artifacts
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = original_helper

        self.assertEqual(captured, [(True, True)])
        self.assertEqual(
            tuple(item["kind"] for item in result),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_execute_configured_tool_registry_provider_runtime_service_actions_records_audit(
        self,
    ) -> None:
        calls: list[dict[str, object]] = []
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        service_actions = [
            {
                "kind": "internal_trace_write",
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
                "persist_force": True,
            },
            {
                "kind": "record_audit_event",
                "kwargs": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "Tool registry diagnostics detected during configured provider resolution.",
                    "detail": {
                        "provider_source": "file_source",
                        "missing_total": 1,
                    },
                },
            }
        ]

        result = execute_configured_tool_registry_provider_runtime_service_actions(
            service_actions=service_actions,
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: calls.append(kwargs),
        )

        self.assertEqual(trace_steps, [service_actions[0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(calls, [service_actions[1]["kwargs"]])
        self.assertEqual(
            result,
            {
                "trace_write_count": 1,
                "audit_event_count": 1,
            },
        )

    def test_execute_configured_tool_registry_provider_runtime_service_actions_uses_result_model_helper(
        self,
    ) -> None:
        calls: list[dict[str, object]] = []
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        service_actions = [
            {
                "kind": "internal_trace_write",
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
                "persist_force": True,
            },
            {
                "kind": "record_audit_event",
                "kwargs": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "Tool registry diagnostics detected during configured provider resolution.",
                    "detail": {
                        "provider_source": "file_source",
                        "missing_total": 1,
                    },
                },
            },
        ]
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = record_helper
        try:
            result = execute_configured_tool_registry_provider_runtime_service_actions(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(trace_steps, [service_actions[0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(calls, [service_actions[1]["kwargs"]])
        self.assertEqual(
            result,
            {
                "trace_write_count": 1,
                "audit_event_count": 1,
            },
        )

    def test_execute_configured_tool_registry_provider_runtime_service_actions_outputs_uses_result_model_helper(
        self,
    ) -> None:
        calls: list[dict[str, object]] = []
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        service_actions = [
            {
                "kind": "internal_trace_write",
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
                "persist_force": True,
            },
            {
                "kind": "record_audit_event",
                "kwargs": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "Tool registry diagnostics detected during configured provider resolution.",
                    "detail": {
                        "provider_source": "file_source",
                        "missing_total": 1,
                    },
                },
            },
        ]
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = record_helper
        try:
            result_model, result_dict = execute_configured_tool_registry_provider_runtime_service_actions_outputs(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 1)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)
        self.assertEqual(trace_steps, [service_actions[0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(calls, [service_actions[1]["kwargs"]])

    def test_build_configured_tool_registry_provider_runtime_artifacts_exposes_selected_source_runtime_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            artifacts = build_configured_tool_registry_provider_runtime_artifacts(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(artifacts["provider_source_name"], "file_source")
        self.assertEqual(
            artifacts["diagnostics_runtime"]["summary"]["missing_total"],
            1,
        )
        self.assertEqual(
            artifacts["diagnostics_runtime"]["trace_event"],
            {
                "task_id": "task-1",
                "step_id": "step-registry",
                "step": artifacts["diagnostics_runtime"]["trace_step"],
            },
        )
        self.assertEqual(
            artifacts["audit_event"],
            {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": artifacts["diagnostics_runtime"]["audit_detail"],
            },
        )
        self.assertEqual(
            tuple(sorted(artifacts["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_keeps_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = build_configured_tool_registry_provider_runtime_artifacts_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(result.audit_event["event_type"], "tool_registry_diagnostics")
        self.assertEqual(tuple(sorted(result.provider.load_tool_registry())), ("calc_eval_fast",))

    def test_build_configured_tool_registry_provider_service_execution_keeps_shape(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = build_configured_tool_registry_provider_service_execution(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(
            tuple(sorted(result["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            [item["kind"] for item in result["service_actions"]],
            ["internal_trace_write", "record_audit_event"],
        )
        self.assertEqual(
            result["runtime_artifacts"]["diagnostics_runtime"]["summary"]["missing_total"],
            1,
        )

    def test_build_configured_tool_registry_provider_service_execution_model_keeps_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_execute_configured_tool_registry_provider_service_execution_applies_actions(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {"provider_source_name": "file_source"},
            "service_actions": [
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                        },
                    },
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": {
                        "event_type": "tool_registry_diagnostics",
                        "code": "tool_registry_diagnostics",
                        "message": "Tool registry diagnostics detected during configured provider resolution.",
                        "detail": {
                            "provider_source": "file_source",
                            "missing_total": 1,
                        },
                    },
                },
            ],
        }

        result = execute_configured_tool_registry_provider_service_execution(
            service_execution=service_execution,
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
        )

        self.assertEqual(trace_steps, [service_execution["service_actions"][0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(audit_calls, [service_execution["service_actions"][1]["kwargs"]])
        self.assertIs(result["provider"], provider)
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(result["trace_write_count"], 1)
        self.assertEqual(result["audit_event_count"], 1)

    def test_execute_configured_tool_registry_provider_service_execution_uses_outputs_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {"provider_source_name": "file_source"},
            "service_actions": [
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                        },
                    },
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": {
                        "event_type": "tool_registry_diagnostics",
                        "code": "tool_registry_diagnostics",
                        "message": "Tool registry diagnostics detected during configured provider resolution.",
                        "detail": {
                            "provider_source": "file_source",
                            "missing_total": 1,
                        },
                    },
                },
            ],
        }
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs
        )
        captured: list[tuple[str, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    len(service_execution["service_actions"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs = record_helper
        try:
            result = execute_configured_tool_registry_provider_service_execution(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs = original_helper

        self.assertEqual(captured, [("file_source", 2)])
        self.assertIs(result["provider"], provider)
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(result["trace_write_count"], 1)
        self.assertEqual(result["audit_event_count"], 1)

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict_uses_result_model_helper(
        self,
    ) -> None:
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict
        )
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            execution_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(execution_result=execution_result)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict(
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict = original_helper

        self.assertEqual(captured, [(1, 2)])
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 2)

    def test_build_configured_tool_registry_provider_service_execution_outputs_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: dict[str, object],
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
        try:
            result_model, result_dict = build_configured_tool_registry_provider_service_execution_outputs(
                service_execution=service_execution,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertIs(result_model.provider, provider)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 2)

    def test_execute_configured_tool_registry_provider_service_execution_outputs_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {"provider_source_name": "file_source"},
            "service_actions": [
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                        },
                    },
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": {
                        "event_type": "tool_registry_diagnostics",
                        "code": "tool_registry_diagnostics",
                        "message": "Tool registry diagnostics detected during configured provider resolution.",
                        "detail": {
                            "provider_source": "file_source",
                            "missing_total": 1,
                        },
                    },
                },
            ],
        }
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
        )
        captured: list[tuple[str, int]] = []

        def record_helper(
            *,
            service_execution: object,
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    len(getattr(service_execution, "service_actions")),
                )
            )
            return original_helper(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
        try:
            result_model, result_dict = tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 2)])
        self.assertIs(result_model.provider, provider)
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)

    def test_build_configured_tool_registry_provider_service_execution_result_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }
        execution_result = {
            "trace_write_count": 1,
            "audit_event_count": 2,
        }

        result = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution,
            execution_result=execution_result,
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertEqual(result.runtime_artifacts.provider_source_name, "default")

    def test_build_configured_tool_registry_provider_service_execution_result_model_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: dict[str, object],
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
        try:
            result = build_configured_tool_registry_provider_service_execution_result_model(
                service_execution=service_execution,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_service_execution_result_model_uses_default_counts(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }

        result = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution,
            execution_result={},
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.trace_write_count, 0)
        self.assertEqual(result.audit_event_count, 0)
        self.assertEqual(result.runtime_artifacts.provider_source_name, "default")

    def test_build_configured_tool_registry_provider_service_execution_result_model_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        runtime_actions_result_model = build_configured_tool_registry_provider_runtime_service_actions_result_model(
            trace_write_count=1,
            audit_event_count=2,
        )

        result = build_configured_tool_registry_provider_service_execution_result_model_from_models(
            service_execution=service_execution_model,
            execution_result=runtime_actions_result_model,
        )

        self.assertIs(result.provider, service_execution_model.provider)
        self.assertEqual(result.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(result.runtime_artifacts.provider_source_name, service_execution_model.runtime_artifacts.provider_source_name)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 1,
                            "skipped_total": 0,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [],
            }
        )

        result = (
            build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model(
                service_execution=service_execution_model,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertTrue(result.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model_uses_outputs_from_models_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 1,
                            "skipped_total": 0,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [],
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(getattr(execution_result, "trace_write_count")),
                    int(getattr(execution_result, "audit_event_count")),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model(
                    service_execution=service_execution_model,
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model_uses_outputs_from_models_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 1,
                            "skipped_total": 0,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [],
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(getattr(execution_result, "trace_write_count")),
                    int(getattr(execution_result, "audit_event_count")),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
                    service_execution=service_execution_model,
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result_model.provider, provider)
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 2)

    def test_build_tool_registry_diagnostics_trace_service_action_model_keeps_fields(
        self,
    ) -> None:
        trace_step = {
            "id": "step-registry",
            "seq": 2,
            "type": "thought",
            "content": "diagnostics",
        }
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-registry",
            "step": trace_step,
        }

        result = build_tool_registry_diagnostics_trace_service_action_model(
            trace_step=trace_step,
            trace_event=trace_event,
            persist_force=True,
        )

        self.assertEqual(result.kind, "internal_trace_write")
        self.assertEqual(result.trace_step, trace_step)
        self.assertEqual(result.trace_event, trace_event)
        self.assertTrue(result.persist_force)
        self.assertIsNone(result.kwargs)

    def test_build_tool_registry_diagnostics_audit_service_action_model_keeps_fields(
        self,
    ) -> None:
        audit_event = {
            "event_type": "tool_registry_diagnostics",
            "code": "tool_registry_diagnostics",
            "message": "diagnostics detected",
            "detail": {"provider_source": "default"},
        }

        result = build_tool_registry_diagnostics_audit_service_action_model(
            audit_event=audit_event,
        )

        self.assertEqual(result.kind, "record_audit_event")
        self.assertIsNone(result.trace_step)
        self.assertIsNone(result.trace_event)
        self.assertFalse(result.persist_force)
        self.assertEqual(result.kwargs, audit_event)

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="file_source",
            runtime_artifacts={
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 1,
                        "missing_total": 2,
                        "total": 3,
                        "entries": ({"kind": "missing_file"},),
                    },
                    "trace_step": {"id": "step-registry"},
                    "trace_event": {"task_id": "task-1"},
                    "audit_detail": {"provider_source": "file_source"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.diagnostics_runtime.summary.total, 3)
        self.assertEqual(result.audit_event, {"event_type": "tool_registry_diagnostics"})

    def test_build_configured_tool_registry_provider_service_execution_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "skipped_total": 0,
                            "missing_total": 1,
                            "total": 1,
                            "entries": (),
                        }
                    }
                },
                "service_actions": [
                    {
                        "kind": "internal_trace_write",
                        "trace_step": {"id": "step-registry"},
                        "trace_event": {"task_id": "task-1"},
                        "persist_force": True,
                    },
                    {
                        "kind": "record_audit_event",
                        "kwargs": {"event_type": "tool_registry_diagnostics"},
                    },
                ],
            }
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_service_execution_model_from_dict_uses_runtime_service_actions_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(service_actions=service_actions)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = record_helper
        try:
            result = build_configured_tool_registry_provider_service_execution_model_from_dict(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "skipped_total": 0,
                                "missing_total": 1,
                                "total": 1,
                                "entries": (),
                            }
                        }
                    },
                    "service_actions": [
                        {
                            "kind": "internal_trace_write",
                            "trace_step": {"id": "step-registry"},
                            "trace_event": {"task_id": "task-1"},
                            "persist_force": True,
                        },
                        {
                            "kind": "record_audit_event",
                            "kwargs": {"event_type": "tool_registry_diagnostics"},
                        },
                    ],
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_service_execution_model_uses_typed_runtime_service_actions_model_helper(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = (
                tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model
            )
            captured: list[tuple[str, int]] = []

            def record_helper(
                *,
                runtime_artifacts: object,
            ) -> object:
                captured.append(
                    (
                        str(getattr(runtime_artifacts, "provider_source_name", None)),
                        int(
                            getattr(
                                getattr(runtime_artifacts, "diagnostics_runtime", None),
                                "summary",
                            ).missing_total
                        ),
                    )
                )
                return original_helper(runtime_artifacts=runtime_artifacts)

            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = record_helper
            try:
                result = build_configured_tool_registry_provider_service_execution_model(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                )
            finally:
                tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = original_helper

        self.assertEqual(captured, [("file_source", 1)])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_keeps_fields(
        self,
    ) -> None:
        result = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "diagnostics",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "diagnostics",
                        },
                    },
                },
                "audit_event": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "diagnostics detected",
                    "detail": {"provider_source": "file_source"},
                },
            },
        )

        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result.to_dict()),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_uses_typed_runtime_artifacts_helper(
        self,
    ) -> None:
        runtime_artifacts = {
            "diagnostics_runtime": {
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "diagnostics",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "diagnostics",
                    },
                },
            },
            "audit_event": {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "diagnostics detected",
                "detail": {"provider_source": "file_source"},
            },
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model
        )
        captured: list[tuple[str, bool]] = []

        def record_helper(
            *, runtime_artifacts: object
        ) -> object:
            captured.append(
                (
                    str(getattr(runtime_artifacts, "provider_source_name", None)),
                    hasattr(runtime_artifacts, "diagnostics_runtime"),
                )
            )
            return original_helper(runtime_artifacts=runtime_artifacts)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_model(
                runtime_artifacts=runtime_artifacts,
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = original_helper

        self.assertEqual(captured, [("default", True)])
        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(
                service_actions=service_actions_model,
            )
        )

        self.assertIs(result_model, service_actions_model)
        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="file_source",
            runtime_artifacts={
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 0,
                        "missing_total": 1,
                        "total": 1,
                    },
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model(
                runtime_artifacts=runtime_artifacts_model,
            )
        )

        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_uses_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model
        )
        captured: list[tuple[str, bool]] = []

        def record_helper(
            *, runtime_artifacts: dict[str, object]
        ) -> object:
            captured.append(
                (
                    str(runtime_artifacts.get("provider_source_name", "")),
                    runtime_artifacts.get("provider") is provider,
                )
            )
            return original_helper(runtime_artifacts=runtime_artifacts)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_runtime_service_actions_outputs(
                    runtime_artifacts={
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "skipped_total": 0,
                                "missing_total": 1,
                                "total": 1,
                            },
                            "trace_step": {"id": "step-registry", "seq": 2},
                            "trace_event": {"task_id": "task-1"},
                        },
                        "audit_event": {"event_type": "tool_registry_diagnostics"},
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = original_helper

        self.assertEqual(captured, [("file_source", True)])
        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model_uses_service_action_builders(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="file_source",
            runtime_artifacts={
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 0,
                        "missing_total": 1,
                        "total": 1,
                    },
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )
        original_trace_helper = (
            tool_runtime_module.build_tool_registry_diagnostics_trace_service_action_model
        )
        original_audit_helper = (
            tool_runtime_module.build_tool_registry_diagnostics_audit_service_action_model
        )
        captured: list[str] = []

        def record_helper(
            **kwargs: object,
        ) -> object:
            captured.append("trace")
            return original_trace_helper(**kwargs)

        def record_audit_helper(
            **kwargs: object,
        ) -> object:
            captured.append("audit")
            return original_audit_helper(**kwargs)

        tool_runtime_module.build_tool_registry_diagnostics_trace_service_action_model = record_helper
        tool_runtime_module.build_tool_registry_diagnostics_audit_service_action_model = record_audit_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model(
                runtime_artifacts=runtime_artifacts_model,
            )
        finally:
            tool_runtime_module.build_tool_registry_diagnostics_trace_service_action_model = original_trace_helper
            tool_runtime_module.build_tool_registry_diagnostics_audit_service_action_model = original_audit_helper

        self.assertEqual(captured, ["trace", "audit"])
        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_model_keeps_fields(
        self,
    ) -> None:
        result = build_configured_tool_registry_provider_runtime_service_actions_result_model(
            trace_write_count=1,
            audit_event_count=2,
        )

        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict_uses_result_model_builder(
        self,
    ) -> None:
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model
        )
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            trace_write_count: int,
            audit_event_count: int,
        ) -> object:
            captured.append(
                (
                    int(trace_write_count),
                    int(audit_event_count),
                )
            )
            return original_helper(
                trace_write_count=trace_write_count,
                audit_event_count=audit_event_count,
            )

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict(
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model = original_helper

        self.assertEqual(captured, [(1, 2)])
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models(
                execution_result=build_configured_tool_registry_provider_runtime_service_actions_result_model(
                    trace_write_count=1,
                    audit_event_count=2,
                )
            )
        )

        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(
            result_dict,
            {
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict_keeps_fields(
        self,
    ) -> None:
        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict(
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        )

        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(
            result_dict,
            {
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts_keeps_fields(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )

        result = build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
            service_actions=[trace_action.to_dict(), audit_action.to_dict()]
        )

        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertTrue(result.actions[0].persist_force)
        self.assertEqual(
            result.actions[1].kwargs,
            {"event_type": "tool_registry_diagnostics"},
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts_uses_action_model_builder(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_action_model_from_dict
        )
        captured: list[int] = []

        def record_helper(
            service_action: dict[str, object],
        ) -> object:
            captured.append(len(service_action))
            return original_helper(service_action)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_action_model_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
                service_actions=[trace_action.to_dict(), audit_action.to_dict()]
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_action_model_from_dict = original_helper

        self.assertEqual(captured, [4, 2])
        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts_uses_model_helper(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(service_actions=service_actions)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts(
                    service_actions=[trace_action.to_dict(), audit_action.to_dict()]
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts_keeps_fields(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )

        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts(
                service_actions=[trace_action.to_dict(), audit_action.to_dict()]
            )
        )

        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_execute_configured_tool_registry_provider_runtime_service_actions_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "diagnostics",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "diagnostics",
                        },
                    },
                },
                "audit_event": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "diagnostics detected",
                    "detail": {"provider_source": "file_source"},
                },
            },
        )

        result = execute_configured_tool_registry_provider_runtime_service_actions_model(
            service_actions=service_actions_model,
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
        )

        self.assertEqual(trace_steps, [service_actions_model.actions[0].trace_step])
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)

    def test_execute_configured_tool_registry_provider_runtime_service_actions_model_uses_result_model_from_models_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models
        )
        captured: list[tuple[str, ...]] = []

        def record_helper(
            *,
            service_actions: object,
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> object:
            captured.append(tuple(action.kind for action in getattr(service_actions, "actions")))
            return original_helper(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models = record_helper
        try:
            result = execute_configured_tool_registry_provider_runtime_service_actions_model(
                service_actions=service_actions_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models = original_helper

        self.assertEqual(captured, [("internal_trace_write", "record_audit_event")])
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        result_model, result_dict = (
            execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(
                service_actions=service_actions_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        )

        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 1)
        self.assertEqual(
            result_dict,
            {
                "trace_write_count": 1,
                "audit_event_count": 1,
            },
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_model_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )
            original_helper = (
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
            )
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, dict[str, object]]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        tuple(action.kind for action in getattr(service_execution, "service_actions")),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("internal_trace_write", "record_audit_event"))])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

            result_model, result_dict = (
                execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            )

        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result_model.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model_uses_outputs_from_models_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )
            original_helper = (
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_models
            )
            captured: list[tuple[str, int, int]] = []

            def record_helper(
                *,
                service_execution: object,
                execution_result: object,
            ) -> tuple[object, dict[str, object]]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        int(getattr(execution_result, "trace_write_count")),
                        int(getattr(execution_result, "audit_event_count")),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    execution_result=execution_result,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_models = record_helper
            try:
                result_model, result_dict = (
                    execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
                        service_execution=service_execution_model,
                        trace_steps=trace_steps,
                        persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                        record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                    )
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_models = original_helper

        self.assertEqual(
            captured,
            [("file_source", 1, 1)],
        )
        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_model_uses_outputs_from_service_execution_model_helper_for_trace_execution(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )
            original_helper = (
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
            )
            captured: list[tuple[int, int]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, dict[str, object]]:
                captured.append(
                    (
                        len(getattr(service_execution, "service_actions", ())),
                        len(trace_steps),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
            try:
                result_model = execute_configured_tool_registry_provider_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [(2, 0)])
        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_keeps_shape(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = execute_configured_tool_registry_provider_preflight(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(
            tuple(sorted(result["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            result["service_execution"]["runtime_artifacts"]["diagnostics_runtime"]["summary"]["missing_total"],
            1,
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
        self.assertEqual(result["trace_write_count"], 1)
        self.assertEqual(result["audit_event_count"], 1)
        self.assertEqual(
            result["summary"],
            {
                "provider_source_name": "file_source",
                "tool_count": 1,
                "tool_names": ("calc_eval_fast",),
                "service_action_count": 2,
                "service_action_kinds": ("internal_trace_write", "record_audit_event"),
                "trace_write_count": 1,
                "audit_event_count": 1,
                "has_diagnostics": True,
                "diagnostics_total": 1,
                "skipped_total": 0,
                "missing_total": 1,
            },
        )

    def test_execute_configured_tool_registry_provider_service_execution_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

            result = execute_configured_tool_registry_provider_service_execution_model(
                service_execution=service_execution_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(trace_steps, [service_execution_model.service_actions[0].trace_step])
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)

    def test_build_configured_tool_registry_provider_preflight_result_keeps_shape(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                    }
                }
            },
            "service_actions": [],
        }
        execution_result = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": service_execution["runtime_artifacts"],
            "trace_write_count": 1,
            "audit_event_count": 2,
        }

        result = build_configured_tool_registry_provider_preflight_result(
            service_execution=service_execution,
            execution_result=execution_result,
        )

        self.assertIs(result["provider"], provider)
        self.assertEqual(result["service_execution"]["provider_source_name"], "file_source")
        self.assertEqual(result["service_execution"]["service_actions"], [])
        self.assertEqual(
            result["summary"],
            {
                "provider_source_name": "file_source",
                "tool_count": 1,
                "tool_names": ("calc_eval",),
                "service_action_count": 0,
                "service_action_kinds": (),
                "trace_write_count": 1,
                "audit_event_count": 2,
                "has_diagnostics": True,
                "diagnostics_total": 0,
                "skipped_total": 0,
                "missing_total": 0,
            },
        )

    def test_build_configured_tool_registry_provider_preflight_result_uses_result_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                    }
                }
            },
            "service_actions": [],
        }
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            execution_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result(
                service_execution=service_execution,
                execution_result={
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": service_execution["runtime_artifacts"],
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result["provider"], provider)
        self.assertEqual(result["summary"]["tool_names"], ("calc_eval",))

    def test_build_configured_tool_registry_provider_preflight_summary_keeps_shape(
        self,
    ) -> None:
        preflight_result = {
            "provider_source_name": "default",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": False,
                    }
                }
            },
            "trace_write_count": 0,
            "audit_event_count": 1,
        }

        result = build_configured_tool_registry_provider_preflight_summary(
            preflight_result=preflight_result
        )

        self.assertEqual(
            result,
            {
                "provider_source_name": "default",
                "tool_count": 0,
                "tool_names": (),
                "service_action_count": 0,
                "service_action_kinds": (),
                "trace_write_count": 0,
                "audit_event_count": 1,
                "has_diagnostics": False,
                "diagnostics_total": 0,
                "skipped_total": 0,
                "missing_total": 0,
            },
        )

    def test_build_configured_tool_registry_provider_preflight_summary_uses_summary_model_helper(
        self,
    ) -> None:
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary(
                preflight_result={
                    "provider_source_name": "default",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "trace_write_count": 0,
                    "audit_event_count": 1,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model = original_helper

        self.assertEqual(captured, [(0, 1)])
        self.assertEqual(result["provider_source_name"], "default")
        self.assertEqual(result["audit_event_count"], 1)

    def test_build_configured_tool_registry_provider_preflight_summary_model_keeps_fields(
        self,
    ) -> None:
        preflight_result = {
            "provider_source_name": "default",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": False,
                        "total": 0,
                        "skipped_total": 0,
                        "missing_total": 0,
                    }
                }
            },
            "provider": StaticToolRegistryProvider({}),
            "service_execution": {"service_actions": []},
            "trace_write_count": 0,
            "audit_event_count": 1,
        }

        result = build_configured_tool_registry_provider_preflight_summary_model(
            preflight_result=preflight_result
        )

        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.tool_count, 0)
        self.assertEqual(result.tool_names, ())
        self.assertEqual(result.service_action_kinds, ())
        self.assertEqual(result.audit_event_count, 1)

    def test_build_configured_tool_registry_provider_preflight_summary_model_uses_summary_model_from_dict_helper(
        self,
    ) -> None:
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model_from_dict
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary_model(
                preflight_result={
                    "provider_source_name": "default",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "provider": StaticToolRegistryProvider({}),
                    "service_execution": {"service_actions": []},
                    "trace_write_count": 0,
                    "audit_event_count": 1,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model_from_dict = original_helper

        self.assertEqual(captured, [(0, 1)])
        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.audit_event_count, 1)

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_dict_uses_service_execution_defaults(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_preflight_summary_model_from_dict(
            preflight_result={
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 1,
                                "skipped_total": 0,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.tool_names, ("calc_eval",))
        self.assertEqual(result.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertEqual(result.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_dict_uses_result_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    str(preflight_result["service_execution"]["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.tool_names, ("calc_eval",))
        self.assertEqual(result.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_service_execution_model_from_dict_merges_runtime_artifacts(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "provider_source_name": "top_level_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "service_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "service_source")
        self.assertEqual(result.service_actions[0].kind, "record_audit_event")
        self.assertTrue(result.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.total, 2)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.skipped_total, 1)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_model_from_dict_uses_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict
        )
        captured: list[tuple[str, int]] = []

        def record_helper(*, preflight_result: dict[str, object]) -> dict[str, object]:
            service_execution = original_helper(preflight_result=preflight_result)
            runtime_artifacts = service_execution["runtime_artifacts"]
            summary = runtime_artifacts["diagnostics_runtime"]["summary"]
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(summary["missing_total"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "provider_source_name": "top_level_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "service_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict = original_helper

        self.assertEqual(captured, [("service_source", 1)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "service_source")
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = (
            build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict(
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertTrue(result.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict_uses_service_execution_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict
        )
        captured: list[tuple[str, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            service_execution_model = original_helper(preflight_result=preflight_result)
            captured.append(
                (
                    str(getattr(service_execution_model, "provider_source_name", None)),
                    int(
                        service_execution_model.runtime_artifacts.diagnostics_runtime.summary.missing_total
                    ),
                )
            )
            return service_execution_model

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict(
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                        "service_execution": {
                            "provider": provider,
                            "provider_source_name": "file_source",
                            "runtime_artifacts": {
                                "diagnostics_runtime": {
                                    "summary": {
                                        "has_diagnostics": True,
                                        "total": 1,
                                        "skipped_total": 0,
                                        "missing_total": 1,
                                    }
                                }
                            },
                            "service_actions": [{"kind": "record_audit_event"}],
                        },
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )
        result = (
            build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertTrue(result.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.total, 2)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model_uses_service_execution_result_model_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    execution_result["trace_write_count"],
                    execution_result["audit_event_count"],
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
                    service_execution=service_execution_model,
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model, execution_result_model = (
            build_configured_tool_registry_provider_preflight_execution_models_from_dict(
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(service_execution_model.service_actions[0].kind, "record_audit_event")
        self.assertTrue(
            service_execution_model.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics
        )
        self.assertEqual(
            service_execution_model.runtime_artifacts.diagnostics_runtime.summary.total, 2
        )
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1
        )

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_dict_uses_service_execution_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict
        captured: list[tuple[str, int]] = []

        def record_models_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            service_execution_model = original_helper(preflight_result=preflight_result)
            captured.append(
                (
                    str(getattr(service_execution_model, "provider_source_name", None)),
                    int(
                        service_execution_model.runtime_artifacts.diagnostics_runtime.summary.missing_total
                    ),
                )
            )
            return service_execution_model

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = record_models_helper
        try:
            service_execution_model, execution_result_model = (
                build_configured_tool_registry_provider_preflight_execution_models_from_dict(
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                        "service_execution": {
                            "provider": provider,
                            "provider_source_name": "file_source",
                            "runtime_artifacts": {
                                "diagnostics_runtime": {
                                    "summary": {
                                        "has_diagnostics": True,
                                        "total": 1,
                                        "skipped_total": 0,
                                        "missing_total": 1,
                                    }
                                }
                            },
                            "service_actions": [{"kind": "record_audit_event"}],
                        },
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_payload_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_payload(
            service_execution={
                "provider": provider,
                "provider_source_name": "service_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [{"kind": "record_audit_event"}],
            },
            preflight_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload_uses_service_execution_result_model_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = record_helper
        try:
            service_execution_model, execution_result_model = (
                tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload(
                    service_execution={
                        "provider": provider,
                        "provider_source_name": "service_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 2,
                                    "skipped_total": 1,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = original_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_payload_uses_execution_models_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            preflight_result: dict[str, object],
        ) -> tuple[object, object]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_payload(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload = original_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_dict(
            preflight_result={
                "provider_source_name": "top_level_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "service_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(summary_model.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_model.missing_total, 1)
        self.assertEqual(result_model.provider_source_name, "service_source")
        self.assertEqual(result_model.summary.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_dict_uses_execution_models_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_dict
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *, preflight_result: dict[str, object]
        ) -> tuple[object, object]:
            captured.append(
                (
                    str(preflight_result["service_execution"]["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_dict = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        service_execution_model_out, execution_result_model = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1
        )

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model_uses_service_execution_result_model_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                )
            )
            return original_helper(service_execution=service_execution, preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = record_helper
        try:
            service_execution_model_out, execution_result_model = (
                tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model(
                    service_execution=service_execution_model,
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_models_uses_models_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = original_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_model_uses_execution_models_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
        )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                )
            )
            return original_helper(service_execution=service_execution, preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = record_helper
        try:
            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        (
            service_execution_model_out,
            execution_result_model,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
            service_execution=service_execution_model,
            preflight_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(summary_model.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(result_model.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_model_uses_models_from_models_helper_via_typed_path(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_models
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    getattr(execution_result, "trace_write_count"),
                    getattr(execution_result, "audit_event_count"),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_models = record_helper
        try:
            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_models = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_parts_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=service_execution_result_model.provider,
            provider_source_name=service_execution_result_model.provider_source_name,
            runtime_artifacts=service_execution_result_model.runtime_artifacts,
            service_actions=service_execution_model.service_actions,
            trace_write_count=service_execution_result_model.trace_write_count,
            audit_event_count=service_execution_result_model.audit_event_count,
        )

        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(
            result.tool_names,
            tuple(sorted(service_execution_result_model.provider.load_tool_registry())),
        )
        self.assertEqual(result.service_action_kinds, ())
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_result_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "total": 1,
                        "skipped_total": 0,
                        "missing_total": 1,
                    }
                }
            },
            "service_actions": [{"kind": "record_audit_event"}],
        }
        execution_result = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": service_execution["runtime_artifacts"],
            "trace_write_count": 1,
            "audit_event_count": 2,
        }

        result = build_configured_tool_registry_provider_preflight_result_model(
            service_execution=service_execution,
            execution_result=execution_result,
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_uses_models_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "total": 1,
                        "skipped_total": 0,
                        "missing_total": 1,
                    }
                }
            },
            "service_actions": [{"kind": "record_audit_event"}],
        }
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result_model(
                service_execution=service_execution,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        result = (
            build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model(
                service_execution=service_execution_model,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model_uses_models_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
        )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_model = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model(
                    service_execution=service_execution_model,
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_result_model_uses_service_execution_defaults(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "total": 1,
                        "skipped_total": 0,
                        "missing_total": 1,
                    }
                }
            },
            "service_actions": [{"kind": "record_audit_event"}],
        }

        result = build_configured_tool_registry_provider_preflight_result_model(
            service_execution=service_execution,
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload_fills_missing_metadata_from_execution_result(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        service_execution_model, execution_result_model = (
            build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload(
                service_execution={
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                preflight_result={
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 1,
                                "skipped_total": 0,
                                "missing_total": 1,
                            }
                        }
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(
            service_execution_model.runtime_artifacts.diagnostics_runtime.summary.missing_total,
            1,
        )
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total,
            1,
        )
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload_overlays_execution_result_runtime_artifacts(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
            service_execution={
                "provider": provider,
                "provider_source_name": "service_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": False,
                            "total": 0,
                            "skipped_total": 0,
                            "missing_total": 0,
                        }
                    }
                },
                "service_actions": [{"kind": "record_audit_event"}],
            },
            execution_result={
                "provider_source_name": "result_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertEqual(service_execution_model.provider_source_name, "service_source")
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.provider_source_name, "service_source")
        self.assertEqual(result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.missing_total, 1)
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total,
            1,
        )
        self.assertEqual(result_dict["provider_source_name"], "service_source")
        self.assertEqual(summary_dict["missing_total"], 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_preflight_result_model_from_dict(
            preflight_result={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 1,
                            "skipped_total": 0,
                            "missing_total": 1,
                        }
                    }
                },
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 1,
                                "skipped_total": 0,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_dict_uses_service_execution_defaults(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_preflight_result_model_from_dict(
            preflight_result={
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 1,
                                "skipped_total": 0,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_dict_uses_outputs_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_models_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict
        captured: list[tuple[int, int, str]] = []

        def record_models_helper(
            *, preflight_result: dict[str, object]
        ) -> tuple[object, object, object, object, dict[str, object], dict[str, object]]:
            captured.append(
                (
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                    str(preflight_result["service_execution"]["provider_source_name"]),
                )
            )
            return original_models_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = record_models_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = original_models_helper

        self.assertEqual(captured, [(1, 2, "file_source")])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_dicts_uses_result_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = record_helper
        try:
            summary_dict, result_dict = build_configured_tool_registry_provider_preflight_dicts(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = original_helper

        self.assertEqual(captured, [(1, 2)])
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(
            result_dict["summary"]["service_action_kinds"],
            ("record_audit_event",),
        )

    def test_build_configured_tool_registry_provider_preflight_result_model_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        result = build_configured_tool_registry_provider_preflight_result_model_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        self.assertIs(result.provider, service_execution_model.provider)
        self.assertEqual(
            result.runtime_artifacts.provider_source_name,
            service_execution_model.runtime_artifacts.provider_source_name,
        )
        self.assertEqual(
            result.service_execution.provider_source_name,
            service_execution_model.provider_source_name,
        )
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertEqual(result.summary.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            result.summary.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )
        self.assertEqual(result.summary.service_action_kinds, ())

    def test_build_configured_tool_registry_provider_preflight_models_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        (
            service_execution_model_out,
            execution_result_model_out,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model_out, service_execution_result_model)
        self.assertEqual(summary_model.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            summary_model.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )
        self.assertEqual(result_model.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(result_model.summary.tool_names, summary_model.tool_names)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        (
            service_execution_model_out,
            execution_result_model_out,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model_out, service_execution_result_model)
        self.assertEqual(summary_dict["provider_source_name"], summary_model.provider_source_name)
        self.assertEqual(summary_dict["tool_names"], summary_model.tool_names)
        self.assertIs(result_dict["provider"], result_model.provider)
        self.assertEqual(result_dict["summary"]["tool_names"], result_model.summary.tool_names)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
            service_execution={
                "provider": provider,
                "provider_source_name": "service_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [{"kind": "record_audit_event"}],
            },
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_uses_outputs_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload
        )
        captured: list[tuple[int, int, str]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            execution_result: dict[str, object],
        ) -> tuple[object, object, object, object, object, object]:
            captured.append(
                (
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                    str(service_execution["provider_source_name"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload = original_helper

        self.assertEqual(captured, [(1, 2, "service_source")])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model
        original_dict_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object, object, object]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = record_helper
        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = (
            lambda **kwargs: (_ for _ in ()).throw(
                AssertionError("outputs_from_service_execution_payload should not call outputs_from_dict")
            )
        )
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = original_helper
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = original_dict_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )

        (
            service_execution_model_out,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
            service_execution=service_execution_model,
            preflight_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_uses_execution_models_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
        )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(service_execution=service_execution, preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = record_helper
        try:
            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_dict(
            preflight_result={
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_dict_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object, dict[str, object], dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs_from_dict(
                preflight_result={
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 1,
                                    "skipped_total": 0,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_models_uses_result_model_from_models_helper(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_models
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> object:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    getattr(execution_result, "trace_write_count"),
                    getattr(execution_result, "audit_event_count"),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_models = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary_model_from_models(
                service_execution=service_execution_model,
                execution_result=service_execution_result_model,
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_models = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertEqual(result.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            result.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_result_model_returns_existing_summary(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )
        preflight_result_model = build_configured_tool_registry_provider_preflight_result_model_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_result_model(
            preflight_result=preflight_result_model,
        )

        self.assertIs(result, preflight_result_model.summary)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_models_uses_outputs_from_models_helper(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_models
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, object, object, object, dict[str, object], dict[str, object]]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    getattr(execution_result, "trace_write_count"),
                    getattr(execution_result, "audit_event_count"),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_models = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result_model_from_models(
                service_execution=service_execution_model,
                execution_result=service_execution_result_model,
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_models = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertEqual(result.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            result.summary.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )

    def test_execute_configured_tool_registry_provider_preflight_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = execute_configured_tool_registry_provider_preflight_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(result.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=settings,
            )

            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = tool_runtime_module.execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
                service_execution=service_execution_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval_fast",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_uses_models_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=settings,
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        tuple(sorted(getattr(service_execution, "provider").load_tool_registry())),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = record_helper
            try:
                (
                    service_execution_model_out,
                    execution_result_model,
                    summary_model,
                    result_model,
                    summary_dict,
                    result_dict,
                ) = tool_runtime_module.execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("calc_eval_fast",))])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval_fast",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_models_from_service_execution_model_uses_service_execution_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=settings,
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, dict[str, object]]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        tuple(sorted(getattr(service_execution, "provider").load_tool_registry())),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
            try:
                (
                    service_execution_model_out,
                    execution_result_model,
                    summary_model,
                    result_model,
                ) = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("calc_eval_fast",))])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_outputs_uses_models_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        task_id,
                        (step_id, str(seq), model),
                    )
                )
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = record_helper
            try:
                (
                    service_execution_model,
                    execution_result_model,
                    summary_model,
                    result_model,
                    summary_dict,
                    result_dict,
                ) = execute_configured_tool_registry_provider_preflight_outputs(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = original_helper

        self.assertEqual(captured, [("task-1", ("step-registry", "2", "mock-gpt"))])
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval_fast",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_models_uses_models_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        tuple(sorted(getattr(service_execution, "provider").load_tool_registry())),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = record_helper
            try:
                (
                    service_execution_model,
                    execution_result_model,
                    summary_model,
                    result_model,
                ) = execute_configured_tool_registry_provider_preflight_models(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("calc_eval_fast",))])
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_summary_model_uses_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_model
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append(
                    (
                        task_id,
                        tuple(),
                    )
                )
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight_summary_model(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = original_helper

        self.assertEqual(captured, [("task-1", ())])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.tool_names, ("calc_eval_fast",))
        self.assertEqual(result.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_summary_uses_summary_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_summary_model
            captured: list[tuple[str, int, str]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append((task_id, seq, model))
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_summary_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight_summary(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_summary_model = original_helper

        self.assertEqual(captured, [("task-1", 2, "mock-gpt")])
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(result["tool_names"], ("calc_eval_fast",))
        self.assertEqual(
            result["service_action_kinds"],
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_model_uses_models_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        task_id,
                        tuple(),
                    )
                )
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight_model(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = original_helper

        self.assertEqual(captured, [("task-1", ())])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_uses_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_model
            captured: list[tuple[str, int, str]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append((task_id, seq, model))
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = original_helper

        self.assertEqual(captured, [("task-1", 2, "mock-gpt")])
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(
            tuple(sorted(result["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            result["summary"]["service_action_kinds"],
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_dicts_uses_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_model
            captured: list[tuple[str, int, str]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append((task_id, seq, model))
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = record_helper
            try:
                summary_dict, result_dict = (
                    execute_configured_tool_registry_provider_preflight_dicts(
                        settings=settings,
                        task_id="task-1",
                        step_id="step-registry",
                        seq=2,
                        model="mock-gpt",
                        trace_steps=trace_steps,
                        persist_trace_fn=lambda **kwargs: persisted.append(
                            bool(kwargs["force"])
                        ),
                        record_audit_event_fn=lambda **kwargs: audit_calls.append(
                            kwargs
                        ),
                    )
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = original_helper

        self.assertEqual(captured, [("task-1", 2, "mock-gpt")])
        self.assertEqual(summary_dict["provider_source_name"], "file_source")
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(
            result_dict["summary"]["service_action_kinds"],
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_build_tool_registry_providers_from_settings_supports_provider_factory_shape(self) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "provider_factory": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(
            providers["planning_provider"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_providers_from_settings_reuses_shared_profile_name_helper_for_factory_hint(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "provider_factory": "custom_factory",
                    }
                }
            )
        )
        original_get_tool_registry_profile_name_from_settings = (
            tool_runtime_module.get_tool_registry_profile_name_from_settings
        )
        original_build_tool_registry_provider_factories_from_settings = (
            tool_runtime_module.build_tool_registry_provider_factories_from_settings
        )
        captured: list[object] = []
        try:
            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "calculator_only"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            def fake_build_tool_registry_provider_factories_from_settings(*, settings=None):
                def factory(_settings=None):
                    return tool_runtime_module.get_default_tool_registry_provider()

                setattr(factory, "_tool_registry_profile_name", " Planning_Only ")
                return {"custom_factory": factory}

            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            tool_runtime_module.build_tool_registry_provider_factories_from_settings = (
                fake_build_tool_registry_provider_factories_from_settings
            )
            providers = build_tool_registry_providers_from_settings(settings=settings)
        finally:
            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )
            tool_runtime_module.build_tool_registry_provider_factories_from_settings = (
                original_build_tool_registry_provider_factories_from_settings
            )

        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval",),
        )

    def test_build_tool_registry_loaders_from_settings_accepts_named_loader_factory_reference(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loader_factories_json=json.dumps(
                {
                    "planning_factory": {
                        "factory": "planning_only",
                    }
                }
            ),
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader_factory": "planning_factory",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        loaders = build_tool_registry_loaders_from_settings(settings=settings)
        planning_registry = loaders["planning_loader"]()

        self.assertEqual(tuple(sorted(planning_registry)), ("calc_eval", "calc_eval_fast", "task_plan"))
        self.assertEqual(planning_registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loaders_from_settings_reuse_shared_reference_normalizer_for_loader_factory_reference(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loader_factories_json=json.dumps(
                {
                    "planning_factory_shadow": {
                        "factory": "planning_only",
                    }
                }
            ),
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader_factory": " Planning_Factory ",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
        )
        original_normalize_named_tool_registry_component_name = getattr(
            tool_runtime_module,
            "_normalize_named_tool_registry_component_name",
        )
        captured: list[object] = []
        try:
            def fake_normalize_named_tool_registry_component_name(
                name: object | None,
            ) -> str | None:
                captured.append(name)
                if name == " Planning_Factory ":
                    return "planning_factory_shadow"
                if not isinstance(name, str):
                    return None
                normalized = name.strip().lower()
                return normalized or None

            tool_runtime_module._normalize_named_tool_registry_component_name = (
                fake_normalize_named_tool_registry_component_name
            )
            loaders = build_tool_registry_loaders_from_settings(settings=settings)
            planning_registry = loaders["planning_loader"]()
        finally:
            tool_runtime_module._normalize_named_tool_registry_component_name = (
                original_normalize_named_tool_registry_component_name
            )

        self.assertIn(" Planning_Factory ", captured)
        self.assertEqual(tuple(sorted(loaders)), ("planning_loader",))
        self.assertEqual(
            tuple(sorted(planning_registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(planning_registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_providers_from_settings_accepts_named_provider_factory_reference(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_factories_json=json.dumps(
                {
                    "planning_factory": {
                        "factory": "planning_only",
                    }
                }
            ),
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "provider_factory": "planning_factory",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )

    def test_build_tool_registry_providers_from_settings_reuse_shared_reference_normalizer_for_named_loader_reference(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader_shadow": {
                        "loader": "default",
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "loader": " Planning_Loader ",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
        )
        original_normalize_named_tool_registry_component_name = getattr(
            tool_runtime_module,
            "_normalize_named_tool_registry_component_name",
        )
        captured: list[object] = []
        try:
            def fake_normalize_named_tool_registry_component_name(
                name: object | None,
            ) -> str | None:
                captured.append(name)
                if name == " Planning_Loader ":
                    return "planning_loader_shadow"
                if not isinstance(name, str):
                    return None
                normalized = name.strip().lower()
                return normalized or None

            tool_runtime_module._normalize_named_tool_registry_component_name = (
                fake_normalize_named_tool_registry_component_name
            )
            providers = build_tool_registry_providers_from_settings(settings=settings)
        finally:
            tool_runtime_module._normalize_named_tool_registry_component_name = (
                original_normalize_named_tool_registry_component_name
            )

        self.assertIn(" Planning_Loader ", captured)
        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            providers["planning_provider"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_loaders_from_settings_accepts_registry_file_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "registry_file": str(registry_file),
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                )
            )

            loaders = build_tool_registry_loaders_from_settings(settings=settings)
            file_registry = loaders["file_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("file_loader",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval_fast", "mock_plan_brief"),
        )

    def test_build_tool_registry_providers_from_settings_accepts_registry_file_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "registry_file": str(registry_file),
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                )
            )

            providers = build_tool_registry_providers_from_settings(settings=settings)
            file_registry = providers["file_provider"].load_tool_registry()

        self.assertEqual(tuple(sorted(providers)), ("file_provider",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval_fast", "mock_plan_brief"),
        )

    def test_build_tool_registry_loaders_from_settings_accepts_registry_file_manifest_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry-manifest.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "registry_file": str(registry_file),
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                )
            )

            loaders = build_tool_registry_loaders_from_settings(settings=settings)
            file_registry = loaders["file_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("file_loader",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval", "calc_eval_fast", "mock_plan_brief", "task_plan"),
        )
        self.assertEqual(file_registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loaders_from_settings_reuse_shared_profile_name_helper_for_registry_manifest(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry-manifest.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "profile": " Planning_Only ",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "registry_file": str(registry_file),
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                )
            )
            original_get_tool_registry_profile_name_from_settings = (
                tool_runtime_module.get_tool_registry_profile_name_from_settings
            )
            captured: list[object] = []
            try:
                def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                    captured.append(getattr(settings, "tool_registry_profile", None))
                    if (
                        getattr(settings, "tool_registry_profile", None)
                        == " Planning_Only "
                    ):
                        return "calculator_only"
                    return original_get_tool_registry_profile_name_from_settings(
                        settings=settings
                    )

                tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                    fake_get_tool_registry_profile_name_from_settings
                )
                loaders = build_tool_registry_loaders_from_settings(settings=settings)
                file_registry = loaders["file_loader"]()
            finally:
                tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                    original_get_tool_registry_profile_name_from_settings
                )

        self.assertEqual(tuple(sorted(loaders)), ("file_loader",))
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval", "calc_eval_fast", "mock_plan_brief"),
        )

    def test_build_tool_registry_providers_from_settings_accepts_registry_file_manifest_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry-manifest.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "profile": "retrieval_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Retrieval Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "registry_file": str(registry_file),
                            "disabled_tool_names": ["mock_retrieve"],
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                )
            )

            providers = build_tool_registry_providers_from_settings(settings=settings)
            file_registry = providers["file_provider"].load_tool_registry()

        self.assertEqual(tuple(sorted(providers)), ("file_provider",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval", "calc_eval_fast", "mock_plan_brief"),
        )
        self.assertEqual(file_registry["calc_eval"].label, "Retrieval Calculator")

    def test_build_tool_registry_loaders_from_settings_accepts_named_loader_factory_backed_by_registry_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(registry_file),
                        }
                    }
                ),
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "loader_factory": "file_factory",
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                ),
            )

            loaders = build_tool_registry_loaders_from_settings(settings=settings)
            file_registry = loaders["file_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("file_loader",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval_fast", "mock_plan_brief"),
        )

    def test_build_tool_registry_providers_from_settings_accepts_named_provider_factory_backed_by_registry_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(registry_file),
                        }
                    }
                ),
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "provider_factory": "file_factory",
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                ),
            )

            providers = build_tool_registry_providers_from_settings(settings=settings)
            file_registry = providers["file_provider"].load_tool_registry()

        self.assertEqual(tuple(sorted(providers)), ("file_provider",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval_fast", "mock_plan_brief"),
        )

    def test_build_tool_registry_providers_from_settings_accepts_named_loader_reference(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader": "default",
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "loader": "planning_loader",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            providers["planning_provider"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_providers_from_settings_accepts_named_loader_built_from_loader_factory(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader_factory": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "loader": "planning_loader",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            providers["planning_provider"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_accepts_named_provider_reference(self) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "loader": "default",
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "provider": "planning_provider",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(sources)), ("planning_suite",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            sources["planning_suite"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_accepts_provider_factory_reference(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "provider_factory": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(sources)), ("planning_suite",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite"]),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(
            sources["planning_suite"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_accepts_named_loader_reference(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader": "default",
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "loader": "planning_loader",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(sources)), ("planning_suite",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            sources["planning_suite"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_accepts_named_loader_built_from_loader_factory(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader_factory": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "loader": "planning_loader",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(sources)), ("planning_suite",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            sources["planning_suite"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_reuses_shared_profile_name_helper(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "profile": " Planning_Only ",
                    }
                }
            )
        )
        original_get_tool_registry_profile_name_from_settings = (
            tool_runtime_module.get_tool_registry_profile_name_from_settings
        )
        captured: list[object] = []
        try:
            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "calculator_only"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            sources = build_tool_registry_provider_sources_from_settings(settings=settings)
        finally:
            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )

        self.assertEqual(tuple(sorted(sources)), ("planning_suite",))
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite"]),
            ("calc_eval",),
        )

    def test_build_tool_registry_provider_sources_from_settings_reuses_shared_provider_source_name_helper(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    " Planning_Suite ": {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                }
            )
        )
        original_get_tool_registry_provider_source_name_from_settings = (
            tool_runtime_module.get_tool_registry_provider_source_name_from_settings
        )
        captured: list[object] = []
        try:
            def fake_get_tool_registry_provider_source_name_from_settings(
                *,
                settings=None,
            ):
                captured.append(getattr(settings, "tool_registry_provider_source", None))
                if (
                    getattr(settings, "tool_registry_provider_source", None)
                    == " Planning_Suite "
                ):
                    return "planning_suite_shadow"
                return original_get_tool_registry_provider_source_name_from_settings(
                    settings=settings
                )

            tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                fake_get_tool_registry_provider_source_name_from_settings
            )
            sources = build_tool_registry_provider_sources_from_settings(settings=settings)
        finally:
            tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                original_get_tool_registry_provider_source_name_from_settings
            )

        self.assertIn(" Planning_Suite ", captured)
        self.assertEqual(tuple(sorted(sources)), ("planning_suite_shadow",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite_shadow"]),
            ("calc_eval_fast",),
        )

    def test_build_tool_registry_providers_from_settings_ignores_unknown_loader_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "broken_provider": {
                        "loader": "missing_loader",
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                            }
                        },
                    }
                }
            )
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(providers, {})

    def test_build_tool_registry_loaders_from_settings_ignores_unknown_loader_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "broken_loader": {
                        "loader": "missing_loader",
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                            }
                        },
                    }
                }
            )
        )

        loaders = build_tool_registry_loaders_from_settings(settings=settings)

        self.assertEqual(loaders, {})

    def test_build_tool_registry_loaders_from_settings_ignores_unknown_loader_factory_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "broken_loader": {
                        "loader_factory": "missing_factory",
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                            }
                        },
                    }
                }
            )
        )

        loaders = build_tool_registry_loaders_from_settings(settings=settings)

        self.assertEqual(loaders, {})

    def test_build_tool_registry_loader_factories_from_settings_ignores_unknown_factory_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loader_factories_json=json.dumps(
                {
                    "broken_factory": {
                        "factory": "missing_factory",
                    }
                }
            )
        )

        factories = build_tool_registry_loader_factories_from_settings(settings=settings)

        self.assertEqual(factories, {})

    def test_build_tool_registry_provider_factories_from_settings_ignores_unknown_factory_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_factories_json=json.dumps(
                {
                    "broken_factory": {
                        "factory": "missing_factory",
                    }
                }
            )
        )

        factories = build_tool_registry_provider_factories_from_settings(settings=settings)

        self.assertEqual(factories, {})

    def test_build_tool_registry_providers_from_settings_ignores_unknown_provider_factory_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "broken_provider": {
                        "provider_factory": "missing_factory",
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                            }
                        },
                    }
                }
            )
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(providers, {})

    def test_build_tool_registry_overrides_from_settings_ignores_unknown_tools_and_bad_shapes(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "unknown_tool": {"label": "Ignored"},
                    "calc_eval": "bad-shape",
                }
            )
        )

        overrides = build_tool_registry_overrides_from_settings(settings=settings)

        self.assertEqual(overrides, {})

    def test_build_tool_registry_settings_config_ignores_unknown_disabled_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "unknown_tool": {"enabled": False},
                    "calc_eval": "bad-shape",
                }
            )
        )

        config = build_tool_registry_settings_config(settings=settings)

        self.assertEqual(config.overrides, {})
        self.assertEqual(config.disabled_tool_names, ())

    def test_get_configured_tool_registry_provider_applies_settings_overrides(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "label": "Configured Calculator",
                        "default_timeout_ms": 8_888,
                        "requires_user_context": False,
                    }
                }
            )
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertIsInstance(provider, ConfiguredToolRegistryProvider)
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        self.assertEqual(runtime_ctx.registration.label, "Configured Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 8_888)
        self.assertEqual(runtime_ctx.user_id, "")

    def test_get_configured_tool_registry_provider_uses_selected_provider_source(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="analytics_suite",
            tool_registry_provider_sources_json=json.dumps(
                {
                    "analytics_suite": {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                            "default_timeout_ms": 1_500,
                        }
                    }
                }
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=None,
            tool_registry_extra_tools_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval_fast",),
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval_fast",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        self.assertEqual(runtime_ctx.registration.label, "Fast Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 1_500)

    def test_get_configured_tool_registry_provider_stacks_global_settings_on_selected_source(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="planning_suite",
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "provider": "default",
                        "profile": "planning_only",
                        "disabled_tool_names": ["mock_plan"],
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "default_timeout_ms": 1_200,
                    }
                }
            ),
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "template": "calc_eval",
                        "label": "Global Fast Calculator",
                    }
                }
            ),
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "calc_eval_fast"),
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        self.assertEqual(runtime_ctx.registration.label, "Planning Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 1_200)

    def test_get_configured_tool_registry_provider_uses_selected_source_backed_by_named_provider(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="planning_suite",
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "loader": "default",
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "provider": "planning_provider",
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "default_timeout_ms": 1_200,
                    }
                }
            ),
            tool_registry_extra_tools_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )

        self.assertEqual(runtime_ctx.registration.label, "Planning Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 1_200)
        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )

    def test_get_configured_tool_registry_provider_uses_selected_source_backed_by_provider_factory(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="planning_suite",
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "provider_factory": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "default_timeout_ms": 1_200,
                    }
                }
            ),
            tool_registry_extra_tools_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )

        self.assertEqual(runtime_ctx.registration.label, "Planning Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 1_200)
        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )

    def test_get_configured_tool_registry_provider_includes_extra_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_profile="default",
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "requires_user_context": False,
                    }
                }
            ),
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "template": "calc_eval",
                        "label": "Fast Calculator",
                        "default_timeout_ms": 1_500,
                    }
                }
            ),
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "calc_eval_fast", "task_plan", "task_retrieve"),
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval_fast",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        self.assertEqual(runtime_ctx.registration.label, "Fast Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 1_500)
        self.assertEqual(runtime_ctx.user_id, "")

    def test_get_configured_tool_registry_provider_applies_profile_disabled_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_profile="planning_only",
            tool_registry_overrides_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("task_plan",),
        )

    def test_get_configured_tool_registry_provider_filters_disabled_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "mock_retrieve": {"enabled": False},
                }
            )
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertIsInstance(provider, ConfiguredToolRegistryProvider)
        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "task_plan"),
        )
        with self.assertRaises(MockToolExecutionError) as ctx:
            ensure_tool_registration(
                "mock_retrieve",
                registry_provider=provider,
            )
        self.assertEqual(str(ctx.exception), "Unknown tool: mock_retrieve")

    def test_get_tool_registry_profile_name_from_settings_defaults_to_default(self) -> None:
        settings = SimpleNamespace(tool_registry_profile=None)

        self.assertEqual(
            get_tool_registry_profile_name_from_settings(settings=settings),
            "default",
        )

    def test_get_tool_registry_provider_source_name_from_settings_defaults_to_default(self) -> None:
        settings = SimpleNamespace(tool_registry_provider_source=None)

        self.assertEqual(
            get_tool_registry_provider_source_name_from_settings(settings=settings),
            "default",
        )

    def test_tool_registry_profile_and_source_helpers_reuse_shared_reference_normalizer(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_profile=" Planning_Only ",
            tool_registry_provider_source=" Planning_Suite ",
        )
        original_normalize_named_tool_registry_component_name = getattr(
            tool_runtime_module,
            "_normalize_named_tool_registry_component_name",
        )
        captured: list[object] = []
        try:
            def fake_normalize_named_tool_registry_component_name(
                name: object | None,
            ) -> str | None:
                captured.append(name)
                if name == " Planning_Only ":
                    return "calculator_only"
                if name == " Planning_Suite ":
                    return "planning_suite_shadow"
                if not isinstance(name, str):
                    return None
                normalized = name.strip().lower()
                return normalized or None

            tool_runtime_module._normalize_named_tool_registry_component_name = (
                fake_normalize_named_tool_registry_component_name
            )
            profile_name = get_tool_registry_profile_name_from_settings(settings=settings)
            provider_source_name = get_tool_registry_provider_source_name_from_settings(
                settings=settings
            )
        finally:
            tool_runtime_module._normalize_named_tool_registry_component_name = (
                original_normalize_named_tool_registry_component_name
            )

        self.assertIn(" Planning_Only ", captured)
        self.assertIn(" Planning_Suite ", captured)
        self.assertEqual(profile_name, "calculator_only")
        self.assertEqual(provider_source_name, "planning_suite_shadow")

    def test_load_tool_registry_returns_isolated_default_snapshot(self) -> None:
        registry = load_tool_registry()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_plan", "task_retrieve"),
        )
        registry.pop("task_plan")
        self.assertEqual(
            get_registered_tool_names(),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_load_tool_registry_applies_overrides_on_fresh_snapshot(self) -> None:
        registry = load_tool_registry(
            overrides={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="custom_calc",
                    label="Custom Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=9_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                ),
                "custom_lookup": ToolRegistration(
                    name="custom_lookup",
                    kind="custom_lookup",
                    label="Custom Lookup",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=False,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                ),
            }
        )

        self.assertEqual(
            get_registered_tool_names(registry=registry),
            ("calc_eval", "custom_lookup", "task_plan", "task_retrieve"),
        )
        self.assertEqual(
            resolve_tool_registration("calc_eval", registry=registry).kind,
            "custom_calc",
        )
        self.assertIsNotNone(resolve_tool_registration("custom_lookup", registry=registry))
        self.assertEqual(
            get_registered_tool_names(),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_load_tool_registry_accepts_custom_loader_then_applies_overrides(self) -> None:
        def custom_loader() -> dict[str, ToolRegistration]:
            return {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            }

        registry = load_tool_registry(
            loader=custom_loader,
            overrides={
                "custom_lookup": ToolRegistration(
                    name="custom_lookup",
                    kind="custom_lookup",
                    label="Custom Lookup",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=False,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            },
        )

        self.assertEqual(
            get_registered_tool_names(registry=registry),
            ("calc_eval", "custom_lookup"),
        )
        self.assertEqual(
            resolve_tool_registration("calc_eval", registry=registry).kind,
            "loader_calc",
        )

    def test_load_tool_registry_accepts_provider_then_applies_overrides(self) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="provider_calc",
                    label="Provider Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=13_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            }
        )

        registry = load_tool_registry(
            provider=provider,
            overrides={
                "custom_lookup": ToolRegistration(
                    name="custom_lookup",
                    kind="custom_lookup",
                    label="Custom Lookup",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=False,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            },
        )

        self.assertEqual(
            get_registered_tool_names(registry=registry),
            ("calc_eval", "custom_lookup"),
        )
        self.assertEqual(
            resolve_tool_registration("calc_eval", registry=registry).kind,
            "provider_calc",
        )

    def test_load_tool_registry_uses_default_provider_when_no_source_is_given(self) -> None:
        original = tool_runtime_module.get_default_tool_registry_provider

        def fake_default_provider() -> StaticToolRegistryProvider:
            return StaticToolRegistryProvider(
                registry={
                    "custom_only": ToolRegistration(
                        name="custom_only",
                        kind="custom_only",
                        label="Custom Only",
                        retryable_by_default=False,
                        default_timeout_ms=7_000,
                        requires_user_context=False,
                        supports_result_preview=False,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "tool_input": tool_input,
                            "prompt": prompt,
                            "user_id": user_id,
                        },
                    )
                }
            )

        tool_runtime_module.get_default_tool_registry_provider = fake_default_provider
        try:
            registry = load_tool_registry()
        finally:
            tool_runtime_module.get_default_tool_registry_provider = original

        self.assertEqual(tuple(sorted(registry)), ("custom_only",))

    def test_execute_tool_plan_item_service_execution_accepts_built_registry_provider(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "provider-ok",
                "tool_kind": "provider_calc",
            }

        provider = build_tool_registry_provider(
            provider=StaticToolRegistryProvider(
                registry={
                    "calc_eval": ToolRegistration(
                        name="calc_eval",
                        kind="provider_calc",
                        label="Provider Calculator",
                        retryable_by_default=False,
                        default_timeout_ms=13_000,
                        requires_user_context=False,
                        supports_result_preview=True,
                        runner=custom_runner,
                    )
                }
            )
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry_provider=provider,
            )
        )

        self.assertEqual(runner_calls, [({"expression": "1+2*3"}, "calc", "")])
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"]["tool_kind"],
            "provider_calc",
        )

    def test_build_tool_registry_merges_overrides_without_mutating_default(self) -> None:
        custom_registry = build_tool_registry(
            overrides={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="custom_calc",
                    label="Custom Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=9_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                ),
                "custom_lookup": ToolRegistration(
                    name="custom_lookup",
                    kind="custom_lookup",
                    label="Custom Lookup",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=False,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                ),
            }
        )

        self.assertEqual(
            get_registered_tool_names(registry=custom_registry),
            ("calc_eval", "custom_lookup", "task_plan", "task_retrieve"),
        )
        self.assertEqual(
            resolve_tool_registration("calc_eval", registry=custom_registry).kind,
            "custom_calc",
        )
        self.assertIsNotNone(resolve_tool_registration("custom_lookup", registry=custom_registry))
        self.assertEqual(
            get_registered_tool_names(),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_normalize_tool_spec_coerces_name_and_defaults_input(self) -> None:
        invocation = normalize_tool_spec(
            {
                "name": 123,
                "input": "not-a-dict",
            }
        )

        self.assertEqual(invocation.name, "123")
        self.assertEqual(invocation.tool_input, {})

    def test_resolve_tool_registration_exposes_explicit_calc_entry(self) -> None:
        registration = resolve_tool_registration("calc_eval")

        self.assertIsNotNone(registration)
        assert registration is not None
        self.assertEqual(registration.name, "calc_eval")
        self.assertEqual(registration.kind, "local_calculator")
        self.assertEqual(registration.label, "Calculator")
        self.assertTrue(registration.retryable_by_default)
        self.assertEqual(registration.default_timeout_ms, 3_000)
        self.assertTrue(registration.requires_user_context)
        self.assertTrue(registration.supports_result_preview)

    def test_build_tool_result_preview_keeps_current_calc_shape(self) -> None:
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        self.assertEqual(
            build_tool_result_preview(name="calc_eval", output=output),
            output,
        )

    def test_tool_runtime_helpers_expose_current_calc_defaults(self) -> None:
        self.assertTrue(tool_requires_user_context("calc_eval"))
        self.assertTrue(is_tool_retryable_by_default("calc_eval"))
        self.assertEqual(get_tool_default_timeout_ms("calc_eval"), 3_000)

    def test_ensure_tool_registration_keeps_unknown_tool_fatal(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            ensure_tool_registration("does_not_exist")

        self.assertTrue(ctx.exception.fatal)
        self.assertIn("unknown tool", str(ctx.exception).lower())

    def test_maybe_raise_tool_execution_error_keeps_transient_semantics(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            maybe_raise_tool_execution_error(
                name="mock_plan",
                prompt="[tool-error]",
                attempt=0,
            )

        self.assertFalse(ctx.exception.fatal)
        self.assertIn("transient error", str(ctx.exception).lower())

    def test_maybe_raise_mock_tool_execution_error_keeps_legacy_marker_compatibility(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            maybe_raise_mock_tool_execution_error(
                name="mock_plan",
                prompt="[mock-tool-error]",
                attempt=0,
            )

        self.assertFalse(ctx.exception.fatal)
        self.assertIn("transient error", str(ctx.exception).lower())

    def test_build_tool_runtime_context_keeps_calc_defaults(self) -> None:
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(ctx.name, "calc_eval")
        self.assertEqual(ctx.user_id, "user-1")
        self.assertEqual(ctx.attempt, 0)
        self.assertEqual(ctx.default_timeout_ms, 3_000)
        self.assertTrue(ctx.retryable_by_default)
        self.assertTrue(ctx.requires_user_context)

    def test_build_tool_runtime_context_accepts_custom_registry_metadata(self) -> None:
        registry = {
            "calc_eval": ToolRegistration(
                name="calc_eval",
                kind="custom_calc",
                label="Custom Calculator",
                retryable_by_default=False,
                default_timeout_ms=9_000,
                requires_user_context=False,
                supports_result_preview=False,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_input": tool_input,
                    "prompt": prompt,
                    "user_id": user_id,
                },
            )
        }

        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="custom-calc",
            user_id="user-1",
            attempt=2,
            registry=registry,
        )

        self.assertEqual(ctx.name, "calc_eval")
        self.assertEqual(ctx.user_id, "")
        self.assertEqual(ctx.attempt, 2)
        self.assertEqual(ctx.default_timeout_ms, 9_000)
        self.assertFalse(ctx.retryable_by_default)
        self.assertFalse(ctx.requires_user_context)
        self.assertEqual(ctx.registration.kind, "custom_calc")

    def test_compute_tool_retry_decision_keeps_current_calc_defaults(self) -> None:
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertTrue(
            compute_tool_retry_decision(
                ctx=ctx,
                exc=MockToolExecutionError("transient", fatal=False),
            )
        )
        self.assertFalse(
            compute_tool_retry_decision(
                ctx=ctx,
                exc=MockToolExecutionError("fatal", fatal=True),
            )
        )

    def test_build_tool_end_payload_keeps_preview_and_retry_shape(self) -> None:
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        self.assertEqual(
            build_tool_end_payload(
                name="calc_eval",
                task_id="task-1",
                step_id="step-1",
                output=output,
                retry_count=0,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "done",
                "latency_ms": 12,
                "output_preview": output,
                "retry_count": 0,
            },
        )

    def test_build_tool_success_and_error_meta_keep_tool_shape(self) -> None:
        tool_input = {"expression": "1+2*3"}
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        success_meta = build_tool_success_meta(
            name="calc_eval",
            tool_input=tool_input,
            output=output,
            retry_count=0,
            last_error=None,
        )
        error_meta = build_tool_error_meta(
            name="calc_eval",
            tool_input=tool_input,
            retry_count=1,
            error_message="transient",
        )

        self.assertEqual(success_meta["tool"]["name"], "calc_eval")
        self.assertEqual(success_meta["tool"]["output"], output)
        self.assertEqual(success_meta["tool"]["status"], "done")
        self.assertEqual(error_meta["tool"]["name"], "calc_eval")
        self.assertEqual(error_meta["tool"]["status"], "error")
        self.assertEqual(error_meta["tool"]["error"], "transient")

    def test_build_tool_start_and_error_payload_keep_current_shape(self) -> None:
        self.assertEqual(
            build_tool_start_payload(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                retry_count=0,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "name": "calc_eval",
                "display_name": "calc_eval",
                "input": {"expression": "1+2*3"},
                "retry_count": 0,
            },
        )
        self.assertEqual(
            build_tool_error_payload(
                task_id="task-1",
                step_id="step-1",
                error_message="transient",
                retry_count=1,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "error",
                "latency_ms": 12,
                "output_preview": {"error": "transient"},
                "retry_count": 1,
                "error": "transient",
            },
        )

    def test_build_tool_phase_and_policy_keep_current_calc_defaults(self) -> None:
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        policy = build_tool_execution_policy(ctx)

        self.assertEqual(build_tool_phase(0), "tool_running")
        self.assertEqual(build_tool_phase(1), "tool_retry")
        self.assertEqual(policy["max_retry"], 1)
        self.assertEqual(policy["latency_ms"], 12)
        self.assertEqual(policy["effective_user_id"], "user-1")

    def test_build_action_step_initial_meta_and_step_keep_current_shape(self) -> None:
        meta = build_action_step_initial_meta(
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            meta=meta,
        )

        self.assertEqual(meta["tool"]["name"], "calc_eval")
        self.assertEqual(meta["tool"]["label"], "calc_eval")
        self.assertEqual(meta["tool"]["status"], "running")
        self.assertEqual(step["id"], "step-1")
        self.assertEqual(step["seq"], 3)
        self.assertEqual(step["content"], "Tool running: calc_eval")

    def test_build_action_step_initial_meta_and_step_use_display_label_for_mock_plan(
        self,
    ) -> None:
        meta = build_action_step_initial_meta(
            name="mock_plan",
            tool_input={"prompt_preview": "请帮我规划"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="mock_plan",
            meta=meta,
        )

        self.assertEqual(meta["tool"]["name"], "task_plan")
        self.assertEqual(meta["tool"]["label"], "Task Planner")
        self.assertEqual(step["content"], "Tool running: Task Planner")

    def test_build_action_step_initial_meta_and_step_use_display_label_for_task_retrieve(
        self,
    ) -> None:
        meta = build_action_step_initial_meta(
            name="task_retrieve",
            tool_input={"query": "检索 demo"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
        )
        step = build_action_step_initial_step(
            step_id="step-2",
            seq=4,
            name="task_retrieve",
            meta=meta,
        )

        self.assertEqual(meta["tool"]["name"], "task_retrieve")
        self.assertEqual(meta["tool"]["label"], "Knowledge Retrieval")
        self.assertEqual(step["content"], "Tool running: Knowledge Retrieval")

    def test_build_tool_attempt_start_and_success_events_keep_shape(self) -> None:
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }
        self.assertEqual(
            build_tool_attempt_start_events(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                attempt=0,
            ),
            {
                "tool_start": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "name": "calc_eval",
                    "display_name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "retry_count": 0,
                },
                "state": {
                    "task_id": "task-1",
                    "phase": "tool_running",
                },
            },
        )
        self.assertEqual(
            build_tool_attempt_success_events(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                output=output,
                retry_count=0,
            ),
            {
                "tool_end": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "status": "done",
                    "latency_ms": 12,
                    "output_preview": output,
                    "retry_count": 0,
                }
            },
        )

    def test_build_tool_attempt_error_events_keep_shape(self) -> None:
        self.assertEqual(
            build_tool_attempt_error_events(
                task_id="task-1",
                step_id="step-1",
                error_message="transient",
                retry_count=1,
            ),
            {
                "tool_end": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "status": "error",
                    "latency_ms": 12,
                    "output_preview": {"error": "transient"},
                    "retry_count": 1,
                    "error": "transient",
                }
            },
        )

    def test_build_tool_attempt_bundle_keeps_runtime_and_start_shapes(self) -> None:
        bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        self.assertEqual(bundle["start_events"]["tool_start"]["retry_count"], 1)
        self.assertEqual(bundle["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(bundle["runtime_ctx"].attempt, 1)
        self.assertEqual(bundle["runtime_policy"]["effective_user_id"], "user-1")

    def test_build_tool_attempt_execution_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        result = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["start_events"]["state"]["phase"], "tool_running")
        self.assertEqual(result["tool_end_event"]["status"], "done")
        self.assertFalse(bool(result["retryable"]))
        self.assertIsNotNone(result["success_effects"])
        self.assertIsNone(result["terminal_effects"])

    def test_build_tool_attempt_execution_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        result = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(result["tool_end_event"]["status"], "error")
        self.assertFalse(bool(result["retryable"]))
        self.assertIsNone(result["success_effects"])
        self.assertIsNotNone(result["terminal_effects"])

    def test_build_tool_attempt_loop_result_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        self.assertEqual(loop_result["tool_end_event"]["status"], "done")
        self.assertFalse(bool(loop_result["retryable"]))
        self.assertIsNotNone(loop_result["success_effects"])
        self.assertIsNone(loop_result["terminal_effects"])

    def test_build_tool_attempt_loop_result_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        self.assertEqual(loop_result["tool_end_event"]["status"], "error")
        self.assertFalse(bool(loop_result["retryable"]))
        self.assertIsNone(loop_result["success_effects"])
        self.assertIsNotNone(loop_result["terminal_effects"])

    def test_build_tool_attempt_loop_terminal_result_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )
        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        terminal = build_tool_attempt_loop_terminal_result(
            loop_result=loop_result,
        )

        self.assertFalse(bool(terminal["should_return"]))
        self.assertIsNone(terminal["terminal_effects"])

    def test_build_tool_attempt_loop_terminal_result_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )
        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        terminal = build_tool_attempt_loop_terminal_result(
            loop_result=loop_result,
        )

        self.assertTrue(bool(terminal["should_return"]))
        self.assertIsNotNone(terminal["terminal_effects"])
        self.assertEqual(terminal["terminal_effects"]["state"]["phase"], "error")

    def test_build_tool_plan_item_retry_loop_result_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_effects = {
            "trace_step": action_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": action_step,
            },
            "observation": 'calc_eval: {"expression": "1+2*3", "result": 7.0, "tool_kind": "local_calculator"}',
            "output": {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            },
            "rag_followup": None,
        }
        loop_result = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": action_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": {"trace": success_effects["trace"]},
            "success_effects": success_effects,
            "terminal_effects": None,
        }

        result = build_tool_plan_item_retry_loop_result(
            loop_result=loop_result,
        )

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["trace_event"]["step"]["content"], "Tool done: calc_eval")
        self.assertIsNotNone(result["success_effects"])
        self.assertIsNone(result["terminal_effects"])

    def test_build_tool_plan_item_retry_loop_result_keeps_terminal_failure_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_effects = {
            "trace_step": action_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": action_step,
            },
            "status": "failed",
            "error_message": "transient",
            "audit_detail": {"step_id": "step-1", "retry_count": 2},
            "state": {"task_id": "task-1", "phase": "error"},
        }
        loop_result = {
            "tool_end_event": {"status": "error"},
            "error_event": {"code": "tool_execution_error"},
            "retryable": False,
            "next_action_step": action_step,
            "last_error": "transient",
            "plan_item_result": {"outcome": "terminal_failure"},
            "postprocess": None,
            "success_effects": None,
            "terminal_effects": terminal_effects,
        }

        result = build_tool_plan_item_retry_loop_result(
            loop_result=loop_result,
        )

        self.assertEqual(result["outcome"], "terminal_failure")
        self.assertEqual(result["trace_event"]["step"]["content"], "Tool error: calc_eval")
        self.assertIsNone(result["success_effects"])
        self.assertIsNotNone(result["terminal_effects"])

    def test_build_tool_step_updates_keep_current_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )
        error_step = build_tool_step_error_update(
            action_step=base_step,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            retry_count=1,
            token_count=9,
            error_message="transient",
        )

        self.assertEqual(success_step["content"], "Tool done: calc_eval")
        self.assertEqual(success_step["meta"]["tool"]["status"], "done")
        self.assertEqual(error_step["content"], "Tool error: calc_eval")
        self.assertEqual(error_step["meta"]["tool"]["status"], "error")

    def test_build_tool_attempt_success_transition_keeps_current_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        transition = build_tool_attempt_success_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(transition["action_step"]["content"], "Tool done: calc_eval")
        self.assertEqual(transition["action_step"]["meta"]["tool"]["status"], "done")
        self.assertEqual(
            transition["events"]["tool_end"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "done",
                "latency_ms": 12,
                "output_preview": output,
                "retry_count": 0,
            },
        )

    def test_build_tool_attempt_error_transition_keeps_current_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        exc = MockToolExecutionError("transient", fatal=False)

        transition = build_tool_attempt_error_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            exc=exc,
            token_count=9,
        )

        self.assertEqual(transition["action_step"]["content"], "Tool error: calc_eval")
        self.assertEqual(transition["action_step"]["meta"]["tool"]["status"], "error")
        self.assertTrue(transition["retryable"])
        self.assertEqual(
            transition["events"]["tool_end"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "error",
                "latency_ms": 12,
                "output_preview": {"error": "transient"},
                "retry_count": 1,
                "error": "transient",
            },
        )
        self.assertEqual(
            transition["events"]["error"],
            {
                "task_id": "task-1",
                "message": "transient",
                "code": "tool_execution_error",
                "fatal": False,
                "retryable": True,
                "retryCount": 1,
                "step_id": "step-1",
            },
        )

    def test_build_tool_step_output_returns_output_dict_when_present(self) -> None:
        step = {
            "meta": {
                "tool": {
                    "output": {
                        "result": 7.0,
                    }
                }
            }
        }

        self.assertEqual(build_tool_step_output(step), {"result": 7.0})

    def test_build_tool_observation_entry_keeps_current_shape(self) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="calc_eval",
                output={
                    "expression": "1+2*3",
                    "result": 7.0,
                    "tool_kind": "local_calculator",
                },
            ),
            'calc_eval: {"expression": "1+2*3", "result": 7.0, "tool_kind": "local_calculator"}',
        )

    def test_build_tool_step_updates_and_observation_use_display_label_for_mock_plan(
        self,
    ) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Task Planner",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "mock_plan",
                    "label": "Task Planner",
                    "input": {"prompt_preview": "请帮我规划"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "plan": "Analyze request -> retrieve context -> synthesize answer.",
            "echo": True,
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="mock_plan",
            tool_input={"prompt_preview": "请帮我规划"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(success_step["content"], "Tool done: Task Planner")
        self.assertEqual(success_step["meta"]["tool"]["label"], "Task Planner")
        self.assertEqual(
            build_tool_observation_entry(name="mock_plan", output=output),
            'Task Planner: {"plan": "Analyze request -> retrieve context -> synthesize answer.", "echo": true}',
        )

    def test_build_tool_step_updates_observation_and_rag_followup_use_display_label_for_mock_retrieve(
        self,
    ) -> None:
        base_step = {
            "id": "step-2",
            "seq": 4,
            "type": "action",
            "content": "Tool running: Knowledge Retrieval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_2",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "mock_retrieve",
                    "label": "Knowledge Retrieval",
                    "input": {"query": "检索 demo"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "chunks": ["alpha", "beta"],
            "knowledge_base_id": "demo-kb",
            "hit_count": 2,
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="mock_retrieve",
            tool_input={"query": "检索 demo"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )
        rag_followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=5,
            model="mock-gpt",
            tool_name="mock_retrieve",
            output=output,
            token_count=2,
        )

        self.assertEqual(success_step["content"], "Tool done: Knowledge Retrieval")
        self.assertEqual(success_step["meta"]["tool"]["name"], "task_retrieve")
        self.assertEqual(
            build_tool_observation_entry(name="mock_retrieve", output=output),
            'Knowledge Retrieval: {"chunks": ["alpha", "beta"], "knowledge_base_id": "demo-kb", "hit_count": 2}',
        )
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["content"],
            "Knowledge Retrieval returned snippets from the selected knowledge base.",
        )

    def test_build_tool_trace_event_keeps_current_shape(self) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                }
            },
        }

        self.assertEqual(
            build_tool_trace_event(
                task_id="task-1",
                step_id="step-1",
                step=step,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": step,
            },
        )

    def test_build_tool_terminal_failure_transition_keeps_current_shape(self) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }

        transition = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=step,
            error_message="transient",
            retry_count=1,
        )

        self.assertEqual(
            transition["trace"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": step,
            },
        )
        self.assertEqual(
            transition["audit_detail"],
            {
                "step_id": "step-1",
                "retry_count": 1,
            },
        )
        self.assertEqual(
            transition["state"],
            {
                "task_id": "task-1",
                "phase": "error",
            },
        )
        self.assertEqual(transition["status"], "failed")
        self.assertEqual(transition["error_message"], "transient")

    def test_build_tool_rag_step_keeps_current_shape(self) -> None:
        self.assertEqual(
            build_tool_rag_step(
                step_id="rag-1",
                seq=4,
                model="mock-gpt",
                chunks=["a", "b"],
                knowledge_base_id="demo",
                token_count=2,
            ),
            {
                "id": "rag-1",
                "seq": 4,
                "type": "thought",
                "content": "Knowledge Retrieval returned snippets from the selected knowledge base.",
                "meta": {
                    "model": "mock-gpt",
                    "step_type": "rag_retrieval",
                    "tokens": 2,
                    "cost_estimate": None,
                    "rag": {
                        "chunks": ["a", "b"],
                        "knowledge_base_id": "demo",
                    },
                },
            },
        )

    def test_build_tool_prompt_with_observations_keeps_current_shape(self) -> None:
        self.assertEqual(
            build_tool_prompt_with_observations(
                prompt="hello",
                tool_observations=[],
            ),
            "hello",
        )
        self.assertEqual(
            build_tool_prompt_with_observations(
                prompt="hello",
                tool_observations=["calc_eval: {\"result\": 7.0}"],
            ),
            'hello\n\nTool observations:\ncalc_eval: {"result": 7.0}',
        )

    def test_build_tool_attempt_result_keeps_success_shape(self) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {"result": 7.0},
                }
            },
        }

        self.assertEqual(
            build_tool_attempt_result(
                outcome="success",
                action_step=step,
                events={
                    "tool_end": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "status": "done",
                    }
                },
                retryable=False,
                error_message=None,
                retry_count=0,
            ),
            {
                "outcome": "success",
                "action_step": step,
                "events": {
                    "tool_end": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "status": "done",
                    }
                },
                "retryable": False,
                "error_message": None,
                "retry_count": 0,
            },
        )

    def test_build_tool_attempt_outcome_keeps_success_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        outcome = build_tool_attempt_outcome(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=build_tool_runtime_context(
                name="calc_eval",
                prompt="calc",
                user_id="user-1",
                attempt=0,
            ),
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(outcome["outcome"], "success")
        self.assertFalse(outcome["retryable"])
        self.assertIsNone(outcome["error_message"])
        self.assertEqual(outcome["retry_count"], 0)
        self.assertEqual(outcome["action_step"]["content"], "Tool done: calc_eval")
        self.assertEqual(outcome["events"]["tool_end"]["status"], "done")

    def test_build_tool_attempt_outcome_keeps_error_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        outcome = build_tool_attempt_outcome(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
        )

        self.assertEqual(outcome["outcome"], "error")
        self.assertTrue(outcome["retryable"])
        self.assertEqual(outcome["error_message"], "transient")
        self.assertEqual(outcome["retry_count"], 1)
        self.assertEqual(outcome["action_step"]["content"], "Tool error: calc_eval")
        self.assertEqual(outcome["events"]["tool_end"]["status"], "error")

    def test_build_tool_iteration_context_keeps_current_shape(self) -> None:
        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        self.assertEqual(context["step_id"], "step-1")
        self.assertEqual(context["action_step"]["id"], "step-1")
        self.assertEqual(context["action_step"]["seq"], 3)
        self.assertEqual(context["action_step"]["content"], "Tool running: calc_eval")
        self.assertEqual(context["action_step"]["meta"]["tool"]["status"], "running")

    def test_build_tool_iteration_success_artifacts_keeps_current_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )

        self.assertEqual(
            artifacts["trace"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": action_step,
            },
        )
        self.assertEqual(
            artifacts["observation"],
            'calc_eval: {"expression": "1+2*3", "result": 7.0, "tool_kind": "local_calculator"}',
        )
        self.assertEqual(
            artifacts["output"],
            {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            },
        )

    def test_build_tool_rag_followup_keeps_current_shape(self) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="mock_retrieve",
            output={
                "chunks": ["a", "b"],
                "knowledge_base_id": "demo",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"],
            {
                "id": "rag-1",
                "seq": 4,
                "type": "thought",
                "content": "Knowledge Retrieval returned snippets from the selected knowledge base.",
                "meta": {
                    "model": "mock-gpt",
                    "step_type": "rag_retrieval",
                    "tokens": 2,
                    "cost_estimate": None,
                    "rag": {
                        "chunks": ["a", "b"],
                        "knowledge_base_id": "demo",
                    },
                },
            },
        )
        self.assertEqual(
            followup["trace"],
            {
                "task_id": "task-1",
                "step_id": "rag-1",
                "step": followup["step"],
            },
        )

    def test_build_tool_iteration_execution_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        execution = build_tool_iteration_execution(
            task_id="task-1",
            step_id="step-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(
            execution["start_events"],
            {
                "tool_start": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "name": "calc_eval",
                    "display_name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "retry_count": 0,
                },
                "state": {
                    "task_id": "task-1",
                    "phase": "tool_running",
                },
            },
        )
        self.assertEqual(execution["outcome"]["outcome"], "success")
        self.assertEqual(execution["outcome"]["events"]["tool_end"]["status"], "done")
        self.assertEqual(
            execution["success_artifacts"]["trace"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": execution["outcome"]["action_step"],
            },
        )
        self.assertIsNone(execution["terminal_failure"])

    def test_build_tool_iteration_execution_keeps_terminal_error_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        execution = build_tool_iteration_execution(
            task_id="task-1",
            step_id="step-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
        )

        self.assertEqual(execution["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(execution["outcome"]["outcome"], "error")
        self.assertFalse(execution["outcome"]["retryable"])
        self.assertIsNone(execution["success_artifacts"])
        self.assertIsNotNone(execution["terminal_failure"])
        assert execution["terminal_failure"] is not None
        self.assertEqual(execution["terminal_failure"]["status"], "failed")
        self.assertEqual(execution["terminal_failure"]["state"]["phase"], "error")

    def test_build_tool_iteration_execution_uses_current_action_step_on_retry(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        current_step = build_tool_step_error_update(
            action_step=iteration_ctx["action_step"],
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            retry_count=1,
            token_count=9,
            error_message="transient",
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        execution = build_tool_iteration_execution(
            task_id="task-1",
            step_id="step-1",
            iteration_ctx=iteration_ctx,
            action_step=current_step,
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error="transient",
        )

        self.assertEqual(execution["start_events"]["tool_start"]["retry_count"], 1)
        self.assertEqual(execution["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(
            execution["outcome"]["action_step"]["meta"]["tool"]["error"],
            "transient",
        )
        self.assertEqual(
            execution["outcome"]["action_step"]["meta"]["tool"]["retry_count"],
            1,
        )

    def test_build_tool_plan_item_success_bundle_keeps_current_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )

        bundle = build_tool_plan_item_success_bundle(
            success_artifacts=success_artifacts,
            rag_followup=None,
        )

        self.assertEqual(bundle["trace"], success_artifacts["trace"])
        self.assertEqual(bundle["observation"], success_artifacts["observation"])
        self.assertEqual(bundle["output"], success_artifacts["output"])
        self.assertIsNone(bundle["rag_followup"])

    def test_build_tool_plan_item_result_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )

        result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=None,
            ),
            terminal_failure=None,
        )

        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(result["last_error"])
        self.assertIsNotNone(result["success_bundle"])
        self.assertIsNone(result["terminal_failure"])

    def test_build_tool_plan_item_result_keeps_terminal_failure_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_failure = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            error_message="transient",
            retry_count=2,
        )

        result = build_tool_plan_item_result(
            outcome="terminal_failure",
            action_step=action_step,
            last_error="transient",
            success_bundle=None,
            terminal_failure=terminal_failure,
        )

        self.assertEqual(result["outcome"], "terminal_failure")
        self.assertEqual(result["last_error"], "transient")
        self.assertIsNone(result["success_bundle"])
        self.assertEqual(result["terminal_failure"]["status"], "failed")

    def test_build_tool_plan_item_execution_result_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )
        iteration_execution = {
            "outcome": {
                "action_step": action_step,
                "error_message": None,
            },
            "success_artifacts": success_artifacts,
            "terminal_failure": None,
        }

        result = build_tool_plan_item_execution_result(
            iteration_execution=iteration_execution,
            rag_followup=None,
        )

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["success_bundle"]["trace"], success_artifacts["trace"])
        self.assertIsNone(result["terminal_failure"])

    def test_build_tool_plan_item_execution_result_keeps_terminal_failure_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_failure = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            error_message="transient",
            retry_count=2,
        )
        iteration_execution = {
            "outcome": {
                "action_step": action_step,
                "error_message": "transient",
            },
            "success_artifacts": None,
            "terminal_failure": terminal_failure,
        }

        result = build_tool_plan_item_execution_result(
            iteration_execution=iteration_execution,
            rag_followup=None,
        )

        self.assertEqual(result["outcome"], "terminal_failure")
        self.assertEqual(result["last_error"], "transient")
        self.assertIsNone(result["success_bundle"])
        self.assertEqual(result["terminal_failure"]["status"], "failed")

    def test_build_tool_plan_item_execution_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["plan_item_result"]["outcome"], "success")
        self.assertEqual(result["start_events"]["state"]["phase"], "tool_running")
        self.assertEqual(
            result["plan_item_result"]["success_bundle"]["trace"]["step"]["content"],
            "Tool done: calc_eval",
        )
        self.assertEqual(result["tool_end_event"]["status"], "done")
        self.assertFalse(bool(result["retryable"]))
        self.assertIsNone(result["error_event"])
        self.assertIsNotNone(result["postprocess"])
        self.assertIsNotNone(result["success_effects"])
        self.assertIsNone(result["terminal_effects"])
        self.assertEqual(
            result["success_effects"]["trace"]["step"]["content"],
            "Tool done: calc_eval",
        )
        self.assertEqual(
            result["next_action_step"]["content"],
            "Tool done: calc_eval",
        )
        self.assertIsNone(result["terminal_failure"])

    def test_build_tool_plan_item_execution_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["plan_item_result"]["outcome"], "terminal_failure")
        self.assertEqual(result["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(result["last_error"], "transient")
        self.assertEqual(result["tool_end_event"]["status"], "error")
        self.assertFalse(bool(result["retryable"]))
        self.assertEqual(result["error_event"]["code"], "tool_execution_error")
        self.assertIsNone(result["postprocess"])
        self.assertIsNone(result["success_effects"])
        self.assertIsNotNone(result["terminal_effects"])
        self.assertEqual(result["terminal_effects"]["state"]["phase"], "error")
        self.assertIsNotNone(result["terminal_failure"])
        assert result["terminal_failure"] is not None
        self.assertEqual(result["terminal_failure"]["status"], "failed")

    def test_build_tool_plan_item_execution_builds_rag_followup_for_retrieve(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="mock_retrieve",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="mock_retrieve",
            prompt="检索 demo",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "chunks": ["alpha", "beta"],
            "knowledge_base_id": "demo-kb",
            "hit_count": 2,
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="mock_retrieve",
            tool_input={"query": "demo"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-1",
            rag_token_count=2,
        )

        rag_followup = result["plan_item_result"]["success_bundle"]["rag_followup"]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(rag_followup["step"]["id"], "rag-1")
        self.assertEqual(
            rag_followup["step"]["content"],
            "Knowledge Retrieval returned snippets from the selected knowledge base.",
        )
        self.assertEqual(rag_followup["step"]["meta"]["tokens"], 2)
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"]["knowledge_base_id"],
            "demo-kb",
        )

    def test_build_tool_plan_item_execution_exposes_iteration_execution_bundle(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(
            result["iteration_execution"]["outcome"]["events"]["tool_end"]["status"],
            "done",
        )
        self.assertEqual(
            result["iteration_execution"]["start_events"]["state"]["phase"],
            "tool_running",
        )

    def test_build_tool_plan_item_postprocess_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )
        plan_item_result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=None,
            ),
            terminal_failure=None,
        )

        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )

        self.assertEqual(postprocess["trace"], success_artifacts["trace"])
        self.assertEqual(
            postprocess["observation"],
            'calc_eval: {"expression": "1+2*3", "result": 7.0, "tool_kind": "local_calculator"}',
        )
        self.assertEqual(postprocess["output"], success_artifacts["output"])
        self.assertIsNone(postprocess["rag_followup"])

    def test_build_tool_plan_item_success_effects_keep_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )
        plan_item_result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=None,
            ),
            terminal_failure=None,
        )
        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )

        effects = build_tool_plan_item_success_effects(
            action_step=action_step,
            postprocess=postprocess,
        )

        self.assertEqual(effects["trace_step"]["id"], "step-1")
        self.assertEqual(effects["trace"]["step"]["content"], "Tool done: calc_eval")
        self.assertEqual(
            effects["observation"],
            'calc_eval: {"expression": "1+2*3", "result": 7.0, "tool_kind": "local_calculator"}',
        )
        self.assertIsNone(effects["rag_followup"])

    def test_build_tool_plan_item_postprocess_keeps_rag_followup_shape(self) -> None:
        rag_followup = {
            "step": {
                "id": "rag-1",
                "seq": 4,
            },
            "trace": {
                "task_id": "task-1",
                "step_id": "rag-1",
                "step": {
                    "id": "rag-1",
                    "seq": 4,
                },
            },
        }
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: mock_retrieve",
            "meta": {
                "tool": {
                    "name": "mock_retrieve",
                    "status": "done",
                    "output": {
                        "chunks": ["alpha"],
                        "knowledge_base_id": "demo-kb",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="mock_retrieve",
        )
        plan_item_result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=rag_followup,
            ),
            terminal_failure=None,
        )

        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )

        self.assertEqual(postprocess["rag_followup"], rag_followup)

    def test_build_tool_plan_item_terminal_effects_keep_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_failure = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            error_message="transient",
            retry_count=2,
        )

        effects = build_tool_plan_item_terminal_effects(
            action_step=action_step,
            terminal_failure=terminal_failure,
        )

        self.assertEqual(effects["trace_step"]["id"], "step-1")
        self.assertEqual(effects["trace"]["step"]["content"], "Tool error: calc_eval")
        self.assertEqual(effects["status"], "failed")
        self.assertEqual(effects["error_message"], "transient")
        self.assertEqual(effects["state"]["phase"], "error")

    def test_build_tool_plan_item_stream_effects_keeps_success_shape(self) -> None:
        loop_execution_result = {
            "trace_event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
            },
            "success_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": "Tool done: mock_retrieve",
                    },
                },
                "observation": 'mock_retrieve: {"chunks": ["alpha"]}',
                "rag_followup": {
                    "step": {
                        "id": "rag-1",
                        "seq": 4,
                        "content": "Retrieved snippets",
                    },
                    "trace": {
                        "task_id": "task-1",
                        "step_id": "rag-1",
                        "step": {
                            "id": "rag-1",
                            "seq": 4,
                            "content": "Retrieved snippets",
                        },
                    },
                },
            },
            "terminal_effects": None,
            "should_return": False,
        }

        result = build_tool_plan_item_stream_effects(
            loop_execution_result=loop_execution_result,
        )

        self.assertFalse(bool(result["should_return"]))
        self.assertEqual(result["seq_increment"], 1)
        self.assertEqual(
            result["tool_observations"],
            ['mock_retrieve: {"chunks": ["alpha"]}'],
        )
        self.assertEqual(result["observation"], 'mock_retrieve: {"chunks": ["alpha"]}')
        self.assertIsNone(result["terminal_effects"])
        self.assertEqual([step["id"] for step in result["trace_steps"]], ["step-1", "rag-1"])
        self.assertEqual([event["step_id"] for event in result["trace_events"]], ["step-1", "rag-1"])

    def test_build_tool_plan_item_stream_effects_keeps_terminal_shape(self) -> None:
        terminal_effects = {
            "trace_step": {
                "id": "step-1",
                "seq": 3,
                "content": "Tool error: calc_eval",
            },
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool error: calc_eval",
                },
            },
            "status": "failed",
            "error_message": "fatal",
            "audit_detail": {"step_id": "step-1", "retry_count": 1},
            "state": {"task_id": "task-1", "phase": "error"},
        }
        loop_execution_result = {
            "trace_event": terminal_effects["trace"],
            "success_effects": None,
            "terminal_effects": terminal_effects,
            "should_return": True,
        }

        result = build_tool_plan_item_stream_effects(
            loop_execution_result=loop_execution_result,
        )

        self.assertTrue(bool(result["should_return"]))
        self.assertEqual(result["seq_increment"], 0)
        self.assertEqual(result["tool_observations"], [])
        self.assertIsNone(result["observation"])
        self.assertEqual(result["terminal_effects"], terminal_effects)
        self.assertEqual([step["id"] for step in result["trace_steps"]], ["step-1"])
        self.assertEqual([event["step_id"] for event in result["trace_events"]], ["step-1"])

    def test_build_tool_plan_item_terminal_return_effects_keeps_shape(self) -> None:
        terminal_effects = {
            "trace_step": {
                "id": "step-1",
                "seq": 3,
                "content": "Tool error: calc_eval",
            },
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool error: calc_eval",
                },
            },
            "status": "failed",
            "error_message": "fatal",
            "audit_detail": {"step_id": "step-1", "retry_count": 1},
            "state": {"task_id": "task-1", "phase": "error"},
        }

        result = build_tool_plan_item_terminal_return_effects(
            terminal_effects=terminal_effects,
        )

        self.assertEqual(result["task_status"], "failed")
        self.assertEqual(result["state_event"]["phase"], "error")
        self.assertEqual(result["failure_event"]["event_type"], "task_failed")
        self.assertEqual(result["failure_event"]["code"], "tool_execution_error")
        self.assertEqual(result["failure_event"]["message"], "fatal")
        self.assertEqual(
            result["failure_event"]["detail"],
            {"step_id": "step-1", "retry_count": 1},
        )

    def test_build_tool_plan_item_return_action_keeps_shape(self) -> None:
        terminal_return_effects = {
            "task_status": "failed",
            "state_event": {"task_id": "task-1", "phase": "error"},
            "failure_event": {
                "event_type": "task_failed",
                "code": "tool_execution_error",
                "message": "fatal",
                "detail": {"step_id": "step-1", "retry_count": 1},
            },
        }
        trace_steps = [
            {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
        ]

        result = build_tool_plan_item_return_action(
            task_id="task-1",
            trace_steps=trace_steps,
            user_id="user-1",
            terminal_return_effects=terminal_return_effects,
        )

        self.assertEqual(
            result["complete_task_kwargs"],
            {
                "task_id": "task-1",
                "trace_steps": trace_steps,
                "user_id": "user-1",
                "status": "failed",
            },
        )
        self.assertEqual(
            result["failure_event_kwargs"],
            terminal_return_effects["failure_event"],
        )
        self.assertEqual(
            result["state_event"],
            terminal_return_effects["state_event"],
        )

    def test_build_tool_plan_item_trace_write_action_keeps_shape(self) -> None:
        trace_write = {
            "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
            "event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
            },
            "force_persist": False,
        }

        result = build_tool_plan_item_trace_write_action(trace_write=trace_write)

        self.assertEqual(result["trace_step"], trace_write["step"])
        self.assertEqual(result["trace_event"], trace_write["event"])
        self.assertEqual(result["persist_force"], False)

    def test_build_tool_plan_item_continue_action_keeps_shape(self) -> None:
        continue_update = {
            "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
            "seq_increment": 1,
        }

        result = build_tool_plan_item_continue_action(
            continue_update=continue_update,
        )

        self.assertEqual(
            result,
            {
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
        )

    def test_build_tool_plan_item_next_action_execution_keeps_continue_shape(self) -> None:
        next_action = {
            "kind": "continue",
            "continue_update": {
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
            "terminal_return_effects": None,
        }

        result = build_tool_plan_item_next_action_execution(
            task_id="task-1",
            trace_steps=[{"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"}],
            user_id="user-1",
            next_action=next_action,
        )

        self.assertEqual(
            result,
            {
                "kind": "continue",
                "continue_update": next_action["continue_update"],
                "continue_action": next_action["continue_update"],
                "return_action": None,
            },
        )

    def test_build_tool_plan_item_next_action_execution_keeps_return_shape(self) -> None:
        next_action = {
            "kind": "return",
            "continue_update": {
                "tool_observations": [],
                "seq_increment": 0,
            },
            "terminal_return_effects": {
                "task_status": "failed",
                "state_event": {"task_id": "task-1", "phase": "error"},
                "failure_event": {
                    "event_type": "task_failed",
                    "code": "tool_execution_error",
                    "message": "fatal",
                    "detail": {"step_id": "step-1", "retry_count": 1},
                },
            },
        }
        trace_steps = [
            {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
        ]

        result = build_tool_plan_item_next_action_execution(
            task_id="task-1",
            trace_steps=trace_steps,
            user_id="user-1",
            next_action=next_action,
        )

        self.assertEqual(result["kind"], "return")
        self.assertEqual(result["continue_update"], next_action["continue_update"])
        self.assertEqual(
            result["continue_action"],
            next_action["continue_update"],
        )
        self.assertEqual(
            result["return_action"],
            {
                "complete_task_kwargs": {
                    "task_id": "task-1",
                    "trace_steps": trace_steps,
                    "user_id": "user-1",
                    "status": "failed",
                },
                "failure_event_kwargs": next_action["terminal_return_effects"]["failure_event"],
                "state_event": next_action["terminal_return_effects"]["state_event"],
            },
        )

    def test_build_tool_plan_item_trace_write_service_action_keeps_shape(self) -> None:
        trace_write_action = {
            "trace_step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
            "trace_event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
            },
            "persist_force": False,
        }

        result = build_tool_plan_item_trace_write_service_action(
            trace_write_action=trace_write_action,
        )

        self.assertEqual(
            result,
            {
                "kind": "trace_write",
                "trace_step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                },
                "persist_force": False,
            },
        )

    def test_build_tool_plan_item_continue_service_action_keeps_shape(self) -> None:
        continue_action = {
            "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
            "seq_increment": 1,
        }

        result = build_tool_plan_item_continue_service_action(
            continue_action=continue_action,
        )

        self.assertEqual(
            result,
            {
                "kind": "continue",
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
        )

    def test_build_tool_plan_item_return_service_actions_keep_shape(self) -> None:
        return_action = {
            "complete_task_kwargs": {
                "task_id": "task-1",
                "trace_steps": [{"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"}],
                "user_id": "user-1",
                "status": "failed",
            },
            "failure_event_kwargs": {
                "event_type": "task_failed",
                "code": "tool_execution_error",
                "message": "fatal",
                "detail": {"step_id": "step-1", "retry_count": 1},
            },
            "state_event": {"task_id": "task-1", "phase": "error"},
        }

        result = build_tool_plan_item_return_service_actions(
            return_action=return_action,
        )

        self.assertEqual(
            result,
            [
                {
                    "kind": "complete_task",
                    "kwargs": return_action["complete_task_kwargs"],
                },
                {
                    "kind": "record_failure_event",
                    "kwargs": return_action["failure_event_kwargs"],
                },
                {
                    "kind": "emit_state",
                    "event": "state",
                    "data": return_action["state_event"],
                },
                {
                    "kind": "return",
                },
            ],
        )

    def test_build_tool_plan_item_service_actions_keep_continue_order(self) -> None:
        service_execution = {
            "trace_write_actions": [
                {
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    },
                    "persist_force": False,
                },
            ],
            "next_action_execution": {
                "kind": "continue",
                "continue_update": {
                    "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                    "seq_increment": 1,
                },
                "continue_action": {
                    "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                    "seq_increment": 1,
                },
                "return_action": None,
            },
        }

        result = build_tool_plan_item_service_actions(
            service_execution=service_execution,
        )

        self.assertEqual(
            result,
            [
                {
                    "kind": "trace_write",
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    },
                    "persist_force": False,
                },
                {
                    "kind": "continue",
                    "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                    "seq_increment": 1,
                },
            ],
        )

    def test_build_tool_plan_item_service_actions_keep_return_order(self) -> None:
        service_execution = {
            "trace_write_actions": [
                {
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    },
                    "persist_force": True,
                },
            ],
            "next_action_execution": {
                "kind": "return",
                "continue_update": {
                    "tool_observations": [],
                    "seq_increment": 0,
                },
                "continue_action": {
                    "tool_observations": [],
                    "seq_increment": 0,
                },
                "return_action": {
                    "complete_task_kwargs": {
                        "task_id": "task-1",
                        "trace_steps": [{"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"}],
                        "user_id": "user-1",
                        "status": "failed",
                    },
                    "failure_event_kwargs": {
                        "event_type": "task_failed",
                        "code": "tool_execution_error",
                        "message": "fatal",
                        "detail": {"step_id": "step-1", "retry_count": 1},
                    },
                    "state_event": {"task_id": "task-1", "phase": "error"},
                },
            },
        }

        result = build_tool_plan_item_service_actions(
            service_execution=service_execution,
        )

        self.assertEqual(
            result,
            [
                {
                    "kind": "trace_write",
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    },
                    "persist_force": True,
                },
                {
                    "kind": "complete_task",
                    "kwargs": service_execution["next_action_execution"]["return_action"]["complete_task_kwargs"],
                },
                {
                    "kind": "record_failure_event",
                    "kwargs": service_execution["next_action_execution"]["return_action"]["failure_event_kwargs"],
                },
                {
                    "kind": "emit_state",
                    "event": "state",
                    "data": service_execution["next_action_execution"]["return_action"]["state_event"],
                },
                {
                    "kind": "return",
                },
            ],
        )

    def test_build_tool_plan_item_service_effects_execution_keeps_continue_shape(self) -> None:
        service_effects = {
            "trace_write_actions": [
                {
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    },
                    "persist_force": False,
                },
            ],
            "next_action": {
                "kind": "continue",
                "continue_update": {
                    "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                    "seq_increment": 1,
                },
                "terminal_return_effects": None,
            },
        }

        result = build_tool_plan_item_service_effects_execution(
            task_id="task-1",
            trace_steps=[{"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"}],
            user_id="user-1",
            service_effects=service_effects,
        )

        self.assertEqual(result["trace_write_actions"], service_effects["trace_write_actions"])
        self.assertEqual(result["next_action_execution"]["kind"], "continue")
        self.assertEqual(
            result["next_action_execution"]["continue_update"],
            service_effects["next_action"]["continue_update"],
        )
        self.assertEqual(
            result["next_action_execution"]["continue_action"],
            service_effects["next_action"]["continue_update"],
        )
        self.assertIsNone(result["next_action_execution"]["return_action"])
        self.assertEqual(
            result["service_actions"],
            [
                {
                    "kind": "trace_write",
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    },
                    "persist_force": False,
                },
                {
                    "kind": "continue",
                    "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                    "seq_increment": 1,
                },
            ],
        )

    def test_build_tool_plan_item_service_effects_execution_keeps_return_shape(self) -> None:
        service_effects = {
            "trace_write_actions": [
                {
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    },
                    "persist_force": True,
                },
            ],
            "next_action": {
                "kind": "return",
                "continue_update": {
                    "tool_observations": [],
                    "seq_increment": 0,
                },
                "terminal_return_effects": {
                    "task_status": "failed",
                    "state_event": {"task_id": "task-1", "phase": "error"},
                    "failure_event": {
                        "event_type": "task_failed",
                        "code": "tool_execution_error",
                        "message": "fatal",
                        "detail": {"step_id": "step-1", "retry_count": 1},
                    },
                },
            },
        }
        trace_steps = [{"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"}]

        result = build_tool_plan_item_service_effects_execution(
            task_id="task-1",
            trace_steps=trace_steps,
            user_id="user-1",
            service_effects=service_effects,
        )

        self.assertEqual(result["trace_write_actions"], service_effects["trace_write_actions"])
        self.assertEqual(result["next_action_execution"]["kind"], "return")
        self.assertEqual(
            result["next_action_execution"]["continue_action"],
            service_effects["next_action"]["continue_update"],
        )
        self.assertEqual(
            result["next_action_execution"]["return_action"],
            {
                "complete_task_kwargs": {
                    "task_id": "task-1",
                    "trace_steps": trace_steps,
                    "user_id": "user-1",
                    "status": "failed",
                },
                "failure_event_kwargs": service_effects["next_action"]["terminal_return_effects"]["failure_event"],
                "state_event": service_effects["next_action"]["terminal_return_effects"]["state_event"],
            },
        )
        self.assertEqual(
            result["service_actions"],
            [
                {
                    "kind": "trace_write",
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    },
                    "persist_force": True,
                },
                {
                    "kind": "complete_task",
                    "kwargs": result["next_action_execution"]["return_action"]["complete_task_kwargs"],
                },
                {
                    "kind": "record_failure_event",
                    "kwargs": result["next_action_execution"]["return_action"]["failure_event_kwargs"],
                },
                {
                    "kind": "emit_state",
                    "event": "state",
                    "data": result["next_action_execution"]["return_action"]["state_event"],
                },
                {
                    "kind": "return",
                },
            ],
        )

    def test_build_tool_plan_item_service_execution_keeps_success_shape(self) -> None:
        loop_execution_result = {
            "trace_event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
            },
            "success_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": "Tool done: mock_retrieve",
                    },
                },
                "observation": 'mock_retrieve: {"chunks": ["alpha"]}',
                "rag_followup": {
                    "step": {
                        "id": "rag-1",
                        "seq": 4,
                        "content": "Retrieved snippets",
                    },
                    "trace": {
                        "task_id": "task-1",
                        "step_id": "rag-1",
                        "step": {
                            "id": "rag-1",
                            "seq": 4,
                            "content": "Retrieved snippets",
                        },
                    },
                },
            },
            "terminal_effects": None,
            "should_return": False,
        }

        result = build_tool_plan_item_service_execution(
            task_id="task-1",
            trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
            user_id="user-1",
            loop_execution_result=loop_execution_result,
        )

        self.assertEqual(
            [(item["trace_step"]["id"], item["trace_event"]["step_id"], item["persist_force"]) for item in result["trace_write_actions"]],
            [("step-1", "step-1", False), ("rag-1", "rag-1", False)],
        )
        self.assertEqual(result["next_action_execution"]["kind"], "continue")
        self.assertEqual(
            result["next_action_execution"]["continue_update"],
            {
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
        )

    def test_build_tool_plan_item_service_execution_keeps_terminal_shape(self) -> None:
        loop_execution_result = {
            "trace_event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool error: calc_eval",
                },
            },
            "success_effects": None,
            "terminal_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool error: calc_eval",
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": "Tool error: calc_eval",
                    },
                },
                "status": "failed",
                "error_message": "fatal",
                "audit_detail": {"step_id": "step-1", "retry_count": 1},
                "state": {"task_id": "task-1", "phase": "error"},
            },
            "should_return": True,
        }

        result = build_tool_plan_item_service_execution(
            task_id="task-1",
            trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
            user_id="user-1",
            loop_execution_result=loop_execution_result,
        )

        self.assertEqual(
            [(item["trace_step"]["id"], item["trace_event"]["step_id"], item["persist_force"]) for item in result["trace_write_actions"]],
            [("step-1", "step-1", True)],
        )
        self.assertEqual(result["next_action_execution"]["kind"], "return")
        self.assertEqual(
            result["next_action_execution"]["return_action"]["complete_task_kwargs"]["status"],
            "failed",
        )

    def test_build_tool_plan_item_service_effects_keeps_success_shape(self) -> None:
        loop_execution_result = {
            "trace_event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
            },
            "success_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": "Tool done: mock_retrieve",
                    },
                },
                "observation": 'mock_retrieve: {"chunks": ["alpha"]}',
                "rag_followup": {
                    "step": {
                        "id": "rag-1",
                        "seq": 4,
                        "content": "Retrieved snippets",
                    },
                    "trace": {
                        "task_id": "task-1",
                        "step_id": "rag-1",
                        "step": {
                            "id": "rag-1",
                            "seq": 4,
                            "content": "Retrieved snippets",
                        },
                    },
                },
            },
            "terminal_effects": None,
            "should_return": False,
        }

        result = build_tool_plan_item_service_effects(
            loop_execution_result=loop_execution_result,
        )

        self.assertFalse(bool(result["should_return"]))
        self.assertEqual(
            [(item["step"]["id"], item["event"]["step_id"], item["force_persist"]) for item in result["trace_writes"]],
            [("step-1", "step-1", False), ("rag-1", "rag-1", False)],
        )
        self.assertEqual(
            [(item["trace_step"]["id"], item["trace_event"]["step_id"], item["persist_force"]) for item in result["trace_write_actions"]],
            [("step-1", "step-1", False), ("rag-1", "rag-1", False)],
        )
        self.assertEqual(
            result["continue_update"],
            {
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
        )
        self.assertEqual(
            result["next_action"],
            {
                "kind": "continue",
                "continue_update": {
                    "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                    "seq_increment": 1,
                },
                "terminal_return_effects": None,
            },
        )
        self.assertEqual(result["terminal_return_effects"], None)
        self.assertEqual(result["tool_observations"], ['mock_retrieve: {"chunks": ["alpha"]}'])
        self.assertEqual(result["seq_increment"], 1)
        self.assertEqual([step["id"] for step in result["trace_steps"]], ["step-1", "rag-1"])
        self.assertEqual([event["step_id"] for event in result["trace_events"]], ["step-1", "rag-1"])

    def test_build_tool_plan_item_service_effects_keeps_terminal_shape(self) -> None:
        terminal_effects = {
            "trace_step": {
                "id": "step-1",
                "seq": 3,
                "content": "Tool error: calc_eval",
            },
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool error: calc_eval",
                },
            },
            "status": "failed",
            "error_message": "fatal",
            "audit_detail": {"step_id": "step-1", "retry_count": 1},
            "state": {"task_id": "task-1", "phase": "error"},
        }
        loop_execution_result = {
            "trace_event": terminal_effects["trace"],
            "success_effects": None,
            "terminal_effects": terminal_effects,
            "should_return": True,
        }

        result = build_tool_plan_item_service_effects(
            loop_execution_result=loop_execution_result,
        )

        self.assertTrue(bool(result["should_return"]))
        self.assertEqual(
            [(item["step"]["id"], item["event"]["step_id"], item["force_persist"]) for item in result["trace_writes"]],
            [("step-1", "step-1", True)],
        )
        self.assertEqual(
            [(item["trace_step"]["id"], item["trace_event"]["step_id"], item["persist_force"]) for item in result["trace_write_actions"]],
            [("step-1", "step-1", True)],
        )
        self.assertEqual(
            result["continue_update"],
            {
                "tool_observations": [],
                "seq_increment": 0,
            },
        )
        self.assertEqual(
            result["next_action"],
            {
                "kind": "return",
                "continue_update": {
                    "tool_observations": [],
                    "seq_increment": 0,
                },
                "terminal_return_effects": result["terminal_return_effects"],
            },
        )
        self.assertEqual(result["tool_observations"], [])
        self.assertEqual(result["seq_increment"], 0)
        self.assertEqual(
            result["terminal_return_effects"]["failure_event"]["message"],
            "fatal",
        )
        self.assertEqual(
            result["terminal_return_effects"]["state_event"]["phase"],
            "error",
        )

    def test_execute_tool_plan_item_retry_loop_yields_start_events_before_runner(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="mock_retrieve",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runner_calls: list[tuple[int, str]] = []

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            runner_calls.append((attempt, user_id))
            return {
                "chunks": ["alpha", "beta"],
                "knowledge_base_id": "demo-kb",
                "hit_count": 2,
            }

        items = execute_tool_plan_item_retry_loop(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            initial_action_step=iteration_ctx["action_step"],
            tool_name="mock_retrieve",
            tool_input={"query": "demo"},
            prompt="检索 demo",
            user_id="user-1",
            model="mock-gpt",
            estimate_token_count=lambda text: len(text.strip()) or 0,
            make_step_id=lambda: "rag-1",
            raise_if_should_abort=lambda: None,
            run_tool_fn=fake_run_tool,
        )

        first = next(items)
        second = next(items)
        self.assertEqual(runner_calls, [])
        third = next(items)
        final_item = next(items)

        self.assertEqual(first["kind"], "event")
        self.assertEqual(first["event"], "tool_start")
        self.assertEqual(second["kind"], "event")
        self.assertEqual(second["event"], "state")
        self.assertEqual(third["kind"], "event")
        self.assertEqual(third["event"], "tool_end")
        self.assertEqual(runner_calls, [(0, "user-1")])
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(final_item["result"]["retry_loop_result"]["outcome"], "success")
        self.assertFalse(bool(final_item["result"]["should_return"]))
        self.assertEqual(
            final_item["result"]["trace_event"]["step"]["content"],
            "Tool done: Knowledge Retrieval",
        )
        self.assertIsNone(final_item["result"]["terminal_effects"])
        self.assertEqual(
            final_item["result"]["success_effects"]["rag_followup"]["step"]["id"],
            "rag-1",
        )

    def test_execute_tool_plan_item_retry_loop_keeps_retry_then_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempts: list[int] = []

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            attempts.append(attempt)
            if attempt == 0:
                raise MockToolExecutionError("transient", fatal=False)
            return {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            }

        items = list(
            execute_tool_plan_item_retry_loop(
                task_id="task-1",
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                run_tool_fn=fake_run_tool,
            )
        )

        self.assertEqual(attempts, [0, 1])
        self.assertEqual(
            [item["event"] for item in items if item["kind"] == "event"],
            ["tool_start", "state", "tool_end", "error", "tool_start", "state", "tool_end"],
        )
        self.assertEqual(items[2]["data"]["status"], "error")
        self.assertTrue(bool(items[3]["data"]["retryable"]))
        self.assertEqual(items[4]["data"]["retry_count"], 1)
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(final_item["result"]["retry_loop_result"]["outcome"], "success")
        self.assertEqual(
            final_item["result"]["loop_result"]["next_action_step"]["meta"]["tool"]["error"],
            "transient",
        )

    def test_execute_tool_plan_item_retry_loop_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            raise MockToolExecutionError("fatal", fatal=True)

        items = list(
            execute_tool_plan_item_retry_loop(
                task_id="task-1",
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                run_tool_fn=fake_run_tool,
            )
        )

        self.assertEqual(
            [item["event"] for item in items if item["kind"] == "event"],
            ["tool_start", "state", "tool_end", "error"],
        )
        self.assertTrue(bool(items[3]["data"]["fatal"]))
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            final_item["result"]["retry_loop_result"]["outcome"],
            "terminal_failure",
        )
        self.assertTrue(bool(final_item["result"]["should_return"]))
        self.assertIsNone(final_item["result"]["success_effects"])
        self.assertEqual(
            final_item["result"]["trace_event"]["step"]["content"],
            "Tool error: calc_eval",
        )
        self.assertEqual(
            final_item["result"]["terminal_effects"]["state"]["phase"],
            "error",
        )

    def test_execute_tool_plan_item_retry_loop_accepts_custom_registry_retry_policy(self) -> None:
        attempt_calls: list[tuple[int, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            del tool_input, prompt
            attempt_calls.append((0, user_id))
            raise MockToolExecutionError("transient", fatal=False)

        registry = build_tool_registry(
            overrides={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="custom_calc",
                    label="Custom Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=9_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        items = list(
            execute_tool_plan_item_retry_loop(
                task_id="task-1",
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        self.assertEqual(attempt_calls, [(0, "")])
        self.assertEqual(
            [item["event"] for item in items if item["kind"] == "event"],
            ["tool_start", "state", "tool_end", "error"],
        )
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(final_item["result"]["outcome"], "terminal_failure")
        self.assertTrue(bool(final_item["result"]["should_return"]))


    def test_execute_tool_plan_item_service_execution_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="mock_retrieve",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            return {
                "chunks": ["alpha", "beta"],
                "knowledge_base_id": "demo-kb",
                "hit_count": 2,
            }

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="mock_retrieve",
                tool_input={"query": "demo"},
                prompt="检索 demo",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                run_tool_fn=fake_run_tool,
            )
        )

        self.assertEqual(
            [item["event"] for item in items if item["kind"] == "event"],
            ["tool_start", "state", "tool_end"],
        )
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            [(item["kind"], item.get("trace_step", {}).get("id")) for item in final_item["result"]["service_actions"]],
            [("trace_write", "step-1"), ("trace_write", "rag-1"), ("continue", None)],
        )
        self.assertEqual(final_item["result"]["next_action_execution"]["kind"], "continue")

    def test_execute_tool_plan_item_service_execution_keeps_terminal_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            raise MockToolExecutionError("fatal", fatal=True)

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                run_tool_fn=fake_run_tool,
            )
        )

        self.assertEqual(
            [item["event"] for item in items if item["kind"] == "event"],
            ["tool_start", "state", "tool_end", "error"],
        )
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            [item["kind"] for item in final_item["result"]["service_actions"]],
            ["trace_write", "complete_task", "record_failure_event", "emit_state", "return"],
        )
        self.assertEqual(final_item["result"]["next_action_execution"]["kind"], "return")

    def test_execute_tool_plan_item_service_execution_accepts_custom_registry(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "custom-ok",
                "tool_kind": "custom_calc",
            }

        registry = build_tool_registry(
            overrides={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="custom_calc",
                    label="Custom Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=9_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        self.assertEqual(runner_calls, [({"expression": "1+2*3"}, "calc", "")])
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"]["tool_kind"],
            "custom_calc",
        )

    def test_execute_tool_plan_item_service_execution_accepts_custom_registry_loader(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "loader-ok",
                "tool_kind": "loader_calc",
            }

        def custom_loader() -> dict[str, ToolRegistration]:
            return {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }

        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry_loader=custom_loader,
            )
        )

        self.assertEqual(runner_calls, [({"expression": "1+2*3"}, "calc", "")])
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"]["tool_kind"],
            "loader_calc",
        )

    def test_execute_tool_plan_item_service_execution_accepts_custom_registry_provider(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "provider-ok",
                "tool_kind": "provider_calc",
            }

        provider = StaticToolRegistryProvider(
            registry={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="provider_calc",
                    label="Provider Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=13_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry_provider=provider,
            )
        )

        self.assertEqual(runner_calls, [({"expression": "1+2*3"}, "calc", "")])
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"]["tool_kind"],
            "provider_calc",
        )

    def test_execute_tool_plan_item_service_actions_keeps_continue_shape(self) -> None:
        trace_steps = [{"id": "existing-1", "seq": 2, "content": "Existing"}]
        tool_observations: list[str] = []
        persist_forces: list[bool] = []
        complete_calls: list[dict[str, object]] = []
        failure_calls: list[dict[str, object]] = []
        service_actions = [
            {
                "kind": "trace_write",
                "trace_step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                },
                "persist_force": False,
            },
            {
                "kind": "continue",
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
        ]

        items = list(
            execute_tool_plan_item_service_actions(
                service_actions=service_actions,
                trace_steps=trace_steps,
                tool_observations=tool_observations,
                seq_cursor=3,
                persist_trace_fn=lambda *, force: persist_forces.append(bool(force)),
                complete_task_fn=lambda **kwargs: complete_calls.append(kwargs),
                record_failure_event_fn=lambda **kwargs: failure_calls.append(kwargs),
            )
        )

        self.assertEqual([item["kind"] for item in items], ["event", "result"])
        self.assertEqual(items[0]["event"], "trace")
        self.assertEqual(items[0]["data"]["step_id"], "step-1")
        self.assertEqual(items[1]["result"], {"seq_cursor": 4, "should_return": False})
        self.assertEqual([step["id"] for step in trace_steps], ["existing-1", "step-1"])
        self.assertEqual(tool_observations, ['mock_retrieve: {"chunks": ["alpha"]}'])
        self.assertEqual(persist_forces, [False])
        self.assertEqual(complete_calls, [])
        self.assertEqual(failure_calls, [])

    def test_execute_tool_plan_item_service_actions_keeps_return_shape(self) -> None:
        trace_steps = [{"id": "existing-1", "seq": 2, "content": "Existing"}]
        tool_observations: list[str] = []
        persist_forces: list[bool] = []
        complete_calls: list[dict[str, object]] = []
        failure_calls: list[dict[str, object]] = []
        service_actions = [
            {
                "kind": "trace_write",
                "trace_step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                },
                "persist_force": True,
            },
            {
                "kind": "complete_task",
                "kwargs": {
                    "task_id": "task-1",
                    "trace_steps": trace_steps,
                    "user_id": "user-1",
                    "status": "failed",
                },
            },
            {
                "kind": "record_failure_event",
                "kwargs": {
                    "event_type": "task_failed",
                    "code": "tool_execution_error",
                    "message": "fatal",
                    "detail": {"step_id": "step-1", "retry_count": 1},
                },
            },
            {
                "kind": "emit_state",
                "event": "state",
                "data": {"task_id": "task-1", "phase": "error"},
            },
            {
                "kind": "return",
            },
        ]

        items = list(
            execute_tool_plan_item_service_actions(
                service_actions=service_actions,
                trace_steps=trace_steps,
                tool_observations=tool_observations,
                seq_cursor=3,
                persist_trace_fn=lambda *, force: persist_forces.append(bool(force)),
                complete_task_fn=lambda **kwargs: complete_calls.append(kwargs),
                record_failure_event_fn=lambda **kwargs: failure_calls.append(kwargs),
            )
        )

        self.assertEqual([item["kind"] for item in items], ["event", "event", "result"])
        self.assertEqual([item["event"] for item in items[:2]], ["trace", "state"])
        self.assertEqual(items[-1]["result"], {"seq_cursor": 3, "should_return": True})
        self.assertEqual([step["id"] for step in trace_steps], ["existing-1", "step-1"])
        self.assertEqual(tool_observations, [])
        self.assertEqual(persist_forces, [True])
        self.assertEqual(complete_calls, [service_actions[1]["kwargs"]])
        self.assertEqual(failure_calls, [service_actions[2]["kwargs"]])


if __name__ == "__main__":
    unittest.main()
