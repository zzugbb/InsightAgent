import test from "node:test";
import assert from "node:assert/strict";

import {
  buildKnowledgeBaseDocumentDeleteUrl,
  resolveKnowledgeBaseDocumentGroups,
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

test("buildKnowledgeBaseDocumentDeleteUrl encodes document selectors", () => {
  assert.equal(
    buildKnowledgeBaseDocumentDeleteUrl(
      "http://127.0.0.1:8000",
      "kb with/slash",
      "api docs",
      "release/notes?draft=1",
    ),
    "http://127.0.0.1:8000/api/rag/knowledge-bases/kb%20with%2Fslash/documents?source=api+docs&document_id=release%2Fnotes%3Fdraft%3D1",
  );
});

test("buildKnowledgeBaseDocumentDeleteUrl normalizes trailing API slash", () => {
  assert.equal(
    buildKnowledgeBaseDocumentDeleteUrl(
      "http://127.0.0.1:8000/",
      "kb",
      "manual",
      "doc-1",
    ),
    "http://127.0.0.1:8000/api/rag/knowledge-bases/kb/documents?source=manual&document_id=doc-1",
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

test("resolveKnowledgeBaseDocumentGroups groups versions by source document", () => {
  assert.deepEqual(
    resolveKnowledgeBaseDocumentGroups([
      {
        document_version: "sha256:bbbbbbbbbbbbbbbb",
        content_hash:
          "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        source: "api-docs",
        document_id: "release-notes",
        chunk_count: 4,
      },
      {
        document_version: "sha256:aaaaaaaaaaaaaaaa",
        content_hash:
          "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        source: "api-docs",
        document_id: "release-notes",
        chunk_count: 1,
      },
      {
        document_version: "sha256:cccccccccccccccc",
        content_hash:
          "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        source: "manual",
        document_id: "ops-note",
        chunk_count: 2,
      },
    ]).map((group) => ({
      key: group.key,
      source: group.source,
      documentId: group.documentId,
      versionCount: group.versionCount,
      chunkCount: group.chunkCount,
      versionLabels: group.versions.map((version) => version.versionLabel),
    })),
    [
      {
        key: "api-docs::release-notes",
        source: "api-docs",
        documentId: "release-notes",
        versionCount: 2,
        chunkCount: 5,
        versionLabels: [
          "sha256:aaaaaaaaaaaaaaaa",
          "sha256:bbbbbbbbbbbbbbbb",
        ],
      },
      {
        key: "manual::ops-note",
        source: "manual",
        documentId: "ops-note",
        versionCount: 1,
        chunkCount: 2,
        versionLabels: ["sha256:cccccccccccccccc"],
      },
    ],
  );
});
