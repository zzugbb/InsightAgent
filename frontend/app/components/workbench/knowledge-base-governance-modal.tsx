"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, App, Button, Modal, Popconfirm, Space, Table, Tag, Tooltip, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { DatabaseZap, LockKeyhole, RefreshCw, UsersRound } from "lucide-react";

import { apiDeleteJson, apiJson, apiPostJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages } from "../../../lib/preferences-context";

import type {
  RagKnowledgeBaseDocumentMutateResponse,
  RagKnowledgeBaseListResponse,
  RagKnowledgeBaseMutateResponse,
  RagKnowledgeBaseSummary,
} from "./types";
import {
  buildKnowledgeBaseDocumentDeleteUrl,
  resolveKnowledgeBaseAccessHint,
  resolveKnowledgeBaseDocumentGroups,
  resolveKnowledgeBaseGovernanceListState,
  resolveKnowledgeBaseGovernanceOperatorHint,
  resolveKnowledgeBaseVersionRows,
  summarizeKnowledgeBaseVersions,
} from "./knowledge-base-governance-modal-utils";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type KnowledgeBaseGovernanceModalProps = {
  open: boolean;
  onClose: () => void;
  onOpenRag: () => void;
  currentUser?: {
    id: string;
    email: string;
    display_name?: string | null;
    role?: string;
  } | null;
};

type DocumentDeleteArgs = {
  key: string;
  knowledgeBaseId: string;
  source: string;
  documentId: string;
};

export function KnowledgeBaseGovernanceModal({
  open,
  onClose,
  onOpenRag,
  currentUser,
}: KnowledgeBaseGovernanceModalProps) {
  const { message } = App.useApp();
  const t = useMessages();
  const queryClient = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["rag-kb-governance"],
    enabled: open,
    staleTime: 8_000,
    queryFn: () =>
      apiJson<RagKnowledgeBaseListResponse>(
        `${API_BASE_URL}/api/rag/knowledge-bases`,
      ),
  });

  const clearMutation = useMutation({
    mutationFn: (knowledgeBaseId: string) =>
      apiPostJson<RagKnowledgeBaseMutateResponse>(
        `${API_BASE_URL}/api/rag/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/clear`,
        {},
      ),
    onSuccess: (data) => {
      message.success(
        t.sidebar.knowledgeBase.clearDone(data.knowledge_base_id, data.deleted_chunks),
      );
      void queryClient.invalidateQueries({ queryKey: ["rag-kb-governance"] });
      void queryClient.invalidateQueries({ queryKey: ["rag-status"] });
    },
    onError: (error) => {
      const u = toUserFacingError(error, t.errors);
      message.error(`${t.sidebar.knowledgeBase.opFailed}: ${u.banner}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (knowledgeBaseId: string) =>
      apiDeleteJson<RagKnowledgeBaseMutateResponse>(
        `${API_BASE_URL}/api/rag/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}`,
      ),
    onSuccess: (data) => {
      message.success(
        t.sidebar.knowledgeBase.deleteDone(data.knowledge_base_id, data.deleted_chunks),
      );
      void queryClient.invalidateQueries({ queryKey: ["rag-kb-governance"] });
      void queryClient.invalidateQueries({ queryKey: ["rag-status"] });
    },
    onError: (error) => {
      const u = toUserFacingError(error, t.errors);
      message.error(`${t.sidebar.knowledgeBase.opFailed}: ${u.banner}`);
    },
  });

  const documentDeleteMutation = useMutation({
    mutationFn: (args: DocumentDeleteArgs) =>
      apiDeleteJson<RagKnowledgeBaseDocumentMutateResponse>(
        buildKnowledgeBaseDocumentDeleteUrl(
          API_BASE_URL,
          args.knowledgeBaseId,
          args.source,
          args.documentId,
        ),
      ),
    onSuccess: (data) => {
      message.success(
        t.sidebar.knowledgeBase.deleteDocumentDone(
          data.knowledge_base_id,
          data.document_id,
          data.deleted_chunks,
        ),
      );
      void queryClient.invalidateQueries({ queryKey: ["rag-kb-governance"] });
      void queryClient.invalidateQueries({ queryKey: ["rag-status"] });
    },
    onError: (error) => {
      const u = toUserFacingError(error, t.errors);
      message.error(`${t.sidebar.knowledgeBase.opFailed}: ${u.banner}`);
    },
  });

  const rows = listQuery.data?.knowledge_bases ?? [];
  const listState = resolveKnowledgeBaseGovernanceListState({
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,
    rowCount: rows.length,
  });
  const listError = listQuery.isError
    ? toUserFacingError(listQuery.error, t.errors)
    : null;
  const operatorHint = resolveKnowledgeBaseGovernanceOperatorHint({
    listState,
    chromaReachable: listQuery.data?.chroma_reachable ?? null,
    labels: {
      staleData: t.sidebar.knowledgeBase.operatorHintStaleData,
      storageUnreachable:
        t.sidebar.knowledgeBase.operatorHintStorageUnreachable,
      empty: t.sidebar.knowledgeBase.operatorHintEmpty,
    },
  });
  const mutationsBlocked = operatorHint?.blocksMutations ?? false;
  const isAdmin =
    String(currentUser?.role ?? "")
      .trim()
      .toLowerCase() === "admin";
  const resolveAccessHint = (knowledgeBaseId: string) =>
    resolveKnowledgeBaseAccessHint({
      knowledgeBaseId,
      isAdmin,
      labels: {
        readOnly: t.sidebar.knowledgeBase.accessSharedReadOnly,
        admin: t.sidebar.knowledgeBase.accessSharedAdmin,
      },
    });
  const renderVersionDetails = (row: RagKnowledgeBaseSummary) => {
    const versionRows = resolveKnowledgeBaseVersionRows(row.document_versions);
    const documentGroups = resolveKnowledgeBaseDocumentGroups(row.document_versions);
    const summary = summarizeKnowledgeBaseVersions(row.document_versions);
    const accessHint = resolveAccessHint(row.knowledge_base_id);
    return (
      <div
        className="kb-version-details"
        data-testid="kb-version-detail-panel"
      >
        <div className="kb-version-details-header">
          <strong>{t.sidebar.knowledgeBase.versionDetailsTitle}</strong>
          <span>
            {t.sidebar.knowledgeBase.versionSummary(
              summary.versionCount,
              summary.documentCount,
              summary.chunkCount,
            )}
          </span>
        </div>
        <div className="kb-document-group-list">
          {documentGroups.map((group) => (
            <div
              className="kb-document-group-row"
              data-testid="kb-document-group-row"
              key={group.key}
            >
              <span>
                <b>{t.sidebar.knowledgeBase.versionSourceLabel}</b>
                {group.source}
              </span>
              <span>
                <b>{t.sidebar.knowledgeBase.versionDocumentLabel}</b>
                {group.documentId}
              </span>
              <strong>
                {t.sidebar.knowledgeBase.documentGroupSummary(
                  group.versionCount,
                  group.chunkCount,
                )}
              </strong>
              <Popconfirm
                title={t.sidebar.knowledgeBase.deleteDocumentConfirmTitle(
                  group.documentId,
                )}
                description={t.sidebar.knowledgeBase.deleteDocumentConfirmDescription}
                okText={t.sidebar.knowledgeBase.actionDelete}
                cancelText={t.sidebar.deleteSessionCancel}
                okButtonProps={{ danger: true }}
                placement="left"
                onConfirm={() =>
                  documentDeleteMutation.mutate({
                    key: group.key,
                    knowledgeBaseId: row.knowledge_base_id,
                    source: group.source,
                    documentId: group.documentId,
                  })
                }
              >
                <Button
                  size="small"
                  danger
                  type="text"
                  className="kb-action-btn"
                  loading={
                    documentDeleteMutation.isPending &&
                    documentDeleteMutation.variables?.key === group.key
                  }
                  disabled={
                    accessHint?.blocksMutations ||
                    mutationsBlocked ||
                    documentDeleteMutation.isPending
                  }
                  title={
                    accessHint?.blocksMutations
                      ? accessHint.label
                      : mutationsBlocked
                        ? operatorHint?.label
                        : undefined
                  }
                  data-testid="kb-document-group-delete"
                >
                  {t.sidebar.knowledgeBase.actionDeleteDocument}
                </Button>
              </Popconfirm>
            </div>
          ))}
        </div>
        <div className="kb-version-detail-list">
          {versionRows.map((version) => (
            <div
              className="kb-version-detail-row"
              data-testid="kb-version-detail-row"
              key={version.key}
            >
              <span>
                <b>{t.sidebar.knowledgeBase.versionSourceLabel}</b>
                {version.source}
              </span>
              <span>
                <b>{t.sidebar.knowledgeBase.versionDocumentLabel}</b>
                {version.documentId}
              </span>
              <code title={version.version}>{version.versionLabel}</code>
              <span>
                <b>{t.sidebar.knowledgeBase.versionHashLabel}</b>
                <code title={version.contentHash}>
                  {version.contentHashLabel}
                </code>
              </span>
              <span>
                <b>{t.sidebar.knowledgeBase.versionChunksLabel}</b>
                {version.chunkCount.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const columns: ColumnsType<RagKnowledgeBaseSummary> = [
    {
      title: t.sidebar.knowledgeBase.tableKbId,
      dataIndex: "knowledge_base_id",
      width: 220,
      render: (value: string) => {
        const accessHint = resolveAccessHint(value);
        const AccessIcon =
          accessHint?.kind === "shared_readonly" ? LockKeyhole : UsersRound;
        return (
          <div className="kb-id-stack">
            <code className="kb-id-cell">{value}</code>
            {accessHint ? (
              <span
                className={`kb-access-hint kb-access-hint--${accessHint.kind}`}
                data-testid="kb-governance-access-hint"
                title={accessHint.label}
              >
                <AccessIcon size={12} aria-hidden />
                {accessHint.label}
              </span>
            ) : null}
          </div>
        );
      },
    },
    {
      title: t.sidebar.knowledgeBase.tableCollection,
      dataIndex: "collection",
      render: (value: string) => (
        <span className="kb-collection-cell" title={value}>
          {value}
        </span>
      ),
    },
    {
      title: t.sidebar.knowledgeBase.tableDocuments,
      dataIndex: "document_count",
      width: 120,
      render: (value: number) => (
        <span className="kb-count-cell">{value.toLocaleString()}</span>
      ),
    },
    {
      title: t.sidebar.knowledgeBase.tableVersions,
      dataIndex: "unique_document_count",
      width: 150,
      render: (_value: number | undefined, row) => {
        const versions = row.document_versions ?? [];
        const versionCount = row.unique_document_count ?? versions.length;
        const firstVersion = versions[0]?.document_version;
        return (
          <Space direction="vertical" size={0}>
            <span className="kb-count-cell">{versionCount.toLocaleString()}</span>
            {firstVersion ? (
              <Typography.Text
                type="secondary"
                className="kb-version-cell"
                title={firstVersion}
              >
                {firstVersion}
              </Typography.Text>
            ) : null}
          </Space>
        );
      },
    },
    {
      title: t.sidebar.knowledgeBase.tableActions,
      className: "kb-actions-col",
      width: 118,
      render: (_, row) => {
        const accessHint = resolveAccessHint(row.knowledge_base_id);
        const clearBusy =
          clearMutation.isPending && clearMutation.variables === row.knowledge_base_id;
        const deleteBusy =
          deleteMutation.isPending && deleteMutation.variables === row.knowledge_base_id;
        const disabled =
          clearBusy ||
          deleteBusy ||
          Boolean(accessHint?.blocksMutations) ||
          mutationsBlocked;
        const disabledReason = accessHint?.blocksMutations
          ? accessHint.label
          : mutationsBlocked
            ? operatorHint?.label
            : undefined;
        return (
          <div className="kb-row-actions">
            <Popconfirm
              title={t.sidebar.knowledgeBase.clearConfirmTitle(row.knowledge_base_id)}
              description={t.sidebar.knowledgeBase.clearConfirmDescription}
              okText={t.sidebar.knowledgeBase.actionClear}
              cancelText={t.sidebar.deleteSessionCancel}
              placement="left"
              onConfirm={() => clearMutation.mutate(row.knowledge_base_id)}
            >
              <Button
                size="small"
                type="text"
                loading={clearBusy}
                disabled={disabled}
                title={disabledReason}
                className="kb-action-btn"
                data-testid="kb-governance-action-clear"
              >
                {clearBusy
                  ? t.sidebar.knowledgeBase.actioning
                  : t.sidebar.knowledgeBase.actionClear}
              </Button>
            </Popconfirm>
            <Popconfirm
              title={t.sidebar.knowledgeBase.deleteConfirmTitle(row.knowledge_base_id)}
              description={t.sidebar.knowledgeBase.deleteConfirmDescription}
              okText={t.sidebar.knowledgeBase.actionDelete}
              cancelText={t.sidebar.deleteSessionCancel}
              okButtonProps={{ danger: true }}
              placement="left"
              onConfirm={() => deleteMutation.mutate(row.knowledge_base_id)}
            >
              <Button
                size="small"
                danger
                type="text"
                className="kb-action-btn"
                loading={deleteBusy}
                disabled={disabled}
                title={disabledReason}
                data-testid="kb-governance-action-delete"
              >
                {deleteBusy
                  ? t.sidebar.knowledgeBase.actioning
                  : t.sidebar.knowledgeBase.actionDelete}
              </Button>
            </Popconfirm>
          </div>
        );
      },
    },
  ];

  return (
    <Modal
      title={<span id="knowledge-base-governance-title">{t.sidebar.knowledgeBase.title}</span>}
      open={open}
      onCancel={onClose}
      footer={null}
      width={720}
      destroyOnHidden
      className="knowledge-base-governance-ant-modal"
    >
      <Typography.Paragraph className="kb-governance-lead" type="secondary">
        {t.sidebar.knowledgeBase.lead}
      </Typography.Paragraph>

      <div className="kb-governance-topline" data-testid="kb-governance-topline">
        <Space size={10} wrap>
          <Tag
            color={listQuery.data?.chroma_reachable ? "green" : "default"}
            className="kb-governance-status"
          >
            {listQuery.data?.chroma_reachable
              ? t.sidebar.knowledgeBase.statusConnected
              : t.sidebar.knowledgeBase.statusDisconnected}
          </Tag>
          <span className="kb-governance-metric">
            {t.sidebar.knowledgeBase.kbCount(listQuery.data?.knowledge_base_count ?? 0)}
          </span>
        </Space>
        <Tooltip title={t.sidebar.knowledgeBase.refresh}>
          <Button
            size="small"
            type="text"
            className="kb-refresh-btn"
            data-testid="kb-governance-refresh"
            onClick={() => {
              void listQuery.refetch();
            }}
            loading={listQuery.isFetching}
            icon={<RefreshCw size={14} aria-hidden />}
            aria-label={t.sidebar.knowledgeBase.refreshAria}
          />
        </Tooltip>
      </div>

      {listError ? (
        <Alert
          type="error"
          showIcon
          className="kb-governance-load-error"
          data-testid="kb-governance-load-error"
          title={t.sidebar.knowledgeBase.loadFailed}
          description={
            listError.hint
              ? `${listError.banner} ${listError.hint}`
              : listError.banner
          }
          action={
            <Button
              size="small"
              data-testid="kb-governance-load-retry"
              loading={listQuery.isFetching}
              onClick={() => {
                void listQuery.refetch();
              }}
            >
              {t.sidebar.knowledgeBase.refresh}
            </Button>
          }
        />
      ) : null}

      {operatorHint ? (
        <Alert
          type={operatorHint.blocksMutations ? "warning" : "info"}
          showIcon
          className={`kb-governance-operator-hint kb-governance-operator-hint--${operatorHint.kind}`}
          data-testid="kb-governance-operator-hint"
          title={t.sidebar.knowledgeBase.operatorHintTitle}
          description={operatorHint.label}
          action={
            operatorHint.action === "open_rag" ? (
              <Button
                size="small"
                type="primary"
                icon={<DatabaseZap size={14} aria-hidden />}
                data-testid="kb-governance-open-rag"
                onClick={onOpenRag}
              >
                {t.sidebar.knowledgeBase.operatorHintOpenRag}
              </Button>
            ) : undefined
          }
        />
      ) : null}

      {listState !== "error" ? (
        <div className="kb-governance-table-wrap" data-testid="kb-governance-table-wrap">
          <Table<RagKnowledgeBaseSummary>
            size="small"
            rowKey={(row) => row.collection}
            columns={columns}
            dataSource={rows}
            loading={listQuery.isLoading}
            expandable={{
              expandedRowRender: renderVersionDetails,
              rowExpandable: (row) =>
                resolveKnowledgeBaseVersionRows(row.document_versions).length > 0,
            }}
            pagination={false}
            locale={{ emptyText: t.sidebar.knowledgeBase.noKnowledgeBases }}
            scroll={{ x: 560 }}
          />
        </div>
      ) : null}
    </Modal>
  );
}
