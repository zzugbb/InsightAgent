import test from "node:test";
import assert from "node:assert/strict";

import {
  formatAuditTaskFailureSummary,
  resolveAuditReadableDetail,
} from "./audit-logs-modal-utils.ts";

const labels = {
  fieldCode: "Code",
  fieldMessage: "Message",
  fieldFailureHint: "Failure hint",
  fieldFailureSource: "Failure source",
  streamErrorByCode: (code: string) =>
    code === "remote_provider_network_error"
      ? "Failed to reach remote provider. Check network or base URL."
      : code,
  taskFailureSourceErrorEvent: "SSE error",
  taskFailureSourceToolError: "Tool error",
  taskFailureSourceTraceContent: "Trace content",
  taskFailureSourceLegacyTrace: "Persisted trace",
};

test("formatAuditTaskFailureSummary prefers readable failure hint and source", () => {
  assert.equal(
    formatAuditTaskFailureSummary(
      "Task failed",
      {
        code: "tool_execution_error",
        message: "generic runtime error",
        failure_hint: "provider_search exhausted retries",
        failure_source: "error_event",
      },
      labels,
    ),
    "Task failed · SSE error: provider_search exhausted retries",
  );
});

test("formatAuditTaskFailureSummary uses message as fallback failure hint", () => {
  assert.equal(
    formatAuditTaskFailureSummary(
      "Task failed",
      {
        code: "custom_error",
        message: "provider crashed before returning a code hint",
      },
      labels,
    ),
    "Task failed · provider crashed before returning a code hint",
  );
});

test("formatAuditTaskFailureSummary maps stream error code before raw transport message", () => {
  assert.equal(
    formatAuditTaskFailureSummary(
      "Task failed",
      {
        code: "remote_provider_network_error",
        message:
          "Remote provider stream network error: <urlopen error [Errno 61] Connection refused>",
      },
      labels,
    ),
    "Task failed · Failed to reach remote provider. Check network or base URL.",
  );
});

test("resolveAuditReadableDetail promotes task failure hint and source", () => {
  const entries = resolveAuditReadableDetail(
    {
      code: "tool_execution_error",
      message: "generic runtime error",
      failure_hint: "provider_search exhausted retries",
      failure_source: "error_event",
    },
    labels,
  );

  assert.deepEqual(entries, [
    { key: "failure_hint", label: "Failure hint", value: "provider_search exhausted retries" },
    { key: "failure_source", label: "Failure source", value: "SSE error" },
    { key: "code", label: "Code", value: "tool_execution_error" },
    { key: "message", label: "Message", value: "generic runtime error" },
  ]);
});

test("resolveAuditReadableDetail treats task failure message as fallback hint", () => {
  const entries = resolveAuditReadableDetail(
    {
      code: "custom_error",
      message: "provider crashed before returning a code hint",
    },
    labels,
  );

  assert.deepEqual(entries, [
    {
      key: "failure_hint",
      label: "Failure hint",
      value: "provider crashed before returning a code hint",
    },
    { key: "code", label: "Code", value: "custom_error" },
  ]);
});

test("resolveAuditReadableDetail keeps raw message after mapped stream code hint", () => {
  const entries = resolveAuditReadableDetail(
    {
      code: "remote_provider_network_error",
      message:
        "Remote provider stream network error: <urlopen error [Errno 61] Connection refused>",
    },
    labels,
  );

  assert.deepEqual(entries, [
    {
      key: "failure_hint",
      label: "Failure hint",
      value: "Failed to reach remote provider. Check network or base URL.",
    },
    { key: "code", label: "Code", value: "remote_provider_network_error" },
    {
      key: "message",
      label: "Message",
      value:
        "Remote provider stream network error: <urlopen error [Errno 61] Connection refused>",
    },
  ]);
});
