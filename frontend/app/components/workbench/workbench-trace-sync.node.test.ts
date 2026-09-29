import assert from "node:assert/strict";
import test from "node:test";

import { resolveTraceDeltaReset } from "./workbench-trace-sync.ts";

test("trace delta reset follows stream, visibility, and task identity", () => {
  const idle = { isStreaming: false, isPageVisible: true, taskId: "" };
  const active = { isStreaming: true, isPageVisible: true, taskId: "task-1" };
  assert.equal(resolveTraceDeltaReset(idle, idle), null);
  assert.equal(resolveTraceDeltaReset(idle, active), "active");
  assert.equal(resolveTraceDeltaReset(active, { ...active, isPageVisible: false }), "paused");
  assert.equal(resolveTraceDeltaReset(active, { ...active, taskId: "task-2" }), "active");
  assert.equal(resolveTraceDeltaReset(active, { ...active, taskId: "" }), "idle");
  assert.equal(resolveTraceDeltaReset(active, idle), "idle");
});

test("hidden streaming remains paused even before a task id arrives", () => {
  const idle = { isStreaming: false, isPageVisible: true, taskId: "" };
  assert.equal(resolveTraceDeltaReset(idle, {
    isStreaming: true,
    isPageVisible: false,
    taskId: "",
  }), "paused");
});
