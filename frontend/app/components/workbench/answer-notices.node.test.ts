import assert from "node:assert/strict";
import test from "node:test";
import { resolveAnswerNotices, resolveLatestAnswerNotices } from "./answer-notices.ts";
import type { TraceStepPayload } from "../../../lib/types/trace.ts";

function final(meta: Record<string, unknown>): TraceStepPayload {
  return { id: "answer", type: "observation", content: "answer", meta: { step_type: "final_answer", ...meta } };
}

test("known tool stops and generation limits remain separate notices", () => {
  for (const reason of ["max_rounds", "max_tool_calls", "observation_limit", "repeated_action", "invalid_decision"]) {
    assert.deepEqual(resolveAnswerNotices([final({ agent_stop_reason: reason, provider_finish_reason: "length" })]), [reason, "length"]);
  }
});
test("normal endings and missing old metadata do not imply incomplete answers", () => {
  for (const meta of [{}, { provider_finish_reason: "stop", agent_stop_reason: "no_tools" },
    { provider_finish_reason: "unknown", agent_stop_reason: "continue" }]) {
    assert.deepEqual(resolveAnswerNotices([final(meta)]), []);
  }
  assert.deepEqual(resolveAnswerNotices([]), []);
});
test("filtering and tool-request endings map to user-facing notices", () => {
  assert.deepEqual(resolveAnswerNotices([final({ provider_finish_reason: "content_filter" })]), ["content_filter"]);
  assert.deepEqual(resolveAnswerNotices([final({ provider_finish_reason: "function_call" })]), ["tool_calls"]);
  assert.deepEqual(resolveAnswerNotices([final({ provider_finish_reason: "tool_calls" })]), ["tool_calls"]);
});
test("only the final answer metadata can cause warnings", () => {
  const planner: TraceStepPayload = { id: "plan", type: "thought", content: "plan", meta: { provider_finish_reason: "length" } };
  assert.deepEqual(resolveAnswerNotices([planner]), []);
  assert.deepEqual(resolveAnswerNotices([planner, final({})]), []);
  assert.deepEqual(resolveAnswerNotices([final({ provider_finish_reason: "length" }), final({ provider_finish_reason: "stop" })]), []);
});

test("a stale live snapshot cannot hide a newer persisted completion reason", () => {
  const stored = { ...final({ provider_finish_reason: "length" }), seq: 5 };
  const live = { ...final({}), seq: 3 };
  assert.deepEqual(resolveLatestAnswerNotices([stored], [live]), ["length"]);
  assert.deepEqual(resolveLatestAnswerNotices([stored], []), ["length"]);
  assert.deepEqual(resolveLatestAnswerNotices([live], [stored]), ["length"]);
  assert.deepEqual(resolveLatestAnswerNotices([], [stored]), ["length"]);
});
