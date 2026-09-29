import assert from "node:assert/strict";
import test from "node:test";

import { reconcileRecoveryPreparation } from "./workbench-recovery.ts";

test("recovery prepares a running candidate only once", () => {
  const initial = { preparedTaskIds: [], launchTaskId: null };
  const first = reconcileRecoveryPreparation(initial, ["task-1"], "task-1");
  assert.deepEqual(first, {
    preparedTaskIds: ["task-1"],
    launchTaskId: "task-1",
  });
  assert.equal(reconcileRecoveryPreparation(first, ["task-1"], "task-1"), first);
  assert.equal(reconcileRecoveryPreparation(first, ["task-1"], null), first);
  assert.equal(reconcileRecoveryPreparation(first, ["task-1"], "task-1"), first);
});

test("recovery allows a new task and forgets terminal tasks", () => {
  const first = { preparedTaskIds: ["task-1"], launchTaskId: "task-1" };
  const second = reconcileRecoveryPreparation(first, ["task-1", "task-2"], "task-2");
  assert.deepEqual(second, {
    preparedTaskIds: ["task-1", "task-2"],
    launchTaskId: "task-2",
  });
  const terminal = reconcileRecoveryPreparation(second, [], null);
  assert.deepEqual(terminal, { preparedTaskIds: [], launchTaskId: null });
  assert.deepEqual(reconcileRecoveryPreparation(terminal, ["task-1"], "task-1"), {
    preparedTaskIds: ["task-1"],
    launchTaskId: "task-1",
  });
});
