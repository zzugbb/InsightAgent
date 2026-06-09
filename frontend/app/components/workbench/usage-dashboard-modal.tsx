"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button, Modal, Segmented, Select, Space, Table, Tag, Tooltip, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { RefreshCw } from "lucide-react";

import { apiJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages, usePreferences } from "../../../lib/preferences-context";

import type {
  SettingsSummary,
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
const GOVERNANCE_FILTER_ALL = "__all__";

function formatUsageSourceLabel(
  value: UsageSourceFilter,
  t: ReturnType<typeof useMessages>,
): string {
  if (value === "provider") {
    return t.sidebar.usage.sourceProvider;
  }
  if (value === "estimated") {
    return t.sidebar.usage.sourceEstimated;
  }
  if (value === "mixed") {
    return t.sidebar.usage.sourceMixed;
  }
  if (value === "legacy") {
    return t.sidebar.usage.sourceLegacy;
  }
  return t.sidebar.usage.sourceFilterAll;
}

function buildDashboardUrl(args: {
  scope: UsageScope;
  sessionId: string | null;
  sourceFilter: UsageSourceFilter;
  toolRegistryProfileFilter: string;
  toolRegistryProviderSourceFilter: string;
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
  if (args.toolRegistryProfileFilter !== GOVERNANCE_FILTER_ALL) {
    params.set("tool_registry_profile", args.toolRegistryProfileFilter);
  }
  if (args.toolRegistryProviderSourceFilter !== GOVERNANCE_FILTER_ALL) {
    params.set(
      "tool_registry_provider_source",
      args.toolRegistryProviderSourceFilter,
    );
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
  const [toolRegistryProfileFilter, setToolRegistryProfileFilter] =
    useState<string>(GOVERNANCE_FILTER_ALL);
  const [toolRegistryProviderSourceFilter, setToolRegistryProviderSourceFilter] =
    useState<string>(GOVERNANCE_FILTER_ALL);

  useEffect(() => {
    if (!open) {
      return;
    }
    setScope(activeSessionId ? "session" : "global");
    setMetric("tokens");
    setView("sessions");
    setSourceFilter("all");
    setToolRegistryProfileFilter(GOVERNANCE_FILTER_ALL);
    setToolRegistryProviderSourceFilter(GOVERNANCE_FILTER_ALL);
  }, [open, activeSessionId]);

  const resolvedScope: UsageScope =
    scope === "session" && activeSessionId ? "session" : "global";

  const settingsQuery = useQuery({
    queryKey: ["usage-dashboard-settings", open],
    enabled: open,
    staleTime: 30_000,
    queryFn: () => apiJson<SettingsSummary>(`${API_BASE_URL}/api/settings`),
  });

  const usageQuery = useQuery({
    queryKey: [
      "usage-dashboard",
      open,
      resolvedScope,
      activeSessionId,
      sourceFilter,
      toolRegistryProfileFilter,
      toolRegistryProviderSourceFilter,
    ],
    enabled: open,
    staleTime: 8_000,
    queryFn: () =>
      apiJson<UsageDashboardResponse>(
        buildDashboardUrl({
          scope: resolvedScope,
          sessionId: activeSessionId,
          sourceFilter,
          toolRegistryProfileFilter,
          toolRegistryProviderSourceFilter,
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

  const profileFilterOptions = useMemo(
    () => [
      {
        label: t.sidebar.usage.governanceProfileFilterAll,
        value: GOVERNANCE_FILTER_ALL,
      },
      ...(settingsQuery.data?.available_tool_registry_profiles ?? []).map((value) => ({
        label: value,
        value,
      })),
    ],
    [settingsQuery.data?.available_tool_registry_profiles, t.sidebar.usage.governanceProfileFilterAll],
  );

  const providerSourceFilterOptions = useMemo(
    () => [
      {
        label: t.sidebar.usage.governanceSourceFilterAll,
        value: GOVERNANCE_FILTER_ALL,
      },
      ...(settingsQuery.data?.available_tool_registry_provider_sources ?? []).map(
        (value) => ({
          label: value,
          value,
        }),
      ),
    ],
    [
      settingsQuery.data?.available_tool_registry_provider_sources,
      t.sidebar.usage.governanceSourceFilterAll,
    ],
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
        const governance = row.governance;
        const governanceAllowedTools =
          governance && governance.allowed_tool_labels.length > 0
            ? governance.allowed_tool_labels
            : governance?.allowed_tool_names ?? [];
        return (
          <div className="usage-session-cell">
            <strong title={label}>{label}</strong>
            <span>{shortenId(row.session_id)}</span>
            <span
              className="usage-session-governance"
              data-testid="usage-session-governance-summary"
            >
              {[
                governance?.profiles?.length
                  ? `${t.sidebar.usage.governanceProfilesLabel} ${governance.profiles.join(", ")}`
                  : null,
                governance?.provider_sources?.length
                  ? `${t.sidebar.usage.governanceSourcesLabel} ${governance.provider_sources.join(", ")}`
                  : null,
                governanceAllowedTools.length > 0
                  ? `${t.inspector.traceMeta.allowedTools} ${governanceAllowedTools.join(", ")}`
                  : null,
              ]
                .filter((item): item is string => Boolean(item))
                .join(" · ")}
            </span>
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
        const governance = row.governance;
        const governanceAllowedTools =
          governance && governance.allowed_tool_labels.length > 0
            ? governance.allowed_tool_labels
            : governance?.allowed_tool_names ?? [];
        return (
          <div className="usage-task-prompt-cell">
            <strong title={prompt}>{prompt}</strong>
            <span>
              {row.session_title?.trim() || shortenId(row.session_id)} · {shortenId(row.task_id)}
            </span>
            <span
              className="usage-task-governance"
              data-testid="usage-task-governance-summary"
            >
              {[
                `${t.sidebar.usage.sourceTitle} ${formatUsageSourceLabel(row.source_kind, t)}`,
                governance?.profile
                  ? `${t.inspector.traceMeta.toolRegistryProfile} ${governance.profile}`
                  : null,
                governance?.provider_source
                  ? `${t.inspector.traceMeta.toolRegistrySource} ${governance.provider_source}`
                  : null,
                governanceAllowedTools.length > 0
                  ? `${t.inspector.traceMeta.allowedTools} ${governanceAllowedTools.join(", ")}`
                  : null,
              ]
                .filter((item): item is string => Boolean(item))
                .join(" · ")}
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

      <div className="usage-dashboard-topline" data-testid="usage-dashboard-topline">
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
            data-testid="usage-scope-segmented"
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
              data-testid="usage-dashboard-refresh"
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
      <div className="usage-source-filter-row" data-testid="usage-source-filter-row">
        <Segmented<UsageSourceFilter>
          size="small"
          data-testid="usage-source-filter-segmented"
          value={sourceFilter}
          onChange={(value) => setSourceFilter(value)}
          options={[
            {
              label: (
                <span data-testid="usage-source-filter-all">
                  {t.sidebar.usage.sourceFilterAll}
                </span>
              ),
              value: "all",
            },
            {
              label: (
                <span data-testid="usage-source-filter-provider">
                  {t.sidebar.usage.sourceProvider}
                </span>
              ),
              value: "provider",
            },
            {
              label: (
                <span data-testid="usage-source-filter-estimated">
                  {t.sidebar.usage.sourceEstimated}
                </span>
              ),
              value: "estimated",
            },
            {
              label: (
                <span data-testid="usage-source-filter-mixed">
                  {t.sidebar.usage.sourceMixed}
                </span>
              ),
              value: "mixed",
            },
            {
              label: (
                <span data-testid="usage-source-filter-legacy">
                  {t.sidebar.usage.sourceLegacy}
                </span>
              ),
              value: "legacy",
            },
          ]}
        />
      </div>
      <div
        className="usage-governance-filter-row"
        data-testid="usage-governance-filter-row"
      >
        <span className="usage-governance-filter-label">
          {t.sidebar.usage.governanceFilterTitle}
        </span>
        <Select
          size="small"
          data-testid="usage-governance-profile-filter"
          value={toolRegistryProfileFilter}
          onChange={(value) => setToolRegistryProfileFilter(value)}
          options={profileFilterOptions}
          popupMatchSelectWidth={false}
          style={{ minWidth: 180 }}
        />
        <Select
          size="small"
          data-testid="usage-governance-source-filter"
          value={toolRegistryProviderSourceFilter}
          onChange={(value) => setToolRegistryProviderSourceFilter(value)}
          options={providerSourceFilterOptions}
          popupMatchSelectWidth={false}
          style={{ minWidth: 180 }}
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
          <div className="usage-source-strip" data-testid="usage-source-strip">
            <span className="usage-source-title">{t.sidebar.usage.sourceTitle}</span>
            <Tag data-testid="usage-source-count-provider">
              {t.sidebar.usage.sourceProvider}:{" "}
              {tokenFmt.format(sourceProviderCount)}
            </Tag>
            <Tag data-testid="usage-source-count-estimated">
              {t.sidebar.usage.sourceEstimated}:{" "}
              {tokenFmt.format(sourceEstimatedCount)}
            </Tag>
            <Tag data-testid="usage-source-count-mixed">
              {t.sidebar.usage.sourceMixed}:{" "}
              {tokenFmt.format(sourceMixedCount)}
            </Tag>
            <Tag data-testid="usage-source-count-legacy">
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
      <div className="usage-source-trend-block" data-testid="usage-source-trend-block">
        <p className="usage-trend-title">{t.sidebar.usage.sourceTrendTitle}</p>
        {sourceTrendRows.length === 0 ? (
          <p className="usage-dashboard-note">{t.sidebar.usage.trendEmpty}</p>
        ) : (
          <div className="usage-source-trend-list" data-testid="usage-source-trend-list">
            {sourceTrendRows.map((row) => (
              <div
                key={`source-${row.day}`}
                className="usage-source-trend-row"
                data-testid="usage-source-trend-row"
              >
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

      <div className="usage-dashboard-table-wrap" data-testid="usage-dashboard-table-wrap">
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
