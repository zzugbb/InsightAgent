"use client";

import { Alert, App, Button, Input, Modal, Pagination, Space, Typography } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiJson, apiPostJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages } from "../../../lib/preferences-context";
import { ACTIVE_WORKBENCH_SESSION_STORAGE_KEY } from "../../../lib/storage-keys";
import type { TaskSummary } from "../../components/workbench/types";
import { API_BASE_URL, shortenId } from "../../components/workbench/utils";

type Branch = { task_id: string; session_id: string; status: string; created_at: string };
type Lineage = { is_rerun: boolean; parent_task_id: string | null; items: Branch[]; total: number };
type RerunInput = { idempotency_key: string; user_input: string };
const terminal = new Set(["completed", "failed", "cancelled", "timed_out"]);

export function TaskRerunPanel({ task }: { task: TaskSummary }) {
  const t = useMessages();
  const copy = t.taskDetail.rerun;
  const { message } = App.useApp();
  const router = useRouter();
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState(task.prompt);
  const [page, setPage] = useState(1);
  const allowed = terminal.has(task.status_normalized ?? task.status);
  const lineage = useQuery({
    queryKey: ["task-reruns", task.id, page],
    queryFn: () => apiJson<Lineage>(`${API_BASE_URL}/api/tasks/${encodeURIComponent(task.id)}/reruns?limit=10&offset=${(page - 1) * 10}`),
  });
  const submit = useMutation({
    mutationFn: (input: RerunInput) => apiPostJson<Branch>(
      `${API_BASE_URL}/api/tasks/${encodeURIComponent(task.id)}/reruns`, input,
    ),
    onSuccess: (branch) => {
      void client.invalidateQueries({ queryKey: ["sessions"] });
      void client.invalidateQueries({ queryKey: ["tasks"] });
      try {
        localStorage.setItem(ACTIVE_WORKBENCH_SESSION_STORAGE_KEY, branch.session_id);
      } catch {
        message.warning(copy.openManually);
      }
      setOpen(false);
      router.push("/");
    },
    onSettled: () => { void client.invalidateQueries({ queryKey: ["task-reruns", task.id] }); },
  });

  return (
    <section className="inspector-block" data-testid="task-rerun-panel">
      <Space wrap style={{ width: "100%", justifyContent: "space-between" }}>
        <Typography.Text strong>{copy.title}</Typography.Text>
        <Button size="small" data-testid="task-rerun-open" disabled={!allowed} onClick={() => {
          setPrompt(task.prompt);
          submit.reset();
          setOpen(true);
        }}>{copy.create}</Button>
      </Space>
      {!allowed ? <p className="panel-note">{copy.waitForTerminal}</p> : null}
      {lineage.error ? <Alert type="warning" showIcon title={copy.loadFailed}
        description={toUserFacingError(lineage.error, t.errors).banner}
        action={<Button size="small" loading={lineage.isFetching} onClick={() => { void lineage.refetch(); }}>{copy.retry}</Button>} /> : null}
      {lineage.data?.is_rerun ? <p className="panel-note">
        {lineage.data.parent_task_id ? <Link data-testid="task-rerun-parent"
          href={`/tasks/${encodeURIComponent(lineage.data.parent_task_id)}`}>{copy.parent} · {shortenId(lineage.data.parent_task_id)}</Link>
          : copy.parentRemoved}
      </p> : null}
      {lineage.isPending ? <p>{t.taskDetail.loading}</p> : null}
      {lineage.data?.total === 0 ? <p className="panel-note">{copy.empty}</p> : null}
      {lineage.data?.items.map((branch) => <p key={branch.task_id} className="panel-note">
        <Link href={`/tasks/${encodeURIComponent(branch.task_id)}`} data-testid={`task-rerun-child-${branch.task_id}`}>
          {copy.branch} · {shortenId(branch.task_id)}
        </Link>
        {" · "}{new Date(branch.created_at).toLocaleString()}
      </p>)}
      {(lineage.data?.total ?? 0) > 10 ? <Pagination size="small" current={page} pageSize={10}
        total={lineage.data?.total} showSizeChanger={false} onChange={setPage} /> : null}
      <Modal open={open} title={copy.create} mask={{ closable: false }} onCancel={() => {
        if (!submit.isPending) setOpen(false);
      }} okText={submit.isError ? copy.retry : copy.run} cancelText={copy.cancel}
        confirmLoading={submit.isPending} cancelButtonProps={{ disabled: submit.isPending }}
        okButtonProps={{ disabled: !allowed || !prompt.trim(), "data-testid": "task-rerun-confirm" }}
        onOk={() => {
          if (submit.isError && submit.variables) submit.mutate(submit.variables);
          else submit.mutate({ idempotency_key: crypto.randomUUID(), user_input: prompt.trim() });
        }}>
        <p>{copy.explanation}</p>
        <Input.TextArea value={prompt} onChange={(event) => setPrompt(event.target.value)}
          disabled={submit.isPending || submit.isError} maxLength={64_000} showCount
          autoSize={{ minRows: 3, maxRows: 8 }} aria-label={copy.input} data-testid="task-rerun-input" />
        {submit.error ? <Alert style={{ marginTop: 24 }} type="error" showIcon title={copy.submitFailed}
          description={toUserFacingError(submit.error, t.errors).banner} /> : null}
      </Modal>
    </section>
  );
}
