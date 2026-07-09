import type { Messages } from "../../../lib/i18n/types";
import type { TraceStepMeta, TraceStepPayload } from "../../../lib/types/trace";

import type { SseTaskUsage } from "../../../lib/stores/chat-stream-store";

import type { SessionSummary, TaskSummary } from "./types";

export type InspectorUsageRow = {
  prompt: string | null;
  completion: string | null;
  total: string | null;
  cost: string | null;
  promptSource: "provider" | "estimated" | null;
  completionSource: "provider" | "estimated" | null;
  usageSource: "provider" | "estimated" | "legacy" | null;
  planning?: UsageBreakdown | null;
  overall?: UsageBreakdown | null;
};

export type UsageAggregateRow = InspectorUsageRow & {
  taskCount: number;
  avgTotal: string | null;
  avgCost: string | null;
};

export type UsageBreakdown = {
  prompt: string | null;
  completion: string | null;
  total: string | null;
  cost: string | null;
  promptSource: "provider" | "estimated" | null;
  completionSource: "provider" | "estimated" | null;
  usageSource: "provider" | "estimated" | "legacy" | null;
};

export type TaskSnapshotSummary = {
  stepCount: number;
  ragHitCount: number;
  ragKnowledgeBaseIds: string[];
  semanticStats: Record<Exclude<TraceStepSemanticFilter, "all">, number>;
  finalAnswer: string | null;
  lastObservation: string | null;
  governance: {
    profile: string | null;
    providerSource: string | null;
    allowedToolNames: string[];
    allowedToolLabels: string[];
  } | null;
};

export type SessionGovernanceSummary = {
  profiles: string[];
  providerSources: string[];
  allowedToolNames: string[];
  allowedToolLabels: string[];
};

export type TraceStepSemanticFilter =
  | "all"
  | "planner"
  | "retrieval"
  | "calculator";

export type TraceStepKindFilter =
  | "all"
  | "thought"
  | "action"
  | "observation"
  | "tool"
  | "rag"
  | "other";

function parseUsageNumber(v: unknown): number | null {
  if (v === null || v === undefined) {
    return null;
  }
  if (typeof v === "number" && Number.isFinite(v)) {
    return v;
  }
  if (typeof v === "string") {
    const trimmed = v.trim();
    if (!trimmed) {
      return null;
    }
    const num = Number(trimmed);
    return Number.isFinite(num) ? num : null;
  }
  return null;
}

function formatTokenCount(v: unknown): string | null {
  const n = parseUsageNumber(v);
  if (n === null) {
    return null;
  }
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(Math.trunc(n));
}

function formatCost(v: unknown): string | null {
  const n = parseUsageNumber(v);
  if (n === null) {
    return null;
  }
  return `$${n.toFixed(6)}`;
}

function parseUsageSource(
  v: unknown,
): "provider" | "estimated" | null {
  if (typeof v !== "string") {
    return null;
  }
  const normalized = v.trim().toLowerCase();
  if (normalized === "provider" || normalized === "estimated") {
    return normalized;
  }
  return null;
}

function normalizeUsageSection(
  raw: Record<string, unknown>,
  prefix = "",
): UsageBreakdown | null {
  const promptKey = `${prefix}prompt_tokens`;
  const completionKey = `${prefix}completion_tokens`;
  const totalKey = `${prefix}total_tokens`;
  const costKey = `${prefix}cost_estimate`;
  const promptSourceKey = `${prefix}prompt_tokens_source`;
  const completionSourceKey = `${prefix}completion_tokens_source`;
  const usageSourceKey = `${prefix}usage_source`;
  const promptRaw = parseUsageNumber(raw[promptKey]);
  const completionRaw = parseUsageNumber(raw[completionKey]);
  const totalRaw = parseUsageNumber(raw[totalKey]);
  const prompt = formatTokenCount(raw[promptKey]);
  const completion = formatTokenCount(raw[completionKey]);
  const total =
    totalRaw !== null
      ? formatTokenCount(totalRaw)
      : promptRaw !== null || completionRaw !== null
        ? formatTokenCount((promptRaw ?? 0) + (completionRaw ?? 0))
        : null;
  const cost = formatCost(raw[costKey]);
  const promptSource = parseUsageSource(raw[promptSourceKey]);
  const completionSource = parseUsageSource(raw[completionSourceKey]);
  const usageSource =
    parseUsageSource(raw[usageSourceKey]) ??
    (promptSource === "provider" || completionSource === "provider"
      ? "provider"
      : promptSource === "estimated" || completionSource === "estimated"
        ? "estimated"
        : prompt !== null || completion !== null || total !== null || cost !== null
          ? "legacy"
          : null);
  if (prompt === null && completion === null && total === null && cost === null) {
    return null;
  }
  return {
    prompt,
    completion,
    total,
    cost,
    promptSource,
    completionSource,
    usageSource,
  };
}

function normalizeUsageObject(
  raw: Record<string, unknown>,
): InspectorUsageRow | null {
  const base = normalizeUsageSection(raw);
  if (!base) {
    return null;
  }
  return {
    ...base,
    planning: normalizeUsageSection(raw, "planning_"),
    overall: normalizeUsageSection(raw, "overall_"),
  };
}

function parseUsageJson(
  json: string | null | undefined,
): InspectorUsageRow | null {
  if (!json || !json.trim()) {
    return null;
  }
  try {
    const v = JSON.parse(json) as unknown;
    if (!v || typeof v !== "object" || Array.isArray(v)) {
      return null;
    }
    return normalizeUsageObject(v as Record<string, unknown>);
  } catch {
    return null;
  }
}

function parseUsageRaw(
  json: string | null | undefined,
): { prompt: number | null; completion: number | null; cost: number | null } | null {
  if (!json || !json.trim()) {
    return null;
  }
  try {
    const v = JSON.parse(json) as unknown;
    if (!v || typeof v !== "object" || Array.isArray(v)) {
      return null;
    }
    const raw = v as Record<string, unknown>;
    return {
      prompt: parseUsageNumber(raw["prompt_tokens"]),
      completion: parseUsageNumber(raw["completion_tokens"]),
      cost: parseUsageNumber(raw["cost_estimate"]),
    };
  } catch {
    return null;
  }
}

/** 任务列表项：从任务持久化字段 usage_json 解析用量。 */
export function resolveTaskUsageFromTask(
  task: TaskSummary,
): InspectorUsageRow | null {
  return parseUsageJson(task.usage_json);
}

/** 会话任务聚合用量：用于上下文面板展示当前会话的总消耗。 */
export function resolveTasksUsageAggregate(
  tasks: TaskSummary[],
): UsageAggregateRow | null {
  let promptSum = 0;
  let completionSum = 0;
  let costSum = 0;
  let hasPrompt = false;
  let hasCompletion = false;
  let hasCost = false;
  let taskCount = 0;
  let tokenTaskCount = 0;
  let costTaskCount = 0;

  for (const task of tasks) {
    const raw = parseUsageRaw(task.usage_json);
    if (!raw) {
      continue;
    }
    taskCount += 1;
    if (raw.prompt !== null) {
      hasPrompt = true;
      promptSum += raw.prompt;
    }
    if (raw.completion !== null) {
      hasCompletion = true;
      completionSum += raw.completion;
    }
    if (raw.cost !== null) {
      hasCost = true;
      costSum += raw.cost;
      costTaskCount += 1;
    }
    if (raw.prompt !== null || raw.completion !== null) {
      tokenTaskCount += 1;
    }
  }

  const prompt = hasPrompt ? formatTokenCount(promptSum) : null;
  const completion = hasCompletion ? formatTokenCount(completionSum) : null;
  const total =
    hasPrompt || hasCompletion
      ? formatTokenCount(promptSum + completionSum)
      : null;
  const cost = hasCost ? formatCost(costSum) : null;
  const avgTotal =
    tokenTaskCount > 0
      ? formatTokenCount((promptSum + completionSum) / tokenTaskCount)
      : null;
  const avgCost =
    costTaskCount > 0
      ? formatCost(costSum / costTaskCount)
      : null;

  if (!prompt && !completion && !total && !cost && !avgTotal && !avgCost) {
    return null;
  }
  return {
    prompt,
    completion,
    total,
    cost,
    promptSource: null,
    completionSource: null,
    usageSource: null,
    taskCount,
    avgTotal,
    avgCost,
  };
}

/** 上下文面板：当前任务用量（流式 `done` 优先，否则用任务列表中的 usage_json） */
export function resolveInspectorTaskUsage(args: {
  taskId: string | null;
  activeTask: TaskSummary | undefined;
  sseTaskUsage: SseTaskUsage | null;
}): InspectorUsageRow | null {
  const { taskId, activeTask, sseTaskUsage } = args;
  if (taskId && sseTaskUsage?.taskId === taskId) {
    const n = normalizeUsageObject(sseTaskUsage.usage);
    if (n) {
      return n;
    }
  }
  if (activeTask?.id === taskId && activeTask.usage_json) {
    return parseUsageJson(activeTask.usage_json);
  }
  return null;
}

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function formatTimestamp(value: string, localeTag: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(localeTag, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function shortenId(value: string): string {
  if (value.length <= 12) {
    return value;
  }
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
}

export function getSessionLabel(
  session: SessionSummary,
  workbench: Messages["workbench"],
): string {
  if (session.title && session.title.trim()) {
    return session.title.trim();
  }
  return workbench.sessionFallback(shortenId(session.id));
}

export function getTaskLabel(
  task: TaskSummary,
  workbench: Messages["workbench"],
): string {
  const prompt = task.prompt.trim();
  if (!prompt) {
    return workbench.taskFallback(shortenId(task.id));
  }
  return prompt.length > 48 ? `${prompt.slice(0, 48)}...` : prompt;
}

function normalizeTaskStatus(status: string): "running" | "completed" | "failed" | "other" {
  const s = status.trim().toLowerCase();
  if (s === "running" || s === "pending") {
    return "running";
  }
  if (s === "completed" || s === "done" || s === "success") {
    return "completed";
  }
  if (s === "failed" || s === "error") {
    return "failed";
  }
  return "other";
}

export function isTaskFailedStatus(status: string): boolean {
  return normalizeTaskStatus(status) === "failed";
}

export function extractTaskFailureHint(task: TaskSummary): string | null {
  if (!isTaskFailedStatus(task.status) || !task.trace_json?.trim()) {
    return null;
  }
  try {
    const parsed = JSON.parse(task.trace_json) as unknown;
    if (!Array.isArray(parsed) || parsed.length === 0) {
      return null;
    }
    const reversed = [...parsed].reverse();
    for (const step of reversed) {
      if (!step || typeof step !== "object" || Array.isArray(step)) {
        continue;
      }
      const content = (step as { content?: unknown }).content;
      if (typeof content === "string" && content.trim()) {
        const normalized = content.trim().replace(/\s+/g, " ");
        return normalized.length > 96
          ? `${normalized.slice(0, 96)}...`
          : normalized;
      }
    }
    return null;
  } catch {
    return null;
  }
}

function normalizeTraceContent(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function stringifyTraceToolOutputPreview(value: unknown): string | null {
  if (typeof value === "string") {
    return normalizeTraceContent(value);
  }
  if (
    value !== null &&
    value !== undefined &&
    (Array.isArray(value) || typeof value === "object" || typeof value === "number" || typeof value === "boolean")
  ) {
    return JSON.stringify(value);
  }
  return null;
}

function resolveTraceSafeToolOutput(
  tool: TraceStepMeta["tool"],
): unknown | null {
  if (!tool) {
    return null;
  }
  const outputKeys = Array.isArray(tool.effective_result_output_keys)
    ? tool.effective_result_output_keys.filter(
        (item): item is string => typeof item === "string" && item.trim().length > 0,
      )
    : [];
  if (outputKeys.length === 0) {
    return null;
  }
  const output = tool.output;
  if (!output || typeof output !== "object" || Array.isArray(output)) {
    return output;
  }
  return Object.fromEntries(
    outputKeys
      .filter((key) => Object.prototype.hasOwnProperty.call(output, key))
      .map((key) => [key, output[key as keyof typeof output]]),
  );
}

function stringifyTraceSafeToolOutput(
  tool: TraceStepMeta["tool"],
): string | null {
  return stringifyTraceToolOutputPreview(resolveTraceSafeToolOutput(tool));
}

function normalizeTraceToolSemanticKind(v: unknown): string | null {
  if (typeof v !== "string") {
    return null;
  }
  const normalized = v.trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  if (
    normalized === "knowledge_retrieval"
    || normalized.endsWith("knowledge_retrieval")
    || normalized.endsWith("_retrieval")
  ) {
    return "knowledge_retrieval";
  }
  if (normalized === "task_planner" || normalized.endsWith("_planner")) {
    return "task_planner";
  }
  if (
    normalized === "local_calculator"
    || normalized.endsWith("_calculator")
    || normalized.endsWith("_calc")
  ) {
    return "local_calculator";
  }
  return normalized;
}

function normalizeTraceToolLabel(v: unknown): string {
  if (typeof v !== "string") {
    return "";
  }
  const normalized = v.trim().replace(/\s*\[[^[\]]+\]\s*$/, "");
  return normalized.toLowerCase().replaceAll("_", " ").split(/\s+/).filter(Boolean).join(" ");
}

function traceToolLabelImpliesLocalKnowledgeRetrieval(v: unknown): boolean {
  const normalized = normalizeTraceToolLabel(v);
  return normalized === "knowledge retrieval"
    || normalized === "hot retrieval"
    || normalized === "task retrieve"
    || normalized === "task retrieve hot"
    || normalized === "mock retrieve";
}

function traceToolLabelImpliesRealRetrievalSummary(v: unknown): boolean {
  const normalized = normalizeTraceToolLabel(v);
  return normalized === "provider search"
    || normalized === "hosted search"
    || normalized === "provider retrieval";
}

function traceToolLabelImpliesRealCalcSummary(v: unknown): boolean {
  const normalized = normalizeTraceToolLabel(v);
  return normalized === "provider math"
    || normalized === "hosted math"
    || normalized === "provider calc"
    || normalized === "provider calculator"
    || normalized === "hosted calc"
    || normalized === "hosted calculator";
}

function traceToolLabelImpliesPlannerSummary(v: unknown): boolean {
  const normalized = normalizeTraceToolLabel(v);
  return normalized === "task planner"
    || normalized === "provider planner"
    || normalized === "hosted planner"
    || normalized === "mock planner";
}

function normalizeTraceToolResultPlanSteps(v: unknown): string[] {
  if (!Array.isArray(v)) {
    return [];
  }
  return v.filter((step): step is string => typeof step === "string" && step.trim().length > 0)
    .map((step) => step.trim());
}

function resolveTraceToolResultSummaryInput(
  tool: TraceStepMeta["tool"],
): Record<string, unknown> | null {
  if (!tool) {
    return null;
  }
  const safeOutput = resolveTraceSafeToolOutput(tool);
  if (safeOutput && typeof safeOutput === "object" && !Array.isArray(safeOutput)) {
    return safeOutput as Record<string, unknown>;
  }
  const preview = tool.output_preview;
  if (preview && typeof preview === "object" && !Array.isArray(preview)) {
    return preview as Record<string, unknown>;
  }
  return null;
}

function inferTraceToolResultSummary(
  tool: TraceStepMeta["tool"],
): string | null {
  if (!tool) {
    return null;
  }
  const output = resolveTraceToolResultSummaryInput(tool);
  if (!output) {
    return null;
  }
  const rawOutput =
    tool.output && typeof tool.output === "object" && !Array.isArray(tool.output)
      ? tool.output as Record<string, unknown>
      : null;
  const rawPreviewOutput =
    tool.output_preview && typeof tool.output_preview === "object" && !Array.isArray(tool.output_preview)
      ? tool.output_preview as Record<string, unknown>
      : null;

  const explicitSemanticKind = normalizeTraceToolSemanticKind(tool.semantic_kind);
  const fallbackRuntimeKind = normalizeTraceToolSemanticKind(
    tool.kind
      ?? (typeof output.tool_kind === "string" ? output.tool_kind : undefined)
      ?? (typeof output.kind === "string" ? output.kind : undefined)
      ?? (typeof rawOutput?.tool_kind === "string" ? rawOutput.tool_kind : undefined)
      ?? (typeof rawOutput?.kind === "string" ? rawOutput.kind : undefined)
      ?? (typeof rawPreviewOutput?.tool_kind === "string" ? rawPreviewOutput.tool_kind : undefined)
      ?? (typeof rawPreviewOutput?.kind === "string" ? rawPreviewOutput.kind : undefined),
  );
  const runtimeSemanticKind = explicitSemanticKind ?? fallbackRuntimeKind;
  const semanticFamily = normalizeTraceToolSemanticKind(
    tool.semantic_family ?? (typeof output.tool_family === "string" ? output.tool_family : undefined),
  );
  const labelImpliesRealCalc = traceToolLabelImpliesRealCalcSummary(tool.label)
    || traceToolLabelImpliesRealCalcSummary(tool.name);

  const plan = output.plan;
  if (typeof plan === "string" && plan.trim()) {
    return `Planned steps - ${plan.trim()}.`;
  }
  const steps = normalizeTraceToolResultPlanSteps(output.steps);
  if (steps.length > 0) {
    return `Planned steps - ${steps.join(" -> ")}.`;
  }

  const expression = output.expression;
  const result = output.result;
  const requestId = output.request_id;
  if (typeof expression === "string" && expression.trim().length > 0 && result !== undefined && result !== null) {
    if (typeof requestId === "string" && requestId.trim().length > 0) {
      return `Calculated ${expression.trim()} = ${String(result)} (request id ${requestId.trim()}).`;
    }
    return `Calculated ${expression.trim()} = ${String(result)}.`;
  }
  if ((
    semanticFamily === "local_calculator"
    || runtimeSemanticKind === "local_calculator"
    || (
      result !== undefined
      && result !== null
      && semanticFamily === null
      && runtimeSemanticKind === null
      && labelImpliesRealCalc
    )
  ) && result !== undefined && result !== null) {
    if (typeof requestId === "string" && requestId.trim().length > 0) {
      return `Calculated result = ${String(result)} (request id ${requestId.trim()}).`;
    }
    return `Calculated result = ${String(result)}.`;
  }

  const hitCount = output.hit_count;
  const knowledgeBaseId = output.knowledge_base_id;
  if (typeof hitCount === "number" && Number.isInteger(hitCount) && hitCount >= 0) {
    const hitLabel = hitCount === 1 ? "hit" : "hits";
    const labelImpliesLocalRetrieval = traceToolLabelImpliesLocalKnowledgeRetrieval(tool.label)
      || traceToolLabelImpliesLocalKnowledgeRetrieval(tool.name);
    if (
      (
        explicitSemanticKind === "knowledge_retrieval"
        || (
          explicitSemanticKind === null
          && (
            semanticFamily === "knowledge_retrieval"
            || (
              semanticFamily === null
              && labelImpliesLocalRetrieval
            )
          )
        )
      )
      && typeof knowledgeBaseId === "string"
      && knowledgeBaseId.trim().length > 0
    ) {
      if (typeof requestId === "string" && requestId.trim().length > 0) {
        return `Retrieved ${hitCount} ${hitLabel} from knowledge base ${knowledgeBaseId.trim()} (request id ${requestId.trim()}).`;
      }
      return `Retrieved ${hitCount} ${hitLabel} from knowledge base ${knowledgeBaseId.trim()}.`;
    }
    if (
      runtimeSemanticKind !== "knowledge_retrieval"
      && semanticFamily === "knowledge_retrieval"
    ) {
      if (typeof requestId === "string" && requestId.trim().length > 0) {
        return `Retrieved ${hitCount} ${hitLabel} (request id ${requestId.trim()}).`;
      }
      return `Retrieved ${hitCount} ${hitLabel}.`;
    }
    if (typeof requestId === "string" && requestId.trim().length > 0) {
      return `Retrieved ${hitCount} ${hitLabel} (request id ${requestId.trim()}).`;
    }
    return `Retrieved ${hitCount} ${hitLabel}.`;
  }

  const documentsTotal = output.documents_total;
  if (typeof documentsTotal === "number" && Number.isInteger(documentsTotal) && documentsTotal >= 0) {
    const documentLabel = documentsTotal === 1 ? "document" : "documents";
    if (typeof requestId === "string" && requestId.trim().length > 0) {
      return `Retrieved ${documentsTotal} ${documentLabel} (request id ${requestId.trim()}).`;
    }
    return `Retrieved ${documentsTotal} ${documentLabel}.`;
  }
  return null;
}

function humanizeToolRegistryDiagnosticsTarget(target: string): string {
  const normalized = target.trim().toLowerCase();
  if (!normalized) {
    return "diagnostics";
  }
  return normalized.replaceAll("_", " ");
}

function formatTraceToolRegistryDiagnosticsLines(
  meta: TraceStepMeta | undefined,
): string[] {
  const entries = Array.isArray(meta?.tool_registry?.entries)
    ? meta.tool_registry.entries.filter(
        (
          entry,
        ): entry is NonNullable<NonNullable<TraceStepMeta["tool_registry"]>["entries"]>[number] =>
          !!entry &&
          typeof entry.kind === "string" &&
          typeof entry.target === "string",
      )
    : [];
  if (entries.length === 0) {
    return [];
  }
  return entries
    .map((entry) => {
      const values = Array.isArray(entry.values)
        ? entry.values.filter(
            (value): value is string => typeof value === "string" && value.trim().length > 0,
          )
        : [];
      const label = `${entry.kind.trim().toLowerCase()} ${humanizeToolRegistryDiagnosticsTarget(entry.target)}`.trim();
      if (values.length === 0) {
        return label ? `${label}: ${entry.count}` : null;
      }
      return `${label}: ${values.join(", ")}`;
    })
    .filter((line): line is string => typeof line === "string" && line.length > 0);
}

export function resolveTraceStepDisplayContent(
  step: TraceStepPayload,
): string | null {
  const content = normalizeTraceContent(step.content);
  const toolRegistryLines = formatTraceToolRegistryDiagnosticsLines(step.meta);
  const resultSummary =
    typeof step.meta?.tool?.result_summary === "string" &&
    step.meta.tool.result_summary.trim()
      ? step.meta.tool.result_summary.trim()
      : inferTraceToolResultSummary(step.meta?.tool);
  const primaryContent =
    resultSummary && (!content || content.startsWith("Tool done:"))
      ? resultSummary
      : content;
  const preview = stringifyTraceToolOutputPreview(step.meta?.tool?.output_preview);
  const safeOutput = stringifyTraceSafeToolOutput(step.meta?.tool);
  const previewLine =
    preview && !(primaryContent && primaryContent.includes(preview))
      ? `Preview: ${preview}`
      : null;
  const outputLine =
    safeOutput && safeOutput !== preview
      ? `Output: ${safeOutput}`
      : null;
  const baseLines = [primaryContent, previewLine, outputLine].filter(Boolean) as string[];
  const diagnosticsLines = toolRegistryLines.filter((line) =>
    !baseLines.some((baseLine) => baseLine.includes(line)),
  );
  if (baseLines.length === 0) {
    if (diagnosticsLines.length > 0) {
      return diagnosticsLines.join("\n");
    }
    return preview ?? safeOutput;
  }
  return [...baseLines, ...diagnosticsLines].join("\n");
}

export function matchesTraceStepSearchQuery(
  step: TraceStepPayload,
  query: string,
): boolean {
  const q = query.trim().toLowerCase();
  if (!q) {
    return true;
  }
  const title = getStepTitle(step).toLowerCase();
  const content = (resolveTraceStepDisplayContent(step) ?? "").toLowerCase();
  const id = step.id.toLowerCase();
  const model =
    typeof step.meta?.model === "string" ? step.meta.model.toLowerCase() : "";
  const toolName =
    typeof step.meta?.tool?.name === "string"
      ? step.meta.tool.name.toLowerCase()
      : "";
  const toolLabel =
    typeof step.meta?.tool?.label === "string"
      ? step.meta.tool.label.toLowerCase()
      : "";
  const toolKind =
    typeof step.meta?.tool?.kind === "string"
      ? step.meta.tool.kind.toLowerCase()
      : "";
  const toolSemanticKind =
    typeof step.meta?.tool?.semantic_kind === "string"
      ? step.meta.tool.semantic_kind.toLowerCase()
      : "";
  const toolSemanticFamily =
    typeof step.meta?.tool?.semantic_family === "string"
      ? step.meta.tool.semantic_family.toLowerCase()
      : "";
  const toolSemanticCategory = resolveTraceStepSemanticCategory(step) ?? "";
  const previewKeys = Array.isArray(step.meta?.tool?.effective_result_preview_keys)
    ? step.meta?.tool?.effective_result_preview_keys
        .filter((item): item is string => typeof item === "string")
        .map((item) => item.toLowerCase())
    : [];
  const outputKeys = Array.isArray(step.meta?.tool?.effective_result_output_keys)
    ? step.meta?.tool?.effective_result_output_keys
        .filter((item): item is string => typeof item === "string")
        .map((item) => item.toLowerCase())
    : [];
  const executionSummaryParts = formatTraceToolExecutionSummaryParts(step.meta?.tool)
    .map((item) => item.toLowerCase());
  const executionDiagnostics = Array.isArray(step.meta?.tool?.execution_diagnostics)
    ? step.meta.tool.execution_diagnostics
        .filter((item): item is string => typeof item === "string")
        .map((item) => item.toLowerCase())
    : [];
  const safeOutput = stringifyTraceSafeToolOutput(step.meta?.tool)?.toLowerCase() ?? "";
  const ragKnowledgeBaseId =
    typeof step.meta?.rag?.knowledge_base_id === "string"
      ? step.meta.rag.knowledge_base_id.toLowerCase()
      : "";
  const ragChunks = Array.isArray(step.meta?.rag?.chunks)
    ? step.meta.rag.chunks
        .filter((item): item is string => typeof item === "string")
        .map((item) => item.toLowerCase())
    : [];
  return (
    title.includes(q) ||
    content.includes(q) ||
    id.includes(q) ||
    model.includes(q) ||
    toolName.includes(q) ||
    toolLabel.includes(q) ||
    toolKind.includes(q) ||
    toolSemanticKind.includes(q) ||
    toolSemanticFamily.includes(q) ||
    toolSemanticCategory.includes(q) ||
    executionSummaryParts.some((part) => part.includes(q)) ||
    executionDiagnostics.some((diagnostic) => diagnostic.includes(q)) ||
    safeOutput.includes(q) ||
    ragKnowledgeBaseId.includes(q) ||
    ragChunks.some((chunk) => chunk.includes(q)) ||
    previewKeys.some((key) => key.includes(q)) ||
    outputKeys.some((key) => key.includes(q))
  );
}

function normalizeTraceToolSemanticValue(value: unknown): string {
  return typeof value === "string" && value.trim() ? value.trim().toLowerCase() : "";
}

function resolveTraceStepSemanticCategory(
  step: TraceStepPayload,
): Exclude<TraceStepSemanticFilter, "all"> | null {
  if (step.meta?.rag) {
    return "retrieval";
  }
  const semantic =
    normalizeTraceToolSemanticValue(step.meta?.tool?.semantic_family) ||
    normalizeTraceToolSemanticValue(step.meta?.tool?.semantic_kind) ||
    normalizeTraceToolSemanticValue(step.meta?.tool?.kind);
  if (semantic) {
    if (semantic === "knowledge_retrieval" || semantic.endsWith("_retrieval")) {
      return "retrieval";
    }
    if (semantic === "local_calculator" || semantic.endsWith("_calculator") || semantic.endsWith("_calc")) {
      return "calculator";
    }
    if (semantic === "task_planner" || semantic.endsWith("_planner")) {
      return "planner";
    }
  }
  const tool = step.meta?.tool;
  if (!tool) {
    return null;
  }
  const output = resolveTraceToolResultSummaryInput(tool);
  if (!output) {
    return null;
  }
  const labelImpliesRetrieval = traceToolLabelImpliesLocalKnowledgeRetrieval(tool.label)
    || traceToolLabelImpliesLocalKnowledgeRetrieval(tool.name)
    || traceToolLabelImpliesRealRetrievalSummary(tool.label)
    || traceToolLabelImpliesRealRetrievalSummary(tool.name);
  if (
    labelImpliesRetrieval
    && (
      (typeof output.hit_count === "number" && Number.isInteger(output.hit_count) && output.hit_count >= 0)
      || (typeof output.documents_total === "number" && Number.isInteger(output.documents_total) && output.documents_total >= 0)
    )
  ) {
    return "retrieval";
  }
  const labelImpliesCalc = traceToolLabelImpliesRealCalcSummary(tool.label)
    || traceToolLabelImpliesRealCalcSummary(tool.name);
  if (
    labelImpliesCalc
    && output.result !== undefined
    && output.result !== null
  ) {
    return "calculator";
  }
  const labelImpliesPlanner = traceToolLabelImpliesPlannerSummary(tool.label)
    || traceToolLabelImpliesPlannerSummary(tool.name);
  const plan = output.plan;
  const steps = normalizeTraceToolResultPlanSteps(output.steps);
  if (
    labelImpliesPlanner
    && (
      (typeof plan === "string" && plan.trim().length > 0)
      || steps.length > 0
    )
  ) {
    return "planner";
  }
  return null;
}

export function matchesTraceStepSemanticFilter(
  step: TraceStepPayload,
  filter: TraceStepSemanticFilter,
): boolean {
  if (filter === "all") {
    return true;
  }
  return resolveTraceStepSemanticCategory(step) === filter;
}

export function filterTraceSteps(
  steps: TraceStepPayload[],
  args: {
    kindFilter?: TraceStepKindFilter;
    semanticFilter?: TraceStepSemanticFilter;
    searchQuery?: string;
  } = {},
): TraceStepPayload[] {
  const kindFilter = args.kindFilter ?? "all";
  const semanticFilter = args.semanticFilter ?? "all";
  const searchQuery = args.searchQuery ?? "";
  return steps.filter((step) => {
    const kind = normalizeTraceStepKind(step);
    if (kindFilter !== "all" && kind !== kindFilter) {
      return false;
    }
    if (!matchesTraceStepSemanticFilter(step, semanticFilter)) {
      return false;
    }
    return matchesTraceStepSearchQuery(step, searchQuery);
  });
}

export function resolveTraceStepSemanticStats(
  steps: TraceStepPayload[],
): Record<Exclude<TraceStepSemanticFilter, "all">, number> {
  const stats = {
    planner: 0,
    retrieval: 0,
    calculator: 0,
  };
  for (const step of steps) {
    const semantic = resolveTraceStepSemanticCategory(step);
    if (semantic && semantic in stats) {
      stats[semantic] += 1;
    }
  }
  return stats;
}

export function formatTraceStepSemanticStatsSummary(
  stats: Record<Exclude<TraceStepSemanticFilter, "all">, number>,
  labels: Record<Exclude<TraceStepSemanticFilter, "all">, string>,
): string {
  return [
    `${labels.planner} ${stats.planner}`,
    `${labels.retrieval} ${stats.retrieval}`,
    `${labels.calculator} ${stats.calculator}`,
  ].join(" · ");
}

function formatTraceToolSemanticDescriptor(tool: TraceStepMeta["tool"]): string {
  if (!tool) {
    return "";
  }
  const semanticKind =
    typeof tool.semantic_kind === "string" && tool.semantic_kind.trim()
      ? tool.semantic_kind.trim()
      : typeof tool.kind === "string" && tool.kind.trim()
        ? tool.kind.trim()
        : "";
  const semanticFamily =
    typeof tool.semantic_family === "string" && tool.semantic_family.trim()
      ? tool.semantic_family.trim()
      : "";
  if (!semanticKind) {
    return semanticFamily;
  }
  if (!semanticFamily || semanticFamily === semanticKind) {
    return semanticKind;
  }
  return `${semanticKind} · ${semanticFamily}`;
}

function formatTraceStepDerivedSemanticDescriptor(
  step: TraceStepPayload,
): string {
  const explicitDescriptor = formatTraceToolSemanticDescriptor(step.meta?.tool);
  if (explicitDescriptor) {
    return explicitDescriptor;
  }
  const category = resolveTraceStepSemanticCategory(step);
  return category ?? "";
}

const TRACE_TOOL_DISPLAY_ACRONYMS: Record<string, string> = {
  api: "API",
  csv: "CSV",
  http: "HTTP",
  https: "HTTPS",
  id: "ID",
  json: "JSON",
  kb: "KB",
  llm: "LLM",
  rag: "RAG",
  sse: "SSE",
  sql: "SQL",
  ui: "UI",
  url: "URL",
  ux: "UX",
};

function normalizeToolRegistryName(value: string): string {
  const normalized = value
    .trim()
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
  return normalized;
}

function humanizeToolRegistryName(value: string): string {
  const normalized = normalizeToolRegistryName(value);
  if (!normalized) {
    return "";
  }
  return normalized
    .split("_")
    .filter((part) => part.length > 0)
    .map((part) => TRACE_TOOL_DISPLAY_ACRONYMS[part] ?? `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

function resolveTraceToolDisplayLabel(tool: TraceStepMeta["tool"]): string {
  if (!tool) {
    return "";
  }
  const rawName =
    typeof tool.name === "string" && tool.name.trim()
      ? tool.name.trim()
      : "";
  const rawLabel =
    typeof tool.label === "string" && tool.label.trim()
      ? tool.label.trim()
      : "";
  if (!rawName) {
    return rawLabel;
  }
  const canonicalLabel = humanizeToolRegistryName(rawName);
  if (!rawLabel) {
    return canonicalLabel;
  }
  if (normalizeToolRegistryName(rawLabel) === normalizeToolRegistryName(rawName)) {
    return canonicalLabel;
  }
  return rawLabel;
}

function formatTraceToolExecutionSummaryParts(
  tool: TraceStepMeta["tool"],
): string[] {
  const executionSummary = tool?.execution_summary;
  if (!executionSummary) {
    return [];
  }
  const parts: string[] = [];
  const method =
    typeof executionSummary.method === "string" && executionSummary.method.trim()
      ? executionSummary.method.trim().toUpperCase()
      : "";
  const urlOrigin =
    typeof executionSummary.url_origin === "string" && executionSummary.url_origin.trim()
      ? executionSummary.url_origin.trim()
      : "";
  const urlPath =
    typeof executionSummary.url_path === "string" && executionSummary.url_path.trim()
      ? executionSummary.url_path.trim()
      : "";
  const endpoint = `${urlOrigin}${urlPath}`;
  if (method || endpoint) {
    parts.push([method, endpoint].filter((item) => item.length > 0).join(" "));
  }
  const headerCount = executionSummary.header_count;
  if (typeof headerCount === "number" && Number.isFinite(headerCount) && headerCount > 0) {
    parts.push(`headers ${Math.trunc(headerCount)}`);
  }
  const queryParamCount = executionSummary.query_param_count;
  if (
    typeof queryParamCount === "number"
    && Number.isFinite(queryParamCount)
    && queryParamCount > 0
  ) {
    parts.push(`query ${Math.trunc(queryParamCount)}`);
  }
  const jsonBodyFieldCount = executionSummary.json_body_field_count;
  if (
    typeof jsonBodyFieldCount === "number"
    && Number.isFinite(jsonBodyFieldCount)
    && jsonBodyFieldCount > 0
  ) {
    parts.push(`body ${Math.trunc(jsonBodyFieldCount)}`);
  }
  const responsePath =
    typeof executionSummary.response_path === "string" && executionSummary.response_path.trim()
      ? executionSummary.response_path.trim()
      : "";
  if (responsePath) {
    parts.push(`response ${responsePath}`);
  }
  const resultFieldNames = Array.isArray(executionSummary.result_field_names)
    ? executionSummary.result_field_names
        .filter((item): item is string => typeof item === "string" && item.trim().length > 0)
        .map((item) => item.trim())
    : [];
  if (resultFieldNames.length > 0) {
    parts.push(`fields ${resultFieldNames.join(", ")}`);
  }
  return parts;
}

function formatTraceToolExecutionSummary(
  tool: TraceStepMeta["tool"],
  labels: Messages["inspector"]["traceMeta"],
): string | null {
  const parts = formatTraceToolExecutionSummaryParts(tool);
  if (parts.length === 0) {
    return null;
  }
  return labels.toolExecutionSummary(parts.join(" · "));
}

function formatTraceToolExecutionDiagnostics(
  tool: TraceStepMeta["tool"],
  labels: Messages["inspector"]["traceMeta"],
): string | null {
  const diagnostics = Array.isArray(tool?.execution_diagnostics)
    ? tool.execution_diagnostics
        .filter((item): item is string => typeof item === "string" && item.trim().length > 0)
        .map((item) => item.trim())
    : [];
  if (diagnostics.length === 0) {
    return null;
  }
  return labels.toolExecutionDiagnostics(diagnostics.join(", "));
}

function formatTraceToolDisplayTitle(tool: TraceStepMeta["tool"]): string {
  if (!tool) {
    return "";
  }
  const toolLabel = resolveTraceToolDisplayLabel(tool);
  if (!toolLabel) {
    return "";
  }
  const semanticDescriptor = formatTraceToolSemanticDescriptor(tool);
  return semanticDescriptor ? `${toolLabel} [${semanticDescriptor}]` : toolLabel;
}

function sortTraceStepsBySeq(steps: TraceStepPayload[]): TraceStepPayload[] {
  return [...steps]
    .map((step, index) => ({ step, index }))
    .sort((a, b) => {
      const aSeq =
        typeof a.step.seq === "number" ? a.step.seq : Number.MAX_SAFE_INTEGER;
      const bSeq =
        typeof b.step.seq === "number" ? b.step.seq : Number.MAX_SAFE_INTEGER;
      if (aSeq === bSeq) {
        return a.index - b.index;
      }
      return aSeq - bSeq;
    })
    .map((entry) => entry.step);
}

export function parseTaskTraceJson(
  traceJson: string | null | undefined,
): TraceStepPayload[] {
  if (!traceJson || !traceJson.trim()) {
    return [];
  }
  try {
    const parsed = JSON.parse(traceJson) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    const steps: TraceStepPayload[] = [];
    for (let i = 0; i < parsed.length; i += 1) {
      const raw = parsed[i];
      if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        continue;
      }
      const row = raw as Record<string, unknown>;
      const id =
        typeof row.id === "string" && row.id.trim()
          ? row.id.trim()
          : `trace-${i + 1}`;
      const type =
        typeof row.type === "string" && row.type.trim()
          ? row.type.trim()
          : "other";
      const content = typeof row.content === "string" ? row.content : "";
      const seq =
        typeof row.seq === "number" && Number.isFinite(row.seq)
          ? row.seq
          : undefined;
      const meta =
        row.meta && typeof row.meta === "object" && !Array.isArray(row.meta)
          ? (row.meta as TraceStepPayload["meta"])
          : undefined;
      steps.push({
        id,
        type,
        content,
        ...(seq !== undefined ? { seq } : {}),
        ...(meta ? { meta } : {}),
      });
    }
    return sortTraceStepsBySeq(steps);
  } catch {
    return [];
  }
}

function findLastStepContent(
  steps: TraceStepPayload[],
  predicate?: (step: TraceStepPayload) => boolean,
): string | null {
  for (let i = steps.length - 1; i >= 0; i -= 1) {
    const step = steps[i];
    if (predicate && !predicate(step)) {
      continue;
    }
    const content = resolveTraceStepDisplayContent(step);
    if (content) {
      return content;
    }
  }
  return null;
}

export function resolveTaskSnapshotSummary(args: {
  task: TaskSummary;
  traceSteps?: TraceStepPayload[];
}): TaskSnapshotSummary {
  const steps =
    args.traceSteps && args.traceSteps.length > 0
      ? sortTraceStepsBySeq(args.traceSteps)
      : parseTaskTraceJson(args.task.trace_json);

  let ragHitCount = 0;
  const ragKnowledgeBaseIds = new Set<string>();
  for (const step of steps) {
    const ragMeta = step.meta?.rag;
    if (!ragMeta) {
      continue;
    }
    if (Array.isArray(ragMeta.chunks)) {
      ragHitCount += ragMeta.chunks.length;
    }
    if (
      typeof ragMeta.knowledge_base_id === "string" &&
      ragMeta.knowledge_base_id.trim()
    ) {
      ragKnowledgeBaseIds.add(ragMeta.knowledge_base_id.trim());
    }
  }

  const semanticStats = resolveTraceStepSemanticStats(steps);
  const lastObservation = findLastStepContent(
    steps,
    (step) => normalizeTraceStepKind(step) === "observation",
  );
  const finalAnswer =
    findLastStepContent(
      steps,
      (step) => !["tool", "rag", "thought"].includes(normalizeTraceStepKind(step)),
    ) ??
    lastObservation ??
    findLastStepContent(steps);

  const taskGovernance = args.task.governance;
  const governanceFromTask =
    taskGovernance &&
    (
      (typeof taskGovernance.profile === "string" && taskGovernance.profile.trim().length > 0)
      || (
        typeof taskGovernance.provider_source === "string"
        && taskGovernance.provider_source.trim().length > 0
      )
      || taskGovernance.allowed_tool_names.length > 0
      || taskGovernance.allowed_tool_labels.length > 0
    )
      ? {
          profile:
            typeof taskGovernance.profile === "string" && taskGovernance.profile.trim().length > 0
              ? taskGovernance.profile.trim()
              : null,
          providerSource:
            typeof taskGovernance.provider_source === "string"
            && taskGovernance.provider_source.trim().length > 0
              ? taskGovernance.provider_source.trim()
              : null,
          allowedToolNames: taskGovernance.allowed_tool_names
            .filter((item) => typeof item === "string")
            .map((item) => item.trim())
            .filter(Boolean),
          allowedToolLabels: taskGovernance.allowed_tool_labels
            .filter((item) => typeof item === "string")
            .map((item) => item.trim())
            .filter(Boolean),
        }
      : null;

  let governance: TaskSnapshotSummary["governance"] = governanceFromTask;
  for (const step of steps) {
    if (governance !== null) {
      break;
    }
    const meta = step.meta;
    if (!meta) {
      continue;
    }
    const profile =
      typeof meta.tool_registry_profile === "string" &&
      meta.tool_registry_profile.trim().length > 0
        ? meta.tool_registry_profile.trim()
        : null;
    const providerSource =
      typeof meta.tool_registry_provider_source === "string" &&
      meta.tool_registry_provider_source.trim().length > 0
        ? meta.tool_registry_provider_source.trim()
        : null;
    const allowedToolNames = Array.isArray(meta.allowed_tool_names)
      ? meta.allowed_tool_names
          .filter((item): item is string => typeof item === "string")
          .map((item) => item.trim())
          .filter(Boolean)
      : [];
    const allowedToolLabels = Array.isArray(meta.allowed_tool_labels)
      ? meta.allowed_tool_labels
          .filter((item): item is string => typeof item === "string")
          .map((item) => item.trim())
          .filter(Boolean)
      : [];
    if (
      profile === null &&
      providerSource === null &&
      allowedToolNames.length === 0 &&
      allowedToolLabels.length === 0
    ) {
      continue;
    }
    governance = {
      profile,
      providerSource,
      allowedToolNames,
      allowedToolLabels,
    };
    break;
  }

  return {
    stepCount: steps.length,
    ragHitCount,
    ragKnowledgeBaseIds: [...ragKnowledgeBaseIds],
    semanticStats,
    finalAnswer,
    lastObservation,
    governance,
  };
}

export function resolveSessionGovernanceSummary(
  tasks: TaskSummary[],
): SessionGovernanceSummary | null {
  const profiles = new Set<string>();
  const providerSources = new Set<string>();
  const allowedToolNames = new Set<string>();
  const allowedToolLabels = new Set<string>();

  for (const task of tasks) {
    const governance = resolveTaskSnapshotSummary({ task }).governance;
    if (!governance) {
      continue;
    }
    if (governance.profile) {
      profiles.add(governance.profile);
    }
    if (governance.providerSource) {
      providerSources.add(governance.providerSource);
    }
    for (const item of governance.allowedToolNames) {
      if (item.trim()) {
        allowedToolNames.add(item.trim());
      }
    }
    for (const item of governance.allowedToolLabels) {
      if (item.trim()) {
        allowedToolLabels.add(item.trim());
      }
    }
  }

  if (
    profiles.size === 0
    && providerSources.size === 0
    && allowedToolNames.size === 0
    && allowedToolLabels.size === 0
  ) {
    return null;
  }

  return {
    profiles: [...profiles].sort(),
    providerSources: [...providerSources].sort(),
    allowedToolNames: [...allowedToolNames].sort(),
    allowedToolLabels: [...allowedToolLabels].sort(),
  };
}

export function getRoleLabel(role: string, roles: Messages["roles"]): string {
  if (role === "user") {
    return roles.user;
  }
  if (role === "assistant") {
    return roles.assistantName;
  }
  return role;
}

/**
 * 流程图节点视觉分类：优先 `meta.tool` / `meta.rag`，其次 `type`；
 * 与主计划 TraceStep 契约一致。
 */
export function normalizeTraceStepKind(
  step: TraceStepPayload,
):
  | "thought"
  | "action"
  | "observation"
  | "tool"
  | "rag"
  | "other" {
  if (step.meta?.tool) {
    return "tool";
  }
  if (step.meta?.rag) {
    return "rag";
  }
  const t = String(step.type ?? "").toLowerCase();
  if (t === "thought") {
    return "thought";
  }
  if (t === "action") {
    return "action";
  }
  if (t === "observation") {
    return "observation";
  }
  if (t === "tool") {
    return "tool";
  }
  if (t === "rag") {
    return "rag";
  }
  return "other";
}

export function getTraceFlowKindLabel(
  kind: ReturnType<typeof normalizeTraceStepKind>,
  labels: Messages["inspector"]["traceFlow"],
): string {
  switch (kind) {
    case "thought":
      return labels.kindThought;
    case "action":
      return labels.kindAction;
    case "observation":
      return labels.kindObservation;
    case "tool":
      return labels.kindTool;
    case "rag":
      return labels.kindRag;
    default:
      return labels.kindOther;
  }
}

export function getStepTitle(step: TraceStepPayload): string {
  const tool = step.meta?.tool;
  if (tool) {
    const toolLabel = resolveTraceToolDisplayLabel(tool);
    if (toolLabel) {
      const semanticDescriptor = formatTraceStepDerivedSemanticDescriptor(step);
      return semanticDescriptor ? `${toolLabel} [${semanticDescriptor}]` : toolLabel;
    }
  }
  if (step.meta?.rag) {
    return "Knowledge Retrieval Snippets";
  }
  const rawTitle =
    typeof step.meta?.label === "string"
      ? step.meta.label
      : typeof step.meta?.step_type === "string"
        ? step.meta.step_type
        : step.type;
  return String(rawTitle).replace(/_/g, " ");
}

export function formatTraceStepMetaSubtitle(
  step: TraceStepPayload,
  labels: Messages["inspector"]["traceMeta"],
): string | null {
  const meta = step.meta;
  if (!meta) {
    return null;
  }
  const model = typeof meta.model === "string" ? meta.model.trim() : "";
  const stepKind =
    typeof meta.step_type === "string" ? meta.step_type.replace(/_/g, " ") : "";
  let tokensPart: string | undefined;
  if ("tokens" in meta) {
    const t = meta.tokens;
    tokensPart =
      t === null || t === undefined ? "—" : String(t);
  }
  let promptTokensPart: string | undefined;
  if ("prompt_tokens" in meta) {
    const t = meta.prompt_tokens;
    promptTokensPart =
      t === null || t === undefined ? "—" : String(t);
  }
  let completionTokensPart: string | undefined;
  if ("completion_tokens" in meta) {
    const t = meta.completion_tokens;
    completionTokensPart =
      t === null || t === undefined ? "—" : String(t);
  }
  let costPart: string | undefined;
  if ("cost_estimate" in meta) {
    const c = meta.cost_estimate;
    if (typeof c === "number" && Number.isFinite(c)) {
      costPart = `$${c.toFixed(6)}`;
    } else if (c === null || c === undefined) {
      costPart = "—";
    }
  }
  const parts: string[] = [];
  if (meta.tool?.name) {
    const name = resolveTraceToolDisplayLabel(meta.tool);
    if (name) {
      const semanticKind = formatTraceStepDerivedSemanticDescriptor(step);
      const toolLine = labels.toolLine(name, String(meta.tool.status ?? ""));
      parts.push(
        semanticKind ? `${toolLine} [${semanticKind}]` : toolLine,
      );
      const retryCountRaw = meta.tool.retry_count;
      if (typeof retryCountRaw === "number" && retryCountRaw > 0) {
        parts.push(labels.toolRetry(retryCountRaw));
      }
      const errRaw = meta.tool.error;
      if (typeof errRaw === "string" && errRaw.trim()) {
        parts.push(labels.toolError(errRaw.trim()));
      }
      if (meta.tool.supports_result_preview === false) {
        parts.push(labels.toolPreviewDisabled);
      } else if (
        Array.isArray(meta.tool.effective_result_preview_keys)
        && meta.tool.effective_result_preview_keys.length > 0
      ) {
        const previewKeys = meta.tool.effective_result_preview_keys
          .filter((key): key is string => typeof key === "string" && key.trim().length > 0)
          .map((key) => key.trim());
        if (previewKeys.length > 0) {
          parts.push(labels.toolPreviewKeys(previewKeys));
        }
      }
      if (
        Array.isArray(meta.tool.effective_result_output_keys)
        && meta.tool.effective_result_output_keys.length > 0
      ) {
        const outputKeys = meta.tool.effective_result_output_keys
          .filter((key): key is string => typeof key === "string" && key.trim().length > 0)
          .map((key) => key.trim());
        if (outputKeys.length > 0) {
          parts.push(labels.toolOutputKeys(outputKeys));
        }
      }
      const executionSummary = formatTraceToolExecutionSummary(meta.tool, labels);
      if (executionSummary) {
        parts.push(executionSummary);
      }
      const executionDiagnostics = formatTraceToolExecutionDiagnostics(meta.tool, labels);
      if (executionDiagnostics) {
        parts.push(executionDiagnostics);
      }
    }
  }
  if (meta.rag?.chunks?.length) {
    const n = meta.rag.chunks.length;
    const kb =
      typeof meta.rag.knowledge_base_id === "string"
        ? meta.rag.knowledge_base_id.trim()
        : undefined;
    parts.push(labels.ragLine(n, kb));
  }
  if (model) {
    parts.push(`${labels.model} ${model}`);
  }
  if (stepKind && !meta.rag) {
    parts.push(`${labels.stepKind} ${stepKind}`);
  }
  if (typeof meta.planning_provider_attempted === "boolean") {
    if (meta.planning_provider_attempted) {
      parts.push(
        meta.planning_provider_used
          ? labels.planningProviderUsed
          : labels.planningProviderFallback,
      );
    } else {
      parts.push(labels.planningProviderRuleOnly);
    }
  } else if (typeof meta.planning_provider_used === "boolean") {
    parts.push(
      meta.planning_provider_used
        ? labels.planningProviderUsed
        : labels.planningProviderFallback,
    );
  }
  if (
    typeof meta.tool_registry_profile === "string"
    && meta.tool_registry_profile.trim().length > 0
  ) {
    parts.push(
      `${labels.toolRegistryProfile} ${meta.tool_registry_profile.trim()}`,
    );
  }
  if (
    typeof meta.tool_registry_provider_source === "string"
    && meta.tool_registry_provider_source.trim().length > 0
  ) {
    parts.push(
      `${labels.toolRegistrySource} ${meta.tool_registry_provider_source.trim()}`,
    );
  }
  const allowedToolLabels = Array.isArray(meta.allowed_tool_labels)
    ? meta.allowed_tool_labels
        .map((item) => (typeof item === "string" ? item.trim() : ""))
        .filter((item) => item.length > 0)
    : [];
  const allowedToolNames =
    allowedToolLabels.length > 0
      ? allowedToolLabels
      : Array.isArray(meta.allowed_tool_names)
        ? meta.allowed_tool_names
            .map((item) => (typeof item === "string" ? item.trim() : ""))
            .filter((item) => item.length > 0)
        : [];
  if (allowedToolNames.length > 0) {
    parts.push(`${labels.allowedTools} ${allowedToolNames.join(", ")}`);
  }
  if (tokensPart !== undefined) {
    parts.push(`${labels.tokens} ${tokensPart}`);
  }
  if (promptTokensPart !== undefined) {
    parts.push(`${labels.promptTokens} ${promptTokensPart}`);
  }
  if (completionTokensPart !== undefined) {
    parts.push(`${labels.completionTokens} ${completionTokensPart}`);
  }
  if (costPart !== undefined) {
    parts.push(`${labels.cost} ${costPart}`);
  }
  if (typeof meta.usage_source === "string" && meta.usage_source.trim()) {
    const usageSource = meta.usage_source.trim().toLowerCase();
    const usageSourceLabel =
      usageSource === "provider"
        ? labels.usageSourceProvider
        : usageSource === "estimated"
          ? labels.usageSourceEstimated
          : usageSource === "legacy"
            ? labels.usageSourceLegacy
            : usageSource;
    parts.push(`${labels.usageSource} ${usageSourceLabel}`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}

/**
 * Inspector Memory 调试区：解析可选 metadata JSON。
 * 仅接受对象为根、且键值均为字符串（与后端 `POST .../memory/add` 对齐）。
 */
export function parseMemoryMetadataJson(
  raw: string,
):
  | { ok: true; metadata: Record<string, string> | null }
  | { ok: false } {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { ok: true, metadata: null };
  }
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (
      parsed === null ||
      typeof parsed !== "object" ||
      Array.isArray(parsed)
    ) {
      return { ok: false };
    }
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(parsed as Record<string, unknown>)) {
      if (typeof k !== "string" || k.length === 0) {
        continue;
      }
      if (typeof v !== "string") {
        return { ok: false };
      }
      out[k] = v;
    }
    return {
      ok: true,
      metadata: Object.keys(out).length > 0 ? out : null,
    };
  } catch {
    return { ok: false };
  }
}
