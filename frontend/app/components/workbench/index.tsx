"use client";

import type { TextAreaRef } from "antd/es/input/TextArea";
import { App, Drawer } from "antd";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";

import {
  ApiError,
  apiDelete,
  apiJson,
  apiPatchJson,
  apiPostJson,
} from "../../../lib/api-client";
import { downloadAuthenticatedExport } from "../../../lib/export-download";
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
import { TaskCenter } from "./task-center";
import { useWorkbenchLayout } from "./use-workbench-layout";
import {
  INSPECTOR_W_MAX,
  INSPECTOR_W_MIN,
  SIDEBAR_W_MAX,
  SIDEBAR_W_MIN,
} from "./workbench-layout";
import {
  reconcileRuntimeNoticeDismissal,
} from "./workbench-runtime-notice";
import type { RuntimeNoticeDismissal } from "./workbench-runtime-notice";
import { resolveTraceDeltaReset } from "./workbench-trace-sync";
import type { TraceDeltaSource } from "./workbench-trace-sync";
import { reconcileRecoveryPreparation } from "./workbench-recovery";
import type { RecoveryPreparation } from "./workbench-recovery";
import {
  resolveNarrowDrawers,
  resolveRemoteSendCooldownUntil,
  resolveTaskCenterScope,
  reconcileQueryBanner,
} from "./workbench-ui-state";
import type { QueryBannerSource } from "./workbench-ui-state";
import type {
  InspectorTab,
  PaginatedList,
  SessionMessage,
  SessionSummary,
  SettingsSummary,
  TaskCancelResponse,
  TaskSummary,
} from "./types";
import {
  ACTIVE_WORKBENCH_SESSION_STORAGE_KEY,
} from "../../../lib/storage-keys";
import {
  API_BASE_URL,
  resolveTaskStreamTerminalReason,
} from "./utils";
import { useMediaQuery } from "./use-media-query";

const NARROW_QUERY = "(max-width: 980px)";
const TRACE_DELTA_SYNC_BASE_MS = 1800;
const TRACE_DELTA_SYNC_MAX_MS = 15_000;
const TRACE_DELTA_SYNC_MAX_RETRY_EXP = 3;
const TRACE_DELTA_RECOVER_HINT_MS = 12_000;
const TRACE_DELTA_FAST_DRAIN_MS = 180;
const ACTIVE_TASK_STATUS_POLL_MS = 600;
const OPEN_MODEL_SETTINGS_EVENT = "insightagent:open-model-settings";
const RUNNING_TASK_STATUSES = new Set(["queued", "pending", "running"]);
const CANCEL_SEND_COOLDOWN_MS = 2200;
const RUNNING_STREAM_PHASES = new Set([
  "queued",
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
    role?: string;
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
  const [observedQueryBannerSource, setObservedQueryBannerSource] =
    useState<QueryBannerSource>({
      settingsError: null,
      sessionsError: null,
      tasksError: null,
      messagesError: null,
      activeSessionId: null,
      errorLabels: null,
    });
  const [runtimeNoticeDismissal, setRuntimeNoticeDismissal] =
    useState<RuntimeNoticeDismissal>({
      mode: undefined,
      apiKeyConfigured: undefined,
      dismissed: false,
    });
  const [inspectorDrawerOpen, setInspectorDrawerOpen] = useState(false);
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState(false);
  const [taskCenterDrawerOpen, setTaskCenterDrawerOpen] = useState(false);
  const [newSessionBusy, setNewSessionBusy] = useState(false);
  const [taskCenterScope, setTaskCenterScope] = useState<"session" | "global">(
    "global",
  );
  const [taskSearchQuery, setTaskSearchQuery] = useState("");
  const [taskGovernanceProfileFilter, setTaskGovernanceProfileFilter] =
    useState<string>("__all__");
  const [taskGovernanceProviderSourceFilter, setTaskGovernanceProviderSourceFilter] =
    useState<string>("__all__");
  const [prompt, setPrompt] = useState("");
  const [lastSentPrompt, setLastSentPrompt] = useState("");
  const [liveRegionText, setLiveRegionText] = useState("");
  const [sessionExporting, setSessionExporting] = useState<
    "json" | "markdown" | null
  >(null);
  const {
    sidebarWidthPx,
    setSidebarWidthPx,
    sidebarCollapsed,
    setSidebarCollapsed,
    inspectorWidthPx,
    setInspectorWidthPx,
    inspectorCollapsed,
    setInspectorCollapsed,
  } = useWorkbenchLayout();
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
  const [observedTraceDeltaSource, setObservedTraceDeltaSource] =
    useState<TraceDeltaSource>({
      isStreaming: false,
      isPageVisible: true,
      taskId: "",
    });
  const [recoveryNotice, setRecoveryNotice] = useState<{
    type: "info" | "success" | "error";
    text: string;
  } | null>(null);
  const [recoveryPreparation, setRecoveryPreparation] =
    useState<RecoveryPreparation>({ preparedTaskIds: [], launchTaskId: null });
  const [cancelSendCooldownUntil, setCancelSendCooldownUntil] = useState<
    number | null
  >(null);
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
  const currentTaskCenterScope = resolveTaskCenterScope(taskCenterScope, activeSessionId);
  if (currentTaskCenterScope !== taskCenterScope) {
    setTaskCenterScope(currentTaskCenterScope);
  }
  const currentNarrowDrawers = resolveNarrowDrawers(isNarrow, {
    inspector: inspectorDrawerOpen,
    session: sessionDrawerOpen,
  });
  if (inspectorDrawerOpen !== currentNarrowDrawers.inspector) {
    setInspectorDrawerOpen(currentNarrowDrawers.inspector);
  }
  if (sessionDrawerOpen !== currentNarrowDrawers.session) {
    setSessionDrawerOpen(currentNarrowDrawers.session);
  }

  const composerRef = useRef<TextAreaRef | null>(null);
  const inspectorShellRef = useRef<HTMLElement>(null);
  const sidebarShellRef = useRef<HTMLElement>(null);
  const activeSessionIdRef = useRef<string | null>(null);
  const sessionOpenButtonRef = useRef<HTMLButtonElement>(null);
  const inspectorOpenButtonRef = useRef<HTMLButtonElement>(null);
  /** 避免 GET /tasks?session_id= 404 时重复 toast / 重复清空 */
  const tasksSession404HandledRef = useRef(false);
  const pendingRestoreSessionIdRef = useRef<string | null>(null);
  const recoveringTaskIdRef = useRef<string | null>(null);
  const cancelSendCooldownTimerRef = useRef<number | null>(null);

  useEffect(() => {
    activeSessionIdRef.current = activeSessionId;
  }, [activeSessionId]);

  const isStreaming = useChatStreamStore((s: ChatStreamStore) => s.isStreaming);
  const sseTokens = useChatStreamStore((s: ChatStreamStore) => s.sseTokens);
  const sseTraceSteps = useChatStreamStore(
    (s: ChatStreamStore) => s.sseTraceSteps,
  );
  const ssePhase = useChatStreamStore((s: ChatStreamStore) => s.ssePhase);
  const sseQueue = useChatStreamStore((s: ChatStreamStore) => s.sseQueue);
  const sseTaskId = useChatStreamStore((s: ChatStreamStore) => s.sseTaskId);
  const currentTraceDeltaSource = {
    isStreaming,
    isPageVisible,
    taskId: sseTaskId?.trim() ?? "",
  };
  const traceDeltaReset = resolveTraceDeltaReset(
    observedTraceDeltaSource,
    currentTraceDeltaSource,
  );
  if (traceDeltaReset !== null) {
    setObservedTraceDeltaSource(currentTraceDeltaSource);
    if (traceDeltaReset === "idle") {
      setTraceDeltaRetryCount(0);
      setTraceDeltaSyncStatus("idle");
      setTraceDeltaNextRetryAt(null);
      setTraceDeltaRecoveredAt(null);
    } else if (traceDeltaReset === "paused") {
      setTraceDeltaSyncStatus("paused");
      setTraceDeltaNextRetryAt(null);
    } else {
      setTraceDeltaLastError(null);
      setTraceDeltaNextRetryAt(null);
      setTraceDeltaRecoveredAt(null);
    }
  }
  const sseSessionId = useChatStreamStore(
    (s: ChatStreamStore) => s.sseSessionId,
  );
  const sseMessage = useChatStreamStore((s: ChatStreamStore) => s.sseMessage);
  const traceCursor = useChatStreamStore((s: ChatStreamStore) => s.traceCursor);
  const sseTaskUsage = useChatStreamStore(
    (s: ChatStreamStore) => s.sseTaskUsage,
  );
  const resetStreamUi = useChatStreamStore(
    (s: ChatStreamStore) => s.resetStreamUi,
  );
  const runTaskStream = useChatStreamStore(
    (s: ChatStreamStore) => s.runTaskStream,
  );
  const cancelActiveStreamLocal = useChatStreamStore(
    (s: ChatStreamStore) => s.cancelActiveStreamLocal,
  );
  const completeActiveStreamLocal = useChatStreamStore(
    (s: ChatStreamStore) => s.completeActiveStreamLocal,
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

  const TASK_PAGE_SESSION = 50;
  const TASK_PAGE_GLOBAL = 50;
  const taskScopeSessionId =
    currentTaskCenterScope === "session" ? activeSessionId : null;
  const deferredTaskSearchQuery = useDeferredValue(taskSearchQuery.trim());
  const deferredTaskGovernanceProfileFilter = useDeferredValue(
    taskGovernanceProfileFilter,
  );
  const deferredTaskGovernanceProviderSourceFilter = useDeferredValue(
    taskGovernanceProviderSourceFilter,
  );

  const tasksQuery = useInfiniteQuery({
    queryKey: [
      "tasks",
      "paged",
      currentTaskCenterScope,
      taskScopeSessionId ?? "__global__",
      deferredTaskSearchQuery,
      deferredTaskGovernanceProfileFilter,
      deferredTaskGovernanceProviderSourceFilter,
    ],
    initialPageParam: 0,
    enabled: currentTaskCenterScope === "global" || Boolean(taskScopeSessionId),
    queryFn: ({ pageParam }) => {
      const limit =
        currentTaskCenterScope === "session" ? TASK_PAGE_SESSION : TASK_PAGE_GLOBAL;
      const base = `${API_BASE_URL}/api/tasks?limit=${limit}&offset=${pageParam}`;
      const withSession = taskScopeSessionId
        ? `${base}&session_id=${encodeURIComponent(taskScopeSessionId)}`
        : base;
      const searchUrl = deferredTaskSearchQuery
        ? `${withSession}&query=${encodeURIComponent(deferredTaskSearchQuery)}`
        : withSession;
      const withProfileFilter =
        deferredTaskGovernanceProfileFilter !== "__all__"
          ? `${searchUrl}&tool_registry_profile=${encodeURIComponent(
              deferredTaskGovernanceProfileFilter,
            )}`
          : searchUrl;
      const url =
        deferredTaskGovernanceProviderSourceFilter !== "__all__"
          ? `${withProfileFilter}&tool_registry_provider_source=${encodeURIComponent(
              deferredTaskGovernanceProviderSourceFilter,
            )}`
          : withProfileFilter;
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
  const tasksHasNextPage = Boolean(tasksQuery.hasNextPage);
  const tasksFetchingNextPage = tasksQuery.isFetchingNextPage;
  const fetchNextTasksPage = tasksQuery.fetchNextPage;
  const tasksErrorText = useMemo(() => {
    if (!tasksQuery.isError || tasksQuery.error == null) {
      return null;
    }
    const userFacing = toUserFacingError(tasksQuery.error, t.errors);
    return userFacing.hint
      ? `${userFacing.banner} ${userFacing.hint}`
      : userFacing.banner;
  }, [tasksQuery.error, tasksQuery.isError, t.errors]);

  useEffect(() => {
    if (!tasksHasNextPage || tasksFetchingNextPage) {
      return;
    }
    void fetchNextTasksPage();
  }, [fetchNextTasksPage, tasksFetchingNextPage, tasksHasNextPage]);

  useEffect(() => {
    if (currentTaskCenterScope !== "session") {
      tasksSession404HandledRef.current = false;
      return;
    }
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
    currentTaskCenterScope,
    tasksQuery.isError,
    tasksQuery.error,
    message,
    queryClient,
    t.workbench.sessionMissingReset,
  ]);

  useEffect(() => {
    try {
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
    onMutate: (taskId) => {
      cancelActiveStreamLocal({ taskId, reason: "cancelled" });
      if (settingsSummary?.mode === "remote") {
        startCancelSendCooldown();
      }
    },
    onSuccess: (data, taskId) => {
      if (!data.already_terminal) {
        cancelActiveStreamLocal({ taskId, reason: "cancelled" });
      }
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
  const recentTasksScoped = useMemo(
    () =>
      activeSessionId
        ? recentTasks.filter((task) => task.session_id === activeSessionId)
        : recentTasks,
    [activeSessionId, recentTasks],
  );
  const settingsSummary = settingsQuery.data ?? null;
  const currentCancelSendCooldownUntil = resolveRemoteSendCooldownUntil(
    settingsSummary?.mode,
    cancelSendCooldownUntil,
  );
  if (currentCancelSendCooldownUntil !== cancelSendCooldownUntil) {
    setCancelSendCooldownUntil(currentCancelSendCooldownUntil);
  }
  const runtimeNotice =
    settingsSummary?.mode === "remote"
      ? settingsSummary.api_key_configured
        ? null
        : t.chat.runtimeNoticeRemoteMissingKey
      : settingsSummary?.mode === "mock"
        ? t.chat.runtimeNoticeMock
        : null;

  const currentRuntimeNoticeDismissal = reconcileRuntimeNoticeDismissal(
    runtimeNoticeDismissal,
    {
      mode: settingsSummary?.mode,
      apiKeyConfigured: settingsSummary?.api_key_configured,
    },
  );
  if (currentRuntimeNoticeDismissal !== runtimeNoticeDismissal) {
    setRuntimeNoticeDismissal(currentRuntimeNoticeDismissal);
  }

  const openModelSettings = useCallback(() => {
    window.dispatchEvent(new CustomEvent(OPEN_MODEL_SETTINGS_EVENT));
  }, []);

  const handleExportSession = useCallback(
    async (sessionIdInput: string, format: "json" | "markdown") => {
      const sessionId = sessionIdInput.trim();
      if (!sessionId) {
        message.warning(t.inspector.sessionExportNoSelection);
        return;
      }
      setSessionExporting(format);
      const encodedSessionId = encodeURIComponent(sessionId);
      const route = format === "json" ? "json" : "markdown";
      const fallbackFilename =
        format === "json"
          ? `insightagent-session-${sessionId}.json`
          : `insightagent-session-${sessionId}.md`;
      const requestUrl =
        `${API_BASE_URL}/api/sessions/${encodedSessionId}/export/${route}?download=1`;
      try {
        await downloadAuthenticatedExport(
          requestUrl,
          fallbackFilename,
        );
        message.success(
          format === "json"
            ? t.inspector.sessionExportJsonDone
            : t.inspector.sessionExportMarkdownDone,
        );
      } catch (error) {
        const u = toUserFacingError(error, t.errors);
        message.error(u.hint ? `${u.banner} ${u.hint}` : u.banner);
      } finally {
        setSessionExporting(null);
      }
    },
    [
      message,
      t.errors,
      t.inspector.sessionExportJsonDone,
      t.inspector.sessionExportMarkdownDone,
      t.inspector.sessionExportNoSelection,
    ],
  );

  const startCancelSendCooldown = useCallback(() => {
    if (cancelSendCooldownTimerRef.current !== null) {
      window.clearTimeout(cancelSendCooldownTimerRef.current);
      cancelSendCooldownTimerRef.current = null;
    }
    const nextUntil = Date.now() + CANCEL_SEND_COOLDOWN_MS;
    setCancelSendCooldownUntil(nextUntil);
    cancelSendCooldownTimerRef.current = window.setTimeout(() => {
      setCancelSendCooldownUntil(null);
      cancelSendCooldownTimerRef.current = null;
    }, CANCEL_SEND_COOLDOWN_MS);
  }, []);

  useEffect(
    () => () => {
      if (cancelSendCooldownTimerRef.current !== null) {
        window.clearTimeout(cancelSendCooldownTimerRef.current);
        cancelSendCooldownTimerRef.current = null;
      }
    },
    [],
  );

  useEffect(() => {
    if (settingsSummary?.mode === "remote") {
      return;
    }
    if (cancelSendCooldownTimerRef.current !== null) {
      window.clearTimeout(cancelSendCooldownTimerRef.current);
      cancelSendCooldownTimerRef.current = null;
    }
  }, [settingsSummary?.mode]);

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

  const streamSessionMatchesActive =
    !activeSessionId ||
    !sseSessionId ||
    sseSessionId.trim() === activeSessionId.trim();
  const scopedIsStreaming = streamSessionMatchesActive ? isStreaming : false;
  const scopedSseTokens = streamSessionMatchesActive ? sseTokens : "";
  const scopedSseTraceSteps = streamSessionMatchesActive ? sseTraceSteps : [];
  const scopedSsePhase = streamSessionMatchesActive ? ssePhase : null;
  const scopedSseQueue = streamSessionMatchesActive ? sseQueue : null;
  const scopedSseTaskId = streamSessionMatchesActive ? sseTaskId : null;
  const scopedSseTaskUsage = streamSessionMatchesActive ? sseTaskUsage : null;
  const scopedSseMessage = streamSessionMatchesActive
    ? sseMessage
    : t.stream.idleHint;
  const scopedTraceCursor = streamSessionMatchesActive ? traceCursor : 0;
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
    const taskId = sseTaskId?.trim() ?? "";
    if (!taskId) {
      return;
    }
    const task = recentTasks.find((item) => item.id === taskId);
    const reason = resolveTaskStreamTerminalReason({
      task,
      activeTaskId: taskId,
      isStreaming,
    });
    if (!reason) {
      return;
    }
    completeActiveStreamLocal({ taskId, reason });
  }, [completeActiveStreamLocal, isStreaming, recentTasks, sseTaskId]);

  useEffect(() => {
    const taskId = sseTaskId?.trim() ?? "";
    if (!isStreaming || !taskId) {
      return;
    }
    let stopped = false;
    let timerId: number | null = null;

    const schedule = () => {
      if (stopped) {
        return;
      }
      timerId = window.setTimeout(() => {
        void run();
      }, ACTIVE_TASK_STATUS_POLL_MS);
    };

    const run = async () => {
      if (stopped) {
        return;
      }
      try {
        const task = await apiJson<TaskSummary>(
          `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}`,
        );
        const reason = resolveTaskStreamTerminalReason({
          task,
          activeTaskId: taskId,
          isStreaming: useChatStreamStore.getState().isStreaming,
        });
        if (reason) {
          completeActiveStreamLocal({ taskId, reason });
          return;
        }
      } catch {
        // Status polling is a best-effort fallback; SSE remains the primary stream contract.
      }
      schedule();
    };

    schedule();
    return () => {
      stopped = true;
      if (timerId !== null) {
        window.clearTimeout(timerId);
      }
    };
  }, [completeActiveStreamLocal, isStreaming, sseTaskId]);

  const currentQueryBanner = reconcileQueryBanner(
    observedQueryBannerSource,
    {
      settingsError: settingsQuery.error,
      sessionsError: sessionsQuery.error,
      tasksError: tasksQuery.error,
      messagesError: messagesQuery.error,
      activeSessionId,
      errorLabels: t.errors,
    },
    bannerError,
    (error) => {
      const userFacing = toUserFacingError(error, t.errors);
      return `${userFacing.banner}${userFacing.hint ? ` ${userFacing.hint}` : ""}`;
    },
  );
  if (currentQueryBanner.source !== observedQueryBannerSource) {
    setObservedQueryBannerSource(currentQueryBanner.source);
    if (currentQueryBanner.banner !== bannerError) {
      setBannerError(currentQueryBanner.banner);
    }
  }

  useEffect(() => {
    const drawerOpen =
      isNarrow && (currentNarrowDrawers.inspector || currentNarrowDrawers.session);
    if (drawerOpen) {
      const previous = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = previous;
      };
    }
  }, [isNarrow, currentNarrowDrawers.inspector, currentNarrowDrawers.session]);

  useEffect(() => {
    if (!isNarrow || (!currentNarrowDrawers.inspector && !currentNarrowDrawers.session)) {
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
  }, [isNarrow, currentNarrowDrawers.inspector, currentNarrowDrawers.session]);

  useFocusTrap(
    currentNarrowDrawers.inspector,
    inspectorShellRef,
    inspectorOpenButtonRef,
  );

  useFocusTrap(
    currentNarrowDrawers.session,
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
    function onTestVisibility(event: Event) {
      const custom = event as CustomEvent<{ visible?: unknown }>;
      const visible = custom.detail?.visible;
      if (typeof visible !== "boolean") {
        return;
      }
      setIsPageVisible(visible);
    }
    window.addEventListener(
      "insightagent:test-page-visibility",
      onTestVisibility as EventListener,
    );
    return () => {
      window.removeEventListener(
        "insightagent:test-page-visibility",
        onTestVisibility as EventListener,
      );
    };
  }, []);

  useEffect(() => {
    if (!isStreaming) {
      traceDeltaRetryCountRef.current = 0;
      return;
    }
    if (!isPageVisible) {
      return;
    }
    const taskId = sseTaskId?.trim() ?? "";
    if (!taskId) {
      traceDeltaRetryCountRef.current = 0;
      return;
    }
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
        void syncTraceDelta(taskId, { silent: true }).then((result) => {
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

  const runningTaskIds = recentTasks
    .filter((task) => isTaskRunningLike(task))
    .map((task) => task.id);
  const activeSessionRunningTask = activeSessionId && isPageVisible
    ? recentTasks
        .filter(
          (task) =>
            task.session_id === activeSessionId && isTaskRunningLike(task),
        )
        .sort(
          (a, b) =>
            Date.parse(b.updated_at || "") - Date.parse(a.updated_at || ""),
        )[0]
    : null;
  const runningTaskId = activeSessionRunningTask?.id.trim() ?? "";
  const currentTaskId = streamSessionMatchesActive ? (sseTaskId?.trim() ?? "") : "";
  const recoveryCandidateId = runningTaskId &&
    !(isStreaming && !streamSessionMatchesActive) &&
    currentTaskId !== runningTaskId
      ? runningTaskId
      : null;
  const currentRecoveryPreparation = reconcileRecoveryPreparation(
    recoveryPreparation,
    runningTaskIds,
    recoveryCandidateId,
  );
  if (currentRecoveryPreparation !== recoveryPreparation) {
    setRecoveryPreparation(currentRecoveryPreparation);
    if (
      currentRecoveryPreparation.launchTaskId &&
      currentRecoveryPreparation.launchTaskId !== recoveryPreparation.launchTaskId
    ) {
      setInspectorTab("trace");
      setRecoveryNotice({
        type: "info",
        text: t.stream.streamRecoveryStart(currentRecoveryPreparation.launchTaskId),
      });
    }
  }

  useEffect(() => {
    const recoveringTaskId = recoveringTaskIdRef.current;
    if (
      recoveringTaskId &&
      !recentTasks.some((task) => task.id === recoveringTaskId && isTaskRunningLike(task))
    ) {
      recoveringTaskIdRef.current = null;
    }
  }, [recentTasks]);

  useEffect(() => {
    if (!activeSessionId || !isPageVisible || !activeSessionRunningTask) {
      return;
    }
    if (!runningTaskId || currentRecoveryPreparation.launchTaskId !== runningTaskId) {
      return;
    }
    if (recoveringTaskIdRef.current === runningTaskId) {
      return;
    }
    if (isStreaming && !streamSessionMatchesActive) {
      return;
    }
    if (currentTaskId && currentTaskId === runningTaskId) {
      return;
    }

    recoveringTaskIdRef.current = runningTaskId;
    let recoveryConnected = false;
    void resumeTaskStream({
      apiBaseUrl: API_BASE_URL,
      taskId: runningTaskId,
      initialStatus:
        activeSessionRunningTask.status_normalized ??
        activeSessionRunningTask.status,
      onSessionResolved: setActiveSessionId,
      sessionId: activeSessionId,
      onStreamConnected: () => {
        recoveryConnected = true;
        setRecoveryNotice({
          type: "success",
          text: t.stream.streamRecoveryDone(runningTaskId),
        });
      },
    })
      .then((ok) => {
        if (!ok) {
          setRecoveryNotice({
            type: "error",
            text: t.stream.streamRecoveryFailed(runningTaskId),
          });
        } else if (!recoveryConnected) {
          setRecoveryNotice({
            type: "success",
            text: t.stream.streamRecoveryDone(runningTaskId),
          });
        }
      });
  }, [
    activeSessionId,
    activeSessionRunningTask,
    currentRecoveryPreparation.launchTaskId,
    currentTaskId,
    isPageVisible,
    isStreaming,
    resumeTaskStream,
    runningTaskId,
    streamSessionMatchesActive,
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
    if (
      settingsSummary?.mode === "remote" &&
      currentCancelSendCooldownUntil !== null
    ) {
      message.info(t.workbench.composerCoolingDown);
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
      setLastSentPrompt(text);
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
        onSessionResolved: (resolvedSessionId) => {
          const currentActiveSessionId = activeSessionIdRef.current?.trim() ?? "";
          const startedSessionId = sessionId.trim();
          if (!currentActiveSessionId || currentActiveSessionId === startedSessionId) {
            setActiveSessionId(resolvedSessionId);
          }
          void queryClient.invalidateQueries({ queryKey: ["tasks"] });
          void queryClient.invalidateQueries({
            queryKey: ["messages", resolvedSessionId],
          });
        },
      });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({
        queryKey: ["messages", sessionId],
      });
    } catch (error) {
      const u = toUserFacingError(error, t.errors);
      setBannerError(`${u.banner}${u.hint ? ` ${u.hint}` : ""}`);
    }
  }

  function handleRetryStream() {
    resetStreamUi();
    if (!prompt.trim() && lastSentPrompt) {
      setPrompt(lastSentPrompt);
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

  const openTaskCenterDrawer = useCallback(() => {
    if (activeSessionId) {
      setTaskCenterScope("session");
    } else {
      setTaskCenterScope("global");
    }
    setTaskCenterDrawerOpen(true);
    if (isNarrow) {
      setInspectorDrawerOpen(false);
      setSessionDrawerOpen(false);
    }
  }, [activeSessionId, isNarrow]);

  function handleLoadPersistedTrace() {
    const taskId = scopedSseTaskId?.trim() ?? "";
    setInspectorTab("trace");
    if (isNarrow) {
      openInspectorDrawer();
    }
    void loadPersistedTrace(API_BASE_URL, taskId);
  }

  function handleLoadTraceDelta() {
    const taskId = scopedSseTaskId?.trim() ?? "";
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
    setTaskCenterDrawerOpen(false);
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

  const activeSession = recentSessions.find((s) => s.id === activeSessionId);
  const activeTaskIdScoped = scopedSseTaskId;
  const activeTaskFromList = recentTasksScoped.find(
    (task) => task.id === activeTaskIdScoped,
  );
  const activeTask = useMemo(() => {
    if (activeTaskFromList) {
      return activeTaskFromList;
    }
    const taskId = activeTaskIdScoped?.trim() ?? "";
    const sessionId = activeSessionId?.trim() ?? "";
    if (!taskId || !sessionId) {
      return undefined;
    }
    const phase = (scopedSsePhase ?? "").trim().toLowerCase();
    const runningLike = scopedIsStreaming || RUNNING_STREAM_PHASES.has(phase);
    if (!runningLike) {
      return undefined;
    }
    const nowIso = new Date().toISOString();
    const prompt = lastSentPrompt.trim();
    return {
      id: taskId,
      session_id: sessionId,
      prompt,
      status: "running",
      status_normalized: "running",
      status_label: "running",
      status_rank: 30,
      trace_json: null,
      usage_json: null,
      created_at: nowIso,
      updated_at: nowIso,
    } satisfies TaskSummary;
  }, [
    activeTaskFromList,
    activeTaskIdScoped,
    activeSessionId,
    lastSentPrompt,
    scopedIsStreaming,
    scopedSsePhase,
  ]);
  const latestTaskForSession = recentTasksScoped.find(
    (t) => t.session_id === activeSessionId,
  );

  const phaseLabelMap: Record<string, string> = {
    done: t.workbench.phaseDone,
    error: t.workbench.phaseError,
    cancelled: t.workbench.phaseCancelled,
    timeout: t.workbench.phaseTimeout,
    replay: t.workbench.phaseReplay,
    streaming: t.workbench.phaseRunning,
    queued:
      scopedSseQueue?.waitPosition && scopedSseQueue.waitPosition > 0
        ? t.workbench.phaseQueuedPosition(scopedSseQueue.waitPosition)
        : t.workbench.phaseQueued,
    running: t.workbench.phaseRunning,
    pending: t.workbench.phaseRunning,
    thinking: t.workbench.phaseRunning,
    tool_running: t.workbench.phaseRunning,
    tool_retry: t.workbench.phaseRunning,
  };
  const phaseLabel = scopedSsePhase
    ? (phaseLabelMap[scopedSsePhase] ?? scopedSsePhase)
    : scopedIsStreaming
      ? t.workbench.phaseRunning
      : t.workbench.phaseIdle;
  const cancellingTaskId = cancelTaskMutation.isPending
    ? (cancelTaskMutation.variables ?? null)
    : null;
  const remoteSendCoolingDown =
    currentCancelSendCooldownUntil !== null;

  let composerHint = t.workbench.composerEnterSend;
  let composerHintVariant: "default" | "error" = "default";
  if (scopedIsStreaming) {
    composerHint = t.workbench.composerGenerating;
  } else if (remoteSendCoolingDown) {
    composerHint = t.workbench.composerCoolingDown;
  }
  if (scopedSsePhase === "error") {
    composerHint = scopedSseMessage;
    composerHintVariant = "error";
  }

  const onSidebarResizeStart = useCallback(
    (event: React.MouseEvent) => {
      if (sidebarCollapsed || isNarrow) return;
      event.preventDefault();
      const startX = event.clientX;
      const startW = sidebarWidthPx;
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
    [isNarrow, setSidebarWidthPx, sidebarCollapsed, sidebarWidthPx],
  );

  const onInspectorResizeStart = useCallback(
    (event: React.MouseEvent) => {
      if (inspectorCollapsed || isNarrow) return;
      event.preventDefault();
      const startX = event.clientX;
      const startW = inspectorWidthPx;
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
    [inspectorCollapsed, inspectorWidthPx, isNarrow, setInspectorWidthPx],
  );

  const shellClass = [
    "app-shell",
    !isNarrow && sidebarCollapsed ? "app-shell--sidebar-collapsed" : "",
    !isNarrow && inspectorCollapsed ? "app-shell--inspector-collapsed" : "",
    currentNarrowDrawers.inspector ? "inspector-drawer-open" : "",
    currentNarrowDrawers.session ? "session-drawer-open" : "",
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
        onExportSession={handleExportSession}
        sessionExporting={sessionExporting}
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
        key="chat-view"
        activeSession={activeSession}
        activeSessionId={activeSessionId}
        settingsSummary={settingsSummary}
        isStreaming={scopedIsStreaming}
        apiBanner={currentQueryBanner.banner}
        onDismissBanner={() => setBannerError(null)}
        sessionMessages={sessionMessages}
        recentTasks={recentTasks}
        activeTraceSteps={scopedSseTraceSteps}
        pendingUserInput={scopedIsStreaming ? lastSentPrompt : ""}
        pendingUserTaskId={scopedSseTaskId}
        messagesLoading={messagesLoading}
        messagesMessage={messagesMessage}
        sseTokens={scopedSseTokens}
        ssePhase={scopedSsePhase}
        prompt={prompt}
        onPromptChange={setPrompt}
        onSend={handleSend}
        sendDisabled={scopedIsStreaming || remoteSendCoolingDown || !prompt.trim()}
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
        showStreamRetry={scopedSsePhase === "error" && !scopedIsStreaming}
        onRetryStream={handleRetryStream}
        onOpenTaskCenter={openTaskCenterDrawer}
        composerRef={composerRef}
        liveRegionText={liveRegionText}
        runtimeNotice={currentRuntimeNoticeDismissal.dismissed ? null : runtimeNotice}
        onOpenModelSettings={openModelSettings}
        onDismissRuntimeNotice={() => setRuntimeNoticeDismissal((current) => ({
          ...current,
          dismissed: true,
        }))}
        recoveryNotice={recoveryNotice}
        onDismissRecoveryNotice={() => setRecoveryNotice(null)}
      />

      <Drawer
        open={taskCenterDrawerOpen}
        onClose={() => setTaskCenterDrawerOpen(false)}
        placement="right"
        size={isNarrow ? "100vw" : "min(880px, 92vw)"}
        closable={false}
        destroyOnClose={false}
        maskClosable
        className="task-center-drawer"
        styles={{ body: { padding: 0 } }}
      >
        <TaskCenter
          activeSession={activeSession}
          activeSessionId={activeSessionId}
          activeTaskId={activeTaskIdScoped}
          recentTasks={recentTasks}
          taskSearchQuery={taskSearchQuery}
          onTaskSearchQueryChange={setTaskSearchQuery}
          taskGovernanceProfileFilter={taskGovernanceProfileFilter}
          onTaskGovernanceProfileFilterChange={setTaskGovernanceProfileFilter}
          taskGovernanceProviderSourceFilter={taskGovernanceProviderSourceFilter}
          onTaskGovernanceProviderSourceFilterChange={
            setTaskGovernanceProviderSourceFilter
          }
          availableToolRegistryProfiles={
            settingsQuery.data?.available_tool_registry_profiles ?? []
          }
          availableToolRegistryProviderSources={
            settingsQuery.data?.available_tool_registry_provider_sources ?? []
          }
          tasksLoading={tasksQuery.isLoading}
          tasksFetching={tasksQuery.isFetching}
          tasksError={tasksErrorText}
          onRetryTasks={() => {
            void tasksQuery.refetch();
          }}
          onSelectTask={handleSelectTask}
          onClose={() => setTaskCenterDrawerOpen(false)}
          scopeMode={currentTaskCenterScope}
          onScopeModeChange={setTaskCenterScope}
        />
      </Drawer>

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
        isStreaming={scopedIsStreaming}
        sseTraceSteps={scopedSseTraceSteps}
        sseMessage={scopedSseMessage}
        sseTaskId={scopedSseTaskId}
        phaseLabel={phaseLabel}
        traceCursor={scopedTraceCursor}
        traceDeltaSyncStatus={traceDeltaSyncStatus}
        traceDeltaRetryCount={traceDeltaRetryCount}
        traceDeltaLastOkAt={traceDeltaLastOkAt}
        traceDeltaLastError={traceDeltaLastError}
        traceDeltaNextRetryAt={traceDeltaNextRetryAt}
        traceDeltaRecoveredAt={traceDeltaRecoveredAt}
        activeSessionId={activeSessionId}
        activeTaskId={activeTaskIdScoped}
        activeTask={activeTask}
        recentTasksScoped={recentTasksScoped}
        sseTaskUsage={scopedSseTaskUsage}
        latestTaskForSession={latestTaskForSession}
        onReplayTrace={handleLoadPersistedTrace}
        onLoadDelta={handleLoadTraceDelta}
        onCancelTask={(task) => {
          cancelTaskMutation.mutate(task.id);
        }}
        cancellingTaskId={cancellingTaskId}
        onOpenTaskCenter={openTaskCenterDrawer}
      />
    </main>
  );
}
