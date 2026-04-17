"use client";

import type { TextAreaRef } from "antd/es/input/TextArea";
import { App } from "antd";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";

import {
  ApiError,
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
  PaginatedList,
  SessionMemoryStatus,
  SessionMessage,
  SessionSummary,
  SettingsSummary,
  TaskCancelResponse,
  TaskSummary,
  UsageSummary,
} from "./types";
import {
  ACTIVE_WORKBENCH_SESSION_STORAGE_KEY,
  INSPECTOR_COLLAPSED_STORAGE_KEY,
  INSPECTOR_WIDTH_STORAGE_KEY,
  SIDEBAR_COLLAPSED_STORAGE_KEY,
  SIDEBAR_WIDTH_STORAGE_KEY,
} from "../../../lib/storage-keys";
import { API_BASE_URL } from "./utils";
import { useMediaQuery } from "./use-media-query";

const NARROW_QUERY = "(max-width: 980px)";
const SIDEBAR_W_MIN = 200;
const SIDEBAR_W_MAX = 480;
const SIDEBAR_W_DEFAULT = 280;

const INSPECTOR_W_MIN = 260;
const INSPECTOR_W_MAX = 560;
const INSPECTOR_W_DEFAULT = 340;
const TRACE_DELTA_SYNC_BASE_MS = 1800;
const TRACE_DELTA_SYNC_MAX_MS = 15_000;
const TRACE_DELTA_SYNC_MAX_RETRY_EXP = 3;
const TRACE_DELTA_RECOVER_HINT_MS = 12_000;
const TRACE_DELTA_FAST_DRAIN_MS = 180;
const OPEN_MODEL_SETTINGS_EVENT = "insightagent:open-model-settings";
const RUNNING_TASK_STATUSES = new Set(["pending", "running"]);
const STREAMING_LIKE_PHASES = new Set([
  "pending",
  "running",
  "thinking",
  "tool_running",
  "tool_retry",
  "streaming",
]);

type WorkbenchProps = {
  currentUser?: {
    id: string;
    email: string;
    display_name?: string | null;
  } | null;
  onLogout?: () => void;
};

function normalizedTaskStatus(task: TaskSummary): string {
  const raw =
    (typeof task.status_normalized === "string"
      ? task.status_normalized
      : task.status) ?? "";
  return raw.trim().toLowerCase();
}

function isTaskRunningLike(task: TaskSummary): boolean {
  return RUNNING_TASK_STATUSES.has(normalizedTaskStatus(task));
}

export function Workbench({ currentUser, onLogout }: WorkbenchProps) {
  const t = useMessages();
  const { modal, message } = App.useApp();
  const queryClient = useQueryClient();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("trace");
  const [bannerError, setBannerError] = useState<string | null>(null);
  const [runtimeNoticeDismissed, setRuntimeNoticeDismissed] = useState(false);
  const [inspectorDrawerOpen, setInspectorDrawerOpen] = useState(false);
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState(false);
  const [newSessionBusy, setNewSessionBusy] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [liveRegionText, setLiveRegionText] = useState("");
  const [sidebarWidthPx, setSidebarWidthPx] = useState(SIDEBAR_W_DEFAULT);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [inspectorWidthPx, setInspectorWidthPx] = useState(INSPECTOR_W_DEFAULT);
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false);
  const [traceDeltaSyncStatus, setTraceDeltaSyncStatus] = useState<
    "idle" | "syncing" | "ok" | "retrying" | "paused"
  >("idle");
  const [traceDeltaRetryCount, setTraceDeltaRetryCount] = useState(0);
  const [traceDeltaLastOkAt, setTraceDeltaLastOkAt] = useState<number | null>(
    null,
  );
  const [traceDeltaLastError, setTraceDeltaLastError] = useState<string | null>(
    null,
  );
  const [traceDeltaNextRetryAt, setTraceDeltaNextRetryAt] = useState<number | null>(
    null,
  );
  const [traceDeltaRecoveredAt, setTraceDeltaRecoveredAt] = useState<number | null>(
    null,
  );
  const [recoveryNotice, setRecoveryNotice] = useState<{
    type: "info" | "success" | "error";
    text: string;
  } | null>(null);
  const [isPageVisible, setIsPageVisible] = useState(
    typeof document === "undefined"
      ? true
      : document.visibilityState !== "hidden",
  );

  const prevStreamingRef = useRef(false);
  const prevStreamingForDeltaRef = useRef(false);
  const traceDeltaSyncInFlightRef = useRef(false);
  const traceDeltaRetryCountRef = useRef(0);
  const isNarrow = useMediaQuery(NARROW_QUERY);
  const sidebarWidthRef = useRef(SIDEBAR_W_DEFAULT);
  sidebarWidthRef.current = sidebarWidthPx;
  const inspectorWidthRef = useRef(INSPECTOR_W_DEFAULT);
  inspectorWidthRef.current = inspectorWidthPx;

  const composerRef = useRef<TextAreaRef | null>(null);
  /** 发送成功后输入框会清空，流式失败重试时用于恢复同一条文案 */
  const lastSentPromptRef = useRef("");
  const inspectorShellRef = useRef<HTMLElement>(null);
  const sidebarShellRef = useRef<HTMLElement>(null);
  const activeSessionIdRef = useRef<string | null>(null);
  activeSessionIdRef.current = activeSessionId;
  const sessionOpenButtonRef = useRef<HTMLButtonElement>(null);
  const inspectorOpenButtonRef = useRef<HTMLButtonElement>(null);
  /** 避免 GET /tasks?session_id= 404 时重复 toast / 重复清空 */
  const tasksSession404HandledRef = useRef(false);
  const pendingRestoreSessionIdRef = useRef<string | null>(null);
  const blockedRecoveryTaskIdsRef = useRef<Set<string>>(new Set());
  const recoveringTaskIdRef = useRef<string | null>(null);

  const isStreaming = useChatStreamStore((s: ChatStreamStore) => s.isStreaming);
  const sseTokens = useChatStreamStore((s: ChatStreamStore) => s.sseTokens);
  const sseTraceSteps = useChatStreamStore(
    (s: ChatStreamStore) => s.sseTraceSteps,
  );
  const ssePhase = useChatStreamStore((s: ChatStreamStore) => s.ssePhase);
  const sseTaskId = useChatStreamStore((s: ChatStreamStore) => s.sseTaskId);
  const sseMessage = useChatStreamStore((s: ChatStreamStore) => s.sseMessage);
  const traceCursor = useChatStreamStore((s: ChatStreamStore) => s.traceCursor);
  const sseTaskUsage = useChatStreamStore((s: ChatStreamStore) => s.sseTaskUsage);
  const resetStreamUi = useChatStreamStore(
    (s: ChatStreamStore) => s.resetStreamUi,
  );
  const runTaskStream = useChatStreamStore(
    (s: ChatStreamStore) => s.runTaskStream,
  );
  const resumeTaskStream = useChatStreamStore(
    (s: ChatStreamStore) => s.resumeTaskStream,
  );
  const loadPersistedTrace = useChatStreamStore(
    (s: ChatStreamStore) => s.loadPersistedTrace,
  );
  const loadTraceDelta = useChatStreamStore(
    (s: ChatStreamStore) => s.loadTraceDelta,
  );
  const setStreamMessages = useChatStreamStore(
    (s: ChatStreamStore) => s.setStreamMessages,
  );

  useEffect(() => {
    setStreamMessages(t.stream);
  }, [setStreamMessages, t.stream]);

  const syncTraceDelta = useCallback(
    (taskId: string, options?: { silent?: boolean }) => {
      const normalizedTaskId = taskId.trim();
      if (!normalizedTaskId || traceDeltaSyncInFlightRef.current) {
        return Promise.resolve({ ok: false, error: null, hasMore: false });
      }
      traceDeltaSyncInFlightRef.current = true;
      setTraceDeltaSyncStatus((prev) => (prev === "retrying" ? prev : "syncing"));
      return loadTraceDelta(API_BASE_URL, normalizedTaskId, options).finally(
        () => {
          traceDeltaSyncInFlightRef.current = false;
        },
      );
    },
    [loadTraceDelta],
  );

  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: () => apiJson<SettingsSummary>(`${API_BASE_URL}/api/settings`),
  });

  const SESSION_PAGE = 10;

  const sessionsQuery = useInfiniteQuery({
    queryKey: ["sessions", "paged"],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      apiJson<PaginatedList<SessionSummary>>(
        `${API_BASE_URL}/api/sessions?limit=${SESSION_PAGE}&offset=${pageParam}`,
      ),
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.offset + lastPage.items.length : undefined,
  });

  const TASK_PAGE_SESSION = 12;
  const TASK_PAGE_GLOBAL = 8;

  const tasksQuery = useInfiniteQuery({
    queryKey: ["tasks", "paged", activeSessionId ?? "__global__"],
    initialPageParam: 0,
    queryFn: ({ pageParam }) => {
      const limit = activeSessionId ? TASK_PAGE_SESSION : TASK_PAGE_GLOBAL;
      const base = `${API_BASE_URL}/api/tasks?limit=${limit}&offset=${pageParam}`;
      const url = activeSessionId
        ? `${base}&session_id=${encodeURIComponent(activeSessionId)}`
        : base;
      return apiJson<PaginatedList<TaskSummary>>(url);
    },
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.offset + lastPage.items.length : undefined,
    retry: (failureCount, err) => {
      if (err instanceof ApiError && err.status === 404) {
        return false;
      }
      return failureCount < 2;
    },
  });

  const sessionMemoryQuery = useQuery({
    queryKey: ["session-memory-status", activeSessionId],
    queryFn: () =>
      apiJson<SessionMemoryStatus>(
        `${API_BASE_URL}/api/sessions/${encodeURIComponent(activeSessionId!)}/memory/status`,
      ),
    enabled: Boolean(activeSessionId),
    staleTime: 20_000,
  });

  const usageSummaryQuery = useQuery({
    queryKey: ["tasks-usage-summary", activeSessionId ?? "__global__"],
    queryFn: () =>
      apiJson<UsageSummary>(
        activeSessionId
          ? `${API_BASE_URL}/api/tasks/usage/summary?session_id=${encodeURIComponent(activeSessionId)}`
          : `${API_BASE_URL}/api/tasks/usage/summary`,
      ),
    staleTime: 20_000,
  });

  const usageSummaryErrorBanner =
    usageSummaryQuery.isError && usageSummaryQuery.error
      ? toUserFacingError(usageSummaryQuery.error, t.errors).banner
      : null;

  const sessionMemoryErrorBanner =
    sessionMemoryQuery.isError && sessionMemoryQuery.error
      ? toUserFacingError(sessionMemoryQuery.error, t.errors).banner
      : null;

  useEffect(() => {
    if (!activeSessionId) {
      tasksSession404HandledRef.current = false;
      return;
    }
    if (!tasksQuery.isError || tasksQuery.error == null) {
      return;
    }
    const err = tasksQuery.error;
    if (!(err instanceof ApiError) || err.status !== 404) {
      return;
    }
    if (tasksSession404HandledRef.current) {
      return;
    }
    tasksSession404HandledRef.current = true;
    setActiveSessionId(null);
    message.warning(t.workbench.sessionMissingReset);
    void queryClient.invalidateQueries({ queryKey: ["sessions"] });
  }, [
    activeSessionId,
    tasksQuery.isError,
    tasksQuery.error,
    message,
    queryClient,
    t.workbench.sessionMissingReset,
  ]);

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
      const iw = localStorage.getItem(INSPECTOR_WIDTH_STORAGE_KEY);
      if (iw) {
        const n = Number.parseInt(iw, 10);
        if (!Number.isNaN(n)) {
          setInspectorWidthPx(
            Math.min(INSPECTOR_W_MAX, Math.max(INSPECTOR_W_MIN, n)),
          );
        }
      }
      if (localStorage.getItem(INSPECTOR_COLLAPSED_STORAGE_KEY) === "1") {
        setInspectorCollapsed(true);
      }
      const activeSessionRaw = localStorage.getItem(
        ACTIVE_WORKBENCH_SESSION_STORAGE_KEY,
      );
      const activeSessionStored = activeSessionRaw?.trim();
      if (activeSessionStored) {
        pendingRestoreSessionIdRef.current = activeSessionStored;
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

  useEffect(() => {
    try {
      localStorage.setItem(
        INSPECTOR_WIDTH_STORAGE_KEY,
        String(inspectorWidthPx),
      );
    } catch {
      /* ignore */
    }
  }, [inspectorWidthPx]);

  useEffect(() => {
    try {
      localStorage.setItem(
        INSPECTOR_COLLAPSED_STORAGE_KEY,
        inspectorCollapsed ? "1" : "0",
      );
    } catch {
      /* ignore */
    }
  }, [inspectorCollapsed]);

  useEffect(() => {
    try {
      if (activeSessionId && activeSessionId.trim()) {
        localStorage.setItem(
          ACTIVE_WORKBENCH_SESSION_STORAGE_KEY,
          activeSessionId.trim(),
        );
      } else {
        localStorage.removeItem(ACTIVE_WORKBENCH_SESSION_STORAGE_KEY);
      }
    } catch {
      /* ignore */
    }
  }, [activeSessionId]);

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

  const cancelTaskMutation = useMutation({
    mutationFn: (taskId: string) =>
      apiPostJson<TaskCancelResponse>(
        `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/cancel`,
        {},
      ),
    onSuccess: (data) => {
      if (data.already_terminal) {
        message.info(t.inspector.taskCancelAlreadyTerminal);
      } else {
        message.success(t.inspector.taskCancelDone);
      }
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (err) => {
      const u = toUserFacingError(err, t.errors);
      message.error(
        `${t.inspector.taskCancelFailed}: ${u.banner}${u.hint ? ` ${u.hint}` : ""}`,
      );
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

  const recentSessions = useMemo(
    () => sessionsQuery.data?.pages.flatMap((p) => p.items) ?? [],
    [sessionsQuery.data],
  );
  const recentTasks = useMemo(
    () => tasksQuery.data?.pages.flatMap((p) => p.items) ?? [],
    [tasksQuery.data],
  );
  const tasksFetchNextBusy = tasksQuery.isFetchingNextPage;
  const tasksCanLoadMore = Boolean(tasksQuery.hasNextPage);
  const settingsSummary = settingsQuery.data ?? null;
  const runtimeNotice =
    settingsSummary?.mode === "remote"
      ? settingsSummary.api_key_configured
        ? t.chat.runtimeNoticeRemote
        : t.chat.runtimeNoticeRemoteMissingKey
      : settingsSummary?.mode === "mock"
        ? t.chat.runtimeNoticeMock
        : null;

  useEffect(() => {
    setRuntimeNoticeDismissed(false);
  }, [settingsSummary?.mode, settingsSummary?.api_key_configured]);

  const openModelSettings = useCallback(() => {
    window.dispatchEvent(new CustomEvent(OPEN_MODEL_SETTINGS_EVENT));
  }, []);

  const sessionMessages = messagesQuery.data?.messages ?? [];

  const sessionsLoading = sessionsQuery.isLoading;
  const sessionsFetchNextBusy = sessionsQuery.isFetchingNextPage;
  const sessionsCanLoadMore = Boolean(sessionsQuery.hasNextPage);
  const sessionsMessage = sessionsQuery.isError
    ? t.errors.requestFailed
    : recentSessions.length === 0
      ? t.workbench.noSessions
      : "";

  useEffect(() => {
    if (activeSessionId) {
      return;
    }
    const pending = pendingRestoreSessionIdRef.current?.trim() ?? "";
    if (!pending) {
      return;
    }
    pendingRestoreSessionIdRef.current = null;
    setActiveSessionId(pending);
  }, [activeSessionId]);

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
  }, [settingsQuery.error, sessionsQuery.error, tasksQuery.error, t.errors]);

  useEffect(() => {
    if (!activeSessionId || !messagesQuery.error) {
      return;
    }
    const u = toUserFacingError(messagesQuery.error, t.errors);
    setBannerError((prev) => prev ?? `${u.banner}${u.hint ? ` ${u.hint}` : ""}`);
  }, [activeSessionId, messagesQuery.error, t.errors]);

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
        void queryClient.invalidateQueries({
          queryKey: ["session-memory-status", activeSessionId],
        });
      }
    }
    prevStreamingRef.current = isStreaming;
  }, [isStreaming, activeSessionId, queryClient]);

  useEffect(() => {
    const onVisibilityChange = () => {
      setIsPageVisible(document.visibilityState !== "hidden");
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  useEffect(() => {
    if (!isStreaming) {
      traceDeltaRetryCountRef.current = 0;
      setTraceDeltaRetryCount(0);
      setTraceDeltaSyncStatus("idle");
      setTraceDeltaNextRetryAt(null);
      setTraceDeltaRecoveredAt(null);
      return;
    }
    if (!isPageVisible) {
      setTraceDeltaSyncStatus("paused");
      setTraceDeltaNextRetryAt(null);
      return;
    }
    const taskId = sseTaskId?.trim() ?? "";
    if (!taskId) {
      traceDeltaRetryCountRef.current = 0;
      setTraceDeltaRetryCount(0);
      setTraceDeltaSyncStatus("idle");
      setTraceDeltaNextRetryAt(null);
      setTraceDeltaRecoveredAt(null);
      return;
    }
    setTraceDeltaLastError(null);
    setTraceDeltaNextRetryAt(null);
    setTraceDeltaRecoveredAt(null);
    let stopped = false;
    let timerId: number | null = null;

    const scheduleNext = (ok: boolean, hasMore: boolean) => {
      if (stopped) {
        return;
      }
      if (ok) {
        const recovered = traceDeltaRetryCountRef.current > 0;
        traceDeltaRetryCountRef.current = 0;
        setTraceDeltaRetryCount(0);
        setTraceDeltaSyncStatus("ok");
        setTraceDeltaLastOkAt(Date.now());
        setTraceDeltaLastError(null);
        setTraceDeltaNextRetryAt(null);
        if (recovered) {
          setTraceDeltaRecoveredAt(Date.now());
        }
      } else {
        setTraceDeltaRecoveredAt(null);
        traceDeltaRetryCountRef.current = Math.min(
          TRACE_DELTA_SYNC_MAX_RETRY_EXP,
          traceDeltaRetryCountRef.current + 1,
        );
        setTraceDeltaRetryCount(traceDeltaRetryCountRef.current);
        setTraceDeltaSyncStatus("retrying");
      }
      const delay = ok
        ? hasMore
          ? TRACE_DELTA_FAST_DRAIN_MS
          : TRACE_DELTA_SYNC_BASE_MS
        : Math.min(
            TRACE_DELTA_SYNC_MAX_MS,
            TRACE_DELTA_SYNC_BASE_MS *
              2 ** traceDeltaRetryCountRef.current,
          );
      setTraceDeltaNextRetryAt(Date.now() + delay);
      timerId = window.setTimeout(() => {
        void run();
      }, delay);
    };

    const run = async () => {
      if (stopped) {
        return;
      }
      const result = await syncTraceDelta(taskId, { silent: true });
      if (!result.ok && result.error) {
        setTraceDeltaRecoveredAt(null);
        setTraceDeltaLastError(result.error);
      }
      scheduleNext(result.ok, result.hasMore);
    };

    void run();
    return () => {
      stopped = true;
      if (timerId !== null) {
        window.clearTimeout(timerId);
      }
    };
  }, [isStreaming, isPageVisible, sseTaskId, syncTraceDelta]);

  useEffect(() => {
    const was = prevStreamingForDeltaRef.current;
    if (was && !isStreaming) {
      const taskId = sseTaskId?.trim() ?? "";
      if (taskId) {
        void syncTraceDelta(taskId).then((result) => {
          if (result.ok) {
            setTraceDeltaSyncStatus("ok");
            setTraceDeltaLastOkAt(Date.now());
            setTraceDeltaLastError(null);
            setTraceDeltaNextRetryAt(null);
            if (traceDeltaRetryCountRef.current > 0) {
              setTraceDeltaRecoveredAt(Date.now());
            }
          } else if (result.error) {
            setTraceDeltaRecoveredAt(null);
            setTraceDeltaLastError(result.error);
          }
        });
      }
    }
    prevStreamingForDeltaRef.current = isStreaming;
  }, [isStreaming, sseTaskId, syncTraceDelta]);

  useEffect(() => {
    if (activeSessionId == null) {
      return;
    }
    void queryClient.invalidateQueries({ queryKey: ["sessions"] });
    void queryClient.invalidateQueries({ queryKey: ["tasks"] });
  }, [activeSessionId, queryClient]);

  useEffect(() => {
    const blocked = blockedRecoveryTaskIdsRef.current;
    if (blocked.size === 0) {
      return;
    }
    const runningTaskIds = new Set(
      recentTasks.filter((task) => isTaskRunningLike(task)).map((task) => task.id),
    );
    for (const taskId of Array.from(blocked)) {
      if (!runningTaskIds.has(taskId)) {
        blocked.delete(taskId);
      }
    }
  }, [recentTasks]);

  useEffect(() => {
    if (!activeSessionId || !isPageVisible) {
      return;
    }

    const activeSessionRunningTask = recentTasks
      .filter(
        (task) =>
          task.session_id === activeSessionId && isTaskRunningLike(task),
      )
      .sort(
        (a, b) =>
          Date.parse(b.updated_at || "") - Date.parse(a.updated_at || ""),
      )[0];

    if (!activeSessionRunningTask) {
      return;
    }

    const runningTaskId = activeSessionRunningTask.id.trim();
    if (!runningTaskId) {
      return;
    }
    if (recoveringTaskIdRef.current === runningTaskId) {
      return;
    }
    if (blockedRecoveryTaskIdsRef.current.has(runningTaskId)) {
      return;
    }

    const currentTaskId = sseTaskId?.trim() ?? "";
    if (isStreaming && currentTaskId === runningTaskId) {
      return;
    }
    if (
      !isStreaming &&
      currentTaskId === runningTaskId &&
      typeof ssePhase === "string" &&
      STREAMING_LIKE_PHASES.has(ssePhase)
    ) {
      return;
    }

    recoveringTaskIdRef.current = runningTaskId;
    setInspectorTab("trace");
    setRecoveryNotice({
      type: "info",
      text: t.stream.streamRecoveryStart(runningTaskId),
    });
    void resumeTaskStream({
      apiBaseUrl: API_BASE_URL,
      taskId: runningTaskId,
      onSessionResolved: setActiveSessionId,
    })
      .then((ok) => {
        if (!ok) {
          blockedRecoveryTaskIdsRef.current.add(runningTaskId);
          setRecoveryNotice({
            type: "error",
            text: t.stream.streamRecoveryFailed(runningTaskId),
          });
        } else {
          setRecoveryNotice({
            type: "success",
            text: t.stream.streamRecoveryDone(runningTaskId),
          });
        }
      })
      .finally(() => {
        if (recoveringTaskIdRef.current === runningTaskId) {
          recoveringTaskIdRef.current = null;
        }
      });
  }, [
    activeSessionId,
    isPageVisible,
    isStreaming,
    recentTasks,
    resumeTaskStream,
    ssePhase,
    sseTaskId,
    t.stream,
  ]);

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
    setRecoveryNotice(null);
    if (
      settingsSummary?.mode === "remote" &&
      !settingsSummary.api_key_configured
    ) {
      setBannerError(t.chat.remoteModeNeedConfig);
      openModelSettings();
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
    void syncTraceDelta(taskId).then((result) => {
      if (result.ok) {
        setTraceDeltaLastError(null);
        setTraceDeltaSyncStatus("ok");
        setTraceDeltaLastOkAt(Date.now());
        setTraceDeltaNextRetryAt(null);
        if (traceDeltaRetryCountRef.current > 0) {
          setTraceDeltaRecoveredAt(Date.now());
        }
      } else if (result.error) {
        setTraceDeltaRecoveredAt(null);
        setTraceDeltaLastError(result.error);
      }
    });
  }

  useEffect(() => {
    if (traceDeltaRecoveredAt === null) {
      return;
    }
    const timer = window.setTimeout(() => {
      setTraceDeltaRecoveredAt(null);
    }, TRACE_DELTA_RECOVER_HINT_MS);
    return () => window.clearTimeout(timer);
  }, [traceDeltaRecoveredAt]);

  useEffect(() => {
    if (!recoveryNotice) {
      return;
    }
    const timeoutMs = recoveryNotice.type === "error" ? 7000 : 4500;
    const timer = window.setTimeout(() => {
      setRecoveryNotice(null);
    }, timeoutMs);
    return () => window.clearTimeout(timer);
  }, [recoveryNotice]);

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

  const phaseLabelMap: Record<string, string> = {
    done: t.workbench.phaseDone,
    error: t.workbench.phaseError,
    cancelled: t.workbench.phaseCancelled,
    timeout: t.workbench.phaseTimeout,
    replay: t.workbench.phaseReplay,
    streaming: t.workbench.phaseRunning,
    running: t.workbench.phaseRunning,
    pending: t.workbench.phaseRunning,
    thinking: t.workbench.phaseRunning,
    tool_running: t.workbench.phaseRunning,
    tool_retry: t.workbench.phaseRunning,
  };
  const phaseLabel = ssePhase
    ? (phaseLabelMap[ssePhase] ?? ssePhase)
    : isStreaming
      ? t.workbench.phaseRunning
      : t.workbench.phaseIdle;
  const cancellingTaskId = cancelTaskMutation.isPending
    ? (cancelTaskMutation.variables ?? null)
    : null;

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

  const onInspectorResizeStart = useCallback(
    (event: React.MouseEvent) => {
      if (inspectorCollapsed || isNarrow) return;
      event.preventDefault();
      const startX = event.clientX;
      const startW = inspectorWidthRef.current;
      function onMove(ev: MouseEvent) {
        const delta = startX - ev.clientX;
        const next = Math.min(
          INSPECTOR_W_MAX,
          Math.max(INSPECTOR_W_MIN, startW + delta),
        );
        setInspectorWidthPx(next);
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
    [isNarrow, inspectorCollapsed],
  );

  const shellClass = [
    "app-shell",
    !isNarrow && sidebarCollapsed ? "app-shell--sidebar-collapsed" : "",
    !isNarrow && inspectorCollapsed ? "app-shell--inspector-collapsed" : "",
    isNarrow && inspectorDrawerOpen ? "inspector-drawer-open" : "",
    isNarrow && sessionDrawerOpen ? "session-drawer-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const shellStyle: CSSProperties | undefined = !isNarrow
    ? ({
        ["--sidebar-width" as string]: `${sidebarCollapsed ? 48 : sidebarWidthPx}px`,
        ["--inspector-width" as string]: `${inspectorCollapsed ? 48 : inspectorWidthPx}px`,
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
        sessionsFetchNextBusy={sessionsFetchNextBusy}
        sessionsCanLoadMore={sessionsCanLoadMore}
        onLoadMoreSessions={() => void sessionsQuery.fetchNextPage()}
        sessionsMessage={sessionsMessage}
        onNewSession={handleNewSession}
        newSessionBusy={newSessionBusy}
        drawerMode={isNarrow}
        desktopSidebarChrome={!isNarrow}
        sidebarCollapsed={sidebarCollapsed}
        onToggleSidebarCollapsed={() => setSidebarCollapsed((c) => !c)}
        onSidebarResizeStart={onSidebarResizeStart}
        currentUser={currentUser}
        onLogout={onLogout}
      />

      <ChatColumn
        activeSession={activeSession}
        activeSessionId={activeSessionId}
        settingsSummary={settingsSummary}
        isStreaming={isStreaming}
        apiBanner={bannerError}
        onDismissBanner={() => setBannerError(null)}
        sessionMessages={sessionMessages}
        pendingUserInput={isStreaming ? lastSentPromptRef.current : ""}
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
        runtimeNotice={runtimeNoticeDismissed ? null : runtimeNotice}
        onOpenModelSettings={openModelSettings}
        onDismissRuntimeNotice={() => setRuntimeNoticeDismissed(true)}
        recoveryNotice={recoveryNotice}
        onDismissRecoveryNotice={() => setRecoveryNotice(null)}
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
        desktopInspectorChrome={!isNarrow}
        inspectorCollapsed={inspectorCollapsed}
        onToggleInspectorCollapsed={() =>
          setInspectorCollapsed((c) => !c)
        }
        onInspectorResizeStart={onInspectorResizeStart}
        isStreaming={isStreaming}
        sseTraceSteps={sseTraceSteps}
        sseMessage={sseMessage}
        sseTaskId={sseTaskId}
        phaseLabel={phaseLabel}
        traceCursor={traceCursor}
        traceDeltaSyncStatus={traceDeltaSyncStatus}
        traceDeltaRetryCount={traceDeltaRetryCount}
        traceDeltaLastOkAt={traceDeltaLastOkAt}
        traceDeltaLastError={traceDeltaLastError}
        traceDeltaNextRetryAt={traceDeltaNextRetryAt}
        traceDeltaRecoveredAt={traceDeltaRecoveredAt}
        sseTaskUsage={sseTaskUsage}
        activeSessionId={activeSessionId}
        activeTaskId={activeTaskId}
        activeTask={activeTask}
        latestTaskForSession={latestTaskForSession}
        recentTasks={recentTasks}
        tasksFetchNextBusy={tasksFetchNextBusy}
        tasksCanLoadMore={tasksCanLoadMore}
        onLoadMoreTasks={() => void tasksQuery.fetchNextPage()}
        onReplayTrace={handleLoadPersistedTrace}
        onLoadDelta={handleLoadTraceDelta}
        onSelectTask={handleSelectTask}
        onCancelTask={(task) => {
          cancelTaskMutation.mutate(task.id);
        }}
        cancellingTaskId={cancellingTaskId}
        apiBaseUrl={API_BASE_URL}
        sessionMemoryStatus={sessionMemoryQuery.data}
        sessionMemoryLoading={sessionMemoryQuery.isLoading}
        sessionMemoryError={sessionMemoryErrorBanner}
        usageSummary={usageSummaryQuery.data}
        usageSummaryLoading={usageSummaryQuery.isLoading}
        usageSummaryError={usageSummaryErrorBanner}
        usageSummaryScope={activeSessionId ? "session" : "global"}
      />
    </main>
  );
}
