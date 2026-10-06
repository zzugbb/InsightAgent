"""Task tool coordinator: serial side effects and stable Trace ordering for concurrent reads."""

from copy import deepcopy
from uuid import uuid4

from app.services.task_tool_parallel import execution_batches, execute_parallel_batch
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
                           complete_task_fn, record_failure_event_fn):
    common = dict(task_id=task_id, prompt=prompt, user_id=user_id, model=model,
                  estimate_token_count=estimate_token_count, make_step_id=lambda: str(uuid4()))
    for batch, batch_provider in execution_batches(tool_plan, max_concurrent=max_concurrent,
                                                  registry_provider=registry_provider):
        raise_if_should_abort()
        touch_heartbeat()
        if len(batch) == 1:
            index, spec = batch[0]
            ctx = prepare_iteration(index, spec, seq_cursor + 1, batch_provider)
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
        finally:
            close = getattr(executions, "close", None)
            if close is not None:
                close()
    yield {"kind": "result", "result": {"seq_cursor": seq_cursor, "should_return": False}}
