#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.tool_runtime import (  # type: ignore[import-not-found]
    MockToolExecutionError,
    build_action_step_initial_meta,
    build_action_step_initial_step,
    build_tool_plan,
    build_tool_attempt_bundle,
    build_tool_attempt_error_events,
    build_tool_attempt_start_events,
    build_tool_attempt_success_events,
    build_tool_attempt_execution,
    build_tool_attempt_loop_result,
    build_tool_attempt_loop_terminal_result,
    build_tool_plan_item_retry_loop_result,
    build_tool_attempt_error_transition,
    build_tool_attempt_outcome,
    build_tool_attempt_result,
    build_tool_iteration_context,
    build_tool_iteration_execution,
    build_tool_plan_item_postprocess,
    build_tool_plan_item_execution,
    build_tool_plan_item_execution_result,
    build_tool_plan_item_result,
    build_tool_plan_item_success_effects,
    build_tool_plan_item_terminal_effects,
    build_tool_plan_item_success_bundle,
    build_tool_iteration_success_artifacts,
    build_tool_rag_followup,
    build_tool_attempt_success_transition,
    build_tool_prompt_with_observations,
    build_tool_rag_step,
    build_tool_end_payload,
    build_tool_error_meta,
    build_tool_error_payload,
    build_tool_execution_policy,
    build_tool_observation_entry,
    build_tool_terminal_failure_transition,
    build_tool_phase,
    build_tool_start_payload,
    build_tool_step_output,
    build_tool_step_error_update,
    build_tool_step_success_update,
    build_tool_success_meta,
    build_tool_trace_event,
    compute_tool_retry_decision,
    execute_tool_spec,
    get_registered_tool_names,
    build_tool_result_preview,
    build_tool_runtime_context,
    ensure_tool_registration,
    get_tool_default_timeout_ms,
    is_tool_retryable_by_default,
    maybe_raise_mock_tool_execution_error,
    tool_requires_user_context,
    normalize_tool_spec,
    resolve_tool_registration,
    run_tool,
)


class ToolRuntimeSliceTests(unittest.TestCase):
    def test_build_tool_plan_keeps_calc_and_retrieve_behavior(self) -> None:
        plan = build_tool_plan("请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]")

        self.assertEqual(plan[0]["name"], "mock_plan")
        self.assertEqual(plan[1]["name"], "mock_retrieve")
        self.assertEqual(plan[1]["input"]["knowledge_base_id"], "demo")
        self.assertEqual(plan[2]["name"], "calc_eval")
        self.assertEqual(plan[2]["input"]["expression"], "1+2*3")

    def test_run_tool_keeps_calc_output_shape(self) -> None:
        output = run_tool(
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(
            output,
            {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            },
        )

    def test_run_tool_keeps_transient_error_semantics(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            run_tool(
                name="mock_plan",
                tool_input={"prompt_preview": "x"},
                prompt="[mock-tool-error]",
                user_id="user-1",
                attempt=0,
            )

        self.assertFalse(ctx.exception.fatal)
        self.assertIn("transient error", str(ctx.exception).lower())

    def test_execute_tool_spec_keeps_calc_behavior(self) -> None:
        output = execute_tool_spec(
            tool_spec={
                "name": "calc_eval",
                "input": {"expression": "2**3"},
            },
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(
            output,
            {
                "expression": "2**3",
                "result": 8.0,
                "tool_kind": "local_calculator",
            },
        )

    def test_execute_tool_spec_unknown_tool_remains_fatal(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            execute_tool_spec(
                tool_spec={"name": "does_not_exist", "input": {}},
                prompt="noop",
                user_id="user-1",
                attempt=0,
            )

        self.assertTrue(ctx.exception.fatal)
        self.assertIn("unknown mock tool", str(ctx.exception).lower())

    def test_registered_tool_names_cover_current_mock_tools(self) -> None:
        self.assertEqual(
            get_registered_tool_names(),
            ("calc_eval", "mock_plan", "mock_retrieve"),
        )

    def test_normalize_tool_spec_coerces_name_and_defaults_input(self) -> None:
        invocation = normalize_tool_spec(
            {
                "name": 123,
                "input": "not-a-dict",
            }
        )

        self.assertEqual(invocation.name, "123")
        self.assertEqual(invocation.tool_input, {})

    def test_resolve_tool_registration_exposes_explicit_calc_entry(self) -> None:
        registration = resolve_tool_registration("calc_eval")

        self.assertIsNotNone(registration)
        assert registration is not None
        self.assertEqual(registration.name, "calc_eval")
        self.assertEqual(registration.kind, "local_calculator")
        self.assertEqual(registration.label, "Calculator")
        self.assertTrue(registration.retryable_by_default)
        self.assertEqual(registration.default_timeout_ms, 3_000)
        self.assertTrue(registration.requires_user_context)
        self.assertTrue(registration.supports_result_preview)

    def test_build_tool_result_preview_keeps_current_calc_shape(self) -> None:
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        self.assertEqual(
            build_tool_result_preview(name="calc_eval", output=output),
            output,
        )

    def test_tool_runtime_helpers_expose_current_calc_defaults(self) -> None:
        self.assertTrue(tool_requires_user_context("calc_eval"))
        self.assertTrue(is_tool_retryable_by_default("calc_eval"))
        self.assertEqual(get_tool_default_timeout_ms("calc_eval"), 3_000)

    def test_ensure_tool_registration_keeps_unknown_tool_fatal(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            ensure_tool_registration("does_not_exist")

        self.assertTrue(ctx.exception.fatal)
        self.assertIn("unknown mock tool", str(ctx.exception).lower())

    def test_maybe_raise_mock_tool_execution_error_keeps_transient_semantics(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            maybe_raise_mock_tool_execution_error(
                name="mock_plan",
                prompt="[mock-tool-error]",
                attempt=0,
            )

        self.assertFalse(ctx.exception.fatal)
        self.assertIn("transient error", str(ctx.exception).lower())

    def test_build_tool_runtime_context_keeps_calc_defaults(self) -> None:
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(ctx.name, "calc_eval")
        self.assertEqual(ctx.user_id, "user-1")
        self.assertEqual(ctx.attempt, 0)
        self.assertEqual(ctx.default_timeout_ms, 3_000)
        self.assertTrue(ctx.retryable_by_default)
        self.assertTrue(ctx.requires_user_context)

    def test_compute_tool_retry_decision_keeps_current_calc_defaults(self) -> None:
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertTrue(
            compute_tool_retry_decision(
                ctx=ctx,
                exc=MockToolExecutionError("transient", fatal=False),
            )
        )
        self.assertFalse(
            compute_tool_retry_decision(
                ctx=ctx,
                exc=MockToolExecutionError("fatal", fatal=True),
            )
        )

    def test_build_tool_end_payload_keeps_preview_and_retry_shape(self) -> None:
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        self.assertEqual(
            build_tool_end_payload(
                name="calc_eval",
                task_id="task-1",
                step_id="step-1",
                output=output,
                retry_count=0,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "done",
                "latency_ms": 12,
                "output_preview": output,
                "retry_count": 0,
            },
        )

    def test_build_tool_success_and_error_meta_keep_tool_shape(self) -> None:
        tool_input = {"expression": "1+2*3"}
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        success_meta = build_tool_success_meta(
            name="calc_eval",
            tool_input=tool_input,
            output=output,
            retry_count=0,
            last_error=None,
        )
        error_meta = build_tool_error_meta(
            name="calc_eval",
            tool_input=tool_input,
            retry_count=1,
            error_message="transient",
        )

        self.assertEqual(success_meta["tool"]["name"], "calc_eval")
        self.assertEqual(success_meta["tool"]["output"], output)
        self.assertEqual(success_meta["tool"]["status"], "done")
        self.assertEqual(error_meta["tool"]["name"], "calc_eval")
        self.assertEqual(error_meta["tool"]["status"], "error")
        self.assertEqual(error_meta["tool"]["error"], "transient")

    def test_build_tool_start_and_error_payload_keep_current_shape(self) -> None:
        self.assertEqual(
            build_tool_start_payload(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                retry_count=0,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "name": "calc_eval",
                "input": {"expression": "1+2*3"},
                "retry_count": 0,
            },
        )
        self.assertEqual(
            build_tool_error_payload(
                task_id="task-1",
                step_id="step-1",
                error_message="transient",
                retry_count=1,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "error",
                "latency_ms": 12,
                "output_preview": {"error": "transient"},
                "retry_count": 1,
                "error": "transient",
            },
        )

    def test_build_tool_phase_and_policy_keep_current_calc_defaults(self) -> None:
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        policy = build_tool_execution_policy(ctx)

        self.assertEqual(build_tool_phase(0), "tool_running")
        self.assertEqual(build_tool_phase(1), "tool_retry")
        self.assertEqual(policy["max_retry"], 1)
        self.assertEqual(policy["latency_ms"], 12)
        self.assertEqual(policy["effective_user_id"], "user-1")

    def test_build_action_step_initial_meta_and_step_keep_current_shape(self) -> None:
        meta = build_action_step_initial_meta(
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            meta=meta,
        )

        self.assertEqual(meta["tool"]["name"], "calc_eval")
        self.assertEqual(meta["tool"]["status"], "running")
        self.assertEqual(step["id"], "step-1")
        self.assertEqual(step["seq"], 3)
        self.assertEqual(step["content"], "Tool running: calc_eval")

    def test_build_tool_attempt_start_and_success_events_keep_shape(self) -> None:
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }
        self.assertEqual(
            build_tool_attempt_start_events(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                attempt=0,
            ),
            {
                "tool_start": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "retry_count": 0,
                },
                "state": {
                    "task_id": "task-1",
                    "phase": "tool_running",
                },
            },
        )
        self.assertEqual(
            build_tool_attempt_success_events(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                output=output,
                retry_count=0,
            ),
            {
                "tool_end": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "status": "done",
                    "latency_ms": 12,
                    "output_preview": output,
                    "retry_count": 0,
                }
            },
        )

    def test_build_tool_attempt_error_events_keep_shape(self) -> None:
        self.assertEqual(
            build_tool_attempt_error_events(
                task_id="task-1",
                step_id="step-1",
                error_message="transient",
                retry_count=1,
            ),
            {
                "tool_end": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "status": "error",
                    "latency_ms": 12,
                    "output_preview": {"error": "transient"},
                    "retry_count": 1,
                    "error": "transient",
                }
            },
        )

    def test_build_tool_attempt_bundle_keeps_runtime_and_start_shapes(self) -> None:
        bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        self.assertEqual(bundle["start_events"]["tool_start"]["retry_count"], 1)
        self.assertEqual(bundle["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(bundle["runtime_ctx"].attempt, 1)
        self.assertEqual(bundle["runtime_policy"]["effective_user_id"], "user-1")

    def test_build_tool_attempt_execution_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        result = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["start_events"]["state"]["phase"], "tool_running")
        self.assertEqual(result["tool_end_event"]["status"], "done")
        self.assertFalse(bool(result["retryable"]))
        self.assertIsNotNone(result["success_effects"])
        self.assertIsNone(result["terminal_effects"])

    def test_build_tool_attempt_execution_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        result = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(result["tool_end_event"]["status"], "error")
        self.assertFalse(bool(result["retryable"]))
        self.assertIsNone(result["success_effects"])
        self.assertIsNotNone(result["terminal_effects"])

    def test_build_tool_attempt_loop_result_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        self.assertEqual(loop_result["tool_end_event"]["status"], "done")
        self.assertFalse(bool(loop_result["retryable"]))
        self.assertIsNotNone(loop_result["success_effects"])
        self.assertIsNone(loop_result["terminal_effects"])

    def test_build_tool_attempt_loop_result_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        self.assertEqual(loop_result["tool_end_event"]["status"], "error")
        self.assertFalse(bool(loop_result["retryable"]))
        self.assertIsNone(loop_result["success_effects"])
        self.assertIsNotNone(loop_result["terminal_effects"])

    def test_build_tool_attempt_loop_terminal_result_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )
        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        terminal = build_tool_attempt_loop_terminal_result(
            loop_result=loop_result,
        )

        self.assertFalse(bool(terminal["should_return"]))
        self.assertIsNone(terminal["terminal_effects"])

    def test_build_tool_attempt_loop_terminal_result_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )
        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        terminal = build_tool_attempt_loop_terminal_result(
            loop_result=loop_result,
        )

        self.assertTrue(bool(terminal["should_return"]))
        self.assertIsNotNone(terminal["terminal_effects"])
        self.assertEqual(terminal["terminal_effects"]["state"]["phase"], "error")

    def test_build_tool_plan_item_retry_loop_result_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_effects = {
            "trace_step": action_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": action_step,
            },
            "observation": 'calc_eval: {"expression": "1+2*3", "result": 7.0, "tool_kind": "local_calculator"}',
            "output": {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            },
            "rag_followup": None,
        }
        loop_result = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": action_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": {"trace": success_effects["trace"]},
            "success_effects": success_effects,
            "terminal_effects": None,
        }

        result = build_tool_plan_item_retry_loop_result(
            loop_result=loop_result,
        )

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["trace_event"]["step"]["content"], "Tool done: calc_eval")
        self.assertIsNotNone(result["success_effects"])
        self.assertIsNone(result["terminal_effects"])

    def test_build_tool_plan_item_retry_loop_result_keeps_terminal_failure_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_effects = {
            "trace_step": action_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": action_step,
            },
            "status": "failed",
            "error_message": "transient",
            "audit_detail": {"step_id": "step-1", "retry_count": 2},
            "state": {"task_id": "task-1", "phase": "error"},
        }
        loop_result = {
            "tool_end_event": {"status": "error"},
            "error_event": {"code": "tool_execution_error"},
            "retryable": False,
            "next_action_step": action_step,
            "last_error": "transient",
            "plan_item_result": {"outcome": "terminal_failure"},
            "postprocess": None,
            "success_effects": None,
            "terminal_effects": terminal_effects,
        }

        result = build_tool_plan_item_retry_loop_result(
            loop_result=loop_result,
        )

        self.assertEqual(result["outcome"], "terminal_failure")
        self.assertEqual(result["trace_event"]["step"]["content"], "Tool error: calc_eval")
        self.assertIsNone(result["success_effects"])
        self.assertIsNotNone(result["terminal_effects"])

    def test_build_tool_step_updates_keep_current_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )
        error_step = build_tool_step_error_update(
            action_step=base_step,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            retry_count=1,
            token_count=9,
            error_message="transient",
        )

        self.assertEqual(success_step["content"], "Tool done: calc_eval")
        self.assertEqual(success_step["meta"]["tool"]["status"], "done")
        self.assertEqual(error_step["content"], "Tool error: calc_eval")
        self.assertEqual(error_step["meta"]["tool"]["status"], "error")

    def test_build_tool_attempt_success_transition_keeps_current_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        transition = build_tool_attempt_success_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(transition["action_step"]["content"], "Tool done: calc_eval")
        self.assertEqual(transition["action_step"]["meta"]["tool"]["status"], "done")
        self.assertEqual(
            transition["events"]["tool_end"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "done",
                "latency_ms": 12,
                "output_preview": output,
                "retry_count": 0,
            },
        )

    def test_build_tool_attempt_error_transition_keeps_current_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        exc = MockToolExecutionError("transient", fatal=False)

        transition = build_tool_attempt_error_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            exc=exc,
            token_count=9,
        )

        self.assertEqual(transition["action_step"]["content"], "Tool error: calc_eval")
        self.assertEqual(transition["action_step"]["meta"]["tool"]["status"], "error")
        self.assertTrue(transition["retryable"])
        self.assertEqual(
            transition["events"]["tool_end"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "error",
                "latency_ms": 12,
                "output_preview": {"error": "transient"},
                "retry_count": 1,
                "error": "transient",
            },
        )
        self.assertEqual(
            transition["events"]["error"],
            {
                "task_id": "task-1",
                "message": "transient",
                "code": "tool_execution_error",
                "fatal": False,
                "retryable": True,
                "retryCount": 1,
                "step_id": "step-1",
            },
        )

    def test_build_tool_step_output_returns_output_dict_when_present(self) -> None:
        step = {
            "meta": {
                "tool": {
                    "output": {
                        "result": 7.0,
                    }
                }
            }
        }

        self.assertEqual(build_tool_step_output(step), {"result": 7.0})

    def test_build_tool_observation_entry_keeps_current_shape(self) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="calc_eval",
                output={
                    "expression": "1+2*3",
                    "result": 7.0,
                    "tool_kind": "local_calculator",
                },
            ),
            'calc_eval: {"expression": "1+2*3", "result": 7.0, "tool_kind": "local_calculator"}',
        )

    def test_build_tool_trace_event_keeps_current_shape(self) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                }
            },
        }

        self.assertEqual(
            build_tool_trace_event(
                task_id="task-1",
                step_id="step-1",
                step=step,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": step,
            },
        )

    def test_build_tool_terminal_failure_transition_keeps_current_shape(self) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }

        transition = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=step,
            error_message="transient",
            retry_count=1,
        )

        self.assertEqual(
            transition["trace"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": step,
            },
        )
        self.assertEqual(
            transition["audit_detail"],
            {
                "step_id": "step-1",
                "retry_count": 1,
            },
        )
        self.assertEqual(
            transition["state"],
            {
                "task_id": "task-1",
                "phase": "error",
            },
        )
        self.assertEqual(transition["status"], "failed")
        self.assertEqual(transition["error_message"], "transient")

    def test_build_tool_rag_step_keeps_current_shape(self) -> None:
        self.assertEqual(
            build_tool_rag_step(
                step_id="rag-1",
                seq=4,
                model="mock-gpt",
                chunks=["a", "b"],
                knowledge_base_id="demo",
                token_count=2,
            ),
            {
                "id": "rag-1",
                "seq": 4,
                "type": "thought",
                "content": "Retrieved snippets from mock knowledge base.",
                "meta": {
                    "model": "mock-gpt",
                    "step_type": "rag_retrieval",
                    "tokens": 2,
                    "cost_estimate": None,
                    "rag": {
                        "chunks": ["a", "b"],
                        "knowledge_base_id": "demo",
                    },
                },
            },
        )

    def test_build_tool_prompt_with_observations_keeps_current_shape(self) -> None:
        self.assertEqual(
            build_tool_prompt_with_observations(
                prompt="hello",
                tool_observations=[],
            ),
            "hello",
        )
        self.assertEqual(
            build_tool_prompt_with_observations(
                prompt="hello",
                tool_observations=["calc_eval: {\"result\": 7.0}"],
            ),
            'hello\n\nTool observations:\ncalc_eval: {"result": 7.0}',
        )

    def test_build_tool_attempt_result_keeps_success_shape(self) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {"result": 7.0},
                }
            },
        }

        self.assertEqual(
            build_tool_attempt_result(
                outcome="success",
                action_step=step,
                events={
                    "tool_end": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "status": "done",
                    }
                },
                retryable=False,
                error_message=None,
                retry_count=0,
            ),
            {
                "outcome": "success",
                "action_step": step,
                "events": {
                    "tool_end": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "status": "done",
                    }
                },
                "retryable": False,
                "error_message": None,
                "retry_count": 0,
            },
        )

    def test_build_tool_attempt_outcome_keeps_success_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        outcome = build_tool_attempt_outcome(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=build_tool_runtime_context(
                name="calc_eval",
                prompt="calc",
                user_id="user-1",
                attempt=0,
            ),
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(outcome["outcome"], "success")
        self.assertFalse(outcome["retryable"])
        self.assertIsNone(outcome["error_message"])
        self.assertEqual(outcome["retry_count"], 0)
        self.assertEqual(outcome["action_step"]["content"], "Tool done: calc_eval")
        self.assertEqual(outcome["events"]["tool_end"]["status"], "done")

    def test_build_tool_attempt_outcome_keeps_error_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        outcome = build_tool_attempt_outcome(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
        )

        self.assertEqual(outcome["outcome"], "error")
        self.assertTrue(outcome["retryable"])
        self.assertEqual(outcome["error_message"], "transient")
        self.assertEqual(outcome["retry_count"], 1)
        self.assertEqual(outcome["action_step"]["content"], "Tool error: calc_eval")
        self.assertEqual(outcome["events"]["tool_end"]["status"], "error")

    def test_build_tool_iteration_context_keeps_current_shape(self) -> None:
        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        self.assertEqual(context["step_id"], "step-1")
        self.assertEqual(context["action_step"]["id"], "step-1")
        self.assertEqual(context["action_step"]["seq"], 3)
        self.assertEqual(context["action_step"]["content"], "Tool running: calc_eval")
        self.assertEqual(context["action_step"]["meta"]["tool"]["status"], "running")

    def test_build_tool_iteration_success_artifacts_keeps_current_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )

        self.assertEqual(
            artifacts["trace"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": action_step,
            },
        )
        self.assertEqual(
            artifacts["observation"],
            'calc_eval: {"expression": "1+2*3", "result": 7.0, "tool_kind": "local_calculator"}',
        )
        self.assertEqual(
            artifacts["output"],
            {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            },
        )

    def test_build_tool_rag_followup_keeps_current_shape(self) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="mock_retrieve",
            output={
                "chunks": ["a", "b"],
                "knowledge_base_id": "demo",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"],
            {
                "id": "rag-1",
                "seq": 4,
                "type": "thought",
                "content": "Retrieved snippets from mock knowledge base.",
                "meta": {
                    "model": "mock-gpt",
                    "step_type": "rag_retrieval",
                    "tokens": 2,
                    "cost_estimate": None,
                    "rag": {
                        "chunks": ["a", "b"],
                        "knowledge_base_id": "demo",
                    },
                },
            },
        )
        self.assertEqual(
            followup["trace"],
            {
                "task_id": "task-1",
                "step_id": "rag-1",
                "step": followup["step"],
            },
        )

    def test_build_tool_iteration_execution_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        execution = build_tool_iteration_execution(
            task_id="task-1",
            step_id="step-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(
            execution["start_events"],
            {
                "tool_start": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "retry_count": 0,
                },
                "state": {
                    "task_id": "task-1",
                    "phase": "tool_running",
                },
            },
        )
        self.assertEqual(execution["outcome"]["outcome"], "success")
        self.assertEqual(execution["outcome"]["events"]["tool_end"]["status"], "done")
        self.assertEqual(
            execution["success_artifacts"]["trace"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": execution["outcome"]["action_step"],
            },
        )
        self.assertIsNone(execution["terminal_failure"])

    def test_build_tool_iteration_execution_keeps_terminal_error_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        execution = build_tool_iteration_execution(
            task_id="task-1",
            step_id="step-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
        )

        self.assertEqual(execution["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(execution["outcome"]["outcome"], "error")
        self.assertFalse(execution["outcome"]["retryable"])
        self.assertIsNone(execution["success_artifacts"])
        self.assertIsNotNone(execution["terminal_failure"])
        assert execution["terminal_failure"] is not None
        self.assertEqual(execution["terminal_failure"]["status"], "failed")
        self.assertEqual(execution["terminal_failure"]["state"]["phase"], "error")

    def test_build_tool_iteration_execution_uses_current_action_step_on_retry(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        current_step = build_tool_step_error_update(
            action_step=iteration_ctx["action_step"],
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            retry_count=1,
            token_count=9,
            error_message="transient",
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        execution = build_tool_iteration_execution(
            task_id="task-1",
            step_id="step-1",
            iteration_ctx=iteration_ctx,
            action_step=current_step,
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error="transient",
        )

        self.assertEqual(execution["start_events"]["tool_start"]["retry_count"], 1)
        self.assertEqual(execution["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(
            execution["outcome"]["action_step"]["meta"]["tool"]["error"],
            "transient",
        )
        self.assertEqual(
            execution["outcome"]["action_step"]["meta"]["tool"]["retry_count"],
            1,
        )

    def test_build_tool_plan_item_success_bundle_keeps_current_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )

        bundle = build_tool_plan_item_success_bundle(
            success_artifacts=success_artifacts,
            rag_followup=None,
        )

        self.assertEqual(bundle["trace"], success_artifacts["trace"])
        self.assertEqual(bundle["observation"], success_artifacts["observation"])
        self.assertEqual(bundle["output"], success_artifacts["output"])
        self.assertIsNone(bundle["rag_followup"])

    def test_build_tool_plan_item_result_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )

        result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=None,
            ),
            terminal_failure=None,
        )

        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(result["last_error"])
        self.assertIsNotNone(result["success_bundle"])
        self.assertIsNone(result["terminal_failure"])

    def test_build_tool_plan_item_result_keeps_terminal_failure_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_failure = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            error_message="transient",
            retry_count=2,
        )

        result = build_tool_plan_item_result(
            outcome="terminal_failure",
            action_step=action_step,
            last_error="transient",
            success_bundle=None,
            terminal_failure=terminal_failure,
        )

        self.assertEqual(result["outcome"], "terminal_failure")
        self.assertEqual(result["last_error"], "transient")
        self.assertIsNone(result["success_bundle"])
        self.assertEqual(result["terminal_failure"]["status"], "failed")

    def test_build_tool_plan_item_execution_result_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )
        iteration_execution = {
            "outcome": {
                "action_step": action_step,
                "error_message": None,
            },
            "success_artifacts": success_artifacts,
            "terminal_failure": None,
        }

        result = build_tool_plan_item_execution_result(
            iteration_execution=iteration_execution,
            rag_followup=None,
        )

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["success_bundle"]["trace"], success_artifacts["trace"])
        self.assertIsNone(result["terminal_failure"])

    def test_build_tool_plan_item_execution_result_keeps_terminal_failure_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_failure = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            error_message="transient",
            retry_count=2,
        )
        iteration_execution = {
            "outcome": {
                "action_step": action_step,
                "error_message": "transient",
            },
            "success_artifacts": None,
            "terminal_failure": terminal_failure,
        }

        result = build_tool_plan_item_execution_result(
            iteration_execution=iteration_execution,
            rag_followup=None,
        )

        self.assertEqual(result["outcome"], "terminal_failure")
        self.assertEqual(result["last_error"], "transient")
        self.assertIsNone(result["success_bundle"])
        self.assertEqual(result["terminal_failure"]["status"], "failed")

    def test_build_tool_plan_item_execution_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["plan_item_result"]["outcome"], "success")
        self.assertEqual(result["start_events"]["state"]["phase"], "tool_running")
        self.assertEqual(
            result["plan_item_result"]["success_bundle"]["trace"]["step"]["content"],
            "Tool done: calc_eval",
        )
        self.assertEqual(result["tool_end_event"]["status"], "done")
        self.assertFalse(bool(result["retryable"]))
        self.assertIsNone(result["error_event"])
        self.assertIsNotNone(result["postprocess"])
        self.assertIsNotNone(result["success_effects"])
        self.assertIsNone(result["terminal_effects"])
        self.assertEqual(
            result["success_effects"]["trace"]["step"]["content"],
            "Tool done: calc_eval",
        )
        self.assertEqual(
            result["next_action_step"]["content"],
            "Tool done: calc_eval",
        )
        self.assertIsNone(result["terminal_failure"])

    def test_build_tool_plan_item_execution_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["plan_item_result"]["outcome"], "terminal_failure")
        self.assertEqual(result["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(result["last_error"], "transient")
        self.assertEqual(result["tool_end_event"]["status"], "error")
        self.assertFalse(bool(result["retryable"]))
        self.assertEqual(result["error_event"]["code"], "tool_execution_error")
        self.assertIsNone(result["postprocess"])
        self.assertIsNone(result["success_effects"])
        self.assertIsNotNone(result["terminal_effects"])
        self.assertEqual(result["terminal_effects"]["state"]["phase"], "error")
        self.assertIsNotNone(result["terminal_failure"])
        assert result["terminal_failure"] is not None
        self.assertEqual(result["terminal_failure"]["status"], "failed")

    def test_build_tool_plan_item_execution_builds_rag_followup_for_retrieve(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="mock_retrieve",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="mock_retrieve",
            prompt="检索 demo",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "chunks": ["alpha", "beta"],
            "knowledge_base_id": "demo-kb",
            "hit_count": 2,
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="mock_retrieve",
            tool_input={"query": "demo"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-1",
            rag_token_count=2,
        )

        rag_followup = result["plan_item_result"]["success_bundle"]["rag_followup"]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(rag_followup["step"]["id"], "rag-1")
        self.assertEqual(rag_followup["step"]["meta"]["tokens"], 2)
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"]["knowledge_base_id"],
            "demo-kb",
        )

    def test_build_tool_plan_item_execution_exposes_iteration_execution_bundle(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(
            result["iteration_execution"]["outcome"]["events"]["tool_end"]["status"],
            "done",
        )
        self.assertEqual(
            result["iteration_execution"]["start_events"]["state"]["phase"],
            "tool_running",
        )

    def test_build_tool_plan_item_postprocess_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )
        plan_item_result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=None,
            ),
            terminal_failure=None,
        )

        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )

        self.assertEqual(postprocess["trace"], success_artifacts["trace"])
        self.assertEqual(
            postprocess["observation"],
            'calc_eval: {"expression": "1+2*3", "result": 7.0, "tool_kind": "local_calculator"}',
        )
        self.assertEqual(postprocess["output"], success_artifacts["output"])
        self.assertIsNone(postprocess["rag_followup"])

    def test_build_tool_plan_item_success_effects_keep_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )
        plan_item_result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=None,
            ),
            terminal_failure=None,
        )
        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )

        effects = build_tool_plan_item_success_effects(
            action_step=action_step,
            postprocess=postprocess,
        )

        self.assertEqual(effects["trace_step"]["id"], "step-1")
        self.assertEqual(effects["trace"]["step"]["content"], "Tool done: calc_eval")
        self.assertEqual(
            effects["observation"],
            'calc_eval: {"expression": "1+2*3", "result": 7.0, "tool_kind": "local_calculator"}',
        )
        self.assertIsNone(effects["rag_followup"])

    def test_build_tool_plan_item_postprocess_keeps_rag_followup_shape(self) -> None:
        rag_followup = {
            "step": {
                "id": "rag-1",
                "seq": 4,
            },
            "trace": {
                "task_id": "task-1",
                "step_id": "rag-1",
                "step": {
                    "id": "rag-1",
                    "seq": 4,
                },
            },
        }
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: mock_retrieve",
            "meta": {
                "tool": {
                    "name": "mock_retrieve",
                    "status": "done",
                    "output": {
                        "chunks": ["alpha"],
                        "knowledge_base_id": "demo-kb",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="mock_retrieve",
        )
        plan_item_result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=rag_followup,
            ),
            terminal_failure=None,
        )

        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )

        self.assertEqual(postprocess["rag_followup"], rag_followup)

    def test_build_tool_plan_item_terminal_effects_keep_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_failure = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            error_message="transient",
            retry_count=2,
        )

        effects = build_tool_plan_item_terminal_effects(
            action_step=action_step,
            terminal_failure=terminal_failure,
        )

        self.assertEqual(effects["trace_step"]["id"], "step-1")
        self.assertEqual(effects["trace"]["step"]["content"], "Tool error: calc_eval")
        self.assertEqual(effects["status"], "failed")
        self.assertEqual(effects["error_message"], "transient")
        self.assertEqual(effects["state"]["phase"], "error")


if __name__ == "__main__":
    unittest.main()
