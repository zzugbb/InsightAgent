import type { TraceStepPayload } from "../../../lib/types/trace.ts";

export type TraceFlowLink = {
  id: string;
  source: string;
  target: string;
  relation: "sequence" | "dependency" | "decision";
};

/** Sequence is recording order, never an inferred tool dependency. */
export function buildTraceFlowLayout(steps: TraceStepPayload[]) {
  const stages: TraceStepPayload[][] = [];
  const groups = new Map<string, number>();
  const positions = new Map<string, { x: number; y: number }>();
  const planNodes = new Map<string, string>();
  const links: TraceFlowLink[] = [];
  const visibleIds = new Set(steps.map((step) => step.id));
  const key = (step: TraceStepPayload, id: string) =>
    JSON.stringify([step.meta?.agent_round ?? 1, id]);

  for (const step of steps) {
    const group = step.meta?.parallel_group_id;
    const stageIndex = group ? groups.get(group) : undefined;
    if (stageIndex !== undefined) {
      stages[stageIndex].push(step);
    } else {
      if (group) groups.set(group, stages.length);
      stages.push([step]);
    }
    const nodeId = step.meta?.plan_node_id;
    if (nodeId) planNodes.set(key(step, nodeId), step.id);
  }

  stages.forEach((stage, row) => {
    stage.forEach((step, column) => {
      positions.set(step.id, { x: 20 + column * 320, y: row * 180 });
      for (const dependency of step.meta?.depends_on ?? []) {
        const source = planNodes.get(key(step, dependency));
        // Filters may hide a dependency. Do not replace it with a visible neighbour.
        if (source && source !== step.id) {
          links.push({ id: `dependency:${source}:${step.id}`, source, target: step.id, relation: "dependency" });
        }
      }
      for (const source of step.meta?.agent_from_step_ids ?? []) {
        if (visibleIds.has(source) && source !== step.id) {
          links.push({ id: `decision:${source}:${step.id}`, source, target: step.id, relation: "decision" });
        }
      }
    });
  });
  for (let index = 1; index < steps.length; index++) {
    const previous = steps[index - 1], current = steps[index];
    if (previous.meta?.parallel_group_id && previous.meta.parallel_group_id === current.meta?.parallel_group_id) continue;
    links.push({ id: `sequence:${previous.id}:${current.id}`, source: previous.id,
      target: current.id, relation: "sequence" });
  }
  // A dependency already conveys the connection; avoid overlapping duplicate edges.
  const dependencies = new Set(links.filter((link) => link.relation !== "sequence")
    .map((link) => `${link.source}:${link.target}`));
  return { positions, rowCount: stages.length,
    links: links.filter((link) => link.relation !== "sequence" || !dependencies.has(`${link.source}:${link.target}`)) };
}
