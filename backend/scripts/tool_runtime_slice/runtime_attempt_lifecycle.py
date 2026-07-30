from __future__ import annotations

from .context import *


class RuntimeAttemptLifecycleMixin:
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
        self.assertEqual(meta["tool"]["label"], "Calculator")
        self.assertEqual(meta["tool"]["status"], "running")
        self.assertEqual(step["id"], "step-1")
        self.assertEqual(step["seq"], 3)
        self.assertEqual(step["content"], "Tool running: Calculator")

    def test_build_action_step_initial_meta_and_step_use_display_label_for_mock_plan(
        self,
    ) -> None:
        meta = build_action_step_initial_meta(
            name="mock_plan",
            tool_input={"prompt_preview": "请帮我规划"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="mock_plan",
            meta=meta,
        )

        self.assertEqual(meta["tool"]["name"], "task_plan")
        self.assertEqual(meta["tool"]["label"], "Task Planner")
        self.assertEqual(step["content"], "Tool running: Task Planner")

    def test_build_action_step_initial_meta_and_step_use_display_label_for_task_retrieve(
        self,
    ) -> None:
        meta = build_action_step_initial_meta(
            name="task_retrieve",
            tool_input={"query": "检索 demo"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
        )
        step = build_action_step_initial_step(
            step_id="step-2",
            seq=4,
            name="task_retrieve",
            meta=meta,
        )

        self.assertEqual(meta["tool"]["name"], "task_retrieve")
        self.assertEqual(meta["tool"]["label"], "Knowledge Retrieval")
        self.assertEqual(meta["tool"]["kind"], "knowledge_retrieval")
        self.assertEqual(meta["tool"]["semantic_kind"], "knowledge_retrieval")
        self.assertTrue(meta["tool"]["supports_result_preview"])
        self.assertEqual(
            meta["tool"]["effective_result_preview_keys"],
            ["hit_count", "knowledge_base_id"],
        )
        self.assertEqual(step["content"], "Tool running: Knowledge Retrieval")

    def test_build_action_step_initial_meta_includes_http_json_execution_summary(
        self,
    ) -> None:
        provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_provider_source="analytics_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "analytics_suite": {
                            "provider": "default",
                            "profile": "default",
                            "disabled_tool_names": [
                                "task_plan",
                                "task_retrieve",
                                "calc_eval",
                            ],
                            "extra_tools": {
                                "provider_search": {
                                    "template": "task_retrieve",
                                    "label": "Provider Search",
                                    "kind": "provider_retrieval",
                                    "runtime_semantic_kind": "provider_search",
                                    "execution": {
                                        "kind": "http_json",
                                        "url": "https://provider.example/search",
                                        "method": "GET",
                                        "query_params": {"q": "$query", "top_k": "$top_k"},
                                        "result_fields": {
                                            "documents_total": "$.meta.total",
                                        },
                                    },
                                    "result_preview_keys": ["documents_total"],
                                    "result_output_keys": ["documents_total"],
                                }
                            },
                        }
                    }
                ),
            )
        )

        meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "检索 demo", "top_k": 3},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registry_provider=provider,
        )

        self.assertEqual(
            meta["tool"]["execution_summary"],
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "query_param_count": 2,
                "result_field_names": ["documents_total"],
            },
        )

    def test_build_action_step_initial_step_supports_registry_provider_without_explicit_label(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Hosted Search",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "tool_kind": "provider_retrieval",
                        },
                        result_preview_keys=("documents_total",),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )

        step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="provider_search",
            meta={"tool": {"name": "provider_search"}},
            registry_provider=provider,
        )

        self.assertEqual(step["content"], "Tool running: Hosted Search")

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
                    "display_name": "Calculator",
                    "input": {"expression": "1+2*3"},
                    "kind": "local_calculator",
                    "semantic_kind": "local_calculator",
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ["expression", "result"],
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
                    "output_preview": {
                        "expression": "1+2*3",
                        "result": 7.0,
                    },
                    "kind": "local_calculator",
                    "semantic_kind": "local_calculator",
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ["expression", "result"],
                    "retry_count": 0,
                }
            },
        )

    def test_build_tool_attempt_error_events_keep_shape(self) -> None:
        self.assertEqual(
            build_tool_attempt_error_events(
                name="calc_eval",
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
                    "kind": "local_calculator",
                    "semantic_kind": "local_calculator",
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ["expression", "result"],
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

    def test_build_tool_attempt_loop_result_redacts_terminal_diagnostics_payload(
        self,
    ) -> None:
        attempt_execution = {
            "tool_end_event": {
                "status": "error",
                "message": "provider_search failed with token=hidden",
            },
            "error_event": {
                "code": "tool_execution_error",
                "message": (
                    "provider_search: http_json execution query_params.access_token must be safe"
                ),
            },
            "retryable": False,
            "next_action_step": {
                "id": "step-1",
                "seq": 3,
                "content": (
                    "provider_search: unsupported tool execution kind api_key=hidden"
                ),
            },
            "last_error": "provider_search failed with token=hidden",
            "plan_item_result": {
                "outcome": "terminal_failure",
                "error": "headers.x-api-key is invalid",
            },
            "postprocess": None,
            "success_effects": None,
            "terminal_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": (
                        "provider_search: unsupported tool execution kind api_key=hidden"
                    ),
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": (
                            "provider_search: http_json execution json_body.client_secret must be safe"
                        ),
                    },
                },
                "status": "failed",
                "error_message": "provider_search failed with token=hidden",
                "audit_detail": {
                    "path": "query_params.access_token",
                    "message": "api_key=hidden",
                },
                "state": {
                    "task_id": "task-1",
                    "phase": "error",
                    "message": "token=hidden",
                },
            },
        }

        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        serialized = json.dumps(loop_result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_attempt_loop_result_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-attempt-loop-http-json-output"
        )
        attempt_execution = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": raw_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": None,
            "success_effects": {
                "trace_step": raw_step,
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-attempt-loop-http-json-output",
                    "step": raw_step,
                },
                "observation": "Provider Status: ok",
                "output": {"status": "ready"},
                "rag_followup": None,
            },
            "terminal_effects": None,
        }

        result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_attempt_loop_result_redacts_http_json_rag_followup_trace_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-attempt-loop-http-json-rag-followup-output"
        )
        rag_followup_step = self._make_sensitive_http_json_action_step(
            step_id="rag-attempt-loop-http-json-output",
            content="Retrieved snippets",
        )
        attempt_execution = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": raw_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": None,
            "success_effects": {
                "trace_step": raw_step,
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-attempt-loop-http-json-rag-followup-output",
                    "step": raw_step,
                },
                "observation": "Provider Status: ok",
                "output": {"status": "ready"},
                "rag_followup": {
                    "step": rag_followup_step,
                    "trace": {
                        "task_id": "task-1",
                        "step_id": "rag-attempt-loop-http-json-output",
                        "step": rag_followup_step,
                    },
                },
            },
            "terminal_effects": None,
        }

        result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_attempt_loop_result_redacts_http_json_postprocess_rag_followup_trace_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-attempt-loop-http-json-postprocess-output"
        )
        rag_followup_step = self._make_sensitive_http_json_action_step(
            step_id="rag-attempt-loop-http-json-postprocess-output",
            content="Retrieved snippets",
        )
        attempt_execution = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": raw_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": {
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-attempt-loop-http-json-postprocess-output",
                    "step": raw_step,
                },
                "observation": "Provider Status: ok",
                "output": {"status": "ready"},
                "rag_followup": {
                    "step": rag_followup_step,
                    "trace": {
                        "task_id": "task-1",
                        "step_id": "rag-attempt-loop-http-json-postprocess-output",
                        "step": rag_followup_step,
                    },
                },
            },
            "success_effects": {
                "trace_step": raw_step,
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-attempt-loop-http-json-postprocess-output",
                    "step": raw_step,
                },
                "observation": "Provider Status: ok",
                "output": {"status": "ready"},
                "rag_followup": None,
            },
            "terminal_effects": None,
        }

        result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

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

    def test_build_tool_attempt_loop_terminal_result_redacts_diagnostics_payload(
        self,
    ) -> None:
        loop_result = {
            "terminal_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": (
                        "provider_search: unsupported tool execution kind api_key=hidden"
                    ),
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": (
                            "provider_search: http_json execution headers.x-api-key must be safe"
                        ),
                    },
                },
                "status": "failed",
                "error_message": "provider_search failed with token=hidden",
                "audit_detail": {
                    "path": "json_body.client_secret",
                    "message": "api_key=hidden",
                },
                "state": {
                    "task_id": "task-1",
                    "phase": "error",
                    "message": "token=hidden",
                },
            },
        }

        result = build_tool_attempt_loop_terminal_result(
            loop_result=loop_result,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

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

    def test_build_tool_plan_item_retry_loop_result_redacts_terminal_diagnostics_payload(
        self,
    ) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": (
                "provider_search: unsupported tool execution kind api_key=hidden"
            ),
        }
        terminal_effects = {
            "trace_step": action_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    **action_step,
                    "content": (
                        "provider_search: http_json execution query_params.access_token must be safe"
                    ),
                },
            },
            "status": "failed",
            "error_message": "provider_search failed with token=hidden",
            "audit_detail": {
                "path": "headers.x-api-key",
                "message": "json_body.client_secret is invalid",
            },
            "state": {
                "task_id": "task-1",
                "phase": "error",
                "message": "api_key=hidden",
            },
        }
        loop_result = {
            "tool_end_event": {"status": "error"},
            "error_event": {"code": "tool_execution_error"},
            "retryable": False,
            "next_action_step": action_step,
            "last_error": "provider_search failed with token=hidden",
            "plan_item_result": {"outcome": "terminal_failure"},
            "postprocess": None,
            "success_effects": None,
            "terminal_effects": terminal_effects,
        }

        result = build_tool_plan_item_retry_loop_result(
            loop_result=loop_result,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_retry_loop_result_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-retry-loop-http-json-output"
        )
        success_effects = {
            "trace_step": raw_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-retry-loop-http-json-output",
                "step": raw_step,
            },
            "observation": "Provider Status: ok",
            "output": {"status": "ready"},
            "rag_followup": None,
        }
        loop_result = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": raw_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": {"trace": success_effects["trace"]},
            "success_effects": success_effects,
            "terminal_effects": None,
        }

        result = build_tool_plan_item_retry_loop_result(
            loop_result=loop_result,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_plan_item_retry_loop_execution_result_redacts_loop_diagnostics_payload(
        self,
    ) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": (
                "provider_search: unsupported tool execution kind api_key=hidden"
            ),
        }
        terminal_effects = {
            "trace_step": action_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    **action_step,
                    "content": (
                        "provider_search: http_json execution json_body.client_secret must be safe"
                    ),
                },
            },
            "status": "failed",
            "error_message": "provider_search failed with token=hidden",
            "audit_detail": {
                "path": "query_params.access_token",
                "message": "headers.x-api-key is invalid",
            },
            "state": {
                "task_id": "task-1",
                "phase": "error",
                "message": "api_key=hidden",
            },
        }
        loop_result = {
            "tool_end_event": {
                "status": "error",
                "message": "provider_search failed with token=hidden",
            },
            "error_event": {
                "code": "tool_execution_error",
                "message": "headers.x-api-key is invalid",
            },
            "retryable": False,
            "next_action_step": action_step,
            "last_error": "provider_search failed with token=hidden",
            "plan_item_result": {
                "outcome": "terminal_failure",
                "error": "json_body.client_secret is invalid",
            },
            "postprocess": None,
            "success_effects": None,
            "terminal_effects": terminal_effects,
        }

        result = build_tool_plan_item_retry_loop_execution_result(
            loop_result=loop_result,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_retry_loop_execution_result_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-retry-loop-execution-http-json-output"
        )
        success_effects = {
            "trace_step": raw_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-retry-loop-execution-http-json-output",
                "step": raw_step,
            },
            "observation": "Provider Status: ok",
            "output": {"status": "ready"},
            "rag_followup": None,
        }
        loop_result = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": raw_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": {"trace": success_effects["trace"]},
            "success_effects": success_effects,
            "terminal_effects": None,
        }

        result = build_tool_plan_item_retry_loop_execution_result(
            loop_result=loop_result,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

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

        self.assertEqual(success_step["content"], "Tool done: Calculator")
        self.assertEqual(success_step["meta"]["tool"]["status"], "done")
        self.assertEqual(error_step["content"], "Tool error: Calculator")
        self.assertEqual(error_step["meta"]["tool"]["status"], "error")

    def test_build_tool_step_error_update_redacts_legacy_error_payload(self) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {},
            execution_kind="http_json",
        )
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Provider Search",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "legacy_error": (
                    "provider_search: http_json execution query_params.access_token must be safe"
                ),
                "tool": {
                    "name": "provider_search",
                    "status": "running",
                    "legacy_error": (
                        "provider_search: unsupported tool execution kind api_key=hidden"
                    ),
                },
            },
        }

        error_step = build_tool_step_error_update(
            action_step=base_step,
            name="provider_search",
            tool_input={"query": "demo"},
            retry_count=1,
            token_count=9,
            error_message="provider_search failed with token=hidden",
            registration=registration,
        )

        serialized = json.dumps(error_step, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)
        self.assertIn("provider_search failed with [redacted]", serialized)

    def test_build_tool_step_updates_support_registry_provider_without_explicit_label_or_registration(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Hosted Search",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "tool_kind": "provider_retrieval",
                        },
                        result_preview_keys=("documents_total",),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: provider_search",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "provider_search",
                    "input": {"query": "revenue trend"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            output={
                "documents_total": 2,
                "tool_kind": "provider_retrieval",
            },
            retry_count=0,
            token_count=7,
            last_error=None,
            registry_provider=provider,
        )
        error_step = build_tool_step_error_update(
            action_step=base_step,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=1,
            token_count=9,
            error_message="transient",
            registry_provider=provider,
        )

        self.assertEqual(success_step["content"], "Tool done: Hosted Search")
        self.assertEqual(error_step["content"], "Tool error: Hosted Search")

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

        self.assertEqual(transition["action_step"]["content"], "Tool done: Calculator")
        self.assertEqual(transition["action_step"]["meta"]["tool"]["status"], "done")
        self.assertEqual(
            transition["events"]["tool_end"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "done",
                "latency_ms": 12,
                "output_preview": {
                    "expression": "1+2*3",
                    "result": 7.0,
                },
                "kind": "local_calculator",
                "semantic_kind": "local_calculator",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
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

        self.assertEqual(transition["action_step"]["content"], "Tool error: Calculator")
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
                "kind": "local_calculator",
                "semantic_kind": "local_calculator",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
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

    def test_build_tool_attempt_error_transition_redacts_http_json_error_event_message(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )
        base_step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="provider_status",
            meta=build_action_step_initial_meta(
                name="provider_status",
                tool_input={"query": "status"},
                model="mock-gpt",
                label="tool_1",
                token_count=5,
                registration=registration,
            ),
            registration=registration,
        )
        ctx = build_tool_runtime_context(
            name="provider_status",
            prompt="status",
            user_id="user-1",
            attempt=0,
            registry={"provider_status": registration},
        )
        exc = MockToolExecutionError(
            "upstream failed token=hidden api_key=hidden",
            fatal=True,
        )

        transition = build_tool_attempt_error_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=ctx,
            name="provider_status",
            tool_input={"query": "status"},
            exc=exc,
            token_count=9,
            registry={"provider_status": registration},
        )
        terminal = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=transition["action_step"],  # type: ignore[arg-type]
            error_message=str(transition["error_message"]),
            retry_count=int(transition["retry_count"]),
        )

        self.assertEqual(
            transition["events"]["tool_end"]["output_preview"],
            {"error": "upstream failed [redacted] [redacted]"},
        )
        self.assertEqual(
            transition["events"]["error"]["message"],  # type: ignore[index]
            "upstream failed [redacted] [redacted]",
        )
        self.assertEqual(
            transition["error_message"],
            "upstream failed [redacted] [redacted]",
        )
        self.assertEqual(
            terminal["error_message"],
            "upstream failed [redacted] [redacted]",
        )
        combined = json.dumps(
            {"transition": transition, "terminal": terminal},
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("api_key=hidden", combined)
        self.assertNotIn("hidden", combined)

    def test_build_tool_attempt_error_transition_honors_runtime_timeout(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Custom Lookup",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "input": {"query": "secret"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        registry = {
            "custom_lookup": ToolRegistration(
                name="custom_lookup",
                kind="custom_lookup",
                label="Custom Lookup",
                retryable_by_default=False,
                default_timeout_ms=12_000,
                requires_user_context=False,
                supports_result_preview=False,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_input": tool_input,
                },
            )
        }
        ctx = build_tool_runtime_context(
            name="custom_lookup",
            prompt="lookup",
            user_id="user-1",
            attempt=0,
            registry=registry,
        )
        exc = MockToolExecutionError("fatal", fatal=True)

        transition = build_tool_attempt_error_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=ctx,
            name="custom_lookup",
            tool_input={"query": "secret"},
            exc=exc,
            token_count=9,
            display_name="Custom Lookup",
        )

        self.assertEqual(transition["events"]["tool_end"]["latency_ms"], 48)
        self.assertEqual(
            transition["events"]["tool_end"]["output_preview"],
            {"error": "fatal"},
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

    def test_build_tool_step_output_redacts_http_json_raw_output_dict(self) -> None:
        step = {
            "meta": {
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "effective_result_output_keys": ["status", "message"],
                    "output": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                }
            }
        }

        output = build_tool_step_output(step)

        self.assertEqual(
            output,
            {
                "status": "ready",
                "message": "gateway token=[redacted]",
            },
        )
        serialized = json.dumps(output, ensure_ascii=False)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)

    def test_build_tool_step_output_redacts_http_json_raw_preview_dict(self) -> None:
        step = {
            "meta": {
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "output_preview": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                }
            }
        }

        output = build_tool_step_output(step)

        self.assertEqual(
            output,
            {
                "status": "ready",
                "message": "gateway token=[redacted]",
                "access_token": "[redacted]",
            },
        )
        serialized = json.dumps(output, ensure_ascii=False)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)

    def test_build_tool_step_success_update_keeps_raw_output_and_stores_preview(
        self,
    ) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Custom Lookup",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "input": {"query": "secret"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        registration = ToolRegistration(
            name="custom_lookup",
            kind="custom_lookup",
            label="Custom Lookup",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            result_preview_keys=("tool_kind", "hit_count"),
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )
        output = {
            "tool_kind": "custom_lookup",
            "hit_count": 1,
            "secret": "do-not-preview",
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="custom_lookup",
            tool_input={"query": "secret"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Custom Lookup",
            registration=registration,
        )

        self.assertEqual(success_step["meta"]["tool"]["output"], output)
        self.assertEqual(
            success_step["meta"]["tool"]["output_preview"],
            {
                "tool_kind": "custom_lookup",
                "hit_count": 1,
            },
        )
