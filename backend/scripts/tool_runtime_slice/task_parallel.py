"""Concurrent read coordination, barriers, retry isolation and lifecycle guards."""

from copy import deepcopy
from dataclasses import replace
from functools import partial
from threading import Barrier, Event, Lock, get_ident
from unittest.mock import Mock, patch

from pydantic import ValidationError

from app.config import Settings
from app.services import task_tool_parallel as parallel
from app.services import tool_runtime as runtime
from app.services.task_tool_execution import execute_task_tool_plan


def spec(name, **tool_input):
    return {"name": name, "input": tool_input}


READS = [spec("task_retrieve", query="fixture", knowledge_base_id="default"), spec("calc_eval", expression="1+2")]


def prepare(index, item, seq, provider):
    return runtime.build_tool_iteration_context(
        step_id=f"step-{index}", seq=seq, name=item["name"], tool_input=item["input"],
        model="mock", label=f"tool_{index}", token_count=1, registry_provider=provider,
    )


def output(name):
    if name == "task_retrieve":
        return {"chunks": ["fixture context"], "hits": [{"content": "fixture context", "metadata": {}}],
                "knowledge_base_id": "default", "hit_count": 1}
    return {"expression": "1+2", "result": 3}


class TaskParallelMixin:
    def run_parallel_plan(self, runner, *, plan=None, cap=2, abort=lambda: None, heartbeat=lambda: None):
        trace, observations, callback_threads, completed, failures = [], [], [], [], []
        def persist(**kwargs):
            callback_threads.append(get_ident())
        def complete(**kwargs):
            callback_threads.append(get_ident())
            completed.append(deepcopy(kwargs))
        def failure(**kwargs):
            callback_threads.append(get_ident())
            failures.append(kwargs)
        with patch.object(parallel, "execute_tool_plan_item_retry_loop",
                          partial(runtime.execute_tool_plan_item_retry_loop, run_tool_fn=runner)):
            events = list(execute_task_tool_plan(
                tool_plan=deepcopy(plan or READS), max_concurrent=cap,
                registry_provider=runtime.get_default_tool_registry_provider(), seq_cursor=7,
                task_id="task", trace_steps=trace, tool_observations=observations, prompt="fixture", user_id="owner",
                model="mock", prepare_iteration=prepare, estimate_token_count=lambda _: 1,
                raise_if_should_abort=abort, touch_heartbeat=heartbeat,
                execute_item=partial(runtime.execute_tool_plan_item_service_execution, run_tool_fn=runner),
                apply_actions=runtime.execute_tool_plan_item_service_actions, persist_trace_fn=persist,
                complete_task_fn=complete, record_failure_event_fn=failure,
            ))
        return events, trace, observations, callback_threads, completed, failures

    def test_task_parallel_config_defaults_off_and_rejects_out_of_range(self):
        self.assertEqual(Settings(_env_file=None).task_tool_max_concurrent, 1)
        for cap in (0, 5):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None, TASK_TOOL_MAX_CONCURRENT=cap)

    def test_task_parallel_default_does_not_reload_registry(self):
        provider = Mock()
        batches = parallel.execution_batches(READS, max_concurrent=1, registry_provider=provider)
        self.assertEqual([len(batch) for batch, _ in batches], [1, 1])
        provider.load_tool_registry.assert_not_called()

    def test_task_parallel_planner_unknown_and_custom_runner_are_barriers(self):
        registry = runtime.get_default_tool_registry()
        registry["calc_eval"] = replace(registry["calc_eval"], runner=lambda **_: {})
        provider = runtime.StaticToolRegistryProvider(registry)
        plan = [READS[0], spec("task_plan"), READS[0], READS[1], spec("unknown")]
        batches = parallel.execution_batches(plan, max_concurrent=4, registry_provider=provider)
        self.assertEqual([len(batch) for batch, _ in batches], [1, 1, 1, 1, 1])

    def test_task_parallel_dependency_hints_are_barriers(self):
        for key in ("depends_on", "dependsOn", "dependencies", "after"):
            for level in ("input", "top"):
                plan = deepcopy(READS)
                (plan[1]["input"] if level == "input" else plan[1])[key] = ["earlier"]
                batches = parallel.execution_batches(plan, max_concurrent=2,
                                                     registry_provider=runtime.get_default_tool_registry_provider())
                self.assertEqual([len(batch) for batch, _ in batches], [1, 1])

    def test_task_parallel_windows_bound_size_and_freeze_registry(self):
        provider = runtime.StaticToolRegistryProvider(runtime.get_default_tool_registry())
        batches = parallel.execution_batches(READS * 3, max_concurrent=4, registry_provider=provider)
        self.assertEqual([len(batch) for batch, _ in batches], [4, 2])
        provider.registry.clear()
        self.assertIn("calc_eval", batches[0][1].load_tool_registry())

    def test_task_parallel_tools_overlap_but_trace_and_effects_follow_plan_order(self):
        barrier, calculator_done, threads = Barrier(2), Event(), []
        def runner(*, name, **kwargs):
            threads.append(get_ident())
            barrier.wait(timeout=2)
            if name == "task_retrieve":
                self.assertTrue(calculator_done.wait(2))
            else:
                calculator_done.set()
            return output(name)
        events, trace, observations, callback_threads, completed, failures = self.run_parallel_plan(runner)
        self.assertEqual(len(set(threads)), 2)
        self.assertNotIn(get_ident(), threads)
        self.assertEqual(set(callback_threads), {get_ident()})
        self.assertEqual([step["seq"] for step in trace], [8, 9, 10])
        self.assertEqual([step["id"] for step in trace if step["type"] == "action"], ["step-1", "step-2"])
        self.assertTrue(all(step["meta"]["execution_mode"] == "parallel" for step in trace if step["type"] == "action"))
        ids = {step["meta"]["parallel_group_id"] for step in trace if step["type"] == "action"}
        self.assertEqual(len(ids), 1)
        self.assertEqual(len(observations), 2)
        self.assertTrue(observations[0].startswith("Knowledge Retrieval"))
        self.assertTrue(observations[1].startswith("Calculator"))
        self.assertEqual(events[-1]["result"], {"seq_cursor": 10, "should_return": False})
        self.assertFalse(completed or failures)

    def test_task_parallel_serial_switch_keeps_calls_on_owner_thread(self):
        threads = []
        def runner(*, name, **kwargs):
            threads.append(get_ident())
            return output(name)
        _, trace, _, _, _, _ = self.run_parallel_plan(runner, cap=1)
        self.assertEqual(threads, [get_ident(), get_ident()])
        self.assertFalse(any("execution_mode" in step.get("meta", {}) for step in trace))
        self.assertEqual([step["seq"] for step in trace], [8, 9, 10])

    def test_task_parallel_retry_does_not_repeat_successful_sibling(self):
        attempts, lock = [], Lock()
        def runner(*, name, attempt, **kwargs):
            with lock:
                attempts.append((name, attempt))
            if name == "task_retrieve" and attempt == 0:
                raise runtime.MockToolExecutionError("retry fixture", fatal=False)
            return output(name)
        _, trace, observations, _, completed, failures = self.run_parallel_plan(runner)
        self.assertEqual(attempts.count(("calc_eval", 0)), 1)
        self.assertIn(("task_retrieve", 1), attempts)
        self.assertEqual(trace[0]["meta"]["retryCount"], 1)
        self.assertEqual(len(observations), 2)
        self.assertFalse(completed or failures)

    def test_task_parallel_fatal_failure_persists_trace_and_stops_final_synthesis(self):
        sibling_started, release_sibling, sibling_finished = Event(), Event(), Event()
        def runner(*, name, **kwargs):
            if name == "calc_eval":
                sibling_started.set()
                release_sibling.wait(2)
                sibling_finished.set()
                return output(name)
            self.assertTrue(sibling_started.wait(2))
            raise runtime.MockToolExecutionError("fatal fixture", fatal=True)
        try:
            events, trace, observations, threads, completed, failures = self.run_parallel_plan(runner)
            self.assertTrue(events[-1]["result"]["should_return"])
            self.assertEqual(len(trace), 1)
            self.assertEqual(trace[0]["seq"], 8)
            self.assertEqual(completed[0]["trace_steps"], trace)
            self.assertEqual(completed[0]["status"], "failed")
            self.assertEqual(len(failures), 1)
            self.assertEqual(set(threads), {get_ident()})
            self.assertEqual(observations, [])
        finally:
            release_sibling.set()
            self.assertTrue(sibling_finished.wait(2))

    def test_task_parallel_cancellation_discards_late_events_and_effects(self):
        started, release, done, cancelled = Event(), Event(), Event(), Event()
        count, lock = [0], Lock()
        def runner(*, name, **kwargs):
            with lock:
                count[0] += 1
                if count[0] == 2:
                    started.set()
            release.wait(2)
            if name == "calc_eval":
                done.set()
            return output(name)
        def abort():
            if started.is_set():
                cancelled.set()
                raise RuntimeError("cancelled fixture")
        try:
            with self.assertRaisesRegex(RuntimeError, "cancelled fixture"):
                self.run_parallel_plan(runner, abort=abort)
            self.assertTrue(cancelled.is_set())
        finally:
            release.set()
            self.assertTrue(done.wait(2))

    def test_task_parallel_generator_close_stops_late_worker_publication(self):
        started, release, finished = Event(), Event(), Event()
        def worker(*, raise_if_should_abort, **kwargs):
            started.set()
            yield {"kind": "event", "event": "tool_start", "data": {}}
            release.wait(2)
            try:
                raise_if_should_abort()
                yield {"kind": "result", "result": {"should_return": False}}
            finally:
                finished.set()
        stream = parallel.execute_parallel_batch([(1, {})], raise_if_should_abort=lambda: None,
                                                  touch_heartbeat=lambda: None, worker_fn=worker)
        self.assertEqual(next(stream)["kind"], "event")
        stream.close()
        release.set()
        self.assertTrue(finished.wait(2))

    def test_task_parallel_unexpected_worker_exception_reaches_owner(self):
        def worker(**kwargs):
            raise ValueError("worker fixture")
            yield
        with self.assertRaisesRegex(ValueError, "worker fixture"):
            list(parallel.execute_parallel_batch([(1, {})], raise_if_should_abort=lambda: None,
                                                touch_heartbeat=lambda: None, worker_fn=worker))

    def test_task_parallel_wait_polls_lifecycle_and_execution_heartbeat(self):
        release, count, touches = Event(), [0], []
        def worker(**kwargs):
            release.wait(2)
            yield {"kind": "result", "result": {"should_return": False}}
        def abort():
            count[0] += 1
            if count[0] == 4:
                release.set()
        events = list(parallel.execute_parallel_batch([(1, {})], raise_if_should_abort=abort,
                                                      touch_heartbeat=lambda: touches.append(get_ident()), worker_fn=worker))
        self.assertGreaterEqual(count[0], 4)
        self.assertGreaterEqual(len(touches), 2)
        self.assertEqual(set(touches), {get_ident()})
        self.assertEqual(events[-1]["kind"], "result")

    def test_task_parallel_shared_pool_bounds_workers_across_pending_reads(self):
        from concurrent.futures import ThreadPoolExecutor
        release, at_capacity, lock = Event(), Event(), Lock()
        active, peak = [0], [0]
        def worker(**kwargs):
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
                if active[0] == parallel.PROCESS_TOOL_WORKERS:
                    at_capacity.set()
            try:
                release.wait(3)
                yield {"kind": "result", "result": {"should_return": False}}
            finally:
                with lock:
                    active[0] -= 1
        jobs = [(index, {}) for index in range(parallel.PROCESS_TOOL_WORKERS + 1)]
        with ThreadPoolExecutor(max_workers=1) as owner:
            future = owner.submit(lambda: list(parallel.execute_parallel_batch(
                jobs, raise_if_should_abort=lambda: None, touch_heartbeat=lambda: None, worker_fn=worker)))
            try:
                self.assertTrue(at_capacity.wait(2))
                self.assertEqual(peak[0], parallel.PROCESS_TOOL_WORKERS)
            finally:
                release.set()
            self.assertEqual(len(future.result(timeout=3)), len(jobs))
        self.assertEqual(peak[0], parallel.PROCESS_TOOL_WORKERS)

    def test_task_parallel_idle_wait_emits_existing_heartbeat(self):
        release, finished = Event(), Event()
        def worker(**kwargs):
            try:
                release.wait(2)
                yield {"kind": "result", "result": {"should_return": False}}
            finally:
                finished.set()
        ticks = iter([0, 3, 3])
        with patch.object(parallel, "monotonic", side_effect=lambda: next(ticks, 3)):
            stream = parallel.execute_parallel_batch([(1, {})], raise_if_should_abort=lambda: None,
                                                      touch_heartbeat=lambda: None, worker_fn=worker)
            try:
                self.assertEqual(next(stream), {"kind": "heartbeat"})
                release.set()
                self.assertEqual(next(stream)["kind"], "result")
            finally:
                stream.close()
                release.set()
                self.assertTrue(finished.wait(2))
