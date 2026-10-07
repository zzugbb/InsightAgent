import test from "node:test";
import assert from "node:assert/strict";
import { buildTraceFlowLayout } from "./trace-flow-layout.ts";
import type { TraceStepMeta, TraceStepPayload } from "../../../lib/types/trace.ts";

const step = (id: string, meta?: TraceStepMeta): TraceStepPayload => ({ id, type: "action", content: id, meta });

test("legacy trace keeps recording order without inventing dependencies", () => {
  const result = buildTraceFlowLayout([step("a"), step("b"), step("c")]);
  assert.deepEqual(result.links.map((edge) => [edge.source, edge.target, edge.relation]),
    [["a", "b", "sequence"], ["b", "c", "sequence"]]);
});

test("decision links use visible source step IDs", () => {
  const result = buildTraceFlowLayout([step("action"), step("decision", { agent_from_step_ids: ["action", "hidden"] })]);
  assert.deepEqual(result.links.map((edge) => [edge.source, edge.target, edge.relation]), [["action", "decision", "decision"]]);
});

test("dependency fork uses plan IDs rather than adjacent tools", () => {
  const result = buildTraceFlowLayout([
    step("a", { plan_node_id: "root", depends_on: [] }),
    step("b", { plan_node_id: "left", depends_on: ["root"] }),
    step("c", { plan_node_id: "right", depends_on: ["root"] }),
  ]);
  assert.deepEqual(result.links.filter((edge) => edge.relation === "dependency").map((edge) => [edge.source, edge.target]),
    [["a", "b"], ["a", "c"]]);
  assert.equal(result.links.filter((edge) => edge.source === "a" && edge.target === "b").length, 1);
});

test("parallel siblings share a row and have no edge between them", () => {
  const result = buildTraceFlowLayout([step("plan"), step("a", { parallel_group_id: "g" }),
    step("b", { parallel_group_id: "g" }), step("final")]);
  assert.equal(result.positions.get("a")?.y, result.positions.get("b")?.y);
  assert.notEqual(result.positions.get("a")?.x, result.positions.get("b")?.x);
  assert.equal(result.links.some((edge) => edge.source === "a" && edge.target === "b"), false);
});

test("interleaved RAG records retain actual order when parallel nodes share a row", () => {
  const result = buildTraceFlowLayout([step("a", { parallel_group_id: "g" }), step("rag"),
    step("b", { parallel_group_id: "g" })]);
  assert.deepEqual(result.links.map((edge) => [edge.source, edge.target]), [["a", "rag"], ["rag", "b"]]);
});

test("filtered dependencies stay absent, and repeated plan IDs are scoped by round", () => {
  const result = buildTraceFlowLayout([step("old", { plan_node_id: "root", agent_round: 1 }),
    step("new", { plan_node_id: "root", agent_round: 2 }),
    step("child", { plan_node_id: "child", depends_on: ["root", "hidden"], agent_round: 2 })]);
  assert.deepEqual(result.links.filter((edge) => edge.relation === "dependency").map((edge) => [edge.source, edge.target]),
    [["new", "child"]]);
});
