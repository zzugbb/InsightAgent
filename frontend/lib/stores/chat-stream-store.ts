import { create } from "zustand";

import { authFetch } from "../api-client";
import { en, type Messages } from "../i18n";
import { parseSseBlock, parseSseBlocks } from "../sse/parse";
import type { TraceStepPayload } from "../types/trace";

export type { TraceStepPayload } from "../types/trace";

const DEFAULT_STREAM_MESSAGES: Messages["stream"] = en.stream;

const KNOWN_SSE_PHASES = new Set([
  "pending",
  "running",
  "thinking",
  "tool_running",
  "tool_retry",
  "streaming",
  "cancelled",
  "timeout",
  "replay",
  "error",
  "done",
]);

function normalizeSsePhase(raw: unknown): string | null {
  if (typeof raw !== "string") {
    return null;
  }
  const phase = raw.trim().toLowerCase();
  if (!phase) {
    return null;
  }
  if (phase === "completed" || phase === "done") {
    return "done";
  }
  if (phase === "failed") {
    return "error";
  }
  if (KNOWN_SSE_PHASES.has(phase)) {
    return phase;
  }
  return phase;
}

function normalizeTraceSteps(steps: TraceStepPayload[]): TraceStepPayload[] {
  return [...steps]
    .map((step, index) => ({ step, index }))
    .sort((a, b) => {
      const aSeq =
        typeof a.step.seq === "number" ? a.step.seq : Number.MAX_SAFE_INTEGER;
      const bSeq =
        typeof b.step.seq === "number" ? b.step.seq : Number.MAX_SAFE_INTEGER;
      if (aSeq === bSeq) {
        return a.index - b.index;
      }
      return aSeq - bSeq;
    })
    .map((entry) => entry.step);
}

const MAX_TRACE_STEPS = 2000;

function capTraceSteps(steps: TraceStepPayload[]): TraceStepPayload[] {
  if (steps.length <= MAX_TRACE_STEPS) {
    return steps;
  }
  return steps.slice(steps.length - MAX_TRACE_STEPS);
}

function getNextTraceCursor(steps: TraceStepPayload[]): number {
  return steps.reduce((maxSeq, step, index) => {
    const fallbackSeq = index + 1;
    const seq = typeof step.seq === "number" ? step.seq : fallbackSeq;
    return Math.max(maxSeq, seq);
  }, 0);
}

function upsertTraceStep(
  steps: TraceStepPayload[],
  step: TraceStepPayload,
): TraceStepPayload[] {
  const index = steps.findIndex((s) => s.id === step.id);
  if (index >= 0) {
    const next = [...steps];
    next[index] = { ...next[index], ...step };
    return capTraceSteps(normalizeTraceSteps(next));
  }
  return capTraceSteps(normalizeTraceSteps([...steps, step]));
}

export type RunTaskStreamOptions = {
  apiBaseUrl: string;
  prompt: string;
  sessionId: string | null;
  onSessionResolved?: (sessionId: string) => void;
};

export type ResumeTaskStreamOptions = {
  apiBaseUrl: string;
  taskId: string;
  afterSeq?: number;
  sessionId?: string | null;
  onSessionResolved?: (sessionId: string) => void;
};

type TaskCreateResponse = {
  task_id: string;
  session_id: string;
  status: string;
};

export type SseTaskUsage = {
  taskId: string;
  usage: Record<string, unknown>;
};

export type ChatStreamStore = {
  isStreaming: boolean;
  sseMessage: string;
  sseTokens: string;
  sseTraceSteps: TraceStepPayload[];
  ssePhase: string | null;
  sseTaskId: string | null;
  sseSessionId: string | null;
  /** 最近一次 `done` 事件携带的用量，按 taskId 对齐，避免切换任务后串台 */
  sseTaskUsage: SseTaskUsage | null;
  traceCursor: number;
  streamMessages: Messages["stream"];

  resetStreamUi: () => void;
  setStreamMessages: (messages: Messages["stream"]) => void;
  dispatchSseEvent: (
    event: string,
    payload: unknown,
    onSessionResolved?: (sessionId: string) => void,
  ) => void;
  setIsStreaming: (value: boolean) => void;
  setSseMessage: (message: string) => void;
  loadPersistedTrace: (apiBaseUrl: string, taskId: string) => Promise<void>;
  loadTraceDelta: (
    apiBaseUrl: string,
    taskId: string,
    options?: { silent?: boolean },
  ) => Promise<{ ok: boolean; error: string | null; hasMore: boolean }>;
  cancelActiveStreamLocal: (options?: {
    taskId?: string | null;
    reason?: "cancelled" | "timeout";
  }) => boolean;
  resumeTaskStream: (options: ResumeTaskStreamOptions) => Promise<boolean>;
  runTaskStream: (options: RunTaskStreamOptions) => Promise<void>;
};

const initialSseMessage =
  DEFAULT_STREAM_MESSAGES.idleHint;
const TRACE_DELTA_FETCH_LIMIT = 200;
let activeStreamController: AbortController | null = null;
let activeStreamControllerTaskId: string | null = null;
let activeStreamRunId = 0;

function isAbortLikeError(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === "AbortError") ||
    (error instanceof Error && error.name === "AbortError")
  );
}

function setActiveStreamController(
  controller: AbortController,
  taskId: string | null,
): void {
  activeStreamController = controller;
  activeStreamControllerTaskId = taskId?.trim() || null;
}

function clearActiveStreamController(controller: AbortController): void {
  if (activeStreamController !== controller) {
    return;
  }
  activeStreamController = null;
  activeStreamControllerTaskId = null;
}

async function consumeSseStream(
  response: Response,
  dispatchSseEvent: ChatStreamStore["dispatchSseEvent"],
  onSessionResolved?: (sessionId: string) => void,
): Promise<void> {
  const body = response.body;
  if (!body) {
    throw new Error("Response has no body.");
  }

  const reader = body.getReader();
  const decoder = new TextDecoder();
  let carry = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    carry += decoder.decode(value, { stream: true });
    const { remainder, blocks } = parseSseBlocks(carry);
    carry = remainder;

    for (const block of blocks) {
      const parsed = parseSseBlock(block);
      if (!parsed) {
        continue;
      }
      let payload: unknown;
      try {
        payload = JSON.parse(parsed.data) as unknown;
      } catch {
        continue;
      }
      dispatchSseEvent(parsed.event, payload, onSessionResolved);
    }
  }
}

export const useChatStreamStore = create<ChatStreamStore>((set, get) => ({
  isStreaming: false,
  sseMessage: initialSseMessage,
  sseTokens: "",
  sseTraceSteps: [],
  ssePhase: null,
  sseTaskId: null,
  sseSessionId: null,
  sseTaskUsage: null,
  traceCursor: 0,
  streamMessages: DEFAULT_STREAM_MESSAGES,

  resetStreamUi: () =>
    set({
      sseTokens: "",
      sseTraceSteps: [],
      ssePhase: null,
      sseTaskId: null,
      sseSessionId: null,
      sseTaskUsage: null,
      traceCursor: 0,
    }),

  setIsStreaming: (value) => set({ isStreaming: value }),

  setSseMessage: (message) => set({ sseMessage: message }),

  setStreamMessages: (messages) =>
    set((state) => {
      const shouldRefreshIdleHint =
        !state.isStreaming &&
        state.ssePhase === null &&
        state.sseTaskId === null &&
        state.sseTokens.length === 0;
      return {
        streamMessages: messages,
        ...(shouldRefreshIdleHint ? { sseMessage: messages.idleHint } : {}),
      };
    }),

  loadPersistedTrace: async (apiBaseUrl, taskId) => {
    const sm = get().streamMessages;
    const normalizedTaskId = taskId.trim();
    if (!normalizedTaskId) {
      set({ sseMessage: sm.taskIdRequiredTrace });
      return;
    }

    set({
      sseMessage: sm.loadingPersistedTrace,
      sseTaskId: normalizedTaskId,
      sseTokens: "",
      sseTraceSteps: [],
      ssePhase: "replay",
      traceCursor: 0,
      sseTaskUsage: null,
    });

    try {
      const response = await authFetch(
        `${apiBaseUrl}/api/tasks/${normalizedTaskId}/trace`,
        {
          cache: "no-store",
        },
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          errorText || `${sm.failedLoadPersistedTrace} (${response.status})`,
        );
      }

      const data = (await response.json()) as {
        task_id: string;
        steps?: TraceStepPayload[];
        status?: string;
      };
      const steps = Array.isArray(data.steps) ? data.steps : [];
      const traceCursor = getNextTraceCursor(steps);

      set({
        sseTaskId: data.task_id || normalizedTaskId,
        sseTraceSteps: capTraceSteps(normalizeTraceSteps(steps)),
        ssePhase:
          typeof data.status === "string"
            ? (normalizeSsePhase(data.status) ?? "replay")
            : "replay",
        traceCursor,
        sseMessage:
          steps.length > 0
            ? sm.persistedTraceLoaded
            : sm.persistedTraceEmpty,
      });
    } catch (error) {
      set({
        sseMessage: error instanceof Error ? error.message : sm.failedLoadPersistedTrace,
      });
    }
  },

  loadTraceDelta: async (apiBaseUrl, taskId, options) => {
    const sm = get().streamMessages;
    const silent = options?.silent === true;
    const normalizedTaskId = taskId.trim();
    if (!normalizedTaskId) {
      if (!silent) {
        set({ sseMessage: sm.taskIdRequiredDelta });
      }
      return {
        ok: false,
        error: sm.taskIdRequiredDelta,
        hasMore: false,
      };
    }

    const currentCursor = get().traceCursor;
    const currentTaskId = get().sseTaskId?.trim() ?? "";
    if (currentTaskId && currentTaskId !== normalizedTaskId) {
      return {
        ok: true,
        error: null,
        hasMore: false,
      };
    }
    if (!silent) {
      set({
        sseMessage: sm.loadingTraceDeltaAfter(currentCursor),
      });
    } else if (!currentTaskId) {
      set({
        sseTaskId: normalizedTaskId,
      });
    }

    try {
      const response = await authFetch(
        `${apiBaseUrl}/api/tasks/${normalizedTaskId}/trace/delta?after_seq=${currentCursor}&limit=${TRACE_DELTA_FETCH_LIMIT}`,
        {
          cache: "no-store",
        },
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          errorText || `${sm.failedLoadTraceDelta} (${response.status})`,
        );
      }

      const data = (await response.json()) as {
        task_id: string;
        steps?: TraceStepPayload[];
        next_cursor?: number;
        has_more?: boolean;
      };
      const steps = Array.isArray(data.steps) ? data.steps : [];

      set((state) => {
        const targetTaskId = (data.task_id || normalizedTaskId).trim();
        const activeTaskId = state.sseTaskId?.trim() ?? "";
        if (activeTaskId && targetTaskId !== activeTaskId) {
          return state;
        }
        return {
          sseTaskId: data.task_id || normalizedTaskId,
          sseTraceSteps: steps.reduce(
            (mergedSteps, step) => upsertTraceStep(mergedSteps, step),
            state.sseTraceSteps,
          ),
          traceCursor:
            typeof data.next_cursor === "number"
              ? Math.max(state.traceCursor, data.next_cursor)
              : Math.max(state.traceCursor, getNextTraceCursor(steps)),
          sseMessage: silent
            ? state.sseMessage
            : steps.length > 0
              ? data.has_more
                ? sm.traceDeltaLoadedMore(steps.length)
                : sm.traceDeltaLoaded(steps.length)
              : sm.traceDeltaEmpty,
        };
      });
      return { ok: true, error: null, hasMore: data.has_more === true };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : sm.failedLoadTraceDelta;
      if (!silent) {
        set({
          sseMessage: errorMessage,
        });
      }
      return { ok: false, error: errorMessage, hasMore: false };
    }
  },

  cancelActiveStreamLocal: (options) => {
    const sm = get().streamMessages;
    const targetTaskId = options?.taskId?.trim() ?? "";
    const reason = options?.reason ?? "cancelled";
    const activeTaskId = get().sseTaskId?.trim() ?? "";
    if (targetTaskId && activeTaskId && targetTaskId !== activeTaskId) {
      return false;
    }

    if (activeStreamController) {
      const streamTaskId = activeStreamControllerTaskId?.trim() ?? "";
      if (!targetTaskId || !streamTaskId || streamTaskId === targetTaskId) {
        activeStreamController.abort();
      }
    }

    set({
      isStreaming: false,
      ssePhase: reason === "timeout" ? "timeout" : "cancelled",
      sseMessage:
        reason === "timeout" ? sm.streamTimeout : sm.streamCancelled,
    });
    return true;
  },

  dispatchSseEvent: (event, payload, onSessionResolved) => {
    if (payload && typeof payload === "object") {
      const p = payload as Record<string, unknown>;
      const eventTaskId =
        typeof p.task_id === "string" ? p.task_id.trim() : "";
      const activeTaskId = get().sseTaskId?.trim() ?? "";
      if (
        event !== "start" &&
        activeTaskId &&
        (!eventTaskId || eventTaskId !== activeTaskId)
      ) {
        return;
      }
    }

    if (event === "start" && payload && typeof payload === "object") {
      const sm = get().streamMessages;
      const p = payload as Record<string, unknown>;
      if (typeof p.task_id === "string") {
        set({ sseTaskId: p.task_id });
      }
      if (typeof p.session_id === "string") {
        set({ sseSessionId: p.session_id });
        onSessionResolved?.(p.session_id);
      }
      set({ sseMessage: sm.streamStarted });
      return;
    }
    if (event === "state" && payload && typeof payload === "object") {
      const p = payload as Record<string, unknown>;
      const normalizedPhase = normalizeSsePhase(p.phase);
      if (normalizedPhase) {
        set({ ssePhase: normalizedPhase });
      }
      return;
    }
    if (event === "trace" && payload && typeof payload === "object") {
      const p = payload as Record<string, unknown>;
      const step = p.step;
      if (step && typeof step === "object") {
        const s = step as Record<string, unknown>;
        if (typeof s.id === "string" && typeof s.type === "string") {
          const stepId = s.id;
          const stepType = s.type;
          const content = typeof s.content === "string" ? s.content : "";
          const meta =
            s.meta && typeof s.meta === "object"
              ? (s.meta as Record<string, unknown>)
              : undefined;
          set((state) => {
            const mergedSteps = upsertTraceStep(state.sseTraceSteps, {
              id: stepId,
              type: stepType,
              content,
              seq: typeof s.seq === "number" ? s.seq : undefined,
              meta,
            });
            return {
              sseTraceSteps: mergedSteps,
              traceCursor: Math.max(
                state.traceCursor,
                typeof s.seq === "number" ? s.seq : getNextTraceCursor(mergedSteps),
              ),
            };
          });
        }
      }
      return;
    }
    if (event === "tool_start" && payload && typeof payload === "object") {
      const sm = get().streamMessages;
      const p = payload as Record<string, unknown>;
      if (typeof p.step_id === "string" && typeof p.name === "string") {
        const stepId = p.step_id;
        const toolName = p.name;
        const toolInput = p.input;
        const retryCount =
          typeof p.retry_count === "number" ? p.retry_count : undefined;
        set((state) => ({
          sseTraceSteps: upsertTraceStep(state.sseTraceSteps, {
            id: stepId,
            type: "action",
            content: sm.toolRunning(toolName),
            meta: {
              ...(state.sseTraceSteps.find((x) => x.id === stepId)?.meta ?? {}),
              step_type: "tool_call",
              tool: {
                name: toolName,
                input: toolInput,
                status: "running",
                retry_count: retryCount ?? 0,
              },
            },
          }),
          sseMessage: sm.toolStarted(toolName),
        }));
      }
      return;
    }
    if (event === "tool_end" && payload && typeof payload === "object") {
      const sm = get().streamMessages;
      const p = payload as Record<string, unknown>;
      if (
        typeof p.step_id === "string" &&
        typeof p.status === "string"
      ) {
        const stepId = p.step_id;
        const status = p.status;
        set((state) => {
          const prev = state.sseTraceSteps.find((x) => x.id === stepId);
          const prevMeta = prev?.meta ?? {};
          const prevTool =
            prevMeta.tool && typeof prevMeta.tool === "object"
              ? prevMeta.tool
              : undefined;
          const toolName =
            prevTool && typeof prevTool.name === "string"
              ? prevTool.name
              : "tool";
          return {
            sseTraceSteps: upsertTraceStep(state.sseTraceSteps, {
              id: stepId,
              type: "action",
              content: sm.toolStatus(status, toolName),
              meta: {
                ...prevMeta,
                step_type: "tool_call",
                retryCount:
                  typeof p.retry_count === "number" ? p.retry_count : undefined,
                latency:
                  typeof p.latency_ms === "number" ? p.latency_ms : undefined,
                tool: {
                  ...(prevTool ?? { name: toolName }),
                  output: p.output_preview,
                  retry_count:
                    typeof p.retry_count === "number" ? p.retry_count : undefined,
                  error: typeof p.error === "string" ? p.error : undefined,
                  status:
                    status === "running" || status === "error"
                      ? status
                      : "done",
                },
              },
            }),
            sseMessage: sm.toolStatus(status, toolName),
          };
        });
      }
      return;
    }
    if (event === "token" && payload && typeof payload === "object") {
      const p = payload as Record<string, unknown>;
      if (typeof p.delta === "string") {
        const delta = p.delta;
        set((state) => {
          if (typeof p.step_id !== "string") {
            return { sseTokens: state.sseTokens + delta };
          }
          const stepId = p.step_id;
          const prevStep = state.sseTraceSteps.find((x) => x.id === stepId);
          return {
            sseTokens: state.sseTokens + delta,
            sseTraceSteps: upsertTraceStep(state.sseTraceSteps, {
              id: stepId,
              type: "observation",
              content: (prevStep?.content ?? "") + delta,
              meta: prevStep?.meta,
            }),
          };
        });
      }
      return;
    }
    if (event === "done") {
      const sm = get().streamMessages;
      let nextUsage: SseTaskUsage | null = null;
      let nextSessionId: string | null = null;
      if (payload && typeof payload === "object") {
        const p = payload as Record<string, unknown>;
        const tid = p.task_id;
        const sid = p.session_id;
        const u = p.usage;
        if (typeof sid === "string" && sid.trim()) {
          nextSessionId = sid.trim();
        }
        if (
          typeof tid === "string" &&
          u &&
          typeof u === "object" &&
          !Array.isArray(u)
        ) {
          nextUsage = { taskId: tid, usage: u as Record<string, unknown> };
        }
      }
      set({
        ssePhase: "done",
        sseMessage: sm.streamCompleted,
        sseSessionId: nextSessionId ?? get().sseSessionId,
        sseTaskUsage: nextUsage,
      });
      return;
    }
    if (event === "cancelled") {
      const sm = get().streamMessages;
      set({
        ssePhase: "cancelled",
        sseMessage: sm.streamCancelled,
      });
      return;
    }
    if (event === "timeout") {
      const sm = get().streamMessages;
      set({
        ssePhase: "timeout",
        sseMessage: sm.streamTimeout,
      });
      return;
    }
    if (event === "error" && payload && typeof payload === "object") {
      const sm = get().streamMessages;
      const p = payload as Record<string, unknown>;
      const code =
        typeof p.code === "string" && p.code.trim().length > 0
          ? p.code.trim()
          : null;
      const normalizedCode = code ? code.toLowerCase() : null;
      if (normalizedCode === "task_cancelled") {
        set({
          ssePhase: "cancelled",
          sseMessage: sm.streamCancelled,
        });
        return;
      }
      if (normalizedCode === "task_timeout") {
        set({
          ssePhase: "timeout",
          sseMessage: sm.streamTimeout,
        });
        return;
      }
      const backendMessage =
        typeof p.message === "string" && p.message.trim().length > 0
          ? p.message.trim()
          : sm.streamErrorFallback;
      const mappedMessage = code ? sm.streamErrorByCode(code) : null;
      const detail =
        typeof p.detail === "string" && p.detail.trim().length > 0
          ? p.detail.trim()
          : null;
      const statusCode =
        typeof p.status_code === "number" && Number.isFinite(p.status_code)
          ? p.status_code
          : null;
      const payloadSessionId =
        typeof p.session_id === "string" && p.session_id.trim().length > 0
          ? p.session_id.trim()
          : null;
      const baseMessage = mappedMessage ?? backendMessage;
      const withStatus =
        statusCode !== null ? `${baseMessage} (HTTP ${statusCode})` : baseMessage;
      const withDetail =
        detail && mappedMessage ? `${withStatus} [${detail}]` : withStatus;
      const msg = code ? `[${code}] ${withDetail}` : withDetail;
      const fatal = typeof p.fatal === "boolean" ? p.fatal : null;
      const retryCount =
        typeof p.retryCount === "number" ? p.retryCount : null;
      set((state) => ({
        ssePhase: fatal ? "error" : state.ssePhase,
        sseMessage: sm.streamErrorMessage(msg, fatal, retryCount),
        sseSessionId: payloadSessionId ?? state.sseSessionId,
      }));
      return;
    }
    if (event === "heartbeat") {
      const sm = get().streamMessages;
      set((state) => ({
        sseMessage: state.sseMessage.startsWith(sm.streamStarted)
          ? state.sseMessage
          : sm.streamHeartbeat,
      }));
    }
  },

  resumeTaskStream: async (options) => {
    const sm = get().streamMessages;
    const taskId = options.taskId.trim();
    if (!taskId) {
      set({ sseMessage: sm.taskIdRequiredTrace });
      return false;
    }

    if (get().isStreaming) {
      const currentTaskId = get().sseTaskId?.trim() ?? "";
      if (currentTaskId === taskId) {
        return true;
      }
      return false;
    }

    const currentTaskId = get().sseTaskId?.trim() ?? "";
    const fallbackCursor = currentTaskId === taskId ? get().traceCursor : 0;
    const rawAfterSeq =
      typeof options.afterSeq === "number" ? options.afterSeq : fallbackCursor;
    const afterSeq = Math.max(
      0,
      Math.floor(Number.isFinite(rawAfterSeq) ? rawAfterSeq : 0),
    );
    const runId = ++activeStreamRunId;
    let streamController: AbortController | null = null;

    set({
      isStreaming: true,
      sseMessage: sm.loadingTraceDeltaAfter(afterSeq),
      sseTokens: "",
      sseTraceSteps: [],
      ssePhase: "running",
      sseTaskId: taskId,
      sseSessionId: options.sessionId?.trim() || null,
      sseTaskUsage: null,
      traceCursor: afterSeq,
    });

    try {
      streamController = new AbortController();
      setActiveStreamController(streamController, taskId);
      const streamResponse = await authFetch(
        `${options.apiBaseUrl}/api/tasks/${taskId}/stream?after_seq=${afterSeq}`,
        {
          method: "GET",
          headers: {
            Accept: "text/event-stream",
          },
          signal: streamController.signal,
        },
      );

      if (!streamResponse.ok) {
        const errorText = await streamResponse.text();
        if (streamResponse.status === 409) {
          set((state) => ({
            ssePhase:
              state.ssePhase === "running" ||
              state.ssePhase === "pending" ||
              state.ssePhase === "streaming"
                ? "done"
                : state.ssePhase,
            sseMessage: sm.streamClosed,
          }));
          return true;
        }
        throw new Error(
          errorText || `${sm.failedReadStream} (${streamResponse.status})`,
        );
      }

      await consumeSseStream(
        streamResponse,
        get().dispatchSseEvent,
        options.onSessionResolved,
      );

      set((state) => ({
        sseMessage:
          state.ssePhase === "done" ||
          state.ssePhase === "cancelled" ||
          state.ssePhase === "timeout" ||
          state.ssePhase === "error"
            ? state.sseMessage
            : sm.streamClosed,
      }));
      return true;
    } catch (error) {
      if (isAbortLikeError(error)) {
        return get().ssePhase === "cancelled" || get().ssePhase === "timeout";
      }
      set({
        sseMessage:
          error instanceof Error ? error.message : sm.failedReadStream,
      });
      return false;
    } finally {
      if (streamController) {
        clearActiveStreamController(streamController);
      }
      if (activeStreamRunId === runId) {
        set({ isStreaming: false });
      }
    }
  },

  runTaskStream: async (options) => {
    const sm = get().streamMessages;
    const prompt = options.prompt.trim();
    if (!prompt) {
      set({ sseMessage: sm.promptEmpty });
      return;
    }

    const runId = ++activeStreamRunId;
    let streamController: AbortController | null = null;
    const { onSessionResolved } = options;
    set({
      isStreaming: true,
      sseMessage: sm.creatingAndOpening,
      sseTokens: "",
      sseTraceSteps: [],
      ssePhase: null,
      sseTaskId: null,
      sseSessionId: options.sessionId?.trim() || null,
      sseTaskUsage: null,
      traceCursor: 0,
    });

    try {
      const taskResponse = await authFetch(`${options.apiBaseUrl}/api/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_input: prompt,
          session_id: options.sessionId,
        }),
      });

      if (!taskResponse.ok) {
        const errorText = await taskResponse.text();
        throw new Error(
          errorText || `${sm.taskCreateFailed} (${taskResponse.status})`,
        );
      }

      const createdTask = (await taskResponse.json()) as TaskCreateResponse;
      set({
        sseTaskId: createdTask.task_id,
        sseSessionId: createdTask.session_id ?? options.sessionId ?? null,
        ssePhase: normalizeSsePhase(createdTask.status) ?? createdTask.status,
      });
      if (createdTask.session_id) {
        onSessionResolved?.(createdTask.session_id);
      }

      streamController = new AbortController();
      setActiveStreamController(streamController, createdTask.task_id);
      const streamResponse = await authFetch(
        `${options.apiBaseUrl}/api/tasks/${createdTask.task_id}/stream`,
        {
          method: "GET",
          headers: {
            Accept: "text/event-stream",
          },
          signal: streamController.signal,
        },
      );

      if (!streamResponse.ok) {
        const errorText = await streamResponse.text();
        throw new Error(
          errorText || `${sm.failedReadStream} (${streamResponse.status})`,
        );
      }

      await consumeSseStream(
        streamResponse,
        get().dispatchSseEvent,
        onSessionResolved,
      );

      set((state) => ({
        sseMessage:
          state.ssePhase === "done" ||
          state.ssePhase === "cancelled" ||
          state.ssePhase === "timeout" ||
          state.ssePhase === "error"
            ? state.sseMessage
            : sm.streamClosed,
      }));
    } catch (error) {
      if (isAbortLikeError(error)) {
        return;
      }
      set({
        sseMessage:
          error instanceof Error ? error.message : sm.failedReadStream,
      });
    } finally {
      if (streamController) {
        clearActiveStreamController(streamController);
      }
      if (activeStreamRunId === runId) {
        set({ isStreaming: false });
      }
    }
  },
}));
