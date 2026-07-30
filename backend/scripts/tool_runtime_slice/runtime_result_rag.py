from __future__ import annotations

from .context import *


class RuntimeResultRagMixin:
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

    def test_build_tool_trace_event_redacts_http_json_step_output_payloads(self) -> None:
        step = {
            "id": "step-http-json-trace-output",
            "seq": 4,
            "type": "action",
            "content": "Tool done: Provider Status",
            "meta": {
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "status": "done",
                    "execution_kind": "http_json",
                    "effective_result_output_keys": ["status", "message"],
                    "output": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                    "output_preview": {
                        "status": "ready",
                        "message": "preview token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        }

        event = build_tool_trace_event(
            task_id="task-1",
            step_id="step-http-json-trace-output",
            step=step,
        )

        tool_meta = event["step"]["meta"]["tool"]
        self.assertEqual(
            tool_meta["output"],
            {
                "status": "ready",
                "message": "gateway token=[redacted]",
            },
        )
        self.assertEqual(
            tool_meta["output_preview"],
            {
                "status": "ready",
                "message": "preview token=[redacted]",
                "access_token": "[redacted]",
            },
        )
        serialized = json.dumps(event, ensure_ascii=False)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)

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

    def test_build_tool_terminal_failure_transition_redacts_raw_diagnostics_payload(
        self,
    ) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": (
                "provider_search: unsupported tool execution kind api_key=hidden"
            ),
            "meta": {
                "tool": {
                    "name": "provider_search",
                    "status": "error",
                    "error": (
                        "provider_search: http_json execution query_params.access_token must be safe"
                    ),
                }
            },
        }

        transition = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=step,
            error_message="provider_search failed with token=hidden",
            retry_count=1,
        )

        serialized = json.dumps(transition, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)
        self.assertIn("provider_search failed with [redacted]", serialized)

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
                "content": "Knowledge Retrieval returned snippets from the selected knowledge base.",
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

    def test_build_tool_attempt_result_redacts_error_payload(self) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": (
                "provider_search: unsupported tool execution kind api_key=hidden"
            ),
            "meta": {
                "tool": {
                    "name": "provider_search",
                    "status": "error",
                    "error": (
                        "provider_search: http_json execution query_params.access_token must be safe"
                    ),
                }
            },
        }

        result = build_tool_attempt_result(
            outcome="error",
            action_step=step,
            events={
                "tool_end": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "status": "error",
                    "error": "headers.x-api-key is invalid",
                },
                "error": {
                    "task_id": "task-1",
                    "message": "provider_search failed with token=hidden",
                    "code": "tool_execution_error",
                },
            },
            retryable=False,
            error_message="provider_search failed with token=hidden",
            retry_count=1,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)
        self.assertIn("provider_search failed with [redacted]", serialized)

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
        self.assertEqual(outcome["action_step"]["content"], "Tool done: Calculator")
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
        self.assertEqual(outcome["action_step"]["content"], "Tool error: Calculator")
        self.assertEqual(outcome["events"]["tool_end"]["status"], "error")

    def test_build_tool_attempt_outcome_redacts_error_payload(self) -> None:
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
        registry = {"provider_search": registration}
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Provider Search",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "legacy_error": (
                    "provider_search: http_json execution json_body.client_secret must be safe"
                ),
                "tool": {
                    "name": "provider_search",
                    "status": "running",
                },
            },
        }

        outcome = build_tool_attempt_outcome(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=build_tool_runtime_context(
                name="provider_search",
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry=registry,
            ),
            name="provider_search",
            tool_input={"query": "demo"},
            output=None,
            exc=MockToolExecutionError("provider_search failed with token=hidden", fatal=True),
            token_count=9,
            last_error=None,
            registry=registry,
        )

        serialized = json.dumps(outcome, default=str)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)
        self.assertIn("provider_search failed with [redacted]", serialized)

    def test_build_tool_attempt_outcome_honors_runtime_preview_policy(self) -> None:
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
                    "documents": [{"title": "Secret"}],
                    "tool_kind": "custom_lookup",
                },
            )
        }

        outcome = build_tool_attempt_outcome(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=build_tool_runtime_context(
                name="custom_lookup",
                prompt="lookup",
                user_id="user-1",
                attempt=0,
                registry=registry,
            ),
            name="custom_lookup",
            tool_input={"query": "secret"},
            output={
                "documents": [{"title": "Secret"}],
                "tool_kind": "custom_lookup",
            },
            exc=None,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(outcome["events"]["tool_end"]["latency_ms"], 48)
        self.assertIsNone(outcome["events"]["tool_end"]["output_preview"])

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
        self.assertEqual(context["action_step"]["content"], "Tool running: Calculator")
        self.assertEqual(context["action_step"]["meta"]["tool"]["status"], "running")

    def test_build_tool_iteration_context_uses_explicit_display_name_for_extra_tool(
        self,
    ) -> None:
        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval_fast",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Fast Calculator",
        )

        self.assertEqual(context["action_step"]["content"], "Tool running: Fast Calculator")
        self.assertEqual(
            context["action_step"]["meta"]["tool"]["label"],
            "Fast Calculator",
        )

    def test_build_tool_iteration_context_humanizes_unlabeled_real_tool_display_name(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=True,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "query": str(tool_input.get("query", "")),
                "documents_total": 1,
            },
            runtime_semantic_kind="provider_search",
        )
        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            registration=registration,
        )

        self.assertEqual(context["action_step"]["content"], "Tool running: Provider Search")
        self.assertEqual(
            context["action_step"]["meta"]["tool"]["label"],
            "Provider Search",
        )

    def test_build_tool_iteration_context_normalizes_task_plan_input_for_extra_planner_registry(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        },
                        "mock_plan_brief": {
                            "template": "mock_plan",
                            "label": "Brief Planner",
                        },
                    }
                ),
                tool_registry_overrides_json=None,
            )
        )

        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_plan",
            tool_input={
                "prompt_preview": "please plan",
                "planned_tool_names": ["mock_plan_brief", "calc_eval_fast"],
                "planned_tool_execution_kinds": ["mock", "http_json"],
            },
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            context["action_step"]["meta"]["tool"]["input"],
            {
                "prompt_preview": "please plan",
                "planned_tool_names": ["calc_eval_fast"],
                "planned_tool_labels": ["Fast Calculator"],
                "planned_tool_kinds": ["local_calculator"],
                "planned_tool_execution_kinds": [""],
            },
        )

    def test_build_tool_iteration_context_normalizes_tuple_task_plan_inputs(self) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        },
                        "mock_plan_brief": {
                            "template": "mock_plan",
                            "label": "Brief Planner",
                        },
                    }
                ),
                tool_registry_overrides_json=None,
            )
        )

        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_plan",
            tool_input={
                "prompt_preview": "please plan",
                "planned_tool_names": ("mock_plan_brief", "calc_eval_fast"),
                "planned_tool_labels": ("Brief Planner", "Fast Calculator"),
            },
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            context["action_step"]["meta"]["tool"]["input"],
            {
                "prompt_preview": "please plan",
                "planned_tool_names": ["calc_eval_fast"],
                "planned_tool_labels": ["Fast Calculator"],
                "planned_tool_kinds": ["local_calculator"],
                "planned_tool_execution_kinds": [""],
            },
        )

    def test_build_tool_iteration_context_normalizes_wrapped_task_plan_inputs(self) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        },
                        "mock_plan_brief": {
                            "template": "mock_plan",
                            "label": "Brief Planner",
                        },
                    }
                ),
                tool_registry_overrides_json=None,
            )
        )

        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_plan",
            tool_input={
                "prompt_preview": UserString("please plan"),
                "planned_tool_names": UserList(
                    [UserString("mock_plan_brief"), UserString("calc_eval_fast")]
                ),
                "planned_tool_labels": UserList(
                    [UserString("Brief Planner"), UserString("Fast Calculator")]
                ),
            },
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            context["action_step"]["meta"]["tool"]["input"],
            {
                "prompt_preview": UserString("please plan"),
                "planned_tool_names": ["calc_eval_fast"],
                "planned_tool_labels": ["Fast Calculator"],
                "planned_tool_kinds": ["local_calculator"],
                "planned_tool_execution_kinds": [""],
            },
        )

    def test_build_tool_iteration_success_artifacts_use_preview_aware_observation_shape(self) -> None:
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-1",
                "seq": 3,
                "type": "action",
                "content": "Tool running: calc_eval",
                "meta": {
                    "tool": {
                        "name": "calc_eval",
                        "status": "running",
                    }
                },
            },
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output={
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            },
            retry_count=0,
            token_count=7,
            last_error=None,
        )

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
            artifacts["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "expression": "1+2*3",
                "result": 7.0,
            },
        )
        self.assertEqual(
            artifacts["observation"],
            'Calculator: {"expression": "1+2*3", "result": 7.0}',
        )
        self.assertEqual(
            artifacts["output"],
            {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            },
        )

    def test_build_tool_iteration_success_artifacts_infer_preview_shape_for_extra_provider_calc_kind(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_math",
            kind="provider_calc",
            label="Provider Math",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "provider_calc",
            "raw_payload": {"audit": "keep-raw-only"},
        }
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-2",
                "seq": 4,
                "type": "action",
                "content": "Tool running: Provider Math",
                "meta": {
                    "tool": {
                        "name": "provider_math",
                        "label": "Provider Math",
                        "status": "running",
                    }
                },
            },
            name="provider_math",
            tool_input={"expression": "1+2*3"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Provider Math",
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-2",
            action_step=action_step,
            name="provider_math",
            display_name="Provider Math",
            registration=registration,
        )

        self.assertEqual(
            artifacts["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "expression": "1+2*3",
                "result": 7.0,
            },
        )
        self.assertEqual(
            artifacts["observation"],
            "Provider Math: Calculated 1+2*3 = 7.0.",
        )
        self.assertEqual(
            artifacts["output"],
            {
                "expression": "1+2*3",
                "result": 7.0,
            },
        )

    def test_build_tool_iteration_success_artifacts_supports_registry_provider_without_explicit_display_name_or_registration(
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
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-2",
                "seq": 4,
                "type": "action",
                "content": "Tool running: provider_search",
                "meta": {
                    "tool": {
                        "name": "provider_search",
                        "status": "running",
                    }
                },
            },
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

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-2",
            action_step=action_step,
            name="provider_search",
            registry_provider=provider,
        )

        self.assertEqual(
            artifacts["observation"],
            "Hosted Search: Retrieved 2 documents.",
        )

    def test_build_tool_iteration_success_artifacts_reuses_step_meta_summary_without_registry_context(
        self,
    ) -> None:
        registration = ToolRegistration(
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
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-2",
                "seq": 4,
                "type": "action",
                "content": "Tool running: provider_search",
                "meta": {
                    "tool": {
                        "name": "provider_search",
                        "status": "running",
                    }
                },
            },
            name="provider_search",
            tool_input={"query": "revenue trend"},
            output={
                "documents_total": 2,
                "tool_kind": "provider_retrieval",
            },
            retry_count=0,
            token_count=7,
            last_error=None,
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-2",
            action_step=action_step,
            name="provider_search",
        )

        self.assertEqual(
            artifacts["observation"],
            "Hosted Search: Retrieved 2 documents.",
        )
        self.assertEqual(
            artifacts["output"],
            {
                "documents_total": 2,
            },
        )

    def test_build_tool_iteration_success_artifacts_infer_preview_shape_for_extra_provider_planner_kind(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_plan",
            kind="provider_planner",
            label="Provider Planner",
            retryable_by_default=False,
            default_timeout_ms=8_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )
        output = {
            "plan": "Analyze request -> Synthesize final answer",
            "steps": [
                "Analyze request",
                "Synthesize final answer",
            ],
            "tool_kind": "provider_planner",
            "raw_payload": {"audit": "keep-raw-only"},
        }
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-3",
                "seq": 5,
                "type": "action",
                "content": "Tool running: Provider Planner",
                "meta": {
                    "tool": {
                        "name": "provider_plan",
                        "label": "Provider Planner",
                        "status": "running",
                    }
                },
            },
            name="provider_plan",
            tool_input={"prompt_preview": "please plan"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Provider Planner",
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-3",
            action_step=action_step,
            name="provider_plan",
            display_name="Provider Planner",
            registration=registration,
        )

        self.assertEqual(
            artifacts["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )
        self.assertEqual(
            artifacts["observation"],
            "Provider Planner: Planned steps - Analyze request -> Synthesize final answer.",
        )
        self.assertEqual(
            artifacts["output"],
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )

    def test_build_tool_iteration_success_artifacts_infer_preview_shape_for_extra_provider_planner_kind_with_tuple_steps(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_plan",
            kind="provider_planner",
            label="Provider Planner",
            retryable_by_default=False,
            default_timeout_ms=8_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )
        output = {
            "plan": "Analyze request -> Synthesize final answer",
            "steps": (
                "Analyze request",
                "Synthesize final answer",
            ),
            "tool_kind": "provider_planner",
            "raw_payload": {"audit": "keep-raw-only"},
        }
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-3",
                "seq": 5,
                "type": "action",
                "content": "Tool running: Provider Planner",
                "meta": {
                    "tool": {
                        "name": "provider_plan",
                        "label": "Provider Planner",
                        "status": "running",
                    }
                },
            },
            name="provider_plan",
            tool_input={"prompt_preview": "please plan"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Provider Planner",
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-3",
            action_step=action_step,
            name="provider_plan",
            display_name="Provider Planner",
            registration=registration,
        )

        self.assertEqual(
            artifacts["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )
        self.assertEqual(
            artifacts["observation"],
            "Provider Planner: Planned steps - Analyze request -> Synthesize final answer.",
        )
        self.assertEqual(
            artifacts["output"],
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )

    def test_build_tool_iteration_success_artifacts_reuses_step_meta_summary_for_hot_retrieval_without_registry_context(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="task_retrieve_hot",
            kind="hot_knowledge_retrieval",
            label="Hot Retrieval",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            result_preview_keys=("tool_kind", "hit_count", "knowledge_base_id"),
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )
        output = {
            "tool_kind": "hot_knowledge_retrieval",
            "hit_count": 2,
            "knowledge_base_id": "demo-kb",
            "chunks": ["alpha", "beta"],
            "raw_documents": [{"id": "doc-1"}],
        }
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-2",
                "seq": 4,
                "type": "action",
                "content": "Tool running: Hot Retrieval",
                "meta": {
                    "tool": {
                        "name": "task_retrieve_hot",
                        "label": "Hot Retrieval",
                        "status": "running",
                    }
                },
            },
            name="task_retrieve_hot",
            tool_input={"query": "hot"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Hot Retrieval",
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-2",
            action_step=action_step,
            name="task_retrieve_hot",
            display_name="Hot Retrieval",
        )

        self.assertEqual(
            artifacts["output"],
            {
                "tool_kind": "hot_knowledge_retrieval",
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )
        self.assertEqual(
            artifacts["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "tool_kind": "hot_knowledge_retrieval",
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )
        self.assertEqual(
            artifacts["observation"],
            "Hot Retrieval: Retrieved 2 hits from knowledge base demo-kb.",
        )

    def test_build_tool_iteration_success_artifacts_reuses_step_meta_preview_without_registry_context(
        self,
    ) -> None:
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
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-4",
                "seq": 6,
                "type": "action",
                "content": "Tool running: Custom Lookup",
                "meta": {
                    "tool": {
                        "name": "custom_lookup",
                        "label": "Custom Lookup",
                        "status": "running",
                    }
                },
            },
            name="custom_lookup",
            tool_input={"query": "secret"},
            output={
                "tool_kind": "custom_lookup",
                "hit_count": 1,
                "secret": "do-not-preview",
            },
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Custom Lookup",
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-4",
            action_step=action_step,
            name="custom_lookup",
        )

        self.assertEqual(
            artifacts["observation"],
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )
        self.assertEqual(
            artifacts["output"],
            {
                "tool_kind": "custom_lookup",
                "hit_count": 1,
                "secret": "do-not-preview",
            },
        )

    def test_build_tool_iteration_success_artifacts_accepts_tuple_effective_result_output_keys_from_step_meta(
        self,
    ) -> None:
        action_step = {
            "id": "step-5",
            "seq": 7,
            "type": "action",
            "content": "Tool done: Custom Lookup",
            "meta": {
                "tool": {
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "status": "done",
                    "effective_result_output_keys": (
                        "tool_kind",
                        "hit_count",
                    ),
                    "output": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                        "secret": "do-not-preview",
                    },
                }
            },
        }

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-5",
            action_step=action_step,
            name="custom_lookup",
        )

        self.assertEqual(
            artifacts["observation"],
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )
        self.assertEqual(
            artifacts["output"],
            {
                "tool_kind": "custom_lookup",
                "hit_count": 1,
                "secret": "do-not-preview",
            },
        )

    def test_build_tool_iteration_success_artifacts_reuses_step_meta_preview_as_output_without_raw_output(
        self,
    ) -> None:
        action_step = {
            "id": "step-6",
            "seq": 8,
            "type": "action",
            "content": "Tool done: Custom Lookup",
            "meta": {
                "tool": {
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "status": "done",
                    "output_preview": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                    },
                }
            },
        }

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-6",
            action_step=action_step,
            name="custom_lookup",
        )

        self.assertEqual(
            artifacts["observation"],
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )
        self.assertEqual(
            artifacts["output"],
            {
                "tool_kind": "custom_lookup",
                "hit_count": 1,
            },
        )
