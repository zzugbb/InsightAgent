import assert from "node:assert/strict";
import test from "node:test";

import {
  reconcileRuntimeNoticeDismissal,
} from "./workbench-runtime-notice.ts";

test("runtime notice dismissal resets only when model runtime settings change", () => {
  const mock = { mode: "mock", apiKeyConfigured: false };
  const dismissed = { ...mock, dismissed: true };

  assert.equal(reconcileRuntimeNoticeDismissal(dismissed, mock), dismissed);

  const remote = { mode: "remote", apiKeyConfigured: false };
  const afterModeChange = reconcileRuntimeNoticeDismissal(dismissed, remote);
  assert.deepEqual(afterModeChange, { ...remote, dismissed: false });
  assert.deepEqual(reconcileRuntimeNoticeDismissal(afterModeChange, mock), {
    ...mock,
    dismissed: false,
  });
  assert.deepEqual(reconcileRuntimeNoticeDismissal(dismissed, {
    ...mock,
    apiKeyConfigured: true,
  }), {
    mode: "mock",
    apiKeyConfigured: true,
    dismissed: false,
  });
});

test("runtime notice dismissal keeps the initial empty settings identity", () => {
  const initial = {
    mode: undefined,
    apiKeyConfigured: undefined,
    dismissed: false,
  };
  assert.equal(reconcileRuntimeNoticeDismissal(initial, {
    mode: undefined,
    apiKeyConfigured: undefined,
  }), initial);
});
