"use client";

import {
  Background,
  Controls,
  ReactFlow,
  useReactFlow,
  type ColorMode,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useLayoutEffect, useMemo } from "react";

import type { TraceStepPayload } from "../../../lib/types/trace";

import { getStepTitle } from "./utils";

const Y_STEP = 76;

type TraceFlowViewProps = {
  steps: TraceStepPayload[];
  colorMode: ColorMode;
};

function AutoFit({ stepCount }: { stepCount: number }) {
  const { fitView } = useReactFlow();

  useLayoutEffect(() => {
    const id = requestAnimationFrame(() => {
      fitView({ padding: 0.18, maxZoom: 1.25, minZoom: 0.35 });
    });
    return () => cancelAnimationFrame(id);
  }, [fitView, stepCount]);

  return null;
}

function TraceFlowInner({ steps, colorMode }: TraceFlowViewProps) {
  const { nodes, edges } = useMemo(() => {
    const n: Node[] = steps.map((step, i) => ({
      id: step.id,
      position: { x: 32, y: i * Y_STEP },
      data: { label: getStepTitle(step) },
    }));
    const e: Edge[] = [];
    for (let i = 1; i < steps.length; i++) {
      e.push({
        id: `${steps[i - 1].id}->${steps[i].id}`,
        source: steps[i - 1].id,
        target: steps[i].id,
      });
    }
    return { nodes: n, edges: e };
  }, [steps]);

  const height = Math.min(420, Math.max(200, 56 + steps.length * Y_STEP));

  return (
    <div className="trace-flow-inner" style={{ height }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        colorMode={colorMode}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        panOnScroll
        zoomOnScroll
        minZoom={0.35}
        maxZoom={1.4}
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
