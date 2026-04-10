import type { Messages } from "../../../lib/i18n/types";
import type { TraceStepPayload } from "../../../lib/types/trace";

import type { SseTaskUsage } from "../../../lib/stores/chat-stream-store";

import type { SessionSummary, TaskSummary } from "./types";

export type InspectorUsageRow = {
  prompt: string | null;
  completion: string | null;
  total: string | null;
  cost: string | null;
};

export type UsageAggregateRow = InspectorUsageRow & {
  taskCount: number;
  avgTotal: string | null;
  avgCost: string | null;
};

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

function normalizeUsageObject(
  raw: Record<string, unknown>,
): InspectorUsageRow | null {
  const promptRaw = parseUsageNumber(raw["prompt_tokens"]);
  const completionRaw = parseUsageNumber(raw["completion_tokens"]);
  const prompt = formatTokenCount(raw["prompt_tokens"]);
  const completion = formatTokenCount(raw["completion_tokens"]);
  const total =
    promptRaw !== null || completionRaw !== null
      ? formatTokenCount((promptRaw ?? 0) + (completionRaw ?? 0))
      : null;
  const cost = formatCost(raw["cost_estimate"]);
  if (prompt === null && completion === null && total === null && cost === null) {
    return null;
  }
  return { prompt, completion, total, cost };
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
  return { prompt, completion, total, cost, taskCount, avgTotal, avgCost };
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
  const parts: string[] = [];
  if (meta.tool?.name) {
    const name = String(meta.tool.name).trim();
    if (name) {
      parts.push(labels.toolLine(name, String(meta.tool.status ?? "")));
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
  if (tokensPart !== undefined) {
    parts.push(`${labels.tokens} ${tokensPart}`);
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
