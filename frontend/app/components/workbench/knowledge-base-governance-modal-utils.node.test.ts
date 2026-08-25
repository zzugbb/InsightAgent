import test from "node:test";
import assert from "node:assert/strict";

import {
  resolveKnowledgeBaseVersionRows,
  summarizeKnowledgeBaseVersions,
} from "./knowledge-base-governance-modal-utils.ts";

test("resolveKnowledgeBaseVersionRows returns stable sorted display rows", () => {
  const rows = resolveKnowledgeBaseVersionRows([
    {
      document_version: "sha256:bbbbbbbbbbbbbbbb",
      content_hash:
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      source: "manual",
      document_id: "release-notes",
      chunk_count: 3,
    },
    {
      document_version: "sha256:aaaaaaaaaaaaaaaa",
      content_hash:
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      source: "api-docs",
      document_id: "auth-guide",
      chunk_count: 1,
    },
  ]);

  assert.deepEqual(
    rows.map((row) => ({
      key: row.key,
      source: row.source,
      documentId: row.documentId,
      versionLabel: row.versionLabel,
      contentHashLabel: row.contentHashLabel,
      chunkCount: row.chunkCount,
    })),
    [
      {
        key: "api-docs::auth-guide::sha256:aaaaaaaaaaaaaaaa",
        source: "api-docs",
        documentId: "auth-guide",
        versionLabel: "sha256:aaaaaaaaaaaaaaaa",
        contentHashLabel: "aaaaaaaaaaaa...",
        chunkCount: 1,
      },
      {
        key: "manual::release-notes::sha256:bbbbbbbbbbbbbbbb",
        source: "manual",
        documentId: "release-notes",
        versionLabel: "sha256:bbbbbbbbbbbbbbbb",
        contentHashLabel: "bbbbbbbbbbbb...",
        chunkCount: 3,
      },
    ],
  );
});

test("summarizeKnowledgeBaseVersions totals documents and chunks", () => {
  assert.deepEqual(
    summarizeKnowledgeBaseVersions([
      {
        document_version: "sha256:aaaaaaaaaaaaaaaa",
        content_hash:
          "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        source: "api-docs",
        document_id: "auth-guide",
        chunk_count: 1,
      },
      {
        document_version: "sha256:bbbbbbbbbbbbbbbb",
        content_hash:
          "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        source: "api-docs",
        document_id: "auth-guide",
        chunk_count: 4,
      },
      {
        document_version: "sha256:cccccccccccccccc",
        content_hash:
          "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        source: "manual",
        document_id: "release-notes",
        chunk_count: 2,
      },
    ]),
    {
      versionCount: 3,
      documentCount: 2,
      chunkCount: 7,
    },
  );
});
