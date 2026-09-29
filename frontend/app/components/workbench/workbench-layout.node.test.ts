import assert from "node:assert/strict";
import test from "node:test";

import {
  INSPECTOR_COLLAPSED_STORAGE_KEY,
  INSPECTOR_WIDTH_STORAGE_KEY,
  SIDEBAR_COLLAPSED_STORAGE_KEY,
  SIDEBAR_WIDTH_STORAGE_KEY,
} from "../../../lib/storage-keys.ts";
import {
  DEFAULT_WORKBENCH_LAYOUT,
  readStoredWorkbenchLayout,
  selectHydratedWorkbenchLayout,
} from "./workbench-layout.ts";

const keys = {
  sidebarWidth: SIDEBAR_WIDTH_STORAGE_KEY,
  sidebarCollapsed: SIDEBAR_COLLAPSED_STORAGE_KEY,
  inspectorWidth: INSPECTOR_WIDTH_STORAGE_KEY,
  inspectorCollapsed: INSPECTOR_COLLAPSED_STORAGE_KEY,
};

test("workbench layout keeps the server snapshot until hydration", () => {
  const stored = {
    sidebarWidthPx: 320,
    sidebarCollapsed: true,
    inspectorWidthPx: 400,
    inspectorCollapsed: false,
  };
  assert.equal(selectHydratedWorkbenchLayout(stored, false), DEFAULT_WORKBENCH_LAYOUT);
  assert.equal(selectHydratedWorkbenchLayout(stored, true), stored);
});

test("workbench layout parses saved widths with the existing bounds", () => {
  const values = new Map([
    [SIDEBAR_WIDTH_STORAGE_KEY, "999"],
    [SIDEBAR_COLLAPSED_STORAGE_KEY, "1"],
    [INSPECTOR_WIDTH_STORAGE_KEY, "100"],
    [INSPECTOR_COLLAPSED_STORAGE_KEY, "0"],
  ]);
  const storage = { getItem: (key: string) => values.get(key) ?? null };
  const layout = readStoredWorkbenchLayout(storage, keys);
  assert.equal(layout.sidebarWidthPx, 480);
  assert.equal(layout.sidebarCollapsed, true);
  assert.equal(layout.inspectorWidthPx, 260);
  assert.equal(layout.inspectorCollapsed, false);
});

test("missing or inaccessible storage leaves the default layout", () => {
  assert.deepEqual(readStoredWorkbenchLayout(null, keys), DEFAULT_WORKBENCH_LAYOUT);
  assert.deepEqual(readStoredWorkbenchLayout({ getItem: () => { throw Error("denied"); } }, keys), DEFAULT_WORKBENCH_LAYOUT);
});
