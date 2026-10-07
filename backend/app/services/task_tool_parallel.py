"""Bounded read-only tool batches. Workers never persist task or Trace state."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from queue import Empty, Queue
from threading import Event, Lock
from time import monotonic

from app.services.tool_http_parallel_policy import is_http_read_runner
from app.services.tool_runtime import (
    StaticToolRegistryProvider, _run_calc_eval, _run_task_retrieve,
    execute_tool_plan_item_retry_loop, resolve_tool_registration,
)

_pool = None
_pool_lock = Lock()
# Across all tasks in one process, including reads finishing after task cancellation.
PROCESS_TOOL_WORKERS = 8
_SAFE_RUNNERS = {"calc_eval": _run_calc_eval, "task_retrieve": _run_task_retrieve}
_DEPENDENCY_KEYS = ("depends_on", "dependsOn", "dependencies", "after")


def execution_batches(tool_plan, *, max_concurrent, registry_provider):
    """Freeze a registry snapshot for each parallel window; other tools are barriers."""
    if max_concurrent <= 1:
        return [([(index, spec)], registry_provider) for index, spec in enumerate(tool_plan, 1)]
    snapshot = StaticToolRegistryProvider(registry_provider.load_tool_registry())
    batches, pending = [], []
    for index, spec in enumerate(tool_plan, 1):
        name, tool_input = str(spec["name"]), spec.get("input", {})
        registration = resolve_tool_registration(name, registry_provider=snapshot)
        dependencies = any(spec.get(key) or (isinstance(tool_input, dict) and tool_input.get(key))
                           for key in _DEPENDENCY_KEYS)
        safe = (registration is not None
                and ((registration.name in _SAFE_RUNNERS
                      and registration.runner is _SAFE_RUNNERS[registration.name])
                     or is_http_read_runner(registration.runner))
                and not dependencies)
        if not safe:
            if pending:
                batches.append((pending, snapshot))
                pending = []
            batches.append(([(index, spec)], registry_provider))
            continue
        pending.append((index, spec))
        if len(pending) == max_concurrent:
            batches.append((pending, snapshot))
            pending = []
    if pending:
        batches.append((pending, snapshot))
    return batches


def _executor():
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = ThreadPoolExecutor(max_workers=PROCESS_TOOL_WORKERS, thread_name_prefix="task-tool-read")
        return _pool


def execute_parallel_batch(jobs, *, raise_if_should_abort, touch_heartbeat, worker_fn=None):
    """Stream worker events, then deliver completed results in plan order on the owner thread."""
    worker_fn = worker_fn or execute_tool_plan_item_retry_loop
    stopped, mailbox = Event(), Queue()
    futures, results, errors = [], {}, []

    def worker(index, kwargs):
        def abort():
            if stopped.is_set():
                raise InterruptedError("tool batch stopped")
        try:
            abort()
            for item in worker_fn(**deepcopy(kwargs), raise_if_should_abort=abort):
                if stopped.is_set():
                    return
                mailbox.put((index, item))
        except BaseException as exc:
            if not stopped.is_set():
                mailbox.put((index, {"kind": "exception", "error": exc}))
        finally:
            mailbox.put((index, {"kind": "finished"}))

    try:
        raise_if_should_abort()
        for index, kwargs in jobs:
            futures.append(_executor().submit(worker, index, kwargs))
        finished, last_heartbeat = 0, monotonic()
        while finished < len(jobs):
            raise_if_should_abort()
            touch_heartbeat()
            try:
                index, item = mailbox.get(timeout=0.05)
            except Empty:
                if monotonic() - last_heartbeat >= 2:
                    yield {"kind": "heartbeat"}
                    last_heartbeat = monotonic()
                continue
            if item["kind"] == "event":
                yield item
            elif item["kind"] == "result":
                results[index] = item["result"]
                if item["result"].get("should_return"):
                    break
            elif item["kind"] == "exception":
                errors.append(item["error"])
                break
            elif item["kind"] == "finished":
                finished += 1
        stopped.set()
        for index in sorted(results):
            raise_if_should_abort()
            yield {"kind": "result", "index": index, "result": results[index]}
        if errors:
            raise errors[0]
    finally:
        stopped.set()
        for future in futures:
            future.cancel()
