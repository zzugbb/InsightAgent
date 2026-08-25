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
