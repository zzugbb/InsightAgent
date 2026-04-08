import { create } from "zustand";

import { parseSseBlock, parseSseBlocks } from "../sse/parse";

/** 与后端 mock SSE `trace` 事件中的 `step` 对齐的最小形状 */
export type TraceStepPayload = {
  id: string;
  type: string;
  content: string;
  seq?: number;
  meta?: Record<string, unknown>;
};

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
    return next;
  }
  return [...steps, step];
}

export type RunChatStreamOptions = {
  apiBaseUrl: string;
  prompt: string;
  sessionId: string | null;
  onSessionResolved?: (sessionId: string) => void;
};

export type ChatStreamStore = {
  isStreaming: boolean;
  sseMessage: string;
  sseTokens: string;
  sseTraceSteps: TraceStepPayload[];
  ssePhase: string | null;
  sseTaskId: string | null;
  traceCursor: number;

  resetStreamUi: () => void;
  dispatchSseEvent: (
    event: string,
    payload: unknown,
    onSessionResolved?: (sessionId: string) => void,
  ) => void;
  setIsStreaming: (value: boolean) => void;
  setSseMessage: (message: string) => void;
  loadPersistedTrace: (apiBaseUrl: string, taskId: string) => Promise<void>;
  loadTraceDelta: (apiBaseUrl: string, taskId: string) => Promise<void>;
  runChatStream: (options: RunChatStreamOptions) => Promise<void>;
};

const initialSseMessage =
  "使用下方按钮通过 POST /api/chat/stream 拉取 SSE，展示 token 与 trace。";

export const useChatStreamStore = create<ChatStreamStore>((set, get) => ({
  isStreaming: false,
  sseMessage: initialSseMessage,
  sseTokens: "",
  sseTraceSteps: [],
  ssePhase: null,
  sseTaskId: null,
  traceCursor: 0,

  resetStreamUi: () =>
    set({
      sseTokens: "",
      sseTraceSteps: [],
      ssePhase: null,
      sseTaskId: null,
      traceCursor: 0,
    }),

  setIsStreaming: (value) => set({ isStreaming: value }),

  setSseMessage: (message) => set({ sseMessage: message }),

  loadPersistedTrace: async (apiBaseUrl, taskId) => {
    const normalizedTaskId = taskId.trim();
    if (!normalizedTaskId) {
      set({ sseMessage: "Task ID is required to load trace." });
      return;
    }

    set({
      sseMessage: "Loading persisted trace...",
      sseTaskId: normalizedTaskId,
      sseTokens: "",
      sseTraceSteps: [],
      ssePhase: "replay",
      traceCursor: 0,
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
        throw new Error(errorText || `Failed to load trace (${response.status})`);
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
        sseTraceSteps: steps,
        ssePhase: typeof data.status === "string" ? data.status : "replay",
        traceCursor,
        sseMessage:
          steps.length > 0
            ? "Persisted trace loaded."
            : "Persisted trace is empty for this task.",
      });
    } catch (error) {
      set({
        sseMessage:
          error instanceof Error ? error.message : "Failed to load persisted trace.",
      });
    }
  },

  loadTraceDelta: async (apiBaseUrl, taskId) => {
    const normalizedTaskId = taskId.trim();
    if (!normalizedTaskId) {
      set({ sseMessage: "Task ID is required to load trace delta." });
      return;
    }

    const currentCursor = get().traceCursor;
    set({
      sseMessage: `Loading trace delta after seq=${currentCursor}...`,
      sseTaskId: normalizedTaskId,
    });

    try {
      const response = await fetch(
        `${apiBaseUrl}/api/tasks/${normalizedTaskId}/trace/delta?after_seq=${currentCursor}`,
        {
          cache: "no-store",
        },
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          errorText || `Failed to load trace delta (${response.status})`,
        );
      }

      const data = (await response.json()) as {
        task_id: string;
        steps?: TraceStepPayload[];
        next_cursor?: number;
        has_more?: boolean;
      };
      const steps = Array.isArray(data.steps) ? data.steps : [];

      set((state) => ({
        sseTaskId: data.task_id || normalizedTaskId,
        sseTraceSteps: steps.reduce(
          (mergedSteps, step) => upsertTraceStep(mergedSteps, step),
          state.sseTraceSteps,
        ),
        traceCursor:
          typeof data.next_cursor === "number"
            ? data.next_cursor
            : Math.max(currentCursor, getNextTraceCursor(steps)),
        sseMessage:
          steps.length > 0
            ? data.has_more
              ? `Trace delta loaded (${steps.length} steps, more available).`
              : `Trace delta loaded (${steps.length} steps).`
            : "No new trace delta steps.",
      }));
    } catch (error) {
      set({
        sseMessage:
          error instanceof Error ? error.message : "Failed to load trace delta.",
      });
    }
  },

  dispatchSseEvent: (event, payload, onSessionResolved) => {
    if (event === "start" && payload && typeof payload === "object") {
      const p = payload as Record<string, unknown>;
      if (typeof p.task_id === "string") {
        set({ sseTaskId: p.task_id });
      }
      if (typeof p.session_id === "string") {
        onSessionResolved?.(p.session_id);
      }
      set({ sseMessage: "Stream started." });
      return;
    }
    if (event === "state" && payload && typeof payload === "object") {
      const p = payload as Record<string, unknown>;
      if (typeof p.phase === "string") {
        set({ ssePhase: p.phase });
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
          set((state) => ({
            sseTraceSteps: upsertTraceStep(state.sseTraceSteps, {
              id: stepId,
              type: stepType,
              content,
              seq: typeof s.seq === "number" ? s.seq : undefined,
              meta,
            }),
            traceCursor: Math.max(
              state.traceCursor,
              typeof s.seq === "number"
                ? s.seq
                : getNextTraceCursor(
                    upsertTraceStep(state.sseTraceSteps, {
                      id: stepId,
                      type: stepType,
                      content,
                      seq: undefined,
                      meta,
                    }),
                  ),
            ),
          }));
        }
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
      set({ sseMessage: "Stream completed (done)." });
      return;
    }
    if (event === "error" && payload && typeof payload === "object") {
      const p = payload as Record<string, unknown>;
      set({
        ssePhase: "error",
        sseMessage:
          typeof p.message === "string"
            ? `Stream error: ${p.message}`
            : "Stream error received.",
      });
      return;
    }
    if (event === "heartbeat") {
      set((state) => ({
        sseMessage: state.sseMessage.startsWith("Stream started")
          ? state.sseMessage
          : "Receiving stream (heartbeat ok).",
      }));
    }
  },

  runChatStream: async (options) => {
    const prompt = options.prompt.trim();
    if (!prompt) {
      set({ sseMessage: "Prompt cannot be empty." });
      return;
    }

    const { onSessionResolved } = options;
    set({
      isStreaming: true,
      sseMessage: "Opening SSE stream...",
      sseTokens: "",
      sseTraceSteps: [],
      ssePhase: null,
      sseTaskId: null,
      traceCursor: 0,
    });

    try {
      const response = await fetch(`${options.apiBaseUrl}/api/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({
          prompt,
          session_id: options.sessionId,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `Stream failed (${response.status})`);
      }

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
          get().dispatchSseEvent(parsed.event, payload, onSessionResolved);
        }
      }

      set((state) => ({
        sseMessage: state.sseMessage.includes("completed")
          ? state.sseMessage
          : "Stream closed.",
      }));
    } catch (error) {
      set({
        sseMessage:
          error instanceof Error ? error.message : "Failed to read SSE stream.",
      });
    } finally {
      set({ isStreaming: false });
    }
  },
}));
