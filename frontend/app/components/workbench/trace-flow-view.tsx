"use client";

import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  useReactFlow,
  type ColorMode,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useLayoutEffect, useMemo } from "react";

import { useMessages } from "../../../lib/preferences-context";
import type { TraceStepPayload } from "../../../lib/types/trace";

import {
  formatTraceStepMetaSubtitle,
  getStepTitle,
  getTraceFlowKindLabel,
  normalizeTraceStepKind,
} from "./utils";

const TRACE_NODE_TYPE = "traceStep" as const;
const Y_STEP = 108;

type TraceFlowNodeData = {
  title: string;
  kind:
    | "thought"
    | "action"
    | "observation"
    | "tool"
    | "rag"
    | "other";
  kindLabel: string;
  metaLine: string | null;
  content: string;
  contentDetailsLabel: string;
  contentEmpty: string;
};

function TraceStepNode({ data }: NodeProps<Node<TraceFlowNodeData>>) {
  const raw = data.content.trim();
  const preview =
    raw.length > 280 ? `${raw.slice(0, 280)}…` : raw;
  const hasContent = preview.length > 0;

  return (
    <div
      className={`trace-flow-node trace-flow-node--${data.kind}`}
      data-kind={data.kind}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="trace-flow-handle"
      />
      <div className="trace-flow-node__row">
        <span className="trace-flow-node__badge">{data.kindLabel}</span>
        <span className="trace-flow-node__title" title={data.title}>
          {data.title}
        </span>
      </div>
      {data.metaLine ? (
        <div className="trace-flow-node__meta">{data.metaLine}</div>
      ) : null}
      <details className="trace-flow-node__details">
        <summary>{data.contentDetailsLabel}</summary>
        <p className="trace-flow-node__body">
          {hasContent ? preview : data.contentEmpty}
        </p>
      </details>
      <Handle
        type="source"
        position={Position.Bottom}
        className="trace-flow-handle"
      />
    </div>
  );
}

const nodeTypes = { [TRACE_NODE_TYPE]: TraceStepNode };

type TraceFlowViewProps = {
  steps: TraceStepPayload[];
  colorMode: ColorMode;
};

function AutoFit({ stepCount }: { stepCount: number }) {
  const { fitView } = useReactFlow();

  useLayoutEffect(() => {
    const id = requestAnimationFrame(() => {
      fitView({ padding: 0.16, maxZoom: 1.15, minZoom: 0.32 });
    });
    return () => cancelAnimationFrame(id);
  }, [fitView, stepCount]);

  return null;
}

function TraceFlowInner({ steps, colorMode }: TraceFlowViewProps) {
  const t = useMessages();

  const { nodes, edges } = useMemo(() => {
    const n: Node<TraceFlowNodeData>[] = steps.map((step, i) => {
      const kind = normalizeTraceStepKind(step);
      return {
        id: step.id,
        type: TRACE_NODE_TYPE,
        position: { x: 20, y: i * Y_STEP },
        data: {
          title: getStepTitle(step),
          kind,
          kindLabel: getTraceFlowKindLabel(kind, t.inspector.traceFlow),
          metaLine: formatTraceStepMetaSubtitle(step, t.inspector.traceMeta),
          content: typeof step.content === "string" ? step.content : "",
          contentDetailsLabel: t.inspector.traceFlow.contentDetails,
          contentEmpty: t.inspector.traceFlow.contentEmpty,
        },
      };
    });
    const e: Edge[] = [];
    for (let i = 1; i < steps.length; i++) {
      e.push({
        id: `${steps[i - 1].id}->${steps[i].id}`,
        source: steps[i - 1].id,
        target: steps[i].id,
        type: "smoothstep",
      });
    }
    return { nodes: n, edges: e };
  }, [steps, t.inspector.traceFlow, t.inspector.traceMeta]);

  const height = Math.min(480, Math.max(220, 72 + steps.length * Y_STEP));

  return (
    <div className="trace-flow-inner" style={{ height }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        colorMode={colorMode}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        panOnScroll
        zoomOnScroll
        minZoom={0.32}
        maxZoom={1.35}
        proOptions={{ hideAttribution: true }}
        className="trace-flow-canvas"
      >
        <AutoFit stepCount={steps.length} />
        <Background gap={14} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export function TraceFlowView(props: TraceFlowViewProps) {
  return (
    <div className="trace-flow-root">
      <TraceFlowInner {...props} />
    </div>
  );
}
