"""Validate explicit tool DAGs and bind only already projected result preview scalars."""

from copy import deepcopy
import math
import re

from app.providers.base import ProviderCallError

MAX_NODES = 32
MAX_EDGES = 128
MAX_BINDINGS = 8
MAX_BOUND_TEXT = 16_384
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


class ToolDependencyError(ProviderCallError):
    def __init__(self, *, input_unavailable=False):
        super().__init__(
            code="tool_dependency_input_unavailable" if input_unavailable else "tool_dependency_plan_invalid",
            user_message=("A required tool result is unavailable or cannot be used as input."
                          if input_unavailable else "The tool dependency plan is invalid. Please retry the request."),
            retryable=False,
        )


def has_dependencies(items):
    return any(isinstance(item, dict) and ("depends_on" in item or "input_bindings" in item) for item in items)


def _valid_id(value):
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _validate_nodes(nodes):
    if not 1 <= len(nodes) <= MAX_NODES:
        raise ToolDependencyError()
    ids = [node.get("id") for node in nodes]
    if not all(_valid_id(node_id) for node_id in ids) or len(set(ids)) != len(ids):
        raise ToolDependencyError()
    all_ids, edges = set(ids), 0
    for node in nodes:
        dependencies = node.get("depends_on", [])
        if (not isinstance(dependencies, list) or len(dependencies) > MAX_NODES
                or not all(_valid_id(dep) for dep in dependencies) or len(set(dependencies)) != len(dependencies)):
            raise ToolDependencyError()
        if node["id"] in dependencies or not set(dependencies) <= all_ids:
            raise ToolDependencyError()
        bindings = node.get("input_bindings", {})
        if not isinstance(bindings, dict) or len(bindings) > MAX_BINDINGS:
            raise ToolDependencyError()
        for target, binding in bindings.items():
            if target not in {"query", "expression"} or target not in node.get("input", {}):
                raise ToolDependencyError()
            if not isinstance(binding, dict) or not set(binding) <= {"node", "path", "template"}:
                raise ToolDependencyError()
            source, path = binding.get("node"), binding.get("path")
            if not _valid_id(source) or source not in all_ids or source == node["id"]:
                raise ToolDependencyError()
            if not isinstance(path, list) or not 1 <= len(path) <= 8:
                raise ToolDependencyError()
            for part in path:
                if not ((isinstance(part, str) and 1 <= len(part) <= 80)
                        or (type(part) is int and 0 <= part <= 1000)):
                    raise ToolDependencyError()
            template = binding.get("template")
            if template is not None and (not isinstance(template, str) or len(template) > 8192
                                         or not 1 <= template.count("{value}") <= 8):
                raise ToolDependencyError()
            if source not in dependencies:
                dependencies = [*dependencies, source]
        node["depends_on"] = dependencies
        edges += len(dependencies)
    if edges > MAX_EDGES:
        raise ToolDependencyError()


def dependency_waves(tool_plan, *, planner_prefix=False):
    """Validate the full graph before yielding any tool; stable topological waves."""
    if not has_dependencies(tool_plan):
        return [list(enumerate(tool_plan, 1))]
    nodes, prefix = deepcopy(tool_plan), []
    if planner_prefix and nodes and "id" not in nodes[0]:
        prefix = [(1, nodes.pop(0))]
    _validate_nodes(nodes)
    indexed = list(enumerate(nodes, 1 + len(prefix)))
    done, waves = set(), ([prefix] if prefix else [])
    while indexed:
        ready = [(index, node) for index, node in indexed if set(node["depends_on"]) <= done]
        if not ready:
            raise ToolDependencyError()
        waves.append(ready)
        done.update(node["id"] for _, node in ready)
        indexed = [(index, node) for index, node in indexed if node["id"] not in done]
    return waves


def normalize_dependency_plan(raw_items, *, normalize_node, planner_prefix):
    if not 1 <= len(raw_items) <= MAX_NODES:
        raise ToolDependencyError()
    nodes = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ToolDependencyError()
        clean = {key: deepcopy(value) for key, value in raw.items()
                 if key not in {"id", "depends_on", "input_bindings"}}
        bindings = raw.get("input_bindings", {})
        if not isinstance(bindings, dict):
            raise ToolDependencyError()
        if "expression" in bindings:
            # Static input validation still runs; the real value is validated again by the tool after binding.
            clean["input"] = {**(clean.get("input") if isinstance(clean.get("input"), dict) else {}), "expression": "0"}
        normalized = normalize_node(clean)
        if normalized is None:
            raise ToolDependencyError()
        nodes.append({**normalized, "id": raw.get("id"), "depends_on": deepcopy(raw.get("depends_on", [])),
                      "input_bindings": deepcopy(bindings)})
    # This both validates references and materializes inferred edges from bindings.
    _validate_nodes(nodes)
    plan = [*planner_prefix, *nodes]
    dependency_waves(plan, planner_prefix=bool(planner_prefix))
    return plan


def bind_node_input(node, outputs):
    resolved = deepcopy(node)
    for target, binding in node.get("input_bindings", {}).items():
        try:
            value = outputs[binding["node"]]
            for part in binding["path"]:
                if isinstance(value, dict) and isinstance(part, str):
                    value = value[part]
                elif isinstance(value, list) and type(part) is int:
                    value = value[part]
                else:
                    raise KeyError()
        except (KeyError, IndexError, TypeError):
            raise ToolDependencyError(input_unavailable=True) from None
        if type(value) not in {str, int, float, bool} or (isinstance(value, float) and not math.isfinite(value)):
            raise ToolDependencyError(input_unavailable=True)
        try:
            text = str(value)
        except (ValueError, OverflowError):
            raise ToolDependencyError(input_unavailable=True) from None
        if len(text) > 8192:
            raise ToolDependencyError(input_unavailable=True)
        template = binding.get("template")
        text = template.replace("{value}", text) if template is not None else text
        if not text.strip() or len(text) > MAX_BOUND_TEXT:
            raise ToolDependencyError(input_unavailable=True)
        resolved["input"][target] = text
    return resolved


def collect_preview(actions):
    for action in actions:
        step = action.get("trace_step", {}) if action.get("kind") == "trace_write" else {}
        tool = (step.get("meta") or {}).get("tool") or {}
        if tool.get("status") == "done" and isinstance(tool.get("output_preview"), dict):
            return deepcopy(tool["output_preview"])
    return {}


def resolved_execution_batches(tool_plan, *, outputs, max_concurrent, registry_provider):
    from app.services.task_tool_parallel import execution_batches
    from app.services.tool_runtime import get_tool_semantic_kind
    advanced = has_dependencies(tool_plan)
    prefix = (advanced and tool_plan and "id" not in tool_plan[0]
              and get_tool_semantic_kind(name=str(tool_plan[0].get("name", "")),
                                         registry_provider=registry_provider) == "task_planner")
    for wave in dependency_waves(tool_plan, planner_prefix=bool(prefix)):
        resolved = [(index, bind_node_input(node, outputs)) for index, node in wave]
        # Only graph dependencies proven satisfied in this wave can be removed for read classification.
        classified = [{key: value for key, value in node.items()
                       if not advanced or key not in {"depends_on", "input_bindings"}} for _, node in resolved]
        for batch, provider in execution_batches(classified, max_concurrent=max_concurrent,
                                                  registry_provider=registry_provider):
            yield [resolved[index - 1] for index, _ in batch], provider
