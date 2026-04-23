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
import { useEffect, useMemo, useState } from "react";

import { useMessages, usePreferences } from "../../../lib/preferences-context";

import type { SessionSummary, TaskSummary } from "./types";
import {
  extractTaskFailureHint,
  formatTimestamp,
  getTaskLabel,
  isTaskFailedStatus,
} from "./utils";

type TaskCenterProps = {
  activeSession: SessionSummary | undefined;
  activeSessionId: string | null;
  activeTaskId: string | null;
  recentTasks: TaskSummary[];
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
  if (normalized === "running" || normalized === "pending") {
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
  tasksLoading,
  onSelectTask,
  onClose,
  closeButtonRef,
  scopeMode,
  onScopeModeChange,
}: TaskCenterProps) {
  const t = useMessages();
  const { localeTag } = usePreferences();
  const [taskStatusFilter, setTaskStatusFilter] = useState<
    "all" | "running" | "completed" | "failed"
  >("all");
  const [taskSortOrder, setTaskSortOrder] = useState<"latest" | "oldest">(
    "latest",
  );
  const [taskSearchQuery, setTaskSearchQuery] = useState("");
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

  const filteredTasks = useMemo(() => {
    const q = taskSearchQuery.trim().toLowerCase();
    const statusMatched = scopedTasks.filter((task) => {
      if (taskStatusFilter === "all") {
        return true;
      }
      const status = task.status.trim().toLowerCase();
      if (taskStatusFilter === "running") {
        return status === "running" || status === "pending";
      }
      if (taskStatusFilter === "completed") {
        return status === "completed" || status === "done" || status === "success";
      }
      return status === "failed" || status === "error";
    });
    const queryMatched =
      q.length === 0
        ? statusMatched
        : statusMatched.filter((task) => {
            const prompt = task.prompt.trim().toLowerCase();
            const id = task.id.toLowerCase();
            return prompt.includes(q) || id.includes(q);
          });
    const sorted = [...queryMatched].sort((a, b) => {
      const at = new Date(a.updated_at).getTime();
      const bt = new Date(b.updated_at).getTime();
      return taskSortOrder === "latest" ? bt - at : at - bt;
    });
    return sorted;
  }, [scopedTasks, taskSearchQuery, taskSortOrder, taskStatusFilter]);

  const scopeDisabledSession = !activeSessionId;

  useEffect(() => {
    setPage(1);
  }, [
    activeSessionId,
    scopeMode,
    taskSearchQuery,
    taskSortOrder,
    taskStatusFilter,
  ]);

  const columns = useMemo(
    () => [
      {
        title: t.taskCenter.tableTask,
        key: "task",
        render: (_value: unknown, task: TaskSummary) => {
          const failedHint = extractTaskFailureHint(task);
          return (
            <div className="task-center-cell-main">
              <strong>{getTaskLabel(task, t.workbench)}</strong>
              {failedHint ? (
                <span className="task-summary-failed-hint">
                  {t.inspector.taskFailureHint}: {failedHint}
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
        render: (_value: unknown, task: TaskSummary) => (
          <Button
            size="small"
            type="default"
            className="task-summary-open-detail"
            data-testid="task-center-open-task-detail"
            aria-label={t.taskCenter.openTaskDetailAria}
            href={`/tasks/${encodeURIComponent(task.id)}`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(event) => {
              event.stopPropagation();
            }}
          >
            {t.taskCenter.openTaskDetail}
          </Button>
        ),
      },
    ],
    [
      localeTag,
      t.inspector,
      t.taskCenter.openTaskDetail,
      t.taskCenter.openTaskDetailAria,
      t.taskCenter.tableActions,
      t.taskCenter.tableStatus,
      t.taskCenter.tableTask,
      t.taskCenter.tableUpdatedAt,
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
            <Input
              data-testid="task-center-keyword-filter"
              allowClear
              value={taskSearchQuery}
              onChange={(e) => setTaskSearchQuery(e.target.value)}
              placeholder={t.inspector.taskSearchPlaceholder}
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
                setTaskSortOrder("latest");
                setTaskSearchQuery("");
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
