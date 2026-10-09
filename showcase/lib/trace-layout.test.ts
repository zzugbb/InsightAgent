import test from "node:test";
import assert from "node:assert/strict";
import { buildTraceFlowLayout } from "./trace-layout.ts";
import type { TraceStepPayload } from "./types.ts";
test("recording order never becomes an inferred dependency", () => {
  const result = buildTraceFlowLayout([
    { id: "a", type: "action", content: "" },
    { id: "b", type: "action", content: "" },
  ]);
  assert.deepEqual(
    result.links.map((link) => link.relation),
    ["sequence"],
  );
});
test("declared dependencies stay within their planning round and hidden parents are not substituted", () => {
  const steps: TraceStepPayload[] = [
    {
      id: "old",
      type: "action",
      content: "",
      meta: { plan_node_id: "root", agent_round: 1 },
    },
    {
      id: "root",
      type: "action",
      content: "",
      meta: { plan_node_id: "root", agent_round: 2 },
    },
    {
      id: "child",
      type: "action",
      content: "",
      meta: { plan_node_id: "child", agent_round: 2, depends_on: ["root"] },
    },
  ];
  assert.deepEqual(
    buildTraceFlowLayout(steps)
      .links.filter((x) => x.relation === "dependency")
      .map((x) => [x.source, x.target]),
    [["root", "child"]],
  );
  assert.equal(
    buildTraceFlowLayout(steps.filter((x) => x.id !== "root")).links.filter(
      (x) => x.relation === "dependency",
    ).length,
    0,
  );
});
test("parallel groups share a stage without a sequential connection", () => {
  const result = buildTraceFlowLayout(
    ["a", "b"].map((id) => ({
      id,
      type: "action",
      content: "",
      meta: { parallel_group_id: "group" },
    })),
  );
  assert.equal(result.positions.get("a")?.y, result.positions.get("b")?.y);
  assert.equal(result.links.length, 0);
});
