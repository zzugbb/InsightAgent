export type RagRecallQualityTone = "strong" | "medium" | "weak";

export type RagRecallQuality = {
  tone: RagRecallQualityTone;
  labelKey:
    | "recallQualityStrong"
    | "recallQualityMedium"
    | "recallQualityWeak";
};

export type RagHitAttributionLabelKey =
  | "sourceLabel"
  | "documentLabel"
  | "versionLabel"
  | "hashLabel"
  | "chunkLabel";

export type RagHitAttributionItem = {
  labelKey: RagHitAttributionLabelKey;
  value: string;
};

function cleanText(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed || null;
}

function cleanFiniteInteger(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.trunc(value);
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value.trim());
    return Number.isFinite(parsed) ? Math.trunc(parsed) : null;
  }
  return null;
}

export function formatRagRecallDistance(value: unknown): string | null {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(4)
    : null;
}

export function resolveRagRecallQuality(value: unknown): RagRecallQuality | null {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return null;
  }
  if (value < 0.25) {
    return {
      tone: "strong",
      labelKey: "recallQualityStrong",
    };
  }
  if (value < 0.65) {
    return {
      tone: "medium",
      labelKey: "recallQualityMedium",
    };
  }
  return {
    tone: "weak",
    labelKey: "recallQualityWeak",
  };
}

export function resolveRagHitAttributionItems(
  metadata: Record<string, unknown> | null | undefined,
): RagHitAttributionItem[] {
  if (!metadata || typeof metadata !== "object") {
    return [];
  }

  const items: RagHitAttributionItem[] = [];
  const source = cleanText(metadata.source);
  const documentId = cleanText(metadata.document_id);
  const documentVersion = cleanText(metadata.document_version);
  const contentHash = cleanText(metadata.content_hash);
  const chunkIndex = cleanFiniteInteger(metadata.chunk_index);
  const chunkTotal = cleanFiniteInteger(metadata.chunk_total);

  if (source) {
    items.push({ labelKey: "sourceLabel", value: source });
  }
  if (documentId) {
    items.push({ labelKey: "documentLabel", value: documentId });
  }
  if (documentVersion) {
    items.push({ labelKey: "versionLabel", value: documentVersion });
  }
  if (contentHash) {
    items.push({ labelKey: "hashLabel", value: contentHash.slice(0, 12) });
  }
  if (chunkIndex !== null && chunkTotal !== null && chunkTotal > 0) {
    items.push({ labelKey: "chunkLabel", value: `${chunkIndex}/${chunkTotal}` });
  } else if (chunkIndex !== null) {
    items.push({ labelKey: "chunkLabel", value: String(chunkIndex) });
  }

  return items;
}
