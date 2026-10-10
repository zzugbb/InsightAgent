"use client";

import { useCallback, useState } from "react";
import type { NodeChange } from "@xyflow/react";

// Controlled graphs must retain renderer measurements across data/selection updates.
// Otherwise a fresh node object loses its dimensions and fitView cannot fit it.
export function useGraphMeasurements() {
  const [measurements, setMeasurements] = useState<
    Record<string, { width: number; height: number }>
  >({});
  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setMeasurements((current) => {
      let next = current;
      for (const change of changes) {
        if (change.type !== "dimensions" || !change.dimensions) continue;
        const previous = current[change.id];
        if (
          previous?.width === change.dimensions.width &&
          previous?.height === change.dimensions.height
        )
          continue;
        if (next === current) next = { ...current };
        next[change.id] = change.dimensions;
      }
      return next;
    });
  }, []);
  return { measurements, onNodesChange };
}
