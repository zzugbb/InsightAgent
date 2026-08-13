#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import ast
import gzip
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zlib
from collections import UserDict, UserList, UserString
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.services.tool_runtime as tool_runtime_module  # type: ignore[import-not-found]
import app.services.chat_execution_service as chat_execution_module  # type: ignore[import-not-found]
import app.services.chat_persistence_service as chat_persistence_module  # type: ignore[import-not-found]
import app.services.chroma_memory_service as chroma_memory_module  # type: ignore[import-not-found]
import app.services.chroma_rag_service as chroma_rag_module  # type: ignore[import-not-found]
import app.services.settings_service as settings_service_module  # type: ignore[import-not-found]
import app.services.audit_service as audit_service_module  # type: ignore[import-not-found]
import app.api.routes.auth as auth_routes_module  # type: ignore[import-not-found]
import app.api.routes.audit as audit_routes_module  # type: ignore[import-not-found]
import app.api.routes.rag as rag_routes_module  # type: ignore[import-not-found]
import app.api.routes.settings as settings_routes_module  # type: ignore[import-not-found]
import app.api.routes.tasks as task_routes_module  # type: ignore[import-not-found]
import app.api.routes.sessions as session_routes_module  # type: ignore[import-not-found]
import app.providers.mock_provider as mock_provider_module  # type: ignore[import-not-found]
import app.providers.openai_compatible_provider as openai_provider_module  # type: ignore[import-not-found]
import app.db as db_module  # type: ignore[import-not-found]
from app.api.routes.settings import (  # type: ignore[import-not-found]
    _apply_tool_registry_preview_to_validate_response,
    _build_settings_summary_response,
    SettingsValidateResponse,
)
from app.providers.base import ProviderUsage  # type: ignore[import-not-found]
from app.providers.mock_provider import MockLLMProvider  # type: ignore[import-not-found]
from app.providers.openai_compatible_provider import (  # type: ignore[import-not-found]
    OpenAICompatibleLLMProvider,
)
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
    build_tool_plan_item_retry_loop_execution_result,
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
    build_tool_result_output,
    build_tool_result_preview,
    build_tool_result_summary,
    build_tool_runtime_semantics_meta,
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
    get_tool_effective_result_output_keys,
    get_tool_effective_result_preview_keys,
    get_tool_semantic_kind,
    normalize_tool_output_for_registration,
    build_tool_registry,
    build_tool_registry_extra_tools_from_settings,
    build_tool_registry_from_file_artifacts,
    build_tool_registry_from_file,
    build_tool_registry_loader_from_file_artifacts,
    build_tool_registry_loader_from_file,
    build_tool_registry_loaders_from_settings_artifacts,
    build_tool_registry_loader_factories_from_settings_artifacts,
    build_tool_registry_provider_from_file_artifacts,
    build_tool_registry_provider_sources_from_settings_artifacts,
    build_tool_registry_provider_sources_from_settings,
    build_tool_registry_provider_from_file,
    build_tool_registry_providers_from_settings_artifacts,
    build_tool_registry_provider_factories_from_settings_artifacts,
    build_tool_registry_overrides_from_settings,
    build_tool_registry_profile_settings_config,
    build_tool_registry_settings_config,
    build_tool_registry_settings_execution_diagnostics,
    build_tool_registry_diagnostics_runtime_artifacts,
    build_tool_registry_diagnostics_summary,
    build_tool_registry_diagnostics_runtime_artifacts_model,
    build_tool_registry_diagnostics_summary_model,
    build_tool_registry_diagnostics_trace_service_action_model,
    build_tool_registry_diagnostics_audit_service_action_model,
    get_enabled_planning_tool_names,
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
    build_configured_tool_registry_provider_preflight_tool_details,
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

from tool_runtime_slice.http_json_mapping import HttpJsonMappingMixin
from tool_runtime_slice.http_json_status_redirect import HttpJsonStatusRedirectMixin
from tool_runtime_slice.http_json_error_handling import HttpJsonErrorHandlingMixin
from tool_runtime_slice.http_json_request_validation import HttpJsonRequestValidationMixin
from tool_runtime_slice.http_json_mapping_diagnostics import HttpJsonMappingDiagnosticsMixin
from tool_runtime_slice.http_json_request_wrappers import HttpJsonRequestWrappersMixin
from tool_runtime_slice.http_json_response_body import HttpJsonResponseBodyMixin
from tool_runtime_slice.http_json_response_protocol import HttpJsonResponseProtocolMixin
from tool_runtime_slice.http_json_template_validation import HttpJsonTemplateValidationMixin
from tool_runtime_slice.model_dump_routes import ModelDumpRoutesMixin
from tool_runtime_slice.planning_provider import PlanningProviderMixin
from tool_runtime_slice.provider_source_http_json import ProviderSourceHttpJsonMixin
from tool_runtime_slice.provider_streaming import ProviderStreamingMixin
from tool_runtime_slice.registry_file_diagnostics import RegistryFileDiagnosticsMixin
from tool_runtime_slice.registry_execution_diagnostics import RegistryExecutionDiagnosticsMixin
from tool_runtime_slice.registry_source_file_diagnostics import RegistrySourceFileDiagnosticsMixin
from tool_runtime_slice.registry_runtime_governance import RegistryRuntimeGovernanceMixin
from tool_runtime_slice.registry_http_json_projection import RegistryHttpJsonProjectionMixin
from tool_runtime_slice.registry_provider_source_artifacts import RegistryProviderSourceArtifactsMixin
from tool_runtime_slice.registry_provider_source_aliases import RegistryProviderSourceAliasesMixin
from tool_runtime_slice.export_provider_source_artifacts import ExportProviderSourceArtifactsMixin
from tool_runtime_slice.response_provider_source_artifacts import ResponseProviderSourceArtifactsMixin
from tool_runtime_slice.audit_provider_source_artifacts import AuditProviderSourceArtifactsMixin
from tool_runtime_slice.sse_provider_source_artifacts import SseProviderSourceArtifactsMixin
from tool_runtime_slice.trace_provider_source_artifacts import TraceProviderSourceArtifactsMixin
from tool_runtime_slice.registry_provider_settings import RegistryProviderSettingsMixin
from tool_runtime_slice.registry_runtime_models import RegistryRuntimeModelsMixin
from tool_runtime_slice.registry_runtime_service_models import RegistryRuntimeServiceModelsMixin
from tool_runtime_slice.runtime_http_json_execution import RuntimeHttpJsonExecutionMixin
from tool_runtime_slice.runtime_attempt_lifecycle import RuntimeAttemptLifecycleMixin
from tool_runtime_slice.runtime_observation_display import RuntimeObservationDisplayMixin
from tool_runtime_slice.runtime_facade_split import RuntimeFacadeSplitMixin
from tool_runtime_slice.rag_governance import RagGovernanceMixin
from tool_runtime_slice.rag_route_governance import RagRouteGovernanceMixin
from tool_runtime_slice.rag_shared_scope_governance import RagSharedScopeGovernanceMixin
from tool_runtime_slice.rag_export_governance import RagExportGovernanceMixin
from tool_runtime_slice.rag_runtime_version_governance import RagRuntimeVersionGovernanceMixin
from tool_runtime_slice.runtime_rag_execution import RuntimeRagExecutionMixin
from tool_runtime_slice.runtime_result_rag import RuntimeResultRagMixin
from tool_runtime_slice.runtime_result_semantics import RuntimeResultSemanticsMixin
from tool_runtime_slice.runtime_service_execution_semantics import RuntimeServiceExecutionSemanticsMixin
from tool_runtime_slice.settings_registry import SettingsRegistryMixin
from tool_runtime_slice.task_routes_usage_governance import TaskRoutesUsageGovernanceMixin
from tool_runtime_slice.task_trace_response_summaries import TaskTraceResponseSummariesMixin
from tool_runtime_slice.task_usage_dashboard import TaskUsageDashboardMixin
from tool_runtime_slice.task_session_export_markdown import TaskSessionExportMarkdownMixin
from tool_runtime_slice.session_export_markdown import SessionExportMarkdownMixin
from tool_runtime_slice.task_export_response_summary import TaskExportResponseSummaryMixin
from tool_runtime_slice.task_session_export_payload import TaskSessionExportPayloadMixin
from tool_runtime_slice.task_trace_export_governance import TaskTraceExportGovernanceMixin
from tool_runtime_slice.production_reliability_execution import (
    ProductionReliabilityExecutionMixin,
)
from tool_runtime_slice.production_reliability_failure_paths import (
    ProductionReliabilityFailurePathsMixin,
)
from tool_runtime_slice.production_reliability_queue import ProductionReliabilityQueueMixin
from tool_runtime_slice.production_reliability_startup import ProductionReliabilityStartupMixin


class ToolRuntimeSliceTests(
    ProviderSourceHttpJsonMixin,
    PlanningProviderMixin,
    SettingsRegistryMixin,
    HttpJsonMappingMixin,
    HttpJsonStatusRedirectMixin,
    HttpJsonErrorHandlingMixin,
    HttpJsonRequestValidationMixin,
    HttpJsonRequestWrappersMixin,
    HttpJsonTemplateValidationMixin,
    HttpJsonMappingDiagnosticsMixin,
    ModelDumpRoutesMixin,
    TaskTraceExportGovernanceMixin,
    TaskRoutesUsageGovernanceMixin,
    TaskTraceResponseSummariesMixin,
    TaskUsageDashboardMixin,
    TaskSessionExportMarkdownMixin,
    TaskSessionExportPayloadMixin,
    SessionExportMarkdownMixin,
    TaskExportResponseSummaryMixin,
    ProviderStreamingMixin,
    RegistryRuntimeGovernanceMixin,
    RegistryHttpJsonProjectionMixin,
    RegistryProviderSourceArtifactsMixin,
    RegistryProviderSourceAliasesMixin,
    ExportProviderSourceArtifactsMixin,
    ResponseProviderSourceArtifactsMixin,
    AuditProviderSourceArtifactsMixin,
    SseProviderSourceArtifactsMixin,
    TraceProviderSourceArtifactsMixin,
    RegistryProviderSettingsMixin,
    RegistryFileDiagnosticsMixin,
    RegistrySourceFileDiagnosticsMixin,
    RegistryExecutionDiagnosticsMixin,
    RegistryRuntimeModelsMixin,
    RegistryRuntimeServiceModelsMixin,
    RuntimeFacadeSplitMixin,
    RagGovernanceMixin,
    RagRouteGovernanceMixin,
    RagSharedScopeGovernanceMixin,
    RagExportGovernanceMixin,
    RagRuntimeVersionGovernanceMixin,
    RuntimeResultRagMixin,
    RuntimeResultSemanticsMixin,
    RuntimeAttemptLifecycleMixin,
    RuntimeObservationDisplayMixin,
    RuntimeRagExecutionMixin,
    RuntimeHttpJsonExecutionMixin,
    HttpJsonResponseProtocolMixin,
    HttpJsonResponseBodyMixin,
    RuntimeServiceExecutionSemanticsMixin,
    ProductionReliabilityFailurePathsMixin,
    ProductionReliabilityExecutionMixin,
    ProductionReliabilityQueueMixin,
    ProductionReliabilityStartupMixin,
    unittest.TestCase,
):
    def _make_sensitive_http_json_action_step(
        self,
        *,
        step_id: str = "step-http-json-raw",
        content: str = "Tool done: Provider Status",
    ) -> dict[str, object]:
        return {
            "id": step_id,
            "seq": 3,
            "type": "action",
            "content": content,
            "meta": {
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "status": "done",
                    "execution_kind": "http_json",
                    "effective_result_output_keys": ["status", "message"],
                    "output": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                    "output_preview": {
                        "status": "ready",
                        "message": "preview token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        }


if __name__ == "__main__":
    unittest.main()
