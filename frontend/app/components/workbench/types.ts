export type SettingsSummary = {
  mode: string;
  provider: string;
  model: string;
  api_key_configured: boolean;
  base_url_configured: boolean;
  sqlite_path: string;
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
  trace_json: string | null;
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
