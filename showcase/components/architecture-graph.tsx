"use client";

import { useEffect, useMemo, useRef, useSyncExternalStore } from "react";
import {
  Background,
  Handle,
  MarkerType,
  Panel,
  Position,
  ReactFlow,
  useNodesInitialized,
  useReactFlow,
  type BuiltInEdge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import {
  Calculator,
  Database,
  FileSearch,
  GitBranch,
  ListTree,
  MessageSquare,
  Save,
  Terminal,
  Workflow,
  ZoomIn,
  ZoomOut,
  Maximize2,
} from "lucide-react";
import { executionModules } from "../lib/architecture";
import { useGraphMeasurements } from "./use-graph-measurements";
import "@xyflow/react/dist/style.css";

type ModuleData = {
  id: string;
  selected: boolean;
  onSelect: (id: string) => void;
};
const icons = {
  input: MessageSquare,
  planner: ListTree,
  executor: Terminal,
  decision: GitBranch,
  answer: MessageSquare,
  commit: Save,
  retrieve: FileSearch,
  calculate: Calculator,
  vector: Database,
  ledger: Database,
};
const positions = {
  input: { x: 14, y: 150 },
  planner: { x: 204, y: 150 },
  executor: { x: 394, y: 150 },
  decision: { x: 584, y: 150 },
  answer: { x: 774, y: 150 },
  commit: { x: 964, y: 150 },
  retrieve: { x: 280, y: 290 },
  calculate: { x: 504, y: 290 },
  vector: { x: 280, y: 435 },
  ledger: { x: 964, y: 290 },
};
const sides = {
  left: Position.Left,
  right: Position.Right,
  top: Position.Top,
  bottom: Position.Bottom,
};
function ModuleNode({ data }: NodeProps<Node<ModuleData>>) {
  const info = executionModules[data.id];
  const Icon = icons[data.id as keyof typeof icons] ?? Workflow;
  return (
    <>
      {Object.entries(sides).flatMap(([side, position]) => [
        <Handle
          key={`in-${side}`}
          id={`in-${side}`}
          type="target"
          position={position}
        />,
        <Handle
          key={`out-${side}`}
          id={`out-${side}`}
          type="source"
          position={position}
        />,
      ])}
      <button
        className="architecture-graph-node"
        aria-label={`查看${info.title}职责`}
        aria-pressed={data.selected}
        onClick={(event) => {
          event.stopPropagation();
          data.onSelect(data.id);
        }}
      >
        <span>
          <Icon size={15} />
          {info.subtitle.split(" · ")[0]}
        </span>
        <strong>{info.title}</strong>
      </button>
    </>
  );
}
const nodeTypes = { module: ModuleNode };
const connections = [
  ["input", "planner"],
  ["planner", "executor"],
  ["executor", "decision"],
  ["decision", "answer"],
  ["answer", "commit"],
  ["executor", "retrieve", "工具示例"],
  ["executor", "calculate"],
  ["retrieve", "vector", "向量检索"],
  ["commit", "ledger", "事务提交"],
  ["decision", "executor", "继续工具 · 有界循环"],
] as const;
function subscribeNarrow(callback: () => void) {
  const media = matchMedia("(max-width: 760px)");
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}
function ViewControls({
  selected,
  onReady,
}: {
  selected: string;
  onReady: () => void;
}) {
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const ready = useNodesInitialized();
  const fittedMode = useRef<boolean | null>(null);
  const narrow = useSyncExternalStore(
    subscribeNarrow,
    () => matchMedia("(max-width: 760px)").matches,
    () => false,
  );
  useEffect(() => {
    if (!ready) return;
    // Keep the visitor's desktop pan/zoom; only mobile follows the selected node.
    if (!narrow && fittedMode.current === narrow) return;
    const frame = requestAnimationFrame(() => {
      fitView({
        nodes: narrow ? [{ id: selected }] : undefined,
        padding: narrow ? 0.9 : 0.12,
        minZoom: narrow ? 0.85 : 0.3,
        maxZoom: 1,
        duration: 0,
      });
      fittedMode.current = narrow;
      onReady();
    });
    return () => cancelAnimationFrame(frame);
  }, [fitView, ready, narrow, selected, onReady]);
  return (
    <Panel position="bottom-left" className="architecture-zoom">
      <button aria-label="放大架构图" onClick={() => zoomIn()}>
        <ZoomIn size={17} />
      </button>
      <button aria-label="缩小架构图" onClick={() => zoomOut()}>
        <ZoomOut size={17} />
      </button>
      <button onClick={() => fitView({ padding: 0.12, maxZoom: 1 })}>
        <Maximize2 size={15} />
        查看全图
      </button>
    </Panel>
  );
}

export default function ArchitectureGraph({
  selected,
  activeEdges,
  playing,
  onSelect,
  onReady,
}: {
  selected: string;
  activeEdges: string[];
  playing: boolean;
  onSelect: (id: string) => void;
  onReady: () => void;
}) {
  const { measurements, onNodesChange } = useGraphMeasurements();
  const { nodes, edges } = useMemo(
    () => ({
      nodes: Object.entries(positions).map(
        ([id, position]): Node<ModuleData> => ({
          id,
          position,
          type: "module",
          width: 156,
          height: 86,
          measured: measurements[id],
          data: { id, selected: selected === id, onSelect },
        }),
      ),
      edges: connections.map(([source, target, label]): BuiltInEdge => {
        const id = `${source}-${target}`;
        const active =
          activeEdges.includes(id) ||
          (activeEdges.length === 0 &&
            (source === selected || target === selected));
        const loop = id === "decision-executor";
        const branch = ["retrieve", "calculate", "vector", "ledger"].includes(
          target,
        );
        return {
          id,
          source,
          target,
          label,
          sourceHandle: `out-${loop ? "top" : branch ? "bottom" : "right"}`,
          targetHandle: `in-${loop ? "top" : branch ? "top" : "left"}`,
          type: "smoothstep",
          pathOptions: { offset: loop ? 55 : 25 },
          animated: active && playing,
          className: active ? "architecture-edge-active" : "",
          style: {
            stroke: active ? "#22c55e" : "#526071",
            strokeWidth: active ? 2.5 : 1.3,
          },
          labelStyle: { fill: active ? "#9aefb9" : "#95a1b2", fontSize: 11 },
          labelBgStyle: { fill: "#101418", fillOpacity: 1 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: active ? "#22c55e" : "#526071",
          },
        };
      }),
    }),
    [selected, activeEdges, playing, onSelect, measurements],
  );
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      nodeTypes={nodeTypes}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      onNodeClick={(_, node) => onSelect(node.id)}
      nodesFocusable={false}
      edgesFocusable={false}
      colorMode="dark"
      minZoom={0.2}
      maxZoom={1.5}
      zoomOnScroll={false}
      preventScrolling={false}
      proOptions={{ hideAttribution: true }}
      aria-label="任务执行架构示意图"
      ariaLabelConfig={{
        "node.a11yDescription.default": "使用节点按钮查看模块职责。",
      }}
    >
      <Background gap={24} color="#28313c" />
      <Panel position="top-left" className="architecture-canvas-label">
        <span className="status-dot" />
        任务执行 · 架构示意<span>点击节点查看职责，拖动画布移动</span>
      </Panel>
      <ViewControls selected={selected} onReady={onReady} />
    </ReactFlow>
  );
}
