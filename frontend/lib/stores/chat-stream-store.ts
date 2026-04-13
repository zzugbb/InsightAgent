import { create } from "zustand";

import type { Messages } from "../i18n";
import { parseSseBlock, parseSseBlocks } from "../sse/parse";
import type { TraceStepPayload } from "../types/trace";

export type { TraceStepPayload } from "../types/trace";

const DEFAULT_STREAM_MESSAGES: Messages["stream"] = {
  streamStarted: "Task stream started.",
  streamCompleted: "Task stream completed (done).",
  streamHeartbeat: "Receiving task stream (heartbeat ok).",
  loadingPersistedTrace: "Loading persisted trace...",
  persistedTraceLoaded: "Persisted trace loaded.",
  persistedTraceEmpty: "Persisted trace is empty for this task.",
  taskIdRequiredTrace: "Task ID is required to load trace.",
  failedLoadPersistedTrace: "Failed to load persisted trace.",
  taskIdRequiredDelta: "Task ID is required to load trace delta.",
  loadingTraceDeltaAfter: (seq) => `Loading trace delta after seq=${seq}...`,
  traceDeltaLoaded: (count) => `Trace delta loaded (${count} steps).`,
  traceDeltaLoadedMore: (count) =>
    `Trace delta loaded (${count} steps, more available).`,
  traceDeltaEmpty: "No new trace delta steps.",
  failedLoadTraceDelta: "Failed to load trace delta.",
  toolRunning: (name) => `Tool running: ${name}`,
  toolStarted: (name) => `Tool started: ${name}`,
  toolStatus: (status, name) => `Tool ${status}: ${name}`,
  streamErrorFallback: "Task stream error received.",
  streamErrorMessage: (message, fatal, retryCount) => {
    const fatalSuffix =
      fatal === null ? "" : fatal ? " (fatal)" : " (retryable)";
    const retrySuffix =
      typeof retryCount === "number" ? ` [retry=${retryCount}]` : "";
    return `Task stream error: ${message}${fatalSuffix}${retrySuffix}`;
  },
  promptEmpty: "Prompt cannot be empty.",
  creatingAndOpening: "Creating task and opening task stream...",
  taskCreateFailed: "Task creation failed.",
  streamClosed: "Task stream closed.",
  failedReadStream: "Failed to read task stream.",
};

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
    return normalizeTraceSteps(next);
  }
  return normalizeTraceSteps([...steps, step]);
}

export type RunTaskStreamOptions = {
  apiBaseUrl: string;
  prompt: string;
  sessionId: string | null;
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
  runTaskStream: (options: RunTaskStreamOptions) => Promise<void>;
};

const initialSseMessage =
  "发送消息后，执行过程会出现在右侧「轨迹」；连接与状态说明会显示在这里。";
const TRACE_DELTA_FETCH_LIMIT = 200;

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
  sseTaskUsage: null,
  traceCursor: 0,
  streamMessages: DEFAULT_STREAM_MESSAGES,

  resetStreamUi: () =>
    set({
      sseTokens: "",
      sseTraceSteps: [],
      ssePhase: null,
      sseTaskId: null,
      sseTaskUsage: null,
      traceCursor: 0,
    }),

  setIsStreaming: (value) => set({ isStreaming: value }),

  setSseMessage: (message) => set({ sseMessage: message }),

  setStreamMessages: (messages) => set({ streamMessages: messages }),

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
      const response = await fetch(
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
        sseTraceSteps: normalizeTraceSteps(steps),
        ssePhase: typeof data.status === "string" ? data.status : "replay",
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
      const response = await fetch(
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
          sseTraceSteps: normalizeTraceSteps(
            steps.reduce(
              (mergedSteps, step) => upsertTraceStep(mergedSteps, step),
              state.sseTraceSteps,
            ),
          ),
          traceCursor:
            typeof data.next_cursor === "number"
              ? data.next_cursor
              : Math.max(currentCursor, getNextTraceCursor(steps)),
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
        set((state) => ({ sseTokens: state.sseTokens + delta }));
        if (typeof p.step_id === "string") {
          const stepId = p.step_id;
          set((state) => ({
            sseTraceSteps: upsertTraceStep(state.sseTraceSteps, {
              id: stepId,
              type: "observation",
              content:
                (state.sseTraceSteps.find((x) => x.id === stepId)?.content ?? "") +
                delta,
              meta: state.sseTraceSteps.find((x) => x.id === stepId)?.meta,
            }),
          }));
        }
      }
      return;
    }
    if (event === "done") {
      const sm = get().streamMessages;
      let nextUsage: SseTaskUsage | null = null;
      if (payload && typeof payload === "object") {
        const p = payload as Record<string, unknown>;
        const tid = p.task_id;
        const u = p.usage;
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
        sseTaskUsage: nextUsage,
      });
      return;
    }
    if (event === "error" && payload && typeof payload === "object") {
      const sm = get().streamMessages;
      const p = payload as Record<string, unknown>;
      const msg =
        typeof p.message === "string" ? p.message : sm.streamErrorFallback;
      const fatal = typeof p.fatal === "boolean" ? p.fatal : null;
      const retryCount =
        typeof p.retryCount === "number" ? p.retryCount : null;
      set((state) => ({
        ssePhase: fatal ? "error" : state.ssePhase,
        sseMessage: sm.streamErrorMessage(msg, fatal, retryCount),
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

  runTaskStream: async (options) => {
    const sm = get().streamMessages;
    const prompt = options.prompt.trim();
    if (!prompt) {
      set({ sseMessage: sm.promptEmpty });
      return;
    }

    const { onSessionResolved } = options;
    set({
      isStreaming: true,
      sseMessage: sm.creatingAndOpening,
      sseTokens: "",
      sseTraceSteps: [],
      ssePhase: null,
      sseTaskId: null,
      sseTaskUsage: null,
      traceCursor: 0,
    });

    try {
      const taskResponse = await fetch(`${options.apiBaseUrl}/api/tasks`, {
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
        ssePhase: createdTask.status,
      });
      if (createdTask.session_id) {
        onSessionResolved?.(createdTask.session_id);
      }

      const streamResponse = await fetch(
        `${options.apiBaseUrl}/api/tasks/${createdTask.task_id}/stream`,
        {
          method: "GET",
          headers: {
            Accept: "text/event-stream",
          },
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
        sseMessage: state.sseMessage.includes(sm.streamCompleted)
          ? state.sseMessage
          : sm.streamClosed,
      }));
    } catch (error) {
      set({
        sseMessage:
          error instanceof Error ? error.message : sm.failedReadStream,
      });
    } finally {
      set({ isStreaming: false });
    }
  },
}));
