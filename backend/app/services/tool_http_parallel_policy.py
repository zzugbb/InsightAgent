"""Opt-in HTTP read capability tied to factory-created runner identity, not tool metadata."""

from threading import Lock
from weakref import WeakSet

_read_runners = WeakSet()
_lock = Lock()


def http_parallel_policy_errors(spec):
    if "parallel_read_only" not in spec:
        return ()
    if type(spec["parallel_read_only"]) is not bool:
        return ("http_json execution parallel_read_only must be a boolean",)
    if spec["parallel_read_only"] and not _is_literal_read(spec):
        return ("http_json execution parallel_read_only requires literal GET without json_body",)
    return ()


def _is_literal_read(spec):
    method = spec.get("method", "GET")
    return isinstance(method, str) and method.strip().upper() == "GET" and spec.get("json_body") is None


def register_http_read_runner(runner, spec):
    if spec.get("parallel_read_only") is True and _is_literal_read(spec):
        with _lock:
            _read_runners.add(runner)


def is_http_read_runner(runner):
    with _lock:
        try:
            return runner in _read_runners
        except TypeError:
            return False
