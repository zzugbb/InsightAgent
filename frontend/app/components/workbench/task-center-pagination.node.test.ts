import assert from "node:assert/strict";
import test from "node:test";

import {
  reconcileTaskCenterPageSelection,
  resolveTaskCenterPage,
} from "./task-center-pagination.ts";
import type { TaskCenterPageFilters } from "./task-center-pagination.ts";

const filters: TaskCenterPageFilters = {
  activeSessionId: "session-a",
  scopeMode: "session",
  taskSearchQuery: "",
  taskObservabilityFilter: "all",
  taskFailureSourceFilter: "all",
  taskSortOrder: "latest",
  taskStatusFilter: "all",
  taskGovernanceProfileFilter: "__all__",
  taskGovernanceProviderSourceFilter: "__all__",
};

test("task center pagination follows current filters without losing a manual page on data refresh", () => {
  assert.equal(resolveTaskCenterPage(null, filters), 1);

  const selectedPage = { page: 3, filters };
  assert.equal(resolveTaskCenterPage(selectedPage, { ...filters }), 3);

  const changes: Array<Partial<TaskCenterPageFilters>> = [
    { activeSessionId: "session-b" },
    { scopeMode: "global" },
    { taskSearchQuery: "failure" },
    { taskObservabilityFilter: "attention" },
    { taskFailureSourceFilter: "error_event" },
    { taskSortOrder: "oldest" },
    { taskStatusFilter: "failed" },
    { taskGovernanceProfileFilter: "restricted" },
    { taskGovernanceProviderSourceFilter: "registry" },
  ];

  for (const change of changes) {
    const nextFilters = { ...filters, ...change };
    assert.equal(resolveTaskCenterPage(selectedPage, nextFilters), 1);
    assert.equal(
      resolveTaskCenterPage({ page: 2, filters: nextFilters }, nextFilters),
      2,
    );
  }
});

test("returning to previous filters does not resurrect the previous page", () => {
  const selectedPage = { page: 3, filters };
  const changedFilters = { ...filters, taskSearchQuery: "failure" };
  const changedSelection = reconcileTaskCenterPageSelection(selectedPage, changedFilters);

  assert.equal(changedSelection?.page, 1);
  assert.equal(
    reconcileTaskCenterPageSelection(changedSelection, filters)?.page,
    1,
  );
  assert.equal(reconcileTaskCenterPageSelection(selectedPage, filters), selectedPage);
  assert.equal(reconcileTaskCenterPageSelection(null, filters), null);
});
