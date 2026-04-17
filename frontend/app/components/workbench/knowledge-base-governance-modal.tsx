"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Modal, Popconfirm, Space, Table, Tag, Tooltip, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

import { apiDeleteJson, apiJson, apiPostJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages } from "../../../lib/preferences-context";

import type {
  RagKnowledgeBaseListResponse,
  RagKnowledgeBaseMutateResponse,
  RagKnowledgeBaseSummary,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type KnowledgeBaseGovernanceModalProps = {
  open: boolean;
  onClose: () => void;
};

function formatSourceTags(
  row: RagKnowledgeBaseSummary,
  labels: {
    noSource: string;
    sourceUnknown: (n: number) => string;
  },
): ReactNode {
  const known = row.top_sources ?? [];
  const tags: ReactNode[] = [];
  if (known.length > 0) {
    known.slice(0, 4).forEach((source) => {
      tags.push(
        <Tooltip
          key={`${row.collection}-${source.source}`}
          title={source.source}
          placement="topLeft"
        >
          <Tag className="kb-source-tag">
            {source.source} ({source.sampled_count})
          </Tag>
        </Tooltip>,
      );
    });
  }
  if (row.source_unknown_count > 0) {
    tags.push(
      <Tag key={`${row.collection}-unknown`} className="kb-source-tag kb-source-tag--muted">
        {labels.sourceUnknown(row.source_unknown_count)}
      </Tag>,
    );
  }
  if (tags.length === 0) {
    return <span className="kb-source-empty">{labels.noSource}</span>;
  }
  return <div className="kb-source-tags">{tags}</div>;
}

export function KnowledgeBaseGovernanceModal({
  open,
  onClose,
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

  const rows = listQuery.data?.knowledge_bases ?? [];
  const sampleSize = rows.reduce(
    (max, row) => Math.max(max, row.source_sample_size),
    0,
  );

  const columns: ColumnsType<RagKnowledgeBaseSummary> = [
    {
      title: t.sidebar.knowledgeBase.tableKbId,
      dataIndex: "knowledge_base_id",
      width: 180,
      render: (value: string) => <code className="kb-id-cell">{value}</code>,
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
      title: t.sidebar.knowledgeBase.tableSources,
      width: 300,
      render: (_, row) =>
        formatSourceTags(row, {
          noSource: t.sidebar.knowledgeBase.noSource,
          sourceUnknown: t.sidebar.knowledgeBase.sourceUnknown,
        }),
    },
    {
      title: t.sidebar.knowledgeBase.tableActions,
      width: 150,
      render: (_, row) => {
        const clearBusy =
          clearMutation.isPending && clearMutation.variables === row.knowledge_base_id;
        const deleteBusy =
          deleteMutation.isPending && deleteMutation.variables === row.knowledge_base_id;
        const disabled = clearBusy || deleteBusy;
        return (
          <Space size={8} className="kb-row-actions">
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
                loading={clearBusy}
                disabled={disabled}
                className="kb-action-btn"
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
                className="kb-action-btn"
                loading={deleteBusy}
                disabled={disabled}
              >
                {deleteBusy
                  ? t.sidebar.knowledgeBase.actioning
                  : t.sidebar.knowledgeBase.actionDelete}
              </Button>
            </Popconfirm>
          </Space>
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
      width={980}
      destroyOnHidden
      className="knowledge-base-governance-ant-modal"
    >
      <Typography.Paragraph className="kb-governance-lead" type="secondary">
        {t.sidebar.knowledgeBase.lead}
      </Typography.Paragraph>

      <div className="kb-governance-topline">
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
          {sampleSize > 0 ? (
            <span className="kb-governance-metric kb-governance-metric--muted">
              {t.sidebar.knowledgeBase.sourceSampleHint(sampleSize)}
            </span>
          ) : null}
        </Space>

        <Tooltip title={t.sidebar.knowledgeBase.refresh}>
          <Button
            size="small"
            className="kb-refresh-btn"
            onClick={() => {
              void listQuery.refetch();
            }}
            loading={listQuery.isFetching}
            icon={<RefreshCw size={14} aria-hidden />}
            aria-label={t.sidebar.knowledgeBase.refreshAria}
          />
        </Tooltip>
      </div>
      {sampleSize > 0 ? (
        <p className="kb-governance-sample-note">
          {t.sidebar.knowledgeBase.sourceSampleExplain(sampleSize)}
        </p>
      ) : null}

      <div className="kb-governance-table-wrap">
        <Table<RagKnowledgeBaseSummary>
          size="small"
          rowKey={(row) => row.collection}
          columns={columns}
          dataSource={rows}
          loading={listQuery.isLoading}
          pagination={false}
          locale={{ emptyText: t.sidebar.knowledgeBase.noKnowledgeBases }}
          scroll={{ x: 860 }}
        />
      </div>
    </Modal>
  );
}
