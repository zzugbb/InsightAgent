"use client";

import {
  Button,
  Flex,
  Input,
  Select,
  Space,
  Table,
} from "antd";
import type { RefObject } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useMessages, usePreferences } from "../../../lib/preferences-context";

import type { SessionSummary, TaskSummary } from "./types";
import {
  buildTaskDetailHref,
  formatTaskFailureSourceLabel,
  formatTraceStepSemanticStatsSummary,
  formatTimestamp,
  getTaskLabel,
  isTaskFailedStatus,
  matchesTaskGovernanceFilters,
  matchesTaskFailureSourceFilter,
  matchesTaskObservabilityFilter,
  resolveTaskFailureDiagnosticDrilldown,
  resolveTaskFailureDiagnosticGroupsForTaskCenter,
  resolveTaskFailureHintDisplay,
  resolveTaskDetailHrefTraceSemanticFilter,
  resolveTaskSnapshotSummary,
} from "./utils";
import type { TaskFailureSourceFilter, TaskObservabilityFilter } from "./utils";

type TaskCenterProps = {
  activeSession: SessionSummary | undefined;
  activeSessionId: string | null;
  activeTaskId: string | null;
  recentTasks: TaskSummary[];
  taskSearchQuery: string;
  onTaskSearchQueryChange: (value: string) => void;
  taskGovernanceProfileFilter: string;
  onTaskGovernanceProfileFilterChange: (value: string) => void;
  taskGovernanceProviderSourceFilter: string;
  onTaskGovernanceProviderSourceFilterChange: (value: string) => void;
  availableToolRegistryProfiles: string[];
  availableToolRegistryProviderSources: string[];
  tasksLoading: boolean;
  onSelectTask: (task: TaskSummary) => void;
  onClose: () => void;
  closeButtonRef?: RefObject<HTMLButtonElement | null>;
  scopeMode: "session" | "global";
  onScopeModeChange: (mode: "session" | "global") => void;
};

function resolveTaskStatusTone(
  status: string,
): "running" | "completed" | "failed" | "other" {
  const normalized = status.trim().toLowerCase();
  if (
    normalized === "queued" ||
    normalized === "running" ||
    normalized === "pending"
  ) {
    return "running";
  }
  if (
    normalized === "completed" ||
    normalized === "done" ||
    normalized === "success"
  ) {
    return "completed";
  }
  if (normalized === "failed" || normalized === "error") {
    return "failed";
  }
  return "other";
}

export function TaskCenter({
  activeSession,
  activeSessionId,
  activeTaskId,
  recentTasks,
  taskSearchQuery,
  onTaskSearchQueryChange,
  taskGovernanceProfileFilter,
  onTaskGovernanceProfileFilterChange,
  taskGovernanceProviderSourceFilter,
  onTaskGovernanceProviderSourceFilterChange,
  availableToolRegistryProfiles,
  availableToolRegistryProviderSources,
  tasksLoading,
  onSelectTask,
  onClose,
  closeButtonRef,
  scopeMode,
  onScopeModeChange,
}: TaskCenterProps) {
  const t = useMessages();
  const { localeTag } = usePreferences();
  const allGovernanceFilterValue = "__all__";
  const [taskStatusFilter, setTaskStatusFilter] = useState<
    "all" | "running" | "completed" | "failed"
  >("all");
  const [taskObservabilityFilter, setTaskObservabilityFilter] =
    useState<TaskObservabilityFilter>("all");
  const [taskFailureSourceFilter, setTaskFailureSourceFilter] =
    useState<TaskFailureSourceFilter>("all");
  const [taskSortOrder, setTaskSortOrder] = useState<"latest" | "oldest">(
    "latest",
  );
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const scopedTasks = useMemo(() => {
    if (scopeMode === "global") {
      return recentTasks;
    }
    if (!activeSessionId) {
      return [];
    }
    return recentTasks.filter((task) => task.session_id === activeSessionId);
  }, [activeSessionId, recentTasks, scopeMode]);

  const taskSnapshots = useMemo(() => {
    const next = new Map<string, ReturnType<typeof resolveTaskSnapshotSummary>>();
    for (const task of scopedTasks) {
      next.set(task.id, resolveTaskSnapshotSummary({ task }));
    }
    return next;
  }, [scopedTasks]);

  const taskMatchesKeyword = useCallback((task: TaskSummary) => {
    const q = taskSearchQuery.trim().toLowerCase();
    if (q.length === 0) {
      return true;
    }
    const prompt = task.prompt.trim().toLowerCase();
    const id = task.id.toLowerCase();
    const snapshot = taskSnapshots.get(task.id);
    const governance = snapshot?.governance;
    const semanticSummary = snapshot
      ? formatTraceStepSemanticStatsSummary(snapshot.semanticStats, {
          planner: t.taskCenter.semanticPlannerLabel,
          retrieval: t.taskCenter.semanticRetrievalLabel,
          calculator: t.taskCenter.semanticCalculatorLabel,
          failure: t.taskCenter.semanticFailureLabel,
        }).toLowerCase()
      : "";
    const governanceKeywords = governance
      ? [
          governance.profile ?? "",
          governance.providerSource ?? "",
          ...governance.allowedToolNames,
          ...governance.allowedToolLabels,
        ]
          .map((item) => item.trim().toLowerCase())
          .filter(Boolean)
      : [];
    const failureSourceLabel =
      snapshot?.failureSource
        ? formatTaskFailureSourceLabel(snapshot.failureSource, t.inspector).toLowerCase()
        : "";
    const failureHintDisplay = resolveTaskFailureHintDisplay(
      snapshot?.failureHint,
      t.stream.streamErrorByCode,
    )?.toLowerCase() ?? "";
    return (
      prompt.includes(q)
      || id.includes(q)
      || semanticSummary.includes(q)
      || Boolean(snapshot?.failureHint?.toLowerCase().includes(q))
      || failureHintDisplay.includes(q)
      || failureSourceLabel.includes(q)
      || governanceKeywords.some((item) => item.includes(q))
    );
  }, [t.inspector, t.stream.streamErrorByCode, t.taskCenter, taskSearchQuery, taskSnapshots]);

  const taskFilterBase = useMemo(() => {
    const statusMatched = scopedTasks.filter((task) => {
      if (taskStatusFilter === "all") {
        return true;
      }
      const status = task.status.trim().toLowerCase();
      if (taskStatusFilter === "running") {
        return status === "queued" || status === "running" || status === "pending";
      }
      if (taskStatusFilter === "completed") {
        return status === "completed" || status === "done" || status === "success";
      }
      return status === "failed" || status === "error";
    });
    const governanceMatched = statusMatched.filter((task) =>
      matchesTaskGovernanceFilters(taskSnapshots.get(task.id), {
        allValue: allGovernanceFilterValue,
        profile: taskGovernanceProfileFilter,
        providerSource: taskGovernanceProviderSourceFilter,
      }),
    );
    const observabilityMatched = governanceMatched.filter((task) =>
      matchesTaskObservabilityFilter(
        task,
        taskSnapshots.get(task.id),
        taskObservabilityFilter,
      ),
    );
    return observabilityMatched;
  }, [
    allGovernanceFilterValue,
    scopedTasks,
    taskGovernanceProfileFilter,
    taskGovernanceProviderSourceFilter,
    taskObservabilityFilter,
    taskSnapshots,
    taskStatusFilter,
  ]);

  const failureDiagnosticGroupTasks = useMemo(
    () => taskFilterBase.filter(taskMatchesKeyword),
    [taskFilterBase, taskMatchesKeyword],
  );

  const filteredTasks = useMemo(() => {
    const failureSourceMatched = taskFilterBase.filter((task) =>
      matchesTaskFailureSourceFilter(
        taskSnapshots.get(task.id),
        taskFailureSourceFilter,
      ),
    );
    const queryMatched = failureSourceMatched.filter(taskMatchesKeyword);
    const sorted = [...queryMatched].sort((a, b) => {
      const at = new Date(a.updated_at).getTime();
      const bt = new Date(b.updated_at).getTime();
      return taskSortOrder === "latest" ? bt - at : at - bt;
    });
    return sorted;
  }, [
    taskFilterBase,
    taskFailureSourceFilter,
    taskSnapshots,
    taskMatchesKeyword,
    taskSortOrder,
  ]);

  const scopeDisabledSession = !activeSessionId;

  const failureDiagnosticGroups = useMemo(
    () =>
      resolveTaskFailureDiagnosticGroupsForTaskCenter({
        drilldownScopeSnapshots: failureDiagnosticGroupTasks.map((task) =>
          taskSnapshots.get(task.id),
        ),
        visibleSnapshots: filteredTasks.map((task) =>
          taskSnapshots.get(task.id),
        ),
        activeFailureSourceFilter: taskFailureSourceFilter,
      }),
    [
      failureDiagnosticGroupTasks,
      filteredTasks,
      taskFailureSourceFilter,
      taskSnapshots,
    ],
  );

  useEffect(() => {
    setPage(1);
  }, [
    activeSessionId,
    scopeMode,
    taskSearchQuery,
    taskObservabilityFilter,
    taskFailureSourceFilter,
    taskSortOrder,
    taskStatusFilter,
    taskGovernanceProfileFilter,
    taskGovernanceProviderSourceFilter,
  ]);

  const columns = useMemo(
    () => [
      {
        title: t.taskCenter.tableTask,
        key: "task",
        render: (_value: unknown, task: TaskSummary) => {
          const snapshot = taskSnapshots.get(task.id);
          const failedHint = resolveTaskFailureHintDisplay(
            snapshot?.failureHint,
            t.stream.streamErrorByCode,
          );
          const failureSourceLabel =
            snapshot?.failureSource
              ? formatTaskFailureSourceLabel(snapshot.failureSource, t.inspector)
              : null;
          const governance = snapshot?.governance;
          const governanceAllowedTools =
            governance && governance.allowedToolLabels.length > 0
              ? governance.allowedToolLabels
              : governance?.allowedToolNames ?? [];
          const semanticSummary = snapshot
            ? formatTraceStepSemanticStatsSummary(snapshot.semanticStats, {
                planner: t.taskCenter.semanticPlannerLabel,
                retrieval: t.taskCenter.semanticRetrievalLabel,
                calculator: t.taskCenter.semanticCalculatorLabel,
                failure: t.taskCenter.semanticFailureLabel,
              })
            : null;
          return (
            <div className="task-center-cell-main">
              <strong>{getTaskLabel(task, t.workbench)}</strong>
              {semanticSummary ? (
                <span
                  className="task-summary-governance"
                  data-testid="task-center-semantic-summary"
                >
                  {semanticSummary}
                </span>
              ) : null}
              {governance ? (
                <span
                  className="task-summary-governance"
                  data-testid="task-center-governance-summary"
                >
                  {[
                    governance.profile
                      ? `${t.inspector.traceMeta.toolRegistryProfile} ${governance.profile}`
                      : null,
                    governance.providerSource
                      ? `${t.inspector.traceMeta.toolRegistrySource} ${governance.providerSource}`
                      : null,
                    governanceAllowedTools.length > 0
                      ? `${t.inspector.traceMeta.allowedTools} ${governanceAllowedTools.join(", ")}`
                      : null,
                  ]
                    .filter((item): item is string => Boolean(item))
                    .join(" · ")}
                </span>
              ) : null}
              {failedHint ? (
                <span className="task-summary-failed-hint">
                  {t.inspector.taskFailureHint}
                  {failureSourceLabel ? ` · ${failureSourceLabel}` : ""}: {failedHint}
                </span>
              ) : null}
            </div>
          );
        },
      },
      {
        title: t.taskCenter.tableStatus,
        dataIndex: "status",
        key: "status",
        width: 120,
        render: (value: string) => (
          <span
            className={`task-status-badge task-status-badge--${resolveTaskStatusTone(value)}`}
          >
            {value}
          </span>
        ),
      },
      {
        title: t.taskCenter.tableUpdatedAt,
        key: "updated_at",
        width: 180,
        render: (_value: unknown, task: TaskSummary) =>
          formatTimestamp(task.updated_at, localeTag),
      },
      {
        title: t.taskCenter.tableActions,
        key: "actions",
        width: 110,
        align: "left" as const,
        render: (_value: unknown, task: TaskSummary) => {
          const snapshot = taskSnapshots.get(task.id);
          return (
            <Button
              size="small"
              type="default"
              className="task-summary-open-detail"
              data-testid="task-center-open-task-detail"
              aria-label={t.taskCenter.openTaskDetailAria}
              href={buildTaskDetailHref(task.id, {
                traceSemanticFilter: resolveTaskDetailHrefTraceSemanticFilter(
                  snapshot,
                  taskObservabilityFilter,
                ),
              })}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(event) => {
                event.stopPropagation();
              }}
            >
              {t.taskCenter.openTaskDetail}
            </Button>
          );
        },
      },
    ],
    [
      localeTag,
      taskSnapshots,
      taskObservabilityFilter,
      t.inspector,
      t.taskCenter.semanticCalculatorLabel,
      t.taskCenter.semanticFailureLabel,
      t.taskCenter.semanticPlannerLabel,
      t.taskCenter.semanticRetrievalLabel,
      t.taskCenter.openTaskDetail,
      t.taskCenter.openTaskDetailAria,
      t.taskCenter.tableActions,
      t.taskCenter.tableStatus,
      t.taskCenter.tableTask,
      t.taskCenter.tableUpdatedAt,
      t.stream.streamErrorByCode,
      t.workbench,
    ],
  );

  return (
    <section className="chat-shell task-center-shell" data-testid="task-center-shell">
      <header className="chat-header">
        <div className="chat-header-lead">
          <h2 id="task-center-title" className="chat-main-heading">
            <span className="chat-title-row">
              <span className="chat-title-text">{t.taskCenter.title}</span>
              <span className="chat-title-divider" aria-hidden />
              <span className="chat-title-time-wrap">
                <span className="chat-title-time">
                  {scopeMode === "session"
                    ? t.taskCenter.scopeSession
                    : t.taskCenter.scopeGlobal}
                </span>
              </span>
            </span>
          </h2>
          <p className="chat-subtitle">{t.taskCenter.lead}</p>
        </div>
        <Flex wrap="wrap" gap="small" align="center" justify="flex-end" className="chat-header-actions task-center-header-actions">
          <Space wrap size="small">
            <Button
              ref={closeButtonRef}
              type="default"
              onClick={onClose}
              className="task-center-close-btn"
              data-testid="task-center-close"
            >
              {t.settings.close}
            </Button>
          </Space>
        </Flex>
      </header>

      <section className="task-center-main" aria-labelledby="task-center-title">
        <div className="task-center-toolbar">
          <div className="task-center-filter-row task-center-filter-row--primary">
            <Select
              data-testid="task-center-scope-filter"
              showSearch
              optionFilterProp="label"
              value={scopeMode}
              onChange={(v) => onScopeModeChange(v as "session" | "global")}
              options={[
                {
                  label: t.taskCenter.scopeSession,
                  value: "session",
                  disabled: scopeDisabledSession,
                },
                { label: t.taskCenter.scopeGlobal, value: "global" },
              ]}
              placeholder={t.taskCenter.scopeLabel}
            />
            <Select
              data-testid="task-center-status-filter"
              showSearch
              optionFilterProp="label"
              value={taskStatusFilter}
              onChange={(v) =>
                setTaskStatusFilter(v as "all" | "running" | "completed" | "failed")
              }
              options={[
                { label: t.inspector.taskFilterAll, value: "all" },
                { label: t.inspector.taskFilterRunning, value: "running" },
                { label: t.inspector.taskFilterDone, value: "completed" },
                { label: t.inspector.taskFilterError, value: "failed" },
              ]}
              placeholder={t.inspector.taskViewLabel}
            />
            <Select
              data-testid="task-center-observability-filter"
              showSearch
              optionFilterProp="label"
              value={taskObservabilityFilter}
              onChange={(v) => setTaskObservabilityFilter(v as TaskObservabilityFilter)}
              options={[
                { label: t.taskCenter.observabilityFilterAll, value: "all" },
                {
                  label: t.taskCenter.observabilityFilterAttention,
                  value: "attention",
                },
                {
                  label: t.taskCenter.observabilityFilterFailedStatus,
                  value: "failed_status",
                },
                {
                  label: t.taskCenter.observabilityFilterFailureHint,
                  value: "failure_hint",
                },
                {
                  label: t.taskCenter.observabilityFilterFailureTrace,
                  value: "failure_trace",
                },
              ]}
              placeholder={t.taskCenter.observabilityFilterAll}
            />
            <Input
              data-testid="task-center-keyword-filter"
              allowClear
              value={taskSearchQuery}
              onChange={(e) => onTaskSearchQueryChange(e.target.value)}
              placeholder={t.inspector.taskSearchPlaceholder}
            />
            <Select
              data-testid="task-center-governance-profile-filter"
              showSearch
              optionFilterProp="label"
              value={taskGovernanceProfileFilter}
              onChange={onTaskGovernanceProfileFilterChange}
              options={[
                {
                  label: t.taskCenter.governanceProfileFilterAll,
                  value: allGovernanceFilterValue,
                },
                ...availableToolRegistryProfiles.map((value) => ({
                  label: value,
                  value,
                })),
              ]}
              placeholder={t.taskCenter.governanceProfileFilterAll}
            />
            <Select
              data-testid="task-center-governance-source-filter"
              showSearch
              optionFilterProp="label"
              value={taskGovernanceProviderSourceFilter}
              onChange={onTaskGovernanceProviderSourceFilterChange}
              options={[
                {
                  label: t.taskCenter.governanceSourceFilterAll,
                  value: allGovernanceFilterValue,
                },
                ...availableToolRegistryProviderSources.map((value) => ({
                  label: value,
                  value,
                })),
              ]}
              placeholder={t.taskCenter.governanceSourceFilterAll}
            />
          </div>
          <div className="task-center-filter-row task-center-filter-row--secondary">
            <Select
              data-testid="task-center-sort-filter"
              showSearch
              optionFilterProp="label"
              value={taskSortOrder}
              onChange={(v) => setTaskSortOrder(v as "latest" | "oldest")}
              options={[
                { label: t.inspector.taskSortLatest, value: "latest" },
                { label: t.inspector.taskSortOldest, value: "oldest" },
              ]}
              placeholder={t.inspector.taskSortLatest}
            />
            <Button
              className="task-center-reset-btn"
              data-testid="task-center-filter-reset"
              onClick={() => {
                onScopeModeChange(scopeDisabledSession ? "global" : "session");
                setTaskStatusFilter("all");
                setTaskObservabilityFilter("all");
                setTaskFailureSourceFilter("all");
                setTaskSortOrder("latest");
                onTaskSearchQueryChange("");
                onTaskGovernanceProfileFilterChange(allGovernanceFilterValue);
                onTaskGovernanceProviderSourceFilterChange(
                  allGovernanceFilterValue,
                );
              }}
            >
              {t.sidebar.audit.filterReset}
            </Button>
          </div>
        </div>

        {scopeMode === "session" && !activeSessionId ? (
          <p className="panel-note panel-note--muted">{t.taskCenter.sessionRequired}</p>
        ) : null}

        {activeSession && scopeMode === "session" ? (
          <p className="panel-note panel-note--muted task-center-session-note">
            {activeSession.title?.trim() || activeSession.id}
            {" · "}
            {t.chat.updatedAt(formatTimestamp(activeSession.updated_at, localeTag))}
          </p>
        ) : null}

        {failureDiagnosticGroups.length > 0 ? (
          <div
            className="task-center-failure-groups"
            data-testid="task-center-failure-diagnostic-groups"
            aria-label={t.taskCenter.failureDiagnosticsTitle}
          >
            <span className="task-center-failure-groups-title">
              {t.taskCenter.failureDiagnosticsTitle}
            </span>
            {failureDiagnosticGroups.map((group) => (
              <button
                key={group.source}
                type="button"
                className="task-center-failure-chip"
                data-testid="task-center-failure-diagnostic-group"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  const drilldown = resolveTaskFailureDiagnosticDrilldown(group.source);
                  setTaskObservabilityFilter(drilldown.observabilityFilter);
                  setTaskFailureSourceFilter(drilldown.failureSourceFilter);
                }}
                aria-pressed={taskFailureSourceFilter === group.source}
              >
                {formatTaskFailureSourceLabel(group.source, t.inspector)}
                {" "}
                {t.taskCenter.failureDiagnosticsCount(group.count)}
              </button>
            ))}
          </div>
        ) : null}

        {tasksLoading ? (
          <div className="task-center-loading">
            <div className="skeleton message-skeleton-row" />
            <div className="skeleton message-skeleton-row" />
          </div>
        ) : null}

        {!tasksLoading ? (
          <div className="task-center-table-wrap">
            <Table<TaskSummary>
              size="small"
              rowKey={(record) => record.id}
              dataSource={filteredTasks}
              className="task-center-table"
              columns={columns}
              locale={{ emptyText: t.inspector.taskEmpty }}
              rowClassName={(record) =>
                `task-center-table-row${record.id === activeTaskId ? " is-active" : ""}${isTaskFailedStatus(record.status) ? " task-summary-item--failed" : ""}`
              }
              onRow={(record) => ({
                onClick: () => onSelectTask(record),
              })}
              pagination={{
                current: page,
                pageSize,
                total: filteredTasks.length,
                showSizeChanger: true,
                onChange: (nextPage, nextPageSize) => {
                  setPage(nextPage);
                  if (nextPageSize && nextPageSize !== pageSize) {
                    setPageSize(nextPageSize);
                  }
                },
              }}
            />
          </div>
        ) : null}
      </section>
    </section>
  );
}
