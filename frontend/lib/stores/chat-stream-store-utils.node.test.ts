import assert from "node:assert/strict";
import test from "node:test";

import {
  buildLiveToolEndPayload,
  mergeToolEndToolMeta,
  mergeToolStartToolMeta,
} from "./chat-stream-store-utils.ts";

test("buildLiveToolEndPayload keeps result summary from raw tool_end event payload", () => {
  const payload = buildLiveToolEndPayload({
    status: "done",
    retry_count: 0,
    output_preview: {
      documents_total: 2,
    },
    output: {
      documents_total: 2,
      request_id: "req-1",
      raw_documents: [{ id: "doc-1" }],
    },
    result_summary: "Retrieved 2 documents (request id req-1).",
    kind: "provider_retrieval",
    semantic_kind: "provider_search",
    semantic_family: "knowledge_retrieval",
    supports_result_preview: true,
    effective_result_preview_keys: ["documents_total"],
    effective_result_output_keys: ["documents_total", "request_id"],
  });

  assert.equal(payload.result_summary, "Retrieved 2 documents (request id req-1).");
  assert.deepEqual(payload.output_preview, {
    documents_total: 2,
  });
  assert.deepEqual(payload.output, {
    documents_total: 2,
    request_id: "req-1",
    raw_documents: [{ id: "doc-1" }],
  });
});

test("mergeToolEndToolMeta keeps preview separate from raw output", () => {
  const meta = mergeToolEndToolMeta(
    {
      name: "task_retrieve_hot",
      label: "Hot Retrieval",
      input: { query: "demo" },
      status: "running",
    },
    {
      status: "done",
      output_preview: {
        tool_kind: "hot_knowledge_retrieval",
        hit_count: 2,
        knowledge_base_id: "demo-kb",
      },
      retry_count: 0,
    },
    {
      name: "task_retrieve_hot",
      label: "Hot Retrieval",
    },
  );

  assert.equal(meta.output, undefined);
  assert.deepEqual(meta.output_preview, {
    tool_kind: "hot_knowledge_retrieval",
    hit_count: 2,
    knowledge_base_id: "demo-kb",
  });
  assert.equal(meta.status, "done");
});

test("mergeToolEndToolMeta preserves existing raw output when only preview arrives", () => {
  const meta = mergeToolEndToolMeta(
    {
      name: "task_retrieve_hot",
      label: "Hot Retrieval",
      output: {
        tool_kind: "hot_knowledge_retrieval",
        hit_count: 2,
        chunks: ["alpha", "beta"],
        raw_documents: [{ id: "doc-1" }],
      },
      status: "running",
    },
    {
      status: "done",
      output_preview: {
        tool_kind: "hot_knowledge_retrieval",
        hit_count: 2,
      },
      retry_count: 0,
    },
    {
      name: "task_retrieve_hot",
      label: "Hot Retrieval",
    },
  );

  assert.deepEqual(meta.output, {
    tool_kind: "hot_knowledge_retrieval",
    hit_count: 2,
    chunks: ["alpha", "beta"],
    raw_documents: [{ id: "doc-1" }],
  });
  assert.deepEqual(meta.output_preview, {
    tool_kind: "hot_knowledge_retrieval",
    hit_count: 2,
  });
  assert.equal(meta.status, "done");
});

test("mergeToolEndToolMeta keeps runtime semantic metadata from tool_end payload", () => {
  const meta = mergeToolEndToolMeta(
    {
      name: "provider_search",
      label: "Provider Search",
      status: "running",
    },
    {
      status: "done",
      output_preview: {
        hit_count: 2,
        knowledge_base_id: "demo-kb",
      },
      kind: "provider_retrieval",
      semantic_kind: "provider_search",
      semantic_family: "knowledge_retrieval",
      supports_result_preview: true,
      effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
      effective_result_output_keys: ["documents_total"],
      retry_count: 0,
    },
    {
      name: "provider_search",
      label: "Provider Search",
    },
  );

  assert.equal(meta.kind, "provider_retrieval");
  assert.equal(meta.semantic_kind, "provider_search");
  assert.equal(meta.semantic_family, "knowledge_retrieval");
  assert.equal(meta.supports_result_preview, true);
  assert.deepEqual(meta.effective_result_preview_keys, [
    "hit_count",
    "knowledge_base_id",
  ]);
  assert.deepEqual(meta.effective_result_output_keys, ["documents_total"]);
  assert.equal(meta.status, "done");
});

test("mergeToolStartToolMeta keeps execution diagnostics from tool_start payload", () => {
  const meta = mergeToolStartToolMeta(
    {
      name: "calc_eval",
      label: "Provider Calculator",
      status: "running",
    },
    {
      name: "calc_eval",
      input: { expression: "1+2*3" },
      kind: "provider_calc",
      semantic_kind: "local_calculator",
      effective_result_output_keys: ["expression", "result"],
      execution_diagnostics: [
        "unsupported tool execution kind unsupported_transport",
      ],
      retry_count: 0,
    },
    {
      name: "calc_eval",
      label: "Provider Calculator",
    },
  );

  assert.deepEqual(meta.execution_diagnostics, [
    "unsupported tool execution kind unsupported_transport",
  ]);
  assert.equal(meta.status, "running");
});

test("mergeToolEndToolMeta preserves execution diagnostics from tool_end payload", () => {
  const meta = mergeToolEndToolMeta(
    {
      name: "calc_eval",
      label: "Provider Calculator",
      status: "running",
      execution_diagnostics: [
        "unsupported tool execution kind unsupported_transport",
      ],
    },
    {
      status: "error",
      error: "Unsupported tool execution kind: unsupported_transport",
      execution_diagnostics: [
        "unsupported tool execution kind unsupported_transport",
      ],
      retry_count: 0,
    },
    {
      name: "calc_eval",
      label: "Provider Calculator",
    },
  );

  assert.deepEqual(meta.execution_diagnostics, [
    "unsupported tool execution kind unsupported_transport",
  ]);
  assert.equal(meta.status, "error");
});

test("mergeToolEndToolMeta filters output to effective_result_output_keys from tool_end payload", () => {
  const meta = mergeToolEndToolMeta(
    {
      name: "provider_search",
      label: "Provider Search",
      input: { query: "demo" },
      status: "running",
    },
    {
      status: "done",
      output: {
        documents_total: 2,
        request_id: "req-1",
        raw_documents: [{ id: "doc-1" }],
      },
      effective_result_output_keys: ["documents_total", "request_id"],
      retry_count: 0,
    },
    {
      name: "provider_search",
      label: "Provider Search",
    },
  );

  assert.deepEqual(meta.output, {
    documents_total: 2,
    request_id: "req-1",
  });
  assert.equal(meta.status, "done");
});

test("mergeToolEndToolMeta keeps result summary from tool_end payload", () => {
  const meta = mergeToolEndToolMeta(
    {
      name: "provider_search",
      label: "Provider Search",
      input: { query: "demo" },
      status: "running",
    },
    {
      status: "done",
      output: {
        documents_total: 2,
        request_id: "req-1",
      },
      effective_result_output_keys: ["documents_total", "request_id"],
      result_summary: "Retrieved 2 documents (request id req-1).",
      retry_count: 0,
    },
    {
      name: "provider_search",
      label: "Provider Search",
    },
  );

  assert.equal(meta.result_summary, "Retrieved 2 documents (request id req-1).");
  assert.equal(meta.status, "done");
});

test("mergeToolEndToolMeta reuses previous effective_result_output_keys to filter output", () => {
  const meta = mergeToolEndToolMeta(
    {
      name: "provider_search",
      label: "Provider Search",
      input: { query: "demo" },
      effective_result_output_keys: ["documents_total", "request_id"],
      status: "running",
    },
    {
      status: "done",
      output: {
        documents_total: 2,
        request_id: "req-1",
        raw_documents: [{ id: "doc-1" }],
      },
      retry_count: 0,
    },
    {
      name: "provider_search",
      label: "Provider Search",
    },
  );

  assert.deepEqual(meta.output, {
    documents_total: 2,
    request_id: "req-1",
  });
  assert.equal(meta.status, "done");
});

test("mergeToolStartToolMeta keeps runtime semantic metadata from tool_start payload", () => {
  const meta = mergeToolStartToolMeta(
    undefined,
    {
      name: "provider_search",
      input: { query: "demo" },
      retry_count: 0,
      kind: "provider_retrieval",
      semantic_kind: "provider_search",
      semantic_family: "knowledge_retrieval",
      supports_result_preview: true,
      effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
      effective_result_output_keys: ["documents_total"],
    },
    {
      name: "provider_search",
      label: "Provider Search",
    },
  );

  assert.equal(meta.name, "provider_search");
  assert.equal(meta.label, "Provider Search");
  assert.deepEqual(meta.input, { query: "demo" });
  assert.equal(meta.kind, "provider_retrieval");
  assert.equal(meta.semantic_kind, "provider_search");
  assert.equal(meta.semantic_family, "knowledge_retrieval");
  assert.equal(meta.supports_result_preview, true);
  assert.deepEqual(meta.effective_result_preview_keys, [
    "hit_count",
    "knowledge_base_id",
  ]);
  assert.deepEqual(meta.effective_result_output_keys, ["documents_total"]);
  assert.equal(meta.retry_count, 0);
  assert.equal(meta.status, "running");
});
