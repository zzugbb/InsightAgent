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

import type {
  InspectorTab,
  MemoryAddResponse,
  MemoryQueryResponse,
  SessionMemoryStatus,
  TaskSummary,
} from "./types";
import { TraceFlowView } from "./trace-flow-view";
import {
  formatTimestamp,
  formatTraceStepMetaSubtitle,
  getStepTitle,
  getTaskLabel,
  normalizeTraceStepKind,
  parseMemoryMetadataJson,
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
  activeSessionId: string | null;
  activeTaskId: string | null;
  activeTask: TaskSummary | undefined;
  latestTaskForSession: TaskSummary | undefined;
  recentTasks: TaskSummary[];
  onReplayTrace: () => void;
  onLoadDelta: () => void;
  onSelectTask: (task: TaskSummary) => void;
  apiBaseUrl: string;
  sessionMemoryStatus: SessionMemoryStatus | undefined;
  sessionMemoryLoading: boolean;
  sessionMemoryError: string | null;
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
    activeSessionId,
    activeTaskId,
    activeTask,
    latestTaskForSession,
    recentTasks,
    onReplayTrace,
    onLoadDelta,
    onSelectTask,
    apiBaseUrl,
    sessionMemoryStatus,
    sessionMemoryLoading,
    sessionMemoryError,
  },
  ref,
) {
  const t = useMessages();
  const { localeTag, theme } = usePreferences();
  const hasTaskContext = Boolean(sseTaskId?.trim());
  const [expandAllTrace, setExpandAllTrace] = useState(false);
  const [traceView, setTraceView] = useState<"list" | "flow">("list");
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [memoryAddDraft, setMemoryAddDraft] = useState("");
  const [memoryMetaDraft, setMemoryMetaDraft] = useState("");
  const [memoryQueryDraft, setMemoryQueryDraft] = useState("");

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
            ? t.inspector.stepsCount(sseTraceSteps.length)
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

      {traceView === "list" && sseTraceSteps.length > TRACE_PREVIEW ? (
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

      {traceView === "flow" && sseTraceSteps.length > 0 ? (
        <TraceFlowView steps={sseTraceSteps} colorMode={theme} />
      ) : traceView === "list" && visibleSteps.length > 0 ? (
        <div className="trace-feed">
          {visibleSteps.map((step) => {
            const traceKind = normalizeTraceStepKind(step);
            const metaLine = formatTraceStepMetaSubtitle(
              step,
              t.inspector.traceMeta,
            );
            return (
            <article
              key={step.id}
              className={`trace-card trace-card--enter trace-card--kind-${traceKind}`}
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

      <div className="summary-card memory-placeholder-card">
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
                    {task.status} · {formatTimestamp(task.updated_at, localeTag)}
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
