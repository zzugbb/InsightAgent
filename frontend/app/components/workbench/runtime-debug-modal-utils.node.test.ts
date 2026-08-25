import test from "node:test";
import assert from "node:assert/strict";

import {
  formatRagRecallDistance,
  resolveRagHitAttributionItems,
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
