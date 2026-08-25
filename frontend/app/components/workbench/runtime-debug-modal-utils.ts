export type RagRecallQualityTone = "strong" | "medium" | "weak";

export type RagRecallQuality = {
  tone: RagRecallQualityTone;
  labelKey:
    | "recallQualityStrong"
    | "recallQualityMedium"
    | "recallQualityWeak";
};

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
