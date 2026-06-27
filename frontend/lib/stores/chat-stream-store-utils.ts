export type LiveToolEndPayload = {
  status: string;
  retry_count?: number;
  latency_ms?: number;
  error?: string;
  output?: unknown;
  output_preview?: unknown;
  kind?: unknown;
  semantic_kind?: unknown;
  supports_result_preview?: unknown;
  effective_result_preview_keys?: unknown;
};

export type LiveToolStartPayload = {
  name: string;
  input?: unknown;
  retry_count?: number;
  kind?: unknown;
  semantic_kind?: unknown;
  supports_result_preview?: unknown;
  effective_result_preview_keys?: unknown;
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
  status?: unknown;
  retry_count?: unknown;
  error?: unknown;
  kind?: unknown;
  semantic_kind?: unknown;
  supports_result_preview?: unknown;
  effective_result_preview_keys?: unknown;
};

function normalizeToolSemantics(
  prevTool: ToolMetaLike | undefined,
  payload: {
    kind?: unknown;
    semantic_kind?: unknown;
    supports_result_preview?: unknown;
    effective_result_preview_keys?: unknown;
  },
): {
  kind?: string;
  semantic_kind?: string;
  supports_result_preview?: boolean;
  effective_result_preview_keys?: string[];
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
  supports_result_preview?: boolean;
  effective_result_preview_keys?: string[];
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
  kind?: string;
  semantic_kind?: string;
  supports_result_preview?: boolean;
  effective_result_preview_keys?: string[];
  status: "running" | "done" | "error";
  retry_count?: number;
  error?: string | undefined;
} {
  const hasRawOutput = Object.prototype.hasOwnProperty.call(payload, "output");
  const nextStatus =
    payload.status === "running" || payload.status === "error"
      ? payload.status
      : "done";

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
    output: hasRawOutput ? payload.output : prevTool?.output,
    output_preview: payload.output_preview,
    ...normalizeToolSemantics(prevTool, payload),
    retry_count:
      typeof payload.retry_count === "number" ? payload.retry_count : undefined,
    error: typeof payload.error === "string" ? payload.error : undefined,
    status: nextStatus,
  };
}
