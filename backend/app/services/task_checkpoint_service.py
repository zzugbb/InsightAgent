"""Experimental linear built-in checkpoints, carried by the owner's existing Trace."""

from copy import deepcopy
import json
from uuid import uuid4

from app.providers.base import ProviderCallError
from app.services.tool_runtime import (
    _run_task_plan, _run_task_retrieve, _run_calc_eval,
    _sanitize_tool_runtime_trace_artifact_payload, resolve_tool_registration,
)

_RUNNERS = {"task_plan": _run_task_plan, "task_retrieve": _run_task_retrieve, "calc_eval": _run_calc_eval}
_INPUT_KEYS = {
    "task_plan": {"prompt_preview", "planned_tool_names", "planned_tool_labels", "planned_tool_kinds", "planned_tool_execution_kinds"},
    "task_retrieve": {"query", "top_k", "knowledge_base_id"},
    "calc_eval": {"expression"},
}
MAX_SNAPSHOT_BYTES = 2_000_000


def checkpoint_plan(tool_plan, registry_provider):
    """Capability checks use runner identity, never a tool's advertised read-only label."""
    if not isinstance(tool_plan, list) or not 1 <= len(tool_plan) <= 32:
        return None
    for node in tool_plan:
        if not isinstance(node, dict) or any(key in node for key in ("depends_on", "input_bindings")):
            return None
        name = node.get("name")
        registration = resolve_tool_registration(name, registry_provider=registry_provider)
        if (name not in _RUNNERS or registration is None or registration.runner is not _RUNNERS[name]
                or not isinstance(node.get("input"), dict)
                or not set(node["input"]) <= _INPUT_KEYS[name]):
            return None
    safe = _sanitize_tool_runtime_trace_artifact_payload(deepcopy(tool_plan))
    # Redacted values cannot be used to reproduce the original plan.
    if safe != tool_plan or len(json.dumps(safe).encode()) > MAX_SNAPSHOT_BYTES:
        return None
    return safe


def annotate_checkpoint_actions(actions, index):
    observations = [text for action in actions if action.get("kind") == "continue"
                    for text in action.get("tool_observations", [])]
    for action in actions:
        if action.get("kind") != "trace_write":
            continue
        step = action["trace_step"]
        meta = step.setdefault("meta", {})
        meta["checkpoint_index"] = index
        if (meta.get("tool") or {}).get("status") == "done":
            meta["checkpoint_observations"] = observations
        action["trace_event"]["step"] = deepcopy(step)


def load_trace(raw):
    if not isinstance(raw, str):
        return []
    try:
        steps = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return steps if isinstance(steps, list) and all(isinstance(step, dict) for step in steps) else []


def _manifest(steps):
    for step in steps:
        plan = (step.get("meta") or {}).get("checkpoint_plan")
        if isinstance(plan, list) and 1 <= len(plan) <= 32:
            return plan
    return None


def checkpoint_candidates(steps):
    plan = _manifest(steps)
    if plan is None:
        return []
    actions = {step.get("meta", {}).get("checkpoint_index"): step for step in steps
               if step.get("type") == "action" and isinstance(step.get("meta"), dict)}
    result = []
    for index, node in enumerate(plan, 1):
        step = actions.get(index)
        if step is None:
            break
        tool = step["meta"].get("tool") or {}
        result.append({"step_id": step["id"], "index": index, "tool_name": node["name"],
                       "reused_steps": index - 1})
        if tool.get("status") != "done" or not isinstance(step["meta"].get("checkpoint_observations"), list):
            break
    return result


def build_checkpoint_seed(steps, step_id):
    candidate = next((item for item in checkpoint_candidates(steps) if item["step_id"] == step_id), None)
    if candidate is None:
        return None
    start = candidate["index"]
    prefix = [deepcopy(step) for step in steps if type((step.get("meta") or {}).get("checkpoint_index")) is int
              and step["meta"]["checkpoint_index"] < start]
    seed = {"plan": deepcopy(_manifest(steps)), "start_index": start, "steps": prefix,
            "source_step_id": step_id}
    if len(json.dumps(seed).encode()) > MAX_SNAPSHOT_BYTES:
        return None
    return seed


def seed_trace(seed):
    return [{"id": str(uuid4()), "seq": 1, "type": "thought", "content": "Experimental checkpoint branch queued.",
             "meta": {"step_type": "checkpoint_seed", "checkpoint_seed": seed}}]


def extract_checkpoint_seed(raw):
    steps = load_trace(raw)
    if len(steps) == 1 and (steps[0].get("meta") or {}).get("step_type") == "checkpoint_seed":
        seed = steps[0]["meta"].get("checkpoint_seed")
        if isinstance(seed, dict):
            return deepcopy(seed)
    return None


def validate_resume(seed, registry_provider):
    plan = checkpoint_plan(seed.get("plan"), registry_provider)
    start = seed.get("start_index")
    if plan is None or type(start) is not int or not 1 <= start <= len(plan):
        raise ProviderCallError(code="checkpoint_unavailable", user_message="The checkpoint is incompatible with current tools. Create a full task rerun.", retryable=False)
    return plan


def restored_prefix(seed, first_seq):
    steps, observations = deepcopy(seed["steps"]), []
    for seq, step in enumerate(steps, first_seq):
        source_id = step["id"]
        step.update(id=str(uuid4()), seq=seq)
        meta = step.setdefault("meta", {})
        observations.extend(meta.get("checkpoint_observations", []))
        # Historic results are not calls made by this task and must not incur usage again.
        for field in ("tokens", "prompt_tokens", "completion_tokens", "latency", "retryCount"):
            if field in meta:
                meta[field] = 0
        meta.update(cost_estimate=0.0, checkpoint_reused=True, checkpoint_source_step_id=source_id)
        step["content"] = "[Reused checkpoint result] " + step["content"]
    return steps, observations
