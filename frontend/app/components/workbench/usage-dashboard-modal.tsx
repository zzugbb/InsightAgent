"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button, Modal, Segmented, Space, Table, Tag, Tooltip, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { RefreshCw } from "lucide-react";

import { apiJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages, usePreferences } from "../../../lib/preferences-context";

import type {
  UsageDashboardResponse,
  UsageDashboardSessionRow,
  UsageDashboardTaskRow,
} from "./types";
import { shortenId, API_BASE_URL } from "./utils";

type UsageDashboardModalProps = {
  open: boolean;
  onClose: () => void;
  activeSessionId?: string | null;
};

type UsageScope = "global" | "session";
type UsageMetric = "tokens" | "cost";
type UsageView = "sessions" | "tasks";
type UsageSourceFilter = "all" | "provider" | "estimated" | "mixed" | "legacy";

function buildDashboardUrl(args: {
  scope: UsageScope;
  sessionId: string | null;
  sourceFilter: UsageSourceFilter;
}): string {
  const params = new URLSearchParams();
  params.set("window_days", "14");
  params.set("top_sessions", "10");
  params.set("top_tasks", "14");
  if (args.scope === "session" && args.sessionId) {
    params.set("session_id", args.sessionId);
  }
  if (args.sourceFilter !== "all") {
    params.set("source_kind", args.sourceFilter);
  }
  return `${API_BASE_URL}/api/tasks/usage/dashboard?${params.toString()}`;
}

function formatDateDay(value: string, localeTag: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(localeTag, {
    month: "2-digit",
    day: "2-digit",
  }).format(parsed);
}

function formatDateTime(value: string, localeTag: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(localeTag, {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

export function UsageDashboardModal({
  open,
  onClose,
  activeSessionId = null,
}: UsageDashboardModalProps) {
  const t = useMessages();
  const { localeTag } = usePreferences();
  const [scope, setScope] = useState<UsageScope>(
    activeSessionId ? "session" : "global",
  );
  const [metric, setMetric] = useState<UsageMetric>("tokens");
  const [view, setView] = useState<UsageView>("sessions");
  const [sourceFilter, setSourceFilter] = useState<UsageSourceFilter>("all");

  useEffect(() => {
    if (!open) {
      return;
    }
    setScope(activeSessionId ? "session" : "global");
    setMetric("tokens");
    setView("sessions");
    setSourceFilter("all");
  }, [open, activeSessionId]);

  const resolvedScope: UsageScope =
    scope === "session" && activeSessionId ? "session" : "global";

  const usageQuery = useQuery({
    queryKey: ["usage-dashboard", open, resolvedScope, activeSessionId, sourceFilter],
    enabled: open,
    staleTime: 8_000,
    queryFn: () =>
      apiJson<UsageDashboardResponse>(
        buildDashboardUrl({
          scope: resolvedScope,
          sessionId: activeSessionId,
          sourceFilter,
        }),
      ),
  });

  const errText = useMemo(() => {
    if (!usageQuery.isError || !usageQuery.error) {
      return null;
    }
    return toUserFacingError(usageQuery.error, t.errors).banner;
  }, [usageQuery.error, usageQuery.isError, t.errors]);

  const tokenFmt = useMemo(
    () =>
      new Intl.NumberFormat(localeTag, {
        maximumFractionDigits: 0,
      }),
    [localeTag],
  );

  const formatCost = (value: number | null | undefined): string => {
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return "—";
    }
    return `$${value.toFixed(6)}`;
  };

  const trendRows = usageQuery.data?.trend ?? [];
  const sourceTrendRows = trendRows.filter((row) => row.tasks_with_usage > 0);
  const trendMax = trendRows.reduce((acc, row) => {
    const current = metric === "tokens" ? row.total_tokens : row.cost_estimate;
    return current > acc ? current : acc;
  }, 0);

  const sessionColumns: ColumnsType<UsageDashboardSessionRow> = [
    {
      title: t.sidebar.usage.tableSession,
      dataIndex: "session_id",
      render: (_value: string, row) => {
        const label = row.session_title?.trim() || shortenId(row.session_id);
        return (
          <div className="usage-session-cell">
            <strong title={label}>{label}</strong>
            <span>{shortenId(row.session_id)}</span>
          </div>
        );
      },
    },
    {
      title: t.sidebar.usage.tableTasksWithUsage,
      dataIndex: "tasks_with_usage",
      width: 110,
      render: (value: number) => tokenFmt.format(Math.max(0, Math.trunc(value))),
    },
    {
      title: t.sidebar.usage.tableTotalTokens,
      dataIndex: "total_tokens",
      width: 132,
      render: (value: number) => tokenFmt.format(Math.max(0, Math.trunc(value))),
    },
    {
      title: t.sidebar.usage.tableCost,
      dataIndex: "cost_estimate",
      width: 120,
      render: (value: number) => formatCost(value),
    },
    {
      title: t.sidebar.usage.tableLastTaskAt,
      dataIndex: "last_task_at",
      width: 124,
      render: (value: string | null) =>
        value ? formatDateTime(value, localeTag) : "—",
    },
  ];

  const taskColumns: ColumnsType<UsageDashboardTaskRow> = [
    {
      title: t.sidebar.usage.tablePrompt,
      dataIndex: "prompt_excerpt",
      render: (_value: string, row) => {
        const prompt = row.prompt_excerpt?.trim() || t.sidebar.usage.promptEmpty;
        return (
          <div className="usage-task-prompt-cell">
            <strong title={prompt}>{prompt}</strong>
            <span>
              {row.session_title?.trim() || shortenId(row.session_id)} · {shortenId(row.task_id)}
            </span>
          </div>
        );
      },
    },
    {
      title: t.sidebar.usage.tableTotalTokens,
      dataIndex: "total_tokens",
      width: 136,
      render: (value: number) => tokenFmt.format(Math.max(0, Math.trunc(value))),
    },
    {
      title: t.sidebar.usage.tableCost,
      dataIndex: "cost_estimate",
      width: 120,
      render: (value: number) => formatCost(value),
    },
    {
      title: t.sidebar.usage.tableUpdatedAt,
      dataIndex: "updated_at",
      width: 124,
      render: (value: string) => formatDateTime(value, localeTag),
    },
  ];

  const summary = usageQuery.data?.summary;
  const sourceProviderCount = Math.max(
    0,
    Math.trunc(summary?.source_tasks_provider ?? 0),
  );
  const sourceEstimatedCount = Math.max(
    0,
    Math.trunc(summary?.source_tasks_estimated ?? 0),
  );
  const sourceMixedCount = Math.max(
    0,
    Math.trunc(summary?.source_tasks_mixed ?? 0),
  );
  const sourceLegacyCount = Math.max(
    0,
    Math.trunc(summary?.source_tasks_legacy ?? 0),
  );
  const sourceLabeledCount = sourceProviderCount + sourceEstimatedCount + sourceMixedCount;

  return (
    <Modal
      title={<span id="usage-dashboard-title">{t.sidebar.usage.title}</span>}
      open={open}
      onCancel={onClose}
      footer={null}
      width={860}
      destroyOnHidden
      className="usage-dashboard-ant-modal"
    >
      <Typography.Paragraph className="usage-dashboard-lead" type="secondary">
        {t.sidebar.usage.lead}
      </Typography.Paragraph>

      <div className="usage-dashboard-topline">
        <Space size={10} wrap>
          <Tag className="usage-dashboard-tag">
            {resolvedScope === "session"
              ? t.sidebar.usage.scopeSession
              : t.sidebar.usage.scopeGlobal}
          </Tag>
          <span className="usage-dashboard-window">
            {t.sidebar.usage.windowLabel(usageQuery.data?.window_days ?? 14)}
          </span>
        </Space>
        <Space size={8}>
          <Segmented<UsageScope>
            size="small"
            value={scope}
            onChange={(value) => setScope(value)}
            options={[
              { label: t.sidebar.usage.scopeGlobal, value: "global" },
              {
                label: t.sidebar.usage.scopeSession,
                value: "session",
                disabled: !activeSessionId,
              },
            ]}
          />
          <Tooltip title={t.sidebar.usage.refresh}>
            <Button
              size="small"
              type="text"
              className="usage-dashboard-refresh-btn"
              onClick={() => {
                void usageQuery.refetch();
              }}
              loading={usageQuery.isFetching}
              icon={<RefreshCw size={14} aria-hidden />}
              aria-label={t.sidebar.usage.refreshAria}
            />
          </Tooltip>
        </Space>
      </div>
      <div className="usage-source-filter-row">
        <Segmented<UsageSourceFilter>
          size="small"
          value={sourceFilter}
          onChange={(value) => setSourceFilter(value)}
          options={[
            { label: t.sidebar.usage.sourceFilterAll, value: "all" },
            { label: t.sidebar.usage.sourceProvider, value: "provider" },
            { label: t.sidebar.usage.sourceEstimated, value: "estimated" },
            { label: t.sidebar.usage.sourceMixed, value: "mixed" },
            { label: t.sidebar.usage.sourceLegacy, value: "legacy" },
          ]}
        />
      </div>

      {usageQuery.isLoading ? (
        <p className="usage-dashboard-note">{t.sidebar.usage.loading}</p>
      ) : null}
      {errText ? <p className="usage-dashboard-note">{t.sidebar.usage.loadFailed(errText)}</p> : null}

      {summary ? (
        <div className="usage-summary-strip">
          <div className="usage-summary-item">
            <span>{t.sidebar.usage.summaryTasksTotal}</span>
            <strong>{tokenFmt.format(summary.tasks_total)}</strong>
          </div>
          <div className="usage-summary-item">
            <span>{t.sidebar.usage.summaryTasksWithUsage}</span>
            <strong>{tokenFmt.format(summary.tasks_with_usage)}</strong>
          </div>
          <div className="usage-summary-item">
            <span>{t.sidebar.usage.summaryTotalTokens}</span>
            <strong>{tokenFmt.format(summary.total_tokens)}</strong>
          </div>
          <div className="usage-summary-item">
            <span>{t.sidebar.usage.summaryTotalCost}</span>
            <strong>{formatCost(summary.cost_estimate)}</strong>
          </div>
          <div className="usage-summary-item">
            <span>{t.sidebar.usage.summaryAvgTokens}</span>
            <strong>
              {summary.avg_total_tokens === null
                ? "—"
                : tokenFmt.format(Math.trunc(summary.avg_total_tokens))}
            </strong>
          </div>
          <div className="usage-summary-item">
            <span>{t.sidebar.usage.summaryAvgCost}</span>
            <strong>{formatCost(summary.avg_cost_estimate)}</strong>
          </div>
        </div>
      ) : null}

      {summary ? (
        <p className="usage-dashboard-coverage">
          {t.sidebar.usage.coverage(summary.tasks_with_usage, summary.tasks_total)}
        </p>
      ) : null}

      {summary && summary.tasks_with_usage > 0 ? (
        <>
          <div className="usage-source-strip">
            <span className="usage-source-title">{t.sidebar.usage.sourceTitle}</span>
            <Tag>
              {t.sidebar.usage.sourceProvider}:{" "}
              {tokenFmt.format(sourceProviderCount)}
            </Tag>
            <Tag>
              {t.sidebar.usage.sourceEstimated}:{" "}
              {tokenFmt.format(sourceEstimatedCount)}
            </Tag>
            <Tag>
              {t.sidebar.usage.sourceMixed}:{" "}
              {tokenFmt.format(sourceMixedCount)}
            </Tag>
            <Tag>
              {t.sidebar.usage.sourceLegacy}:{" "}
              {tokenFmt.format(sourceLegacyCount)}
            </Tag>
          </div>
          <p className="usage-dashboard-note">
            {t.sidebar.usage.sourceCoverage(sourceLabeledCount, summary.tasks_with_usage)}
          </p>
          {sourceLegacyCount > 0 ? (
            <p className="usage-dashboard-note">
              {t.sidebar.usage.sourceLegacyHint(sourceLegacyCount)}
            </p>
          ) : null}
        </>
      ) : null}

      <div className="usage-trend-block">
        <div className="usage-trend-head">
          <p className="usage-trend-title">{t.sidebar.usage.trendTitle}</p>
          <Segmented<UsageMetric>
            size="small"
            value={metric}
            onChange={(value) => setMetric(value)}
            options={[
              { label: t.sidebar.usage.metricTokens, value: "tokens" },
              { label: t.sidebar.usage.metricCost, value: "cost" },
            ]}
          />
        </div>
        <div className="usage-trend-list">
          {trendRows.length === 0 ? (
            <p className="usage-dashboard-note">{t.sidebar.usage.trendEmpty}</p>
          ) : (
            trendRows.map((row) => {
              const value = metric === "tokens" ? row.total_tokens : row.cost_estimate;
              const widthPct = trendMax > 0 ? Math.max((value / trendMax) * 100, 2) : 0;
              return (
                <div key={row.day} className="usage-trend-row">
                  <span className="usage-trend-day">{formatDateDay(row.day, localeTag)}</span>
                  <div className="usage-trend-bar-wrap" aria-hidden>
                    <div
                      className="usage-trend-bar"
                      style={{ width: `${widthPct}%` }}
                    />
                  </div>
                  <span className="usage-trend-value">
                    {metric === "tokens"
                      ? tokenFmt.format(Math.max(0, Math.trunc(value)))
                      : formatCost(value)}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
      <div className="usage-source-trend-block">
        <p className="usage-trend-title">{t.sidebar.usage.sourceTrendTitle}</p>
        {sourceTrendRows.length === 0 ? (
          <p className="usage-dashboard-note">{t.sidebar.usage.trendEmpty}</p>
        ) : (
          <div className="usage-source-trend-list">
            {sourceTrendRows.map((row) => (
              <div key={`source-${row.day}`} className="usage-source-trend-row">
                <span className="usage-trend-day">{formatDateDay(row.day, localeTag)}</span>
                <div className="usage-source-trend-tags">
                  <Tag>
                    {t.sidebar.usage.sourceProvider}:{" "}
                    {tokenFmt.format(Math.max(0, Math.trunc(row.source_tasks_provider)))}
                  </Tag>
                  <Tag>
                    {t.sidebar.usage.sourceEstimated}:{" "}
                    {tokenFmt.format(Math.max(0, Math.trunc(row.source_tasks_estimated)))}
                  </Tag>
                  <Tag>
                    {t.sidebar.usage.sourceMixed}:{" "}
                    {tokenFmt.format(Math.max(0, Math.trunc(row.source_tasks_mixed)))}
                  </Tag>
                  <Tag>
                    {t.sidebar.usage.sourceLegacy}:{" "}
                    {tokenFmt.format(Math.max(0, Math.trunc(row.source_tasks_legacy)))}
                  </Tag>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="usage-bottom-head">
        <p className="usage-trend-title">
          {view === "sessions" ? t.sidebar.usage.sessionsTitle : t.sidebar.usage.tasksTitle}
        </p>
        <Segmented<UsageView>
          size="small"
          value={view}
          onChange={(value) => setView(value)}
          options={[
            { label: t.sidebar.usage.sessionsTitle, value: "sessions" },
            { label: t.sidebar.usage.tasksTitle, value: "tasks" },
          ]}
        />
      </div>

      <div className="usage-dashboard-table-wrap">
        {view === "sessions" ? (
          <Table<UsageDashboardSessionRow>
            size="small"
            rowKey={(row) => row.session_id}
            columns={sessionColumns}
            dataSource={usageQuery.data?.by_session ?? []}
            loading={usageQuery.isLoading}
            pagination={false}
            locale={{ emptyText: t.sidebar.usage.tableNoData }}
            scroll={{ x: 760 }}
          />
        ) : (
          <Table<UsageDashboardTaskRow>
            size="small"
            rowKey={(row) => row.task_id}
            columns={taskColumns}
            dataSource={usageQuery.data?.top_tasks ?? []}
            loading={usageQuery.isLoading}
            pagination={false}
            locale={{ emptyText: t.sidebar.usage.tableNoData }}
            scroll={{ x: 760 }}
          />
        )}
      </div>

      {!activeSessionId && scope === "session" ? (
        <p className="usage-dashboard-note">{t.sidebar.usage.scopeSessionFallback}</p>
      ) : null}

      {!usageQuery.isLoading && usageQuery.data?.summary.tasks_with_usage === 0 ? (
        <p className="usage-dashboard-note">{t.sidebar.usage.tableNoData}</p>
      ) : null}
    </Modal>
  );
}
