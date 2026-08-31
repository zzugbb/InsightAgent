import type { TraceStepPayload } from "../../../lib/types/trace";

export type TaskDetailTraceView = "list" | "flow";
export type TaskDetailTraceSemanticFilter =
  | "all"
  | "planner"
  | "retrieval"
  | "calculator"
  | "failure";
export type TaskDetailTraceKindFilter =
  | "all"
  | "thought"
  | "action"
  | "observation"
  | "tool"
  | "rag"
  | "other";

export type TaskDetailTraceFilterState = {
  traceView: TaskDetailTraceView;
  traceSemanticFilter: TaskDetailTraceSemanticFilter;
  traceKindFilter: TaskDetailTraceKindFilter;
  traceSearchQuery: string;
};

export type TaskDetailStatusTone =
  | "running"
  | "completed"
  | "failed"
  | "other";

type TaskDetailStatusInput = {
  status: string;
  status_normalized?: string;
  status_label?: string;
};

const FAILURE_DIAGNOSTIC_TOKENS = [
  "error",
  "failed",
  "failure",
  "timeout",
  "timed_out",
  "cancel",
  "cancelled",
  "unauthorized",
  "forbidden",
  "rate_limited",
  "rate limit",
  "permission_denied",
  "permission denied",
  "access_denied",
  "connection_refused",
  "connection refused",
  "refused",
  "unavailable",
  "quota_exceeded",
  "quota exceeded",
  "exhausted",
  "invalid_json",
  "empty_response",
  "interrupted",
];

const TRACE_SEMANTIC_PRESETS: readonly Exclude<TaskDetailTraceSemanticFilter, "all">[] = [
  "planner",
  "retrieval",
  "calculator",
  "failure",
];

function isFailureDiagnosticContent(value: string): boolean {
  const content = value.trim().toLowerCase();
  return Boolean(content) && FAILURE_DIAGNOSTIC_TOKENS.some((token) => content.includes(token));
}

export function isTaskDetailRunningLike(
  task: TaskDetailStatusInput | null | undefined,
): boolean {
  const status = (task?.status_normalized?.trim() || task?.status || "")
    .trim()
    .toLowerCase();
  return status === "queued" || status === "running" || status === "pending";
}

function resolveTaskDetailStatusTone(status: string): TaskDetailStatusTone {
  const normalized = status.trim().toLowerCase();
  if (
    normalized === "queued" ||
    normalized === "running" ||
    normalized === "pending"
  ) {
    return "running";
  }
  if (
    normalized === "completed" ||
    normalized === "done" ||
    normalized === "success"
  ) {
    return "completed";
  }
  if (normalized === "failed" || normalized === "error") {
    return "failed";
  }
  return "other";
}

export function resolveTaskDetailStatusDisplay(
  task: TaskDetailStatusInput,
): { label: string; tone: TaskDetailStatusTone } {
  const normalized = task.status_normalized?.trim() ?? "";
  const raw = task.status.trim();
  return {
    label: normalized || task.status_label?.trim() || raw || "unknown",
    tone: resolveTaskDetailStatusTone(normalized || raw),
  };
}

export function buildTaskDetailTraceSemanticHref(
  taskId: string,
  semanticFilter: TaskDetailTraceSemanticFilter,
): string {
  const normalizedTaskId = taskId.trim();
  const baseHref = `/tasks/${encodeURIComponent(normalizedTaskId)}`;
  if (!normalizedTaskId) {
    return baseHref;
  }
  return semanticFilter === "all"
    ? baseHref
    : `${baseHref}?trace_semantic=${semanticFilter}`;
}

export function resolveTaskDetailFailureTracePreset(
  current: TaskDetailTraceFilterState,
): TaskDetailTraceFilterState {
  void current;
  return {
    traceView: "list",
    traceSemanticFilter: "failure",
    traceKindFilter: "all",
    traceSearchQuery: "",
  };
}

export function resolveTaskDetailSemanticTracePreset(
  semanticFilter: Exclude<TaskDetailTraceSemanticFilter, "all">,
  current: TaskDetailTraceFilterState,
): TaskDetailTraceFilterState {
  void current;
  return {
    traceView: "list",
    traceSemanticFilter: semanticFilter,
    traceKindFilter: "all",
    traceSearchQuery: "",
  };
}

export function resolveTaskDetailSemanticFilterChange(
  semanticFilter: TaskDetailTraceSemanticFilter,
  current: TaskDetailTraceFilterState,
): TaskDetailTraceFilterState {
  return {
    traceView: current.traceView,
    traceSemanticFilter: semanticFilter,
    traceKindFilter: "all",
    traceSearchQuery: "",
  };
}

export function resolveTaskDetailInitialTraceFilterState(
  traceSemanticPreset: string | null | undefined,
): TaskDetailTraceFilterState {
  const normalizedPreset = traceSemanticPreset?.trim().toLowerCase();
  const semanticPreset = TRACE_SEMANTIC_PRESETS.find(
    (preset) => preset === normalizedPreset,
  );
  if (semanticPreset) {
    return resolveTaskDetailSemanticTracePreset(semanticPreset, {
      traceView: "list",
      traceSemanticFilter: "all",
      traceKindFilter: "all",
      traceSearchQuery: "",
    });
  }
  return {
    traceView: "list",
    traceSemanticFilter: "all",
    traceKindFilter: "all",
    traceSearchQuery: "",
  };
}

export function resolveTaskDetailFailureHint(
  hint: string | null | undefined,
  streamErrorByCode?: (code: string) => string | null,
): string | null {
  const normalized = typeof hint === "string" ? hint.trim() : "";
  if (!normalized) {
    return null;
  }
  const mapped = streamErrorByCode?.(normalized)?.trim();
  return mapped && mapped !== normalized ? mapped : normalized;
}

export function resolveTaskDetailTraceSteps(args: {
  primarySteps: TraceStepPayload[];
  fallbackSteps: TraceStepPayload[];
  explicitFailureHint?: string | null;
}): TraceStepPayload[] {
  if (args.primarySteps.length === 0) {
    if (args.fallbackSteps.length > 0) {
      return args.fallbackSteps;
    }
    return buildExplicitFailureTraceSteps(args.explicitFailureHint);
  }
  if (args.primarySteps.some(isFailureTraceStep)) {
    return args.primarySteps;
  }
  const primaryStepIds = new Set(args.primarySteps.map((step) => step.id));
  const fallbackFailureSteps = args.fallbackSteps.filter(
    (step) => !primaryStepIds.has(step.id) && isFailureTraceStep(step),
  );
  if (fallbackFailureSteps.length > 0) {
    return [...args.primarySteps, ...fallbackFailureSteps];
  }
  return [
    ...args.primarySteps,
    ...buildExplicitFailureTraceSteps(args.explicitFailureHint),
  ];
}

function isFailureTraceStep(step: TraceStepPayload): boolean {
  const meta = step.meta;
  if (meta?.error_event) {
    return true;
  }
  const tool = meta?.tool;
  if (
    tool &&
    (
      typeof tool.error === "string" && tool.error.trim().length > 0 ||
      String(tool.status ?? "").trim().toLowerCase() === "error"
    )
  ) {
    return true;
  }
  return isFailureDiagnosticContent(step.content);
}

function buildExplicitFailureTraceSteps(
  explicitFailureHint: string | null | undefined,
): TraceStepPayload[] {
  const hint =
    typeof explicitFailureHint === "string" ? explicitFailureHint.trim() : "";
  if (!hint) {
    return [];
  }
  return [
    {
      id: "task-detail-failure-summary",
      type: "other",
      content: hint,
      meta: {
        error_event: {
          message: hint,
        },
      },
    },
  ];
}
