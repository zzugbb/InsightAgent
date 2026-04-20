"use client";

import { App, Button, Input, Modal, Segmented, Select, Space, Table, Tag } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { apiJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages, usePreferences } from "../../../lib/preferences-context";

import type { AuditLogItem, AuditLogListResponse } from "./types";
import { shortenId } from "./utils";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type AuditLogsModalProps = {
  open: boolean;
  onClose: () => void;
};

type EventFilter =
  | "all"
  | "login"
  | "logout"
  | "refresh"
  | "settings_update"
  | "settings_validate"
  | "task_create"
  | "task_cancel"
  | "task_timeout"
  | "task_failed"
  | "rag_ingest"
  | "rag_kb_clear"
  | "rag_kb_delete";
type TimeFilter = "all" | "7d" | "30d";
type ExportScope = "current" | "all";
type DetailEntry = { key: string; label: string; value: string };

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

function asDetailMap(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function asBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

export function AuditLogsModal({ open, onClose }: AuditLogsModalProps) {
  const { message } = App.useApp();
  const t = useMessages();
  const { localeTag } = usePreferences();

  const [eventFilter, setEventFilter] = useState<EventFilter>("all");
  const [timeFilter, setTimeFilter] = useState<TimeFilter>("7d");
  const [sessionIdFilter, setSessionIdFilter] = useState("");
  const [taskIdFilter, setTaskIdFilter] = useState("");
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [exporting, setExporting] = useState<"json" | "csv" | null>(null);
  const [exportScope, setExportScope] = useState<ExportScope>("all");
  const offset = (page - 1) * pageSize;

  useEffect(() => {
    if (!open) {
      return;
    }
    setEventFilter("all");
    setTimeFilter("7d");
    setSessionIdFilter("");
    setTaskIdFilter("");
    setKeyword("");
    setPage(1);
    setPageSize(10);
    setExportScope("all");
    setExporting(null);
  }, [open]);

  const query = useQuery({
    queryKey: [
      "audit-modal",
      eventFilter,
      timeFilter,
      sessionIdFilter,
      taskIdFilter,
      keyword,
      pageSize,
      offset,
      open,
    ],
    enabled: open,
    queryFn: () =>
      apiJson<AuditLogListResponse>(
        buildAuditUrl({
          limit: pageSize,
          offset,
          eventType: eventFilter,
          timeFilter,
          sessionId: sessionIdFilter,
          taskId: taskIdFilter,
        }),
      ),
    staleTime: 8_000,
  });

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
    if (normalized === "settings_validate") {
      return t.sidebar.audit.eventLabelSettingsValidate;
    }
    if (normalized === "task_create") {
      return t.sidebar.audit.eventLabelTaskCreate;
    }
    if (normalized === "task_cancel") {
      return t.sidebar.audit.eventLabelTaskCancel;
    }
    if (normalized === "task_timeout") {
      return t.sidebar.audit.eventLabelTaskTimeout;
    }
    if (normalized === "task_failed") {
      return t.sidebar.audit.eventLabelTaskFailed;
    }
    if (normalized === "rag_ingest") {
      return t.sidebar.audit.eventLabelRagIngest;
    }
    if (normalized === "rag_kb_clear") {
      return t.sidebar.audit.eventLabelRagKbClear;
    }
    if (normalized === "rag_kb_delete") {
      return t.sidebar.audit.eventLabelRagKbDelete;
    }
    return t.sidebar.audit.eventLabelUnknown;
  };

  const resolveEventColor = (eventType: string): string => {
    const normalized = eventType.trim().toLowerCase();
    if (normalized === "login") {
      return "green";
    }
    if (normalized === "logout") {
      return "volcano";
    }
    if (normalized === "refresh") {
      return "blue";
    }
    if (normalized === "settings_update") {
      return "purple";
    }
    if (normalized === "settings_validate") {
      return "magenta";
    }
    if (normalized === "task_create") {
      return "geekblue";
    }
    if (normalized === "task_cancel") {
      return "orange";
    }
    if (normalized === "task_timeout") {
      return "gold";
    }
    if (normalized === "task_failed") {
      return "red";
    }
    if (normalized === "rag_ingest") {
      return "cyan";
    }
    if (normalized === "rag_kb_clear" || normalized === "rag_kb_delete") {
      return "volcano";
    }
    return "default";
  };

  const resolveReasonLabel = (reason: string | null): string | null => {
    if (!reason) {
      return null;
    }
    if (reason === "password") {
      return t.sidebar.audit.reasonPassword;
    }
    if (reason === "register_auto_login") {
      return t.sidebar.audit.reasonRegisterAutoLogin;
    }
    return reason;
  };

  const resolveScopeLabel = (scope: string | null): string | null => {
    if (!scope) {
      return null;
    }
    if (scope === "all") {
      return t.sidebar.audit.scopeAll;
    }
    if (scope === "single") {
      return t.sidebar.audit.scopeSingle;
    }
    if (scope === "refresh_token") {
      return t.sidebar.audit.scopeRefreshToken;
    }
    return scope;
  };

  const resolveSummaryText = (item: AuditLogItem): string => {
    const eventLabel = resolveEventLabel(item.event_type);
    const normalizedEventType = item.event_type.trim().toLowerCase();
    const detail = asDetailMap(item.event_detail);
    if (!detail) {
      return eventLabel;
    }

    const reason = resolveReasonLabel(asString(detail.reason));
    const scope = resolveScopeLabel(asString(detail.scope));
    const revoked = asBoolean(detail.revoked);
    const mode = asString(detail.mode);
    const provider = asString(detail.provider);
    const model = asString(detail.model);

    if (normalizedEventType === "login" && reason) {
      return `${eventLabel} · ${reason}`;
    }
    if (normalizedEventType === "logout") {
      const parts: string[] = [];
      if (scope) {
        parts.push(scope);
      }
      if (revoked !== null) {
        parts.push(
          `${t.sidebar.audit.fieldRevoked} ${
            revoked ? t.sidebar.audit.boolYes : t.sidebar.audit.boolNo
          }`,
        );
      }
      return parts.length > 0 ? `${eventLabel} · ${parts.join(" · ")}` : eventLabel;
    }
    if (normalizedEventType === "settings_update") {
      const triplet = [mode, provider, model].filter(Boolean).join(" / ");
      return triplet ? `${eventLabel} · ${triplet}` : eventLabel;
    }
    if (normalizedEventType === "settings_validate") {
      const parts: string[] = [];
      if (mode || provider || model) {
        parts.push([mode, provider, model].filter(Boolean).join(" / "));
      }
      const code = asString(detail.error_code);
      if (code) {
        parts.push(`${t.sidebar.audit.fieldCode}: ${code}`);
      }
      return parts.length > 0 ? `${eventLabel} · ${parts.join(" · ")}` : eventLabel;
    }
    if (normalizedEventType === "task_create") {
      const promptLength = detail.prompt_length;
      if (typeof promptLength === "number" && Number.isFinite(promptLength)) {
        return `${eventLabel} · ${t.sidebar.audit.fieldPromptLength} ${Math.trunc(promptLength)}`;
      }
    }
    if (normalizedEventType === "task_failed" || normalizedEventType === "task_timeout") {
      const code = asString(detail.code);
      return code ? `${eventLabel} · ${code}` : eventLabel;
    }
    if (normalizedEventType === "rag_ingest") {
      const docs = detail.documents_ingested;
      const chunks = detail.chunks_added;
      const parts: string[] = [];
      if (typeof docs === "number" && Number.isFinite(docs)) {
        parts.push(`${t.sidebar.audit.fieldDocumentsIngested} ${Math.trunc(docs)}`);
      }
      if (typeof chunks === "number" && Number.isFinite(chunks)) {
        parts.push(`${t.sidebar.audit.fieldChunksAdded} ${Math.trunc(chunks)}`);
      }
      return parts.length > 0 ? `${eventLabel} · ${parts.join(" · ")}` : eventLabel;
    }
    return eventLabel;
  };

  const resolveReadableDetail = (item: AuditLogItem): DetailEntry[] => {
    const detail = asDetailMap(item.event_detail);
    if (!detail) {
      return [];
    }
    const entries: DetailEntry[] = [];
    const pushIfPresent = (
      key: string,
      label: string,
      value: unknown,
      transform?: (raw: unknown) => string | null,
    ) => {
      if (value === undefined || value === null) {
        return;
      }
      const finalValue = transform ? transform(value) : asString(value);
      if (!finalValue) {
        return;
      }
      entries.push({ key, label, value: finalValue });
    };

    pushIfPresent(
      "reason",
      t.sidebar.audit.fieldReason,
      detail.reason,
      (raw) => resolveReasonLabel(asString(raw)),
    );
    pushIfPresent(
      "scope",
      t.sidebar.audit.fieldScope,
      detail.scope,
      (raw) => resolveScopeLabel(asString(raw)),
    );
    pushIfPresent("mode", t.sidebar.audit.fieldMode, detail.mode);
    pushIfPresent("provider", t.sidebar.audit.fieldProvider, detail.provider);
    pushIfPresent("model", t.sidebar.audit.fieldModel, detail.model);
    pushIfPresent("code", t.sidebar.audit.fieldCode, detail.code);
    pushIfPresent("message", t.sidebar.audit.fieldMessage, detail.message);
    pushIfPresent(
      "prompt_length",
      t.sidebar.audit.fieldPromptLength,
      detail.prompt_length,
      (raw) => {
        if (typeof raw === "number" && Number.isFinite(raw)) {
          return String(Math.trunc(raw));
        }
        return asString(raw);
      },
    );
    pushIfPresent(
      "documents_ingested",
      t.sidebar.audit.fieldDocumentsIngested,
      detail.documents_ingested,
      (raw) => {
        if (typeof raw === "number" && Number.isFinite(raw)) {
          return String(Math.trunc(raw));
        }
        return asString(raw);
      },
    );
    pushIfPresent(
      "chunks_added",
      t.sidebar.audit.fieldChunksAdded,
      detail.chunks_added,
      (raw) => {
        if (typeof raw === "number" && Number.isFinite(raw)) {
          return String(Math.trunc(raw));
        }
        return asString(raw);
      },
    );
    pushIfPresent(
      "document_count",
      t.sidebar.audit.fieldDocumentCount,
      detail.document_count,
      (raw) => {
        if (typeof raw === "number" && Number.isFinite(raw)) {
          return String(Math.trunc(raw));
        }
        return asString(raw);
      },
    );
    pushIfPresent(
      "chunk_size",
      t.sidebar.audit.fieldChunkSize,
      detail.chunk_size,
      (raw) => {
        if (typeof raw === "number" && Number.isFinite(raw)) {
          return String(Math.trunc(raw));
        }
        return asString(raw);
      },
    );
    pushIfPresent(
      "chunk_overlap",
      t.sidebar.audit.fieldChunkOverlap,
      detail.chunk_overlap,
      (raw) => {
        if (typeof raw === "number" && Number.isFinite(raw)) {
          return String(Math.trunc(raw));
        }
        return asString(raw);
      },
    );
    pushIfPresent(
      "revoked",
      t.sidebar.audit.fieldRevoked,
      detail.revoked,
      (raw) => {
        const parsed = asBoolean(raw);
        if (parsed === null) {
          return null;
        }
        return parsed ? t.sidebar.audit.boolYes : t.sidebar.audit.boolNo;
      },
    );
    pushIfPresent(
      "base_url_configured",
      t.sidebar.audit.fieldBaseUrlConfigured,
      detail.base_url_configured,
      (raw) => {
        const parsed = asBoolean(raw);
        if (parsed === null) {
          return null;
        }
        return parsed ? t.sidebar.audit.boolYes : t.sidebar.audit.boolNo;
      },
    );
    pushIfPresent(
      "api_key_configured",
      t.sidebar.audit.fieldApiKeyConfigured,
      detail.api_key_configured,
      (raw) => {
        const parsed = asBoolean(raw);
        if (parsed === null) {
          return null;
        }
        return parsed ? t.sidebar.audit.boolYes : t.sidebar.audit.boolNo;
      },
    );
    return entries;
  };

  const resolveDetailInlineText = (item: AuditLogItem): string => {
    const entries = resolveReadableDetail(item);
    if (entries.length === 0) {
      return "—";
    }
    return entries.map((entry) => `${entry.label}: ${entry.value}`).join(" · ");
  };

  const rows = query.data?.items ?? [];
  const total = query.data?.total ?? 0;
  const normalizedKeyword = keyword.trim().toLowerCase();
  const filteredRows = !normalizedKeyword
    ? rows
    : rows.filter((item) => {
        const haystack = [
          resolveEventLabel(item.event_type),
          resolveSummaryText(item),
          resolveDetailInlineText(item),
          item.session_id ?? "",
          item.task_id ?? "",
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(normalizedKeyword);
      });

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
    const normalizedKeyword = keyword.trim().toLowerCase();
    if (!normalizedKeyword) {
      return allRows;
    }
    return allRows.filter((item) => {
      const haystack = [
        resolveEventLabel(item.event_type),
        resolveSummaryText(item),
        item.session_id ?? "",
        item.task_id ?? "",
        JSON.stringify(item.event_detail ?? {}),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedKeyword);
    });
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
        <div className="audit-modal-filter-row audit-modal-filter-row--primary">
          <Select
            showSearch
            value={eventFilter}
            onChange={(value) => {
              setEventFilter(value as EventFilter);
              setPage(1);
            }}
            options={[
              { label: t.sidebar.audit.filterEventAll, value: "all" },
              { label: t.sidebar.audit.filterEventLogin, value: "login" },
              { label: t.sidebar.audit.filterEventLogout, value: "logout" },
              { label: t.sidebar.audit.filterEventRefresh, value: "refresh" },
              {
                label: t.sidebar.audit.filterEventSettingsUpdate,
                value: "settings_update",
              },
              {
                label: t.sidebar.audit.filterEventSettingsValidate,
                value: "settings_validate",
              },
              {
                label: t.sidebar.audit.filterEventTaskCreate,
                value: "task_create",
              },
              {
                label: t.sidebar.audit.filterEventTaskCancel,
                value: "task_cancel",
              },
              {
                label: t.sidebar.audit.filterEventTaskTimeout,
                value: "task_timeout",
              },
              {
                label: t.sidebar.audit.filterEventTaskFailed,
                value: "task_failed",
              },
              {
                label: t.sidebar.audit.filterEventRagIngest,
                value: "rag_ingest",
              },
              {
                label: t.sidebar.audit.filterEventRagKbClear,
                value: "rag_kb_clear",
              },
              {
                label: t.sidebar.audit.filterEventRagKbDelete,
                value: "rag_kb_delete",
              },
            ]}
            optionFilterProp="label"
            placeholder={t.sidebar.audit.filterEventLabel}
          />
          <Select
            showSearch
            value={timeFilter}
            onChange={(value) => {
              setTimeFilter(value as TimeFilter);
              setPage(1);
            }}
            options={[
              { label: t.sidebar.audit.filterRangeAll, value: "all" },
              { label: t.sidebar.audit.filterRange7d, value: "7d" },
              { label: t.sidebar.audit.filterRange30d, value: "30d" },
            ]}
            optionFilterProp="label"
            placeholder={t.sidebar.audit.filterRangeLabel}
          />
          <Input
            allowClear
            value={keyword}
            onChange={(event) => {
              setKeyword(event.target.value);
              setPage(1);
            }}
            placeholder={t.sidebar.audit.searchPlaceholder}
          />
        </div>
        <div className="audit-modal-filter-row audit-modal-filter-row--secondary">
          <Input
            allowClear
            value={sessionIdFilter}
            onChange={(event) => {
              setSessionIdFilter(event.target.value);
              setPage(1);
            }}
            placeholder={t.sidebar.audit.filterSessionPlaceholder}
          />
          <Input
            allowClear
            value={taskIdFilter}
            onChange={(event) => {
              setTaskIdFilter(event.target.value);
              setPage(1);
            }}
            placeholder={t.sidebar.audit.filterTaskPlaceholder}
          />
          <Button
            className="audit-modal-reset-btn"
            onClick={() => {
              setEventFilter("all");
              setTimeFilter("7d");
              setKeyword("");
              setSessionIdFilter("");
              setTaskIdFilter("");
              setPage(1);
            }}
          >
            {t.sidebar.audit.filterReset}
          </Button>
        </div>
      </div>

      <div className="audit-modal-actions">
        <Space wrap>
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
      {errorText ? <p className="audit-modal-note">{`${t.sidebar.audit.error} ${errorText}`}</p> : null}
      {!query.isLoading && !errorText && filteredRows.length === 0 ? (
        <p className="audit-modal-note">{t.sidebar.audit.empty}</p>
      ) : null}

      {filteredRows.length > 0 ? (
        <>
          <div className="audit-modal-table-wrap">
            <Table<AuditLogItem>
              size="small"
              rowKey={(record) => record.id}
              dataSource={filteredRows}
              pagination={{
                current: page,
                pageSize,
                total,
                showSizeChanger: true,
                showTotal: (n) => t.sidebar.audit.total(n),
                onChange: (nextPage, nextPageSize) => {
                  setPage(nextPage);
                  if (nextPageSize && nextPageSize !== pageSize) {
                    setPageSize(nextPageSize);
                  }
                },
              }}
              className="audit-modal-table"
              columns={[
                {
                  title: t.sidebar.audit.colEvent,
                  dataIndex: "event_type",
                  key: "event_type",
                  width: 130,
                  render: (_value, record) => (
                    <Tag color={resolveEventColor(record.event_type)}>
                      {resolveEventLabel(record.event_type)}
                    </Tag>
                  ),
                },
                {
                  title: t.sidebar.audit.colDetail,
                  key: "summary",
                  render: (_value, record) => (
                    <span className="audit-modal-table-summary">
                      {resolveSummaryText(record)}
                    </span>
                  ),
                },
                {
                  title: t.sidebar.audit.colSession,
                  key: "session_id",
                  width: 120,
                  render: (_value, record) =>
                    record.session_id ? shortenId(record.session_id) : "—",
                },
                {
                  title: t.sidebar.audit.colTask,
                  key: "task_id",
                  width: 120,
                  render: (_value, record) =>
                    record.task_id ? shortenId(record.task_id) : "—",
                },
                {
                  title: t.sidebar.audit.colTime,
                  key: "created_at",
                  width: 180,
                  render: (_value, record) =>
                    new Date(record.created_at).toLocaleString(localeTag, {
                      hour12: false,
                    }),
                },
              ]}
              expandable={{
                expandedRowRender: (record) => {
                  const detailRows = resolveReadableDetail(record);
                  const detailText = record.event_detail
                    ? JSON.stringify(record.event_detail, null, 2)
                    : "";
                  if (detailRows.length === 0 && !detailText) {
                    return <span className="audit-modal-note">—</span>;
                  }
                  return (
                    <div className="audit-modal-expanded">
                      {detailRows.length > 0 ? (
                        <dl className="audit-modal-detail-list">
                          {detailRows.map((entry) => (
                            <div key={entry.key} className="audit-modal-detail-row">
                              <dt>{entry.label}</dt>
                              <dd>{entry.value}</dd>
                            </div>
                          ))}
                        </dl>
                      ) : null}
                      {detailText ? (
                        <pre className="audit-modal-expanded-raw">{detailText}</pre>
                      ) : null}
                    </div>
                  );
                },
                rowExpandable: (record) =>
                  resolveReadableDetail(record).length > 0 || Boolean(record.event_detail),
              }}
              rowClassName={() => "audit-modal-table-row"}
            />
          </div>
          <div className="audit-modal-footer">
            <span className="audit-modal-total">{t.sidebar.audit.total(total)}</span>
          </div>
        </>
      ) : null}
    </Modal>
  );
}
