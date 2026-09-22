"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, App, Button, Input, Modal, Space, Typography } from "antd";
import { BookOpenCheck, RefreshCw } from "lucide-react";
import { useRef, useState } from "react";

import { apiJson, apiPostJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages } from "../../../lib/preferences-context";

import type {
  RagIngestResponse,
  RagQueryResponse,
  RagStatus,
} from "./types";
import { RuntimeDebugMemorySection } from "./runtime-debug-memory-section";
import { RuntimeDebugRecoveryAlert } from "./runtime-debug-recovery-alert";
import { RuntimeDebugRagResults } from "./runtime-debug-rag-results";
import {
  resolveRagKnowledgeBaseSwitch,
  resolveRagMutationRecovery,
  resolveRagStatusView,
} from "./runtime-debug-modal-utils";
import { API_BASE_URL } from "./utils";
import { shortenId } from "./utils";

const { TextArea } = Input;

type RuntimeDebugModalProps = {
  open: boolean;
  onClose: () => void;
  activeSessionId?: string | null;
  initialFocus?: "rag" | null;
  onReviewKnowledgeBase: (knowledgeBaseId: string) => void;
};

export function RuntimeDebugModal({
  open,
  onClose,
  activeSessionId = null,
  initialFocus = null,
  onReviewKnowledgeBase,
}: RuntimeDebugModalProps) {
  const t = useMessages();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [ragKnowledgeBaseId, setRagKnowledgeBaseId] = useState("default");
  const [ragAppliedKnowledgeBaseId, setRagAppliedKnowledgeBaseId] =
    useState("default");
  const [ragIngestDraft, setRagIngestDraft] = useState("");
  const [ragIngestSource, setRagIngestSource] = useState("");
  const [ragQueryDraft, setRagQueryDraft] = useState("");
  const ragSectionRef = useRef<HTMLDivElement>(null);

  const ragIngestMutation = useMutation({
    mutationFn: async (payload: {
      knowledgeBaseId: string;
      text: string;
      source: string;
    }) =>
      apiPostJson<RagIngestResponse>(`${API_BASE_URL}/api/rag/ingest`, {
        knowledge_base_id: payload.knowledgeBaseId,
        documents: [
          {
            text: payload.text,
            source: payload.source || "manual",
          },
        ],
      }),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: ["rag-status"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["rag-kb-governance"],
      });
      message.success(
        t.inspector.rag.ingestSuccess(data.chunks_added, data.document_count),
      );
    },
  });

  const ragQueryMutation = useMutation({
    mutationFn: async (payload: { knowledgeBaseId: string; query: string }) =>
      apiPostJson<RagQueryResponse>(`${API_BASE_URL}/api/rag/query`, {
        knowledge_base_id: payload.knowledgeBaseId,
        query: payload.query,
        top_k: 6,
      }),
  });

  const ragStatusQuery = useQuery({
    queryKey: ["rag-status", ragAppliedKnowledgeBaseId.trim() || "default"],
    queryFn: () =>
      apiJson<RagStatus>(
        `${API_BASE_URL}/api/rag/status?knowledge_base_id=${encodeURIComponent(
          ragAppliedKnowledgeBaseId.trim() || "default",
        )}`,
      ),
    enabled: open,
    staleTime: 10_000,
  });
  const ragStatus = ragStatusQuery.data;
  const ragStatusLoading = ragStatusQuery.isLoading;
  const ragStatusError =
    ragStatusQuery.isError && ragStatusQuery.error
      ? toUserFacingError(ragStatusQuery.error, t.errors).banner
      : null;
  const ragStatusView = resolveRagStatusView({
    isLoading: ragStatusLoading,
    isError: Boolean(ragStatusError),
    hasData: Boolean(ragStatus),
  });
  const ragIngestError =
    ragIngestMutation.isError && ragIngestMutation.error
      ? toUserFacingError(ragIngestMutation.error, t.errors)
      : null;
  const ragIngestRecovery = ragIngestError
    ? resolveRagMutationRecovery(ragIngestMutation.error)
    : null;
  const ragQueryError =
    ragQueryMutation.isError && ragQueryMutation.error
      ? toUserFacingError(ragQueryMutation.error, t.errors)
      : null;
  const ragQueryRecovery = ragQueryError
    ? resolveRagMutationRecovery(ragQueryMutation.error)
    : null;
  const recoveryGuidance = {
    retry: t.inspector.rag.recoveryRetryHint,
    review_input: t.inspector.rag.recoveryReviewInputHint,
    reauthenticate: t.inspector.rag.recoveryReauthenticateHint,
  };
  const ragOperationPending =
    ragIngestMutation.isPending || ragQueryMutation.isPending;

  const applyRagKnowledgeBase = () => {
    const next = resolveRagKnowledgeBaseSwitch(
      ragAppliedKnowledgeBaseId,
      ragKnowledgeBaseId,
    );
    setRagKnowledgeBaseId(next.knowledgeBaseId);
    setRagAppliedKnowledgeBaseId(next.knowledgeBaseId);
    if (next.changed) {
      ragIngestMutation.reset();
      ragQueryMutation.reset();
    }
  };

  return (
    <Modal
      title={t.sidebar.menuRuntimeDebug}
      open={open}
      onCancel={onClose}
      footer={null}
      width={760}
      destroyOnHidden
      className="runtime-debug-ant-modal"
      data-testid="runtime-debug-modal"
      afterOpenChange={(isOpen) => {
        if (!isOpen || initialFocus !== "rag") {
          return;
        }
        const ragSection = ragSectionRef.current;
        ragSection?.scrollIntoView({ block: "start" });
        ragSection
          ?.querySelector<HTMLTextAreaElement>(
            '[data-testid="inspector-rag-ingest-input"]',
          )
          ?.focus({ preventScroll: true });
      }}
    >
      <Typography.Paragraph
        type="secondary"
        className="runtime-debug-lead"
        style={{ marginTop: 0 }}
      >
        {t.inspector.contextKicker}
      </Typography.Paragraph>
      <div className="runtime-debug-topline">
        <span className="runtime-debug-chip">
          {t.inspector.session}
          <code>{activeSessionId ? shortenId(activeSessionId) : "—"}</code>
        </span>
        <span className="runtime-debug-chip">
          KB
          <code>{ragAppliedKnowledgeBaseId || "default"}</code>
        </span>
      </div>
      <div className="runtime-debug-shell">

      <RuntimeDebugMemorySection
        key={activeSessionId ?? "__none__"}
        open={open}
        activeSessionId={activeSessionId}
      />

      <div
        ref={ragSectionRef}
        className="runtime-debug-section"
        data-testid="runtime-debug-rag-section"
      >
        <p className="summary-label">{t.inspector.rag.kicker}</p>
        <strong className="memory-placeholder-title">{t.inspector.rag.title}</strong>
        <p className="panel-note panel-note--muted memory-placeholder-lead">
          {t.inspector.rag.lead}
        </p>

        <div className="memory-collection-row">
          <span className="memory-collection-label">{t.inspector.rag.kbIdLabel}</span>
          <Space.Compact size="small" className="rag-kb-compact">
            <Input
              size="small"
              value={ragKnowledgeBaseId}
              onChange={(e) => setRagKnowledgeBaseId(e.target.value)}
              onPressEnter={applyRagKnowledgeBase}
              placeholder={t.inspector.rag.kbIdPlaceholder}
              className="rag-kb-input"
              disabled={ragOperationPending}
              data-testid="inspector-rag-kb-input"
            />
            <Button
              size="small"
              onClick={applyRagKnowledgeBase}
              disabled={ragOperationPending}
              data-testid="inspector-rag-kb-apply"
            >
              {t.inspector.rag.applyKb}
            </Button>
          </Space.Compact>
        </div>

        <div className="memory-status-block" aria-live="polite">
          {ragStatusView.showLoading ? (
            <p className="memory-status-loading">{t.inspector.rag.statusLoading}</p>
          ) : null}
          {ragStatusView.showError && ragStatusError ? (
            <Alert
              type="error"
              showIcon
              data-testid="inspector-rag-status-error"
              title={t.inspector.rag.statusFailedTitle}
              description={ragStatusError}
              action={
                <Button
                  size="small"
                  icon={<RefreshCw size={14} aria-hidden />}
                  loading={ragStatusQuery.isFetching}
                  data-testid="inspector-rag-status-retry"
                  onClick={() => {
                    void ragStatusQuery.refetch();
                  }}
                >
                  {t.inspector.rag.statusRefresh}
                </Button>
              }
            />
          ) : null}
          {ragStatusView.showStatus && ragStatus ? (
            <>
              <div className="memory-status-line">
                <span className="memory-status-key">Chroma</span>
                <span
                  className={
                    ragStatus.chroma_reachable
                      ? "memory-status-val memory-status-val--ok"
                      : "memory-status-val memory-status-val--bad"
                  }
                >
                  {ragStatus.chroma_reachable
                    ? t.inspector.rag.chromaConnected
                    : t.inspector.rag.chromaDisconnected}
                </span>
              </div>
              <div className="memory-status-line">
                <span className="memory-status-key"> </span>
                <span className="memory-status-val">
                  {ragStatus.collection_exists
                    ? t.inspector.rag.collectionExists
                    : t.inspector.rag.collectionMissing}
                </span>
              </div>
              <div className="memory-status-line">
                <span className="memory-status-key"> </span>
                <span className="memory-status-val">
                  {t.inspector.rag.docCount(ragStatus.document_count)}
                </span>
              </div>
              {ragStatus.error ? (
                <p className="panel-note panel-note--muted memory-chroma-err">
                  {ragStatus.error}
                </p>
              ) : null}
            </>
          ) : null}
        </div>

        <div className="memory-debug-block">
          <TextArea
            className="memory-debug-textarea"
            value={ragIngestDraft}
            onChange={(e) => setRagIngestDraft(e.target.value)}
            placeholder={t.inspector.rag.ingestPlaceholder}
            rows={3}
            disabled={ragIngestMutation.isPending}
            data-testid="inspector-rag-ingest-input"
          />
          <Input
            size="small"
            value={ragIngestSource}
            onChange={(e) => setRagIngestSource(e.target.value)}
            placeholder={t.inspector.rag.ingestSourcePlaceholder}
            disabled={ragIngestMutation.isPending}
            data-testid="inspector-rag-ingest-source"
          />
          <div className="memory-debug-actions">
            <Button
              type="primary"
              size="small"
              loading={ragIngestMutation.isPending}
              data-testid="inspector-rag-ingest-submit"
              onClick={() => {
                const text = ragIngestDraft.trim();
                if (!text) {
                  message.warning(t.inspector.rag.ingestEmpty);
                  return;
                }
                ragIngestMutation.mutate({
                  knowledgeBaseId: ragAppliedKnowledgeBaseId.trim() || "default",
                  text,
                  source: ragIngestSource.trim(),
                });
              }}
            >
              {t.inspector.rag.ingestButton}
            </Button>
          </div>
          {ragIngestError && ragIngestRecovery ? (
            <RuntimeDebugRecoveryAlert
              title={t.inspector.rag.ingestFailedTitle}
              error={ragIngestError}
              guidance={recoveryGuidance[ragIngestRecovery.kind]}
              retryLabel={t.inspector.rag.recoveryRetry}
              canRetry={
                ragIngestRecovery.canRetry && Boolean(ragIngestMutation.variables)
              }
              retrying={ragIngestMutation.isPending}
              testId="inspector-rag-ingest-error"
              onRetry={() => {
                if (ragIngestMutation.variables) {
                  ragIngestMutation.mutate(ragIngestMutation.variables);
                }
              }}
            />
          ) : null}
          {ragIngestMutation.isSuccess && ragIngestMutation.data ? (
            <Alert
              type="success"
              showIcon
              data-testid="inspector-rag-ingest-review"
              title={t.inspector.rag.ingestReviewTitle}
              description={t.inspector.rag.ingestReviewDescription(
                ragIngestMutation.data.knowledge_base_id,
              )}
              action={
                <Button
                  size="small"
                  icon={<BookOpenCheck size={14} aria-hidden />}
                  data-testid="inspector-rag-ingest-review-open"
                  onClick={() =>
                    onReviewKnowledgeBase(
                      ragIngestMutation.data.knowledge_base_id,
                    )
                  }
                >
                  {t.inspector.rag.ingestReviewAction}
                </Button>
              }
            />
          ) : null}

          <TextArea
            className="memory-debug-textarea memory-debug-textarea--query"
            value={ragQueryDraft}
            onChange={(e) => setRagQueryDraft(e.target.value)}
            placeholder={t.inspector.rag.queryPlaceholder}
            rows={2}
            disabled={ragQueryMutation.isPending}
            data-testid="inspector-rag-query-input"
          />
          <div className="memory-debug-actions">
            <Button
              size="small"
              loading={ragQueryMutation.isPending}
              data-testid="inspector-rag-query-submit"
              onClick={() => {
                const text = ragQueryDraft.trim();
                if (!text) {
                  message.warning(t.inspector.rag.queryEmptyInput);
                  return;
                }
                ragQueryMutation.mutate({
                  knowledgeBaseId: ragAppliedKnowledgeBaseId.trim() || "default",
                  query: text,
                });
              }}
            >
              {t.inspector.rag.queryButton}
            </Button>
          </div>
          {ragQueryError && ragQueryRecovery ? (
            <RuntimeDebugRecoveryAlert
              title={t.inspector.rag.queryFailedTitle}
              error={ragQueryError}
              guidance={recoveryGuidance[ragQueryRecovery.kind]}
              retryLabel={t.inspector.rag.recoveryRetry}
              canRetry={
                ragQueryRecovery.canRetry && Boolean(ragQueryMutation.variables)
              }
              retrying={ragQueryMutation.isPending}
              testId="inspector-rag-query-error"
              onRetry={() => {
                if (ragQueryMutation.variables) {
                  ragQueryMutation.mutate(ragQueryMutation.variables);
                }
              }}
            />
          ) : null}
          {ragQueryMutation.isSuccess && ragQueryMutation.data ? (
            <RuntimeDebugRagResults
              hitCount={ragQueryMutation.data.hit_count}
              hits={ragQueryMutation.data.hits}
              t={t}
            />
          ) : null}
        </div>
      </div>
      </div>
    </Modal>
  );
}
