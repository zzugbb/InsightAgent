export type LiveToolEndPayload = {
  status: string;
  retry_count?: number;
  latency_ms?: number;
  error?: string;
  output?: unknown;
  output_preview?: unknown;
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
};

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
    retry_count:
      typeof payload.retry_count === "number" ? payload.retry_count : undefined,
    error: typeof payload.error === "string" ? payload.error : undefined,
    status: nextStatus,
  };
}
