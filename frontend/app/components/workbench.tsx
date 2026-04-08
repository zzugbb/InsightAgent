"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  type TraceStepPayload,
  useChatStreamStore,
  type ChatStreamStore,
} from "../../lib/stores/chat-stream-store";

type SettingsSummary = {
  mode: string;
  provider: string;
  model: string;
  api_key_configured: boolean;
  base_url_configured: boolean;
  sqlite_path: string;
};

type SessionSummary = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

type SessionMessage = {
  id: string;
  session_id: string;
  task_id: string | null;
  role: string;
  content: string;
  created_at: string;
};

type TaskSummary = {
  id: string;
  session_id: string;
  prompt: string;
  status: string;
  trace_json: string | null;
  created_at: string;
  updated_at: string;
};

type ChatResponse = {
  content: string;
  provider: string;
  model: string;
  mode: string;
  session_id: string;
  task_id: string;
};

type SettingsFormState = {
  mode: string;
  provider: string;
  model: string;
  base_url: string;
  api_key: string;
};

const DEFAULT_SETTINGS: SettingsFormState = {
  mode: "mock",
  provider: "mock",
  model: "mock-gpt",
  base_url: "",
  api_key: "",
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function Workbench() {
  const [settingsForm, setSettingsForm] =
    useState<SettingsFormState>(DEFAULT_SETTINGS);
  const [settingsSummary, setSettingsSummary] = useState<SettingsSummary | null>(
    null,
  );
  const [settingsMessage, setSettingsMessage] = useState<string>(
    "Loading settings...",
  );
  const [recentSessions, setRecentSessions] = useState<SessionSummary[]>([]);
  const [sessionsMessage, setSessionsMessage] = useState("Loading recent sessions...");
  const [recentTasks, setRecentTasks] = useState<TaskSummary[]>([]);
  const [tasksMessage, setTasksMessage] = useState("Loading recent tasks...");
  const [sessionMessages, setSessionMessages] = useState<SessionMessage[]>([]);
  const [messagesMessage, setMessagesMessage] = useState(
    "Select a session to inspect persisted messages.",
  );
  const [chatPrompt, setChatPrompt] = useState("");
  const [chatResult, setChatResult] = useState<ChatResponse | null>(null);
  const [chatMessage, setChatMessage] = useState(
    "JSON chat is kept only as a minimal non-stream debug entry.",
  );
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isChatting, setIsChatting] = useState(false);

  const isStreaming = useChatStreamStore((s: ChatStreamStore) => s.isStreaming);
  const sseTokens = useChatStreamStore((s: ChatStreamStore) => s.sseTokens);
  const sseTraceSteps = useChatStreamStore((s: ChatStreamStore) => s.sseTraceSteps);
  const ssePhase = useChatStreamStore((s: ChatStreamStore) => s.ssePhase);
  const sseTaskId = useChatStreamStore((s: ChatStreamStore) => s.sseTaskId);
  const sseMessage = useChatStreamStore((s: ChatStreamStore) => s.sseMessage);
  const traceCursor = useChatStreamStore((s: ChatStreamStore) => s.traceCursor);
  const runTaskStream = useChatStreamStore((s: ChatStreamStore) => s.runTaskStream);
  const loadPersistedTrace = useChatStreamStore(
    (s: ChatStreamStore) => s.loadPersistedTrace,
  );
  const loadTraceDelta = useChatStreamStore((s: ChatStreamStore) => s.loadTraceDelta);

  useEffect(() => {
    void loadSettings();
    void loadSessions();
    void loadTasks();
  }, []);

  useEffect(() => {
    void loadSessions();
    void loadTasks();
  }, [activeSessionId]);

  useEffect(() => {
    if (!activeSessionId) {
      setSessionMessages([]);
      setMessagesMessage("Select a session to inspect persisted messages.");
      return;
    }
    void loadSessionMessages(activeSessionId);
  }, [activeSessionId]);

  async function loadSettings() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`Failed to load settings (${response.status})`);
      }
      const data = (await response.json()) as SettingsSummary;
      setSettingsSummary(data);
      setSettingsForm({
        mode: data.mode,
        provider: data.provider,
        model: data.model,
        base_url: "",
        api_key: "",
      });
      setSettingsMessage("Settings loaded from backend.");
    } catch (error) {
      setSettingsMessage(
        error instanceof Error ? error.message : "Failed to load settings.",
      );
    }
  }

  async function loadSessions() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sessions?limit=8`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`Failed to load sessions (${response.status})`);
      }
      const data = (await response.json()) as { items: SessionSummary[] };
      setRecentSessions(Array.isArray(data.items) ? data.items : []);
      setSessionsMessage(
        Array.isArray(data.items) && data.items.length > 0
          ? "Recent sessions loaded."
          : "No persisted sessions yet.",
      );
    } catch (error) {
      setSessionsMessage(
        error instanceof Error ? error.message : "Failed to load sessions.",
      );
    }
  }

  async function loadSessionMessages(sessionId: string) {
    try {
      setMessagesMessage("Loading session messages...");
      const response = await fetch(
        `${API_BASE_URL}/api/sessions/${sessionId}/messages`,
        {
          cache: "no-store",
        },
      );
      if (!response.ok) {
        throw new Error(`Failed to load messages (${response.status})`);
      }
      const data = (await response.json()) as {
        messages?: SessionMessage[];
      };
      const messages = Array.isArray(data.messages) ? data.messages : [];
      setSessionMessages(messages);
      setMessagesMessage(
        messages.length > 0
          ? "Persisted session messages loaded."
          : "No persisted messages in this session yet.",
      );
    } catch (error) {
      setSessionMessages([]);
      setMessagesMessage(
        error instanceof Error ? error.message : "Failed to load session messages.",
      );
    }
  }

  async function loadTasks() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/tasks?limit=8`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`Failed to load tasks (${response.status})`);
      }
      const data = (await response.json()) as { items: TaskSummary[] };
      setRecentTasks(Array.isArray(data.items) ? data.items : []);
      setTasksMessage(
        Array.isArray(data.items) && data.items.length > 0
          ? "Recent tasks loaded."
          : "No persisted tasks yet.",
      );
    } catch (error) {
      setTasksMessage(
        error instanceof Error ? error.message : "Failed to load tasks.",
      );
    }
  }

  async function handleSaveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setSettingsMessage("Saving settings...");

    try {
      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          mode: settingsForm.mode,
          provider: settingsForm.provider,
          model: settingsForm.model,
          base_url: settingsForm.base_url || null,
          api_key: settingsForm.api_key || null,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `Failed to save settings (${response.status})`);
      }

      const data = (await response.json()) as SettingsSummary;
      setSettingsSummary(data);
      setSettingsMessage("Settings saved.");
      setSettingsForm((current) => ({
        ...current,
        api_key: "",
      }));
    } catch (error) {
      setSettingsMessage(
        error instanceof Error ? error.message : "Failed to save settings.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSendChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!chatPrompt.trim()) {
      setChatMessage("Prompt cannot be empty.");
      return;
    }

    setIsChatting(true);
    setChatMessage("Sending prompt...");

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prompt: chatPrompt,
          session_id: activeSessionId,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `Chat failed (${response.status})`);
      }

      const data = (await response.json()) as ChatResponse;
      setChatResult(data);
      setActiveSessionId(data.session_id);
      setChatMessage("JSON debug request completed.");
    } catch (error) {
      setChatMessage(
        error instanceof Error ? error.message : "Failed to send prompt.",
      );
    } finally {
      setIsChatting(false);
    }
  }

  function handleSendTaskStream() {
    void runTaskStream({
      apiBaseUrl: API_BASE_URL,
      prompt: chatPrompt,
      sessionId: activeSessionId,
      onSessionResolved: setActiveSessionId,
    });
  }

  function handleLoadPersistedTrace() {
    const taskId = sseTaskId ?? chatResult?.task_id ?? "";
    void loadPersistedTrace(API_BASE_URL, taskId);
  }

  function handleLoadTraceDelta() {
    const taskId = sseTaskId ?? chatResult?.task_id ?? "";
    void loadTraceDelta(API_BASE_URL, taskId);
  }

  return (
    <main className="page-shell">
      <section className="hero-card">
        <p className="eyebrow">InsightAgent</p>
        <h1>Frontend W1 Workbench</h1>
        <p className="lead">
          当前以 Task Stream 为主链路；JSON chat 仅保留为最小非流式调试入口。Task
          Stream（token / trace）当前经由
          <code>POST /api/tasks</code> + <code>GET /api/tasks/{"{id}"}/stream</code>
          进入 Zustand（<code>useChatStreamStore</code>）。尚未接入 React Flow。
        </p>
      </section>

      <section className="workbench-grid">
        <form className="panel-card" onSubmit={handleSaveSettings}>
          <div className="panel-head">
            <h2>Settings</h2>
            <p>{settingsMessage}</p>
          </div>

          <label className="field">
            <span>Mode</span>
            <select
              value={settingsForm.mode}
              onChange={(event) =>
                setSettingsForm((current) => ({
                  ...current,
                  mode: event.target.value,
                }))
              }
            >
              <option value="mock">mock</option>
              <option value="remote">remote</option>
            </select>
          </label>

          <label className="field">
            <span>Provider</span>
            <input
              value={settingsForm.provider}
              onChange={(event) =>
                setSettingsForm((current) => ({
                  ...current,
                  provider: event.target.value,
                }))
              }
              placeholder="mock"
            />
          </label>

          <label className="field">
            <span>Model</span>
            <input
              value={settingsForm.model}
              onChange={(event) =>
                setSettingsForm((current) => ({
                  ...current,
                  model: event.target.value,
                }))
              }
              placeholder="mock-gpt"
            />
          </label>

          <label className="field">
            <span>Base URL</span>
            <input
              value={settingsForm.base_url}
              onChange={(event) =>
                setSettingsForm((current) => ({
                  ...current,
                  base_url: event.target.value,
                }))
              }
              placeholder="Optional"
            />
          </label>

          <label className="field">
            <span>API Key</span>
            <input
              type="password"
              value={settingsForm.api_key}
              onChange={(event) =>
                setSettingsForm((current) => ({
                  ...current,
                  api_key: event.target.value,
                }))
              }
              placeholder={settingsSummary?.api_key_configured ? "Configured" : "Optional in mock mode"}
            />
          </label>

          <button className="action-button" disabled={isSaving} type="submit">
            {isSaving ? "Saving..." : "Save Settings"}
          </button>

          {settingsSummary ? (
            <div className="meta-block">
              <p>Configured mode: {settingsSummary.mode}</p>
              <p>Configured provider: {settingsSummary.provider}</p>
              <p>Configured model: {settingsSummary.model}</p>
              <p>API key configured: {settingsSummary.api_key_configured ? "yes" : "no"}</p>
            </div>
          ) : null}
        </form>

        <form className="panel-card" onSubmit={handleSendChat}>
          <div className="panel-head">
            <h2>Debug & Stream</h2>
            <p>{chatMessage}</p>
          </div>

          <label className="field">
            <span>Prompt</span>
            <textarea
              value={chatPrompt}
              onChange={(event) => setChatPrompt(event.target.value)}
              placeholder="Ask the mock agent something..."
              rows={7}
            />
          </label>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
            <button className="action-button" disabled={isChatting} type="submit">
              {isChatting ? "Sending..." : "Send JSON Debug"}
            </button>
            <button
              className="action-button"
              disabled={isStreaming || isChatting}
              type="button"
              onClick={handleSendTaskStream}
            >
              {isStreaming ? "Streaming..." : "Send Task Stream"}
            </button>
            <button
              className="action-button"
              disabled={isStreaming || isChatting || (!sseTaskId && !chatResult?.task_id)}
              type="button"
              onClick={handleLoadPersistedTrace}
            >
              Load Persisted Trace
            </button>
            <button
              className="action-button"
              disabled={isStreaming || isChatting || (!sseTaskId && !chatResult?.task_id)}
              type="button"
              onClick={handleLoadTraceDelta}
            >
              Load Trace Delta
            </button>
          </div>

          <div className="meta-block">
            <p className="result-label" style={{ marginBottom: "8px" }}>
              Task Stream
            </p>
            <p style={{ margin: "0 0 8px", color: "var(--muted)", lineHeight: 1.6 }}>
              {sseMessage}
            </p>
            {sseTaskId ? (
              <p style={{ margin: "0 0 8px", color: "var(--muted)", wordBreak: "break-word" }}>
                task_id: {sseTaskId}
                {ssePhase ? ` · phase: ${ssePhase}` : ""}
                {traceCursor > 0 ? ` · cursor: ${traceCursor}` : ""}
              </p>
            ) : null}
            {sseTokens ? (
              <div className="result-card" style={{ marginTop: "12px" }}>
                <p className="result-label">Token stream (delta 拼接)</p>
                <p className="result-content" style={{ whiteSpace: "pre-wrap" }}>
                  {sseTokens}
                </p>
              </div>
            ) : null}
            {sseTraceSteps.length > 0 ? (
              <div className="result-card" style={{ marginTop: "12px" }}>
                <p className="result-label">Trace steps</p>
                <ul style={{ margin: "8px 0 0", paddingLeft: "1.2rem", lineHeight: 1.7 }}>
                  {sseTraceSteps.map((step: TraceStepPayload) => (
                    <li key={step.id}>
                      <strong>{step.type}</strong>{" "}
                      <span style={{ color: "var(--muted)", fontSize: "0.85em" }}>
                        ({step.id.slice(0, 8)}…)
                      </span>
                      {typeof step.seq === "number" ? (
                        <span style={{ color: "var(--muted)" }}> · seq {step.seq}</span>
                      ) : null}
                      {step.meta?.step_type != null ? (
                        <span style={{ color: "var(--muted)" }}>
                          {" "}
                          · {String(step.meta.step_type)}
                        </span>
                      ) : null}
                      {step.content ? (
                        <div style={{ marginTop: "4px", whiteSpace: "pre-wrap" }}>
                          {step.content}
                        </div>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>

          {chatResult ? (
            <div className="result-card">
              <p className="result-label">JSON Debug Response</p>
              <p className="result-content">{chatResult.content}</p>
              <div className="meta-block">
                <p>session_id: {chatResult.session_id}</p>
                <p>task_id: {chatResult.task_id}</p>
                <p>provider: {chatResult.provider}</p>
                <p>model: {chatResult.model}</p>
              </div>
            </div>
          ) : null}
        </form>

        <section className="panel-card">
          <div className="panel-head">
            <h2>Recent Sessions</h2>
            <p>{sessionsMessage}</p>
          </div>

          {recentSessions.length > 0 ? (
            <div className="meta-block" style={{ marginTop: 0, paddingTop: 0, borderTop: 0 }}>
              {recentSessions.map((session) => {
                const isActive = session.id === activeSessionId;
                return (
                  <button
                    key={session.id}
                    className="result-card"
                    type="button"
                    onClick={() => setActiveSessionId(session.id)}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      cursor: "pointer",
                      border: isActive ? "1px solid var(--accent)" : undefined,
                      marginTop: 0,
                      marginBottom: "12px",
                    }}
                  >
                    <p className="result-label" style={{ marginBottom: "8px" }}>
                      {isActive ? "Active Session" : "Session"}
                    </p>
                    <p className="result-content" style={{ marginBottom: "10px" }}>
                      {session.title || "Untitled Session"}
                    </p>
                    <div className="meta-block" style={{ marginTop: 0, paddingTop: 0, borderTop: 0 }}>
                      <p>session_id: {session.id}</p>
                      <p>updated_at: {session.updated_at}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : null}
        </section>

        <section className="panel-card">
          <div className="panel-head">
            <h2>Session Messages</h2>
            <p>{messagesMessage}</p>
          </div>

          {sessionMessages.length > 0 ? (
            <div className="meta-block" style={{ marginTop: 0, paddingTop: 0, borderTop: 0 }}>
              {sessionMessages.map((message) => (
                <div
                  key={message.id}
                  className="result-card"
                  style={{ marginTop: 0, marginBottom: "12px" }}
                >
                  <p className="result-label" style={{ marginBottom: "8px" }}>
                    {message.role}
                  </p>
                  <p className="result-content" style={{ whiteSpace: "pre-wrap" }}>
                    {message.content}
                  </p>
                  <div className="meta-block" style={{ marginTop: "12px" }}>
                    <p>message_id: {message.id}</p>
                    {message.task_id ? <p>task_id: {message.task_id}</p> : null}
                    <p>created_at: {message.created_at}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </section>

        <section className="panel-card">
          <div className="panel-head">
            <h2>Recent Tasks</h2>
            <p>{tasksMessage}</p>
          </div>

          {recentTasks.length > 0 ? (
            <div className="meta-block" style={{ marginTop: 0, paddingTop: 0, borderTop: 0 }}>
              {recentTasks.map((task) => {
                const isActive = task.id === sseTaskId || task.id === chatResult?.task_id;
                return (
                  <button
                    key={task.id}
                    className="result-card"
                    type="button"
                    onClick={() => {
                      void loadPersistedTrace(API_BASE_URL, task.id);
                      setActiveSessionId(task.session_id);
                    }}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      cursor: "pointer",
                      border: isActive ? "1px solid var(--accent)" : undefined,
                      marginTop: 0,
                      marginBottom: "12px",
                    }}
                  >
                    <p className="result-label" style={{ marginBottom: "8px" }}>
                      {isActive ? "Active Task" : "Task"}
                    </p>
                    <p className="result-content" style={{ marginBottom: "10px" }}>
                      {task.prompt}
                    </p>
                    <div className="meta-block" style={{ marginTop: 0, paddingTop: 0, borderTop: 0 }}>
                      <p>task_id: {task.id}</p>
                      <p>session_id: {task.session_id}</p>
                      <p>status: {task.status}</p>
                      <p>updated_at: {task.updated_at}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : null}
        </section>
      </section>
    </main>
  );
}
