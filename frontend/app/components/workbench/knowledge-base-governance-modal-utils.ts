import type { RagDocumentVersionSummary } from "./types";

export type KnowledgeBaseVersionRow = {
  key: string;
  source: string;
  documentId: string;
  version: string;
  versionLabel: string;
  contentHash: string;
  contentHashLabel: string;
  chunkCount: number;
};

export type KnowledgeBaseVersionSummary = {
  versionCount: number;
  documentCount: number;
  chunkCount: number;
};

export type KnowledgeBaseDocumentGroup = {
  key: string;
  source: string;
  documentId: string;
  versionCount: number;
  chunkCount: number;
  versions: KnowledgeBaseVersionRow[];
};

export type KnowledgeBaseGovernanceListState =
  | "loading"
  | "error"
  | "stale_error"
  | "empty"
  | "ready";

export type KnowledgeBaseGovernanceOperatorHintKind =
  | "stale_data"
  | "storage_unreachable"
  | "empty";

export type KnowledgeBaseGovernanceOperatorHint = {
  kind: KnowledgeBaseGovernanceOperatorHintKind;
  label: string;
  blocksMutations: boolean;
};

export type KnowledgeBaseAccessHint = {
  kind: "shared_readonly" | "shared_admin";
  label: string;
  blocksMutations: boolean;
};

export function resolveKnowledgeBaseGovernanceListState(args: {
  isLoading: boolean;
  isError: boolean;
  rowCount: number;
}): KnowledgeBaseGovernanceListState {
  if (args.isError) {
    return args.rowCount > 0 ? "stale_error" : "error";
  }
  if (args.isLoading) {
    return "loading";
  }
  return args.rowCount > 0 ? "ready" : "empty";
}

export function resolveKnowledgeBaseGovernanceOperatorHint(args: {
  listState: KnowledgeBaseGovernanceListState;
  chromaReachable: boolean | null;
  labels: {
    staleData: string;
    storageUnreachable: string;
    empty: string;
  };
}): KnowledgeBaseGovernanceOperatorHint | null {
  if (args.listState === "stale_error") {
    return {
      kind: "stale_data",
      label: args.labels.staleData,
      blocksMutations: true,
    };
  }
  if (
    args.listState !== "loading" &&
    args.listState !== "error" &&
    args.chromaReachable === false
  ) {
    return {
      kind: "storage_unreachable",
      label: args.labels.storageUnreachable,
      blocksMutations: true,
    };
  }
  if (args.listState === "empty") {
    return {
      kind: "empty",
      label: args.labels.empty,
      blocksMutations: false,
    };
  }
  return null;
}

export function resolveKnowledgeBaseAccessHint(args: {
  knowledgeBaseId: string;
  isAdmin: boolean;
  labels: {
    readOnly: string;
    admin: string;
  };
}): KnowledgeBaseAccessHint | null {
  if (!args.knowledgeBaseId.trim().toLowerCase().startsWith("shared-")) {
    return null;
  }
  return args.isAdmin
    ? {
        kind: "shared_admin",
        label: args.labels.admin,
        blocksMutations: false,
      }
    : {
        kind: "shared_readonly",
        label: args.labels.readOnly,
        blocksMutations: true,
      };
}

export function buildKnowledgeBaseDocumentDeleteUrl(
  apiBaseUrl: string,
  knowledgeBaseId: string,
  source: string,
  documentId: string,
): string {
  const baseUrl = apiBaseUrl.replace(/\/+$/, "");
  const params = new URLSearchParams({
    source,
    document_id: documentId,
  });
  return `${baseUrl}/api/rag/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents?${params.toString()}`;
}

function normalizeVersionText(value: unknown, fallback: string): string {
  const normalized = typeof value === "string" ? value.trim() : "";
  return normalized || fallback;
}

function normalizeChunkCount(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) && value > 0
    ? Math.floor(value)
    : 0;
}

function shortenContentHash(value: string): string {
  return value.length > 12 ? `${value.slice(0, 12)}...` : value;
}

export function resolveKnowledgeBaseVersionRows(
  versions: RagDocumentVersionSummary[] | null | undefined,
): KnowledgeBaseVersionRow[] {
  if (!Array.isArray(versions)) {
    return [];
  }
  return versions
    .map((version, index) => {
      const source = normalizeVersionText(version.source, "manual");
      const documentId = normalizeVersionText(version.document_id, "untitled");
      const versionValue = normalizeVersionText(
        version.document_version,
        `version-${index + 1}`,
      );
      const contentHash = normalizeVersionText(version.content_hash, "");
      return {
        key: `${source}::${documentId}::${versionValue}`,
        source,
        documentId,
        version: versionValue,
        versionLabel: versionValue,
        contentHash,
        contentHashLabel: shortenContentHash(contentHash),
        chunkCount: normalizeChunkCount(version.chunk_count),
      };
    })
    .sort((a, b) =>
      a.source.localeCompare(b.source) ||
      a.documentId.localeCompare(b.documentId) ||
      a.version.localeCompare(b.version),
    );
}

export function summarizeKnowledgeBaseVersions(
  versions: RagDocumentVersionSummary[] | null | undefined,
): KnowledgeBaseVersionSummary {
  const rows = resolveKnowledgeBaseVersionRows(versions);
  const documentKeys = new Set(
    rows.map((row) => `${row.source}::${row.documentId}`),
  );
  return {
    versionCount: rows.length,
    documentCount: documentKeys.size,
    chunkCount: rows.reduce((total, row) => total + row.chunkCount, 0),
  };
}

export function resolveKnowledgeBaseDocumentGroups(
  versions: RagDocumentVersionSummary[] | null | undefined,
): KnowledgeBaseDocumentGroup[] {
  const rows = resolveKnowledgeBaseVersionRows(versions);
  const groups = new Map<string, KnowledgeBaseDocumentGroup>();

  for (const row of rows) {
    const key = `${row.source}::${row.documentId}`;
    const existing = groups.get(key);
    if (existing) {
      existing.versionCount += 1;
      existing.chunkCount += row.chunkCount;
      existing.versions.push(row);
      continue;
    }
    groups.set(key, {
      key,
      source: row.source,
      documentId: row.documentId,
      versionCount: 1,
      chunkCount: row.chunkCount,
      versions: [row],
    });
  }

  return [...groups.values()];
}
