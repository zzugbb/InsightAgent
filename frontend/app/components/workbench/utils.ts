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

export function resolveTraceStepDisplayContent(
  step: TraceStepPayload,
): string | null {
  const content = normalizeTraceContent(step.content);
  const preview = stringifyTraceToolOutputPreview(step.meta?.tool?.output_preview);
  if (!preview) {
    return content;
  }
  if (content && content.includes(preview)) {
    return content;
  }
  return content ? `${content}\nPreview: ${preview}` : preview;
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
  if (!semantic) {
    return null;
  }
  if (semantic === "knowledge_retrieval" || semantic.endsWith("_retrieval")) {
    return "retrieval";
  }
  if (semantic === "local_calculator" || semantic.endsWith("_calculator") || semantic.endsWith("_calc")) {
    return "calculator";
  }
  if (semantic === "task_planner" || semantic.endsWith("_planner")) {
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
    lastObservation ??
    findLastStepContent(
      steps,
      (step) => !["tool", "rag", "thought"].includes(normalizeTraceStepKind(step)),
    ) ??
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
    const name = String(meta.tool.label ?? meta.tool.name).trim();
    if (name) {
      const semanticKind = formatTraceToolSemanticDescriptor(meta.tool);
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
  if (stepKind) {
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
