import type { Messages } from "../../../lib/i18n/types";
import type { TraceStepPayload } from "../../../lib/types/trace";

import type { SessionSummary, TaskSummary } from "./types";

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
