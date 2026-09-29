export type TraceDeltaSource = {
  isStreaming: boolean;
  isPageVisible: boolean;
  taskId: string;
};

export function resolveTraceDeltaReset(
  previous: TraceDeltaSource,
  current: TraceDeltaSource,
): "idle" | "paused" | "active" | null {
  if (
    previous.isStreaming === current.isStreaming &&
    previous.isPageVisible === current.isPageVisible &&
    previous.taskId === current.taskId
  ) {
    return null;
  }
  if (!current.isStreaming) return "idle";
  if (!current.isPageVisible) return "paused";
  return current.taskId ? "active" : "idle";
}
