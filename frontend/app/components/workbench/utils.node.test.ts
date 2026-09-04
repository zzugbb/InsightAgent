import test from "node:test";
import assert from "node:assert/strict";

import {
  filterTraceSteps,
  buildTaskDetailHref,
  formatTaskFailureSummary,
  resolveTaskFailureHintDisplay,
  formatTraceStepSemanticStatsSummary,
  formatTraceStepMetaSubtitle,
  getStepTitle,
  matchesTaskGovernanceFilters,
  matchesTaskFailureSourceFilter,
  matchesTaskObservabilityFilter,
  matchesTaskStatusFilter,
  matchesTraceStepSearchQuery,
  matchesTraceStepSemanticFilter,
  resolveTaskFailureDiagnosticGroups,
  resolveTaskFailureDiagnosticGroupsForTaskCenter,
  resolveTaskFailureDiagnosticChipClick,
  resolveTaskFailureDiagnosticDrilldown,
  resolveTaskCenterListState,
  resolveTaskCenterOperatorHint,
  resolveTaskDetailHrefTraceSemanticFilter,
  resolveInspectorTraceSemanticFilterChange,
  resolveTaskStatusDisplay,
  resolveTaskObservabilityFilterChange,
  resolveAuditTaskDetailHref,
  resolveTaskSnapshotSummary,
  resolveTaskStreamTerminalReason,
  resolveTraceStepSemanticStats,
  resolveTraceStepDisplayContent,
} from "./utils.ts";

test("resolveTaskCenterListState distinguishes initial and stale-data errors", () => {
  assert.equal(
    resolveTaskCenterListState({
      isLoading: false,
      isError: true,
      rowCount: 0,
    }),
    "error",
  );
  assert.equal(
    resolveTaskCenterListState({
      isLoading: false,
      isError: true,
      rowCount: 2,
    }),
    "stale_error",
  );
  assert.equal(
    resolveTaskCenterListState({
      isLoading: false,
      isError: false,
      rowCount: 0,
    }),
    "empty",
  );
});

test("buildTaskDetailHref encodes task ids for replay links", () => {
  assert.equal(
    buildTaskDetailHref("task/with space?x=1"),
    "/tasks/task%2Fwith%20space%3Fx%3D1",
  );
  assert.equal(
    buildTaskDetailHref("task/with space?x=1", {
      traceSemanticFilter: "failure",
    }),
    "/tasks/task%2Fwith%20space%3Fx%3D1?trace_semantic=failure",
  );
});

test("resolveAuditTaskDetailHref uses top-level or detail task ids", () => {
  assert.equal(
    resolveAuditTaskDetailHref({
      task_id: "task/top level",
      event_detail: { task_id: "task-detail" },
    }),
    "/tasks/task%2Ftop%20level",
  );
  assert.equal(
    resolveAuditTaskDetailHref({
      task_id: null,
      event_detail: { task_id: "task/detail?x=1" },
    }),
    "/tasks/task%2Fdetail%3Fx%3D1",
  );
  assert.equal(
    resolveAuditTaskDetailHref({
      task_id: " ",
      event_detail: { task_id: " " },
    }),
    null,
  );
  assert.equal(
    resolveAuditTaskDetailHref({
      task_id: "task-failed",
      event_type: "task_failed",
      event_detail: {
        failure_hint: "remote_provider_network_error",
      },
    }),
    "/tasks/task-failed?trace_semantic=failure",
  );
});

test("formatTaskFailureSummary renders safe failure hint and source", () => {
  const labels = {
    failureHintTitle: "Failure hint",
    taskFailureSourceErrorEvent: "SSE error",
    taskFailureSourceToolError: "Tool error",
    taskFailureSourceTraceContent: "Trace content",
    taskFailureSourceLegacyTrace: "Persisted trace",
  };
  assert.equal(
    formatTaskFailureSummary(
      {
        failureHint: " upstream timed out after 30s ",
        failureSource: "tool_error",
      },
      labels,
    ),
    "Failure hint · Tool error: upstream timed out after 30s",
  );
  assert.equal(
    formatTaskFailureSummary(
      {
        failureHint: "  ",
        failureSource: "tool_error",
      },
      labels,
    ),
    null,
  );
});

test("resolveTaskFailureHintDisplay maps known stream error codes", () => {
  assert.equal(
    resolveTaskFailureHintDisplay("remote_provider_network_error", (code) =>
      code === "remote_provider_network_error"
        ? "Failed to reach remote provider. Check network or base URL."
        : null,
    ),
    "Failed to reach remote provider. Check network or base URL.",
  );
  assert.equal(
    resolveTaskFailureHintDisplay("custom failure", () => null),
    "custom failure",
  );
});

test("resolveInspectorTraceSemanticFilterChange clears stale kind and search filters", () => {
  assert.deepEqual(
    resolveInspectorTraceSemanticFilterChange("retrieval", {
      traceView: "flow",
      traceSemanticFilter: "planner",
      traceKindFilter: "tool",
      traceSearchQuery: "remote_provider_network_error",
    }),
    {
      traceView: "flow",
      traceSemanticFilter: "retrieval",
      traceKindFilter: "all",
      traceSearchQuery: "",
    },
  );
  assert.deepEqual(
    resolveInspectorTraceSemanticFilterChange("all", {
      traceView: "list",
      traceSemanticFilter: "failure",
      traceKindFilter: "action",
      traceSearchQuery: "timeout",
    }),
    {
      traceView: "list",
      traceSemanticFilter: "all",
      traceKindFilter: "all",
      traceSearchQuery: "",
    },
  );
});

test("formatTaskFailureSummary maps stream error codes when labels provide a mapper", () => {
  const labels = {
    failureHintTitle: "Failure hint",
    streamErrorByCode: (code: string) =>
      code === "remote_provider_network_error"
        ? "Failed to reach remote provider. Check network or base URL."
        : null,
    taskFailureSourceErrorEvent: "SSE error",
    taskFailureSourceToolError: "Tool error",
    taskFailureSourceTraceContent: "Trace content",
    taskFailureSourceLegacyTrace: "Persisted trace",
  };
  assert.equal(
    formatTaskFailureSummary(
      {
        failureHint: "remote_provider_network_error",
        failureSource: "error_event",
      },
      labels,
    ),
    "Failure hint · SSE error: Failed to reach remote provider. Check network or base URL.",
  );
});

test("resolveTaskFailureDiagnosticGroups counts failure hints by source", () => {
  const groups = resolveTaskFailureDiagnosticGroups([
    {
      failureHint: "remote_provider_network_error",
      failureSource: "error_event",
    },
    {
      failureHint: "upstream timed out after 30s",
      failureSource: "tool_error",
    },
    {
      failureHint: "provider exhausted retries",
      failureSource: "error_event",
    },
    {
      failureHint: "trace mentioned a warning but no source",
      failureSource: null,
    },
    {
      failureHint: " ",
      failureSource: "legacy_trace",
    },
  ]);

  assert.deepEqual(groups, [
    { source: "error_event", count: 2 },
    { source: "tool_error", count: 1 },
  ]);
});

test("resolveTaskFailureDiagnosticGroupsForTaskCenter keeps sibling source chips during drilldown", () => {
  const drilldownScopeSnapshots = [
    {
      failureHint: "remote_provider_network_error",
      failureSource: "error_event",
    },
    {
      failureHint: "provider_search execution failed",
      failureSource: "tool_error",
    },
  ];
  const visibleSnapshots = drilldownScopeSnapshots.filter(
    (snapshot) => snapshot.failureSource === "tool_error",
  );

  assert.deepEqual(
    resolveTaskFailureDiagnosticGroupsForTaskCenter({
      drilldownScopeSnapshots,
      visibleSnapshots,
      activeFailureSourceFilter: "tool_error",
    }),
    [
      { source: "error_event", count: 1 },
      { source: "tool_error", count: 1 },
    ],
  );
  assert.deepEqual(
    resolveTaskFailureDiagnosticGroupsForTaskCenter({
      drilldownScopeSnapshots,
      visibleSnapshots,
      activeFailureSourceFilter: "all",
    }),
    [{ source: "tool_error", count: 1 }],
  );
});

test("resolveTaskFailureDiagnosticDrilldown builds source drilldown filters", () => {
  assert.deepEqual(
    resolveTaskFailureDiagnosticDrilldown("error_event"),
    {
      observabilityFilter: "failure_hint",
      failureSourceFilter: "error_event",
    },
  );
});

test("resolveTaskFailureDiagnosticChipClick toggles the active source drilldown", () => {
  assert.deepEqual(
    resolveTaskFailureDiagnosticChipClick({
      source: "tool_error",
      currentFailureSourceFilter: "all",
    }),
    {
      observabilityFilter: "failure_hint",
      failureSourceFilter: "tool_error",
    },
  );
  assert.deepEqual(
    resolveTaskFailureDiagnosticChipClick({
      source: "tool_error",
      currentFailureSourceFilter: "error_event",
    }),
    {
      observabilityFilter: "failure_hint",
      failureSourceFilter: "tool_error",
    },
  );
  assert.deepEqual(
    resolveTaskFailureDiagnosticChipClick({
      source: "tool_error",
      currentFailureSourceFilter: "tool_error",
    }),
    {
      observabilityFilter: "failure_hint",
      failureSourceFilter: "all",
    },
  );
});

test("resolveTaskObservabilityFilterChange clears hidden failure source outside failure hints", () => {
  assert.deepEqual(
    resolveTaskObservabilityFilterChange({
      observabilityFilter: "all",
      currentFailureSourceFilter: "tool_error",
    }),
    {
      observabilityFilter: "all",
      failureSourceFilter: "all",
    },
  );
  assert.deepEqual(
    resolveTaskObservabilityFilterChange({
      observabilityFilter: "failure_trace",
      currentFailureSourceFilter: "error_event",
    }),
    {
      observabilityFilter: "failure_trace",
      failureSourceFilter: "all",
    },
  );
  assert.deepEqual(
    resolveTaskObservabilityFilterChange({
      observabilityFilter: "failure_hint",
      currentFailureSourceFilter: "legacy_trace",
    }),
    {
      observabilityFilter: "failure_hint",
      failureSourceFilter: "legacy_trace",
    },
  );
});

test("resolveTraceStepDisplayContent prefers inferred result summary from preview-only action steps", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-preview-tool",
    type: "action",
    content: "Tool done: Task Planner",
    meta: {
      tool: {
        name: "task_plan",
        label: "Task Planner",
        status: "done",
        output_preview: {
          plan: "Analyze request -> Synthesize final answer",
          prompt_preview: "playwright trace preview content",
        },
      },
    },
  });

  assert.equal(typeof content, "string");
  assert.match(content, /Planned steps - Analyze request -> Synthesize final answer\./);
  assert.doesNotMatch(content, /Tool done: Task Planner/);
  assert.match(content, /Preview: \{"plan":"Analyze request -> Synthesize final answer","prompt_preview":"playwright trace preview content"\}/);
  assert.match(content, /Analyze request -> Synthesize final answer/);
  assert.match(content, /playwright trace preview content/);
});

test("resolveTraceStepDisplayContent infers result summary from JSON string output preview", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-preview-json-string",
    type: "action",
    content: "Tool done: Hosted Math",
    meta: {
      tool: {
        name: "hosted_math",
        label: "Hosted Math",
        status: "done",
        output_preview: '{"result":7,"request_id":"req-calc-1"}',
      },
    },
  });

  assert.equal(typeof content, "string");
  assert.match(content, /Calculated result = 7 \(request id req-calc-1\)\./);
  assert.doesNotMatch(content, /Tool done: Hosted Math/);
});

test("resolveTraceStepDisplayContent infers result summary from quoted JSON string output preview", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-preview-quoted-json-string",
    type: "action",
    content: "Tool done: Hosted Math",
    meta: {
      tool: {
        name: "hosted_math",
        label: "Hosted Math",
        status: "done",
        output_preview: JSON.stringify(
          '{"result":7,"request_id":"req-calc-1"}',
        ),
      },
    },
  });

  assert.equal(typeof content, "string");
  assert.equal(
    content,
    'Calculated result = 7 (request id req-calc-1).\nPreview: {"result":7,"request_id":"req-calc-1"}',
  );
  assert.doesNotMatch(content, /Tool done: Hosted Math/);
  assert.doesNotMatch(content, /\\\\\\"result/);
});

test("resolveTraceStepDisplayContent infers result summary from JSON string safe output without preview", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-output-json-string-safe-output",
    type: "action",
    content: "Tool done: Hosted Math",
    meta: {
      tool: {
        name: "hosted_math",
        label: "Hosted Math",
        status: "done",
        effective_result_output_keys: ["result", "request_id"],
        output:
          '{"result":7,"request_id":"req-calc-1","kind":"provider_calc","secret":"hidden"}',
      },
    },
  });

  assert.equal(typeof content, "string");
  assert.equal(
    content,
    'Calculated result = 7 (request id req-calc-1).\nOutput: {"result":7,"request_id":"req-calc-1"}',
  );
  assert.doesNotMatch(content, /Tool done: Hosted Math/);
  assert.doesNotMatch(content, /secret/);
});

test("resolveTraceStepDisplayContent infers result summary from quoted JSON string safe output without preview", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-output-quoted-json-string-safe-output",
    type: "action",
    content: "Tool done: Hosted Math",
    meta: {
      tool: {
        name: "hosted_math",
        label: "Hosted Math",
        status: "done",
        effective_result_output_keys: ["result", "request_id"],
        output: JSON.stringify(
          '{"result":7,"request_id":"req-calc-1","kind":"provider_calc","secret":"hidden"}',
        ),
      },
    },
  });

  assert.equal(typeof content, "string");
  assert.equal(
    content,
    'Calculated result = 7 (request id req-calc-1).\nOutput: {"result":7,"request_id":"req-calc-1"}',
  );
  assert.doesNotMatch(content, /Tool done: Hosted Math/);
  assert.doesNotMatch(content, /secret/);
});

test("resolveTraceStepDisplayContent prefers output preview without leaking raw output", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-preview-safe",
    type: "action",
    content: "Tool done: Hot Retrieval",
    meta: {
      tool: {
        name: "task_retrieve_hot",
        label: "Hot Retrieval",
        status: "done",
        output: {
          tool_kind: "hot_knowledge_retrieval",
          raw_documents: [{ id: "doc-1" }],
        },
        output_preview: {
          tool_kind: "hot_knowledge_retrieval",
          knowledge_base_id: "demo-kb",
          hit_count: 2,
        },
      },
    },
  });

  assert.equal(typeof content, "string");
  assert.match(content, /knowledge_base_id/);
  assert.match(content, /demo-kb/);
  assert.match(content, /hit_count/);
  assert.doesNotMatch(content, /raw_documents/);
});

test("resolveTraceStepDisplayContent appends safe tool output fields beyond preview when output policy is present", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-output-policy-safe-extra",
    type: "action",
    content: "Tool done: Provider Search",
    meta: {
      tool: {
        name: "provider_search",
        label: "Provider Search",
        status: "done",
        effective_result_preview_keys: ["documents_total"],
        effective_result_output_keys: ["documents_total", "request_id"],
        output_preview: {
          documents_total: 2,
        },
        output: {
          documents_total: 2,
          request_id: "req-1",
        },
      },
    },
  });

  assert.equal(typeof content, "string");
  assert.match(content, /Preview: \{"documents_total":2\}/);
  assert.match(content, /Output: \{"documents_total":2,"request_id":"req-1"\}/);
});

test("resolveTraceStepDisplayContent prefers tool result summary over generic done content", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-output-policy-result-summary",
    type: "action",
    content: "Tool done: Provider Search",
    meta: {
      tool: {
        name: "provider_search",
        label: "Provider Search",
        status: "done",
        result_summary: "Retrieved 2 documents (request id req-1).",
        effective_result_preview_keys: ["documents_total"],
        effective_result_output_keys: ["documents_total", "request_id"],
        output_preview: {
          documents_total: 2,
        },
        output: {
          documents_total: 2,
          request_id: "req-1",
        },
      },
    },
  });

  assert.equal(
    content,
    'Retrieved 2 documents (request id req-1).\nPreview: {"documents_total":2}\nOutput: {"documents_total":2,"request_id":"req-1"}',
  );
});

test("resolveTraceStepDisplayContent infers retrieval result summary from safe output without explicit result summary", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-output-policy-result-summary-inferred",
    type: "action",
    content: "Tool done: Provider Search",
    meta: {
      tool: {
        name: "provider_search",
        label: "Provider Search",
        kind: "provider_retrieval",
        semantic_kind: "provider_search",
        semantic_family: "knowledge_retrieval",
        status: "done",
        effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
        effective_result_output_keys: [
          "hit_count",
          "knowledge_base_id",
          "request_id",
        ],
        output_preview: {
          hit_count: 2,
          knowledge_base_id: "provider-kb",
        },
        output: {
          hit_count: 2,
          knowledge_base_id: "provider-kb",
          request_id: "req-1",
        },
      },
    },
  });

  assert.equal(
    content,
    'Retrieved 2 hits (request id req-1).\nPreview: {"hit_count":2,"knowledge_base_id":"provider-kb"}\nOutput: {"hit_count":2,"knowledge_base_id":"provider-kb","request_id":"req-1"}',
  );
});

test("resolveTraceStepDisplayContent does not imply local kb for name-only real retrieval steps", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-output-policy-result-summary-name-only-real-tool",
    type: "action",
    content: "Tool done: Provider Search",
    meta: {
      tool: {
        name: "provider_search",
        label: "Provider Search",
        kind: "provider_retrieval",
        status: "done",
        effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
        effective_result_output_keys: [
          "hit_count",
          "knowledge_base_id",
          "request_id",
        ],
        output_preview: {
          hit_count: 2,
          knowledge_base_id: "provider-kb",
        },
        output: {
          hit_count: 2,
          knowledge_base_id: "provider-kb",
          request_id: "req-1",
        },
      },
    },
  });

  assert.equal(
    content,
    'Retrieved 2 hits (request id req-1).\nPreview: {"hit_count":2,"knowledge_base_id":"provider-kb"}\nOutput: {"hit_count":2,"knowledge_base_id":"provider-kb","request_id":"req-1"}',
  );
});

test("resolveTraceStepDisplayContent infers calc result summary from safe output without explicit result summary", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-output-policy-result-summary-calc-inferred",
    type: "action",
    content: "Tool done: Provider Math",
    meta: {
      tool: {
        name: "provider_math",
        label: "Provider Math",
        kind: "provider_calc",
        semantic_kind: "local_calculator",
        status: "done",
        effective_result_preview_keys: ["result"],
        effective_result_output_keys: ["result", "request_id"],
        output_preview: {
          result: 7,
        },
        output: {
          result: 7,
          request_id: "req-calc-1",
        },
      },
    },
  });

  assert.equal(
    content,
    'Calculated result = 7 (request id req-calc-1).\nPreview: {"result":7}\nOutput: {"result":7,"request_id":"req-calc-1"}',
  );
});

test("resolveTraceStepDisplayContent infers calc result summary from structural kind in raw output without semantic family", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-output-policy-result-summary-calc-structural-kind",
    type: "action",
    content: "Tool done: Hosted Math",
    meta: {
      tool: {
        name: "hosted_math",
        label: "Hosted Math",
        status: "done",
        effective_result_preview_keys: ["result"],
        effective_result_output_keys: ["result", "request_id"],
        output_preview: {
          result: 7,
        },
        output: {
          kind: "provider_calc",
          result: 7,
          request_id: "req-calc-1",
        },
      },
    },
  });

  assert.equal(
    content,
    'Calculated result = 7 (request id req-calc-1).\nPreview: {"result":7}\nOutput: {"result":7,"request_id":"req-calc-1"}',
  );
});

test("resolveTraceStepDisplayContent infers calc result summary for name-only real tool without semantic family", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-output-policy-result-summary-calc-name-only-real-tool",
    type: "action",
    content: "Tool done: Hosted Math",
    meta: {
      tool: {
        name: "hosted_math",
        label: "Hosted Math",
        status: "done",
        effective_result_preview_keys: ["result"],
        effective_result_output_keys: ["result", "request_id"],
        output_preview: {
          result: 7,
        },
        output: {
          result: 7,
          request_id: "req-calc-1",
        },
      },
    },
  });

  assert.equal(
    content,
    'Calculated result = 7 (request id req-calc-1).\nPreview: {"result":7}\nOutput: {"result":7,"request_id":"req-calc-1"}',
  );
});

test("resolveTraceStepDisplayContent infers calc result summary for productized calculator label without semantic family", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-output-policy-result-summary-calc-productized-label",
    type: "action",
    content: "Tool done: Hosted Math [calculator]",
    meta: {
      tool: {
        name: "custom_math_runner",
        label: "Hosted Math [calculator]",
        status: "done",
        effective_result_preview_keys: ["result"],
        effective_result_output_keys: ["result", "request_id"],
        output_preview: {
          result: 7,
        },
        output: {
          result: 7,
          request_id: "req-calc-1",
        },
      },
    },
  });

  assert.equal(
    content,
    'Calculated result = 7 (request id req-calc-1).\nPreview: {"result":7}\nOutput: {"result":7,"request_id":"req-calc-1"}',
  );
});

test("resolveTraceStepDisplayContent appends tool registry diagnostics entries", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-tool-registry-diagnostics",
    type: "observation",
    content: "Tool registry diagnostics: source=file_source skipped=1 missing=1",
    meta: {
      tool_registry: {
        provider_source: "file_source",
        has_diagnostics: true,
        skipped_total: 1,
        missing_total: 1,
        total: 2,
        entries: [
          {
            kind: "skipped",
            target: "registry_sources",
            count: 1,
            values: ["planning_suite"],
          },
          {
            kind: "missing",
            target: "registry_files",
            count: 1,
            values: ["/tmp/missing-registry.json"],
          },
        ],
      },
    },
  });

  assert.equal(
    content,
    "Tool registry diagnostics: source=file_source skipped=1 missing=1\nskipped registry sources: planning_suite\nmissing registry files: /tmp/missing-registry.json",
  );
});

test("resolveTraceStepDisplayContent filters safe tool output to effective_result_output_keys subset", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-output-policy-safe-filtered",
    type: "action",
    content: "Tool done: Provider Search",
    meta: {
      tool: {
        name: "provider_search",
        label: "Provider Search",
        status: "done",
        effective_result_preview_keys: ["documents_total"],
        effective_result_output_keys: ["documents_total", "request_id"],
        output_preview: {
          documents_total: 2,
        },
        output: {
          documents_total: 2,
          request_id: "req-1",
          raw_documents: [{ id: "doc-1" }],
        },
      },
    },
  });

  assert.equal(typeof content, "string");
  assert.match(content, /Output: \{"documents_total":2,"request_id":"req-1"\}/);
  assert.doesNotMatch(content, /raw_documents/);
});

test("resolveTraceStepDisplayContent falls back to original content without preview", () => {
  const content = resolveTraceStepDisplayContent({
    id: "step-plain",
    type: "thought",
    content: "plain trace body",
  });

  assert.equal(content, "plain trace body");
});

test("formatTraceStepMetaSubtitle includes tool semantic kind when available", () => {
  const subtitle = formatTraceStepMetaSubtitle(
    {
      id: "step-semantic-kind",
      type: "action",
      content: "Tool done: Provider Search",
      meta: {
        tool: {
          name: "provider_search",
          label: "Provider Search",
          kind: "provider_retrieval",
          semantic_kind: "knowledge_retrieval",
          supports_result_preview: true,
          effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
          status: "done",
        },
      },
    },
    {
      toolLine: (name: string, status: string) => `${name} (${status})`,
      toolRetry: (count: number) => `Retry ${count}`,
      toolError: (message: string) => `Error ${message}`,
      toolPreviewKeys: (keys: string[]) => `Preview ${keys.join(", ")}`,
      toolPreviewDisabled: "Preview disabled",
      toolOutputKeys: (keys: string[]) => `Output ${keys.join(", ")}`,
      ragLine: (count: number, kb?: string) =>
        kb ? `RAG ${count} ${kb}` : `RAG ${count}`,
      model: "Model",
      stepKind: "Step",
      planningProviderUsed: "Planning provider used",
      planningProviderFallback: "Planning provider fallback",
      planningProviderRuleOnly: "Planning provider rule only",
      toolRegistryProfile: "Profile",
      toolRegistrySource: "Source",
      allowedTools: "Allowed",
      tokens: "Tokens",
      promptTokens: "Prompt",
      completionTokens: "Completion",
      cost: "Cost",
      usageSource: "Usage",
      usageSourceProvider: "provider",
      usageSourceEstimated: "estimated",
      usageSourceLegacy: "legacy",
    },
  );

  assert.equal(
    subtitle,
    "Provider Search (done) [knowledge_retrieval] · Preview hit_count, knowledge_base_id",
  );
});

test("formatTraceStepMetaSubtitle includes tool preview policy when available", () => {
  const subtitle = formatTraceStepMetaSubtitle(
    {
      id: "step-preview-policy",
      type: "action",
      content: "Tool running: Provider Search",
      meta: {
        tool: {
          name: "provider_search",
          label: "Provider Search",
          kind: "provider_retrieval",
          semantic_kind: "knowledge_retrieval",
          supports_result_preview: true,
          effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
          status: "running",
        },
      },
    },
    {
      toolLine: (name: string, status: string) => `${name} (${status})`,
      toolRetry: (count: number) => `Retry ${count}`,
      toolError: (message: string) => `Error ${message}`,
      toolPreviewKeys: (keys: string[]) => `Preview ${keys.join(", ")}`,
      toolPreviewDisabled: "Preview disabled",
      toolOutputKeys: (keys: string[]) => `Output ${keys.join(", ")}`,
      ragLine: (count: number, kb?: string) =>
        kb ? `RAG ${count} ${kb}` : `RAG ${count}`,
      model: "Model",
      stepKind: "Step",
      planningProviderUsed: "Planning provider used",
      planningProviderFallback: "Planning provider fallback",
      planningProviderRuleOnly: "Planning provider rule only",
      toolRegistryProfile: "Profile",
      toolRegistrySource: "Source",
      allowedTools: "Allowed",
      tokens: "Tokens",
      promptTokens: "Prompt",
      completionTokens: "Completion",
      cost: "Cost",
      usageSource: "Usage",
      usageSourceProvider: "provider",
      usageSourceEstimated: "estimated",
      usageSourceLegacy: "legacy",
    },
  );

  assert.equal(
    subtitle,
    "Provider Search (running) [knowledge_retrieval] · Preview hit_count, knowledge_base_id",
  );
});

test("formatTraceStepMetaSubtitle includes tool output policy when available", () => {
  const subtitle = formatTraceStepMetaSubtitle(
    {
      id: "step-output-policy",
      type: "action",
      content: "Tool done: Provider Search",
      meta: {
        tool: {
          name: "provider_search",
          label: "Provider Search",
          kind: "provider_retrieval",
          semantic_kind: "provider_search",
          semantic_family: "knowledge_retrieval",
          supports_result_preview: true,
          effective_result_preview_keys: ["documents_total"],
          effective_result_output_keys: ["documents_total"],
          status: "done",
        },
      },
    },
    {
      toolLine: (name: string, status: string) => `${name} (${status})`,
      toolRetry: (count: number) => `Retry ${count}`,
      toolError: (message: string) => `Error ${message}`,
      toolPreviewKeys: (keys: string[]) => `Preview ${keys.join(", ")}`,
      toolPreviewDisabled: "Preview disabled",
      toolOutputKeys: (keys: string[]) => `Output ${keys.join(", ")}`,
      ragLine: (count: number, kb?: string) =>
        kb ? `RAG ${count} ${kb}` : `RAG ${count}`,
      model: "Model",
      stepKind: "Step",
      planningProviderUsed: "Planning provider used",
      planningProviderFallback: "Planning provider fallback",
      planningProviderRuleOnly: "Planning provider rule only",
      toolRegistryProfile: "Profile",
      toolRegistrySource: "Source",
      allowedTools: "Allowed",
      tokens: "Tokens",
      promptTokens: "Prompt",
      completionTokens: "Completion",
      cost: "Cost",
      usageSource: "Usage",
      usageSourceProvider: "provider",
      usageSourceEstimated: "estimated",
      usageSourceLegacy: "legacy",
    },
  );

  assert.equal(
    subtitle,
    "Provider Search (done) [provider_search · knowledge_retrieval] · Preview documents_total · Output documents_total",
  );
});

test("formatTraceStepMetaSubtitle includes safe execution summary for http_json tools", () => {
  const subtitle = formatTraceStepMetaSubtitle(
    {
      id: "step-execution-summary",
      type: "action",
      content: "Tool running: Provider Search",
      meta: {
        tool: {
          name: "provider_search",
          label: "Provider Search",
          kind: "provider_retrieval",
          semantic_kind: "provider_search",
          semantic_family: "knowledge_retrieval",
          supports_result_preview: true,
          effective_result_preview_keys: ["documents_total"],
          effective_result_output_keys: ["documents_total", "request_id"],
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
          status: "running",
        },
      },
    },
    {
      toolLine: (name: string, status: string) => `${name} (${status})`,
      toolRetry: (count: number) => `Retry ${count}`,
      toolError: (message: string) => `Error ${message}`,
      toolPreviewKeys: (keys: string[]) => `Preview ${keys.join(", ")}`,
      toolPreviewDisabled: "Preview disabled",
      toolOutputKeys: (keys: string[]) => `Output ${keys.join(", ")}`,
      toolExecutionSummary: (summary: string) => `Execution ${summary}`,
      ragLine: (count: number, kb?: string) =>
        kb ? `RAG ${count} ${kb}` : `RAG ${count}`,
      model: "Model",
      stepKind: "Step",
      planningProviderUsed: "Planning provider used",
      planningProviderFallback: "Planning provider fallback",
      planningProviderRuleOnly: "Planning provider rule only",
      toolRegistryProfile: "Profile",
      toolRegistrySource: "Source",
      allowedTools: "Allowed",
      tokens: "Tokens",
      promptTokens: "Prompt",
      completionTokens: "Completion",
      cost: "Cost",
      usageSource: "Usage",
      usageSourceProvider: "provider",
      usageSourceEstimated: "estimated",
      usageSourceLegacy: "legacy",
    },
  );

  assert.equal(
    subtitle,
    "Provider Search (running) [provider_search · knowledge_retrieval] · Preview documents_total · Output documents_total, request_id · Execution POST https://provider.example/search · headers 1 · query 1 · body 2 · response $.data · fields documents_total, request_id",
  );
});

test("getStepTitle uses productized tool title for real tool steps", () => {
  const title = getStepTitle({
    id: "step-productized-title",
    type: "action",
    content: "Tool done: Provider Search",
    meta: {
      tool: {
        name: "provider_search",
        label: "Provider Search",
        kind: "provider_retrieval",
        semantic_kind: "provider_search",
        semantic_family: "knowledge_retrieval",
        status: "done",
      },
    },
  });

  assert.equal(
    title,
    "Provider Search [provider_search · knowledge_retrieval]",
  );
});

test("matchesTraceStepSearchQuery matches safe tool output values beyond preview when output policy is present", () => {
  const step = {
    id: "step-output-policy-search",
    type: "action",
    content: "Tool done: Provider Search",
    meta: {
      tool: {
        name: "provider_search",
        label: "Provider Search",
        status: "done",
        effective_result_preview_keys: ["documents_total"],
        effective_result_output_keys: ["documents_total", "request_id"],
        output_preview: {
          documents_total: 2,
        },
        output: {
          documents_total: 2,
          request_id: "req-1",
        },
      },
    },
  } as const;

  assert.equal(matchesTraceStepSearchQuery(step, "req-1"), true);
  assert.equal(matchesTraceStepSearchQuery(step, "documents_total"), true);
});

test("matchesTraceStepSearchQuery ignores tool output values outside effective_result_output_keys", () => {
  const step = {
    id: "step-output-policy-search-filtered",
    type: "action",
    content: "Tool done: Provider Search",
    meta: {
      tool: {
        name: "provider_search",
        label: "Provider Search",
        status: "done",
        effective_result_preview_keys: ["documents_total"],
        effective_result_output_keys: ["documents_total", "request_id"],
        output_preview: {
          documents_total: 2,
        },
        output: {
          documents_total: 2,
          request_id: "req-1",
          raw_documents: [{ id: "doc-1" }],
        },
      },
    },
  } as const;

  assert.equal(matchesTraceStepSearchQuery(step, "req-1"), true);
  assert.equal(matchesTraceStepSearchQuery(step, "raw_documents"), false);
  assert.equal(matchesTraceStepSearchQuery(step, "doc-1"), false);
});

test("matchesTraceStepSearchQuery matches tool registry diagnostics entry values", () => {
  const step = {
    id: "step-tool-registry-diagnostics-search",
    type: "observation",
    content: "Tool registry diagnostics: source=file_source skipped=1 missing=1",
    meta: {
      tool_registry: {
        provider_source: "file_source",
        has_diagnostics: true,
        skipped_total: 1,
        missing_total: 1,
        total: 2,
        entries: [
          {
            kind: "missing",
            target: "registry_files",
            count: 1,
            values: ["/tmp/missing-registry.json"],
          },
        ],
      },
    },
  } as const;

  assert.equal(matchesTraceStepSearchQuery(step, "missing registry files"), true);
  assert.equal(matchesTraceStepSearchQuery(step, "missing-registry.json"), true);
});

test("getStepTitle humanizes unlabeled real tool names for trace steps", () => {
  const title = getStepTitle({
    id: "step-productized-title-unlabeled",
    type: "action",
    content: "Tool done: provider_search",
    meta: {
      tool: {
        name: "provider_search",
        kind: "provider_retrieval",
        semantic_kind: "provider_search",
        semantic_family: "knowledge_retrieval",
        status: "done",
      },
    },
  });

  assert.equal(
    title,
    "Provider Search [provider_search · knowledge_retrieval]",
  );
});

test("getStepTitle infers semantic category for name-only history steps", () => {
  const title = getStepTitle({
    id: "step-productized-title-name-only-planner",
    type: "action",
    content: "Tool done: Hosted Planner",
    meta: {
      tool: {
        name: "hosted_planner",
        label: "Hosted Planner",
        status: "done",
        effective_result_output_keys: ["steps"],
        output: {
          steps: [
            "Analyze request",
            "Synthesize final answer",
          ],
        },
      },
    },
  });

  assert.equal(
    title,
    "Hosted Planner [planner]",
  );
});

test("getStepTitle uses productized title for rag retrieval follow-up steps", () => {
  const title = getStepTitle({
    id: "step-rag-followup-title",
    type: "thought",
    content: "Provider Search returned snippets.",
    meta: {
      step_type: "rag_retrieval",
      rag: {
        chunks: ["alpha", "beta"],
        knowledge_base_id: "demo-kb",
      },
    },
  });

  assert.equal(title, "Knowledge Retrieval Snippets");
});

test("formatTraceStepMetaSubtitle hides raw rag step kind when rag summary is present", () => {
  const subtitle = formatTraceStepMetaSubtitle(
    {
      id: "step-rag-followup-subtitle",
      type: "thought",
      content: "Provider Search returned snippets.",
      meta: {
        step_type: "rag_retrieval",
        rag: {
          chunks: ["alpha", "beta"],
          knowledge_base_id: "demo-kb",
        },
        model: "mock-gpt",
        tokens: 2,
      },
    },
    {
      toolLine: (name: string, status: string) => `${name} (${status})`,
      toolRetry: (count: number) => `Retry ${count}`,
      toolError: (message: string) => `Error ${message}`,
      toolPreviewKeys: (keys: string[]) => `Preview ${keys.join(", ")}`,
      toolPreviewDisabled: "Preview disabled",
      toolOutputKeys: (keys: string[]) => `Output ${keys.join(", ")}`,
      ragLine: (count: number, kb?: string) =>
        kb ? `RAG ${count} ${kb}` : `RAG ${count}`,
      model: "Model",
      stepKind: "Step",
      planningProviderUsed: "Planning provider used",
      planningProviderFallback: "Planning provider fallback",
      planningProviderRuleOnly: "Planning provider rule only",
      toolRegistryProfile: "Profile",
      toolRegistrySource: "Source",
      allowedTools: "Allowed",
      tokens: "Tokens",
      promptTokens: "Prompt",
      completionTokens: "Completion",
      cost: "Cost",
      usageSource: "Usage",
      usageSourceProvider: "provider",
      usageSourceEstimated: "estimated",
      usageSourceLegacy: "legacy",
    },
  );

  assert.equal(subtitle, "RAG 2 demo-kb · Model mock-gpt · Tokens 2");
});

test("formatTraceStepMetaSubtitle humanizes unlabeled real tool names", () => {
  const subtitle = formatTraceStepMetaSubtitle(
    {
      id: "step-unlabeled-preview-policy",
      type: "action",
      content: "Tool running: provider_search",
      meta: {
        tool: {
          name: "provider_search",
          kind: "provider_retrieval",
          semantic_kind: "knowledge_retrieval",
          supports_result_preview: true,
          effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
          status: "running",
        },
      },
    },
    {
      toolLine: (name: string, status: string) => `${name} (${status})`,
      toolRetry: (count: number) => `Retry ${count}`,
      toolError: (message: string) => `Error ${message}`,
      toolPreviewKeys: (keys: string[]) => `Preview ${keys.join(", ")}`,
      toolPreviewDisabled: "Preview disabled",
      toolOutputKeys: (keys: string[]) => `Output ${keys.join(", ")}`,
      ragLine: (count: number, kb?: string) =>
        kb ? `RAG ${count} ${kb}` : `RAG ${count}`,
      model: "Model",
      stepKind: "Step",
      planningProviderUsed: "Planning provider used",
      planningProviderFallback: "Planning provider fallback",
      planningProviderRuleOnly: "Planning provider rule only",
      toolRegistryProfile: "Profile",
      toolRegistrySource: "Source",
      allowedTools: "Allowed",
      tokens: "Tokens",
      promptTokens: "Prompt",
      completionTokens: "Completion",
      cost: "Cost",
      usageSource: "Usage",
      usageSourceProvider: "provider",
      usageSourceEstimated: "estimated",
      usageSourceLegacy: "legacy",
    },
  );

  assert.equal(
    subtitle,
    "Provider Search (running) [knowledge_retrieval] · Preview hit_count, knowledge_base_id",
  );
});

test("formatTraceStepMetaSubtitle infers semantic category for name-only history steps", () => {
  const subtitle = formatTraceStepMetaSubtitle(
    {
      id: "step-name-only-planner-subtitle",
      type: "action",
      content: "Tool done: Hosted Planner",
      meta: {
        tool: {
          name: "hosted_planner",
          label: "Hosted Planner",
          status: "done",
          effective_result_output_keys: ["steps"],
          output: {
            steps: [
              "Analyze request",
              "Synthesize final answer",
            ],
          },
        },
      },
    },
    {
      toolLine: (name: string, status: string) => `${name} (${status})`,
      toolRetry: (count: number) => `Retry ${count}`,
      toolError: (message: string) => `Error ${message}`,
      toolPreviewKeys: (keys: string[]) => `Preview ${keys.join(", ")}`,
      toolPreviewDisabled: "Preview disabled",
      toolOutputKeys: (keys: string[]) => `Output ${keys.join(", ")}`,
      ragLine: (count: number, kb?: string) =>
        kb ? `RAG ${count} ${kb}` : `RAG ${count}`,
      model: "Model",
      stepKind: "Step",
      planningProviderUsed: "Planning provider used",
      planningProviderFallback: "Planning provider fallback",
      planningProviderRuleOnly: "Planning provider rule only",
      toolRegistryProfile: "Profile",
      toolRegistrySource: "Source",
      allowedTools: "Allowed",
      tokens: "Tokens",
      promptTokens: "Prompt",
      completionTokens: "Completion",
      cost: "Cost",
      usageSource: "Usage",
      usageSourceProvider: "provider",
      usageSourceEstimated: "estimated",
      usageSourceLegacy: "legacy",
    },
  );

  assert.equal(
    subtitle,
    "Hosted Planner (done) [planner] · Output steps",
  );
});

test("filterTraceSteps matches real tool semantic family and output keys", () => {
  const filtered = filterTraceSteps(
    [
      {
        id: "step-provider-search",
        type: "action",
        content: "Tool done: Provider Search",
        meta: {
          tool: {
            name: "provider_search",
            label: "Provider Search",
            kind: "provider_retrieval",
            semantic_kind: "provider_search",
            semantic_family: "knowledge_retrieval",
            supports_result_preview: true,
            effective_result_preview_keys: ["documents_total"],
            effective_result_output_keys: ["documents_total"],
            status: "done",
          },
        },
      },
      {
        id: "step-calculator",
        type: "action",
        content: "Tool done: Calculator",
        meta: {
          tool: {
            name: "calc_eval",
            label: "Calculator",
            kind: "local_calculator",
            semantic_kind: "local_calculator",
            supports_result_preview: true,
            effective_result_preview_keys: ["expression", "result"],
            effective_result_output_keys: ["expression", "result"],
            status: "done",
          },
        },
      },
    ],
    {
      kindFilter: "all",
      searchQuery: "documents_total",
    },
  );

  assert.deepEqual(filtered.map((step) => step.id), ["step-provider-search"]);
});

test("filterTraceSteps applies shared semantic and kind filters", () => {
  const filtered = filterTraceSteps(
    [
      {
        id: "step-provider-search",
        type: "action",
        content: "Tool done: Provider Search",
        meta: {
          tool: {
            name: "provider_search",
            label: "Provider Search",
            kind: "provider_retrieval",
            semantic_kind: "provider_search",
            semantic_family: "knowledge_retrieval",
            status: "done",
          },
        },
      },
      {
        id: "step-rag-followup",
        type: "thought",
        content: "Retrieved snippets",
        meta: {
          rag: {
            chunks: ["alpha"],
            knowledge_base_id: "demo-kb",
          },
        },
      },
      {
        id: "step-calculator",
        type: "action",
        content: "Tool done: Calculator",
        meta: {
          tool: {
            name: "calc_eval",
            label: "Calculator",
            kind: "local_calculator",
            semantic_kind: "local_calculator",
            status: "done",
          },
        },
      },
    ],
    {
      kindFilter: "rag",
      semanticFilter: "retrieval",
      searchQuery: "demo-kb",
    },
  );

  assert.deepEqual(filtered.map((step) => step.id), ["step-rag-followup"]);
});

test("filterTraceSteps matches failure semantic hints", () => {
  const filtered = filterTraceSteps(
    [
      {
        id: "step-ok",
        type: "thought",
        content: "Plan looks good",
        seq: 1,
        meta: null,
      },
      {
        id: "step-error-event",
        type: "observation",
        content: "Remote failed",
        seq: 2,
        meta: {
          error_event: {
            code: "remote_error",
            message: "upstream timeout",
          },
        },
      },
      {
        id: "step-tool-error",
        type: "action",
        content: "Tool call failed",
        seq: 3,
        meta: {
          tool: {
            name: "provider_search",
            status: "error",
          },
        },
      },
      {
        id: "step-rate-limited-code",
        type: "observation",
        content: "remote_provider_rate_limited",
        seq: 4,
        meta: null,
      },
    ],
    {
      semanticFilter: "failure",
    },
  );

  assert.deepEqual(
    filtered.map((step) => step.id),
    ["step-error-event", "step-tool-error", "step-rate-limited-code"],
  );
  assert.equal(
    matchesTraceStepSemanticFilter(
      {
        id: "step-content-timeout",
        type: "observation",
        content: "request timeout while reading response",
        meta: null,
      },
      "failure",
    ),
    true,
  );
});

test("matchesTraceStepSearchQuery matches preview policy keys for running tool steps", () => {
  const matches = matchesTraceStepSearchQuery(
    {
      id: "step-running-preview-policy",
      type: "action",
      content: "Tool running: Provider Search",
      meta: {
        tool: {
          name: "provider_search",
          label: "Provider Search",
          kind: "provider_retrieval",
          semantic_kind: "knowledge_retrieval",
          supports_result_preview: true,
          effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
          status: "running",
        },
      },
    },
    "knowledge_base_id",
  );

  assert.equal(matches, true);
});

test("matchesTraceStepSearchQuery matches rag version metadata", () => {
  const step = {
    id: "rag-version-step",
    type: "thought",
    content: "Knowledge Retrieval returned snippets.",
    meta: {
      rag: {
        knowledge_base_id: "kb-provider",
        chunks: ["Versioned safe snippet"],
        chunk_metadata: [
          {
            source: "handbook.md?[redacted]",
            document_id: "doc-1",
            document_version: "sha256:aaaaaaaaaaaaaaaa",
            content_hash:
              "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
          },
        ],
        document_versions: [
          {
            document_version: "sha256:aaaaaaaaaaaaaaaa",
            content_hash:
              "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            source: "handbook.md?[redacted]",
            document_id: "doc-1",
            chunk_count: 1,
          },
        ],
      },
    },
  };

  assert.equal(matchesTraceStepSearchQuery(step, "sha256:aaaaaaaa"), true);
  assert.equal(matchesTraceStepSearchQuery(step, "handbook.md"), true);
});

test("matchesTraceStepSearchQuery matches output policy keys for tool steps", () => {
  const matches = matchesTraceStepSearchQuery(
    {
      id: "step-output-policy-search",
      type: "action",
      content: "Tool done: Provider Search",
      meta: {
        tool: {
          name: "provider_search",
          label: "Provider Search",
          kind: "provider_retrieval",
          semantic_kind: "provider_search",
          supports_result_preview: true,
          effective_result_preview_keys: ["documents_total"],
          effective_result_output_keys: ["documents_total"],
          status: "done",
        },
      },
    },
    "documents_total",
  );

  assert.equal(matches, true);
});

test("matchesTraceStepSearchQuery matches execution summary fields for http_json tools", () => {
  const matches = matchesTraceStepSearchQuery(
    {
      id: "step-execution-summary-search",
      type: "action",
      content: "Tool running: Provider Search",
      meta: {
        tool: {
          name: "provider_search",
          label: "Provider Search",
          kind: "provider_retrieval",
          semantic_kind: "provider_search",
          semantic_family: "knowledge_retrieval",
          supports_result_preview: true,
          execution_kind: "http_json",
          execution_summary: {
            method: "POST",
            url_origin: "https://provider.example",
            url_path: "/search",
            result_field_names: ["documents_total", "request_id"],
          },
          status: "running",
        },
      },
    },
    "provider.example/search",
  );

  assert.equal(matches, true);
});

test("formatTraceStepMetaSubtitle includes execution diagnostics for invalid real tools", () => {
  const subtitle = formatTraceStepMetaSubtitle(
    {
      id: "step-execution-diagnostics-subtitle",
      type: "action",
      content: "Tool error: Provider Calculator",
      meta: {
        tool: {
          name: "calc_eval",
          label: "Provider Calculator",
          kind: "provider_calc",
          semantic_kind: "local_calculator",
          execution_diagnostics: [
            "unsupported tool execution kind unsupported_transport",
          ],
          status: "error",
          error: "Unsupported tool execution kind: unsupported_transport",
        },
      },
    },
    {
      toolLine: (name: string, status: string) => `${name} (${status})`,
      toolRetry: (count: number) => `Retry ${count}`,
      toolError: (message: string) => `Error ${message}`,
      toolPreviewKeys: (keys: string[]) => `Preview ${keys.join(", ")}`,
      toolPreviewDisabled: "Preview disabled",
      toolOutputKeys: (keys: string[]) => `Output ${keys.join(", ")}`,
      toolExecutionSummary: (summary: string) => `Execution ${summary}`,
      toolExecutionDiagnostics: (summary: string) => `Diagnostics ${summary}`,
      ragLine: (count: number, kb?: string) =>
        kb ? `RAG ${count} ${kb}` : `RAG ${count}`,
      model: "Model",
      stepKind: "Step",
      planningProviderUsed: "Planning provider used",
      planningProviderFallback: "Planning provider fallback",
      planningProviderRuleOnly: "Planning provider rule only",
      toolRegistryProfile: "Profile",
      toolRegistrySource: "Source",
      allowedTools: "Allowed",
      tokens: "Tokens",
      promptTokens: "Prompt",
      completionTokens: "Completion",
      cost: "Cost",
      usageSource: "Usage",
      usageSourceProvider: "provider",
      usageSourceEstimated: "estimated",
      usageSourceLegacy: "legacy",
    },
  );

  assert.match(
    subtitle,
    /Diagnostics unsupported tool execution kind unsupported_transport/,
  );
});

test("matchesTraceStepSearchQuery matches execution diagnostics for invalid real tools", () => {
  const matches = matchesTraceStepSearchQuery(
    {
      id: "step-execution-diagnostics-search",
      type: "action",
      content: "Tool error: Provider Calculator",
      meta: {
        tool: {
          name: "calc_eval",
          label: "Provider Calculator",
          kind: "provider_calc",
          semantic_kind: "local_calculator",
          execution_diagnostics: [
            "unsupported tool execution kind unsupported_transport",
          ],
          status: "error",
        },
      },
    },
    "unsupported_transport",
  );

  assert.equal(matches, true);
});

test("matchesTraceStepSearchQuery matches derived semantic category for name-only history steps", () => {
  const plannerMatches = matchesTraceStepSearchQuery(
    {
      id: "step-name-only-planner-search",
      type: "action",
      content: "Tool done: Hosted Planner",
      meta: {
        tool: {
          name: "hosted_planner",
          label: "Hosted Planner",
          status: "done",
          effective_result_output_keys: ["steps"],
          output: {
            steps: [
              "Analyze request",
              "Synthesize final answer",
            ],
          },
        },
      },
    },
    "planner",
  );
  const calculatorMatches = matchesTraceStepSearchQuery(
    {
      id: "step-name-only-calc-search",
      type: "action",
      content: "Tool done: Hosted Math",
      meta: {
        tool: {
          name: "hosted_math",
          label: "Hosted Math",
          status: "done",
          effective_result_output_keys: ["result", "request_id"],
          output: {
            result: 7,
            request_id: "req-calc-1",
          },
        },
      },
    },
    "calculator",
  );

  assert.equal(plannerMatches, true);
  assert.equal(calculatorMatches, true);
});

test("matchesTraceStepSemanticFilter matches retrieval tool and rag follow-up", () => {
  const retrievalToolMatches = matchesTraceStepSemanticFilter(
    {
      id: "step-retrieval-tool",
      type: "action",
      content: "Tool done: Provider Search",
      meta: {
        tool: {
          name: "provider_search",
          label: "Provider Search",
          kind: "provider_retrieval",
          semantic_kind: "provider_search",
          semantic_family: "knowledge_retrieval",
          status: "done",
        },
      },
    },
    "retrieval",
  );
  const ragMatches = matchesTraceStepSemanticFilter(
    {
      id: "step-rag-followup",
      type: "thought",
      content: "Provider Search returned snippets.",
      meta: {
        rag: {
          chunks: ["alpha", "beta"],
          knowledge_base_id: "demo-kb",
        },
      },
    },
    "retrieval",
  );

  assert.equal(retrievalToolMatches, true);
  assert.equal(ragMatches, true);
});

test("matchesTraceStepSemanticFilter infers retrieval and calculator categories for name-only real tool history steps", () => {
  const retrievalMatches = matchesTraceStepSemanticFilter(
    {
      id: "step-name-only-retrieval",
      type: "action",
      content: "Tool done: Hosted Search",
      meta: {
        tool: {
          name: "hosted_search",
          label: "Hosted Search",
          status: "done",
          effective_result_output_keys: ["documents_total", "request_id"],
          output: {
            documents_total: 2,
            request_id: "req-1",
          },
        },
      },
    },
    "retrieval",
  );
  const calculatorMatches = matchesTraceStepSemanticFilter(
    {
      id: "step-name-only-calc",
      type: "action",
      content: "Tool done: Hosted Math",
      meta: {
        tool: {
          name: "hosted_math",
          label: "Hosted Math",
          status: "done",
          effective_result_output_keys: ["result", "request_id"],
          output: {
            result: 7,
            request_id: "req-calc-1",
          },
        },
      },
    },
    "calculator",
  );

  assert.equal(retrievalMatches, true);
  assert.equal(calculatorMatches, true);
});

test("matchesTraceStepSemanticFilter infers categories for productized bracket labels without semantic hints", () => {
  const retrievalMatches = matchesTraceStepSemanticFilter(
    {
      id: "step-productized-retrieval-label",
      type: "action",
      content: "Tool done: Provider Search [retrieval]",
      meta: {
        tool: {
          name: "custom_provider_search",
          label: "Provider Search [retrieval]",
          status: "done",
          output_preview: {
            documents_total: 2,
          },
          output: {
            documents_total: 2,
            request_id: "req-1",
          },
        },
      },
    },
    "retrieval",
  );
  const calculatorMatches = matchesTraceStepSemanticFilter(
    {
      id: "step-productized-calculator-label",
      type: "action",
      content: "Tool done: Hosted Math [calculator]",
      meta: {
        tool: {
          name: "custom_math_runner",
          label: "Hosted Math [calculator]",
          status: "done",
          output_preview: {
            result: 7,
          },
          output: {
            result: 7,
            request_id: "req-calc-1",
          },
        },
      },
    },
    "calculator",
  );

  assert.equal(retrievalMatches, true);
  assert.equal(calculatorMatches, true);
});

test("matchesTraceStepSemanticFilter infers planner category for name-only planner history steps", () => {
  const plannerMatches = matchesTraceStepSemanticFilter(
    {
      id: "step-name-only-planner",
      type: "action",
      content: "Tool done: Hosted Planner",
      meta: {
        tool: {
          name: "hosted_planner",
          label: "Hosted Planner",
          status: "done",
          effective_result_output_keys: ["steps"],
          output: {
            steps: [
              "Analyze request",
              "Synthesize final answer",
            ],
          },
        },
      },
    },
    "planner",
  );

  assert.equal(plannerMatches, true);
});

test("resolveTraceStepSemanticStats counts planner retrieval and calculator traces", () => {
  const stats = resolveTraceStepSemanticStats([
    {
      id: "step-planner",
      type: "action",
      content: "Tool done: Task Planner",
      meta: {
        tool: {
          name: "task_plan",
          label: "Task Planner",
          kind: "task_planner",
          semantic_kind: "task_planner",
          status: "done",
        },
      },
    },
    {
      id: "step-retrieval",
      type: "action",
      content: "Tool done: Provider Search",
      meta: {
        tool: {
          name: "provider_search",
          label: "Provider Search",
          kind: "provider_retrieval",
          semantic_kind: "provider_search",
          semantic_family: "knowledge_retrieval",
          status: "done",
        },
      },
    },
    {
      id: "step-rag",
      type: "thought",
      content: "Retrieved snippets",
      meta: {
        rag: {
          chunks: ["alpha"],
          knowledge_base_id: "demo-kb",
        },
      },
    },
    {
      id: "step-calculator",
      type: "action",
      content: "Tool done: Calculator",
      meta: {
        tool: {
          name: "calc_eval",
          label: "Calculator",
          kind: "local_calculator",
          semantic_kind: "local_calculator",
          status: "done",
        },
      },
    },
  ]);

  assert.deepEqual(stats, {
    planner: 1,
    retrieval: 2,
    calculator: 1,
    failure: 0,
  });
});

test("resolveTraceStepSemanticStats counts name-only real retrieval and calc steps without semantic hints", () => {
  const stats = resolveTraceStepSemanticStats([
    {
      id: "step-name-only-retrieval",
      type: "action",
      content: "Tool done: Hosted Search",
      meta: {
        tool: {
          name: "hosted_search",
          label: "Hosted Search",
          status: "done",
          effective_result_output_keys: ["documents_total", "request_id"],
          output: {
            documents_total: 2,
            request_id: "req-1",
          },
        },
      },
    },
    {
      id: "step-name-only-calc",
      type: "action",
      content: "Tool done: Hosted Math",
      meta: {
        tool: {
          name: "hosted_math",
          label: "Hosted Math",
          status: "done",
          effective_result_output_keys: ["result", "request_id"],
          output: {
            result: 7,
            request_id: "req-calc-1",
          },
        },
      },
    },
  ]);

  assert.deepEqual(stats, {
    planner: 0,
    retrieval: 1,
    calculator: 1,
    failure: 0,
  });
});

test("resolveTraceStepSemanticStats counts local retrieval steps once without virtual observations", () => {
  const stats = resolveTraceStepSemanticStats([
    {
      id: "step-local-retrieval",
      type: "action",
      content: "Tool done: Knowledge Retrieval",
      meta: {
        tool: {
          name: "task_retrieve",
          label: "Knowledge Retrieval",
          kind: "knowledge_retrieval",
          semantic_kind: "knowledge_retrieval",
          status: "done",
          effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
          output_preview: {
            hit_count: 0,
            knowledge_base_id: "detail-check",
          },
        },
      },
    },
  ]);

  assert.deepEqual(stats, {
    planner: 0,
    retrieval: 1,
    calculator: 0,
    failure: 0,
  });
});

test("resolveTraceStepSemanticStats matches retrieval semantic filter count", () => {
  const steps = [
    {
      id: "step-local-retrieval",
      type: "action" as const,
      content: "Tool done: Knowledge Retrieval",
      meta: {
        tool: {
          name: "task_retrieve",
          label: "Knowledge Retrieval",
          kind: "knowledge_retrieval",
          semantic_kind: "knowledge_retrieval",
          status: "done",
          effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
          output_preview: {
            hit_count: 0,
            knowledge_base_id: "detail-check",
          },
        },
      },
    },
  ];

  assert.equal(
    resolveTraceStepSemanticStats(steps).retrieval,
    filterTraceSteps(steps, { semanticFilter: "retrieval" }).length,
  );
});

test("resolveTraceStepSemanticStats counts name-only planner steps without semantic hints", () => {
  const stats = resolveTraceStepSemanticStats([
    {
      id: "step-name-only-planner",
      type: "action",
      content: "Tool done: Hosted Planner",
      meta: {
        tool: {
          name: "hosted_planner",
          label: "Hosted Planner",
          status: "done",
          effective_result_output_keys: ["steps"],
          output: {
            steps: [
              "Analyze request",
              "Synthesize final answer",
            ],
          },
        },
      },
    },
  ]);

  assert.deepEqual(stats, {
    planner: 1,
    retrieval: 0,
    calculator: 0,
    failure: 0,
  });
});

test("resolveTaskSnapshotSummary carries semantic stats for task detail snapshots", () => {
  const summary = resolveTaskSnapshotSummary({
    task: {
      id: "task-semantic-summary",
      session_id: "session-semantic-summary",
      prompt: "Summarize tool semantics",
      status: "completed",
      trace_json: null,
      created_at: "2026-06-27T00:00:00Z",
      updated_at: "2026-06-27T00:00:01Z",
    },
    traceSteps: [
      {
        id: "step-planner",
        type: "action",
        content: "Tool done: Task Planner",
        meta: {
          tool: {
            name: "task_plan",
            label: "Task Planner",
            kind: "task_planner",
            semantic_kind: "task_planner",
            status: "done",
          },
        },
      },
      {
        id: "step-retrieval",
        type: "action",
        content: "Tool done: Provider Search",
        meta: {
        tool: {
          name: "provider_search",
          label: "Provider Search",
          kind: "provider_retrieval",
          semantic_kind: "provider_search",
          semantic_family: "knowledge_retrieval",
          status: "done",
        },
      },
      },
      {
        id: "step-rag",
        type: "thought",
        content: "Retrieved snippets",
        meta: {
          rag: {
            chunks: ["alpha"],
            knowledge_base_id: "demo-kb",
          },
        },
      },
      {
        id: "step-calculator",
        type: "action",
        content: "Tool done: Calculator",
        meta: {
          tool: {
            name: "calc_eval",
            label: "Calculator",
            kind: "local_calculator",
            semantic_kind: "local_calculator",
            status: "done",
          },
        },
      },
    ],
  });

  assert.deepEqual(summary.semanticStats, {
    planner: 1,
    retrieval: 2,
    calculator: 1,
    failure: 0,
  });
});

test("resolveTaskStreamTerminalReason maps active terminal task status to local stream completion reason", () => {
  assert.equal(
    resolveTaskStreamTerminalReason({
      task: {
        id: "task-cancelled",
        status: "cancelled",
        status_normalized: "cancelled",
      },
      activeTaskId: "task-cancelled",
      isStreaming: true,
    }),
    "cancelled",
  );
  assert.equal(
    resolveTaskStreamTerminalReason({
      task: {
        id: "task-running",
        status: "running",
        status_normalized: "running",
      },
      activeTaskId: "task-running",
      isStreaming: true,
    }),
    null,
  );
  assert.equal(
    resolveTaskStreamTerminalReason({
      task: {
        id: "task-other",
        status: "cancelled",
        status_normalized: "cancelled",
      },
      activeTaskId: "task-current",
      isStreaming: true,
    }),
    null,
  );
  assert.equal(
    resolveTaskStreamTerminalReason({
      task: {
        id: "task-completed",
        status: "completed",
        status_normalized: "completed",
      },
      activeTaskId: "task-completed",
      isStreaming: true,
    }),
    "done",
  );
});

test("resolveTaskSnapshotSummary prefers final answer over last observation in task snapshots", () => {
  const summary = resolveTaskSnapshotSummary({
    task: {
      id: "task-final-answer-priority",
      session_id: "session-final-answer-priority",
      prompt: "Need a final answer",
      status: "completed",
      trace_json: null,
      created_at: "2026-06-30T00:00:00Z",
      updated_at: "2026-06-30T00:00:01Z",
    },
    traceSteps: [
      {
        id: "step-observation",
        type: "observation",
        content: "Provider Search: Retrieved 2 documents (request id req-1).",
      },
      {
        id: "step-final-answer",
        type: "other",
        content: "Summary: Retrieved 2 documents and synthesized final answer.",
      },
    ],
  });

  assert.equal(
    summary.finalAnswer,
    "Summary: Retrieved 2 documents and synthesized final answer.",
  );
  assert.equal(
    summary.lastObservation,
    "Provider Search: Retrieved 2 documents (request id req-1).",
  );
});

test("resolveTaskSnapshotSummary extracts terminal failure hints from trace diagnostics", () => {
  const summary = resolveTaskSnapshotSummary({
    task: {
      id: "task-failure-hint",
      session_id: "session-failure-hint",
      prompt: "Need a failure hint",
      status: "failed",
      trace_json: null,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:01Z",
    },
    traceSteps: [
      {
        id: "step-observation",
        type: "observation",
        content: "Retrieved 2 documents before failure.",
      },
      {
        id: "step-tool-error",
        type: "action",
        content: "Tool error: Provider Search",
        meta: {
          tool: {
            name: "provider_search",
            label: "Provider Search",
            status: "error",
            error: "upstream timed out after 30s",
          },
        },
      },
      {
        id: "step-error-event",
        type: "other",
        content: "Task failed",
        meta: {
          error_event: {
            code: "tool_execution_error",
            message: "provider_search exhausted retries",
          },
        },
      },
    ],
  });

  assert.equal(
    summary.failureHint,
    "provider_search exhausted retries",
  );
  assert.equal(summary.failureSource, "error_event");
});

test("resolveTaskSnapshotSummary prefers legacy failure diagnostics over neutral persisted steps", () => {
  const summary = resolveTaskSnapshotSummary({
    task: {
      id: "task-legacy-failure-priority",
      session_id: "session-legacy-failure-priority",
      prompt: "trigger remote network error",
      status: "failed",
      trace_json: JSON.stringify([
        {
          id: "legacy-error-event",
          type: "other",
          content: "Task failed",
          meta: {
            error_event: {
              code: "remote_provider_network_error",
              message: "Failed to reach remote provider",
            },
          },
        },
        {
          id: "legacy-tool-done",
          type: "action",
          content: "Tool done: Task Planner",
          meta: {
            tool: {
              name: "task_plan",
              label: "Task Planner",
              status: "done",
            },
          },
        },
      ]),
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:01Z",
    },
    traceSteps: [
      {
        id: "persisted-tool-done",
        type: "action",
        content: "Tool done: Task Planner",
        meta: {
          tool: {
            name: "task_plan",
            label: "Task Planner",
            status: "done",
          },
        },
      },
    ],
  });

  assert.equal(summary.failureHint, "Failed to reach remote provider");
  assert.equal(summary.failureSource, "error_event");
});

test("resolveTaskSnapshotSummary prefers explicit task failure hints over neutral persisted steps", () => {
  const summary = resolveTaskSnapshotSummary({
    task: {
      id: "task-explicit-failure-priority",
      session_id: "session-explicit-failure-priority",
      prompt: "trigger remote network error",
      status: "failed",
      trace_json: JSON.stringify([
        {
          id: "legacy-tool-done",
          type: "action",
          content: "Tool done: Task Planner",
        },
      ]),
      failure_hint: "Failed to reach remote provider",
      failure_source: "error_event",
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:01Z",
    },
    traceSteps: [
      {
        id: "persisted-tool-done",
        type: "action",
        content: "Tool done: Task Planner",
      },
    ],
  });

  assert.equal(summary.failureHint, "Failed to reach remote provider");
  assert.equal(summary.failureSource, "error_event");
});

test("resolveTaskSnapshotSummary can use a mapped explicit task failure hint", () => {
  const summary = resolveTaskSnapshotSummary({
    task: {
      id: "task-explicit-failure-code-priority",
      session_id: "session-explicit-failure-code-priority",
      prompt: "trigger remote network error",
      status: "failed",
      trace_json: JSON.stringify([
        {
          id: "persisted-summary",
          type: "other",
          content: "Failed to reach remote provider. Check network or base URL.",
        },
      ]),
      failure_hint: "remote_provider_network_error",
      failure_source: "error_event",
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:01Z",
    },
    traceSteps: [
      {
        id: "persisted-summary",
        type: "other",
        content: "Failed to reach remote provider. Check network or base URL.",
      },
    ],
    explicitFailureHint: "Failed to reach remote provider. Check network or base URL.",
  });

  assert.equal(
    summary.failureHint,
    "Failed to reach remote provider. Check network or base URL.",
  );
  assert.equal(summary.failureSource, "error_event");
});

test("resolveTaskSnapshotSummary keeps failure diagnostics for normalized failed status", () => {
  const summary = resolveTaskSnapshotSummary({
    task: {
      id: "task-normalized-failure-hint",
      session_id: "session-normalized-failure-hint",
      prompt: "trigger normalized remote network error",
      status: "completed",
      status_normalized: "failed",
      status_label: "Failed",
      trace_json: null,
      failure_hint: "Failed to reach remote provider",
      failure_source: "error_event",
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:01Z",
    },
    traceSteps: [
      {
        id: "step-generic-failure-content",
        type: "other",
        content: "Task failed after replaying the original prompt",
      },
    ],
  });

  assert.equal(summary.failureHint, "Failed to reach remote provider");
  assert.equal(summary.failureSource, "error_event");
});

test("resolveTaskSnapshotSummary classifies tool failure hints", () => {
  const summary = resolveTaskSnapshotSummary({
    task: {
      id: "task-tool-failure-source",
      session_id: "session-tool-failure-source",
      prompt: "Need a tool failure source",
      status: "failed",
      trace_json: null,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:01Z",
    },
    traceSteps: [
      {
        id: "step-tool-error",
        type: "action",
        content: "Tool error: Provider Search",
        meta: {
          tool: {
            name: "provider_search",
            label: "Provider Search",
            status: "error",
            error: "upstream timed out after 30s",
          },
        },
      },
    ],
  });

  assert.equal(summary.failureHint, "upstream timed out after 30s");
  assert.equal(summary.failureSource, "tool_error");
});

test("matchesTaskObservabilityFilter groups failed status, failure hints and failure traces", () => {
  const baseTask = {
    id: "task-observability",
    session_id: "session-observability",
    prompt: "Need observability filtering",
    status: "completed",
    trace_json: null,
    created_at: "2026-08-14T00:00:00Z",
    updated_at: "2026-08-14T00:00:01Z",
  };
  const cleanSnapshot = resolveTaskSnapshotSummary({
    task: baseTask,
    traceSteps: [
      {
        id: "step-final",
        type: "other",
        content: "Summary: completed successfully.",
      },
    ],
  });
  const failedStatusTask = {
    ...baseTask,
    id: "task-failed-status",
    status: "failed",
  };
  const failureHintSnapshot = resolveTaskSnapshotSummary({
    task: {
      ...baseTask,
      id: "task-failure-hint-filter",
      status: "failed",
    },
    traceSteps: [
      {
        id: "step-error-event",
        type: "other",
        content: "Task failed",
        meta: {
          error_event: {
            message: "provider_search exhausted retries",
          },
        },
      },
    ],
  });
  const failureTraceSnapshot = resolveTaskSnapshotSummary({
    task: {
      ...baseTask,
      id: "task-failure-trace-filter",
      status: "completed",
    },
    traceSteps: [
      {
        id: "step-tool-error",
        type: "action",
        content: "Tool call failed",
        meta: {
          tool: {
            name: "provider_search",
            status: "error",
          },
        },
      },
    ],
  });

  assert.equal(
    matchesTaskObservabilityFilter(baseTask, cleanSnapshot, "attention"),
    false,
  );
  assert.equal(
    matchesTaskObservabilityFilter(failedStatusTask, cleanSnapshot, "attention"),
    true,
  );
  assert.equal(
    matchesTaskObservabilityFilter(baseTask, failureHintSnapshot, "failure_hint"),
    true,
  );
  assert.equal(
    matchesTaskObservabilityFilter(baseTask, failureTraceSnapshot, "failure_trace"),
    true,
  );
  assert.equal(
    matchesTaskObservabilityFilter(baseTask, failureTraceSnapshot, "failure_hint"),
    false,
  );
});

test("matchesTaskStatusFilter prefers normalized task status for Task Center filters", () => {
  const task = {
    status: "completed",
    status_normalized: "failed",
  };

  assert.equal(matchesTaskStatusFilter(task, "all"), true);
  assert.equal(matchesTaskStatusFilter(task, "failed"), true);
  assert.equal(matchesTaskStatusFilter(task, "completed"), false);
});

test("resolveTaskStatusDisplay keeps Task Center status text and tone on normalized status", () => {
  assert.deepEqual(
    resolveTaskStatusDisplay({
      status: "completed",
      status_label: "Completed",
      status_normalized: "failed",
    }),
    {
      label: "failed",
      tone: "failed",
    },
  );
  assert.deepEqual(
    resolveTaskStatusDisplay({
      status: "pending",
      status_label: "Queued for execution",
    }),
    {
      label: "Queued for execution",
      tone: "running",
    },
  );
});

test("resolveTaskCenterOperatorHint gives Task Center local next actions", () => {
  const labels = {
    failureHint: "Open Failure trace and fix the reported source",
    failureTrace: "Review Failure trace before retrying",
    queued: "Watch queue capacity before sending another run",
    running: "Monitor live stream until the task finishes",
  };

  assert.deepEqual(
    resolveTaskCenterOperatorHint({
      task: { status: "completed", status_normalized: "failed" },
      snapshot: {
        failureHint: "remote_provider_network_error",
        semanticStats: {
          planner: 1,
          retrieval: 0,
          calculator: 0,
          failure: 1,
        },
      },
      labels,
    }),
    {
      kind: "failure_hint",
      label: "Open Failure trace and fix the reported source",
    },
  );
  assert.deepEqual(
    resolveTaskCenterOperatorHint({
      task: { status: "completed" },
      snapshot: {
        failureHint: null,
        semanticStats: {
          planner: 1,
          retrieval: 0,
          calculator: 0,
          failure: 1,
        },
      },
      labels,
    }),
    {
      kind: "failure_trace",
      label: "Review Failure trace before retrying",
    },
  );
  assert.deepEqual(
    resolveTaskCenterOperatorHint({
      task: { status: "queued" },
      snapshot: null,
      labels,
    }),
    {
      kind: "queued",
      label: "Watch queue capacity before sending another run",
    },
  );
  assert.deepEqual(
    resolveTaskCenterOperatorHint({
      task: { status: "running" },
      snapshot: null,
      labels,
    }),
    {
      kind: "running",
      label: "Monitor live stream until the task finishes",
    },
  );
  assert.equal(
    resolveTaskCenterOperatorHint({
      task: { status: "completed" },
      snapshot: {
        failureHint: null,
        semanticStats: {
          planner: 0,
          retrieval: 0,
          calculator: 0,
          failure: 0,
        },
      },
      labels,
    }),
    null,
  );
});

test("resolveTaskDetailHrefTraceSemanticFilter keeps failure trace drilldown focus", () => {
  const failureTraceSnapshot = resolveTaskSnapshotSummary({
    task: {
      id: "task-failure-trace-link",
      session_id: "session-failure-trace-link",
      prompt: "Need failure trace detail link",
      status: "completed",
      trace_json: null,
      created_at: "2026-08-14T00:00:00Z",
      updated_at: "2026-08-14T00:00:01Z",
    },
    traceSteps: [
      {
        id: "step-tool-error-link",
        type: "action",
        content: "Provider search failed",
        meta: {
          tool: {
            name: "provider_search",
            status: "error",
          },
        },
      },
    ],
  });

  assert.equal(failureTraceSnapshot.failureHint, null);
  assert.equal(
    resolveTaskDetailHrefTraceSemanticFilter(
      failureTraceSnapshot,
      "failure_trace",
    ),
    "failure",
  );
  assert.equal(
    resolveTaskDetailHrefTraceSemanticFilter(failureTraceSnapshot, "all"),
    null,
  );

  const failureHintSnapshot = resolveTaskSnapshotSummary({
    task: {
      id: "task-failure-hint-link",
      session_id: "session-failure-hint-link",
      prompt: "Need failure hint detail link",
      status: "failed",
      failure_hint: "remote_provider_network_error",
      failure_source: "error_event",
      trace_json: null,
      created_at: "2026-08-14T00:00:00Z",
      updated_at: "2026-08-14T00:00:01Z",
    },
  });

  assert.equal(
    resolveTaskDetailHrefTraceSemanticFilter(failureHintSnapshot, "all"),
    "failure",
  );
});

test("matchesTaskFailureSourceFilter applies local failure source drilldown", () => {
  const snapshot = resolveTaskSnapshotSummary({
    task: {
      id: "task-failure-source-filter",
      session_id: "session-failure-source-filter",
      prompt: "Need failure source filtering",
      status: "failed",
      failure_hint: "remote_provider_network_error",
      failure_source: "error_event",
      trace_json: null,
      created_at: "2026-08-14T00:00:00Z",
      updated_at: "2026-08-14T00:00:01Z",
    },
  });

  assert.equal(matchesTaskFailureSourceFilter(snapshot, "all"), true);
  assert.equal(matchesTaskFailureSourceFilter(snapshot, "error_event"), true);
  assert.equal(matchesTaskFailureSourceFilter(snapshot, "tool_error"), false);
  assert.equal(matchesTaskFailureSourceFilter(null, "error_event"), false);
});

test("matchesTaskGovernanceFilters applies profile and provider source together", () => {
  const snapshot = resolveTaskSnapshotSummary({
    task: {
      id: "task-governance-filter",
      session_id: "session-governance-filter",
      prompt: "Need governance filtering",
      status: "completed",
      trace_json: JSON.stringify([
        {
          id: "step-governance",
          type: "action",
          content: "Tool registry profile prod with remote provider",
          meta: {
            tool_registry_profile: "prod",
            tool_registry_provider_source: "remote",
            allowed_tool_names: ["provider_search"],
            allowed_tool_labels: ["Provider Search"],
          },
        },
      ]),
      created_at: "2026-08-14T00:00:00Z",
      updated_at: "2026-08-14T00:00:01Z",
    },
  });

  assert.equal(
    matchesTaskGovernanceFilters(snapshot, {
      allValue: "__all__",
      profile: "__all__",
      providerSource: "__all__",
    }),
    true,
  );
  assert.equal(
    matchesTaskGovernanceFilters(snapshot, {
      allValue: "__all__",
      profile: "prod",
      providerSource: "remote",
    }),
    true,
  );
  assert.equal(
    matchesTaskGovernanceFilters(snapshot, {
      allValue: "__all__",
      profile: "prod",
      providerSource: "local",
    }),
    false,
  );
  assert.equal(
    matchesTaskGovernanceFilters(null, {
      allValue: "__all__",
      profile: "prod",
      providerSource: "__all__",
    }),
    false,
  );
});

test("formatTraceStepSemanticStatsSummary renders compact planner retrieval calculator counts", () => {
  const content = formatTraceStepSemanticStatsSummary(
    {
      planner: 1,
      retrieval: 2,
      calculator: 0,
      failure: 3,
    },
    {
      planner: "Planner",
      retrieval: "Retrieval",
      calculator: "Calculator",
      failure: "Failure",
    },
  );

  assert.equal(content, "Planner 1 · Retrieval 2 · Calculator 0 · Failure 3");
});
