"use client";

import { App, Button, Input, Segmented, Spin } from "antd";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { ApiError, apiJson } from "../../../lib/api-client";
import { downloadAuthenticatedExport } from "../../../lib/export-download";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages, usePreferences } from "../../../lib/preferences-context";
import type { TraceStepPayload } from "../../../lib/types/trace";
import { TraceFlowView } from "../../components/workbench/trace-flow-view";
import type { TaskSummary } from "../../components/workbench/types";
import {
  API_BASE_URL,
  filterTraceSteps,
  formatTimestamp,
  formatTraceStepMetaSubtitle,
  getStepTitle,
  getTaskLabel,
  normalizeTraceStepKind,
  parseTaskTraceJson,
  resolveTraceStepDisplayContent,
  resolveTaskSnapshotSummary,
  resolveTaskUsageFromTask,
  shortenId,
} from "../../components/workbench/utils";

const TRACE_REFRESH_MS = 2200;

type TaskTraceResponse = {
  task_id: string;
  steps: TraceStepPayload[];
  status: string;
  status_normalized: string;
  status_label: string;
  status_rank: number;
};

function isRunningLike(status: string | null | undefined): boolean {
  const normalized = String(status ?? "")
    .trim()
    .toLowerCase();
  return normalized === "running" || normalized === "pending";
}

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

export default function TaskDetailPage() {
  const t = useMessages();
  const { localeTag, theme } = usePreferences();
  const { message } = App.useApp();
  const params = useParams<{ taskId: string }>();
  const [traceView, setTraceView] = useState<"list" | "flow">("list");
  const [traceDensity, setTraceDensity] = useState<"comfortable" | "compact">(
    "comfortable",
  );
  const [traceKindFilter, setTraceKindFilter] = useState<
    "all" | "thought" | "action" | "observation" | "tool" | "rag" | "other"
  >("all");
  const [traceSearchQuery, setTraceSearchQuery] = useState("");
  const [taskExporting, setTaskExporting] = useState<"json" | "markdown" | null>(
    null,
  );

  const taskId = decodeURIComponent(params.taskId ?? "").trim();

  const taskQuery = useQuery({
    queryKey: ["task-detail", taskId],
    enabled: taskId.length > 0,
    queryFn: () =>
      apiJson<TaskSummary>(`${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}`),
    refetchInterval: (query) =>
      isRunningLike(query.state.data?.status) ? TRACE_REFRESH_MS : false,
  });

  const traceQuery = useQuery({
    queryKey: ["task-trace-detail", taskId],
    enabled: taskId.length > 0 && taskQuery.isSuccess,
    queryFn: () =>
      apiJson<TaskTraceResponse>(
        `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/trace`,
      ),
    refetchInterval: () =>
      isRunningLike(taskQuery.data?.status) ? TRACE_REFRESH_MS : false,
  });

  const task = taskQuery.data;

  const traceSteps = useMemo(() => {
    if (traceQuery.data?.steps?.length) {
      return traceQuery.data.steps;
    }
    if (!task) {
      return [];
    }
    return parseTaskTraceJson(task.trace_json);
  }, [task, traceQuery.data?.steps]);

  const taskSnapshot = useMemo(
    () =>
      task
        ? resolveTaskSnapshotSummary({
            task,
            traceSteps,
          })
        : null,
    [task, traceSteps],
  );

  const taskUsage = useMemo(() => (task ? resolveTaskUsageFromTask(task) : null), [task]);

  const filteredTraceSteps = useMemo(() => {
    return filterTraceSteps(traceSteps, {
      kindFilter: traceKindFilter,
      searchQuery: traceSearchQuery,
    });
  }, [traceKindFilter, traceSearchQuery, traceSteps]);

  const exportTask = async (format: "json" | "markdown") => {
    if (!task?.id) {
      return;
    }
    setTaskExporting(format);
    const encodedTaskId = encodeURIComponent(task.id);
    const route = format === "json" ? "json" : "markdown";
    const fallbackFilename =
      format === "json"
        ? `insightagent-task-${task.id}.json`
        : `insightagent-task-${task.id}.md`;
    const requestUrl =
      `${API_BASE_URL}/api/tasks/${encodedTaskId}/export/${route}?download=1`;
    try {
      await downloadAuthenticatedExport(
        requestUrl,
        fallbackFilename,
      );
      message.success(
        format === "json"
          ? t.taskDetail.exportJsonDone
          : t.taskDetail.exportMarkdownDone,
      );
    } catch (error) {
      const u = toUserFacingError(error, t.errors);
      message.error(u.hint ? `${u.banner} ${u.hint}` : u.banner);
    } finally {
      setTaskExporting(null);
    }
  };

  const taskError = taskQuery.isError ? toUserFacingError(taskQuery.error, t.errors) : null;
  const isNotFound =
    taskQuery.error instanceof ApiError && taskQuery.error.status === 404;

  return (
    <main className="task-detail-page" data-testid="task-detail-page">
      <div className="task-detail-shell">
        <header className="task-detail-header">
          <Link className="task-detail-back-link" href="/">
            <ArrowLeft size={16} aria-hidden />
            <span>{t.taskDetail.backToWorkbench}</span>
          </Link>
          <div className="task-detail-headline">
            <p className="chat-kicker">{t.taskDetail.heading}</p>
            <h1>
              {task ? getTaskLabel(task, t.workbench) : shortenId(taskId || "unknown")}
            </h1>
            <p>{t.taskDetail.lead}</p>
          </div>
          <div className="task-detail-actions">
            <Button
              size="small"
              data-testid="task-detail-export-json"
              loading={taskExporting === "json"}
              disabled={!task}
              onClick={() => {
                void exportTask("json");
              }}
            >
              {t.taskDetail.exportJson}
            </Button>
            <Button
              size="small"
              data-testid="task-detail-export-markdown"
              loading={taskExporting === "markdown"}
              disabled={!task}
              onClick={() => {
                void exportTask("markdown");
              }}
            >
              {t.taskDetail.exportMarkdown}
            </Button>
          </div>
        </header>

        {!taskId ? (
          <div className="panel-empty">{t.taskDetail.notFound}</div>
        ) : taskQuery.isLoading ? (
          <div className="task-detail-loading">
            <Spin size="small" />
            <span>{t.taskDetail.loading}</span>
          </div>
        ) : taskError ? (
          <div className="panel-empty">
            {isNotFound ? t.taskDetail.notFound : `${t.taskDetail.loadFailed} ${taskError.banner}`}
          </div>
        ) : task ? (
          <>
            <section className="task-detail-kpi-grid">
              <div className="inspector-kpi-item">
                <span>{t.taskDetail.taskIdLabel}</span>
                <strong title={task.id}>{shortenId(task.id)}</strong>
              </div>
              <div className="inspector-kpi-item">
                <span>{t.taskDetail.sessionIdLabel}</span>
                <strong title={task.session_id}>{shortenId(task.session_id)}</strong>
              </div>
              <div className="inspector-kpi-item">
                <span>{t.taskDetail.statusLabel}</span>
                <strong>
                  <span
                    className={`task-status-badge task-status-badge--${resolveTaskStatusTone(task.status)}`}
                  >
                    {task.status}
                  </span>
                </strong>
              </div>
              <div className="inspector-kpi-item">
                <span>{t.taskDetail.createdAtLabel}</span>
                <strong>{formatTimestamp(task.created_at, localeTag)}</strong>
              </div>
              <div className="inspector-kpi-item">
                <span>{t.taskDetail.updatedAtLabel}</span>
                <strong>{formatTimestamp(task.updated_at, localeTag)}</strong>
              </div>
              <div className="inspector-kpi-item">
                <span>{t.taskDetail.stepCountLabel}</span>
                <strong>{taskSnapshot?.stepCount ?? traceSteps.length}</strong>
              </div>
              <div className="inspector-kpi-item">
                <span>{t.taskDetail.ragHitsLabel}</span>
                <strong>{taskSnapshot?.ragHitCount ?? 0}</strong>
              </div>
              <div className="inspector-kpi-item">
                <span>{t.taskDetail.usageLead}</span>
                <strong>
                  {taskUsage?.total ?? "—"}
                  {taskUsage?.cost ? ` · ${taskUsage.cost}` : ""}
                </strong>
              </div>
            </section>

            {taskSnapshot && taskSnapshot.ragKnowledgeBaseIds.length > 0 ? (
              <p className="panel-note panel-note--muted task-detail-rag-kb-note">
                {t.taskDetail.ragKnowledgeBasesLabel(
                  taskSnapshot.ragKnowledgeBaseIds.join(", "),
                )}
              </p>
            ) : null}

            {taskSnapshot?.governance ? (
              <section
                className="inspector-block task-detail-governance-block"
                data-testid="task-detail-governance-summary"
              >
                <div className="panel-head">
                  <div>
                    <p className="chat-kicker">{t.taskDetail.governanceTitle}</p>
                    <h3>{t.taskDetail.governanceTitle}</h3>
                  </div>
                </div>
                <div className="task-detail-kpi-grid">
                  <div className="inspector-kpi-item">
                    <span>{t.taskDetail.governanceProfileLabel}</span>
                    <strong>
                      {taskSnapshot.governance.profile ?? t.taskDetail.governanceNone}
                    </strong>
                  </div>
                  <div className="inspector-kpi-item">
                    <span>{t.taskDetail.governanceSourceLabel}</span>
                    <strong>
                      {taskSnapshot.governance.providerSource ??
                        t.taskDetail.governanceNone}
                    </strong>
                  </div>
                  <div className="inspector-kpi-item">
                    <span>{t.taskDetail.governanceAllowedToolsLabel}</span>
                    <strong>
                      {(taskSnapshot.governance.allowedToolLabels.length > 0
                        ? taskSnapshot.governance.allowedToolLabels
                        : taskSnapshot.governance.allowedToolNames
                      ).join(", ") || t.taskDetail.governanceNone}
                    </strong>
                  </div>
                </div>
              </section>
            ) : null}

            {taskSnapshot ? (
              <section
                className="inspector-block task-detail-semantic-block"
                data-testid="task-detail-semantic-summary"
              >
                <div className="panel-head">
                  <div>
                    <p className="chat-kicker">{t.taskDetail.semanticTitle}</p>
                    <h3>{t.taskDetail.semanticTitle}</h3>
                  </div>
                </div>
                <div className="task-detail-kpi-grid">
                  <div
                    className="inspector-kpi-item"
                    data-testid="task-detail-semantic-planner"
                  >
                    <span>{t.taskDetail.semanticPlannerLabel}</span>
                    <strong>{taskSnapshot.semanticStats.planner}</strong>
                  </div>
                  <div
                    className="inspector-kpi-item"
                    data-testid="task-detail-semantic-retrieval"
                  >
                    <span>{t.taskDetail.semanticRetrievalLabel}</span>
                    <strong>{taskSnapshot.semanticStats.retrieval}</strong>
                  </div>
                  <div
                    className="inspector-kpi-item"
                    data-testid="task-detail-semantic-calculator"
                  >
                    <span>{t.taskDetail.semanticCalculatorLabel}</span>
                    <strong>{taskSnapshot.semanticStats.calculator}</strong>
                  </div>
                </div>
              </section>
            ) : null}

            <section className="task-detail-main-grid">
              <article className="inspector-block task-detail-content-block">
                <p className="summary-label">{t.taskDetail.taskPromptTitle}</p>
                <pre className="task-snapshot-body task-detail-body">
                  {task.prompt.trim() || "—"}
                </pre>

                <p className="summary-label">{t.taskDetail.finalAnswerTitle}</p>
                <pre className="task-snapshot-body task-detail-body">
                  {taskSnapshot?.finalAnswer ?? t.taskDetail.finalAnswerEmpty}
                </pre>

                {taskSnapshot?.lastObservation &&
                taskSnapshot.lastObservation !== taskSnapshot.finalAnswer ? (
                  <>
                    <p className="summary-label">{t.taskDetail.lastObservationTitle}</p>
                    <pre className="task-snapshot-body task-detail-body">
                      {taskSnapshot.lastObservation}
                    </pre>
                  </>
                ) : null}
              </article>

              <article className="inspector-block task-detail-trace-block">
                <div className="panel-head">
                  <div>
                    <p className="chat-kicker">{t.taskDetail.traceTitle}</p>
                    <h3>{t.taskDetail.traceTitle}</h3>
                  </div>
                  <span>
                    {traceSteps.length > 0
                      ? t.taskDetail.traceVisibleCount(
                          filteredTraceSteps.length,
                          traceSteps.length,
                        )
                      : "—"}
                  </span>
                </div>

                <div className="trace-view-toolbar">
                  <Segmented
                    value={traceView}
                    onChange={(v) => setTraceView(v as "list" | "flow")}
                    options={[
                      { label: t.taskDetail.traceViewList, value: "list" },
                      { label: t.taskDetail.traceViewFlow, value: "flow" },
                    ]}
                  />
                </div>

                <div className="trace-filter-toolbar">
                  <Segmented
                    size="small"
                    value={traceKindFilter}
                    onChange={(v) =>
                      setTraceKindFilter(
                        v as
                          | "all"
                          | "thought"
                          | "action"
                          | "observation"
                          | "tool"
                          | "rag"
                          | "other",
                      )
                    }
                    options={[
                      { label: t.taskDetail.traceFilterAll, value: "all" },
                      { label: t.taskDetail.traceFilterThought, value: "thought" },
                      { label: t.taskDetail.traceFilterAction, value: "action" },
                      {
                        label: t.taskDetail.traceFilterObservation,
                        value: "observation",
                      },
                      { label: t.taskDetail.traceFilterTool, value: "tool" },
                      { label: t.taskDetail.traceFilterRag, value: "rag" },
                      { label: t.taskDetail.traceFilterOther, value: "other" },
                    ]}
                  />
                  <Input
                    size="small"
                    allowClear
                    value={traceSearchQuery}
                    onChange={(e) => setTraceSearchQuery(e.target.value)}
                    placeholder={t.taskDetail.traceSearchPlaceholder}
                  />
                  <Segmented
                    size="small"
                    value={traceDensity}
                    onChange={(v) => setTraceDensity(v as "comfortable" | "compact")}
                    options={[
                      {
                        label: t.taskDetail.traceDensityComfortable,
                        value: "comfortable",
                      },
                      { label: t.taskDetail.traceDensityCompact, value: "compact" },
                    ]}
                  />
                </div>

                {traceQuery.isLoading ? (
                  <div className="task-detail-loading task-detail-loading--inline">
                    <Spin size="small" />
                    <span>{t.taskDetail.loading}</span>
                  </div>
                ) : traceView === "flow" && filteredTraceSteps.length > 0 ? (
                  <TraceFlowView steps={filteredTraceSteps} colorMode={theme} />
                ) : traceView === "list" && filteredTraceSteps.length > 0 ? (
                  <div
                    className={`trace-feed trace-feed--${traceDensity}`}
                    data-testid="task-detail-trace-feed"
                  >
                    {filteredTraceSteps.map((step) => {
                      const traceKind = normalizeTraceStepKind(step);
                      const metaLine = formatTraceStepMetaSubtitle(
                        step,
                        t.inspector.traceMeta,
                      );
                      return (
                        <article
                          key={step.id}
                          className={`trace-card trace-card--kind-${traceKind}${
                            traceDensity === "compact" ? " trace-card--compact" : ""
                          }`}
                          data-testid="task-detail-trace-card"
                        >
                          <div className="trace-top">
                            <strong>{getStepTitle(step)}</strong>
                            <span>{shortenId(step.id)}</span>
                          </div>
                          <p
                            className="trace-card-meta"
                            data-testid="task-detail-trace-card-meta"
                          >
                            {metaLine ?? t.taskDetail.traceMetaNone}
                          </p>
                          <p>{resolveTraceStepDisplayContent(step) || t.inspector.stepEmpty}</p>
                        </article>
                      );
                    })}
                  </div>
                ) : filteredTraceSteps.length === 0 && traceSteps.length > 0 ? (
                  <div className="panel-empty">{t.taskDetail.traceNoMatch}</div>
                ) : (
                  <div className="panel-empty">{t.taskDetail.traceEmpty}</div>
                )}
              </article>
            </section>
          </>
        ) : (
          <div className="panel-empty">{t.taskDetail.notFound}</div>
        )}
      </div>
    </main>
  );
}
