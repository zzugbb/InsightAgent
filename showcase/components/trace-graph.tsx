"use client";
import { useEffect, useMemo } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  Panel,
  ReactFlow,
  useReactFlow,
  useNodesInitialized,
  type Node,
  type NodeProps,
  type Edge,
} from "@xyflow/react";
import { Maximize2 } from "lucide-react";
import "@xyflow/react/dist/style.css";
import { buildTraceFlowLayout } from "../lib/trace-layout";
import type { TraceStepPayload } from "../lib/types";
import { isError, stepKind, stepTitle } from "../lib/labels";
import { useGraphMeasurements } from "./use-graph-measurements";
type GraphData = {
  title: string;
  kind: string;
  selected: boolean;
  error: boolean;
  select: () => void;
  seq: number;
};
function StepNode({ data }: NodeProps<Node<GraphData>>) {
  return (
    <>
      <Handle type="target" position={Position.Top} />
      <button
        className={`graph-node ${data.selected ? "selected" : ""} ${data.error ? "error" : ""}`}
        onClick={data.select}
        aria-pressed={data.selected}
      >
        <span>
          {String(data.seq).padStart(2, "0")} / {data.kind}
        </span>
        <strong>{data.title}</strong>
        <small>查看节点详情</small>
      </button>
      <Handle type="source" position={Position.Bottom} />
    </>
  );
}
const nodeTypes = { step: StepNode };
function ShowFullGraph() {
  const { fitView } = useReactFlow();
  return (
    <Panel position="top-right">
      <button
        className="graph-fit-button"
        onClick={() => fitView({ padding: 0.15, maxZoom: 1 })}
      >
        <Maximize2 size={15} />
        查看全图
      </button>
    </Panel>
  );
}
function AutoFit({ recentIds }: { recentIds: string }) {
  const { fitView } = useReactFlow();
  const ready = useNodesInitialized();
  useEffect(() => {
    if (!ready) return;
    const frame = requestAnimationFrame(() =>
      fitView({
        nodes: recentIds.split(",").map((id) => ({ id })),
        padding: 0.15,
        minZoom: 0.5,
        maxZoom: 1,
      }),
    );
    return () => cancelAnimationFrame(frame);
  }, [recentIds, fitView, ready]);
  return null;
}
export default function TraceGraph({
  steps,
  selected,
  onSelect,
}: {
  steps: TraceStepPayload[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const { measurements, onNodesChange } = useGraphMeasurements();
  const { nodes, edges } = useMemo(() => {
    const layout = buildTraceFlowLayout(steps);
    const nodes: Node<GraphData>[] = steps.map((step, index) => ({
      id: step.id,
      type: "step",
      position: layout.positions.get(step.id)!,
      measured: measurements[step.id],
      data: {
        title: stepTitle(step),
        kind: stepKind(step),
        selected: selected === step.id,
        error: isError(step),
        select: () => onSelect(step.id),
        seq: index + 1,
      },
    }));
    const edges: Edge[] = layout.links.map((link) => ({
      ...link,
      type: "smoothstep",
      className: `relation-${link.relation}`,
      style: {
        stroke: link.relation === "sequence" ? "#8290a1" : "#22c55e",
        strokeWidth: link.relation === "sequence" ? 1.5 : 2.5,
        strokeDasharray: link.relation === "sequence" ? "5 5" : undefined,
      },
      markerEnd:
        link.relation === "sequence"
          ? undefined
          : { type: MarkerType.ArrowClosed, color: "#22c55e" },
    }));
    return { nodes, edges };
  }, [steps, selected, onSelect, measurements]);
  return (
    <div className="graph-wrap">
      <p className="graph-legend">
        <span className="sequence-line" />
        记录顺序
        <span className="dependency-line" />
        已声明依赖 / 决策关系
      </p>
      <p className="graph-hint">
        默认聚焦最近步骤。拖动画布移动，或点击“查看全图”浏览完整记录。
      </p>
      <div className="graph-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          nodeTypes={nodeTypes}
          colorMode="dark"
          nodesDraggable={false}
          nodesConnectable={false}
          minZoom={0.3}
          maxZoom={1.4}
          proOptions={{ hideAttribution: true }}
        >
          <AutoFit
            recentIds={steps
              .slice(-3)
              .map((step) => step.id)
              .join(",")}
          />
          <Background gap={20} color="#2a3440" />
          <ShowFullGraph />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  );
}
