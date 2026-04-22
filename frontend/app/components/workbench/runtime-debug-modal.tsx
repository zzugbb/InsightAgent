"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Input, Modal, Space, Typography } from "antd";
import { useEffect, useState } from "react";

import { apiJson, apiPostJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages } from "../../../lib/preferences-context";

import type {
  MemoryAddResponse,
  MemoryQueryResponse,
  RagIngestResponse,
  RagQueryResponse,
  RagStatus,
  SessionMemoryStatus,
} from "./types";
import { API_BASE_URL } from "./utils";
import { parseMemoryMetadataJson } from "./utils";

const { TextArea } = Input;

type RuntimeDebugModalProps = {
  open: boolean;
  onClose: () => void;
  activeSessionId?: string | null;
};

export function RuntimeDebugModal({
  open,
  onClose,
  activeSessionId = null,
}: RuntimeDebugModalProps) {
  const t = useMessages();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [memoryAddDraft, setMemoryAddDraft] = useState("");
  const [memoryMetaDraft, setMemoryMetaDraft] = useState("");
  const [memoryQueryDraft, setMemoryQueryDraft] = useState("");
  const [ragKnowledgeBaseId, setRagKnowledgeBaseId] = useState("default");
  const [ragAppliedKnowledgeBaseId, setRagAppliedKnowledgeBaseId] =
    useState("default");
  const [ragIngestDraft, setRagIngestDraft] = useState("");
  const [ragIngestSource, setRagIngestSource] = useState("");
  const [ragQueryDraft, setRagQueryDraft] = useState("");

  const sessionMemoryQuery = useQuery({
    queryKey: ["session-memory-status", activeSessionId ?? "__none__"],
    queryFn: () =>
      apiJson<SessionMemoryStatus>(
        `${API_BASE_URL}/api/sessions/${encodeURIComponent(activeSessionId!)}/memory/status`,
      ),
    enabled: open && Boolean(activeSessionId),
    staleTime: 20_000,
  });

  const sessionMemoryErrorBanner =
    sessionMemoryQuery.isError && sessionMemoryQuery.error
      ? toUserFacingError(sessionMemoryQuery.error, t.errors).banner
      : null;

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
        `${API_BASE_URL}/api/sessions/${encodeURIComponent(activeSessionId)}/memory/add`,
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
        `${API_BASE_URL}/api/sessions/${encodeURIComponent(activeSessionId)}/memory/query`,
        { text, n_results: 8 },
      );
    },
  });

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

  const applyRagKnowledgeBase = () => {
    const next = ragKnowledgeBaseId.trim() || "default";
    setRagKnowledgeBaseId(next);
    setRagAppliedKnowledgeBaseId(next);
  };

  useEffect(() => {
    setMemoryAddDraft("");
    setMemoryMetaDraft("");
    setMemoryQueryDraft("");
    memoryAddMutation.reset();
    memoryQueryMutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId]);

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
    >
      <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
        {t.inspector.contextKicker}
      </Typography.Paragraph>

      <div className="inspector-block memory-placeholder-card">
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
            {activeSessionId ? `memory_${activeSessionId}` : "—"}
          </code>
        </div>
        <div className="memory-status-block" aria-live="polite">
          {!activeSessionId ? (
            <p className="panel-note panel-note--muted memory-pick-session">
              {t.inspector.memory.pickSession}
            </p>
          ) : sessionMemoryQuery.isLoading ? (
            <p className="memory-status-loading">{t.inspector.memory.statusLoading}</p>
          ) : sessionMemoryErrorBanner ? (
            <p className="memory-status-err">{sessionMemoryErrorBanner}</p>
          ) : sessionMemoryQuery.data ? (
            <>
              <div className="memory-status-line">
                <span className="memory-status-key">Chroma</span>
                <span
                  className={
                    sessionMemoryQuery.data.chroma_reachable
                      ? "memory-status-val memory-status-val--ok"
                      : "memory-status-val memory-status-val--bad"
                  }
                >
                  {sessionMemoryQuery.data.chroma_reachable
                    ? t.inspector.memory.chromaConnected
                    : t.inspector.memory.chromaDisconnected}
                </span>
              </div>
              {sessionMemoryQuery.data.chroma_reachable ? (
                <>
                  <div className="memory-status-line">
                    <span className="memory-status-key"> </span>
                    <span className="memory-status-val">
                      {sessionMemoryQuery.data.collection_exists
                        ? t.inspector.memory.collectionExists
                        : t.inspector.memory.collectionMissing}
                    </span>
                  </div>
                  <div className="memory-status-line">
                    <span className="memory-status-key"> </span>
                    <span className="memory-status-val">
                      {t.inspector.memory.docCount(
                        sessionMemoryQuery.data.document_count,
                      )}
                    </span>
                  </div>
                </>
              ) : null}
              {sessionMemoryQuery.data.error ? (
                <p className="panel-note panel-note--muted memory-chroma-err">
                  {sessionMemoryQuery.data.error}
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
                      const id = memoryQueryMutation.data?.ids[0]?.[i] ?? String(i);
                      const dist = memoryQueryMutation.data?.distances?.[0]?.[i];
                      const hitMeta = memoryQueryMutation.data?.metadatas?.[0]?.[i];
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
                              {JSON.stringify(hitMeta as Record<string, unknown>, null, 2)}
                            </pre>
                          ) : null}
                          {typeof dist === "number" && Number.isFinite(dist) ? (
                            <span className="memory-query-hit-dist">
                              {t.inspector.memory.distanceLabel}: {dist.toFixed(4)}
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

      <div className="inspector-block memory-placeholder-card">
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
              data-testid="inspector-rag-kb-input"
            />
            <Button
              size="small"
              onClick={applyRagKnowledgeBase}
              data-testid="inspector-rag-kb-apply"
            >
              {t.inspector.rag.applyKb}
            </Button>
          </Space.Compact>
        </div>

        <div className="memory-status-block" aria-live="polite">
          {ragStatusLoading ? (
            <p className="memory-status-loading">{t.inspector.rag.statusLoading}</p>
          ) : ragStatusError ? (
            <p className="memory-status-err">{ragStatusError}</p>
          ) : ragStatus ? (
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
          {ragIngestMutation.isError && ragIngestMutation.error ? (
            <p className="memory-debug-err">
              {(() => {
                const u = toUserFacingError(ragIngestMutation.error, t.errors);
                return u.hint ? `${u.banner} ${u.hint}` : u.banner;
              })()}
            </p>
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
          {ragQueryMutation.isError && ragQueryMutation.error ? (
            <p className="memory-debug-err">
              {(() => {
                const u = toUserFacingError(ragQueryMutation.error, t.errors);
                return u.hint ? `${u.banner} ${u.hint}` : u.banner;
              })()}
            </p>
          ) : null}
          {ragQueryMutation.isSuccess && ragQueryMutation.data ? (
            <div
              className="memory-query-results"
              aria-live="polite"
              data-testid="inspector-rag-query-results"
            >
              <p className="memory-query-hits-label">
                {t.inspector.rag.queryHits(ragQueryMutation.data.hit_count)}
              </p>
              {ragQueryMutation.data.hit_count <= 0 ? (
                <p className="panel-note panel-note--muted">{t.inspector.rag.queryEmpty}</p>
              ) : (
                <ul className="memory-query-hit-list">
                  {ragQueryMutation.data.hits.map((hit) => {
                    const metaKeys = Object.keys(hit.metadata || {});
                    return (
                      <li key={hit.id} className="memory-query-hit-item">
                        <pre className="memory-query-hit-doc">{hit.content}</pre>
                        {metaKeys.length > 0 ? (
                          <pre className="memory-query-hit-meta">
                            {t.inspector.rag.hitMetadataLabel}:{"\n"}
                            {JSON.stringify(hit.metadata, null, 2)}
                          </pre>
                        ) : null}
                        {typeof hit.distance === "number" && Number.isFinite(hit.distance) ? (
                          <span className="memory-query-hit-dist">
                            {t.inspector.rag.distanceLabel}: {hit.distance.toFixed(4)}
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
      </div>
    </Modal>
  );
}
