import type { Messages } from "../../../lib/i18n/types";
import type { TraceStepPayload } from "../../../lib/stores/chat-stream-store";

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

export function getStepTitle(step: TraceStepPayload): string {
  const rawTitle =
    typeof step.meta?.label === "string"
      ? step.meta.label
      : typeof step.meta?.step_type === "string"
        ? step.meta.step_type
        : step.type;
  return String(rawTitle).replace(/_/g, " ");
}
