"""Task tool coordinator: serial side effects and stable Trace ordering for concurrent reads."""

from copy import deepcopy
from uuid import uuid4

from app.services.task_tool_parallel import execute_parallel_batch
from app.services.task_checkpoint_service import annotate_checkpoint_actions
from app.services.tool_plan_dependencies import collect_preview, resolved_execution_batches
from app.services.tool_runtime import build_tool_plan_item_service_execution


def _rebase_trace_actions(actions, *, first_seq, trace_steps):
    actions = deepcopy(actions)
    next_seq = first_seq
    for action in actions:
        if action["kind"] == "trace_write":
            action["trace_step"]["seq"] = next_seq
            action["trace_event"]["step"]["seq"] = next_seq
            next_seq += 1
        elif action["kind"] == "complete_task":
            action["kwargs"]["trace_steps"] = trace_steps
    return actions


def execute_task_tool_plan(*, tool_plan, max_concurrent, registry_provider, seq_cursor,
                           task_id, trace_steps, tool_observations, prompt, user_id, model,
                           prepare_iteration, estimate_token_count, raise_if_should_abort,
                           touch_heartbeat, execute_item, apply_actions, persist_trace_fn,
                           complete_task_fn, record_failure_event_fn, checkpoint_start_index=1,
                           checkpoint_enabled=False, confirm_should_continue=None, allow_tool_input=None):
    common = dict(task_id=task_id, prompt=prompt, user_id=user_id, model=model,
                  estimate_token_count=estimate_token_count, make_step_id=lambda: str(uuid4()))
    outputs = {}
    for batch, batch_provider in resolved_execution_batches(tool_plan, outputs=outputs,
                                                            max_concurrent=max_concurrent,
                                                            registry_provider=registry_provider):
        batch = [(index, spec) for index, spec in batch if index >= checkpoint_start_index]
        if not batch:
            continue
        raise_if_should_abort()
        touch_heartbeat()
        if allow_tool_input is not None and not all(allow_tool_input(spec) for _, spec in batch):
            # Entire ready batch is checked before action events, workers or tool side effects.
            yield {"kind": "result", "result": {"seq_cursor": seq_cursor, "should_return": False,
                                                  "stop_reason": "repeated_action"}}
            return
        if len(batch) == 1:
            index, spec = batch[0]
            ctx = prepare_iteration(index, spec, seq_cursor + 1, batch_provider)
            if "id" in spec:
                ctx["action_step"]["meta"].update(plan_node_id=spec["id"], depends_on=spec.get("depends_on", []))
            seq_cursor += 1
            execution = None
            for item in execute_item(**common, trace_steps=trace_steps, iteration_ctx=ctx,
                                     initial_action_step=ctx["action_step"], tool_name=str(spec["name"]),
                                     tool_input=spec.get("input") if isinstance(spec.get("input"), dict) else {},
                                     raise_if_should_abort=raise_if_should_abort, registry_provider=batch_provider):
                if item["kind"] == "event":
                    yield item
                else:
                    execution = item["result"]
            assert execution is not None
            executions = iter([{"kind": "service_result", "result": execution}])
        else:
            group_id, jobs = str(uuid4()), []
            for index, spec in batch:
                ctx = prepare_iteration(index, spec, 0, batch_provider)
                if "id" in spec:
                    ctx["action_step"]["meta"].update(plan_node_id=spec["id"], depends_on=spec.get("depends_on", []))
                ctx["action_step"]["meta"].update(execution_mode="parallel",
                                                   parallel_group_id=group_id, parallel_group_size=len(batch))
                jobs.append((index, dict(**common, iteration_ctx=ctx, initial_action_step=ctx["action_step"],
                                         tool_name=str(spec["name"]), tool_input=spec.get("input", {}),
                                         registry_provider=batch_provider)))
            executions = execute_parallel_batch(jobs, raise_if_should_abort=raise_if_should_abort,
                                                touch_heartbeat=touch_heartbeat)
        try:
            for item in executions:
                if item["kind"] in {"event", "heartbeat"}:
                    yield item
                    continue
                (confirm_should_continue or raise_if_should_abort)()
                if item["kind"] == "result":
                    execution = build_tool_plan_item_service_execution(
                        task_id=task_id, trace_steps=trace_steps, user_id=user_id,
                        loop_execution_result=item["result"],
                    )
                    seq_cursor += 1
                    actions = _rebase_trace_actions(execution["service_actions"], first_seq=seq_cursor,
                                                   trace_steps=trace_steps)
                else:
                    actions = item["result"]["service_actions"]
                node = next(spec for index, spec in batch if index == item.get("index", batch[0][0]))
                # Terminal persistence must include the Trace writes applied just before it.
                # Serial builders sanitize/copy kwargs before those writes reach the owner list.
                for action in actions:
                    if action.get("kind") == "complete_task":
                        action["kwargs"]["trace_steps"] = trace_steps
                if checkpoint_enabled:
                    index = next(index for index, spec in batch if spec is node)
                    annotate_checkpoint_actions(actions, index)
                action_result = None
                for action in apply_actions(service_actions=actions, trace_steps=trace_steps,
                                            tool_observations=tool_observations, seq_cursor=seq_cursor,
                                            persist_trace_fn=persist_trace_fn, complete_task_fn=complete_task_fn,
                                            record_failure_event_fn=record_failure_event_fn):
                    if action["kind"] == "event":
                        yield action
                    else:
                        action_result = action["result"]
                assert action_result is not None
                seq_cursor = int(action_result["seq_cursor"])
                if action_result["should_return"]:
                    yield {"kind": "result", "result": {"seq_cursor": seq_cursor, "should_return": True}}
                    return
                if "id" in node:
                    outputs[node["id"]] = collect_preview(actions)
        finally:
            close = getattr(executions, "close", None)
            if close is not None:
                close()
    yield {"kind": "result", "result": {"seq_cursor": seq_cursor, "should_return": False}}
