"use client";

import type { TextAreaRef } from "antd/es/input/TextArea";
import { App } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";

import {
  apiDelete,
  apiJson,
  apiPatchJson,
  apiPostJson,
} from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useFocusTrap } from "../../../lib/hooks/use-focus-trap";
import { useMessages } from "../../../lib/preferences-context";
import {
  useChatStreamStore,
  type ChatStreamStore,
} from "../../../lib/stores/chat-stream-store";
import { ChatColumn } from "./chat-column";
import { Inspector } from "./inspector";
import { Sidebar } from "./sidebar";
import type {
  InspectorTab,
  SessionMessage,
  SessionSummary,
  SettingsSummary,
  TaskSummary,
} from "./types";
import {
  SIDEBAR_COLLAPSED_STORAGE_KEY,
  SIDEBAR_WIDTH_STORAGE_KEY,
} from "../../../lib/storage-keys";
import { API_BASE_URL } from "./utils";
import { useMediaQuery } from "./use-media-query";

const NARROW_QUERY = "(max-width: 980px)";
const SIDEBAR_W_MIN = 200;
const SIDEBAR_W_MAX = 480;
const SIDEBAR_W_DEFAULT = 280;

export function Workbench() {
  const t = useMessages();
  const { modal } = App.useApp();
  const queryClient = useQueryClient();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("trace");
  const [bannerError, setBannerError] = useState<string | null>(null);
  const [inspectorDrawerOpen, setInspectorDrawerOpen] = useState(false);
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState(false);
  const [newSessionBusy, setNewSessionBusy] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [liveRegionText, setLiveRegionText] = useState("");
  const [sidebarWidthPx, setSidebarWidthPx] = useState(SIDEBAR_W_DEFAULT);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const prevStreamingRef = useRef(false);
  const isNarrow = useMediaQuery(NARROW_QUERY);
  const sidebarWidthRef = useRef(SIDEBAR_W_DEFAULT);
  sidebarWidthRef.current = sidebarWidthPx;

  const composerRef = useRef<TextAreaRef | null>(null);
  /** 发送成功后输入框会清空，流式失败重试时用于恢复同一条文案 */
  const lastSentPromptRef = useRef("");
  const inspectorShellRef = useRef<HTMLElement>(null);
  const sidebarShellRef = useRef<HTMLElement>(null);
  const activeSessionIdRef = useRef<string | null>(null);
  activeSessionIdRef.current = activeSessionId;
  const sessionOpenButtonRef = useRef<HTMLButtonElement>(null);
  const inspectorOpenButtonRef = useRef<HTMLButtonElement>(null);

  const isStreaming = useChatStreamStore((s: ChatStreamStore) => s.isStreaming);
  const sseTokens = useChatStreamStore((s: ChatStreamStore) => s.sseTokens);
  const sseTraceSteps = useChatStreamStore(
    (s: ChatStreamStore) => s.sseTraceSteps,
  );
  const ssePhase = useChatStreamStore((s: ChatStreamStore) => s.ssePhase);
  const sseTaskId = useChatStreamStore((s: ChatStreamStore) => s.sseTaskId);
  const sseMessage = useChatStreamStore((s: ChatStreamStore) => s.sseMessage);
  const traceCursor = useChatStreamStore((s: ChatStreamStore) => s.traceCursor);
  const resetStreamUi = useChatStreamStore(
    (s: ChatStreamStore) => s.resetStreamUi,
  );
  const runTaskStream = useChatStreamStore(
    (s: ChatStreamStore) => s.runTaskStream,
  );
  const loadPersistedTrace = useChatStreamStore(
    (s: ChatStreamStore) => s.loadPersistedTrace,
  );
  const loadTraceDelta = useChatStreamStore(
    (s: ChatStreamStore) => s.loadTraceDelta,
  );

  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: () => apiJson<SettingsSummary>(`${API_BASE_URL}/api/settings`),
  });

  const sessionsQuery = useQuery({
    queryKey: ["sessions"],
    queryFn: () =>
      apiJson<{ items: SessionSummary[] }>(
        `${API_BASE_URL}/api/sessions?limit=10`,
      ),
  });

  const tasksQuery = useQuery({
    queryKey: ["tasks"],
    queryFn: () =>
      apiJson<{ items: TaskSummary[] }>(
        `${API_BASE_URL}/api/tasks?limit=8`,
      ),
  });

  useEffect(() => {
    try {
      const w = localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY);
      if (w) {
        const n = Number.parseInt(w, 10);
        if (!Number.isNaN(n)) {
          setSidebarWidthPx(
            Math.min(SIDEBAR_W_MAX, Math.max(SIDEBAR_W_MIN, n)),
          );
        }
      }
      if (localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === "1") {
        setSidebarCollapsed(true);
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(sidebarWidthPx));
    } catch {
      /* ignore */
    }
  }, [sidebarWidthPx]);

  useEffect(() => {
    try {
      localStorage.setItem(
        SIDEBAR_COLLAPSED_STORAGE_KEY,
        sidebarCollapsed ? "1" : "0",
      );
    } catch {
      /* ignore */
    }
  }, [sidebarCollapsed]);

  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) =>
      apiDelete(`${API_BASE_URL}/api/sessions/${sessionId}`),
    onSuccess: (_, sessionId) => {
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.removeQueries({ queryKey: ["messages", sessionId] });
      if (activeSessionIdRef.current === sessionId) {
        setActiveSessionId(null);
        setPrompt("");
        resetStreamUi();
      }
    },
    onError: (err) => {
      const u = toUserFacingError(err, t.errors);
      setBannerError(`${u.banner}${u.hint ? ` ${u.hint}` : ""}`);
    },
  });

  const renameSessionMutation = useMutation({
    mutationFn: ({
      sessionId,
      title,
    }: {
      sessionId: string;
      title: string;
    }) =>
      apiPatchJson<SessionSummary>(
        `${API_BASE_URL}/api/sessions/${sessionId}`,
        { title },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
    onError: (err) => {
      const u = toUserFacingError(err, t.errors);
      setBannerError(`${u.banner}${u.hint ? ` ${u.hint}` : ""}`);
    },
  });

  const messagesQuery = useQuery({
    queryKey: ["messages", activeSessionId],
    queryFn: () =>
      apiJson<{ messages: SessionMessage[] }>(
        `${API_BASE_URL}/api/sessions/${activeSessionId}/messages`,
      ),
    enabled: Boolean(activeSessionId),
  });

  const recentSessions = sessionsQuery.data?.items ?? [];
  const recentTasks = tasksQuery.data?.items ?? [];
  const settingsSummary = settingsQuery.data ?? null;
  const sessionMessages = messagesQuery.data?.messages ?? [];

  const sessionsLoading = sessionsQuery.isLoading;
  const sessionsMessage = sessionsQuery.isError
    ? t.errors.requestFailed
    : recentSessions.length === 0
      ? t.workbench.noSessions
      : "";

  const messagesLoading = Boolean(activeSessionId) && messagesQuery.isLoading;
  let messagesMessage: string = t.workbench.selectSessionForHistory;
  if (activeSessionId) {
    if (messagesQuery.isError) {
      messagesMessage = t.errors.requestFailed;
    } else if (!messagesLoading) {
      messagesMessage = sessionMessages.length
        ? t.workbench.loadedHistory
        : t.workbench.sessionEmpty;
    } else {
      messagesMessage = t.workbench.loadingMessages;
    }
  }

  useEffect(() => {
    const err =
      settingsQuery.error || sessionsQuery.error || tasksQuery.error;
    if (err) {
      const u = toUserFacingError(err, t.errors);
      setBannerError((prev) => prev ?? `${u.banner}${u.hint ? ` ${u.hint}` : ""}`);
    }
  }, [settingsQuery.error, sessionsQuery.error, tasksQuery.error]);

  useEffect(() => {
    if (!activeSessionId || !messagesQuery.error) {
      return;
    }
    const u = toUserFacingError(messagesQuery.error, t.errors);
    setBannerError((prev) => prev ?? `${u.banner}${u.hint ? ` ${u.hint}` : ""}`);
  }, [activeSessionId, messagesQuery.error]);

  useEffect(() => {
    if (!isNarrow) {
      setInspectorDrawerOpen(false);
      setSessionDrawerOpen(false);
    }
  }, [isNarrow]);

  useEffect(() => {
    const drawerOpen =
      isNarrow && (inspectorDrawerOpen || sessionDrawerOpen);
    if (drawerOpen) {
      const previous = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = previous;
      };
    }
  }, [isNarrow, inspectorDrawerOpen, sessionDrawerOpen]);

  useEffect(() => {
    if (!isNarrow || (!inspectorDrawerOpen && !sessionDrawerOpen)) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setInspectorDrawerOpen(false);
        setSessionDrawerOpen(false);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isNarrow, inspectorDrawerOpen, sessionDrawerOpen]);

  useFocusTrap(
    Boolean(isNarrow && inspectorDrawerOpen),
    inspectorShellRef,
    inspectorOpenButtonRef,
  );

  useFocusTrap(
    Boolean(isNarrow && sessionDrawerOpen),
    sidebarShellRef,
    sessionOpenButtonRef,
  );

  const prevStreamingForLive = useRef(isStreaming);
  useEffect(() => {
    const was = prevStreamingForLive.current;
    if (was && !isStreaming) {
      setLiveRegionText(
        ssePhase === "error"
          ? t.workbench.liveRegionError
          : t.workbench.liveRegionDone,
      );
      const hideLiveTimer = window.setTimeout(() => setLiveRegionText(""), 3200);
      prevStreamingForLive.current = isStreaming;
      return () => window.clearTimeout(hideLiveTimer);
    }
    prevStreamingForLive.current = isStreaming;
  }, [isStreaming, ssePhase, t]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        composerRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    const was = prevStreamingRef.current;
    if (was && !isStreaming) {
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      if (activeSessionId) {
        void queryClient.invalidateQueries({
          queryKey: ["messages", activeSessionId],
        });
      }
    }
    prevStreamingRef.current = isStreaming;
  }, [isStreaming, activeSessionId, queryClient]);

  useEffect(() => {
    if (activeSessionId == null) {
      return;
    }
    void queryClient.invalidateQueries({ queryKey: ["sessions"] });
    void queryClient.invalidateQueries({ queryKey: ["tasks"] });
  }, [activeSessionId, queryClient]);

  async function ensureSessionForSend(): Promise<string> {
    if (activeSessionId) {
      return activeSessionId;
    }
    const created = await apiPostJson<SessionSummary>(
      `${API_BASE_URL}/api/sessions`,
      {},
    );
    setActiveSessionId(created.id);
    await queryClient.invalidateQueries({ queryKey: ["sessions"] });
    return created.id;
  }

  async function handleNewSession() {
    setNewSessionBusy(true);
    try {
      const created = await apiPostJson<SessionSummary>(
        `${API_BASE_URL}/api/sessions`,
        {},
      );
      setActiveSessionId(created.id);
      setInspectorTab("trace");
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
      if (isNarrow) {
        setSessionDrawerOpen(false);
      }
    } catch (error) {
      const u = toUserFacingError(error, t.errors);
      setBannerError(`${u.banner}${u.hint ? ` ${u.hint}` : ""}`);
    } finally {
      setNewSessionBusy(false);
    }
  }

  async function handleSend() {
    const text = prompt.trim();
    if (!text) {
      return;
    }
    try {
      const sessionId = await ensureSessionForSend();
      lastSentPromptRef.current = text;
      setPrompt("");
      setInspectorTab("trace");
      if (isNarrow) {
        setInspectorDrawerOpen(true);
        setSessionDrawerOpen(false);
      }
      void runTaskStream({
        apiBaseUrl: API_BASE_URL,
        prompt: text,
        sessionId,
        onSessionResolved: setActiveSessionId,
      });
    } catch (error) {
      const u = toUserFacingError(error, t.errors);
      setBannerError(`${u.banner}${u.hint ? ` ${u.hint}` : ""}`);
    }
  }

  function handleRetryStream() {
    resetStreamUi();
    if (!prompt.trim() && lastSentPromptRef.current) {
      setPrompt(lastSentPromptRef.current);
    }
    void handleSend();
  }

  function openSessionDrawer() {
    setSessionDrawerOpen(true);
    setInspectorDrawerOpen(false);
  }

  function openInspectorDrawer() {
    setInspectorDrawerOpen(true);
    setSessionDrawerOpen(false);
  }

  function handleLoadPersistedTrace() {
    const taskId = sseTaskId?.trim() ?? "";
    setInspectorTab("trace");
    if (isNarrow) {
      openInspectorDrawer();
    }
    void loadPersistedTrace(API_BASE_URL, taskId);
  }

  function handleLoadTraceDelta() {
    const taskId = sseTaskId?.trim() ?? "";
    setInspectorTab("trace");
    if (isNarrow) {
      openInspectorDrawer();
    }
    void loadTraceDelta(API_BASE_URL, taskId);
  }

  function handleSelectTask(task: TaskSummary) {
    setActiveSessionId(task.session_id);
    setInspectorTab("trace");
    if (isNarrow) {
      openInspectorDrawer();
    }
    void loadPersistedTrace(API_BASE_URL, task.id);
  }

  function handleDeleteSession(sessionId: string) {
    modal.confirm({
      title: t.sidebar.deleteSessionTitle,
      content: t.sidebar.deleteSessionConfirm,
      okText: t.sidebar.deleteSessionOk,
      cancelText: t.sidebar.deleteSessionCancel,
      okType: "danger",
      centered: true,
      onOk: () => {
        deleteSessionMutation.mutate(sessionId);
      },
    });
  }

  const activeTaskId = sseTaskId;
  const activeSession = recentSessions.find((s) => s.id === activeSessionId);
  const activeTask = recentTasks.find((t) => t.id === activeTaskId);
  const latestTaskForSession = recentTasks.find(
    (t) => t.session_id === activeSessionId,
  );

  const phaseLabel =
    ssePhase === "done"
      ? t.workbench.phaseDone
      : ssePhase === "error"
        ? t.workbench.phaseError
        : ssePhase === "replay"
          ? t.workbench.phaseReplay
          : ssePhase
            ? ssePhase
            : isStreaming
              ? t.workbench.phaseRunning
              : t.workbench.phaseIdle;

  let composerHint = t.workbench.composerEnterSend;
  let composerHintVariant: "default" | "error" = "default";
  if (isStreaming) {
    composerHint = t.workbench.composerGenerating;
  }
  if (ssePhase === "error") {
    composerHint = sseMessage;
    composerHintVariant = "error";
  }

  const onSidebarResizeStart = useCallback(
    (event: React.MouseEvent) => {
      if (sidebarCollapsed || isNarrow) return;
      event.preventDefault();
      const startX = event.clientX;
      const startW = sidebarWidthRef.current;
      function onMove(ev: MouseEvent) {
        const delta = ev.clientX - startX;
        const next = Math.min(
          SIDEBAR_W_MAX,
          Math.max(SIDEBAR_W_MIN, startW + delta),
        );
        setSidebarWidthPx(next);
      }
      function onUp() {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    },
    [isNarrow, sidebarCollapsed],
  );

  const shellClass = [
    "app-shell",
    !isNarrow && sidebarCollapsed ? "app-shell--sidebar-collapsed" : "",
    isNarrow && inspectorDrawerOpen ? "inspector-drawer-open" : "",
    isNarrow && sessionDrawerOpen ? "session-drawer-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const shellStyle: CSSProperties | undefined = !isNarrow
    ? ({
        ["--sidebar-width" as string]: `${sidebarCollapsed ? 48 : sidebarWidthPx}px`,
      } as CSSProperties)
    : undefined;

  return (
    <main className={shellClass} style={shellStyle}>
      <Sidebar
        ref={sidebarShellRef}
        recentSessions={recentSessions}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => {
          setActiveSessionId(id);
          if (isNarrow) {
            setSessionDrawerOpen(false);
          }
        }}
        onDeleteSession={handleDeleteSession}
        deletingSessionId={
          deleteSessionMutation.isPending &&
          deleteSessionMutation.variables !== undefined
            ? deleteSessionMutation.variables
            : null
        }
        renamingSessionId={
          renameSessionMutation.isPending &&
          renameSessionMutation.variables !== undefined
            ? renameSessionMutation.variables.sessionId
            : null
        }
        onRenameSession={(sessionId, title) =>
          renameSessionMutation.mutateAsync({ sessionId, title })
        }
        sessionsLoading={sessionsLoading}
        sessionsMessage={sessionsMessage}
        onNewSession={handleNewSession}
        newSessionBusy={newSessionBusy}
        drawerMode={isNarrow}
        desktopSidebarChrome={!isNarrow}
        sidebarCollapsed={sidebarCollapsed}
        onToggleSidebarCollapsed={() => setSidebarCollapsed((c) => !c)}
        onSidebarResizeStart={onSidebarResizeStart}
      />

      <ChatColumn
        activeSession={activeSession}
        activeSessionId={activeSessionId}
        settingsSummary={settingsSummary}
        isStreaming={isStreaming}
        apiBanner={bannerError}
        onDismissBanner={() => setBannerError(null)}
        sessionMessages={sessionMessages}
        messagesLoading={messagesLoading}
        messagesMessage={messagesMessage}
        sseTokens={sseTokens}
        ssePhase={ssePhase}
        prompt={prompt}
        onPromptChange={setPrompt}
        onSend={handleSend}
        sendDisabled={isStreaming || !prompt.trim()}
        composerHint={composerHint}
        composerHintVariant={composerHintVariant}
        showSessionDrawerTrigger={isNarrow}
        onOpenSessionDrawer={openSessionDrawer}
        sessionDrawerTriggerRef={sessionOpenButtonRef}
        showInspectorTrigger={isNarrow}
        onOpenInspector={() => {
          setInspectorTab("trace");
          openInspectorDrawer();
        }}
        inspectorDrawerTriggerRef={inspectorOpenButtonRef}
        showNarrowLayoutHint={isNarrow}
        showStreamRetry={ssePhase === "error" && !isStreaming}
        onRetryStream={handleRetryStream}
        composerRef={composerRef}
        liveRegionText={liveRegionText}
      />

      {isNarrow ? (
        <>
          <button
            type="button"
            className="session-backdrop"
            aria-label={t.a11y.closeSessionDrawer}
            onClick={() => setSessionDrawerOpen(false)}
          />
          <button
            type="button"
            className="inspector-backdrop"
            aria-label={t.a11y.closeInspectorDrawer}
            onClick={() => setInspectorDrawerOpen(false)}
          />
        </>
      ) : null}

      <Inspector
        ref={inspectorShellRef}
        tab={inspectorTab}
        setTab={setInspectorTab}
        isStreaming={isStreaming}
        sseTraceSteps={sseTraceSteps}
        sseMessage={sseMessage}
        sseTaskId={sseTaskId}
        phaseLabel={phaseLabel}
        traceCursor={traceCursor}
        activeSessionId={activeSessionId}
        activeTaskId={activeTaskId}
        activeTask={activeTask}
        latestTaskForSession={latestTaskForSession}
        recentTasks={recentTasks}
        onReplayTrace={handleLoadPersistedTrace}
        onLoadDelta={handleLoadTraceDelta}
        onSelectTask={handleSelectTask}
        apiBaseUrl={API_BASE_URL}
      />
    </main>
  );
}
