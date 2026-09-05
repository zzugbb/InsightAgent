import type { TaskFailureSource } from "./utils";

export type AuditDetailEntry = { key: string; label: string; value: string };
export type AuditEventFilter =
  | "all"
  | "login"
  | "logout"
  | "refresh"
  | "settings_update"
  | "settings_validate"
  | "task_create"
  | "task_cancel"
  | "task_timeout"
  | "task_failed"
  | "rag_ingest"
  | "rag_kb_clear"
  | "rag_kb_delete";
export type AuditTimeFilter = "all" | "7d" | "30d";
export type AuditLogsListState =
  | "loading"
  | "error"
  | "stale_error"
  | "empty"
  | "ready";
export type AuditOperatorHintKind = "task_failure" | "task_timeout";
export type AuditOperatorHint = {
  kind: AuditOperatorHintKind;
  label: string;
  traceSemanticFilter: "failure";
  canOpenTaskDetail: boolean;
};

export type AuditFailureLabels = {
  fieldCode: string;
  fieldMessage: string;
  fieldFailureHint: string;
  fieldFailureSource: string;
  fieldDiagnosticReason: string;
  streamErrorByCode?: (code: string) => string | null;
  taskFailureSourceErrorEvent: string;
  taskFailureSourceToolError: string;
  taskFailureSourceTraceContent: string;
  taskFailureSourceLegacyTrace: string;
};

type AuditOperatorHintLabels = {
  taskFailure: string;
  taskTimeout: string;
};

export function resolveAuditLogsListState(args: {
  isLoading: boolean;
  isError: boolean;
  rowCount: number;
}): AuditLogsListState {
  if (args.isError) {
    return args.rowCount > 0 ? "stale_error" : "error";
  }
  if (args.isLoading) {
    return "loading";
  }
  return args.rowCount > 0 ? "ready" : "empty";
}

export function buildAuditLogsUrl(params: {
  apiBaseUrl: string;
  limit: number;
  offset: number;
  eventType: AuditEventFilter;
  timeFilter: AuditTimeFilter;
  sessionId: string;
  taskId: string;
  keyword: string;
  nowMs?: number;
}): string {
  const q = new URLSearchParams();
  q.set("limit", String(params.limit));
  q.set("offset", String(params.offset));
  if (params.eventType !== "all") {
    q.set("event_type", params.eventType);
  }
  if (params.timeFilter !== "all") {
    const days = params.timeFilter === "7d" ? 7 : 30;
    q.set(
      "start_at",
      new Date((params.nowMs ?? Date.now()) - days * 24 * 60 * 60 * 1000).toISOString(),
    );
  }
  if (params.sessionId.trim()) {
    q.set("session_id", params.sessionId.trim());
  }
  if (params.taskId.trim()) {
    q.set("task_id", params.taskId.trim());
  }
  if (params.keyword.trim()) {
    q.set("keyword", params.keyword.trim());
  }
  return `${params.apiBaseUrl.replace(/\/+$/, "")}/api/audit/logs?${q.toString()}`;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function isTaskFailureSource(value: unknown): value is TaskFailureSource {
  return (
    value === "error_event" ||
    value === "tool_error" ||
    value === "trace_content" ||
    value === "legacy_trace"
  );
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

export function formatAuditFailureSourceLabel(
  source: unknown,
  labels: Pick<
    AuditFailureLabels,
    | "taskFailureSourceErrorEvent"
    | "taskFailureSourceToolError"
    | "taskFailureSourceTraceContent"
    | "taskFailureSourceLegacyTrace"
  >,
): string | null {
  if (source === "error_event") {
    return labels.taskFailureSourceErrorEvent;
  }
  if (source === "tool_error") {
    return labels.taskFailureSourceToolError;
  }
  if (source === "trace_content") {
    return labels.taskFailureSourceTraceContent;
  }
  if (source === "legacy_trace") {
    return labels.taskFailureSourceLegacyTrace;
  }
  return asString(source);
}

function resolveFailureHint(
  detail: Record<string, unknown> | null | undefined,
  labels: Pick<AuditFailureLabels, "streamErrorByCode">,
): {
  hint: string | null;
  message: string | null;
  messageUsedAsFallbackHint: boolean;
} {
  const message = asString(detail?.message);
  const explicitFailureHint = asString(detail?.failure_hint);
  if (explicitFailureHint) {
    return { hint: explicitFailureHint, message, messageUsedAsFallbackHint: false };
  }
  const code = asString(detail?.code);
  const codeHint =
    code && labels.streamErrorByCode
      ? asString(labels.streamErrorByCode(code))
      : null;
  if (codeHint && codeHint !== code) {
    return { hint: codeHint, message, messageUsedAsFallbackHint: false };
  }
  return { hint: message, message, messageUsedAsFallbackHint: Boolean(message) };
}

export function formatAuditTaskFailureSummary(
  eventLabel: string,
  detail: Record<string, unknown> | null | undefined,
  labels: Pick<
    AuditFailureLabels,
    | "streamErrorByCode"
    | "taskFailureSourceErrorEvent"
    | "taskFailureSourceToolError"
    | "taskFailureSourceTraceContent"
    | "taskFailureSourceLegacyTrace"
  >,
): string {
  const { hint: failureHint } = resolveFailureHint(detail, labels);
  if (!failureHint) {
    return eventLabel;
  }
  const failureSource = isTaskFailureSource(detail?.failure_source)
    ? formatAuditFailureSourceLabel(detail?.failure_source, labels)
    : null;
  return `${eventLabel} · ${failureSource ? `${failureSource}: ` : ""}${failureHint}`;
}

export function resolveAuditOperatorHint(args: {
  eventType: string;
  hasTaskDetailHref: boolean;
  detail: Record<string, unknown> | null | undefined;
  labels: AuditOperatorHintLabels;
}): AuditOperatorHint | null {
  const normalizedEventType = args.eventType.trim().toLowerCase();
  if (normalizedEventType !== "task_failed" && normalizedEventType !== "task_timeout") {
    return null;
  }
  if (!args.detail) {
    return null;
  }
  const hasFailureSignal = Boolean(
    asString(args.detail.failure_hint) ||
      asString(args.detail.code) ||
      asString(args.detail.message) ||
      asString(asRecord(args.detail.diagnostic)?.reason),
  );
  if (!hasFailureSignal) {
    return null;
  }
  return {
    kind: normalizedEventType === "task_timeout" ? "task_timeout" : "task_failure",
    label:
      normalizedEventType === "task_timeout"
        ? args.labels.taskTimeout
        : args.labels.taskFailure,
    traceSemanticFilter: "failure",
    canOpenTaskDetail: args.hasTaskDetailHref,
  };
}

export function resolveAuditReadableDetail(
  detail: Record<string, unknown> | null | undefined,
  labels: AuditFailureLabels,
): AuditDetailEntry[] {
  if (!detail) {
    return [];
  }
  const entries: AuditDetailEntry[] = [];
  const {
    hint: failureHint,
    message,
    messageUsedAsFallbackHint,
  } = resolveFailureHint(detail, labels);
  if (failureHint) {
    entries.push({
      key: "failure_hint",
      label: labels.fieldFailureHint,
      value: failureHint,
    });
  }
  const failureSource = formatAuditFailureSourceLabel(
    detail.failure_source,
    labels,
  );
  if (failureSource) {
    entries.push({
      key: "failure_source",
      label: labels.fieldFailureSource,
      value: failureSource,
    });
  }
  const diagnosticReason = asString(asRecord(detail.diagnostic)?.reason);
  if (diagnosticReason) {
    entries.push({
      key: "diagnostic_reason",
      label: labels.fieldDiagnosticReason,
      value: diagnosticReason,
    });
  }
  const code = asString(detail.code);
  if (code) {
    entries.push({ key: "code", label: labels.fieldCode, value: code });
  }
  if (message && !messageUsedAsFallbackHint) {
    entries.push({ key: "message", label: labels.fieldMessage, value: message });
  }
  return entries;
}
