/**
 * 与 `.cursor/plans` 中 TraceStep 契约及后端 SSE `trace` 事件对齐。
 * `type` 三大类便于 Flow；细分子类走 `meta.step_type`。
 */
export type TraceStepKind =
  | "thought"
  | "action"
  | "observation"
  /** 显式类型或与 meta.tool / meta.rag 联用 */
  | "tool"
  | "rag";

export type TraceStepMeta = {
  model?: string;
  step_type?: string;
  tool?: {
    name: string;
    input?: unknown;
    output?: unknown;
    status: "running" | "done" | "error";
    retry_count?: number;
    error?: string | null;
  };
  rag?: { chunks: string[]; knowledge_base_id?: string };
  memory?: string[];
  latency?: number;
  tokens?: number | null;
  cost_estimate?: number | null;
  retryCount?: number;
  prompt?: string;
  /** 扩展：自定义展示标题 */
  label?: string;
};

export type TraceStepPayload = {
  id: string;
  type: TraceStepKind | string;
  content: string;
  /** 与 SQLite / delta 游标对齐的序号，缺省时由索引推导 */
  seq?: number;
  meta?: TraceStepMeta;
};
