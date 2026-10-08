import type { TraceStepPayload } from "../../../lib/types/trace.ts";

const TOOL_LIMITS = ["max_rounds", "max_tool_calls", "observation_limit", "repeated_action", "invalid_decision"] as const;
export type AnswerNoticeCode = typeof TOOL_LIMITS[number] | "length" | "content_filter" | "tool_calls";

export function resolveAnswerNotices(steps: TraceStepPayload[]): AnswerNoticeCode[] {
  const final = steps.findLast((step) => step.meta?.step_type === "final_answer");
  if (!final) return [];
  const notices: AnswerNoticeCode[] = [];
  const stop = final.meta?.agent_stop_reason;
  if (TOOL_LIMITS.some((reason) => reason === stop)) notices.push(stop as AnswerNoticeCode);
  const finish = final.meta?.provider_finish_reason;
  if (finish === "length" || finish === "content_filter") notices.push(finish);
  if (finish === "tool_calls" || finish === "function_call") notices.push("tool_calls");
  return notices;
}

export function resolveLatestAnswerNotices(stored: TraceStepPayload[], live: TraceStepPayload[]): AnswerNoticeCode[] {
  const storedFinal = stored.findLast((step) => step.meta?.step_type === "final_answer");
  const liveFinal = live.findLast((step) => step.meta?.step_type === "final_answer");
  return resolveAnswerNotices(liveFinal && (!storedFinal || (liveFinal.seq ?? 0) >= (storedFinal.seq ?? 0)) ? live : stored);
}
