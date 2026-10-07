"use client";

import {
  Background,
  Controls,
  Handle,
  MarkerType,
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
  resolveTraceStepDisplayContent,
} from "./utils";
import { buildTraceFlowLayout } from "./trace-flow-layout";

const TRACE_NODE_TYPE = "traceStep" as const;

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
  metadata: string;
  metadataLabel: string;
  parallelLabel: string | null;
};

function TraceStepNode({ data }: NodeProps<Node<TraceFlowNodeData>>) {
  const raw = data.content.trim();
  const hasContent = raw.length > 0;

  return (
    <div
      className={`trace-flow-node nowheel trace-flow-node--${data.kind}`}
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
      {data.parallelLabel ? <div className="trace-flow-node__meta">{data.parallelLabel}</div> : null}
      <details className="trace-flow-node__details nodrag nowheel nopan">
        <summary>{data.contentDetailsLabel}</summary>
        <p className="trace-flow-node__body">
          {hasContent ? raw : data.contentEmpty}
        </p>
      </details>
      <details className="trace-flow-node__details nodrag nowheel nopan">
        <summary>{data.metadataLabel}</summary>
        <pre className="trace-flow-node__body">{data.metadata}</pre>
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

  const { nodes, edges, rowCount } = useMemo(() => {
    const layout = buildTraceFlowLayout(steps);
    const n: Node<TraceFlowNodeData>[] = steps.map((step) => {
      const kind = normalizeTraceStepKind(step);
      return {
        id: step.id,
        type: TRACE_NODE_TYPE,
        position: layout.positions.get(step.id)!,
        data: {
          title: getStepTitle(step),
          kind,
          kindLabel: getTraceFlowKindLabel(kind, t.inspector.traceFlow),
          metaLine: formatTraceStepMetaSubtitle(step, t.inspector.traceMeta),
          content: resolveTraceStepDisplayContent(step) ?? "",
          contentDetailsLabel: t.inspector.traceFlow.contentDetails,
          contentEmpty: t.inspector.traceFlow.contentEmpty,
          metadata: JSON.stringify(step.meta ?? {}, null, 2),
          metadataLabel: t.inspector.traceFlow.metadata,
          parallelLabel: step.meta?.parallel_group_id ? t.inspector.traceFlow.parallel : null,
        },
      };
    });
    const e: Edge[] = layout.links.map((link) => ({
      ...link, type: "smoothstep",
      style: link.relation === "sequence"
        ? { stroke: "var(--muted)", strokeWidth: 1.5, strokeDasharray: "5 5", opacity: 0.65 }
        : { stroke: "var(--accent)", strokeWidth: 3 },
      markerEnd: link.relation === "sequence" ? undefined : { type: MarkerType.ArrowClosed, color: "var(--accent)" },
      className: `trace-flow-edge--${link.relation}`,
    }));
    return { nodes: n, edges: e, rowCount: layout.rowCount };
  }, [steps, t.inspector.traceFlow, t.inspector.traceMeta]);

  const height = Math.min(480, Math.max(220, 72 + rowCount * 180));

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
  const t = useMessages();
  return (
    <div className="trace-flow-root">
      <div className="trace-flow-legend">{t.inspector.traceFlow.legend}</div>
      <TraceFlowInner {...props} />
    </div>
  );
}
