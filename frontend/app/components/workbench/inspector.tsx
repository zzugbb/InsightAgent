"use client";

import { App, Button, Input, Segmented, Space, Tabs } from "antd";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import {
  forwardRef,
  useEffect,
  useMemo,
  useState,
  type MouseEvent,
} from "react";

import { apiPostJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import type { TraceStepPayload } from "../../../lib/types/trace";
import {
  useMessages,
  usePreferences,
} from "../../../lib/preferences-context";

import type { SseTaskUsage } from "../../../lib/stores/chat-stream-store";
import type {
  InspectorTab,
  MemoryAddResponse,
  MemoryQueryResponse,
  SessionMemoryStatus,
  TaskSummary,
  UsageSummary,
} from "./types";
import { TraceFlowView } from "./trace-flow-view";
import {
  extractTaskFailureHint,
  formatTimestamp,
  formatTraceStepMetaSubtitle,
  getStepTitle,
  getTaskLabel,
  isTaskFailedStatus,
  normalizeTraceStepKind,
  parseMemoryMetadataJson,
  resolveInspectorTaskUsage,
  resolveTaskUsageFromTask,
  shortenId,
} from "./utils";

const TRACE_PREVIEW = 6;

const { TextArea } = Input;

type InspectorProps = {
  tab: InspectorTab;
  setTab: (tab: InspectorTab) => void;
  desktopInspectorChrome: boolean;
  inspectorCollapsed: boolean;
  onToggleInspectorCollapsed: () => void;
  onInspectorResizeStart: (event: MouseEvent) => void;
  isStreaming: boolean;
  sseTraceSteps: TraceStepPayload[];
  sseMessage: string;
  sseTaskId: string | null;
  phaseLabel: string;
  traceCursor: number;
  traceDeltaSyncStatus: "idle" | "syncing" | "ok" | "retrying" | "paused";
  traceDeltaRetryCount: number;
  traceDeltaLastOkAt: number | null;
  traceDeltaLastError: string | null;
  traceDeltaNextRetryAt: number | null;
  traceDeltaRecoveredAt: number | null;
  sseTaskUsage: SseTaskUsage | null;
  activeSessionId: string | null;
  activeTaskId: string | null;
  activeTask: TaskSummary | undefined;
  latestTaskForSession: TaskSummary | undefined;
  recentTasks: TaskSummary[];
  tasksFetchNextBusy: boolean;
  tasksCanLoadMore: boolean;
  onLoadMoreTasks: () => void;
  onReplayTrace: () => void;
  onLoadDelta: () => void;
  onSelectTask: (task: TaskSummary) => void;
  apiBaseUrl: string;
  sessionMemoryStatus: SessionMemoryStatus | undefined;
  sessionMemoryLoading: boolean;
  sessionMemoryError: string | null;
  usageSummary: UsageSummary | undefined;
  usageSummaryLoading: boolean;
  usageSummaryError: string | null;
  usageSummaryScope: "session" | "global";
};

export const Inspector = forwardRef<HTMLElement, InspectorProps>(function Inspector(
  {
    tab,
    setTab,
    desktopInspectorChrome,
    inspectorCollapsed,
    onToggleInspectorCollapsed,
    onInspectorResizeStart,
    isStreaming,
    sseTraceSteps,
    sseMessage,
    sseTaskId,
    phaseLabel,
    traceCursor,
    traceDeltaSyncStatus,
    traceDeltaRetryCount,
    traceDeltaLastOkAt,
    traceDeltaLastError,
    traceDeltaNextRetryAt,
    traceDeltaRecoveredAt,
    sseTaskUsage,
    activeSessionId,
    activeTaskId,
    activeTask,
    latestTaskForSession,
    recentTasks,
    tasksFetchNextBusy,
    tasksCanLoadMore,
    onLoadMoreTasks,
    onReplayTrace,
    onLoadDelta,
    onSelectTask,
    apiBaseUrl,
    sessionMemoryStatus,
    sessionMemoryLoading,
    sessionMemoryError,
    usageSummary,
    usageSummaryLoading,
    usageSummaryError,
    usageSummaryScope,
  },
  ref,
) {
  const t = useMessages();
  const { localeTag, theme } = usePreferences();
  const hasTaskContext = Boolean(sseTaskId?.trim());
  const [expandAllTrace, setExpandAllTrace] = useState(false);
  const [traceView, setTraceView] = useState<"list" | "flow">("list");
  const [traceDensity, setTraceDensity] = useState<"comfortable" | "compact">(
    "comfortable",
  );
  const [traceKindFilter, setTraceKindFilter] = useState<
    "all" | "thought" | "action" | "observation" | "tool" | "rag" | "other"
  >("all");
  const [traceSearchQuery, setTraceSearchQuery] = useState("");
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [memoryAddDraft, setMemoryAddDraft] = useState("");
  const [memoryMetaDraft, setMemoryMetaDraft] = useState("");
  const [memoryQueryDraft, setMemoryQueryDraft] = useState("");
  const [taskStatusFilter, setTaskStatusFilter] = useState<
    "all" | "running" | "completed" | "failed"
  >("all");
  const [taskSortOrder, setTaskSortOrder] = useState<"latest" | "oldest">(
    "latest",
  );
  const [taskPrioritizeFailed, setTaskPrioritizeFailed] = useState(true);
  const [taskSearchQuery, setTaskSearchQuery] = useState("");
  const [retryCountdownSec, setRetryCountdownSec] = useState<number | null>(null);

  const scrollToContextSection = (id: string) => {
    const el = document.getElementById(id);
    if (!el) {
      return;
    }
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const memoryAddMutation = useMutation({
    mutationFn: async (payload: {
      text: string;
      metadata: Record<string, string> | null;
    }) => {
      if (!activeSessionId?.trim()) {
        throw new Error("NO_SESSION");
      }
      const body: { text: string; metadata?: Record<string, string> } = {
        text: payload.text,
      };
      if (payload.metadata && Object.keys(payload.metadata).length > 0) {
        body.metadata = payload.metadata;
      }
      return apiPostJson<MemoryAddResponse>(
        `${apiBaseUrl}/api/sessions/${encodeURIComponent(activeSessionId)}/memory/add`,
        body,
      );
    },
    onSuccess: (data) => {
      if (activeSessionId) {
        void queryClient.invalidateQueries({
          queryKey: ["session-memory-status", activeSessionId],
        });
      }
      message.success(t.inspector.memory.addSuccess(data.document_count));
    },
  });

  const memoryQueryMutation = useMutation({
    mutationFn: async (text: string) => {
      if (!activeSessionId?.trim()) {
        throw new Error("NO_SESSION");
      }
      return apiPostJson<MemoryQueryResponse>(
        `${apiBaseUrl}/api/sessions/${encodeURIComponent(activeSessionId)}/memory/query`,
        { text, n_results: 8 },
      );
    },
  });

  useEffect(() => {
    setMemoryAddDraft("");
    setMemoryMetaDraft("");
    setMemoryQueryDraft("");
    memoryAddMutation.reset();
    memoryQueryMutation.reset();
    // 仅在切换会话时清空调试区
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId]);

  const collapsedRail =
    desktopInspectorChrome && inspectorCollapsed;
  const showDesktopChrome =
    desktopInspectorChrome && !inspectorCollapsed;

  const traceKindStats = useMemo(() => {
    const stats = {
      thought: 0,
      action: 0,
      observation: 0,
      tool: 0,
      rag: 0,
      other: 0,
    };
    for (const step of sseTraceSteps) {
      const kind = normalizeTraceStepKind(step);
      if (kind in stats) {
        stats[kind as keyof typeof stats] += 1;
      } else {
        stats.other += 1;
      }
    }
    return stats;
  }, [sseTraceSteps]);

  const filteredTraceSteps = useMemo(() => {
    const q = traceSearchQuery.trim().toLowerCase();
    return sseTraceSteps.filter((step) => {
      const kind = normalizeTraceStepKind(step);
      if (traceKindFilter !== "all" && kind !== traceKindFilter) {
        return false;
      }
      if (!q) {
        return true;
      }
      const title = getStepTitle(step).toLowerCase();
      const content = (step.content ?? "").toLowerCase();
      const id = step.id.toLowerCase();
      const model =
        typeof step.meta?.model === "string" ? step.meta.model.toLowerCase() : "";
      const toolName =
        typeof step.meta?.tool?.name === "string"
          ? step.meta.tool.name.toLowerCase()
          : "";
      return (
        title.includes(q) ||
        content.includes(q) ||
        id.includes(q) ||
        model.includes(q) ||
        toolName.includes(q)
      );
    });
  }, [sseTraceSteps, traceKindFilter, traceSearchQuery]);

  const { visibleSteps, hiddenCount } = useMemo(() => {
    const steps = filteredTraceSteps;
    if (expandAllTrace || steps.length <= TRACE_PREVIEW) {
      return { visibleSteps: steps, hiddenCount: 0 };
    }
    return {
      visibleSteps: steps.slice(-TRACE_PREVIEW),
      hiddenCount: steps.length - TRACE_PREVIEW,
    };
  }, [filteredTraceSteps, expandAllTrace]);

  const inspectorTaskUsage = useMemo(
    () =>
      resolveInspectorTaskUsage({
        taskId: activeTaskId,
        activeTask,
        sseTaskUsage,
      }),
    [activeTaskId, activeTask, sseTaskUsage],
  );

  const sessionUsageAggregate = useMemo(() => {
    if (!usageSummary) {
      return null;
    }
    const tokenFmt = new Intl.NumberFormat(localeTag, {
      maximumFractionDigits: 0,
    });
    const costFmt = (n: number | null | undefined) =>
      n === null || n === undefined ? null : `$${n.toFixed(6)}`;

    return {
      prompt: tokenFmt.format(Math.trunc(usageSummary.prompt_tokens)),
      completion: tokenFmt.format(
        Math.trunc(usageSummary.completion_tokens),
      ),
      total: tokenFmt.format(Math.trunc(usageSummary.total_tokens)),
      cost: costFmt(usageSummary.cost_estimate),
      avgTotal:
        usageSummary.avg_total_tokens === null
          ? null
          : tokenFmt.format(Math.trunc(usageSummary.avg_total_tokens)),
      avgCost: costFmt(usageSummary.avg_cost_estimate),
      taskCount: usageSummary.tasks_with_usage,
    };
  }, [localeTag, usageSummary]);

  const traceDeltaSyncStatusLabel =
    traceDeltaSyncStatus === "syncing"
      ? t.inspector.traceSyncStateSyncing
      : traceDeltaSyncStatus === "ok"
        ? t.inspector.traceSyncStateOk
        : traceDeltaSyncStatus === "retrying"
          ? t.inspector.traceSyncStateRetrying
          : traceDeltaSyncStatus === "paused"
            ? t.inspector.traceSyncStatePaused
          : t.inspector.traceSyncStateIdle;
  const traceDeltaLastOkLabel =
    traceDeltaLastOkAt === null
      ? "—"
      : new Date(traceDeltaLastOkAt).toLocaleTimeString(localeTag, {
          hour12: false,
        });
  const traceDeltaNextRetryLabel =
    traceDeltaSyncStatus === "retrying" && traceDeltaNextRetryAt !== null
      ? new Date(traceDeltaNextRetryAt).toLocaleTimeString(localeTag, {
          hour12: false,
        })
      : "—";
  const traceDeltaRecoveredLabel =
    traceDeltaSyncStatus !== "ok" || traceDeltaRecoveredAt === null
      ? null
      : new Date(traceDeltaRecoveredAt).toLocaleTimeString(localeTag, {
          hour12: false,
        });
  useEffect(() => {
    if (traceDeltaSyncStatus !== "retrying" || traceDeltaNextRetryAt === null) {
      setRetryCountdownSec(null);
      return;
    }
    const updateCountdown = () => {
      const ms = traceDeltaNextRetryAt - Date.now();
      setRetryCountdownSec(ms <= 0 ? 0 : Math.ceil(ms / 1000));
    };
    updateCountdown();
    const timer = window.setInterval(updateCountdown, 1000);
    return () => window.clearInterval(timer);
  }, [traceDeltaSyncStatus, traceDeltaNextRetryAt]);
  const showTraceDeltaWarning =
    isStreaming &&
    traceDeltaSyncStatus === "retrying" &&
    traceDeltaRetryCount >= 2;

  const filteredTasks = useMemo(() => {
    const q = taskSearchQuery.trim().toLowerCase();
    const statusMatched = recentTasks.filter((task) => {
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
  }, [recentTasks, taskStatusFilter, taskSortOrder, taskPrioritizeFailed, taskSearchQuery]);

  const resolveTaskStatusTone = (status: string): "running" | "completed" | "failed" | "other" => {
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
  };

  const tracePanel = (
    <section
      className="inspector-panel"
      role="tabpanel"
      id="inspector-panel-trace"
      aria-labelledby="inspector-tab-trace"
    >
      <div className="panel-head">
        <div>
          <p className="chat-kicker">{t.inspector.traceKicker}</p>
          <h3>{t.inspector.timelineTitle}</h3>
        </div>
        <span>
          {sseTraceSteps.length > 0
            ? t.inspector.traceVisibleCount(
                filteredTraceSteps.length,
                sseTraceSteps.length,
              )
            : t.inspector.stepsNone}
        </span>
      </div>

      <div className="trace-view-toolbar">
        <Segmented
          value={traceView}
          onChange={(v) => setTraceView(v as "list" | "flow")}
          options={[
            { label: t.inspector.traceViewList, value: "list" },
            { label: t.inspector.traceViewFlow, value: "flow" },
          ]}
        />
      </div>
      <div className="trace-filter-toolbar">
        <Segmented
          size="small"
          value={traceKindFilter}
          onChange={(v) =>
            setTraceKindFilter(
              v as "all" | "thought" | "action" | "observation" | "tool" | "rag" | "other",
            )
          }
          options={[
            { label: t.inspector.traceFilterAll, value: "all" },
            { label: t.inspector.traceFilterThought, value: "thought" },
            { label: t.inspector.traceFilterAction, value: "action" },
            { label: t.inspector.traceFilterObservation, value: "observation" },
            { label: t.inspector.traceFilterTool, value: "tool" },
            { label: t.inspector.traceFilterRag, value: "rag" },
            { label: t.inspector.traceFilterOther, value: "other" },
          ]}
        />
        <Input
          size="small"
          allowClear
          value={traceSearchQuery}
          onChange={(e) => setTraceSearchQuery(e.target.value)}
          placeholder={t.inspector.traceSearchPlaceholder}
        />
        <Segmented
          size="small"
          value={traceDensity}
          onChange={(v) => setTraceDensity(v as "comfortable" | "compact")}
          options={[
            { label: t.inspector.traceDensityComfortable, value: "comfortable" },
            { label: t.inspector.traceDensityCompact, value: "compact" },
          ]}
        />
      </div>
      <div className="trace-kind-stats">
        <span>{t.inspector.traceFlow.kindThought}: {traceKindStats.thought}</span>
        <span>{t.inspector.traceFlow.kindAction}: {traceKindStats.action}</span>
        <span>{t.inspector.traceFlow.kindObservation}: {traceKindStats.observation}</span>
        <span>{t.inspector.traceFlow.kindTool}: {traceKindStats.tool}</span>
        <span>{t.inspector.traceFlow.kindRag}: {traceKindStats.rag}</span>
        <span>{t.inspector.traceFlow.kindOther}: {traceKindStats.other}</span>
      </div>

      {traceView === "list" && filteredTraceSteps.length > TRACE_PREVIEW ? (
        <div className="trace-density-row">
          <Button
            type="default"
            className="trace-density-btn"
            onClick={() => setExpandAllTrace((v) => !v)}
          >
            {expandAllTrace
              ? t.workbench.traceCollapse
              : t.workbench.traceExpandAll}
          </Button>
          {!expandAllTrace && hiddenCount > 0 ? (
            <span className="trace-density-note">
              {t.workbench.traceHidden(hiddenCount)}
            </span>
          ) : null}
        </div>
      ) : null}

      <div className="panel-actions">
        <Space wrap>
          <Button
            type="default"
            disabled={isStreaming || !hasTaskContext}
            onClick={onReplayTrace}
          >
            {t.inspector.replayTrace}
          </Button>
          <Button
            type="default"
            disabled={isStreaming || !hasTaskContext}
            onClick={onLoadDelta}
          >
            {t.inspector.loadDelta}
          </Button>
        </Space>
      </div>

      <p className="panel-note">{sseMessage}</p>

      {traceView === "flow" && filteredTraceSteps.length > 0 ? (
        <TraceFlowView steps={filteredTraceSteps} colorMode={theme} />
      ) : traceView === "list" && visibleSteps.length > 0 ? (
        <div className={`trace-feed trace-feed--${traceDensity}`}>
          {visibleSteps.map((step) => {
            const traceKind = normalizeTraceStepKind(step);
            const metaLine = formatTraceStepMetaSubtitle(
              step,
              t.inspector.traceMeta,
            );
            return (
            <article
              key={step.id}
              className={`trace-card trace-card--enter trace-card--kind-${traceKind}${traceDensity === "compact" ? " trace-card--compact" : ""}`}
              data-trace-kind={traceKind}
            >
              <div className="trace-top">
                <strong>{getStepTitle(step)}</strong>
                <span>
                  {typeof step.seq === "number"
                    ? `${t.inspector.seqLabel} ${step.seq}`
                    : shortenId(step.id)}
                </span>
              </div>
              {metaLine ? (
                <p className="trace-card-meta">{metaLine}</p>
              ) : null}
              <p>{step.content || t.inspector.stepEmpty}</p>
            </article>
            );
          })}
        </div>
      ) : filteredTraceSteps.length === 0 && sseTraceSteps.length > 0 ? (
        <div className="panel-empty">{t.inspector.traceNoMatch}</div>
      ) : (
        <div className="panel-empty">{t.inspector.traceEmpty}</div>
      )}
    </section>
  );

  const contextPanel = (
    <section
      className="inspector-panel"
      role="tabpanel"
      id="inspector-panel-context"
      aria-labelledby="inspector-tab-context"
    >
      <div className="panel-head">
        <div>
          <p className="chat-kicker">{t.inspector.contextKicker}</p>
          <h3>{t.inspector.summaryTitle}</h3>
        </div>
      </div>
      <div className="context-jumpbar">
        <span className="context-jumpbar-label">{t.inspector.contextJumpTo}</span>
        <div className="context-jumpbar-actions">
          <Button size="small" onClick={() => scrollToContextSection("ctx-overview")}>
            {t.inspector.contextJumpOverview}
          </Button>
          <Button size="small" onClick={() => scrollToContextSection("ctx-sync")}>
            {t.inspector.contextJumpSync}
          </Button>
          <Button size="small" onClick={() => scrollToContextSection("ctx-usage")}>
            {t.inspector.contextJumpUsage}
          </Button>
          <Button size="small" onClick={() => scrollToContextSection("ctx-memory")}>
            {t.inspector.contextJumpMemory}
          </Button>
          <Button size="small" onClick={() => scrollToContextSection("ctx-tasks")}>
            {t.inspector.contextJumpTasks}
          </Button>
        </div>
      </div>

      <div className="inspector-kpi-grid" id="ctx-overview">
        <div className="inspector-kpi-item">
          <span>{t.inspector.currentPhase}</span>
          <strong>{phaseLabel}</strong>
        </div>
        <div className="inspector-kpi-item">
          <span>{t.inspector.currentTask}</span>
          <strong>{activeTaskId ? shortenId(activeTaskId) : "—"}</strong>
        </div>
        <div className="inspector-kpi-item">
          <span>{t.inspector.traceCursor}</span>
          <strong>{traceCursor}</strong>
        </div>
        <div className="inspector-kpi-item">
          <span>{t.inspector.traceSyncStatus}</span>
          <strong>{traceDeltaSyncStatusLabel}</strong>
        </div>
        <div className="inspector-kpi-item">
          <span>{t.inspector.session}</span>
          <strong>{activeSessionId ? shortenId(activeSessionId) : "—"}</strong>
        </div>
      </div>

      <div className="inspector-block" id="ctx-sync">
        <p className="summary-label">{t.inspector.traceSyncStatus}</p>
        <p className="inspector-section-lead">{t.inspector.traceSyncLead}</p>
        <div className="context-grid context-grid--stats compact">
          <span>{t.inspector.traceSyncRetries}</span>
          <strong>{traceDeltaRetryCount}</strong>
          <span>{t.inspector.traceSyncLastOk}</span>
          <strong>{traceDeltaLastOkLabel}</strong>
          <span>{t.inspector.traceSyncNextRetry}</span>
          <strong>{traceDeltaNextRetryLabel}</strong>
        </div>
        {showTraceDeltaWarning ? (
          <p className="panel-note panel-note--muted">
            {t.inspector.traceSyncWarning(traceDeltaRetryCount)}
          </p>
        ) : null}
        {traceDeltaSyncStatus === "retrying" && traceDeltaLastError ? (
          <p className="panel-note panel-note--muted">
            {t.inspector.traceSyncLastError(traceDeltaLastError)}
          </p>
        ) : null}
        {traceDeltaSyncStatus === "retrying" && retryCountdownSec !== null ? (
          <p className="panel-note panel-note--muted">
            {t.inspector.traceSyncRetryEta(retryCountdownSec)}
          </p>
        ) : null}
        {traceDeltaRecoveredLabel ? (
          <p className="panel-note panel-note--muted">
            {t.inspector.traceSyncRecovered(traceDeltaRecoveredLabel)}
          </p>
        ) : null}
      </div>

      <div className="inspector-block" id="ctx-usage">
        <p className="summary-label inspector-usage-kicker">{t.inspector.usageTitle}</p>
        <p className="inspector-section-lead">{t.inspector.usageLead}</p>
        {inspectorTaskUsage ? (
          <div className="context-grid context-grid--stats">
            <span>{t.inspector.usagePrompt}</span>
            <strong>{inspectorTaskUsage.prompt ?? "—"}</strong>
            <span>{t.inspector.usageCompletion}</span>
            <strong>{inspectorTaskUsage.completion ?? "—"}</strong>
            <span>{t.inspector.usageTotal}</span>
            <strong>{inspectorTaskUsage.total ?? "—"}</strong>
            <span>{t.inspector.usageCost}</span>
            <strong>{inspectorTaskUsage.cost ?? "—"}</strong>
          </div>
        ) : (
          <p className="panel-note panel-note--muted">{t.inspector.usageSummaryEmpty}</p>
        )}

        {usageSummaryLoading ? (
          <p className="panel-note panel-note--muted">{t.inspector.usageSummaryLoading}</p>
        ) : null}
        {usageSummaryError ? (
          <p className="panel-note panel-note--muted">{t.inspector.usageSummaryError}</p>
        ) : null}

        {sessionUsageAggregate ? (
          <div className="inspector-subblock">
            <p className="summary-label inspector-usage-kicker">
              {t.inspector.usageSummaryTitle}
            </p>
            <span>
              {usageSummaryScope === "session"
                ? t.inspector.usageScopeSession
                : t.inspector.usageScopeGlobal}
            </span>
            <div className="context-grid context-grid--stats compact">
              <span>{t.inspector.usagePrompt}</span>
              <strong>{sessionUsageAggregate.prompt ?? "—"}</strong>
              <span>{t.inspector.usageCompletion}</span>
              <strong>{sessionUsageAggregate.completion ?? "—"}</strong>
              <span>{t.inspector.usageTotal}</span>
              <strong>{sessionUsageAggregate.total ?? "—"}</strong>
              <span>{t.inspector.usageCost}</span>
              <strong>{sessionUsageAggregate.cost ?? "—"}</strong>
              <span>{t.inspector.usageAvgTotal}</span>
              <strong>{sessionUsageAggregate.avgTotal ?? "—"}</strong>
              <span>{t.inspector.usageAvgCost}</span>
              <strong>{sessionUsageAggregate.avgCost ?? "—"}</strong>
            </div>
            <span>{t.inspector.usageTaskCount(sessionUsageAggregate.taskCount)}</span>
            <span>
              {t.inspector.usageTaskCoverage(
                usageSummary?.tasks_with_usage ?? sessionUsageAggregate.taskCount,
                usageSummary?.tasks_total ?? sessionUsageAggregate.taskCount,
              )}
            </span>
          </div>
        ) : null}

        {!usageSummaryLoading &&
        !usageSummaryError &&
        usageSummary &&
        usageSummary.tasks_with_usage === 0 ? (
          <p className="panel-note panel-note--muted">{t.inspector.usageSummaryEmpty}</p>
        ) : null}
      </div>

      <div className="inspector-block memory-placeholder-card" id="ctx-memory">
        <p className="summary-label">{t.inspector.memory.kicker}</p>
        <strong className="memory-placeholder-title">{t.inspector.memory.title}</strong>
        <p className="panel-note panel-note--muted memory-placeholder-lead">
          {t.inspector.memory.lead}
        </p>
        <div className="memory-collection-row">
          <span className="memory-collection-label">
            {t.inspector.memory.collectionLabel}
          </span>
          <code className="memory-collection-code">
            {activeSessionId
              ? `memory_${activeSessionId}`
              : "—"}
          </code>
        </div>
        <div className="memory-status-block" aria-live="polite">
          {!activeSessionId ? (
            <p className="panel-note panel-note--muted memory-pick-session">
              {t.inspector.memory.pickSession}
            </p>
          ) : sessionMemoryLoading ? (
            <p className="memory-status-loading">{t.inspector.memory.statusLoading}</p>
          ) : sessionMemoryError ? (
            <p className="memory-status-err">{sessionMemoryError}</p>
          ) : sessionMemoryStatus ? (
            <>
              <div className="memory-status-line">
                <span className="memory-status-key">Chroma</span>
                <span
                  className={
                    sessionMemoryStatus.chroma_reachable
                      ? "memory-status-val memory-status-val--ok"
                      : "memory-status-val memory-status-val--bad"
                  }
                >
                  {sessionMemoryStatus.chroma_reachable
                    ? t.inspector.memory.chromaConnected
                    : t.inspector.memory.chromaDisconnected}
                </span>
              </div>
              {sessionMemoryStatus.chroma_reachable ? (
                <>
                  <div className="memory-status-line">
                    <span className="memory-status-key"> </span>
                    <span className="memory-status-val">
                      {sessionMemoryStatus.collection_exists
                        ? t.inspector.memory.collectionExists
                        : t.inspector.memory.collectionMissing}
                    </span>
                  </div>
                  <div className="memory-status-line">
                    <span className="memory-status-key"> </span>
                    <span className="memory-status-val">
                      {t.inspector.memory.docCount(
                        sessionMemoryStatus.document_count,
                      )}
                    </span>
                  </div>
                </>
              ) : null}
              {sessionMemoryStatus.error ? (
                <p className="panel-note panel-note--muted memory-chroma-err">
                  {sessionMemoryStatus.error}
                </p>
              ) : null}
            </>
          ) : null}
        </div>
        {activeSessionId ? (
          <div className="memory-debug-block">
            <p className="memory-debug-kicker">{t.inspector.memory.debugKicker}</p>
            <TextArea
              className="memory-debug-textarea"
              value={memoryAddDraft}
              onChange={(e) => setMemoryAddDraft(e.target.value)}
              placeholder={t.inspector.memory.addPlaceholder}
              rows={2}
              disabled={memoryAddMutation.isPending}
            />
            <TextArea
              className="memory-debug-textarea memory-debug-textarea--meta"
              value={memoryMetaDraft}
              onChange={(e) => setMemoryMetaDraft(e.target.value)}
              placeholder={t.inspector.memory.metadataPlaceholder}
              rows={2}
              disabled={memoryAddMutation.isPending}
            />
            <div className="memory-debug-actions">
              <Button
                type="primary"
                size="small"
                loading={memoryAddMutation.isPending}
                onClick={() => {
                  const text = memoryAddDraft.trim();
                  if (!text) {
                    message.warning(t.inspector.memory.addEmpty);
                    return;
                  }
                  const parsed = parseMemoryMetadataJson(memoryMetaDraft);
                  if (!parsed.ok) {
                    message.warning(t.inspector.memory.metadataInvalid);
                    return;
                  }
                  memoryAddMutation.mutate({
                    text,
                    metadata: parsed.metadata,
                  });
                }}
              >
                {t.inspector.memory.addButton}
              </Button>
            </div>
            {memoryAddMutation.isError && memoryAddMutation.error ? (
              <p className="memory-debug-err">
                {(() => {
                  const u = toUserFacingError(memoryAddMutation.error, t.errors);
                  return u.hint ? `${u.banner} ${u.hint}` : u.banner;
                })()}
              </p>
            ) : null}
            <TextArea
              className="memory-debug-textarea memory-debug-textarea--query"
              value={memoryQueryDraft}
              onChange={(e) => setMemoryQueryDraft(e.target.value)}
              placeholder={t.inspector.memory.queryPlaceholder}
              rows={2}
              disabled={memoryQueryMutation.isPending}
            />
            <div className="memory-debug-actions">
              <Button
                size="small"
                loading={memoryQueryMutation.isPending}
                onClick={() => {
                  const text = memoryQueryDraft.trim();
                  if (!text) {
                    message.warning(t.inspector.memory.queryInputEmpty);
                    return;
                  }
                  memoryQueryMutation.mutate(text);
                }}
              >
                {t.inspector.memory.queryButton}
              </Button>
            </div>
            {memoryQueryMutation.isError && memoryQueryMutation.error ? (
              <p className="memory-debug-err">
                {(() => {
                  const u = toUserFacingError(memoryQueryMutation.error, t.errors);
                  return u.hint ? `${u.banner} ${u.hint}` : u.banner;
                })()}
              </p>
            ) : null}
            {memoryQueryMutation.isSuccess && memoryQueryMutation.data ? (
              <div className="memory-query-results" aria-live="polite">
                <p className="memory-query-hits-label">
                  {t.inspector.memory.queryHits(
                    memoryQueryMutation.data.documents[0]?.length ?? 0,
                  )}
                </p>
                {(memoryQueryMutation.data.documents[0]?.length ?? 0) === 0 ? (
                  <p className="panel-note panel-note--muted">{t.inspector.memory.queryEmpty}</p>
                ) : (
                  <ul className="memory-query-hit-list">
                    {memoryQueryMutation.data.documents[0]?.map((doc, i) => {
                      const id =
                        memoryQueryMutation.data?.ids[0]?.[i] ?? String(i);
                      const dist = memoryQueryMutation.data?.distances?.[0]?.[i];
                      const hitMeta =
                        memoryQueryMutation.data?.metadatas?.[0]?.[i];
                      const metaKeys =
                        hitMeta && typeof hitMeta === "object" && hitMeta !== null
                          ? Object.keys(hitMeta as Record<string, unknown>)
                          : [];
                      return (
                        <li key={id} className="memory-query-hit-item">
                          <pre className="memory-query-hit-doc">{doc}</pre>
                          {metaKeys.length > 0 ? (
                            <pre className="memory-query-hit-meta">
                              {t.inspector.memory.hitMetadataLabel}:{"\n"}
                              {JSON.stringify(
                                hitMeta as Record<string, unknown>,
                                null,
                                2,
                              )}
                            </pre>
                          ) : null}
                          {typeof dist === "number" && Number.isFinite(dist) ? (
                            <span className="memory-query-hit-dist">
                              {t.inspector.memory.distanceLabel}:{" "}
                              {dist.toFixed(4)}
                            </span>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {activeTask ? (
        <div className="inspector-block">
          <p className="summary-label">{t.inspector.currentTaskCard}</p>
          <strong>{getTaskLabel(activeTask, t.workbench)}</strong>
          <span>
            {t.inspector.statusPrefix}
            {activeTask.status}
          </span>
        </div>
      ) : null}

      {latestTaskForSession ? (
        <div className="inspector-block">
          <p className="summary-label">{t.inspector.latestTaskSession}</p>
          <strong>{getTaskLabel(latestTaskForSession, t.workbench)}</strong>
          <span>
            {formatTimestamp(latestTaskForSession.updated_at, localeTag)}
          </span>
        </div>
      ) : null}

      {recentTasks.length > 0 ? (
        <div className="inspector-block" id="ctx-tasks">
          <p className="summary-label">
            {activeSessionId
              ? t.inspector.sessionTasks
              : t.inspector.recentTasks}
          </p>
          <p className="inspector-section-lead">{t.inspector.taskIndexLead}</p>
          <div className="task-index-toolbar">
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
          <p className="task-index-summary">
            {t.inspector.taskVisibleCount(filteredTasks.length, recentTasks.length)}
          </p>
          <div className="task-summary-list">
            {filteredTasks.map((task) => {
              const isActive = task.id === activeTaskId;
              const failedHint = extractTaskFailureHint(task);
              const usage = resolveTaskUsageFromTask(task);
              const usageLine = usage
                ? [
                    usage.completion
                      ? `${t.inspector.usageCompletion}: ${usage.completion}`
                      : null,
                    usage.total
                      ? `${t.inspector.usageTotal}: ${usage.total}`
                      : null,
                    usage.cost
                      ? `${t.inspector.usageCost}: ${usage.cost}`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")
                : "";
              return (
                <button
                  key={task.id}
                  className={`task-summary-item${isActive ? " is-active" : ""}${isTaskFailedStatus(task.status) ? " task-summary-item--failed" : ""}`}
                  type="button"
                  onClick={() => onSelectTask(task)}
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
                  {usageLine ? (
                    <span className="task-summary-usage">{usageLine}</span>
                  ) : null}
                  {failedHint ? (
                    <span className="task-summary-failed-hint">
                      {t.inspector.taskFailureHint}: {failedHint}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
          {filteredTasks.length === 0 ? (
            <p className="panel-note panel-note--muted">{t.inspector.taskEmpty}</p>
          ) : null}
          {tasksCanLoadMore ? (
            <div className="inspector-task-load-more">
              <Button
                type="default"
                size="small"
                block
                loading={tasksFetchNextBusy}
                onClick={() => onLoadMoreTasks()}
              >
                {t.inspector.loadMoreTasks}
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}

      <p className="panel-note panel-note--muted">
        {t.inspector.backendUrl}
        <code>{apiBaseUrl}</code>
      </p>
    </section>
  );

  return (
    <aside
      ref={ref}
      className={`inspector-shell${collapsedRail ? " inspector-shell--collapsed" : ""}`}
      aria-label={t.inspector.ariaShell}
    >
      {showDesktopChrome ? (
        <div
          className="inspector-resizer"
          role="separator"
          aria-orientation="vertical"
          aria-hidden
          onMouseDown={onInspectorResizeStart}
        />
      ) : null}

      {collapsedRail ? (
        <div className="inspector-collapsed-inner">
          <button
            type="button"
            className="inspector-expand-strip"
            aria-label={t.inspector.expandInspectorAria}
            title={t.inspector.expandInspectorAria}
            onClick={onToggleInspectorCollapsed}
          >
            <PanelRightOpen size={20} strokeWidth={2} aria-hidden />
          </button>
        </div>
      ) : (
        <div className="inspector-main">
          <Tabs
            className="inspector-ant-tabs"
            activeKey={tab}
            onChange={(k) => setTab(k as InspectorTab)}
            aria-label={t.inspector.ariaTablist}
            tabBarExtraContent={
              desktopInspectorChrome ? (
                <Button
                  type="text"
                  size="small"
                  className="inspector-collapse-btn"
                  aria-label={t.inspector.collapseInspectorAria}
                  title={t.inspector.collapseInspectorAria}
                  icon={
                    <PanelRightClose size={18} strokeWidth={2} aria-hidden />
                  }
                  onClick={onToggleInspectorCollapsed}
                />
              ) : null
            }
            items={[
              {
                key: "trace",
                label: t.inspector.tabTrace,
                children: tracePanel,
              },
              {
                key: "context",
                label: t.inspector.tabContext,
                children: contextPanel,
              },
            ]}
          />
        </div>
      )}
    </aside>
  );
});
