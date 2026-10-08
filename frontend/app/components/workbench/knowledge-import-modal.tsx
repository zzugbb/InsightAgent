"use client";

import { Alert, Button, Input, Modal, Space, Typography } from "antd";
import { useRef, useState } from "react";
import { useMessages } from "../../../lib/preferences-context";
import { RagIngestJobs } from "./rag-ingest-jobs";
import { resolveKnowledgeBaseAccessHint } from "./knowledge-base-governance-modal-utils";
import { KnowledgeImportError, readKnowledgeFiles, validImportKnowledgeBaseId, type ImportDocument } from "./knowledge-import-utils";

export function KnowledgeImportModal({ open, initialKnowledgeBaseId, isAdmin, onClose, onReview }: {
  open: boolean;
  initialKnowledgeBaseId: string;
  isAdmin: boolean;
  onClose: (knowledgeBaseId: string) => void;
  onReview: (knowledgeBaseId: string) => void;
}) {
  const t = useMessages();
  const copy = t.sidebar.knowledgeImport;
  const [knowledgeBaseId, setKnowledgeBaseId] = useState(initialKnowledgeBaseId);
  const [documents, setDocuments] = useState<ImportDocument[]>([]);
  const [reading, setReading] = useState(false);
  const [locked, setLocked] = useState(false);
  const [error, setError] = useState<KnowledgeImportError | null>(null);
  const selection = useRef(0);
  const target = knowledgeBaseId.trim();
  const validTarget = validImportKnowledgeBaseId(target);
  const access = resolveKnowledgeBaseAccessHint({ knowledgeBaseId: target, isAdmin,
    labels: { readOnly: t.sidebar.knowledgeBase.accessSharedReadOnly, admin: t.sidebar.knowledgeBase.accessSharedAdmin } });

  return (
    <Modal title={copy.title} open={open} onCancel={() => onClose(target)} footer={null} width={720}
      closable={!locked} mask={{ closable: !locked }} keyboard={!locked}>
      <Typography.Paragraph type="secondary">{copy.lead}</Typography.Paragraph>
      <label htmlFor="knowledge-import-target">{copy.target}</label>
      <Input id="knowledge-import-target" data-testid="knowledge-import-target" value={knowledgeBaseId}
        disabled={locked} onChange={(event) => setKnowledgeBaseId(event.target.value)} />
      <Typography.Paragraph type="secondary">{copy.targetHint}</Typography.Paragraph>
      {!validTarget ? <Alert type="warning" showIcon title={copy.invalidTarget} /> : null}
      {access ? <Alert type={access.blocksMutations ? "warning" : "info"} showIcon title={access.label} /> : null}
      <div style={{ margin: "16px 0" }}>
        <label htmlFor="knowledge-import-files">{copy.files}</label>
        <input id="knowledge-import-files" data-testid="knowledge-import-files" type="file" multiple
          accept=".txt,.md,.markdown" disabled={locked} style={{ display: "block", maxWidth: "100%", marginTop: 8 }}
          onChange={async (event) => {
            const files = Array.from(event.currentTarget.files ?? []);
            const request = ++selection.current;
            setDocuments([]);
            setError(null);
            if (!files.length) { setReading(false); return; }
            setReading(true);
            try {
              const next = await readKnowledgeFiles(files);
              if (selection.current === request) setDocuments(next);
            } catch (error) {
              if (selection.current === request) setError(error instanceof KnowledgeImportError
                ? error : new KnowledgeImportError("read"));
            } finally {
              if (selection.current === request) setReading(false);
            }
          }} />
      </div>
      {reading ? <p role="status">{copy.reading}</p> : null}
      {error ? <Alert type="error" showIcon data-testid="knowledge-import-file-error"
        title={copy.errors[error.code]} description={error.fileName || undefined} /> : null}
      {documents.length > 0 ? (
        <div data-testid="knowledge-import-preview">
          <Typography.Paragraph>{copy.preview(documents.length)}</Typography.Paragraph>
          <Typography.Paragraph type="secondary">{copy.versionHint}</Typography.Paragraph>
          {documents.map((document) => (
            <details key={document.source} style={{ marginBottom: 12 }}>
              <summary style={{ overflowWrap: "anywhere" }}>{document.source} · {copy.characters(Array.from(document.text).length)}</summary>
              <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: 160, overflow: "auto" }}>
                {document.text.slice(0, 1000)}{document.text.length > 1000 ? "…" : ""}
              </pre>
            </details>
          ))}
        </div>
      ) : null}
      <RagIngestJobs open={open && validTarget} knowledgeBaseId={target} documents={documents}
        disabled={reading || !validTarget || Boolean(access?.blocksMutations)}
        onSubmissionStateChange={setLocked} onReview={onReview} />
      <Space style={{ marginTop: 16 }}>
        <Button disabled={locked} onClick={() => onClose(target)}>{copy.back}</Button>
      </Space>
    </Modal>
  );
}
