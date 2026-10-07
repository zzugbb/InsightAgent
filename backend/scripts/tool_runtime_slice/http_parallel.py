"""Explicit HTTP read opt-in, immutable config, safe classification and owner coordination."""

from copy import deepcopy
from dataclasses import replace
import gc
import json
from threading import Barrier, Lock, get_ident
from unittest.mock import patch
from urllib.error import HTTPError
from weakref import ref

from app.config import Settings
from app.services import task_tool_parallel as parallel
from app.services import tool_runtime as runtime
from app.services.tool_http_parallel_policy import is_http_read_runner
from tool_runtime_slice.task_parallel import TaskParallelMixin


def execution(**overrides):
    return {"kind": "http_json", "url": "http://fixture.test/read", "method": "GET",
            "parallel_read_only": True, "result_fields": {"result": "result"}, **overrides}


def provider(*, opted=True, methods=("GET", "GET")):
    extra = {name: {"template": "calc_eval", "execution": execution(
        url=f"http://fixture.test/{name}", method=method, parallel_read_only=opted),
        "result_preview_keys": ["result"], "result_output_keys": ["result"]}
        for name, method in zip(("read_a", "read_b"), methods)}
    settings = Settings(_env_file=None).model_copy(update={"tool_registry_extra_tools_json": json.dumps(extra)})
    return runtime.get_configured_tool_registry_provider(settings=settings)


PLAN = [{"name": name, "input": {"expression": "1+2"}} for name in ("read_a", "read_b")]


class Response:
    headers = {"Content-Type": "application/json"}
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self):
        return b'{"result": 3, "api_key": "response-fixture-secret"}'


class HttpParallelMixin:
    def run_http_parallel(self, registry, opener, *, cap=2, plan=None):
        with patch.object(runtime, "get_default_tool_registry_provider", return_value=registry), \
             patch.object(runtime, "urlopen", side_effect=opener):
            return TaskParallelMixin.run_parallel_plan(self, runtime.run_tool, plan=plan or PLAN, cap=cap)

    def test_http_parallel_flag_defaults_to_serial_and_must_be_boolean(self):
        for value in (None, "true", 1, {}, []):
            with self.subTest(value=value):
                errors = runtime._describe_tool_execution_spec_validation_errors(execution(parallel_read_only=value))
                self.assertTrue(any("parallel_read_only must be a boolean" in error for error in errors))
        spec = execution()
        del spec["parallel_read_only"]
        runner = runtime._build_tool_runner_from_execution_spec(
            execution_spec=spec, fallback_runner=lambda **_: {}, default_timeout_ms=1000)
        self.assertFalse(is_http_read_runner(runner))

    def test_http_parallel_requires_literal_get_and_no_body(self):
        for override in ({"method": "POST"}, {"method": "HEAD"}, {"method": "DELETE"},
                         {"method": "$method"}, {"method": {"value": "GET"}},
                         {"json_body": {}}, {"json_body": {"query": "fixture"}}):
            with self.subTest(override=override):
                errors = runtime._describe_tool_execution_spec_validation_errors(execution(**override),
                                                                                template_context={"method": "GET"})
                self.assertTrue(any("requires literal GET" in error for error in errors))

    def test_http_parallel_false_keeps_existing_dynamic_method_validation(self):
        errors = runtime._describe_tool_execution_spec_validation_errors(
            execution(method="$method", parallel_read_only=False), template_context={"method": "POST"})
        self.assertFalse(errors)

    def test_http_parallel_default_get_can_opt_in_and_summary_only_exposes_flag(self):
        spec = execution()
        del spec["method"]
        runner = runtime._build_tool_runner_from_execution_spec(
            execution_spec=spec, fallback_runner=lambda **_: {}, default_timeout_ms=1000)
        self.assertTrue(is_http_read_runner(runner))
        summary = runtime._build_tool_execution_summary_from_spec(spec)
        self.assertIs(summary["parallel_read_only"], True)

    def test_http_parallel_only_opted_factory_runners_are_eligible(self):
        for opted, expected in ((True, [2]), (False, [1, 1])):
            batches = parallel.execution_batches(PLAN, max_concurrent=2, registry_provider=provider(opted=opted))
            self.assertEqual([len(batch) for batch, _ in batches], expected)

    def test_http_parallel_metadata_or_callable_attribute_cannot_grant_capability(self):
        registry = provider().load_tool_registry()
        def forged(**kwargs):
            return {}
        forged.parallel_read_only = True
        for name in ("read_a", "read_b"):
            registry[name] = replace(registry[name], runner=forged, execution_summary={"parallel_read_only": True, "method": "GET"})
        batches = parallel.execution_batches(PLAN, max_concurrent=2,
                                             registry_provider=runtime.StaticToolRegistryProvider(registry))
        self.assertEqual([len(batch) for batch, _ in batches], [1, 1])

    def test_http_parallel_unhashable_custom_callable_stays_serial(self):
        class Callable:
            __hash__ = None
            def __call__(self, **kwargs):
                return {}
        registry = provider().load_tool_registry()
        registry["read_a"] = replace(registry["read_a"], runner=Callable())
        batches = parallel.execution_batches(PLAN, max_concurrent=2,
                                             registry_provider=runtime.StaticToolRegistryProvider(registry))
        self.assertEqual([len(batch) for batch, _ in batches], [1, 1])

    def test_http_parallel_config_and_runtime_context_are_frozen_before_execution(self):
        spec = execution(headers={"Authorization": "$settings_api_key"}, query_params={"q": "$expression"})
        context = {"settings_api_key": "original-fixture-secret"}
        runner = runtime._build_tool_runner_from_execution_spec(execution_spec=spec, fallback_runner=lambda **_: {},
                                                               default_timeout_ms=1000, template_context=context)
        spec.update(method="POST", url="http://changed.test/write", parallel_read_only=False)
        spec["headers"]["Authorization"] = "changed"
        context["settings_api_key"] = "changed"
        requests = []
        def opener(request, timeout):
            requests.append(request)
            return Response()
        with patch.object(runtime, "urlopen", side_effect=opener):
            # The runtime facade synchronizes the HTTP execution namespace before invoking configured runners.
            registration = replace(runtime.get_default_tool_registry()["calc_eval"], runner=runner, execution_kind="http_json")
            runtime.run_tool(name="calc_eval", tool_input={"expression": "1+2"}, prompt="fixture", user_id="owner", attempt=0,
                             registry_provider=runtime.StaticToolRegistryProvider({"calc_eval": registration}))
        self.assertEqual(requests[0].get_method(), "GET")
        self.assertEqual(requests[0].full_url, "http://fixture.test/read?q=1%2B2")
        self.assertEqual(requests[0].get_header("Authorization"), "original-fixture-secret")
        self.assertTrue(is_http_read_runner(runner))

    def test_http_parallel_capability_does_not_retain_discarded_runner_configs(self):
        runner = runtime._build_tool_runner_from_execution_spec(
            execution_spec=execution(), fallback_runner=lambda **_: {}, default_timeout_ms=1000)
        weak = ref(runner)
        del runner
        gc.collect()
        self.assertIsNone(weak())

    def test_http_parallel_overlap_owner_trace_order_and_secret_projection(self):
        barrier, requests, threads = Barrier(2), [], []
        def opener(request, timeout):
            requests.append(request.full_url)
            threads.append(get_ident())
            barrier.wait(timeout=3)
            return Response()
        events, trace, observations, owners, completed, failures = self.run_http_parallel(provider(), opener)
        self.assertEqual(len(set(threads)), 2)
        self.assertEqual([step["meta"]["tool"]["name"] for step in trace], ["read_a", "read_b"])
        self.assertEqual([step["seq"] for step in trace], [8, 9])
        self.assertTrue(all(step["meta"]["execution_mode"] == "parallel" for step in trace))
        self.assertEqual(set(owners), {get_ident()})
        self.assertNotIn("response-fixture-secret", str((events, trace, observations)))
        self.assertFalse(completed or failures)

    def test_http_parallel_serial_switch_keeps_owner_thread(self):
        threads = []
        def opener(request, timeout):
            threads.append(get_ident())
            return Response()
        _, trace, *_ = self.run_http_parallel(provider(), opener, cap=1)
        self.assertEqual(threads, [get_ident(), get_ident()])
        self.assertFalse(any("execution_mode" in step["meta"] for step in trace))

    def test_http_parallel_http_failure_retries_only_failed_read(self):
        counts, lock = {}, Lock()
        def opener(request, timeout):
            with lock:
                count = counts[request.full_url] = counts.get(request.full_url, 0) + 1
            if request.full_url.endswith("read_a") and count == 1:
                raise HTTPError(request.full_url, 503, "fixture", {}, None)
            return Response()
        events, _, _, _, completed, _ = self.run_http_parallel(provider(), opener)
        self.assertEqual(counts, {"http://fixture.test/read_a": 2, "http://fixture.test/read_b": 1})
        self.assertFalse(events[-1]["result"]["should_return"])
        self.assertFalse(completed)

    def test_http_parallel_invalid_opt_in_fails_before_network(self):
        calls = []
        events, *_ = self.run_http_parallel(provider(methods=("POST", "GET")), lambda *args, **kw: calls.append(args))
        self.assertTrue(events[-1]["result"]["should_return"])
        self.assertEqual(calls, [])

    def test_http_parallel_dag_binding_releases_only_ready_http_reads(self):
        barrier = Barrier(2)
        def opener(request, timeout):
            self.assertIn("q=3.0", request.full_url)
            barrier.wait(timeout=3)
            return Response()
        registry = provider().load_tool_registry()
        for name in ("read_a", "read_b"):
            registry[name] = replace(registry[name], runner=runtime._build_tool_runner_from_execution_spec(
                execution_spec=execution(url=f"http://fixture.test/{name}", query_params={"q": "$expression"}),
                fallback_runner=registry[name].runner, default_timeout_ms=1000))
        plan = [{"id": "root", "name": "calc_eval", "input": {"expression": "1+2"}, "depends_on": []},
                *[{**deepcopy(node), "id": node["name"], "depends_on": ["root"],
                   "input_bindings": {"expression": {"node": "root", "path": ["result"]}}} for node in PLAN]]
        _, trace, *_ = self.run_http_parallel(runtime.StaticToolRegistryProvider(registry), opener, plan=plan)
        self.assertEqual([step["meta"]["plan_node_id"] for step in trace], ["root", "read_a", "read_b"])
        self.assertTrue(all(step["meta"].get("execution_mode") == "parallel" for step in trace[1:]))

    def test_http_parallel_serial_write_is_barrier_between_read_windows(self):
        registry = provider().load_tool_registry()
        registry["write"] = replace(registry["read_a"], name="write", runner=lambda **kw: {})
        plan = [*PLAN, {"name": "write", "input": {}}, *PLAN]
        batches = parallel.execution_batches(plan, max_concurrent=4, registry_provider=runtime.StaticToolRegistryProvider(registry))
        self.assertEqual([len(batch) for batch, _ in batches], [2, 1, 2])
