"use client";

import { Alert, App, Button, Modal, Select, Space, Typography } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiJson, apiPostJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages } from "../../../lib/preferences-context";
import { ACTIVE_WORKBENCH_SESSION_STORAGE_KEY } from "../../../lib/storage-keys";
import type { TaskSummary } from "../../components/workbench/types";
import { API_BASE_URL } from "../../components/workbench/utils";

type Candidate = { step_id: string; index: number; tool_name: string; reused_steps: number };
type ResumeInput = { idempotency_key: string; checkpoint_step_id: string };
const terminal = new Set(["completed", "failed", "cancelled", "timed_out"]);

export function TaskCheckpointPanel({ task }: { task: TaskSummary }) {
  const t = useMessages();
  const copy = t.taskDetail.checkpoint;
  const { message } = App.useApp();
  const router = useRouter();
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<string>();
  const allowed = terminal.has(task.status_normalized ?? task.status);
  const candidates = useQuery({
    queryKey: ["task-checkpoints", task.id],
    queryFn: () => apiJson<{ items: Candidate[] }>(`${API_BASE_URL}/api/tasks/${encodeURIComponent(task.id)}/checkpoints`),
    enabled: allowed,
  });
  const submit = useMutation({
    mutationFn: (input: ResumeInput) => apiPostJson<{ session_id: string }>(
      `${API_BASE_URL}/api/tasks/${encodeURIComponent(task.id)}/reruns`, input,
    ),
    onSuccess: (branch) => {
      void client.invalidateQueries({ queryKey: ["sessions"] });
      void client.invalidateQueries({ queryKey: ["tasks"] });
      void client.invalidateQueries({ queryKey: ["task-reruns", task.id] });
      try { localStorage.setItem(ACTIVE_WORKBENCH_SESSION_STORAGE_KEY, branch.session_id); }
      catch { message.warning(t.taskDetail.rerun.openManually); }
      setOpen(false);
      router.push("/");
    },
  });
  const options = candidates.data?.items ?? [];
  const chosen = options.find((item) => item.step_id === selected);
  return (
    <section className="inspector-block" data-testid="task-checkpoint-panel">
      <Space wrap style={{ width: "100%", justifyContent: "space-between" }}>
        <Typography.Text strong>{copy.title}</Typography.Text>
        <Button size="small" data-testid="task-checkpoint-open" disabled={!allowed || options.length === 0} onClick={() => {
          setSelected(options.at(-1)?.step_id);
          submit.reset();
          setOpen(true);
        }}>{copy.create}</Button>
      </Space>
      <p className="panel-note">{copy.scope}</p>
      {!allowed ? <p className="panel-note">{t.taskDetail.rerun.waitForTerminal}</p> : null}
      {allowed && candidates.isPending ? <p>{t.taskDetail.loading}</p> : null}
      {allowed && candidates.data && options.length === 0 ? <p className="panel-note">{copy.unavailable}</p> : null}
      {candidates.error ? <Alert type="warning" showIcon title={copy.loadFailed}
        description={toUserFacingError(candidates.error, t.errors).banner}
        action={<Button size="small" loading={candidates.isFetching} onClick={() => { void candidates.refetch(); }}>{t.taskDetail.rerun.retry}</Button>} /> : null}
      <Modal open={open} title={copy.title} mask={{ closable: false }}
        onCancel={() => { if (!submit.isPending) setOpen(false); }}
        okText={submit.isError ? t.taskDetail.rerun.retry : t.taskDetail.rerun.run}
        cancelText={t.taskDetail.rerun.cancel} confirmLoading={submit.isPending}
        cancelButtonProps={{ disabled: submit.isPending }}
        okButtonProps={{ disabled: !allowed || !chosen, "data-testid": "task-checkpoint-confirm" }}
        onOk={() => {
          if (submit.isError && submit.variables) submit.mutate(submit.variables);
          else if (selected) submit.mutate({ idempotency_key: crypto.randomUUID(), checkpoint_step_id: selected });
        }}>
        <p>{copy.explanation}</p>
        <Select value={selected} onChange={setSelected} style={{ width: "100%" }} aria-label={copy.step}
          data-testid="task-checkpoint-select" disabled={submit.isPending || submit.isError}
          options={options.map((item) => ({ value: item.step_id, label: `${item.index}. ${item.tool_name}` }))} />
        {chosen ? <p>{copy.reuse(chosen.reused_steps)}</p> : null}
        {submit.error ? <Alert type="error" showIcon title={t.taskDetail.rerun.submitFailed}
          description={toUserFacingError(submit.error, t.errors).banner} /> : null}
      </Modal>
    </section>
  );
}
