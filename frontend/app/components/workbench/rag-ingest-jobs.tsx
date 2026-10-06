"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, App, Button, Progress, Space, Tag, Typography } from "antd";
import { useEffect, useRef } from "react";

import { apiJson, apiPostJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages } from "../../../lib/preferences-context";
import type { RagIngestResponse } from "./types";
import { API_BASE_URL } from "./utils";

type ImportStatus = "queued" | "running" | "completed" | "failed" | "cancelled";
type ImportError = "invalid_input" | "chroma_unavailable" | "interrupted" | "permission_revoked";
export type RagIngestJob = {
  id: string;
  knowledge_base_id: string;
  document_total: number;
  status: ImportStatus;
  result: RagIngestResponse | null;
  progress?: { documents_processed: number; chunks_written: number; chunk_total: number } | null;
  error_code: ImportError | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};
type ImportPayload = {
  idempotency_key: string;
  knowledge_base_id: string;
  documents: { text: string; source: string }[];
};
const statusColors: Record<ImportStatus, string> = {
  queued: "default", running: "processing", completed: "success",
  failed: "error", cancelled: "default",
};

export function RagIngestJobs({ open, knowledgeBaseId, text, source, disabled, onReview }: {
  open: boolean;
  knowledgeBaseId: string;
  text: string;
  source: string;
  disabled: boolean;
  onReview: (knowledgeBaseId: string) => void;
}) {
  const t = useMessages();
  const copy = t.inspector.rag.jobs;
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const observedTerminals = useRef(new Set<string>());
  const queryKey = ["rag-ingest-jobs", knowledgeBaseId];
  const history = useQuery({
    queryKey,
    queryFn: () => apiJson<{ items: RagIngestJob[] }>(
      `${API_BASE_URL}/api/rag/ingest-jobs?knowledge_base_id=${encodeURIComponent(knowledgeBaseId)}`,
    ),
    enabled: open,
    refetchInterval: open ? 1500 : false,
    refetchIntervalInBackground: false,
  });
  const submit = useMutation({
    mutationFn: (payload: ImportPayload) => apiPostJson<RagIngestJob>(
      `${API_BASE_URL}/api/rag/ingest-jobs`, payload,
    ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["rag-ingest-jobs"] });
      message.success(copy.accepted);
    },
  });
  const cancel = useMutation({
    mutationFn: (id: string) => apiPostJson<RagIngestJob>(
      `${API_BASE_URL}/api/rag/ingest-jobs/${encodeURIComponent(id)}/cancel`, {},
    ),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["rag-ingest-jobs"] });
    },
  });

  useEffect(() => {
    let changed = false;
    for (const job of history.data?.items ?? []) {
      if ((job.status === "completed" || job.status === "failed") && !observedTerminals.current.has(job.id)) {
        observedTerminals.current.add(job.id);
        changed = true;
      }
    }
    if (changed) {
      void queryClient.invalidateQueries({ queryKey: ["rag-status", knowledgeBaseId] });
      void queryClient.invalidateQueries({ queryKey: ["rag-kb-governance"] });
    }
  }, [history.data, knowledgeBaseId, queryClient]);

  const submissionError = submit.error ? toUserFacingError(submit.error, t.errors).banner : null;
  const historyError = history.error ? toUserFacingError(history.error, t.errors).banner : null;
  const cancelError = cancel.error ? toUserFacingError(cancel.error, t.errors).banner : null;

  return (
    <div data-testid="rag-ingest-jobs">
      <Space wrap>
        <Button size="small" loading={submit.isPending} disabled={disabled || !text.trim()}
          data-testid="rag-ingest-background-submit" onClick={() => {
            submit.mutate({ idempotency_key: crypto.randomUUID(), knowledge_base_id: knowledgeBaseId,
              documents: [{ text: text.trim(), source: source.trim() || "manual" }] });
          }}>
          {copy.submit}
        </Button>
        <Typography.Text type="secondary">{copy.hint}</Typography.Text>
      </Space>
      {submissionError ? (
        <Alert type="error" showIcon title={copy.submitFailed} description={submissionError}
          data-testid="rag-ingest-job-submit-error" action={
            <Button size="small" loading={submit.isPending} disabled={disabled}
              data-testid="rag-ingest-job-submit-retry" onClick={() => {
                if (submit.variables) submit.mutate(submit.variables);
              }}>{t.inspector.rag.recoveryRetry}</Button>
          } />
      ) : null}
      <Space style={{ marginTop: 12 }}>
        <Typography.Text strong>{copy.title}</Typography.Text>
        <Button size="small" loading={history.isFetching} data-testid="rag-ingest-jobs-refresh"
          onClick={() => { void history.refetch(); }}>{t.inspector.rag.statusRefresh}</Button>
      </Space>
      {historyError ? <Alert type="error" showIcon title={copy.loadFailed}
        description={historyError} data-testid="rag-ingest-jobs-error" /> : null}
      {cancelError ? <Alert type="warning" showIcon title={copy.cancelFailed}
        description={cancelError} /> : null}
      {!history.data && history.isPending ? <p>{t.inspector.rag.statusLoading}</p> : null}
      {history.data?.items.length === 0 ? <p className="panel-note">{copy.empty}</p> : null}
      <div aria-live="polite">
        {history.data?.items.map((job) => (
          <div key={job.id} data-testid={`rag-ingest-job-${job.id}`} style={{ padding: "10px 0" }}>
            <Space wrap>
              <Tag color={statusColors[job.status]}>{copy.status[job.status]}</Tag>
              <Typography.Text>{copy.documents(job.document_total)}</Typography.Text>
              <Typography.Text type="secondary">{new Date(job.created_at).toLocaleString()}</Typography.Text>
              {job.status === "queued" ? (
                <Button size="small" loading={cancel.isPending && cancel.variables === job.id}
                  disabled={cancel.isPending} data-testid={`rag-ingest-job-cancel-${job.id}`}
                  onClick={() => cancel.mutate(job.id)}>{copy.cancel}</Button>
              ) : null}
              {job.status === "completed" || job.status === "failed" ? (
                <Button size="small" data-testid={`rag-ingest-job-review-${job.id}`}
                  onClick={() => onReview(job.knowledge_base_id)}>{t.inspector.rag.ingestReviewAction}</Button>
              ) : null}
            </Space>
            {job.progress && job.progress.chunk_total > 0 ? (
              <div data-testid={`rag-ingest-job-progress-${job.id}`}>
                <Progress size="small" showInfo={false}
                  percent={Math.min(100, Math.round(100 * job.progress.chunks_written / job.progress.chunk_total))}
                  status={job.status === "failed" ? "exception" : job.status === "completed" ? "success" : "active"} />
                <Typography.Text type="secondary">{copy.progress(job.progress.documents_processed,
                  job.document_total, job.progress.chunks_written, job.progress.chunk_total)}</Typography.Text>
                {job.status === "failed" ? <p className="panel-note">{copy.confirmedOnly}</p> : null}
              </div>
            ) : null}
            {job.result ? <p className="panel-note">{t.inspector.rag.ingestSuccess(
              job.result.chunks_added, job.result.document_count,
            )}</p> : null}
            {job.error_code ? <Alert type="warning" showIcon title={copy.errors[job.error_code]}
              description={copy.reviewBeforeRetry} /> : null}
          </div>
        ))}
      </div>
    </div>
  );
}
