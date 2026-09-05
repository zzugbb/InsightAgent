export type RagRecallQualityTone = "strong" | "medium" | "weak";
export type RagRecallQualityFilter = "all" | RagRecallQualityTone;
export const RAG_UNATTRIBUTED_SOURCE_FILTER_VALUE =
  "__insightagent_unattributed_source__";
export type RagFilterEmptyMessageKey =
  | "qualityFilterEmpty"
  | "sourceFilterEmpty"
  | "combinedFilterEmpty"
  | "filterEmptyGeneric";
export type RagMutationRecoveryKind =
  | "retry"
  | "review_input"
  | "reauthenticate";

export type RagMutationRecovery = {
  kind: RagMutationRecoveryKind;
  canRetry: boolean;
};

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

export type RagSourceFilterOption = {
  value: string;
  source: string | null;
  count: number;
};

export type RagQueryInsightHit = {
  distance?: number | null;
  metadata?: Record<string, unknown> | null;
};

export type RagQueryInsight = {
  bestDistance: string | null;
  bestQuality: RagRecallQuality | null;
  guidanceKey:
    | "recallGuidanceStrong"
    | "recallGuidanceMedium"
    | "recallGuidanceWeak"
    | null;
  topSource: string | null;
  sourceCount: number;
  documentCount: number;
  qualityCounts: Record<RagRecallQualityTone, number>;
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

export function resolveRagMutationRecovery(error: unknown): RagMutationRecovery {
  const status =
    typeof error === "object" && error !== null && "status" in error
      ? cleanFiniteInteger(error.status)
      : null;
  if (status === 401 || status === 403) {
    return { kind: "reauthenticate", canRetry: false };
  }
  if (
    status !== null &&
    status >= 400 &&
    status < 500 &&
    status !== 408 &&
    status !== 429
  ) {
    return { kind: "review_input", canRetry: false };
  }
  return { kind: "retry", canRetry: true };
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

export function filterRagHitsByRecallQuality<T extends RagQueryInsightHit>(
  hits: T[],
  filter: RagRecallQualityFilter,
): T[] {
  if (filter === "all") {
    return hits;
  }
  return hits.filter(
    (hit) => resolveRagRecallQuality(hit.distance)?.tone === filter,
  );
}

export function resolveRagSourceFilterOptions(
  hits: RagQueryInsightHit[],
): RagSourceFilterOption[] {
  const counts = new Map<string, number>();
  let unattributedCount = 0;
  for (const hit of hits) {
    const source = cleanText(hit.metadata?.source);
    if (!source) {
      unattributedCount += 1;
      continue;
    }
    counts.set(source, (counts.get(source) ?? 0) + 1);
  }
  const sourceOptions: RagSourceFilterOption[] = [...counts.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([source, count]) => ({ value: source, source, count }));
  if (unattributedCount > 0) {
    sourceOptions.push({
      value: RAG_UNATTRIBUTED_SOURCE_FILTER_VALUE,
      source: null,
      count: unattributedCount,
    });
  }
  return sourceOptions;
}

export function filterRagHitsBySource<T extends RagQueryInsightHit>(
  hits: T[],
  sourceFilter: string,
): T[] {
  if (sourceFilter === "all") {
    return hits;
  }
  if (sourceFilter === RAG_UNATTRIBUTED_SOURCE_FILTER_VALUE) {
    return hits.filter((hit) => !cleanText(hit.metadata?.source));
  }
  return hits.filter((hit) => cleanText(hit.metadata?.source) === sourceFilter);
}

export function resolveRagFilterEmptyMessageKey(
  qualityFilter: RagRecallQualityFilter,
  sourceFilter: string,
): RagFilterEmptyMessageKey {
  const hasQualityFilter = qualityFilter !== "all";
  const hasSourceFilter = sourceFilter !== "all";
  if (hasQualityFilter && hasSourceFilter) {
    return "combinedFilterEmpty";
  }
  if (hasSourceFilter) {
    return "sourceFilterEmpty";
  }
  if (hasQualityFilter) {
    return "qualityFilterEmpty";
  }
  return "filterEmptyGeneric";
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

export function resolveRagQueryInsight(
  hits: RagQueryInsightHit[],
): RagQueryInsight | null {
  if (!Array.isArray(hits) || hits.length === 0) {
    return null;
  }

  const sources = new Set<string>();
  const documents = new Set<string>();
  const qualityCounts: Record<RagRecallQualityTone, number> = {
    strong: 0,
    medium: 0,
    weak: 0,
  };
  let bestDistanceValue: number | null = null;
  let topSource: string | null = null;

  for (const hit of hits) {
    const metadata = hit.metadata || {};
    const source = cleanText(metadata.source);
    const documentId = cleanText(metadata.document_id);
    if (source) {
      sources.add(source);
    }
    if (documentId) {
      documents.add(documentId);
    }

    const distance = hit.distance;
    if (typeof distance !== "number" || !Number.isFinite(distance)) {
      continue;
    }
    const quality = resolveRagRecallQuality(distance);
    if (quality) {
      qualityCounts[quality.tone] += 1;
    }
    if (bestDistanceValue === null || distance < bestDistanceValue) {
      bestDistanceValue = distance;
      topSource = source;
    }
  }

  const bestQuality = resolveRagRecallQuality(bestDistanceValue);
  let guidanceKey: RagQueryInsight["guidanceKey"] = null;
  if (bestQuality?.tone === "strong") {
    guidanceKey = "recallGuidanceStrong";
  } else if (bestQuality?.tone === "medium") {
    guidanceKey = "recallGuidanceMedium";
  } else if (bestQuality?.tone === "weak") {
    guidanceKey = "recallGuidanceWeak";
  }

  return {
    bestDistance: formatRagRecallDistance(bestDistanceValue),
    bestQuality,
    guidanceKey,
    topSource,
    sourceCount: sources.size,
    documentCount: documents.size,
    qualityCounts,
  };
}
