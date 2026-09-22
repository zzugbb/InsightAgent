"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Input } from "antd";
import { useState } from "react";

import { apiJson, apiPostJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages } from "../../../lib/preferences-context";

import type {
  MemoryAddResponse,
  MemoryQueryResponse,
  SessionMemoryStatus,
} from "./types";
import { API_BASE_URL, parseMemoryMetadataJson } from "./utils";

const { TextArea } = Input;

type RuntimeDebugMemorySectionProps = {
  open: boolean;
  activeSessionId: string | null;
};

export function RuntimeDebugMemorySection({
  open,
  activeSessionId,
}: RuntimeDebugMemorySectionProps) {
  const t = useMessages();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [memoryAddDraft, setMemoryAddDraft] = useState("");
  const [memoryMetaDraft, setMemoryMetaDraft] = useState("");
  const [memoryQueryDraft, setMemoryQueryDraft] = useState("");

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

  return (
    <div className="runtime-debug-section">
      <p className="summary-label">{t.inspector.memory.kicker}</p>
      <strong className="memory-placeholder-title">
        {t.inspector.memory.title}
      </strong>
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
          <p className="memory-status-loading">
            {t.inspector.memory.statusLoading}
          </p>
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
          <p className="memory-debug-kicker">
            {t.inspector.memory.debugKicker}
          </p>
          <TextArea
            className="memory-debug-textarea"
            value={memoryAddDraft}
            onChange={(event) => setMemoryAddDraft(event.target.value)}
            placeholder={t.inspector.memory.addPlaceholder}
            rows={2}
            disabled={memoryAddMutation.isPending}
          />
          <TextArea
            className="memory-debug-textarea memory-debug-textarea--meta"
            value={memoryMetaDraft}
            onChange={(event) => setMemoryMetaDraft(event.target.value)}
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
                const error = toUserFacingError(
                  memoryAddMutation.error,
                  t.errors,
                );
                return error.hint
                  ? `${error.banner} ${error.hint}`
                  : error.banner;
              })()}
            </p>
          ) : null}
          <TextArea
            className="memory-debug-textarea memory-debug-textarea--query"
            value={memoryQueryDraft}
            onChange={(event) => setMemoryQueryDraft(event.target.value)}
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
                const error = toUserFacingError(
                  memoryQueryMutation.error,
                  t.errors,
                );
                return error.hint
                  ? `${error.banner} ${error.hint}`
                  : error.banner;
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
                <p className="panel-note panel-note--muted">
                  {t.inspector.memory.queryEmpty}
                </p>
              ) : (
                <ul className="memory-query-hit-list">
                  {memoryQueryMutation.data.documents[0]?.map((doc, index) => {
                    const id =
                      memoryQueryMutation.data?.ids[0]?.[index] ?? String(index);
                    const distance =
                      memoryQueryMutation.data?.distances?.[0]?.[index];
                    const metadata =
                      memoryQueryMutation.data?.metadatas?.[0]?.[index];
                    const metadataKeys =
                      metadata &&
                      typeof metadata === "object" &&
                      metadata !== null
                        ? Object.keys(metadata as Record<string, unknown>)
                        : [];
                    return (
                      <li key={id} className="memory-query-hit-item">
                        <pre className="memory-query-hit-doc">{doc}</pre>
                        {metadataKeys.length > 0 ? (
                          <pre className="memory-query-hit-meta">
                            {t.inspector.memory.hitMetadataLabel}:{"\n"}
                            {JSON.stringify(
                              metadata as Record<string, unknown>,
                              null,
                              2,
                            )}
                          </pre>
                        ) : null}
                        {typeof distance === "number" &&
                        Number.isFinite(distance) ? (
                          <span className="memory-query-hit-dist">
                            {t.inspector.memory.distanceLabel}:{" "}
                            {distance.toFixed(4)}
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
  );
}
