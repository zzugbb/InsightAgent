import test from "node:test";
import assert from "node:assert/strict";

import {
  filterTraceSteps,
  formatTraceStepSemanticStatsSummary,
  formatTraceStepMetaSubtitle,
  getStepTitle,
  matchesTraceStepSearchQuery,
  matchesTraceStepSemanticFilter,
  resolveTaskSnapshotSummary,
  resolveTraceStepSemanticStats,
  resolveTraceStepDisplayContent,
} from "./utils.ts";

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
  });
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
  });
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

test("formatTraceStepSemanticStatsSummary renders compact planner retrieval calculator counts", () => {
  const content = formatTraceStepSemanticStatsSummary(
    {
      planner: 1,
      retrieval: 2,
      calculator: 0,
    },
    {
      planner: "Planner",
      retrieval: "Retrieval",
      calculator: "Calculator",
    },
  );

  assert.equal(content, "Planner 1 · Retrieval 2 · Calculator 0");
});
