import assert from "node:assert/strict";
import test from "node:test";

import {
  mergeToolEndToolMeta,
  mergeToolStartToolMeta,
} from "./chat-stream-store-utils.ts";

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
      semantic_kind: "knowledge_retrieval",
      supports_result_preview: true,
      effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
      retry_count: 0,
    },
    {
      name: "provider_search",
      label: "Provider Search",
    },
  );

  assert.equal(meta.kind, "provider_retrieval");
  assert.equal(meta.semantic_kind, "knowledge_retrieval");
  assert.equal(meta.supports_result_preview, true);
  assert.deepEqual(meta.effective_result_preview_keys, [
    "hit_count",
    "knowledge_base_id",
  ]);
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
      semantic_kind: "knowledge_retrieval",
      supports_result_preview: true,
      effective_result_preview_keys: ["hit_count", "knowledge_base_id"],
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
  assert.equal(meta.semantic_kind, "knowledge_retrieval");
  assert.equal(meta.supports_result_preview, true);
  assert.deepEqual(meta.effective_result_preview_keys, [
    "hit_count",
    "knowledge_base_id",
  ]);
  assert.equal(meta.retry_count, 0);
  assert.equal(meta.status, "running");
});
