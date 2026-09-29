import assert from "node:assert/strict";
import test from "node:test";

import {
  resolveNarrowDrawers,
  resolveRemoteSendCooldownUntil,
  resolveTaskCenterScope,
  reconcileQueryBanner,
} from "./workbench-ui-state.ts";

test("remote send cooldown clears when runtime mode leaves remote", () => {
  assert.equal(resolveRemoteSendCooldownUntil("remote", 1234), 1234);
  assert.equal(resolveRemoteSendCooldownUntil("mock", 1234), null);
  assert.equal(resolveRemoteSendCooldownUntil(undefined, 1234), null);
  assert.equal(resolveRemoteSendCooldownUntil("remote", null), null);
});

test("task center scope falls back to global without an active session", () => {
  assert.equal(resolveTaskCenterScope("session", "session-1"), "session");
  assert.equal(resolveTaskCenterScope("session", null), "global");
  assert.equal(resolveTaskCenterScope("global", "session-1"), "global");
});

test("wide layout closes only the narrow drawers", () => {
  const open = { inspector: true, session: false };
  assert.equal(resolveNarrowDrawers(true, open), open);
  assert.deepEqual(resolveNarrowDrawers(false, open), {
    inspector: false,
    session: false,
  });
  const closed = { inspector: false, session: false };
  assert.equal(resolveNarrowDrawers(false, closed), closed);
});

test("query banner preserves dismissal until an observed error source changes", () => {
  const settingsError = new Error("settings");
  const messagesError = new Error("messages");
  const initial = {
    settingsError: null,
    sessionsError: null,
    tasksError: null,
    messagesError: null,
    activeSessionId: null,
    errorLabels: null,
  };
  const format = (error: unknown) => (error as Error).message;
  const active = { ...initial, settingsError, messagesError, activeSessionId: "s1" };
  const first = reconcileQueryBanner(initial, active, null, format);
  assert.equal(first.banner, "settings");
  assert.equal(reconcileQueryBanner(active, active, null, format).banner, null);
  assert.equal(reconcileQueryBanner(active, active, "local error", format).banner, "local error");

  const changed = { ...active, settingsError: null };
  assert.equal(reconcileQueryBanner(active, changed, null, format).banner, "messages");
  assert.equal(reconcileQueryBanner(changed, initial, null, format).banner, null);
  assert.equal(reconcileQueryBanner(initial, active, null, format).banner, "settings");
});
