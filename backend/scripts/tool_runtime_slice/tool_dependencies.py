"""Explicit dependency graphs, bounded scalar bindings and task coordination."""

from copy import deepcopy
from dataclasses import replace
from threading import Barrier, get_ident
from types import SimpleNamespace
from unittest.mock import patch
import json

from app.services import tool_runtime as runtime
from app.services import tool_runtime_planning as planning
from app.services.tool_plan_dependencies import (
    ToolDependencyError, bind_node_input, collect_preview, dependency_waves,
    resolved_execution_batches,
)
from tool_runtime_slice.task_parallel import TaskParallelMixin


def calc(node_id, expression="1+2", *, depends_on=(), binding=None):
    node = {"id": node_id, "name": "calc_eval", "input": {"expression": expression},
            "depends_on": list(depends_on)}
    if binding is not None:
        node["input_bindings"] = {"expression": binding}
    return node


def ref(node="root", path=None, **kwargs):
    return {"node": node, "path": ["result"] if path is None else path, **kwargs}


def normalize(nodes, provider=None):
    return planning._normalize_provider_tool_plan(nodes, prompt="fixture", registry_provider=provider)


class ToolDependenciesMixin:
    run_dependency_plan = TaskParallelMixin.run_parallel_plan

    def test_tool_dependency_legacy_deduplicates_but_explicit_graph_keeps_same_tool_nodes(self):
        legacy = [{"name": "calc_eval", "input": {"expression": value}} for value in ("1+2", "3*2")]
        self.assertEqual([node["name"] for node in normalize(legacy)], ["task_plan", "calc_eval"])
        plan = normalize([calc("root"), calc("scaled", binding=ref(template="{value} * 2"))])
        self.assertEqual([node.get("id") for node in plan], [None, "root", "scaled"])
        self.assertEqual(plan[-1]["depends_on"], ["root"])

    def test_tool_dependency_forward_references_follow_stable_topological_order(self):
        nodes = [calc("last", depends_on=["left", "right"]), calc("left", depends_on=["root"]),
                 calc("root"), calc("right", binding=ref())]
        waves = dependency_waves(nodes)
        self.assertEqual([[node["id"] for _, node in wave] for wave in waves],
                         [["root"], ["left", "right"], ["last"]])
        self.assertEqual([index for wave in waves for index, _ in wave], [3, 2, 4, 1])
        self.assertEqual(nodes[-1]["depends_on"], [])

    def test_tool_dependency_missing_first_id_cannot_be_mistaken_for_planner(self):
        plan = [calc("root"), calc("child", depends_on=["root"])]
        del plan[0]["id"]
        with self.assertRaises(ToolDependencyError):
            list(resolved_execution_batches(plan, outputs={}, max_concurrent=2,
                                            registry_provider=runtime.get_default_tool_registry_provider()))

    def test_tool_dependency_rejects_cycles_self_unknown_and_duplicate_references(self):
        plans = [[calc("a", depends_on=["b"]), calc("b", depends_on=["a"])],
                 [calc("a", depends_on=["a"])], [calc("a", depends_on=["unknown"])],
                 [calc("a"), calc("a")], [calc("a"), calc("b", depends_on=["a", "a"])],
                 [calc("a", binding=ref("a"))]]
        for plan in plans:
            with self.subTest(plan=plan), self.assertRaises(ToolDependencyError):
                normalize(plan)

    def test_tool_dependency_rejects_invalid_ids_and_dependency_types(self):
        for value in (None, "", "1bad", "has space", "x" * 65, 2, True):
            with self.subTest(value=value), self.assertRaises(ToolDependencyError):
                normalize([calc(value)])
        for value in (None, "root", {}, [True]):
            plan = [calc("root"), calc("child")]
            plan[1]["depends_on"] = value
            with self.subTest(value=value), self.assertRaises(ToolDependencyError):
                normalize(plan)

    def test_tool_dependency_node_and_edge_limits(self):
        self.assertEqual(len(normalize([calc(f"n{i}") for i in range(32)])), 33)
        with self.assertRaises(ToolDependencyError):
            normalize([calc(f"n{i}") for i in range(33)])
        with self.assertRaises(ToolDependencyError):
            normalize([calc(f"n{i}", depends_on=[f"n{j}" for j in range(i)]) for i in range(17)])

    def test_tool_dependency_invalid_or_disabled_tool_never_becomes_partial_plan(self):
        registry = runtime.get_default_tool_registry()
        registry.pop("calc_eval")
        for provider in (runtime.StaticToolRegistryProvider(registry),):
            with self.assertRaises(ToolDependencyError):
                normalize([calc("root")], provider)
        plan = [calc("root"), {"id": "bad", "name": "unknown", "depends_on": []}]
        with self.assertRaises(ToolDependencyError):
            normalize(plan)

    def test_tool_dependency_binding_cannot_change_knowledge_base_or_identity(self):
        for target in ("knowledge_base_id", "user_id", "headers", "api_key"):
            node = {"id": "search", "name": "task_retrieve", "depends_on": [],
                    "input": {"query": "fixture", "knowledge_base_id": "literal"},
                    "input_bindings": {target: ref()}}
            with self.subTest(target=target), self.assertRaises(ToolDependencyError):
                normalize([calc("root"), node])

    def test_tool_dependency_binding_rejects_malformed_paths_templates_and_extra_fields(self):
        bindings = [ref(path=[]), ref(path=[True]), ref(path=[-1]), ref(path=[1001]),
                    ref(path=["x" * 81]), ref(path=["x"] * 9), ref(path="result"),
                    ref(template="missing placeholder"), ref(template=5),
                    ref(template="{value}" * 9), ref(template="{value}" + "x" * 8192),
                    ref(extra="not allowed"), ref("unknown")]
        for binding in bindings:
            with self.subTest(binding=binding), self.assertRaises(ToolDependencyError):
                normalize([calc("root"), calc("child", binding=binding)])

    def test_tool_dependency_scalar_binding_uses_literal_replace_and_copies_input(self):
        node = calc("child", binding=ref(template="{value} + {value} {value.__class__}"))
        resolved = bind_node_input(node, {"root": {"result": 3}})
        self.assertEqual(resolved["input"]["expression"], "3 + 3 {value.__class__}")
        self.assertEqual(node["input"]["expression"], "1+2")

    def test_tool_dependency_nested_preview_path_and_literal_query_scope(self):
        node = {"id": "search", "name": "task_retrieve", "depends_on": [],
                "input": {"query": "fixture", "knowledge_base_id": "literal"},
                "input_bindings": {"query": ref(path=["hits", 0, "content"])}}
        plan = normalize([calc("root"), node])
        resolved = bind_node_input(plan[-1], {"root": {"hits": [{"content": "scoped query"}]}})
        self.assertEqual(resolved["input"]["query"], "scoped query")
        self.assertEqual(resolved["input"]["knowledge_base_id"], "literal")

    def test_tool_dependency_preview_collection_never_reads_raw_output_or_failed_trace(self):
        action = {"kind": "trace_write", "trace_step": {"meta": {"tool": {
            "status": "done", "output": {"secret": "raw fixture"}, "output_preview": {"result": 3}}}}}
        preview = collect_preview([action])
        self.assertEqual(preview, {"result": 3})
        preview["result"] = 7
        self.assertEqual(collect_preview([action]), {"result": 3})
        action["trace_step"]["meta"]["tool"]["status"] = "error"
        self.assertEqual(collect_preview([action]), {})

    def test_tool_dependency_binding_missing_raw_or_wrong_container_path_is_fixed_error(self):
        for outputs, path in (({}, ["result"]), ({"root": {"result": 3}}, ["secret"]),
                              ({"root": {"result": []}}, ["result", 0]),
                              ({"root": {"result": 3}}, ["result", "attribute"])):
            with self.subTest(path=path), self.assertRaises(ToolDependencyError) as error:
                bind_node_input(calc("child", binding=ref(path=path)), outputs)
            self.assertEqual(error.exception.code, "tool_dependency_input_unavailable")
            self.assertNotIn("secret", str(error.exception))

    def test_tool_dependency_binding_rejects_non_scalar_empty_nonfinite_and_large_values(self):
        for value in (None, {}, [], float("nan"), float("inf"), " ", "x" * 8193):
            with self.subTest(value=type(value)), self.assertRaises(ToolDependencyError):
                bind_node_input(calc("child", binding=ref()), {"root": {"result": value}})
        with self.assertRaises(ToolDependencyError):
            bind_node_input(calc("child", binding=ref(template="{value}" * 8)),
                            {"root": {"result": "x" * 8192}})

    def test_tool_dependency_scalar_zero_and_false_are_available(self):
        for value in (0, False):
            resolved = bind_node_input(calc("child", binding=ref()), {"root": {"result": value}})
            self.assertEqual(resolved["input"]["expression"], str(value))

    def test_tool_dependency_coordinator_chain_result_input_and_trace_sequence(self):
        plan = normalize([calc("root"), calc("child", binding=ref(template="{value} * 2"))])
        calls = []
        def runner(**kwargs):
            calls.append(deepcopy(kwargs))
            return runtime.run_tool(**kwargs)
        for cap in (1, 2):
            calls.clear()
            events, trace, observations, owners, completed, failures = self.run_dependency_plan(runner, plan=plan, cap=cap)
            actions = [step for step in trace if step["type"] == "action"]
            self.assertEqual([step["meta"].get("plan_node_id") for step in actions], [None, "root", "child"])
            self.assertEqual(actions[-1]["meta"]["depends_on"], ["root"])
            self.assertEqual(actions[-1]["meta"]["tool"]["output_preview"]["result"], 6)
            self.assertEqual(calls[-1]["tool_input"]["expression"], "3.0 * 2")
            self.assertEqual([step["seq"] for step in trace], sorted({step["seq"] for step in trace}))
            self.assertEqual(set(owners), {get_ident()})
            self.assertFalse(events[-1]["result"]["should_return"])
            self.assertFalse(completed or failures)

    def test_tool_dependency_ready_fanout_runs_concurrently_after_root(self):
        barrier, root_done, threads = Barrier(2), [], []
        def runner(**kwargs):
            expression = kwargs["tool_input"].get("expression")
            if expression and expression != "1+2":
                self.assertTrue(root_done)
                threads.append(get_ident())
                barrier.wait(timeout=3)
            result = runtime.run_tool(**kwargs)
            if expression == "1+2":
                root_done.append(True)
            return result
        plan = normalize([calc("root"), calc("left", binding=ref(template="{value} * 2")),
                          calc("right", binding=ref(template="{value} * 3"))])
        _, trace, *_ = self.run_dependency_plan(runner, plan=plan)
        self.assertEqual(len(set(threads)), 2)
        parallel = [step for step in trace if step["meta"].get("execution_mode") == "parallel"]
        self.assertEqual([step["meta"]["plan_node_id"] for step in parallel], ["left", "right"])
        self.assertEqual(len({step["meta"]["parallel_group_id"] for step in parallel}), 1)

    def test_tool_dependency_custom_runner_keeps_serial_barrier_with_satisfied_dependencies(self):
        registry = runtime.get_default_tool_registry()
        registry["calc_eval"] = replace(registry["calc_eval"], runner=lambda **_: {})
        provider = runtime.StaticToolRegistryProvider(registry)
        plan = [calc("left", depends_on=["root"]), calc("root"), calc("right", depends_on=["root"])]
        batches = list(resolved_execution_batches(plan, outputs={}, max_concurrent=4, registry_provider=provider))
        self.assertEqual([[node["id"] for _, node in batch] for batch, _ in batches], [["root"], ["left"], ["right"]])

    def test_tool_dependency_upstream_fatal_stops_dependent_and_keeps_failure_trace(self):
        calls = []
        def runner(**kwargs):
            calls.append(kwargs["tool_input"].get("expression"))
            if kwargs["name"] == "calc_eval":
                raise runtime.MockToolExecutionError("fatal fixture", fatal=True)
            return runtime.run_tool(**kwargs)
        events, trace, _, _, completed, _ = self.run_dependency_plan(
            runner, plan=normalize([calc("root"), calc("child", depends_on=["root"])]))
        self.assertEqual(calls, [None, "1+2"])
        self.assertTrue(events[-1]["result"]["should_return"])
        self.assertTrue(completed)
        self.assertFalse(any(step["meta"].get("plan_node_id") == "child" for step in trace))

    def test_tool_dependency_invalid_graph_fails_before_any_runner(self):
        calls = []
        with self.assertRaises(ToolDependencyError):
            self.run_dependency_plan(lambda **kwargs: calls.append(kwargs),
                                     plan=[calc("a", depends_on=["b"]), calc("b", depends_on=["a"])])
        self.assertEqual(calls, [])

    def test_tool_dependency_unavailable_preview_stops_before_bound_tool(self):
        calls = []
        def runner(**kwargs):
            calls.append(kwargs["name"])
            return runtime.run_tool(**kwargs)
        with self.assertRaises(ToolDependencyError):
            self.run_dependency_plan(runner, plan=normalize([calc("root"), calc("child", binding=ref(path=["secret"]))]))
        self.assertEqual(calls, ["task_plan", "calc_eval"])

    def test_tool_dependency_retry_exhaustion_stops_order_only_dependent(self):
        calls = []
        def runner(**kwargs):
            calls.append((kwargs["tool_input"].get("expression"), kwargs["attempt"]))
            if kwargs["name"] == "calc_eval":
                raise runtime.MockToolExecutionError("retry fixture", fatal=False)
            return runtime.run_tool(**kwargs)
        events, trace, _, _, completed, _ = self.run_dependency_plan(
            runner, plan=normalize([calc("root"), calc("child", "8+9", depends_on=["root"])]))
        self.assertTrue(events[-1]["result"]["should_return"])
        self.assertTrue(completed)
        self.assertFalse(any(expression == "8+9" for expression, _ in calls))
        self.assertFalse(any(step["meta"].get("plan_node_id") == "child" for step in trace))

    def test_tool_dependency_bound_expression_still_uses_calculator_ast_validation(self):
        executed = []
        def runner(**kwargs):
            executed.append(kwargs["tool_input"].get("expression"))
            return runtime.run_tool(**kwargs)
        plan = normalize([calc("root"), calc("child", binding=ref(template="__import__('os').system('{value}')"))])
        with patch("os.system") as system:
            events, _, _, _, completed, _ = self.run_dependency_plan(runner, plan=plan)
        system.assert_not_called()
        self.assertTrue(events[-1]["result"]["should_return"])
        self.assertTrue(completed)
        self.assertIn("__import__('os').system('3.0')", executed)

    def test_tool_dependency_provider_invalid_graph_is_not_silently_rule_fallback(self):
        provider = SimpleNamespace(provider="offline-fixture", generate=lambda _: SimpleNamespace(
            content=json.dumps({"tools": [calc("root", depends_on=["secret-fixture"])]})))
        with self.assertRaises(ToolDependencyError) as error:
            runtime.build_tool_plan_artifacts("rag [calc:1+2]", provider=provider)
        self.assertEqual(error.exception.code, "tool_dependency_plan_invalid")
        self.assertNotIn("secret-fixture", str(error.exception))

    def test_tool_dependency_sdk_attribute_payload_preserves_graph_fields(self):
        raw = SimpleNamespace(tools=[SimpleNamespace(**calc("root")),
                                     SimpleNamespace(**calc("child", binding=ref()))])
        items = planning._extract_provider_tool_plan_items(raw)
        plan = normalize(items)
        self.assertEqual(plan[-1]["depends_on"], ["root"])
        self.assertEqual(plan[-1]["input_bindings"]["expression"]["path"], ["result"])
