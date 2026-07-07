import assert from "node:assert/strict";
import test from "node:test";

import {
  formatToolRegistryProviderSourceDiagnosticsSummary,
  formatToolRegistryProviderToolDetailsSummary,
  resolveModelSettingsSelectionDetails,
} from "./model-settings-modal-utils.ts";

test("resolveModelSettingsSelectionDetails uses preview source detail summaries", () => {
  const result = resolveModelSettingsSelectionDetails({
    previewSource: {
      enabled_tool_labels: ["Provider Search", "Provider Math"],
      available_tool_registry_profile_details: [
        {
          name: "default",
          enabled_tool_names: ["task_plan", "task_retrieve", "calc_eval"],
          enabled_tool_labels: ["Task Planner", "Knowledge Retrieval", "calc_eval"],
        },
        {
          name: "retrieval_only",
          enabled_tool_names: ["task_retrieve"],
          enabled_tool_labels: ["Knowledge Retrieval"],
          tool_details: [
            {
              name: "task_retrieve",
              label: "Knowledge Retrieval",
              kind: "knowledge_retrieval",
              semantic_kind: "knowledge_retrieval",
              retryable_by_default: true,
              default_timeout_ms: 5_000,
              requires_user_context: true,
              supports_result_preview: true,
              effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
            },
          ],
        },
      ],
      available_tool_registry_provider_source_details: [
        {
          name: "analytics_suite",
          base_profile: "retrieval_only",
          enabled_tool_names: ["provider_search", "provider_math"],
          enabled_tool_labels: ["Provider Search", "Provider Math"],
          diagnostics_summary: {
            has_diagnostics: true,
            skipped_total: 0,
            missing_total: 1,
            total: 1,
            entries: [
              {
                kind: "missing",
                target: "registry_files",
                count: 1,
                values: ["missing-registry.json"],
              },
            ],
          },
          tool_details: [
            {
              name: "provider_search",
              label: "Provider Search",
              kind: "provider_retrieval",
              semantic_kind: "provider_search",
              semantic_family: "knowledge_retrieval",
              execution_kind: "http_json",
              execution_summary: {
                method: "POST",
                url_origin: "https://provider.example",
                url_path: "/search",
                header_count: 1,
                query_param_count: 1,
                json_body_field_count: 2,
                response_path: "$.data",
                result_field_names: ["documents_total", "request_id"],
              },
              execution_diagnostics: [
                "http_json execution response_path must be a non-empty string when provided",
              ],
              retryable_by_default: false,
              default_timeout_ms: 21_000,
              requires_user_context: true,
              supports_result_preview: true,
              effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
              effective_result_output_keys: ["documents_total"],
            },
            {
              name: "provider_math",
              label: "Provider Math",
              kind: "provider_calc",
              semantic_kind: "local_calculator",
              retryable_by_default: true,
              default_timeout_ms: 13_000,
              requires_user_context: true,
              supports_result_preview: true,
              effective_result_preview_keys: ["expression", "result"],
            },
          ],
        },
      ],
    },
    profileName: "retrieval_only",
    sourceName: "analytics_suite",
  });

  assert.equal(result.selectedProfileTools, "Knowledge Retrieval");
  assert.equal(
    result.selectedProfileToolDetailsSummary,
    "Knowledge Retrieval [knowledge_retrieval]: hit_count, knowledge_base_id",
  );
  assert.equal(result.selectedSourceTools, "Provider Search, Provider Math");
  assert.equal(result.selectedSourceBaseProfile, "retrieval_only");
  assert.equal(
    result.selectedSourceDiagnosticsSummary,
    "missing registry files: missing-registry.json",
  );
  assert.equal(
    result.selectedSourceToolDetailsSummary,
    "Provider Search [provider_search · knowledge_retrieval via http_json @ POST https://provider.example/search · headers 1 · query 1 · body 2 · response $.data · fields documents_total, request_id]: preview hit_count, knowledge_base_id; output documents_total; diagnostics http_json execution response_path must be a non-empty string when provided | Provider Math [local_calculator]: expression, result",
  );
});

test("formatToolRegistryProviderSourceDiagnosticsSummary humanizes missing entries", () => {
  const result = formatToolRegistryProviderSourceDiagnosticsSummary({
    has_diagnostics: true,
    skipped_total: 0,
    missing_total: 2,
    total: 2,
    entries: [
      {
        kind: "missing",
        target: "registry_files",
        count: 2,
        values: ["missing-a.json", "missing-b.json"],
      },
    ],
  });

  assert.equal(
    result,
    "missing registry files: missing-a.json, missing-b.json",
  );
});

test("formatToolRegistryProviderToolDetailsSummary falls back to kind when preview keys are unavailable", () => {
  const result = formatToolRegistryProviderToolDetailsSummary([
    {
      name: "custom_lookup",
      label: "Custom Lookup",
      kind: "custom_lookup",
      semantic_kind: null,
      retryable_by_default: false,
      default_timeout_ms: 5_000,
      requires_user_context: true,
      supports_result_preview: false,
      effective_result_preview_keys: [],
    },
  ]);

  assert.equal(result, "Custom Lookup [custom_lookup]");
});

test("formatToolRegistryProviderToolDetailsSummary includes output keys when available", () => {
  const result = formatToolRegistryProviderToolDetailsSummary([
    {
      name: "provider_search",
      label: "Provider Search",
      kind: "provider_retrieval",
      semantic_kind: "provider_search",
      execution_kind: "http_json",
      execution_summary: {
        method: "POST",
        url_origin: "https://provider.example",
        url_path: "/search",
        header_count: 1,
        query_param_count: 1,
        json_body_field_count: 2,
        response_path: "$.data",
        result_field_names: ["documents_total", "request_id"],
      },
      retryable_by_default: false,
      default_timeout_ms: 21_000,
      requires_user_context: true,
      supports_result_preview: true,
      effective_result_preview_keys: ["documents_total"],
      effective_result_output_keys: ["documents_total"],
    },
  ]);

  assert.equal(
    result,
    "Provider Search [provider_search via http_json @ POST https://provider.example/search · headers 1 · query 1 · body 2 · response $.data · fields documents_total, request_id]: preview documents_total; output documents_total",
  );
});

test("formatToolRegistryProviderToolDetailsSummary includes execution diagnostics when available", () => {
  const result = formatToolRegistryProviderToolDetailsSummary([
    {
      name: "provider_search",
      label: "Provider Search",
      kind: "provider_retrieval",
      semantic_kind: "provider_search",
      execution_kind: "http_json",
      execution_summary: {
        method: "POST",
        url_origin: "https://provider.example",
        url_path: "/search",
      },
      execution_diagnostics: [
        "http_json execution response_path must be a non-empty string when provided",
        "http_json execution result_fields mapping must not be empty",
      ],
      retryable_by_default: false,
      default_timeout_ms: 21_000,
      requires_user_context: true,
      supports_result_preview: true,
      effective_result_preview_keys: ["documents_total"],
      effective_result_output_keys: ["documents_total"],
    },
  ]);

  assert.equal(
    result,
    "Provider Search [provider_search via http_json @ POST https://provider.example/search]: preview documents_total; output documents_total; diagnostics http_json execution response_path must be a non-empty string when provided, http_json execution result_fields mapping must not be empty",
  );
});
