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

test("resolveTraceStepDisplayContent appends tool output preview for action steps", () => {
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
  assert.match(content, /Tool done: Task Planner/);
  assert.match(content, /Analyze request -> Synthesize final answer/);
  assert.match(content, /playwright trace preview content/);
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

test("getStepTitle uses productized title for rag retrieval follow-up steps", () => {
  const title = getStepTitle({
    id: "step-rag-followup-title",
    type: "thought",
    content: "Provider Search returned snippets from the selected knowledge base.",
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
      content: "Provider Search returned snippets from the selected knowledge base.",
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
