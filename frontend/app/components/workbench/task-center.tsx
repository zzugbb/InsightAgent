"use client";

import {
  Button,
  Dropdown,
  Flex,
  Input,
  Segmented,
  Space,
  Tag,
  type MenuProps,
} from "antd";
import { MoreHorizontal } from "lucide-react";
import type { RefObject } from "react";
import { useMemo, useState } from "react";

import { useMessages, usePreferences } from "../../../lib/preferences-context";

import type { SessionSummary, TaskSummary } from "./types";
import {
  extractTaskFailureHint,
  formatTimestamp,
  getTaskLabel,
  isTaskFailedStatus,
  resolveTaskUsageFromTask,
} from "./utils";

type SettingsSummaryLite = {
  mode: string;
  provider: string;
  model: string;
} | null;

type TaskCenterProps = {
  activeSession: SessionSummary | undefined;
  activeSessionId: string | null;
  activeTaskId: string | null;
  settingsSummary: SettingsSummaryLite;
  recentTasks: TaskSummary[];
  tasksLoading: boolean;
  tasksFetchNextBusy: boolean;
  tasksCanLoadMore: boolean;
  onLoadMoreTasks: () => void;
  onSelectTask: (task: TaskSummary) => void;
  showSessionDrawerTrigger: boolean;
  onOpenSessionDrawer: () => void;
  sessionDrawerTriggerRef?: RefObject<HTMLButtonElement | null>;
  showInspectorTrigger: boolean;
  onOpenInspector: () => void;
  inspectorDrawerTriggerRef?: RefObject<HTMLButtonElement | null>;
  onBackToChat: () => void;
  onExportSession: (format: "json" | "markdown") => void | Promise<void>;
  sessionExportDisabled: boolean;
  sessionExporting: "json" | "markdown" | null;
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
  settingsSummary,
  recentTasks,
  tasksLoading,
  tasksFetchNextBusy,
  tasksCanLoadMore,
  onLoadMoreTasks,
  onSelectTask,
  showSessionDrawerTrigger,
  onOpenSessionDrawer,
  sessionDrawerTriggerRef,
  showInspectorTrigger,
  onOpenInspector,
  inspectorDrawerTriggerRef,
  onBackToChat,
  onExportSession,
  sessionExportDisabled,
  sessionExporting,
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
  const [taskPrioritizeFailed, setTaskPrioritizeFailed] = useState(true);
  const [taskSearchQuery, setTaskSearchQuery] = useState("");

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
    if (!taskPrioritizeFailed) {
      return sorted;
    }
    return sorted.sort((a, b) => {
      const af = isTaskFailedStatus(a.status) ? 1 : 0;
      const bf = isTaskFailedStatus(b.status) ? 1 : 0;
      return bf - af;
    });
  }, [scopedTasks, taskSearchQuery, taskSortOrder, taskStatusFilter, taskPrioritizeFailed]);

  const scopeDisabledSession = !activeSessionId;
  const sessionActionMenu = useMemo<MenuProps["items"]>(
    () => [
      {
        key: "session-export-json",
        disabled: sessionExportDisabled || sessionExporting !== null,
        label: (
          <span data-testid="task-center-session-export-json">
            {t.inspector.sessionExportJson}
          </span>
        ),
        onClick: () => {
          void onExportSession("json");
        },
      },
      {
        key: "session-export-markdown",
        disabled: sessionExportDisabled || sessionExporting !== null,
        label: (
          <span data-testid="task-center-session-export-markdown">
            {t.inspector.sessionExportMarkdown}
          </span>
        ),
        onClick: () => {
          void onExportSession("markdown");
        },
      },
    ],
    [onExportSession, sessionExportDisabled, sessionExporting, t.inspector],
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
        <Flex wrap="wrap" gap="small" align="center" justify="flex-end" className="chat-header-actions">
          <Space wrap size="small">
            {showSessionDrawerTrigger ? (
              <Button
                ref={sessionDrawerTriggerRef}
                type="default"
                className="mobile-inspector-trigger"
                onClick={onOpenSessionDrawer}
              >
                {t.chat.sessionList}
              </Button>
            ) : null}
            {showInspectorTrigger ? (
              <Button
                ref={inspectorDrawerTriggerRef}
                type="default"
                className="mobile-inspector-trigger"
                onClick={onOpenInspector}
              >
                {t.chat.traceAndContext}
              </Button>
            ) : null}
            <Button type="default" onClick={onBackToChat} data-testid="task-center-back-chat">
              {t.chat.backToChat}
            </Button>
            <Dropdown menu={{ items: sessionActionMenu }} trigger={["click"]}>
              <Button
                type="default"
                icon={<MoreHorizontal size={16} strokeWidth={2} aria-hidden />}
                data-testid="task-center-session-actions"
                loading={sessionExporting !== null}
                disabled={sessionExportDisabled}
              >
                {t.chat.moreActions}
              </Button>
            </Dropdown>
          </Space>
          <div className="chat-runtime-badges" aria-label="runtime">
            <Tag variant="filled" className="header-badge-tag header-badge-tag--mode">
              <span className="header-badge-label">{t.chat.modeLabel}</span>
              <span className="header-badge-value">{settingsSummary?.mode ?? "—"}</span>
            </Tag>
            <Tag variant="filled" className="header-badge-tag header-badge-tag--stack">
              <span className="header-badge-value header-badge-value--mono">
                {settingsSummary?.provider ?? "—"}
              </span>
              <span className="header-badge-sep" aria-hidden>
                /
              </span>
              <span className="header-badge-value header-badge-value--mono header-badge-value--model">
                {settingsSummary?.model ?? "—"}
              </span>
            </Tag>
          </div>
        </Flex>
      </header>

      <section className="task-center-main" aria-labelledby="task-center-title">
        <div className="task-center-toolbar">
          <span className="task-index-toolbar-label">{t.taskCenter.scopeLabel}</span>
          <Segmented
            size="small"
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
          />
          <span className="task-index-toolbar-label">{t.inspector.taskViewLabel}</span>
          <Segmented
            size="small"
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
          />
          <Input
            size="small"
            allowClear
            value={taskSearchQuery}
            onChange={(e) => setTaskSearchQuery(e.target.value)}
            placeholder={t.inspector.taskSearchPlaceholder}
          />
          <Segmented
            size="small"
            value={taskSortOrder}
            onChange={(v) => setTaskSortOrder(v as "latest" | "oldest")}
            options={[
              { label: t.inspector.taskSortLatest, value: "latest" },
              { label: t.inspector.taskSortOldest, value: "oldest" },
            ]}
          />
          <Button
            type={taskPrioritizeFailed ? "primary" : "default"}
            size="small"
            onClick={() => setTaskPrioritizeFailed((v) => !v)}
          >
            {t.inspector.taskPinFailed}
          </Button>
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

        <p className="task-index-summary">
          {t.inspector.taskVisibleCount(filteredTasks.length, scopedTasks.length)}
        </p>

        {tasksLoading ? (
          <div className="task-center-loading">
            <div className="skeleton message-skeleton-row" />
            <div className="skeleton message-skeleton-row" />
          </div>
        ) : null}

        {!tasksLoading ? (
          <div className="task-summary-list task-center-list">
            {filteredTasks.map((task) => {
              const isActive = task.id === activeTaskId;
              const failedHint = extractTaskFailureHint(task);
              const usage = resolveTaskUsageFromTask(task);
              const usageSourceText = usage?.usageSource
                ? usage.usageSource === "provider"
                  ? t.inspector.usageSourceProvider
                  : usage.usageSource === "estimated"
                    ? t.inspector.usageSourceEstimated
                    : t.inspector.usageSourceLegacy
                : null;
              const usageLine = usage
                ? [
                    usage.completion
                      ? `${t.inspector.usageCompletion}: ${usage.completion}`
                      : null,
                    usage.total ? `${t.inspector.usageTotal}: ${usage.total}` : null,
                    usage.cost ? `${t.inspector.usageCost}: ${usage.cost}` : null,
                    usageSourceText
                      ? `${t.inspector.usageSource}: ${usageSourceText}`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")
                : "";
              return (
                <div
                  key={task.id}
                  className={`task-summary-item${isActive ? " is-active" : ""}${isTaskFailedStatus(task.status) ? " task-summary-item--failed" : ""}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectTask(task)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelectTask(task);
                    }
                  }}
                >
                  <strong>{getTaskLabel(task, t.workbench)}</strong>
                  <div className="task-summary-meta">
                    <span
                      className={`task-status-badge task-status-badge--${resolveTaskStatusTone(task.status)}`}
                    >
                      {task.status}
                    </span>
                    <span>{formatTimestamp(task.updated_at, localeTag)}</span>
                  </div>
                  {usageLine ? <span className="task-summary-usage">{usageLine}</span> : null}
                  {failedHint ? (
                    <span className="task-summary-failed-hint">
                      {t.inspector.taskFailureHint}: {failedHint}
                    </span>
                  ) : null}
                  <div className="task-summary-actions">
                    <Button
                      size="small"
                      type="text"
                      className="task-summary-open-detail"
                      data-testid="task-center-open-task-detail"
                      aria-label={t.taskCenter.openTaskDetailAria}
                      href={`/tasks/${encodeURIComponent(task.id)}`}
                      onClick={(event) => {
                        event.stopPropagation();
                      }}
                    >
                      {t.taskCenter.openTaskDetail}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : null}

        {!tasksLoading && filteredTasks.length === 0 ? (
          <p className="panel-note panel-note--muted">{t.inspector.taskEmpty}</p>
        ) : null}

        {tasksCanLoadMore ? (
          <div className="inspector-task-load-more">
            <Button
              type="default"
              size="small"
              block
              loading={tasksFetchNextBusy}
              onClick={onLoadMoreTasks}
            >
              {t.inspector.loadMoreTasks}
            </Button>
          </div>
        ) : null}
      </section>
    </section>
  );
}
