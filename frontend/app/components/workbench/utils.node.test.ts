import test from "node:test";
import assert from "node:assert/strict";

import {
  formatTraceStepMetaSubtitle,
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

  assert.equal(subtitle, "Provider Search (done) [knowledge_retrieval]");
});
