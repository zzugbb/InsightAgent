"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { apiDelete, apiJson, apiPostJson } from "../../../lib/api-client";
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
import { API_BASE_URL } from "./utils";
import { useMediaQuery } from "./use-media-query";

const NARROW_QUERY = "(max-width: 980px)";

export function Workbench() {
  const t = useMessages();
  const queryClient = useQueryClient();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("trace");
  const [bannerError, setBannerError] = useState<string | null>(null);
  const [inspectorDrawerOpen, setInspectorDrawerOpen] = useState(false);
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState(false);
  const [newSessionBusy, setNewSessionBusy] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [liveRegionText, setLiveRegionText] = useState("");

  const prevStreamingRef = useRef(false);
  const isNarrow = useMediaQuery(NARROW_QUERY);

  const composerRef = useRef<HTMLTextAreaElement>(null);
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
    : recentSessions.length > 0
      ? t.workbench.loadedSessions
      : t.workbench.noSessions;

  const tasksMessage = tasksQuery.isError
    ? t.errors.requestFailed
    : recentTasks.length > 0
      ? t.workbench.loadedTasks
      : t.workbench.noTasks;

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
    try {
      const sessionId = await ensureSessionForSend();
      setInspectorTab("trace");
      if (isNarrow) {
        setInspectorDrawerOpen(true);
        setSessionDrawerOpen(false);
      }
      void runTaskStream({
        apiBaseUrl: API_BASE_URL,
        prompt,
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
    if (!window.confirm(t.sidebar.deleteSessionConfirm)) {
      return;
    }
    deleteSessionMutation.mutate(sessionId);
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

  let composerHint = t.workbench.composerIdleHint;
  let composerHintVariant: "default" | "error" = "default";
  if (isStreaming) {
    composerHint = t.workbench.composerGenerating;
  }
  if (ssePhase === "error") {
    composerHint = sseMessage;
    composerHintVariant = "error";
  }

  const shellClass = [
    "app-shell",
    isNarrow && inspectorDrawerOpen ? "inspector-drawer-open" : "",
    isNarrow && sessionDrawerOpen ? "session-drawer-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <main className={shellClass}>
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
        sessionsLoading={sessionsLoading}
        sessionsMessage={sessionsMessage}
        onNewSession={handleNewSession}
        newSessionBusy={newSessionBusy}
        drawerMode={isNarrow}
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
        tasksMessage={tasksMessage}
        onReplayTrace={handleLoadPersistedTrace}
        onLoadDelta={handleLoadTraceDelta}
        onSelectTask={handleSelectTask}
        apiBaseUrl={API_BASE_URL}
      />
    </main>
  );
}
