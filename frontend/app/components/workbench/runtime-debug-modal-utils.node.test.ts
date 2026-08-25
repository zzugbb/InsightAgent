import test from "node:test";
import assert from "node:assert/strict";

import {
  formatRagRecallDistance,
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
