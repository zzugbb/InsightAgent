import test from "node:test";
import assert from "node:assert/strict";
import { resolveTasksUsageAggregate, resolveTaskUsageFromTask } from "./utils.ts";
import type { TaskSummary } from "./types.ts";

function task(usage: Record<string, unknown>): TaskSummary {
  return {
    id: "fixture", session_id: "fixture", prompt: "fixture", status: "completed",
    trace_json: null, usage_json: JSON.stringify(usage), created_at: "fixture", updated_at: "fixture",
  };
}

test("session totals include planning once and preserve the task breakdown", () => {
  const row = task({ prompt_tokens: 30, completion_tokens: 5, cost_estimate: 0.04,
    planning_prompt_tokens: 30, planning_completion_tokens: 6, planning_cost_estimate: 0.05,
    overall_prompt_tokens: 60, overall_completion_tokens: 11, overall_cost_estimate: 0.09 });
  const aggregate = resolveTasksUsageAggregate([row]);
  assert.equal(aggregate?.total, "71");
  assert.equal(aggregate?.cost, "$0.090000");
  assert.equal(aggregate?.avgTotal, "71");
  const breakdown = resolveTaskUsageFromTask(row);
  assert.equal(breakdown?.total, "35");
  assert.equal(breakdown?.planning?.total, "36");
  assert.equal(breakdown?.overall?.total, "71");
});

test("overall zero and numeric strings take precedence without double counting", () => {
  const aggregate = resolveTasksUsageAggregate([task({ prompt_tokens: 3, completion_tokens: 2,
    planning_prompt_tokens: 4, overall_prompt_tokens: "7", overall_completion_tokens: 0,
    cost_estimate: 1, planning_cost_estimate: 2, overall_cost_estimate: 0 })]);
  assert.equal(aggregate?.total, "7");
  assert.equal(aggregate?.cost, "$0.000000");
});

test("missing overall fields use final plus planning individually", () => {
  const aggregate = resolveTasksUsageAggregate([task({ prompt_tokens: "10", completion_tokens: 2,
    cost_estimate: "0.1", planning_prompt_tokens: 5, planning_completion_tokens: "3",
    planning_cost_estimate: "0.2", overall_prompt_tokens: 15 })]);
  assert.equal(aggregate?.prompt, "15");
  assert.equal(aggregate?.completion, "5");
  assert.equal(aggregate?.cost, "$0.300000");
});

test("invalid overall values fall back to known stage values", () => {
  for (const invalid of [null, "", "bad", true, -1, "NaN", "Infinity"]) {
    const aggregate = resolveTasksUsageAggregate([task({ prompt_tokens: 3,
      planning_prompt_tokens: 4, overall_prompt_tokens: invalid })]);
    assert.equal(aggregate?.total, "7");
  }
});

test("legacy and planning-only records retain their known values and averages", () => {
  const aggregate = resolveTasksUsageAggregate([
    task({ prompt_tokens: 10, completion_tokens: 4, cost_estimate: 0.1 }),
    task({ planning_prompt_tokens: 4, planning_cost_estimate: 0.03 }),
  ]);
  assert.equal(aggregate?.total, "18");
  assert.equal(aggregate?.cost, "$0.130000");
  assert.equal(aggregate?.avgTotal, "9");
  assert.equal(aggregate?.taskCount, 2);
});

test("invalid stage numbers cannot poison the session totals", () => {
  assert.equal(resolveTasksUsageAggregate([task({ prompt_tokens: true,
    completion_tokens: "NaN", cost_estimate: "Infinity", planning_prompt_tokens: -1 })]), null);
});
