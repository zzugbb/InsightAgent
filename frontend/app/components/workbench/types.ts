export type SettingsSummary = {
  mode: string;
  provider: string;
  model: string;
  base_url: string | null;
  api_key_configured: boolean;
  base_url_configured: boolean;
  database_locator: string;
};

/** 与 GET /api/sessions、GET /api/tasks 分页响应一致 */
export type PaginatedList<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

export type SessionSummary = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export type SessionMessage = {
  id: string;
  session_id: string;
  task_id: string | null;
  role: string;
  content: string;
  created_at: string;
};

export type TaskSummary = {
  id: string;
  session_id: string;
  prompt: string;
  status: string;
  status_normalized?: string;
  status_label?: string;
  status_rank?: number;
  trace_json: string | null;
  /** JSON 字符串，与 SSE `done.usage` 同结构（prompt_tokens / completion_tokens / cost_estimate） */
  usage_json?: string | null;
  created_at: string;
  updated_at: string;
};

export type SettingsFormState = {
  mode: string;
  provider: string;
  model: string;
  base_url: string;
  api_key: string;
};

export type SettingsValidateResponse = {
  ok: boolean;
  mode: string;
  provider: string;
  model: string;
  message: string;
  error: string | null;
  error_code?: string | null;
};

export type InspectorTab = "trace" | "context";

/** 与 GET /api/sessions/{id}/memory/status 对齐 */
export type SessionMemoryStatus = {
  collection: string;
  chroma_url: string;
  chroma_reachable: boolean;
  collection_exists: boolean;
  document_count: number;
  error: string | null;
};

/** 与 GET /api/tasks/usage/summary、GET /api/sessions/{id}/usage/summary 对齐 */
export type UsageSummary = {
  tasks_total: number;
  tasks_with_usage: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_estimate: number;
  avg_total_tokens: number | null;
  avg_cost_estimate: number | null;
};

export type SessionUsageSummary = UsageSummary;

export type RagStatus = {
  knowledge_base_id: string;
  collection: string;
  chroma_url: string;
  chroma_reachable: boolean;
  collection_exists: boolean;
  document_count: number;
  error: string | null;
};

export type RagHit = {
  id: string;
  content: string;
  distance: number | null;
  metadata: Record<string, unknown>;
};

export type RagQueryResponse = {
  knowledge_base_id: string;
  collection: string;
  hit_count: number;
  hits: RagHit[];
};

export type RagIngestResponse = {
  knowledge_base_id: string;
  collection: string;
  documents_ingested: number;
  chunks_added: number;
  document_count: number;
  chunk_size: number;
  chunk_overlap: number;
};

export type AuditLogItem = {
  id: string;
  event_type: "login" | "logout" | "refresh" | "settings_update" | string;
  event_detail: Record<string, unknown> | null;
  session_id?: string | null;
  task_id?: string | null;
  created_at: string;
};

export type AuditLogListResponse = {
  items: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

/** POST /api/sessions/{id}/memory/add */
export type MemoryAddResponse = {
  added_id: string;
  document_count: number;
};

/** POST /api/sessions/{id}/memory/query */
export type MemoryQueryResponse = {
  ids: string[][];
  documents: string[][];
  distances: number[][] | null;
  metadatas?: Record<string, unknown>[][] | null;
};
