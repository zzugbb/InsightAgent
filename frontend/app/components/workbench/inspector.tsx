"use client";

import { forwardRef, useMemo, useState } from "react";

import type { TraceStepPayload } from "../../../lib/stores/chat-stream-store";
import {
  useMessages,
  usePreferences,
} from "../../../lib/preferences-context";

import type { InspectorTab, TaskSummary } from "./types";
import { formatTimestamp, getStepTitle, getTaskLabel, shortenId } from "./utils";

const TRACE_PREVIEW = 6;

type InspectorProps = {
  tab: InspectorTab;
  setTab: (tab: InspectorTab) => void;
  isStreaming: boolean;
  sseTraceSteps: TraceStepPayload[];
  sseMessage: string;
  sseTaskId: string | null;
  phaseLabel: string;
  traceCursor: number;
  activeSessionId: string | null;
  activeTaskId: string | null;
  activeTask: TaskSummary | undefined;
  latestTaskForSession: TaskSummary | undefined;
  recentTasks: TaskSummary[];
  tasksMessage: string;
  onReplayTrace: () => void;
  onLoadDelta: () => void;
  onSelectTask: (task: TaskSummary) => void;
  apiBaseUrl: string;
};

export const Inspector = forwardRef<HTMLElement, InspectorProps>(function Inspector(
  {
    tab,
    setTab,
    isStreaming,
    sseTraceSteps,
    sseMessage,
    sseTaskId,
    phaseLabel,
    traceCursor,
    activeSessionId,
    activeTaskId,
    activeTask,
    latestTaskForSession,
    recentTasks,
    tasksMessage,
    onReplayTrace,
    onLoadDelta,
    onSelectTask,
    apiBaseUrl,
  },
  ref,
) {
  const t = useMessages();
  const { localeTag } = usePreferences();
  const hasTaskContext = Boolean(sseTaskId?.trim());
  const [expandAllTrace, setExpandAllTrace] = useState(false);

  const { visibleSteps, hiddenCount } = useMemo(() => {
    const steps = sseTraceSteps;
    if (expandAllTrace || steps.length <= TRACE_PREVIEW) {
      return { visibleSteps: steps, hiddenCount: 0 };
    }
    return {
      visibleSteps: steps.slice(-TRACE_PREVIEW),
      hiddenCount: steps.length - TRACE_PREVIEW,
    };
  }, [sseTraceSteps, expandAllTrace]);

  return (
    <aside
      ref={ref}
      className="inspector-shell"
      aria-label={t.inspector.ariaShell}
    >
      <div className="inspector-tab-row">
        <div
          className="inspector-tabs inspector-tabs--pair"
          role="tablist"
          aria-label={t.inspector.ariaTablist}
        >
          <button
            className={tab === "trace" ? "active" : ""}
            type="button"
            role="tab"
            id="inspector-tab-trace"
            aria-selected={tab === "trace"}
            aria-controls="inspector-panel-trace"
            onClick={() => setTab("trace")}
          >
            {t.inspector.tabTrace}
          </button>
          <button
            className={tab === "context" ? "active" : ""}
            type="button"
            role="tab"
            id="inspector-tab-context"
            aria-selected={tab === "context"}
            aria-controls="inspector-panel-context"
            onClick={() => setTab("context")}
          >
            {t.inspector.tabContext}
          </button>
        </div>
      </div>

      {tab === "trace" ? (
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
                ? t.inspector.stepsCount(sseTraceSteps.length)
                : t.inspector.stepsNone}
            </span>
          </div>

          {sseTraceSteps.length > TRACE_PREVIEW ? (
            <div className="trace-density-row">
              <button
                type="button"
                className="ghost-button trace-density-btn"
                onClick={() => setExpandAllTrace((v) => !v)}
              >
                {expandAllTrace
                  ? t.workbench.traceCollapse
                  : t.workbench.traceExpandAll}
              </button>
              {!expandAllTrace && hiddenCount > 0 ? (
                <span className="trace-density-note">
                  {t.workbench.traceHidden(hiddenCount)}
                </span>
              ) : null}
            </div>
          ) : null}

          <div className="panel-actions">
            <button
              className="ghost-button"
              disabled={isStreaming || !hasTaskContext}
              type="button"
              onClick={onReplayTrace}
            >
              {t.inspector.replayTrace}
            </button>
            <button
              className="ghost-button"
              disabled={isStreaming || !hasTaskContext}
              type="button"
              onClick={onLoadDelta}
            >
              {t.inspector.loadDelta}
            </button>
          </div>

          <p className="panel-note">{sseMessage}</p>

          {visibleSteps.length > 0 ? (
            <div className="trace-feed">
              {visibleSteps.map((step) => (
                <article key={step.id} className="trace-card trace-card--enter">
                  <div className="trace-top">
                    <strong>{getStepTitle(step)}</strong>
                    <span>
                      {typeof step.seq === "number"
                        ? `${t.inspector.seqLabel} ${step.seq}`
                        : shortenId(step.id)}
                    </span>
                  </div>
                  <p>{step.content || t.inspector.stepEmpty}</p>
                </article>
              ))}
            </div>
          ) : (
            <div className="panel-empty">{t.inspector.traceEmpty}</div>
          )}
        </section>
      ) : null}

      {tab === "context" ? (
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

          <div className="context-grid context-grid--stats">
            <span>{t.inspector.currentPhase}</span>
            <strong>{phaseLabel}</strong>
            <span>{t.inspector.currentTask}</span>
            <strong>{activeTaskId ? shortenId(activeTaskId) : "—"}</strong>
            <span>{t.inspector.traceCursor}</span>
            <strong>{traceCursor}</strong>
            <span>{t.inspector.session}</span>
            <strong>{activeSessionId ? shortenId(activeSessionId) : "—"}</strong>
          </div>

          <div className="summary-card">
            <p className="summary-label">{t.inspector.taskList}</p>
            <span className="summary-card-hint">{tasksMessage}</span>
          </div>

          {activeTask ? (
            <div className="summary-card">
              <p className="summary-label">{t.inspector.currentTaskCard}</p>
              <strong>{getTaskLabel(activeTask, t.workbench)}</strong>
              <span>
                {t.inspector.statusPrefix}
                {activeTask.status}
              </span>
            </div>
          ) : null}

          {latestTaskForSession ? (
            <div className="summary-card">
              <p className="summary-label">{t.inspector.latestTaskSession}</p>
              <strong>{getTaskLabel(latestTaskForSession, t.workbench)}</strong>
              <span>
                {formatTimestamp(latestTaskForSession.updated_at, localeTag)}
              </span>
            </div>
          ) : null}

          {recentTasks.length > 0 ? (
            <div className="summary-card">
              <p className="summary-label">{t.inspector.recentTasks}</p>
              <div className="task-summary-list">
                {recentTasks.map((task) => {
                  const isActive = task.id === activeTaskId;
                  return (
                    <button
                      key={task.id}
                      className={`task-summary-item${isActive ? " is-active" : ""}`}
                      type="button"
                      onClick={() => onSelectTask(task)}
                    >
                      <strong>{getTaskLabel(task, t.workbench)}</strong>
                      <span>
                        {task.status} ·{" "}
                        {formatTimestamp(task.updated_at, localeTag)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}

          <p className="panel-note panel-note--muted">
            {t.inspector.backendUrl}
            <code>{apiBaseUrl}</code>
          </p>
        </section>
      ) : null}
    </aside>
  );
});
