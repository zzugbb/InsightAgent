export type LiveToolEndPayload = {
  status: string;
  retry_count?: number;
  latency_ms?: number;
  error?: string;
  output?: unknown;
  output_preview?: unknown;
  result_summary?: unknown;
  kind?: unknown;
  semantic_kind?: unknown;
  semantic_family?: unknown;
  supports_result_preview?: unknown;
  effective_result_preview_keys?: unknown;
  effective_result_output_keys?: unknown;
};

export type LiveToolStartPayload = {
  name: string;
  input?: unknown;
  retry_count?: number;
  kind?: unknown;
  semantic_kind?: unknown;
  semantic_family?: unknown;
  supports_result_preview?: unknown;
  effective_result_preview_keys?: unknown;
  effective_result_output_keys?: unknown;
};

type ToolIdentity = {
  name: string;
  label: string;
};

type ToolMetaLike = {
  name?: unknown;
  label?: unknown;
  input?: unknown;
  output?: unknown;
  output_preview?: unknown;
  result_summary?: unknown;
  status?: unknown;
  retry_count?: unknown;
  error?: unknown;
  kind?: unknown;
  semantic_kind?: unknown;
  semantic_family?: unknown;
  supports_result_preview?: unknown;
  effective_result_preview_keys?: unknown;
  effective_result_output_keys?: unknown;
};

function normalizeToolOutputByKeys(
  output: unknown,
  outputKeys: string[] | undefined,
): unknown {
  if (
    !output
    || typeof output !== "object"
    || Array.isArray(output)
    || !outputKeys
    || outputKeys.length === 0
  ) {
    return output;
  }
  return Object.fromEntries(
    outputKeys
      .filter((key) => Object.prototype.hasOwnProperty.call(output, key))
      .map((key) => [key, output[key as keyof typeof output]]),
  );
}

function normalizeToolSemantics(
  prevTool: ToolMetaLike | undefined,
  payload: {
    kind?: unknown;
    semantic_kind?: unknown;
    semantic_family?: unknown;
    supports_result_preview?: unknown;
    effective_result_preview_keys?: unknown;
    effective_result_output_keys?: unknown;
  },
): {
  kind?: string;
  semantic_kind?: string;
  semantic_family?: string;
  supports_result_preview?: boolean;
  effective_result_preview_keys?: string[];
  effective_result_output_keys?: string[];
} {
  return {
    kind:
      typeof payload.kind === "string" && payload.kind.trim()
        ? payload.kind.trim()
        : typeof prevTool?.kind === "string" && prevTool.kind.trim()
          ? prevTool.kind.trim()
          : undefined,
    semantic_kind:
      typeof payload.semantic_kind === "string" && payload.semantic_kind.trim()
        ? payload.semantic_kind.trim()
        : typeof prevTool?.semantic_kind === "string" &&
            prevTool.semantic_kind.trim()
          ? prevTool.semantic_kind.trim()
          : undefined,
    semantic_family:
      typeof payload.semantic_family === "string" && payload.semantic_family.trim()
        ? payload.semantic_family.trim()
        : typeof prevTool?.semantic_family === "string" &&
            prevTool.semantic_family.trim()
          ? prevTool.semantic_family.trim()
          : undefined,
    supports_result_preview:
      typeof payload.supports_result_preview === "boolean"
        ? payload.supports_result_preview
        : typeof prevTool?.supports_result_preview === "boolean"
          ? prevTool.supports_result_preview
          : undefined,
    effective_result_preview_keys: Array.isArray(
      payload.effective_result_preview_keys,
    )
      ? payload.effective_result_preview_keys.filter(
          (key): key is string => typeof key === "string" && key.trim().length > 0,
        )
      : Array.isArray(prevTool?.effective_result_preview_keys)
        ? prevTool.effective_result_preview_keys.filter(
            (key): key is string =>
              typeof key === "string" && key.trim().length > 0,
          )
        : undefined,
    effective_result_output_keys: Array.isArray(
      payload.effective_result_output_keys,
    )
      ? payload.effective_result_output_keys.filter(
          (key): key is string => typeof key === "string" && key.trim().length > 0,
        )
      : Array.isArray(prevTool?.effective_result_output_keys)
        ? prevTool.effective_result_output_keys.filter(
            (key): key is string =>
              typeof key === "string" && key.trim().length > 0,
          )
        : undefined,
  };
}

export function mergeToolStartToolMeta(
  prevTool: ToolMetaLike | undefined,
  payload: LiveToolStartPayload,
  identity: ToolIdentity,
): {
  name: string;
  label: string;
  input?: unknown;
  kind?: string;
  semantic_kind?: string;
  semantic_family?: string;
  supports_result_preview?: boolean;
  effective_result_preview_keys?: string[];
  effective_result_output_keys?: string[];
  status: "running";
  retry_count: number;
} {
  return {
    name:
      typeof prevTool?.name === "string" && prevTool.name.trim()
        ? prevTool.name.trim()
        : identity.name,
    label:
      typeof prevTool?.label === "string" && prevTool.label.trim()
        ? prevTool.label.trim()
        : identity.label,
    input: payload.input,
    ...normalizeToolSemantics(prevTool, payload),
    retry_count:
      typeof payload.retry_count === "number" ? payload.retry_count : 0,
    status: "running",
  };
}

export function mergeToolEndToolMeta(
  prevTool: ToolMetaLike | undefined,
  payload: LiveToolEndPayload,
  identity: ToolIdentity,
): {
  name: string;
  label: string;
  input?: unknown;
  output?: unknown;
  output_preview?: unknown;
  result_summary?: string;
  kind?: string;
  semantic_kind?: string;
  semantic_family?: string;
  supports_result_preview?: boolean;
  effective_result_preview_keys?: string[];
  effective_result_output_keys?: string[];
  status: "running" | "done" | "error";
  retry_count?: number;
  error?: string | undefined;
} {
  const hasRawOutput = Object.prototype.hasOwnProperty.call(payload, "output");
  const nextStatus =
    payload.status === "running" || payload.status === "error"
      ? payload.status
      : "done";
  const semantics = normalizeToolSemantics(prevTool, payload);

  return {
    name:
      typeof prevTool?.name === "string" && prevTool.name.trim()
        ? prevTool.name.trim()
        : identity.name,
    label:
      typeof prevTool?.label === "string" && prevTool.label.trim()
        ? prevTool.label.trim()
        : identity.label,
    input: prevTool?.input,
    output: hasRawOutput
      ? normalizeToolOutputByKeys(
          payload.output,
          semantics.effective_result_output_keys,
        )
      : prevTool?.output,
    output_preview: payload.output_preview,
    result_summary:
      typeof payload.result_summary === "string" && payload.result_summary.trim()
        ? payload.result_summary.trim()
        : typeof prevTool?.result_summary === "string" &&
            prevTool.result_summary.trim()
          ? prevTool.result_summary.trim()
          : undefined,
    ...semantics,
    retry_count:
      typeof payload.retry_count === "number" ? payload.retry_count : undefined,
    error: typeof payload.error === "string" ? payload.error : undefined,
    status: nextStatus,
  };
}
