"use client";

import { App, Button, Input, Modal, Segmented, Space } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { apiJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages, usePreferences } from "../../../lib/preferences-context";

import type { AuditLogItem, AuditLogListResponse } from "./types";
import { shortenId } from "./utils";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const PAGE_SIZE = 20;

type AuditLogsModalProps = {
  open: boolean;
  onClose: () => void;
};

type EventFilter = "all" | "login" | "logout" | "refresh" | "settings_update";
type TimeFilter = "all" | "7d" | "30d";
type ExportScope = "current" | "all";

function buildAuditUrl(params: {
  limit: number;
  offset: number;
  eventType: EventFilter;
  timeFilter: TimeFilter;
  sessionId: string;
  taskId: string;
}): string {
  const q = new URLSearchParams();
  q.set("limit", String(params.limit));
  q.set("offset", String(params.offset));
  if (params.eventType !== "all") {
    q.set("event_type", params.eventType);
  }
  if (params.timeFilter !== "all") {
    const days = params.timeFilter === "7d" ? 7 : 30;
    q.set(
      "start_at",
      new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString(),
    );
  }
  if (params.sessionId.trim()) {
    q.set("session_id", params.sessionId.trim());
  }
  if (params.taskId.trim()) {
    q.set("task_id", params.taskId.trim());
  }
  return `${API_BASE_URL}/api/audit/logs?${q.toString()}`;
}

function downloadText(filename: string, content: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function csvEscape(value: unknown): string {
  const raw = value === null || value === undefined ? "" : String(value);
  if (raw.includes(",") || raw.includes("\"") || raw.includes("\n")) {
    return `"${raw.replaceAll("\"", "\"\"")}"`;
  }
  return raw;
}

export function AuditLogsModal({ open, onClose }: AuditLogsModalProps) {
  const { message } = App.useApp();
  const t = useMessages();
  const { localeTag } = usePreferences();

  const [eventFilter, setEventFilter] = useState<EventFilter>("all");
  const [timeFilter, setTimeFilter] = useState<TimeFilter>("7d");
  const [sessionIdFilter, setSessionIdFilter] = useState("");
  const [taskIdFilter, setTaskIdFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [rows, setRows] = useState<AuditLogItem[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [exporting, setExporting] = useState<"json" | "csv" | null>(null);
  const [exportScope, setExportScope] = useState<ExportScope>("all");

  const query = useQuery({
    queryKey: [
      "audit-modal",
      eventFilter,
      timeFilter,
      sessionIdFilter,
      taskIdFilter,
      offset,
      open,
    ],
    enabled: open,
    queryFn: () =>
      apiJson<AuditLogListResponse>(
        buildAuditUrl({
          limit: PAGE_SIZE,
          offset,
          eventType: eventFilter,
          timeFilter,
          sessionId: sessionIdFilter,
          taskId: taskIdFilter,
        }),
      ),
    staleTime: 8_000,
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    setOffset(0);
    setRows([]);
    setHasMore(false);
  }, [open, eventFilter, timeFilter, sessionIdFilter, taskIdFilter]);

  useEffect(() => {
    if (!query.data) {
      return;
    }
    const incoming = query.data.items ?? [];
    if (offset === 0) {
      setRows(incoming);
    } else {
      setRows((prev) => {
        const seen = new Set(prev.map((r) => r.id));
        const merged = [...prev];
        for (const item of incoming) {
          if (!seen.has(item.id)) {
            merged.push(item);
          }
        }
        return merged;
      });
    }
    setHasMore(Boolean(query.data.has_more));
  }, [offset, query.data]);

  const errorText = useMemo(() => {
    if (!query.isError || !query.error) {
      return null;
    }
    return toUserFacingError(query.error, t.errors).banner;
  }, [query.error, query.isError, t.errors]);

  const resolveEventLabel = (eventType: string): string => {
    const normalized = eventType.trim().toLowerCase();
    if (normalized === "login") {
      return t.sidebar.audit.eventLabelLogin;
    }
    if (normalized === "logout") {
      return t.sidebar.audit.eventLabelLogout;
    }
    if (normalized === "refresh") {
      return t.sidebar.audit.eventLabelRefresh;
    }
    if (normalized === "settings_update") {
      return t.sidebar.audit.eventLabelSettingsUpdate;
    }
    return t.sidebar.audit.eventLabelUnknown;
  };

  const exportAllRows = async (): Promise<AuditLogItem[]> => {
    const allRows: AuditLogItem[] = [];
    let nextOffset = 0;
    while (true) {
      const page = await apiJson<AuditLogListResponse>(
        buildAuditUrl({
          limit: 100,
          offset: nextOffset,
          eventType: eventFilter,
          timeFilter,
          sessionId: sessionIdFilter,
          taskId: taskIdFilter,
        }),
      );
      allRows.push(...page.items);
      if (!page.has_more || page.items.length === 0) {
        break;
      }
      nextOffset += page.items.length;
    }
    return allRows;
  };

  const resolveExportRows = async (): Promise<AuditLogItem[]> => {
    if (exportScope === "current") {
      return rows;
    }
    return exportAllRows();
  };

  const handleExportJson = async () => {
    if (exporting) {
      return;
    }
    setExporting("json");
    try {
      const allRows = await resolveExportRows();
      downloadText(
        `audit-logs-${Date.now()}.json`,
        JSON.stringify(allRows, null, 2),
        "application/json;charset=utf-8",
      );
      message.success(t.sidebar.audit.exportDone(allRows.length));
    } catch (error) {
      const tip = toUserFacingError(error, t.errors).banner;
      message.error(tip);
    } finally {
      setExporting(null);
    }
  };

  const handleExportCsv = async () => {
    if (exporting) {
      return;
    }
    setExporting("csv");
    try {
      const allRows = await resolveExportRows();
      const header = [
        t.sidebar.audit.colEvent,
        t.sidebar.audit.colTime,
        t.sidebar.audit.colSession,
        t.sidebar.audit.colTask,
        t.sidebar.audit.colDetail,
      ];
      const lines = [header.map(csvEscape).join(",")];
      for (const item of allRows) {
        lines.push(
          [
            resolveEventLabel(item.event_type),
            item.created_at,
            item.session_id ?? "",
            item.task_id ?? "",
            item.event_detail ? JSON.stringify(item.event_detail) : "",
          ]
            .map(csvEscape)
            .join(","),
        );
      }
      downloadText(`audit-logs-${Date.now()}.csv`, lines.join("\n"), "text/csv;charset=utf-8");
      message.success(t.sidebar.audit.exportDone(allRows.length));
    } catch (error) {
      const tip = toUserFacingError(error, t.errors).banner;
      message.error(tip);
    } finally {
      setExporting(null);
    }
  };

  return (
    <Modal
      title={t.sidebar.audit.title}
      open={open}
      onCancel={onClose}
      footer={null}
      width={900}
      destroyOnHidden
      className="audit-modal"
    >
      <p className="audit-modal-lead">{t.sidebar.audit.lead}</p>
      <div className="audit-modal-toolbar">
        <span className="audit-modal-label">{t.sidebar.audit.filterEventLabel}</span>
        <Segmented
          size="small"
          value={eventFilter}
          onChange={(value) => setEventFilter(value as EventFilter)}
          options={[
            { label: t.sidebar.audit.filterEventAll, value: "all" },
            { label: t.sidebar.audit.filterEventLogin, value: "login" },
            { label: t.sidebar.audit.filterEventLogout, value: "logout" },
            { label: t.sidebar.audit.filterEventRefresh, value: "refresh" },
            {
              label: t.sidebar.audit.filterEventSettingsUpdate,
              value: "settings_update",
            },
          ]}
        />

        <span className="audit-modal-label">{t.sidebar.audit.filterRangeLabel}</span>
        <Segmented
          size="small"
          value={timeFilter}
          onChange={(value) => setTimeFilter(value as TimeFilter)}
          options={[
            { label: t.sidebar.audit.filterRangeAll, value: "all" },
            { label: t.sidebar.audit.filterRange7d, value: "7d" },
            { label: t.sidebar.audit.filterRange30d, value: "30d" },
          ]}
        />
        <Input
          value={sessionIdFilter}
          onChange={(event) => setSessionIdFilter(event.target.value)}
          placeholder={t.sidebar.audit.filterSessionPlaceholder}
        />
        <Input
          value={taskIdFilter}
          onChange={(event) => setTaskIdFilter(event.target.value)}
          placeholder={t.sidebar.audit.filterTaskPlaceholder}
        />
      </div>

      <div className="audit-modal-actions">
        <Space>
          <span className="audit-modal-label">{t.sidebar.audit.exportScopeLabel}</span>
          <Segmented
            size="small"
            value={exportScope}
            onChange={(value) => setExportScope(value as ExportScope)}
            options={[
              { label: t.sidebar.audit.exportScopeCurrent, value: "current" },
              { label: t.sidebar.audit.exportScopeAll, value: "all" },
            ]}
          />
          <Button
            size="small"
            onClick={() => void handleExportJson()}
            loading={exporting === "json"}
            disabled={Boolean(exporting)}
          >
            {exporting === "json" ? t.sidebar.audit.exportLoading : t.sidebar.audit.exportJson}
          </Button>
          <Button
            size="small"
            onClick={() => void handleExportCsv()}
            loading={exporting === "csv"}
            disabled={Boolean(exporting)}
          >
            {exporting === "csv" ? t.sidebar.audit.exportLoading : t.sidebar.audit.exportCsv}
          </Button>
        </Space>
      </div>

      {query.isLoading && offset === 0 ? (
        <p className="audit-modal-note">{t.sidebar.audit.loading}</p>
      ) : null}
      {errorText ? <p className="audit-modal-note">{t.sidebar.audit.error}</p> : null}
      {!query.isLoading && !errorText && rows.length === 0 ? (
        <p className="audit-modal-note">{t.sidebar.audit.empty}</p>
      ) : null}

      {rows.length > 0 ? (
        <>
          <p className="audit-modal-total">{t.sidebar.audit.total(rows.length)}</p>
          <div className="audit-modal-list">
            {rows.map((item) => {
              const detailText = item.event_detail
                ? JSON.stringify(item.event_detail, null, 2)
                : "";
              return (
                <article key={item.id} className="audit-modal-item">
                  <div className="audit-modal-item-head">
                    <strong>{resolveEventLabel(item.event_type)}</strong>
                    <span>
                      {new Date(item.created_at).toLocaleString(localeTag, { hour12: false })}
                    </span>
                  </div>
                  <div className="audit-modal-item-meta">
                    <span>
                      {t.sidebar.audit.colSession}: {item.session_id ? shortenId(item.session_id) : "—"}
                    </span>
                    <span>
                      {t.sidebar.audit.colTask}: {item.task_id ? shortenId(item.task_id) : "—"}
                    </span>
                  </div>
                  {detailText ? (
                    <details className="audit-modal-details">
                      <summary>{t.sidebar.audit.detailExpand}</summary>
                      <pre>{detailText}</pre>
                    </details>
                  ) : null}
                </article>
              );
            })}
          </div>
        </>
      ) : null}

      {hasMore ? (
        <div className="audit-modal-loadmore">
          <Button
            block
            size="small"
            loading={query.isFetching && offset > 0}
            onClick={() => setOffset((prev) => prev + PAGE_SIZE)}
          >
            {t.sidebar.audit.loadMore}
          </Button>
        </div>
      ) : null}
    </Modal>
  );
}
