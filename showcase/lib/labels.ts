import type { TraceStepPayload } from "./types";
export const repository = "https://github.com/zzugbb/InsightAgent";
export function stepTitle(step: TraceStepPayload) {
  const meta = step.meta;
  if (meta?.step_type === "final_answer") return "最终回答";
  if (meta?.tool?.name === "task_retrieve") return "检索工具";
  if (meta?.tool?.name === "task_plan") return "规划工具";
  if (meta?.tool?.name === "calc_eval") return "计算工具";
  if (meta?.tool) return meta.tool.label || meta.tool.name;
  if (meta?.rag) return "检索证据";
  if (meta?.error_event) return "执行错误";
  if (step.type === "thought")
    return meta?.agent_decision ? "后续决策" : "任务规划";
  if (step.type === "observation") return "结果反馈";
  return meta?.label || "执行记录";
}
export function isError(step: TraceStepPayload) {
  return Boolean(step.meta?.error_event || step.meta?.tool?.status === "error");
}
export function stepKind(step: TraceStepPayload) {
  if (isError(step)) return "错误";
  if (step.meta?.step_type === "final_answer") return "回答";
  if (step.meta?.tool) return "工具";
  return step.type === "thought" ? "规划" : "观察";
}
