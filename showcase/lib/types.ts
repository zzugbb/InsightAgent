/** Public allowlist adapted from frontend/lib/types/trace.ts; no runtime credentials. */
export type TraceStepPayload = {
  id: string;
  seq?: number;
  type: string;
  content: string;
  meta?: {
    step_type?: string;
    plan_node_id?: string;
    depends_on?: string[];
    agent_round?: number;
    agent_decision?: string;
    agent_from_step_ids?: string[];
    agent_stop_reason?: string;
    provider_finish_reason?: string;
    planning_provider_used?: boolean;
    planning_provider_attempted?: boolean;
    parallel_group_id?: string;
    model?: string;
    label?: string;
    latency?: number;
    tokens?: number | null;
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    tool?: {
      name: string;
      label?: string;
      input?: unknown;
      output_preview?: unknown;
      result_summary?: string;
      status: string;
      error?: string;
    };
    rag?: {
      chunks?: string[];
      knowledge_base_id?: string;
      chunk_metadata?: Array<{
        source?: string;
        document_version?: string;
        document_id?: string;
        content_hash?: string;
      }>;
      document_versions?: Array<{
        source?: string;
        document_version?: string;
        content_hash?: string;
      }>;
    };
    error_event?: { code?: string; message?: string; detail?: string };
  };
};
export type Run = {
  id: string;
  title: string;
  prompt: string;
  source: "real_model" | "controlled_fixture";
  model: string;
  status: string;
  answer: string;
  steps: TraceStepPayload[];
  elapsedSeconds: number;
  preparedAt: string;
  sourceCommit: string;
  parentId: string | null;
  usage: {
    planning_total_tokens: number | null;
    total_tokens: number | null;
    overall_total_tokens: number | null;
  } | null;
};
