import test from "node:test";
import assert from "node:assert/strict";

import {
  buildTaskDetailTraceSemanticHref,
  resolveTaskDetailFailureHint,
  resolveTaskDetailFailureTracePreset,
  resolveTaskDetailInitialTraceFilterState,
  resolveTaskDetailSemanticFilterChange,
  resolveTaskDetailSemanticTracePreset,
  resolveTaskDetailStatusDisplay,
  resolveTaskDetailTraceSteps,
} from "./[taskId]/task-detail-page-utils.ts";

test("resolveTaskDetailStatusDisplay prioritizes normalized task status", () => {
  assert.deepEqual(
    resolveTaskDetailStatusDisplay({
      status: "completed",
      status_label: "Completed",
      status_normalized: "failed",
    }),
    {
      label: "failed",
      tone: "failed",
    },
  );
  assert.deepEqual(
    resolveTaskDetailStatusDisplay({
      status: "pending",
      status_label: "Queued for execution",
    }),
    {
      label: "Queued for execution",
      tone: "running",
    },
  );
});

test("buildTaskDetailTraceSemanticHref preserves shareable semantic trace focus", () => {
  assert.equal(
    buildTaskDetailTraceSemanticHref("task/with space?x=1", "retrieval"),
    "/tasks/task%2Fwith%20space%3Fx%3D1?trace_semantic=retrieval",
  );
  assert.equal(
    buildTaskDetailTraceSemanticHref("task/with space?x=1", "failure"),
    "/tasks/task%2Fwith%20space%3Fx%3D1?trace_semantic=failure",
  );
  assert.equal(
    buildTaskDetailTraceSemanticHref("task/with space?x=1", "all"),
    "/tasks/task%2Fwith%20space%3Fx%3D1",
  );
  assert.equal(buildTaskDetailTraceSemanticHref("", "planner"), "/tasks/");
});

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

test("resolveTaskDetailInitialTraceFilterState applies semantic replay URL presets", () => {
  assert.deepEqual(
    resolveTaskDetailInitialTraceFilterState("failure"),
    {
      traceView: "list",
      traceSemanticFilter: "failure",
      traceKindFilter: "all",
      traceSearchQuery: "",
    },
  );
  assert.deepEqual(
    resolveTaskDetailInitialTraceFilterState(" retrieval "),
    {
      traceView: "list",
      traceSemanticFilter: "retrieval",
      traceKindFilter: "all",
      traceSearchQuery: "",
    },
  );
  assert.deepEqual(
    resolveTaskDetailInitialTraceFilterState("PLANNER"),
    {
      traceView: "list",
      traceSemanticFilter: "planner",
      traceKindFilter: "all",
      traceSearchQuery: "",
    },
  );
  assert.deepEqual(
    resolveTaskDetailInitialTraceFilterState("calculator"),
    {
      traceView: "list",
      traceSemanticFilter: "calculator",
      traceKindFilter: "all",
      traceSearchQuery: "",
    },
  );
  assert.deepEqual(
    resolveTaskDetailInitialTraceFilterState("unknown"),
    {
      traceView: "list",
      traceSemanticFilter: "all",
      traceKindFilter: "all",
      traceSearchQuery: "",
    },
  );
});

test("resolveTaskDetailSemanticTracePreset focuses semantic traces from any trace state", () => {
  assert.deepEqual(
    resolveTaskDetailSemanticTracePreset("retrieval", {
      traceView: "flow",
      traceSemanticFilter: "failure",
      traceKindFilter: "tool",
      traceSearchQuery: "remote_provider_network_error",
    }),
    {
      traceView: "list",
      traceSemanticFilter: "retrieval",
      traceKindFilter: "all",
      traceSearchQuery: "",
    },
  );
});

test("resolveTaskDetailSemanticFilterChange clears stale kind and search filters", () => {
  assert.deepEqual(
    resolveTaskDetailSemanticFilterChange("retrieval", {
      traceView: "flow",
      traceSemanticFilter: "planner",
      traceKindFilter: "tool",
      traceSearchQuery: "remote_provider_network_error",
    }),
    {
      traceView: "flow",
      traceSemanticFilter: "retrieval",
      traceKindFilter: "all",
      traceSearchQuery: "",
    },
  );
  assert.deepEqual(
    resolveTaskDetailSemanticFilterChange("all", {
      traceView: "list",
      traceSemanticFilter: "failure",
      traceKindFilter: "action",
      traceSearchQuery: "timeout",
    }),
    {
      traceView: "list",
      traceSemanticFilter: "all",
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
        {
          id: "legacy-unauthorized-code",
          type: "other",
          content: "remote_api_key_unauthorized",
        },
      ],
    }).map((step) => step.id),
    ["persisted-tool-done", "legacy-error-event", "legacy-unauthorized-code"],
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
