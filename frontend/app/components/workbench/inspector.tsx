"use client";

import { Button, Input, Segmented, Space, Tabs } from "antd";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import {
  forwardRef,
  useEffect,
  useMemo,
  useState,
  type MouseEvent,
} from "react";
import type { TraceStepPayload } from "../../../lib/types/trace";
import {
  useMessages,
  usePreferences,
} from "../../../lib/preferences-context";

import type {
  InspectorTab,
  TaskSummary,
} from "./types";
import { TraceFlowView } from "./trace-flow-view";
import {
  formatTimestamp,
  formatTraceStepMetaSubtitle,
  getStepTitle,
  getTaskLabel,
  normalizeTraceStepKind,
  shortenId,
} from "./utils";

const TRACE_PREVIEW = 6;

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
  activeSessionId: string | null;
  activeTaskId: string | null;
  activeTask: TaskSummary | undefined;
  latestTaskForSession: TaskSummary | undefined;
  onReplayTrace: () => void;
  onLoadDelta: () => void;
  onOpenTaskCenter: () => void;
  onCancelTask: (task: TaskSummary) => void;
  cancellingTaskId: string | null;
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
    activeSessionId,
    activeTaskId,
    activeTask,
    latestTaskForSession,
    onReplayTrace,
    onLoadDelta,
    onOpenTaskCenter,
    onCancelTask,
    cancellingTaskId,
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
  const [retryCountdownSec, setRetryCountdownSec] = useState<number | null>(null);

  const scrollToContextSection = (id: string) => {
    const el = document.getElementById(id);
    if (!el) {
      return;
    }
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

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

  const isTaskCancelable = (status: string): boolean => {
    const normalized = status.trim().toLowerCase();
    return normalized === "pending" || normalized === "running";
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
          <Button size="small" onClick={onOpenTaskCenter}>
            {t.inspector.openTaskCenter}
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
          <strong data-testid="inspector-trace-sync-status">
            {traceDeltaSyncStatusLabel}
          </strong>
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
          <strong data-testid="inspector-trace-sync-retries">
            {traceDeltaRetryCount}
          </strong>
          <span>{t.inspector.traceSyncLastOk}</span>
          <strong data-testid="inspector-trace-sync-last-ok">
            {traceDeltaLastOkLabel}
          </strong>
          <span>{t.inspector.traceSyncNextRetry}</span>
          <strong data-testid="inspector-trace-sync-next-retry">
            {traceDeltaNextRetryLabel}
          </strong>
        </div>
        {showTraceDeltaWarning ? (
          <p className="panel-note panel-note--muted" data-testid="inspector-trace-sync-warning">
            {t.inspector.traceSyncWarning(traceDeltaRetryCount)}
          </p>
        ) : null}
        {traceDeltaSyncStatus === "retrying" && traceDeltaLastError ? (
          <p className="panel-note panel-note--muted" data-testid="inspector-trace-sync-last-error">
            {t.inspector.traceSyncLastError(traceDeltaLastError)}
          </p>
        ) : null}
        {traceDeltaSyncStatus === "retrying" && retryCountdownSec !== null ? (
          <p className="panel-note panel-note--muted" data-testid="inspector-trace-sync-retry-eta">
            {t.inspector.traceSyncRetryEta(retryCountdownSec)}
          </p>
        ) : null}
        {traceDeltaRecoveredLabel ? (
          <p className="panel-note panel-note--muted" data-testid="inspector-trace-sync-recovered">
            {t.inspector.traceSyncRecovered(traceDeltaRecoveredLabel)}
          </p>
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
          <div className="task-export-actions">
            <Button size="small" type="default" onClick={onOpenTaskCenter}>
              {t.inspector.openTaskCenter}
            </Button>
            <Button
              size="small"
              data-testid="inspector-task-open-detail"
              href={`/tasks/${encodeURIComponent(activeTask.id)}`}
            >
              {t.inspector.taskOpenDetail}
            </Button>
            {isTaskCancelable(activeTask.status) ? (
                <Button
                  size="small"
                  danger
                  loading={cancellingTaskId === activeTask.id}
                  data-testid="inspector-task-cancel"
                  onClick={() => onCancelTask(activeTask)}
                >
                  {t.inspector.taskCancel}
                </Button>
            ) : null}
          </div>
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
                label: (
                  <span data-testid="inspector-tab-trace">
                    {t.inspector.tabTrace}
                  </span>
                ),
                children: tracePanel,
              },
              {
                key: "context",
                label: (
                  <span data-testid="inspector-tab-context">
                    {t.inspector.tabContext}
                  </span>
                ),
                children: contextPanel,
              },
            ]}
          />
        </div>
      )}
    </aside>
  );
});
