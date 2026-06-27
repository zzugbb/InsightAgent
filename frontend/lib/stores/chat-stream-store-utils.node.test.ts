import assert from "node:assert/strict";
import test from "node:test";

import { mergeToolEndToolMeta } from "./chat-stream-store-utils.ts";

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
