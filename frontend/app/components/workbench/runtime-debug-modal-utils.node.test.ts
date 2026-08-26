import test from "node:test";
import assert from "node:assert/strict";

import {
  filterRagHitsByRecallQuality,
  filterRagHitsBySource,
  formatRagRecallDistance,
  resolveRagHitAttributionItems,
  resolveRagSourceFilterOptions,
  resolveRagQueryInsight,
  resolveRagRecallQuality,
} from "./runtime-debug-modal-utils.ts";

test("formatRagRecallDistance formats finite distances", () => {
  assert.equal(formatRagRecallDistance(0.123456), "0.1235");
  assert.equal(formatRagRecallDistance(null), null);
  assert.equal(formatRagRecallDistance(Number.NaN), null);
});

test("resolveRagRecallQuality maps lower distances to stronger recall labels", () => {
  assert.deepEqual(resolveRagRecallQuality(0.19), {
    tone: "strong",
    labelKey: "recallQualityStrong",
  });
  assert.deepEqual(resolveRagRecallQuality(0.42), {
    tone: "medium",
    labelKey: "recallQualityMedium",
  });
  assert.deepEqual(resolveRagRecallQuality(0.82), {
    tone: "weak",
    labelKey: "recallQualityWeak",
  });
  assert.equal(resolveRagRecallQuality(null), null);
});

test("resolveRagHitAttributionItems summarizes safe recall metadata", () => {
  const items = resolveRagHitAttributionItems({
    source: "release-notes.md",
    document_id: "docs/rag-product-experience",
    document_version: "sha256:1234567890abcdef1234",
    content_hash: "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
    chunk_index: "2",
    chunk_total: "5",
    ignored: "noise",
  });

  assert.deepEqual(items, [
    { labelKey: "sourceLabel", value: "release-notes.md" },
    { labelKey: "documentLabel", value: "docs/rag-product-experience" },
    { labelKey: "versionLabel", value: "sha256:1234567890abcdef1234" },
    { labelKey: "hashLabel", value: "abcdef012345" },
    { labelKey: "chunkLabel", value: "2/5" },
  ]);
  assert.deepEqual(resolveRagHitAttributionItems(null), []);
});

test("resolveRagQueryInsight summarizes best recall and source coverage", () => {
  const insight = resolveRagQueryInsight([
    {
      distance: 0.52,
      metadata: {
        source: "handbook.md",
        document_id: "manual",
      },
    },
    {
      distance: 0.18,
      metadata: {
        source: "release-notes.md",
        document_id: "release-2026",
      },
    },
    {
      distance: null,
      metadata: {
        source: "release-notes.md",
        document_id: "release-2026",
      },
    },
  ]);

  assert.deepEqual(insight, {
    bestDistance: "0.1800",
    bestQuality: {
      tone: "strong",
      labelKey: "recallQualityStrong",
    },
    guidanceKey: "recallGuidanceStrong",
    topSource: "release-notes.md",
    sourceCount: 2,
    documentCount: 2,
    qualityCounts: {
      strong: 1,
      medium: 1,
      weak: 0,
    },
  });
  assert.equal(resolveRagQueryInsight([]), null);
});

test("resolveRagQueryInsight guides weak recall results", () => {
  const insight = resolveRagQueryInsight([
    {
      distance: 0.81,
      metadata: {
        source: "handbook.md",
      },
    },
  ]);

  assert.equal(insight?.guidanceKey, "recallGuidanceWeak");
});

test("filterRagHitsByRecallQuality narrows hits by recall quality", () => {
  const hits = [
    { id: "strong", distance: 0.12, metadata: { source: "a.md" } },
    { id: "medium", distance: 0.4, metadata: { source: "b.md" } },
    { id: "weak", distance: 0.82, metadata: { source: "c.md" } },
    { id: "unknown", distance: null, metadata: { source: "d.md" } },
  ];

  assert.deepEqual(
    filterRagHitsByRecallQuality(hits, "all").map((hit) => hit.id),
    ["strong", "medium", "weak", "unknown"],
  );
  assert.deepEqual(
    filterRagHitsByRecallQuality(hits, "strong").map((hit) => hit.id),
    ["strong"],
  );
  assert.deepEqual(
    filterRagHitsByRecallQuality(hits, "medium").map((hit) => hit.id),
    ["medium"],
  );
  assert.deepEqual(
    filterRagHitsByRecallQuality(hits, "weak").map((hit) => hit.id),
    ["weak"],
  );
});

test("resolveRagSourceFilterOptions summarizes stable source counts", () => {
  const hits = [
    { id: "one", metadata: { source: "beta.md" } },
    { id: "two", metadata: { source: "alpha.md" } },
    { id: "three", metadata: { source: "beta.md" } },
    { id: "blank", metadata: { source: " " } },
  ];

  assert.deepEqual(resolveRagSourceFilterOptions(hits), [
    { source: "alpha.md", count: 1 },
    { source: "beta.md", count: 2 },
  ]);
});

test("filterRagHitsBySource narrows hits by safe source metadata", () => {
  const hits = [
    { id: "alpha", metadata: { source: "alpha.md" } },
    { id: "beta", metadata: { source: "beta.md" } },
    { id: "unknown", metadata: {} },
  ];

  assert.deepEqual(
    filterRagHitsBySource(hits, "all").map((hit) => hit.id),
    ["alpha", "beta", "unknown"],
  );
  assert.deepEqual(
    filterRagHitsBySource(hits, "beta.md").map((hit) => hit.id),
    ["beta"],
  );
});
