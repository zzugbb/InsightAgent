import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import type { Run } from "./types.ts";
const content = readFileSync(
  new URL("../data/cases.json", import.meta.url),
  "utf8",
);
const cases = JSON.parse(content) as Run[];
test("public cases distinguish real execution, controlled failure and a separate recovery", () => {
  assert.deepEqual(
    cases.map((run) => run.id),
    ["rag", "failure", "recovery"],
  );
  assert.deepEqual(
    cases.map((run) => [run.source, run.status]),
    [
      ["real_model", "completed"],
      ["controlled_fixture", "failed"],
      ["real_model", "completed"],
    ],
  );
  assert.equal(cases[2].parentId, "failure");
  assert.equal(cases[1].answer, "");
  assert.equal(cases[1].usage, null);
  for (const run of cases) {
    assert.match(run.sourceCommit, /^[a-f0-9]{40}$/);
    assert.ok(run.steps.length > 0);
    assert.equal(
      new Set(run.steps.map((step) => step.id)).size,
      run.steps.length,
    );
    const seq = run.steps.map((step) => step.seq!);
    assert.deepEqual(
      seq,
      [...seq].sort((a, b) => a - b),
    );
    for (const step of run.steps) {
      assert.ok(!step.meta || !("prompt" in step.meta));
      for (const parent of step.meta?.agent_from_step_ids ?? [])
        assert.ok(run.steps.some((x) => x.id === parent));
    }
  }
});
test("successful RAG example has actual retrieval and calculator evidence, plus a cited version", () => {
  const run = cases[0];
  const actions = run.steps.filter(
    (step) => step.type === "action" && step.meta?.tool?.status === "done",
  );
  assert.ok(actions.some((step) => step.meta?.tool?.name === "calc_eval"));
  assert.ok(actions.some((step) => step.meta?.tool?.name === "task_retrieve"));
  assert.ok(
    run.steps.some((step) =>
      step.meta?.rag?.chunk_metadata?.some(
        (chunk) => chunk.source === "budget.md" && chunk.document_version,
      ),
    ),
  );
  assert.ok(run.answer.includes("14"));
  assert.equal(typeof run.steps[0].meta?.planning_provider_used, "boolean");
  assert.ok(
    cases[2].steps.some(
      (step) =>
        step.type === "action" &&
        step.meta?.tool?.name === "calc_eval" &&
        step.meta.tool.status === "done",
    ),
  );
});
test("publication allowlist excludes auth, identity, private network and runtime configuration", () => {
  assert.doesNotMatch(
    content,
    /sk-[A-Za-z0-9]{12,}|Bearer\s+\S+|api_key|password|https?:\/\/|127\.0\.0\.1|localhost|api_key_enc|user_id|session_id|tool_registry|"prompt"\s*:\s*"You are/i,
  );
  const stepKeys = new Set(["id", "seq", "type", "content", "meta"]);
  for (const run of cases)
    for (const step of run.steps)
      assert.ok(Object.keys(step).every((key) => stepKeys.has(key)));
});
