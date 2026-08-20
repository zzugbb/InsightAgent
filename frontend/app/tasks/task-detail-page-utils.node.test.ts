import test from "node:test";
import assert from "node:assert/strict";

import {
  resolveTaskDetailFailureHint,
  resolveTaskDetailFailureTracePreset,
  resolveTaskDetailTraceSteps,
} from "./[taskId]/task-detail-page-utils.ts";

test("resolveTaskDetailFailureTracePreset focuses failure traces from any trace state", () => {
  assert.deepEqual(
    resolveTaskDetailFailureTracePreset({
      traceView: "flow",
      traceSemanticFilter: "retrieval",
      traceKindFilter: "tool",
      traceSearchQuery: "remote_provider_network_error",
    }),
    {
      traceView: "list",
      traceSemanticFilter: "failure",
      traceKindFilter: "all",
      traceSearchQuery: "",
    },
  );
});

test("resolveTaskDetailFailureHint maps stream error codes when labels know them", () => {
  assert.equal(
    resolveTaskDetailFailureHint("remote_provider_network_error", (code) =>
      code === "remote_provider_network_error"
        ? "Failed to reach remote provider. Check network or base URL."
        : null,
    ),
    "Failed to reach remote provider. Check network or base URL.",
  );
});

test("resolveTaskDetailTraceSteps keeps fallback failure diagnostics missing from primary trace", () => {
  assert.deepEqual(
    resolveTaskDetailTraceSteps({
      primarySteps: [
        {
          id: "persisted-tool-done",
          type: "action",
          content: "Tool done: Task Planner",
          meta: {
            tool: {
              name: "task_plan",
              label: "Task Planner",
              status: "done",
            },
          },
        },
      ],
      fallbackSteps: [
        {
          id: "legacy-error-event",
          type: "other",
          content: "Task failed",
          meta: {
            error_event: {
              code: "remote_provider_network_error",
              message: "Failed to reach remote provider",
            },
          },
        },
        {
          id: "legacy-tool-done",
          type: "action",
          content: "Tool done: Task Planner",
        },
      ],
    }).map((step) => step.id),
    ["persisted-tool-done", "legacy-error-event"],
  );
});

test("resolveTaskDetailTraceSteps synthesizes explicit task failures missing from trace", () => {
  const steps = resolveTaskDetailTraceSteps({
    primarySteps: [
      {
        id: "persisted-tool-done",
        type: "action",
        content: "Tool done: Task Planner",
      },
    ],
    fallbackSteps: [],
    explicitFailureHint: "Failed to reach remote provider. Check network or base URL.",
  });

  assert.equal(steps.length, 2);
  assert.equal(steps[1].id, "task-detail-failure-summary");
  assert.equal(
    steps[1].content,
    "Failed to reach remote provider. Check network or base URL.",
  );
});
