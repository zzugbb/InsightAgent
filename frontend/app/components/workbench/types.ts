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
