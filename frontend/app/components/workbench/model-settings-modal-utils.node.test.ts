import assert from "node:assert/strict";
import test from "node:test";

import {
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
          tool_details: [
            {
              name: "provider_search",
              label: "Provider Search",
              kind: "provider_retrieval",
              semantic_kind: "knowledge_retrieval",
              retryable_by_default: false,
              default_timeout_ms: 21_000,
              requires_user_context: true,
              supports_result_preview: true,
              effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
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
    result.selectedSourceToolDetailsSummary,
    "Provider Search [knowledge_retrieval]: hit_count, knowledge_base_id | Provider Math [local_calculator]: expression, result",
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
