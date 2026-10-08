import type { AnswerCompletionPayload, TraceStepPayload } from "../../../lib/types/trace.ts";

const TOOL_LIMITS = ["max_rounds", "max_tool_calls", "observation_limit", "repeated_action", "invalid_decision"] as const;
export type AnswerNoticeCode = typeof TOOL_LIMITS[number] | "length" | "content_filter" | "tool_calls";

export function resolveAnswerNotices(steps: TraceStepPayload[]): AnswerNoticeCode[] {
  const final = steps.findLast((step) => step.meta?.step_type === "final_answer");
  return resolveCompletionNotices(final?.meta);
}

function resolveCompletionNotices(completion?: AnswerCompletionPayload | null): AnswerNoticeCode[] {
  const notices: AnswerNoticeCode[] = [];
  const stop = completion?.agent_stop_reason;
  if (TOOL_LIMITS.some((reason) => reason === stop)) notices.push(stop as AnswerNoticeCode);
  const finish = completion?.provider_finish_reason;
  if (finish === "length" || finish === "content_filter") notices.push(finish);
  if (finish === "tool_calls" || finish === "function_call") notices.push("tool_calls");
  return notices;
}

function sequence(value: unknown): number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? value : 0;
}

export function resolveLatestAnswerNotices(
  stored: TraceStepPayload[], live: TraceStepPayload[], completion?: AnswerCompletionPayload | null,
): AnswerNoticeCode[] {
  const storedFinal = stored.findLast((step) => step.meta?.step_type === "final_answer");
  const liveFinal = live.findLast((step) => step.meta?.step_type === "final_answer");
  const latest = liveFinal && (!storedFinal || sequence(liveFinal.seq) >= sequence(storedFinal.seq)) ? liveFinal : storedFinal;
  // Persisted messages win ties against a task page; an equally current active stream wins its tie.
  if (completion && typeof completion === "object" && !Array.isArray(completion)
      && (!latest || sequence(completion.seq) > sequence(latest.seq)
          || (sequence(completion.seq) === sequence(latest.seq) && latest !== liveFinal))) {
    return resolveCompletionNotices(completion);
  }
  return resolveCompletionNotices(latest?.meta);
}
