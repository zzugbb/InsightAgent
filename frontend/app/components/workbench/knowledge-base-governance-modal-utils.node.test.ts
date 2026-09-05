import test from "node:test";
import assert from "node:assert/strict";

import {
  buildKnowledgeBaseDocumentDeleteUrl,
  resolveKnowledgeBaseAccessHint,
  resolveKnowledgeBaseDocumentGroups,
  resolveKnowledgeBaseGovernanceListState,
  resolveKnowledgeBaseGovernanceOperatorHint,
  resolveKnowledgeBaseVersionRows,
  summarizeKnowledgeBaseVersions,
} from "./knowledge-base-governance-modal-utils.ts";

test("resolveKnowledgeBaseGovernanceListState distinguishes load and stale-data errors", () => {
  assert.equal(
    resolveKnowledgeBaseGovernanceListState({
      isLoading: false,
      isError: true,
      rowCount: 0,
    }),
    "error",
  );
  assert.equal(
    resolveKnowledgeBaseGovernanceListState({
      isLoading: false,
      isError: true,
      rowCount: 2,
    }),
    "stale_error",
  );
  assert.equal(
    resolveKnowledgeBaseGovernanceListState({
      isLoading: false,
      isError: false,
      rowCount: 0,
    }),
    "empty",
  );
});

test("resolveKnowledgeBaseGovernanceOperatorHint prioritizes safe local next actions", () => {
  const labels = {
    staleData: "Refresh cached data before destructive changes",
    storageUnreachable: "Restore storage connectivity, then refresh",
    empty: "Ingest content before reviewing governance details",
  };

  assert.deepEqual(
    resolveKnowledgeBaseGovernanceOperatorHint({
      listState: "stale_error",
      chromaReachable: false,
      labels,
    }),
    {
      kind: "stale_data",
      label: labels.staleData,
      blocksMutations: true,
    },
  );
  assert.deepEqual(
    resolveKnowledgeBaseGovernanceOperatorHint({
      listState: "ready",
      chromaReachable: false,
      labels,
    }),
    {
      kind: "storage_unreachable",
      label: labels.storageUnreachable,
      blocksMutations: true,
    },
  );
  assert.deepEqual(
    resolveKnowledgeBaseGovernanceOperatorHint({
      listState: "empty",
      chromaReachable: true,
      labels,
    }),
    {
      kind: "empty",
      label: labels.empty,
      blocksMutations: false,
    },
  );
  assert.equal(
    resolveKnowledgeBaseGovernanceOperatorHint({
      listState: "ready",
      chromaReachable: true,
      labels,
    }),
    null,
  );
  assert.equal(
    resolveKnowledgeBaseGovernanceOperatorHint({
      listState: "loading",
      chromaReachable: null,
      labels,
    }),
    null,
  );
});

test("resolveKnowledgeBaseAccessHint explains shared scope by role", () => {
  const labels = {
    readOnly: "Shared scope is read-only; ask an admin to change it",
    admin: "Changes affect everyone with shared access",
  };

  assert.deepEqual(
    resolveKnowledgeBaseAccessHint({
      knowledgeBaseId: "shared-release-notes",
      isAdmin: false,
      labels,
    }),
    {
      kind: "shared_readonly",
      label: labels.readOnly,
      blocksMutations: true,
    },
  );
  assert.deepEqual(
    resolveKnowledgeBaseAccessHint({
      knowledgeBaseId: "shared-release-notes",
      isAdmin: true,
      labels,
    }),
    {
      kind: "shared_admin",
      label: labels.admin,
      blocksMutations: false,
    },
  );
  assert.equal(
    resolveKnowledgeBaseAccessHint({
      knowledgeBaseId: "private-release-notes",
      isAdmin: false,
      labels,
    }),
    null,
  );
});

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
