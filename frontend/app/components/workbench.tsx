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

type InspectorTab = "trace" | "context" | "settings";

const DEFAULT_SETTINGS: SettingsFormState = {
  mode: "mock",
  provider: "mock",
  model: "mock-gpt",
  base_url: "",
  api_key: "",
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function shortenId(value: string): string {
  if (value.length <= 12) {
    return value;
  }
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
}

function getSessionLabel(session: SessionSummary): string {
  if (session.title && session.title.trim()) {
    return session.title.trim();
  }
  return `会话 ${shortenId(session.id)}`;
}

function getTaskLabel(task: TaskSummary): string {
  const prompt = task.prompt.trim();
  if (!prompt) {
    return `任务 ${shortenId(task.id)}`;
  }
  return prompt.length > 48 ? `${prompt.slice(0, 48)}...` : prompt;
}

function getRoleLabel(role: string): string {
  if (role === "user") {
    return "你";
  }
  if (role === "assistant") {
    return "InsightAgent";
  }
  return role;
}

function getStepTitle(step: TraceStepPayload): string {
  const rawTitle =
    typeof step.meta?.label === "string"
      ? step.meta.label
      : typeof step.meta?.step_type === "string"
        ? step.meta.step_type
        : step.type;
  return rawTitle.replace(/_/g, " ");
}

export function Workbench() {
  const [settingsForm, setSettingsForm] =
    useState<SettingsFormState>(DEFAULT_SETTINGS);
  const [settingsSummary, setSettingsSummary] = useState<SettingsSummary | null>(
    null,
  );
  const [settingsMessage, setSettingsMessage] = useState("正在加载设置...");
  const [recentSessions, setRecentSessions] = useState<SessionSummary[]>([]);
  const [sessionsMessage, setSessionsMessage] = useState(
    "正在加载最近会话...",
  );
  const [recentTasks, setRecentTasks] = useState<TaskSummary[]>([]);
  const [tasksMessage, setTasksMessage] = useState("正在加载最近任务...");
  const [sessionMessages, setSessionMessages] = useState<SessionMessage[]>([]);
  const [messagesMessage, setMessagesMessage] = useState(
    "选择一个会话后，这里会显示历史消息。",
  );
  const [chatPrompt, setChatPrompt] = useState("");
  const [chatResult, setChatResult] = useState<ChatResponse | null>(null);
  const [chatMessage, setChatMessage] = useState(
    "任务流是主入口；JSON 调试只作为最小非流式调试能力保留。",
  );
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isChatting, setIsChatting] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("trace");

  const isStreaming = useChatStreamStore((s: ChatStreamStore) => s.isStreaming);
  const sseTokens = useChatStreamStore((s: ChatStreamStore) => s.sseTokens);
  const sseTraceSteps = useChatStreamStore(
    (s: ChatStreamStore) => s.sseTraceSteps,
  );
  const ssePhase = useChatStreamStore((s: ChatStreamStore) => s.ssePhase);
  const sseTaskId = useChatStreamStore((s: ChatStreamStore) => s.sseTaskId);
  const sseMessage = useChatStreamStore((s: ChatStreamStore) => s.sseMessage);
  const traceCursor = useChatStreamStore((s: ChatStreamStore) => s.traceCursor);
  const runTaskStream = useChatStreamStore(
    (s: ChatStreamStore) => s.runTaskStream,
  );
  const loadPersistedTrace = useChatStreamStore(
    (s: ChatStreamStore) => s.loadPersistedTrace,
  );
  const loadTraceDelta = useChatStreamStore(
    (s: ChatStreamStore) => s.loadTraceDelta,
  );

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
      setMessagesMessage("选择一个会话后，这里会显示历史消息。");
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
      setSettingsMessage("设置已从后端同步。");
    } catch (error) {
      setSettingsMessage(
        error instanceof Error ? error.message : "加载设置失败。",
      );
    }
  }

  async function loadSessions() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sessions?limit=10`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`Failed to load sessions (${response.status})`);
      }
      const data = (await response.json()) as { items: SessionSummary[] };
      const sessions = Array.isArray(data.items) ? data.items : [];
      setRecentSessions(sessions);
      setSessionsMessage(
        sessions.length > 0 ? "最近会话已加载。" : "还没有会话。",
      );
    } catch (error) {
      setSessionsMessage(
        error instanceof Error ? error.message : "加载会话失败。",
      );
    }
  }

  async function loadSessionMessages(sessionId: string) {
    try {
      setMessagesMessage("正在加载会话消息...");
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
          ? "会话历史已加载。"
          : "这个会话暂时还没有持久化消息。",
      );
    } catch (error) {
      setSessionMessages([]);
      setMessagesMessage(
        error instanceof Error ? error.message : "加载会话消息失败。",
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
      const tasks = Array.isArray(data.items) ? data.items : [];
      setRecentTasks(tasks);
      setTasksMessage(tasks.length > 0 ? "最近任务已加载。" : "还没有任务。");
    } catch (error) {
      setTasksMessage(
        error instanceof Error ? error.message : "加载任务失败。",
      );
    }
  }

  async function handleSaveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setSettingsMessage("正在保存设置...");

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
      setSettingsMessage("设置已保存。");
      setSettingsForm((current) => ({
        ...current,
        api_key: "",
      }));
    } catch (error) {
      setSettingsMessage(
        error instanceof Error ? error.message : "保存设置失败。",
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSendChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!chatPrompt.trim()) {
      setChatMessage("输入内容不能为空。");
      return;
    }

    setIsChatting(true);
    setChatMessage("正在发送 JSON 调试请求...");

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
      setChatMessage("JSON 调试请求已完成。");
      setInspectorTab("context");
    } catch (error) {
      setChatMessage(
        error instanceof Error ? error.message : "发送请求失败。",
      );
    } finally {
      setIsChatting(false);
    }
  }

  function handleSendTaskStream() {
    setInspectorTab("trace");
    void runTaskStream({
      apiBaseUrl: API_BASE_URL,
      prompt: chatPrompt,
      sessionId: activeSessionId,
      onSessionResolved: setActiveSessionId,
    });
  }

  function handleLoadPersistedTrace() {
    const taskId = sseTaskId ?? chatResult?.task_id ?? "";
    setInspectorTab("trace");
    void loadPersistedTrace(API_BASE_URL, taskId);
  }

  function handleLoadTraceDelta() {
    const taskId = sseTaskId ?? chatResult?.task_id ?? "";
    setInspectorTab("trace");
    void loadTraceDelta(API_BASE_URL, taskId);
  }

  const hasTaskContext = Boolean(sseTaskId || chatResult?.task_id);
  const activeTaskId = sseTaskId ?? chatResult?.task_id ?? null;
  const activeSession = recentSessions.find((session) => session.id === activeSessionId);
  const activeTask = recentTasks.find((task) => task.id === activeTaskId);
  const latestTaskForSession = recentTasks.find(
    (task) => task.session_id === activeSessionId,
  );
  const phaseLabel =
    ssePhase === "done"
      ? "已完成"
      : ssePhase === "error"
        ? "失败"
        : ssePhase === "replay"
          ? "回放中"
          : ssePhase
            ? ssePhase
            : isStreaming
              ? "运行中"
              : "待命";

  return (
    <main className="app-shell">
      <aside className="app-sidebar">
        <div className="brand-block">
          <p className="brand-kicker">InsightAgent</p>
          <h1>智能体</h1>
          <p>围绕会话与任务展开，而不是围绕调试面板展开。</p>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-head">
            <h2>最近会话</h2>
            <span>{sessionsMessage}</span>
          </div>
          <div className="sidebar-list">
            {recentSessions.length > 0 ? (
              recentSessions.map((session) => {
                const isActive = session.id === activeSessionId;
                return (
                  <button
                    key={session.id}
                    className={`sidebar-item${isActive ? " is-active" : ""}`}
                    type="button"
                    onClick={() => setActiveSessionId(session.id)}
                  >
                    <strong>{getSessionLabel(session)}</strong>
                    <span>{formatTimestamp(session.updated_at)}</span>
                  </button>
                );
              })
            ) : (
              <div className="sidebar-empty">还没有会话记录。</div>
            )}
          </div>
        </div>
      </aside>

      <section className="chat-shell">
        <header className="chat-header">
          <div>
            <p className="chat-kicker">当前工作区</p>
            <h2>{activeSession ? getSessionLabel(activeSession) : "新的对话"}</h2>
            <p className="chat-subtitle">
              {activeSession
                ? `最近更新于 ${formatTimestamp(activeSession.updated_at)}`
                : "发送第一条任务，让 InsightAgent 开始工作。"}
            </p>
          </div>
          <div className="header-badges">
            <span className="header-badge">模式 {settingsSummary?.mode ?? "mock"}</span>
            <span className="header-badge">
              {settingsSummary?.provider ?? "mock"} / {settingsSummary?.model ?? "mock-gpt"}
            </span>
            <span className={`header-badge ${isStreaming ? "accent" : ""}`}>
              {isStreaming ? "任务流执行中" : "已就绪"}
            </span>
          </div>
        </header>

        <section className="hero-prompt">
          <div className="hero-copy">
            <p className="chat-kicker">主入口</p>
            <h3>像 ChatGPT 或 Claude 一样，以消息流为主舞台。</h3>
            <p>
              任务流是默认路径，设置和轨迹退到右侧面板，首页只保留开始对话、继续对话和查看结果这几件最重要的事。
            </p>
          </div>
          <div className="hero-stats">
            <div className="stat-pill">
              <span>当前阶段</span>
              <strong>{phaseLabel}</strong>
            </div>
            <div className="stat-pill">
              <span>当前任务</span>
              <strong>{activeTaskId ? shortenId(activeTaskId) : "未激活"}</strong>
            </div>
            <div className="stat-pill">
              <span>轨迹游标</span>
              <strong>{traceCursor}</strong>
            </div>
          </div>
        </section>

        <section className="message-stage">
          {sessionMessages.length > 0 ? (
            <div className="message-feed">
              {sessionMessages.map((message) => (
                <article
                  key={message.id}
                  className={`message-row ${message.role === "user" ? "user" : "assistant"}`}
                >
                  <div className="avatar">{message.role === "user" ? "你" : "IA"}</div>
                  <div className="message-card">
                    <div className="message-meta">
                      <strong>{getRoleLabel(message.role)}</strong>
                      <span>{formatTimestamp(message.created_at)}</span>
                    </div>
                    <p>{message.content}</p>
                    {message.task_id ? (
                      <div className="message-tag">关联任务 {shortenId(message.task_id)}</div>
                    ) : null}
                  </div>
                </article>
              ))}

              {sseTokens ? (
                <article className="message-row assistant live">
                  <div className="avatar">IA</div>
                  <div className="message-card">
                    <div className="message-meta">
                      <strong>InsightAgent</strong>
                      <span>{isStreaming ? "实时生成中" : "最新输出"}</span>
                    </div>
                    <p>{sseTokens}</p>
                  </div>
                </article>
              ) : null}

              {chatResult ? (
                <article className="message-row assistant debug">
                  <div className="avatar">调</div>
                  <div className="message-card debug-card">
                    <div className="message-meta">
                      <strong>JSON 调试响应</strong>
                      <span>{chatResult.provider}</span>
                    </div>
                    <p>{chatResult.content}</p>
                  </div>
                </article>
              ) : null}
            </div>
          ) : (
            <div className="empty-hero">
              <h3>从一个任务开始</h3>
              <p>
                当前主界面已经切成标准聊天型结构。你可以先发送一个任务流请求，然后在右侧查看轨迹、上下文和运行设置。
              </p>
              <div className="empty-actions">
                <button
                  className="primary-button"
                  type="button"
                  disabled={isStreaming || isChatting}
                  onClick={handleSendTaskStream}
                >
                  {isStreaming ? "任务流执行中..." : "运行任务流"}
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isChatting}
                  onClick={() => setInspectorTab("settings")}
                >
                  查看运行设置
                </button>
              </div>
            </div>
          )}
        </section>

        <form className="composer-shell" onSubmit={handleSendChat}>
          <textarea
            value={chatPrompt}
            onChange={(event) => setChatPrompt(event.target.value)}
            placeholder="描述一个问题、一个目标，或者让智能体执行下一步。"
            rows={5}
          />
          <div className="composer-footer">
            <p>{chatMessage}</p>
            <div className="composer-actions">
              <button
                className="primary-button"
                disabled={isStreaming || isChatting}
                type="button"
                onClick={handleSendTaskStream}
              >
                {isStreaming ? "任务流执行中..." : "运行任务流"}
              </button>
              <button className="secondary-button" disabled={isChatting} type="submit">
                {isChatting ? "发送中..." : "运行 JSON 调试"}
              </button>
            </div>
          </div>
        </form>
      </section>

      <aside className="inspector-shell">
        <div className="inspector-tabs">
          <button
            className={inspectorTab === "trace" ? "active" : ""}
            type="button"
            onClick={() => setInspectorTab("trace")}
          >
            轨迹
          </button>
          <button
            className={inspectorTab === "context" ? "active" : ""}
            type="button"
            onClick={() => setInspectorTab("context")}
          >
            上下文
          </button>
          <button
            className={inspectorTab === "settings" ? "active" : ""}
            type="button"
            onClick={() => setInspectorTab("settings")}
          >
            设置
          </button>
        </div>

        {inspectorTab === "trace" ? (
          <section className="inspector-panel">
            <div className="panel-head">
              <div>
                <p className="chat-kicker">执行轨迹</p>
                <h3>任务时间线</h3>
              </div>
              <span>{sseTraceSteps.length > 0 ? `${sseTraceSteps.length} 步` : "暂无数据"}</span>
            </div>

            <div className="panel-actions">
              <button
                className="ghost-button"
                disabled={isStreaming || isChatting || !hasTaskContext}
                type="button"
                onClick={handleLoadPersistedTrace}
              >
                回放轨迹
              </button>
              <button
                className="ghost-button"
                disabled={isStreaming || isChatting || !hasTaskContext}
                type="button"
                onClick={handleLoadTraceDelta}
              >
                加载增量
              </button>
            </div>

            <p className="panel-note">{sseMessage}</p>

            {sseTraceSteps.length > 0 ? (
              <div className="trace-feed">
                {sseTraceSteps.map((step) => (
                  <article key={step.id} className="trace-card">
                    <div className="trace-top">
                      <strong>{getStepTitle(step)}</strong>
                      <span>
                        {typeof step.seq === "number" ? `seq ${step.seq}` : shortenId(step.id)}
                      </span>
                    </div>
                    <p>{step.content || "该步骤暂时还没有文本内容。"}</p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="panel-empty">
                先执行一个任务流，或者从左侧选择一个已有任务，这里就会展示时间线与后续可视化节点数据。
              </div>
            )}
          </section>
        ) : null}

        {inspectorTab === "context" ? (
          <section className="inspector-panel">
              <div className="panel-head">
              <div>
                <p className="chat-kicker">当前上下文</p>
                <h3>会话与任务摘要</h3>
              </div>
            </div>

            <div className="context-grid">
              <span>会话</span>
              <strong>{activeSessionId ? shortenId(activeSessionId) : "无"}</strong>
              <span>任务</span>
              <strong>{activeTaskId ? shortenId(activeTaskId) : "无"}</strong>
              <span>阶段</span>
              <strong>{phaseLabel}</strong>
              <span>轨迹游标</span>
              <strong>{traceCursor}</strong>
            </div>

            <div className="summary-card">
              <p className="summary-label">任务视角</p>
              <strong>任务是会话中的一次具体执行，不再作为左侧主导航入口。</strong>
              <span>{tasksMessage}</span>
            </div>

            {activeTask ? (
              <div className="summary-card">
                <p className="summary-label">当前任务</p>
                <strong>{getTaskLabel(activeTask)}</strong>
                <span>状态 {activeTask.status}</span>
              </div>
            ) : null}

            {latestTaskForSession ? (
              <div className="summary-card">
                <p className="summary-label">当前会话最近任务</p>
                <strong>{getTaskLabel(latestTaskForSession)}</strong>
                <span>{formatTimestamp(latestTaskForSession.updated_at)}</span>
              </div>
            ) : null}

            {recentTasks.length > 0 ? (
              <div className="summary-card">
                <p className="summary-label">最近任务列表</p>
                <div className="task-summary-list">
                  {recentTasks.map((task) => {
                    const isActive = task.id === activeTaskId;
                    return (
                      <button
                        key={task.id}
                        className={`task-summary-item${isActive ? " is-active" : ""}`}
                        type="button"
                        onClick={() => {
                          setActiveSessionId(task.session_id);
                          setInspectorTab("trace");
                          void loadPersistedTrace(API_BASE_URL, task.id);
                        }}
                      >
                        <strong>{getTaskLabel(task)}</strong>
                        <span>
                          {task.status} · {formatTimestamp(task.updated_at)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null}

            {chatResult ? (
              <div className="summary-card">
                <p className="summary-label">最新调试响应</p>
                <strong>{chatResult.provider} / {chatResult.model}</strong>
                <span>{shortenId(chatResult.task_id)}</span>
              </div>
            ) : null}
          </section>
        ) : null}

        {inspectorTab === "settings" ? (
          <section className="inspector-panel">
            <div className="panel-head">
              <div>
                <p className="chat-kicker">运行设置</p>
                <h3>后端配置</h3>
              </div>
              <span>{settingsMessage}</span>
            </div>

            <form className="settings-form" onSubmit={handleSaveSettings}>
              <label className="field">
                <span>模式</span>
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
                <span>提供方</span>
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
                <span>模型</span>
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
                <span>基础地址</span>
                <input
                  value={settingsForm.base_url}
                  onChange={(event) =>
                    setSettingsForm((current) => ({
                      ...current,
                      base_url: event.target.value,
                    }))
                  }
                  placeholder="可选"
                />
              </label>

              <label className="field">
                <span>API 密钥</span>
                <input
                  type="password"
                  value={settingsForm.api_key}
                  onChange={(event) =>
                    setSettingsForm((current) => ({
                      ...current,
                      api_key: event.target.value,
                    }))
                  }
                  placeholder={
                    settingsSummary?.api_key_configured ? "已配置" : "mock 模式下可留空"
                  }
                />
              </label>

              <button className="secondary-button full-width" disabled={isSaving} type="submit">
                {isSaving ? "保存中..." : "保存设置"}
              </button>
            </form>

            {settingsSummary ? (
              <div className="context-grid compact">
                <span>提供方</span>
                <strong>{settingsSummary.provider}</strong>
                <span>模型</span>
                <strong>{settingsSummary.model}</strong>
                <span>API 密钥</span>
                <strong>{settingsSummary.api_key_configured ? "已配置" : "未配置"}</strong>
                <span>SQLite</span>
                <strong>{settingsSummary.sqlite_path}</strong>
              </div>
            ) : null}
          </section>
        ) : null}
      </aside>
    </main>
  );
}
