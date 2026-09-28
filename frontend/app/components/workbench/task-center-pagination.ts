import type {
  TaskFailureSourceFilter,
  TaskObservabilityFilter,
  TaskStatusFilter,
} from "./utils";

export type TaskCenterPageFilters = {
  activeSessionId: string | null;
  scopeMode: "session" | "global";
  taskSearchQuery: string;
  taskObservabilityFilter: TaskObservabilityFilter;
  taskFailureSourceFilter: TaskFailureSourceFilter;
  taskSortOrder: "latest" | "oldest";
  taskStatusFilter: TaskStatusFilter;
  taskGovernanceProfileFilter: string;
  taskGovernanceProviderSourceFilter: string;
};

export type TaskCenterPageSelection = {
  page: number;
  filters: TaskCenterPageFilters;
};

function sameTaskCenterPageFilters(
  previous: TaskCenterPageFilters,
  current: TaskCenterPageFilters,
): boolean {
  return (Object.keys(current) as Array<keyof TaskCenterPageFilters>)
    .every((key) => previous[key] === current[key]);
}

export function resolveTaskCenterPage(
  selection: TaskCenterPageSelection | null,
  filters: TaskCenterPageFilters,
): number {
  if (!selection) {
    return 1;
  }
  return sameTaskCenterPageFilters(selection.filters, filters) ? selection.page : 1;
}

export function reconcileTaskCenterPageSelection(
  selection: TaskCenterPageSelection | null,
  filters: TaskCenterPageFilters,
): TaskCenterPageSelection | null {
  if (!selection || sameTaskCenterPageFilters(selection.filters, filters)) {
    return selection;
  }
  return { page: 1, filters };
}
