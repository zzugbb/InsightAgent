from __future__ import annotations

from .context import *


class RegistryRuntimeGovernanceMixin:
    def test_build_tool_plan_summary_returns_none_when_only_planner_is_present(self) -> None:
        plan = build_tool_plan("普通问答，不包含显式工具标记")

        self.assertEqual(
            build_tool_plan_summary(plan),
            "Planned tools: none",
        )

    def test_build_tool_plan_summary_excludes_extra_primary_planner_and_keeps_execution_tools(
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

        plan = build_tool_plan(
            "请帮我计算 [calc:1+2]",
            registry_provider=registry_provider,
        )

        self.assertEqual(
            build_tool_plan_summary(
                plan,
                registry_provider=registry_provider,
            ),
            "Planned tools: Fast Calculator",
        )

    def test_build_usage_payload_supports_overall_and_planning_fields(self) -> None:
        planning_usage = chat_execution_module._build_usage_payload(  # type: ignore[attr-defined]
            prompt_text="planner prompt",
            completion_text="Planned tools: Task Planner, Knowledge Retrieval",
            provider_usage=ProviderUsage(
                prompt_tokens=10,
                completion_tokens=6,
                total_tokens=16,
            ),
        )
        final_usage = chat_execution_module._build_usage_payload(  # type: ignore[attr-defined]
            prompt_text="final prompt",
            completion_text="final answer",
            provider_usage=ProviderUsage(
                prompt_tokens=20,
                completion_tokens=8,
                total_tokens=28,
            ),
        )

        merged = chat_execution_module._merge_usage_payloads(  # type: ignore[attr-defined]
            final_usage=final_usage,
            planning_usage=planning_usage,
        )

        self.assertEqual(merged["prompt_tokens"], 20)
        self.assertEqual(merged["completion_tokens"], 8)
        self.assertEqual(merged["planning_prompt_tokens"], 10)
        self.assertEqual(merged["planning_completion_tokens"], 6)
        self.assertEqual(merged["overall_prompt_tokens"], 30)
        self.assertEqual(merged["overall_completion_tokens"], 14)
        self.assertEqual(merged["overall_total_tokens"], 44)
        self.assertEqual(merged["planning_usage_source"], "provider")

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

    def test_run_tool_task_plan_normalizes_productized_planned_tool_names(
        self,
    ) -> None:
        output = run_tool(
            name="task_plan",
            tool_input={
                "planned_tool_names": ["calc_eval [calculator]"],
                "planned_tool_labels": ["Calculator [calculator]"],
                "prompt_preview": "planned from historical payload",
            },
            prompt="请规划计算步骤",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Evaluate calculation -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Evaluate calculation",
                    "Synthesize final answer",
                ],
                "prompt_preview": "planned from historical payload",
                "echo": True,
            },
        )

    def test_run_tool_supports_task_plan_alias(self) -> None:
        output = run_tool(
            name="task_plan",
            tool_input={"prompt_preview": "请帮我规划"},
            prompt="请帮我检索知识库并计算 [calc:1+2*3]",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Retrieve supporting context -> Evaluate calculation -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Retrieve supporting context",
                    "Evaluate calculation",
                    "Synthesize final answer",
                ],
                "prompt_preview": "请帮我规划",
                "echo": True,
            },
        )

    def test_run_tool_supports_task_plan_alias_using_actual_planned_tools(self) -> None:
        output = run_tool(
            name="task_plan",
            tool_input={
                "prompt_preview": "请帮我规划",
                "planned_tool_names": ["calc_eval"],
                "planned_tool_labels": ["calc_eval"],
            },
            prompt="普通问答，不包含显式计算标记",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Evaluate calculation -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Evaluate calculation",
                    "Synthesize final answer",
                ],
                "prompt_preview": "请帮我规划",
                "echo": True,
            },
        )

    def test_run_tool_supports_task_plan_alias_using_tuple_planned_tools(self) -> None:
        output = run_tool(
            name="task_plan",
            tool_input={
                "prompt_preview": "请帮我规划",
                "planned_tool_names": ("calc_eval",),
                "planned_tool_labels": ("calc_eval",),
            },
            prompt="普通问答，不包含显式计算标记",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Evaluate calculation -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Evaluate calculation",
                    "Synthesize final answer",
                ],
                "prompt_preview": "请帮我规划",
                "echo": True,
            },
        )

    def test_run_tool_supports_task_plan_alias_using_sequence_wrappers(self) -> None:
        output = run_tool(
            name="task_plan",
            tool_input={
                "prompt_preview": UserString("请帮我规划"),
                "planned_tool_names": UserList(
                    [UserString("calc_eval"), UserString("task_retrieve")]
                ),
                "planned_tool_labels": UserList(
                    [UserString("Calculator"), UserString("Knowledge Retrieval")]
                ),
                "planned_tool_kinds": UserList(
                    [UserString("local_calculator"), UserString("knowledge_retrieval")]
                ),
            },
            prompt="普通问答，不包含显式工具标记",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Evaluate calculation -> Retrieve supporting context -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Evaluate calculation",
                    "Retrieve supporting context",
                    "Synthesize final answer",
                ],
                "prompt_preview": "请帮我规划",
                "echo": True,
            },
        )

    def test_run_tool_task_plan_uses_registry_semantics_for_extra_retrieval_tool(self) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "task_retrieve_hot": {
                            "template": "task_retrieve",
                            "label": "Hot Retrieval",
                        }
                    }
                ),
                tool_registry_overrides_json=None,
            )
        )

        output = run_tool(
            name="task_plan",
            tool_input={
                "prompt_preview": "请帮我规划",
                "planned_tool_names": ["task_retrieve_hot"],
            },
            prompt="普通问答，不包含显式检索标记",
            user_id="user-1",
            attempt=0,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Retrieve supporting context -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Retrieve supporting context",
                    "Synthesize final answer",
                ],
                "prompt_preview": "请帮我规划",
                "echo": True,
            },
        )

    def test_run_tool_task_plan_uses_semantic_family_for_runtime_override_real_retrieval_tool(
        self,
    ) -> None:
        registry_provider = StaticToolRegistryProvider(
            {
                "task_plan": get_default_tool_registry()["task_plan"],
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="Provider Search",
                    retryable_by_default=False,
                    default_timeout_ms=21_000,
                    requires_user_context=True,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_kind": "provider_retrieval",
                        "documents_total": 2,
                    },
                    runtime_semantic_kind="provider_search",
                ),
            }
        )

        planned = build_tool_plan(
            "请先检索 revenue trend",
            provider=SimpleNamespace(
                provider="openai",
                generate=lambda prompt: SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "provider_search",
                                    "input": {"query": "revenue trend"},
                                }
                            ]
                        },
                        ensure_ascii=False,
                    )
                ),
            ),
            registry_provider=registry_provider,
        )

        output = run_tool(
            name="task_plan",
            tool_input=planned[0]["input"],
            prompt="普通问答，不包含显式检索标记",
            user_id="user-1",
            attempt=0,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Retrieve supporting context -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Retrieve supporting context",
                    "Synthesize final answer",
                ],
                "prompt_preview": "请先检索 revenue trend",
                "echo": True,
            },
        )

    def test_run_tool_task_plan_uses_registry_semantics_for_extra_calculator_tool(self) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                tool_registry_overrides_json=None,
            )
        )

        output = run_tool(
            name="task_plan",
            tool_input={
                "prompt_preview": "请帮我规划",
                "planned_tool_names": ["calc_eval_fast"],
            },
            prompt="普通问答，不包含显式计算标记",
            user_id="user-1",
            attempt=0,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Evaluate calculation -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Evaluate calculation",
                    "Synthesize final answer",
                ],
                "prompt_preview": "请帮我规划",
                "echo": True,
            },
        )

    def test_run_tool_task_plan_infers_label_only_real_retrieval_tool_semantics(
        self,
    ) -> None:
        registry_provider = StaticToolRegistryProvider(
            {
                "task_plan": get_default_tool_registry()["task_plan"],
                "hosted_search_gateway": ToolRegistration(
                    name="hosted_search_gateway",
                    kind=None,
                    label="Hosted Search",
                    retryable_by_default=False,
                    default_timeout_ms=21_000,
                    requires_user_context=True,
                    supports_result_preview=True,
                    execution_kind="http_json",
                    runner=lambda *, tool_input, prompt, user_id: {
                        "documents_total": 2,
                    },
                ),
            }
        )

        output = run_tool(
            name="task_plan",
            tool_input={
                "prompt_preview": "请帮我规划",
                "planned_tool_names": ["hosted_search_gateway"],
            },
            prompt="普通问答，不包含显式检索标记",
            user_id="user-1",
            attempt=0,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Retrieve supporting context -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Retrieve supporting context",
                    "Synthesize final answer",
                ],
                "prompt_preview": "请帮我规划",
                "echo": True,
            },
        )

    def test_run_tool_task_plan_infers_label_only_real_calculator_tool_semantics(
        self,
    ) -> None:
        registry_provider = StaticToolRegistryProvider(
            {
                "task_plan": get_default_tool_registry()["task_plan"],
                "hosted_math_gateway": ToolRegistration(
                    name="hosted_math_gateway",
                    kind=None,
                    label="Hosted Math",
                    retryable_by_default=False,
                    default_timeout_ms=21_000,
                    requires_user_context=True,
                    supports_result_preview=True,
                    execution_kind="http_json",
                    runner=lambda *, tool_input, prompt, user_id: {
                        "result": 3.0,
                    },
                ),
            }
        )

        output = run_tool(
            name="task_plan",
            tool_input={
                "prompt_preview": "请帮我规划",
                "planned_tool_names": ["hosted_math_gateway"],
            },
            prompt="普通问答，不包含显式计算标记",
            user_id="user-1",
            attempt=0,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Evaluate calculation -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Evaluate calculation",
                    "Synthesize final answer",
                ],
                "prompt_preview": "请帮我规划",
                "echo": True,
            },
        )

    def test_run_tool_task_plan_filters_planner_tools_from_planned_tool_names(self) -> None:
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

        output = run_tool(
            name="task_plan",
            tool_input={
                "prompt_preview": "请帮我规划",
                "planned_tool_names": ["mock_plan_brief", "calc_eval_fast"],
            },
            prompt="普通问答，不包含显式计算标记",
            user_id="user-1",
            attempt=0,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            output,
            {
                "plan": "Analyze request -> Evaluate calculation -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Evaluate calculation",
                    "Synthesize final answer",
                ],
                "prompt_preview": "请帮我规划",
                "echo": True,
            },
        )

    def test_run_tool_supports_task_retrieve_alias(self) -> None:
        original_query = tool_runtime_module.query_knowledge_base

        def fake_query_knowledge_base(
            *,
            user_id: str,
            knowledge_base_id: str,
            query_text: str,
            top_k: int,
        ) -> dict[str, object]:
            self.assertEqual(user_id, "user-1")
            self.assertEqual(knowledge_base_id, "demo-kb")
            self.assertEqual(query_text, "检索 demo")
            self.assertEqual(top_k, 2)
            return {
                "hits": [{"content": "alpha"}],
                "hit_count": 1,
                "knowledge_base_id": knowledge_base_id,
                "collection": "kb_demo-kb",
            }

        tool_runtime_module.query_knowledge_base = fake_query_knowledge_base
        try:
            output = run_tool(
                name="task_retrieve",
                tool_input={
                    "query": "检索 demo",
                    "knowledge_base_id": "demo-kb",
                    "top_k": 2,
                },
                prompt="检索 demo",
                user_id="user-1",
                attempt=0,
            )
        finally:
            tool_runtime_module.query_knowledge_base = original_query

        self.assertEqual(
            output,
            {
                "chunks": ["alpha"],
                "hits": [{"content": "alpha"}],
                "hit_count": 1,
                "knowledge_base_id": "demo-kb",
                "collection": "kb_demo-kb",
            },
        )

    def test_run_tool_extra_calc_alias_rewrites_template_tool_kind_to_registration_kind(
        self,
    ) -> None:
        provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                            "kind": "fast_calculator",
                        }
                    }
                ),
            )
        )

        output = run_tool(
            name="calc_eval_fast",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )

        self.assertEqual(
            output,
            {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "fast_calculator",
            },
        )

    def test_run_tool_extra_retrieve_alias_adds_registration_kind_to_output(self) -> None:
        original_query = tool_runtime_module.query_knowledge_base

        def fake_query_knowledge_base(
            *,
            user_id: str,
            knowledge_base_id: str,
            query_text: str,
            top_k: int,
        ) -> dict[str, object]:
            self.assertEqual(user_id, "user-1")
            self.assertEqual(knowledge_base_id, "demo-kb")
            self.assertEqual(query_text, "hot retrieval")
            self.assertEqual(top_k, 2)
            return {
                "hits": [{"content": "alpha"}],
                "hit_count": 1,
                "knowledge_base_id": knowledge_base_id,
                "collection": "kb_demo-kb",
            }

        tool_runtime_module.query_knowledge_base = fake_query_knowledge_base
        try:
            provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_extra_tools_json=json.dumps(
                        {
                            "task_retrieve_hot": {
                                "template": "task_retrieve",
                                "label": "Hot Retrieval",
                                "kind": "hot_knowledge_retrieval",
                            }
                        }
                    ),
                )
            )
            output = run_tool(
                name="task_retrieve_hot",
                tool_input={
                    "query": "hot retrieval",
                    "knowledge_base_id": "demo-kb",
                    "top_k": 2,
                },
                prompt="检索 demo",
                user_id="user-1",
                attempt=0,
                registry_provider=provider,
            )
        finally:
            tool_runtime_module.query_knowledge_base = original_query

        self.assertEqual(
            output,
            {
                "chunks": ["alpha"],
                "hits": [{"content": "alpha"}],
                "hit_count": 1,
                "knowledge_base_id": "demo-kb",
                "collection": "kb_demo-kb",
                "tool_kind": "hot_knowledge_retrieval",
            },
        )

    def test_run_tool_accepts_custom_registry_override(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "custom-ok",
                "tool_kind": "custom_calc",
            }

        registry = {
            "calc_eval": ToolRegistration(
                name="calc_eval",
                kind="custom_calc",
                label="Custom Calculator",
                retryable_by_default=False,
                default_timeout_ms=9_000,
                requires_user_context=False,
                supports_result_preview=True,
                runner=custom_runner,
            )
        }

        output = run_tool(
            name="calc_eval",
            tool_input={"expression": "ignored"},
            prompt="custom-calc",
            user_id="user-1",
            attempt=0,
            registry=registry,
        )

        self.assertEqual(
            output,
            {
                "result": "custom-ok",
                "tool_kind": "custom_calc",
            },
        )
        self.assertEqual(
            runner_calls,
            [({"expression": "ignored"}, "custom-calc", "")],
        )

    def test_run_tool_accepts_custom_registry_loader_override(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "loader-ok",
                "tool_kind": "loader_calc",
            }

        def custom_loader() -> dict[str, ToolRegistration]:
            return {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }

        output = run_tool(
            name="calc_eval",
            tool_input={"expression": "ignored"},
            prompt="loader-calc",
            user_id="user-1",
            attempt=0,
            registry_loader=custom_loader,
        )

        self.assertEqual(
            output,
            {
                "result": "loader-ok",
                "tool_kind": "loader_calc",
            },
        )
        self.assertEqual(
            runner_calls,
            [({"expression": "ignored"}, "loader-calc", "")],
        )

    def test_run_tool_accepts_custom_registry_provider_override(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "provider-ok",
                "tool_kind": "provider_calc",
            }

        provider = StaticToolRegistryProvider(
            registry={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="provider_calc",
                    label="Provider Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=13_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }
        )

        output = run_tool(
            name="calc_eval",
            tool_input={"expression": "ignored"},
            prompt="provider-calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )

        self.assertEqual(
            output,
            {
                "result": "provider-ok",
                "tool_kind": "provider_calc",
            },
        )
        self.assertEqual(
            runner_calls,
            [({"expression": "ignored"}, "provider-calc", "")],
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

    def test_execute_tool_spec_accepts_custom_registry_override(self) -> None:
        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            return {
                "echo_input": tool_input,
                "tool_kind": "custom_calc",
                "prompt": prompt,
                "user_id": user_id,
            }

        registry = {
            "calc_eval": ToolRegistration(
                name="calc_eval",
                kind="custom_calc",
                label="Custom Calculator",
                retryable_by_default=False,
                default_timeout_ms=9_000,
                requires_user_context=False,
                supports_result_preview=True,
                runner=custom_runner,
            )
        }

        output = execute_tool_spec(
            tool_spec={"name": "calc_eval", "input": {"expression": "9*9"}},
            prompt="custom-calc",
            user_id="user-1",
            attempt=0,
            registry=registry,
        )

        self.assertEqual(
            output,
            {
                "echo_input": {"expression": "9*9"},
                "tool_kind": "custom_calc",
                "prompt": "custom-calc",
                "user_id": "",
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
        self.assertIn("unknown tool", str(ctx.exception).lower())

    def test_registered_tool_names_cover_current_mock_tools(self) -> None:
        self.assertEqual(
            get_registered_tool_names(),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_get_default_tool_registry_returns_copy_of_current_entries(self) -> None:
        registry = get_default_tool_registry()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_plan", "task_retrieve"),
        )
        registry.pop("calc_eval")
        self.assertEqual(
            get_registered_tool_names(),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_get_default_tool_registry_provider_returns_isolated_snapshot(self) -> None:
        provider = get_default_tool_registry_provider()
        registry = provider.load_tool_registry()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_plan", "task_retrieve"),
        )
        registry.pop("calc_eval")
        self.assertEqual(
            tuple(sorted(provider.load_tool_registry())),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_get_default_tool_registry_provider_returns_default_provider_impl(self) -> None:
        provider = get_default_tool_registry_provider()

        self.assertIsInstance(provider, DefaultToolRegistryProvider)

    def test_build_tool_registry_provider_without_args_returns_default_provider(self) -> None:
        provider = build_tool_registry_provider()

        self.assertIsInstance(provider, DefaultToolRegistryProvider)
        self.assertEqual(
            tuple(sorted(provider.load_tool_registry())),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_default_tool_registry_provider_loads_fresh_snapshot_per_call(self) -> None:
        provider = DefaultToolRegistryProvider()
        first = provider.load_tool_registry()
        second = provider.load_tool_registry()

        self.assertEqual(
            tuple(sorted(first)),
            ("calc_eval", "task_plan", "task_retrieve"),
        )
        self.assertEqual(
            tuple(sorted(second)),
            ("calc_eval", "task_plan", "task_retrieve"),
        )
        self.assertIsNot(first, second)

    def test_build_tool_registry_provider_with_loader_and_overrides_returns_configured_provider(self) -> None:
        def custom_loader() -> dict[str, ToolRegistration]:
            return {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            }

        provider = build_tool_registry_provider(
            loader=custom_loader,
            overrides={
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
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            },
        )

        self.assertIsInstance(provider, ConfiguredToolRegistryProvider)
        self.assertEqual(
            tuple(sorted(provider.load_tool_registry())),
            ("calc_eval", "custom_lookup"),
        )
        self.assertEqual(
            provider.load_tool_registry()["calc_eval"].kind,
            "loader_calc",
        )

    def test_resolve_tool_registry_provider_wraps_explicit_registry(self) -> None:
        provider = resolve_tool_registry_provider(
            registry={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="wrapped_calc",
                    label="Wrapped Calculator",
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
            }
        )

        self.assertIsInstance(provider, StaticToolRegistryProvider)
        self.assertEqual(
            provider.load_tool_registry()["calc_eval"].kind,
            "wrapped_calc",
        )

    def test_build_tool_registry_provider_prefers_explicit_provider_over_loader(self) -> None:
        provider = build_tool_registry_provider(
            provider=StaticToolRegistryProvider(
                registry={
                    "calc_eval": ToolRegistration(
                        name="calc_eval",
                        kind="provider_calc",
                        label="Provider Calculator",
                        retryable_by_default=False,
                        default_timeout_ms=13_000,
                        requires_user_context=False,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "tool_input": tool_input,
                            "prompt": prompt,
                            "user_id": user_id,
                        },
                    )
                }
            ),
            loader=lambda: {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            },
        )

        self.assertIsInstance(provider, StaticToolRegistryProvider)
        self.assertEqual(
            provider.load_tool_registry()["calc_eval"].kind,
            "provider_calc",
        )

    def test_resolve_tool_registry_provider_prefers_explicit_registry_over_provider_and_loader(self) -> None:
        provider = resolve_tool_registry_provider(
            registry={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="registry_calc",
                    label="Registry Calculator",
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
            },
            registry_provider=StaticToolRegistryProvider(
                registry={
                    "calc_eval": ToolRegistration(
                        name="calc_eval",
                        kind="provider_calc",
                        label="Provider Calculator",
                        retryable_by_default=False,
                        default_timeout_ms=13_000,
                        requires_user_context=False,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "tool_input": tool_input,
                            "prompt": prompt,
                            "user_id": user_id,
                        },
                    )
                }
            ),
            registry_loader=lambda: {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            },
        )

        self.assertIsInstance(provider, StaticToolRegistryProvider)
        self.assertEqual(
            provider.load_tool_registry()["calc_eval"].kind,
            "registry_calc",
        )

    def test_get_configured_tool_registry_provider_returns_default_provider_stack(self) -> None:
        provider = get_configured_tool_registry_provider()

        self.assertIsInstance(provider, DefaultToolRegistryProvider)
        self.assertEqual(
            tuple(sorted(provider.load_tool_registry())),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_build_tool_registry_overrides_from_settings_updates_known_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "label": "Configured Calculator",
                        "default_timeout_ms": 9_999,
                        "retryable_by_default": False,
                    }
                }
            )
        )

        overrides = build_tool_registry_overrides_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(overrides)), ("calc_eval",))
        self.assertEqual(overrides["calc_eval"].label, "Configured Calculator")
        self.assertEqual(overrides["calc_eval"].default_timeout_ms, 9_999)
        self.assertFalse(overrides["calc_eval"].retryable_by_default)
        self.assertEqual(overrides["calc_eval"].kind, "local_calculator")

    def test_build_registry_overrides_from_specs_accepts_mapping_wrappers(self) -> None:
        overrides, disabled_tool_names = (
            tool_runtime_module._build_registry_overrides_from_specs(  # type: ignore[attr-defined]
                override_specs=UserDict(
                    {
                        UserString("calc_eval"): UserDict(
                            {
                                UserString("label"): UserString(
                                    "Provider Calculator"
                                ),
                                UserString("kind"): UserString("provider_calc"),
                                UserString("execution"): UserDict(
                                    {
                                        UserString("kind"): UserString("http_json"),
                                        UserString("url"): UserString(
                                            "https://provider.example/calc"
                                        ),
                                        UserString("method"): UserString("POST"),
                                        UserString("json_body"): UserDict(
                                            {
                                                UserString("expression"): UserString(
                                                    "$expression"
                                                )
                                            }
                                        ),
                                        UserString("result_fields"): UserDict(
                                            {
                                                UserString("result"): UserString(
                                                    "$.data.value"
                                                )
                                            }
                                        ),
                                    }
                                ),
                            }
                        )
                    }
                ),
                base_registry=get_default_tool_registry(),
                disabled_tool_names=set(),
            )
        )

        self.assertEqual(disabled_tool_names, set())
        self.assertEqual(tuple(sorted(overrides)), ("calc_eval",))
        override = overrides["calc_eval"]
        self.assertEqual(override.label, "Provider Calculator")
        self.assertEqual(override.kind, "provider_calc")
        self.assertEqual(override.execution_kind, "http_json")
        self.assertEqual(
            override.execution_summary,
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/calc",
                "json_body_field_count": 1,
                "result_field_names": ["result"],
            },
        )

    def test_build_tool_registry_provider_adapter_accepts_mapping_wrappers(self) -> None:
        provider = tool_runtime_module.build_tool_registry_provider_adapter(
            spec=UserDict(
                {
                    UserString("profile"): UserString("planning_only"),
                    UserString("disabled_tool_names"): UserList(
                        [UserString("task_plan")]
                    ),
                    UserString("extra_tools"): UserDict(
                        {
                            UserString("calc_eval_fast"): UserDict(
                                {
                                    UserString("template"): UserString("calc_eval"),
                                    UserString("label"): UserString("Fast Calculator"),
                                    UserString("result_preview_keys"): UserList(
                                        [
                                            UserString("expression"),
                                            UserString("result"),
                                        ]
                                    ),
                                }
                            )
                        }
                    ),
                }
            )
        )

        self.assertIsNotNone(provider)
        assert provider is not None
        registry = provider.load_tool_registry()
        self.assertEqual(tuple(sorted(registry)), ("calc_eval_fast",))
        self.assertEqual(registry["calc_eval_fast"].label, "Fast Calculator")
        self.assertEqual(
            registry["calc_eval_fast"].result_preview_keys,
            ("expression", "result"),
        )

    def test_build_tool_registry_settings_config_supports_disabled_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "label": "Configured Calculator",
                        "enabled": False,
                    },
                    "mock_retrieve": {
                        "enabled": False,
                    },
                }
            )
        )

        config = build_tool_registry_settings_config(settings=settings)

        self.assertEqual(tuple(sorted(config.overrides)), ("calc_eval",))
        self.assertEqual(
            config.disabled_tool_names,
            ("calc_eval", "task_retrieve"),
        )
        self.assertEqual(
            get_disabled_tool_names_from_settings(settings=settings),
            ("calc_eval", "task_retrieve"),
        )

    def test_build_tool_registry_profile_settings_config_supports_planning_only_profile(self) -> None:
        config = build_tool_registry_profile_settings_config(profile_name="planning_only")

        self.assertEqual(config.overrides, {})
        self.assertEqual(
            config.disabled_tool_names,
            ("calc_eval", "task_retrieve"),
        )

    def test_build_tool_registry_settings_config_allows_reenable_over_profile_disable(self) -> None:
        settings = SimpleNamespace(
            tool_registry_profile="planning_only",
            tool_registry_overrides_json=json.dumps(
                {
                    "mock_retrieve": {
                        "enabled": True,
                        "label": "Profile Reenabled Retrieve",
                    }
                }
            ),
        )

        config = build_tool_registry_settings_config(settings=settings)

        self.assertEqual(
            config.disabled_tool_names,
            ("calc_eval",),
        )
        self.assertEqual(
            config.overrides["task_retrieve"].label,
            "Profile Reenabled Retrieve",
        )

    def test_build_tool_registry_extra_tools_from_settings_clones_template_registration(self) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "template": "calc_eval",
                        "label": "Fast Calculator",
                        "default_timeout_ms": 1_500,
                        "retryable_by_default": False,
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(extra_tools)), ("calc_eval_fast",))
        self.assertEqual(extra_tools["calc_eval_fast"].name, "calc_eval_fast")
        self.assertEqual(extra_tools["calc_eval_fast"].label, "Fast Calculator")
        self.assertEqual(extra_tools["calc_eval_fast"].default_timeout_ms, 1_500)
        self.assertFalse(extra_tools["calc_eval_fast"].retryable_by_default)
        self.assertEqual(extra_tools["calc_eval_fast"].kind, "local_calculator")

    def test_build_tool_registry_extra_tools_from_specs_accepts_mapping_wrappers(
        self,
    ) -> None:
        extra_tools = tool_runtime_module.build_tool_registry_extra_tools_from_specs(
            extra_tool_specs=UserDict(
                {
                    UserString("provider_search"): UserDict(
                        {
                            UserString("template"): UserString("task_retrieve"),
                            UserString("label"): UserString("Provider Search"),
                            UserString("kind"): UserString("provider_retrieval"),
                            UserString("runtime_semantic_kind"): UserString(
                                "provider_search"
                            ),
                            UserString("result_preview_keys"): UserList(
                                [UserString("documents_total")]
                            ),
                            UserString("result_output_keys"): UserList(
                                [
                                    UserString("documents_total"),
                                    UserString("request_id"),
                                ]
                            ),
                            UserString("execution"): UserDict(
                                {
                                    UserString("kind"): UserString("http_json"),
                                    UserString("url"): UserString(
                                        "https://provider.example/search"
                                    ),
                                    UserString("method"): UserString("POST"),
                                    UserString("json_body"): UserDict(
                                        {
                                            UserString("query"): UserString("$query"),
                                        }
                                    ),
                                    UserString("result_fields"): UserDict(
                                        {
                                            UserString("documents_total"): UserString(
                                                "$.meta.total"
                                            ),
                                            UserString("request_id"): UserString(
                                                "$.meta.request_id"
                                            ),
                                        }
                                    ),
                                }
                            ),
                        }
                    )
                }
            )
        )

        self.assertEqual(tuple(sorted(extra_tools)), ("provider_search",))
        provider_search = extra_tools["provider_search"]
        self.assertEqual(provider_search.label, "Provider Search")
        self.assertEqual(provider_search.kind, "provider_retrieval")
        self.assertEqual(provider_search.runtime_semantic_kind, "provider_search")
        self.assertEqual(provider_search.execution_kind, "http_json")
        self.assertEqual(provider_search.result_preview_keys, ("documents_total",))
        self.assertEqual(
            provider_search.result_output_keys,
            ("documents_total", "request_id"),
        )
        self.assertEqual(
            provider_search.execution_summary,
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "json_body_field_count": 1,
                "result_field_names": ["documents_total", "request_id"],
            },
        )

    def test_build_tool_registry_extra_tools_from_settings_sanitizes_inherited_execution_meta(
        self,
    ) -> None:
        original_registration = tool_runtime_module._REGISTERED_TOOLS["task_retrieve"]  # type: ignore[attr-defined]
        inherited_registration = ToolRegistration(
            **{
                **original_registration.__dict__,
                "execution_kind": "http_json",
                "execution_summary": {
                    "method": "GET",
                    "url_path": "/v1/token=hidden/api_key/secret/search",
                    "response_path": "$.data.access_token",
                    "result_field_names": ["documents_total", "access_token"],
                },
                "execution_diagnostics": (
                    "unsupported tool execution kind api_key=hidden",
                    "http_json execution query_params.access_token must be safe",
                ),
            }
        )
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                    }
                }
            )
        )
        try:
            tool_runtime_module._REGISTERED_TOOLS["task_retrieve"] = inherited_registration  # type: ignore[attr-defined]

            extra_tools = build_tool_registry_extra_tools_from_settings(
                settings=settings,
            )
        finally:
            tool_runtime_module._REGISTERED_TOOLS["task_retrieve"] = original_registration  # type: ignore[attr-defined]

        provider_search = extra_tools["provider_search"]
        self.assertEqual(
            provider_search.execution_summary,
            {
                "method": "GET",
                "url_path": "/v1/[redacted]/[redacted]/[redacted]/search",
                "response_path": "$.data.[redacted]",
                "result_field_names": ["documents_total", "[redacted]"],
            },
        )
        self.assertEqual(
            provider_search.execution_diagnostics,
            (
                "unsupported tool execution kind [redacted]",
                "http_json execution [redacted] must be safe",
            ),
        )
        combined = json.dumps(
            {
                "summary": provider_search.execution_summary,
                "diagnostics": provider_search.execution_diagnostics,
            },
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("api_key/secret", combined)
        self.assertNotIn("access_token", combined)

    def test_build_tool_registry_extra_tools_from_settings_diagnoses_invalid_default_timeout(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "template": "calc_eval",
                        "label": "Fast Calculator",
                        "default_timeout_ms": "slow",
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(extra_tools)), ("calc_eval_fast",))
        self.assertEqual(extra_tools["calc_eval_fast"].default_timeout_ms, 3_000)
        self.assertEqual(
            extra_tools["calc_eval_fast"].execution_diagnostics,
            ("tool default_timeout_ms must be a positive number of milliseconds",),
        )

    def test_build_tool_registry_extra_tools_from_settings_diagnoses_non_finite_default_timeout(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "template": "calc_eval",
                        "label": "Fast Calculator",
                        "default_timeout_ms": float("nan"),
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(extra_tools)), ("calc_eval_fast",))
        self.assertEqual(extra_tools["calc_eval_fast"].default_timeout_ms, 3_000)
        self.assertEqual(
            extra_tools["calc_eval_fast"].execution_diagnostics,
            ("tool default_timeout_ms must be a positive number of milliseconds",),
        )

    def test_build_tool_registry_extra_tools_from_settings_accepts_result_preview_keys(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "task_retrieve_hot": {
                        "template": "task_retrieve",
                        "label": "Hot Retrieval",
                        "result_preview_keys": [
                            "tool_kind",
                            "hit_count",
                            "knowledge_base_id",
                            "hit_count",
                            " ",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            extra_tools["task_retrieve_hot"].result_preview_keys,
            ("tool_kind", "hit_count", "knowledge_base_id"),
        )

    def test_build_tool_registry_extra_tools_from_settings_accepts_runtime_semantic_kind(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            extra_tools["provider_search"].runtime_semantic_kind,
            "provider_search",
        )

    def test_build_tool_registry_extra_tools_from_settings_accepts_result_output_keys(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "result_output_keys": [
                            "documents_total",
                            "documents_total",
                            " ",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            extra_tools["provider_search"].result_output_keys,
            ("documents_total",),
        )

    def test_build_tool_registry_extra_tools_from_settings_supports_http_json_execution(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "headers": {"X-Trace-Token": "trace-demo"},
                            "json_body": {
                                "query": "$query",
                                "limit": "$top_k",
                                "knowledge_base_id": "$knowledge_base_id",
                            },
                            "result_fields": {
                                "documents_total": "$.meta.total",
                                "documents": "$.data.documents",
                                "chunks": "$.data.snippets",
                                "request_id": "$.meta.request_id",
                                "knowledge_base_id": "$.meta.knowledge_base_id",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total", "request_id"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)
        urlopen_calls: list[tuple[object, object]] = []

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append((request, timeout))
                or FakeHttpResponse(
                    {
                        "meta": {
                            "total": 2,
                            "request_id": "req-http-1",
                            "knowledge_base_id": "provider-kb",
                        },
                        "data": {
                            "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                            "snippets": ["alpha", "beta"],
                        },
                    }
                )
            )

            output = run_tool(
                name="provider_search",
                tool_input={
                    "query": "revenue trend",
                    "top_k": 2,
                    "knowledge_base_id": "provider-kb",
                },
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(len(urlopen_calls), 1)
        request, timeout = urlopen_calls[0]
        self.assertEqual(timeout, 5.0)
        self.assertEqual(request.full_url, "https://provider.example/search")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.headers["X-trace-token"], "trace-demo")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "revenue trend",
                "limit": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            output,
            {
                "documents_total": 2,
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                "chunks": ["alpha", "beta"],
                "request_id": "req-http-1",
                "knowledge_base_id": "provider-kb",
                "tool_kind": "provider_search",
            },
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_data_count_from_registration_semantics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": [
                        {"documentText": "alpha document text"},
                        {"documentText": "beta document text"},
                    ],
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident timeline"},
                prompt="search incident timeline",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["documents_total"], 2)
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 documents.",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_documents_total_from_response_path_list(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "response_path": "$.data",
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "data": [
                            {"documentText": "alpha document text"},
                            {"documentText": "beta document text"},
                            {"documentText": "gamma document text"},
                        ],
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse()  # type: ignore[attr-defined]

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident timeline"},
                prompt="search incident timeline",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["documents_total"], 3)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 3,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 3 documents.",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_records_count_from_registration_semantics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "records": [
                        {"chunkText": "alpha chunk text"},
                        {"passage": "beta passage"},
                    ],
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "capacity plan"},
                prompt="search capacity plan",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["documents_total"], 2)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 documents.",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_hit_count_from_data_registration_semantics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                        },
                        "result_preview_keys": ["hit_count"],
                        "result_output_keys": ["hit_count"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": [
                        {"documentText": "alpha document text"},
                        {"documentText": "beta document text"},
                    ],
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "capacity plan"},
                prompt="search capacity plan",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 2,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 hits.",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_hit_count_from_response_path_list(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "response_path": "$.data",
                        },
                        "result_preview_keys": ["hit_count"],
                        "result_output_keys": ["hit_count"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "data": [
                            {"snippetText": "alpha snippet"},
                            {"snippetText": "beta snippet"},
                            {"snippetText": "gamma snippet"},
                            {"snippetText": "delta snippet"},
                        ],
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse()  # type: ignore[attr-defined]

            output = run_tool(
                name="provider_search",
                tool_input={"query": "capacity plan"},
                prompt="search capacity plan",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["hit_count"], 4)
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 4,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 4 hits.",
        )

    def test_build_tool_registry_extra_tools_from_settings_projects_chunks_from_response_path_list(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "response_path": "$.data",
                        },
                        "result_preview_keys": ["chunks"],
                        "result_output_keys": ["chunks"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "data": [
                            {"snippetText": "alpha snippet"},
                            {"source": {"contentText": "beta content"}},
                            "gamma string",
                            {"title": "ignored title only"},
                        ],
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse()  # type: ignore[attr-defined]

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident timeline"},
                prompt="search incident timeline",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        expected_chunks = ["alpha snippet", "beta content", "gamma string"]
        self.assertEqual(output["chunks"], expected_chunks)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "chunks": expected_chunks,
            },
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_total_count_result_field_from_registration_semantics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "totalCount": "$.meta.totalCount",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {"meta": {"totalCount": "3"}}
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident timeline"},
                prompt="search incident timeline",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["documents_total"], 3)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 3,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 3 documents.",
        )

    def test_build_tool_registry_extra_tools_from_settings_projects_chunks_from_result_fields_list(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "chunks": "$.data.items",
                            },
                        },
                        "result_preview_keys": ["chunks"],
                        "result_output_keys": ["chunks"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": {
                        "items": [
                            {"snippetText": "alpha snippet"},
                            {"attributes": {"contentText": "beta content"}},
                            "gamma string",
                            {"title": "ignored title only"},
                        ],
                    }
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident timeline"},
                prompt="search incident timeline",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        expected_chunks = ["alpha snippet", "beta content", "gamma string"]
        self.assertEqual(output["chunks"], expected_chunks)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 3 snippets.",
        )

    def test_build_tool_registry_extra_tools_from_settings_projects_graphql_connection_documents(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "documents": "$.data.search",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total", "chunks"],
                        "result_output_keys": [
                            "documents_total",
                            "chunks",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": {
                        "search": {
                            "totalCount": "4",
                            "edges": [
                                {"node": {"snippetText": "alpha graph snippet"}},
                                {
                                    "node": {
                                        "attributes": {
                                            "contentText": "beta graph content",
                                        }
                                    }
                                },
                                {"node": "gamma graph string"},
                                {"node": {"title": "ignored title only"}},
                            ],
                        }
                    },
                    "meta": {
                        "request_id": "req-graphql-connection-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident graph"},
                prompt="search incident graph",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        expected_chunks = [
            "alpha graph snippet",
            "beta graph content",
            "gamma graph string",
        ]
        self.assertEqual(output["documents_total"], 4)
        self.assertEqual(output["chunks"], expected_chunks)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 4,
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 4,
                "chunks": expected_chunks,
                "request_id": "req-graphql-connection-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 4 documents (request id req-graphql-connection-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_projects_elasticsearch_hits_documents(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "documents": "$.hits",
                                "request_id": "$._request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total", "chunks"],
                        "result_output_keys": [
                            "documents_total",
                            "chunks",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "hits": {
                        "total": {"value": "12"},
                        "hits": [
                            {
                                "_source": {
                                    "snippetText": "alpha source snippet",
                                },
                            },
                            {
                                "fields": {
                                    "contentText": "beta fields content",
                                },
                            },
                            {"_source": {"title": "ignored title only"}},
                        ],
                    },
                    "_request_id": "req-elastic-hits-1",
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident hits"},
                prompt="search incident hits",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        expected_chunks = [
            "alpha source snippet",
            "beta fields content",
        ]
        self.assertEqual(output["documents_total"], 12)
        self.assertEqual(output["chunks"], expected_chunks)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 12,
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 12,
                "chunks": expected_chunks,
                "request_id": "req-elastic-hits-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 12 documents (request id req-elastic-hits-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_projects_azure_odata_documents(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/index/docs/search",
                            "method": "POST",
                            "json_body": {
                                "search": "$query",
                            },
                            "result_fields": {
                                "documents": "$",
                                "request_id": "$.request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total", "chunks"],
                        "result_output_keys": [
                            "documents_total",
                            "chunks",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "@odata.count": "27",
                    "value": [
                        {
                            "content": "alpha azure content",
                            "@search.score": 8.5,
                        },
                        {
                            "document": {
                                "snippetText": "beta azure snippet",
                            },
                        },
                        {"title": "ignored title only"},
                    ],
                    "request_id": "req-azure-odata-1",
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident odata"},
                prompt="search incident odata",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        expected_chunks = [
            "alpha azure content",
            "beta azure snippet",
        ]
        self.assertEqual(output["documents_total"], 27)
        self.assertEqual(output["chunks"], expected_chunks)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 27,
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 27,
                "chunks": expected_chunks,
                "request_id": "req-azure-odata-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 27 documents (request id req-azure-odata-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_projects_organic_results_documents(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "GET",
                            "query_params": {
                                "q": "$query",
                            },
                        },
                        "result_preview_keys": ["documents_total", "chunks"],
                        "result_output_keys": [
                            "documents_total",
                            "chunks",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "search_metadata": {
                        "id": "req-organic-results-1",
                    },
                    "search_information": {
                        "total_results": "99",
                    },
                    "organic_results": [
                        {"snippet": "alpha organic snippet"},
                        {
                            "rich_snippet": {
                                "top": {
                                    "detected_extensions": {
                                        "description": "beta rich organic content",
                                    },
                                },
                            },
                        },
                        {"title": "ignored title only"},
                    ],
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident organic"},
                prompt="search incident organic",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        expected_chunks = [
            "alpha organic snippet",
            "beta rich organic content",
        ]
        self.assertEqual(output["documents_total"], 99)
        self.assertEqual(output["chunks"], expected_chunks)
        self.assertEqual(output["request_id"], "req-organic-results-1")
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 99,
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 99,
                "chunks": expected_chunks,
                "request_id": "req-organic-results-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 99 documents (request id req-organic-results-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_projects_qdrant_points_documents(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/collections/demo/points/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "documents": "$.result",
                                "request_id": "$.status.request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total", "chunks"],
                        "result_output_keys": [
                            "documents_total",
                            "chunks",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "result": {
                        "count": "6",
                        "points": [
                            {
                                "payload": {
                                    "text": "alpha qdrant payload",
                                },
                            },
                            {
                                "payload": {
                                    "metadata": {
                                        "summary": "beta qdrant summary",
                                    },
                                },
                            },
                            {"id": "point-title-only"},
                        ],
                    },
                    "status": {
                        "request_id": "req-qdrant-points-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident points"},
                prompt="search incident points",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        expected_chunks = [
            "alpha qdrant payload",
            "beta qdrant summary",
        ]
        self.assertEqual(output["documents_total"], 6)
        self.assertEqual(output["chunks"], expected_chunks)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 6,
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 6,
                "chunks": expected_chunks,
                "request_id": "req-qdrant-points-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 6 documents (request id req-qdrant-points-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_projects_milvus_entity_documents(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/vectors/search",
                            "method": "GET",
                            "query_params": {
                                "q": "$query",
                            },
                        },
                        "result_preview_keys": ["documents_total", "chunks"],
                        "result_output_keys": [
                            "documents_total",
                            "chunks",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "count": "5",
                    "requestId": "req-milvus-entity-1",
                    "data": [
                        {
                            "entity": {
                                "text": "alpha milvus entity",
                            },
                        },
                        {
                            "entity": {
                                "metadata": {
                                    "content": "beta milvus content",
                                },
                            },
                        },
                        {"id": "entity-title-only"},
                    ],
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident entity"},
                prompt="search incident entity",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        expected_chunks = [
            "alpha milvus entity",
            "beta milvus content",
        ]
        self.assertEqual(output["documents_total"], 5)
        self.assertEqual(output["chunks"], expected_chunks)
        self.assertEqual(output["request_id"], "req-milvus-entity-1")
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 5,
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 5,
                "chunks": expected_chunks,
                "request_id": "req-milvus-entity-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 5 documents (request id req-milvus-entity-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_projects_source_nodes_documents(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/rag/query",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                        },
                        "result_preview_keys": ["documents_total", "chunks"],
                        "result_output_keys": [
                            "documents_total",
                            "chunks",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "source_nodes": [
                        {"node": {"text": "alpha source node"}},
                        {
                            "node": {
                                "metadata": {
                                    "summary": "beta source node summary",
                                },
                            },
                        },
                        {"node": {"title": "ignored title only"}},
                    ]
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident source nodes"},
                prompt="search incident source nodes",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        expected_chunks = [
            "alpha source node",
            "beta source node summary",
        ]
        self.assertEqual(output["documents_total"], 3)
        self.assertEqual(output["chunks"], expected_chunks)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 3,
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 3,
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 3 documents.",
        )

    def test_build_tool_registry_extra_tools_from_settings_projects_chroma_document_matrix(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/chroma/query",
                            "method": "POST",
                            "json_body": {
                                "query_texts": ["$query"],
                                "n_results": 3,
                            },
                        },
                        "result_preview_keys": ["documents_total", "chunks"],
                        "result_output_keys": [
                            "documents_total",
                            "chunks",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "ids": [["doc-1", "doc-2", "doc-3"]],
                    "documents": [
                        [
                            "alpha chroma document",
                            "beta chroma document",
                            "gamma chroma document",
                        ]
                    ],
                    "metadatas": [[{"source": "kb"}, {"source": "kb"}, {}]],
                    "distances": [[0.12, 0.2, 0.33]],
                    "traceId": "req-chroma-matrix-1",
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident chroma"},
                prompt="search incident chroma",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        expected_chunks = [
            "alpha chroma document",
            "beta chroma document",
            "gamma chroma document",
        ]
        self.assertEqual(output["documents_total"], 3)
        self.assertEqual(output["chunks"], expected_chunks)
        self.assertEqual(output["request_id"], "req-chroma-matrix-1")
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 3,
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 3,
                "chunks": expected_chunks,
                "request_id": "req-chroma-matrix-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 3 documents (request id req-chroma-matrix-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_projects_weaviate_graphql_get_documents(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/v1/graphql",
                            "method": "POST",
                            "json_body": {
                                "query": "{ Get { IncidentDoc { text } } }",
                                "variables": {
                                    "query": "$query",
                                },
                            },
                        },
                        "result_preview_keys": ["documents_total", "chunks"],
                        "result_output_keys": [
                            "documents_total",
                            "chunks",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": {
                        "Get": {
                            "IncidentDoc": [
                                {"text": "alpha weaviate doc"},
                                {
                                    "metadata": {
                                        "summary": "beta weaviate summary",
                                    },
                                },
                                {"title": "ignored title only"},
                            ]
                        }
                    },
                    "extensions": {
                        "requestId": "req-weaviate-graphql-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "incident graphql"},
                prompt="search incident graphql",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        expected_chunks = [
            "alpha weaviate doc",
            "beta weaviate summary",
        ]
        self.assertEqual(output["documents_total"], 3)
        self.assertEqual(output["chunks"], expected_chunks)
        self.assertEqual(output["request_id"], "req-weaviate-graphql-1")
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 3,
                "chunks": expected_chunks,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 3,
                "chunks": expected_chunks,
                "request_id": "req-weaviate-graphql-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 3 documents (request id req-weaviate-graphql-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_hit_count_result_field_from_registration_semantics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "hitCount": "$.meta.hitCount",
                            },
                        },
                        "result_preview_keys": ["hit_count"],
                        "result_output_keys": ["hit_count"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {"meta": {"hitCount": "4"}}
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "capacity plan"},
                prompt="search capacity plan",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["hit_count"], 4)
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 4,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 4 hits.",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_hit_count_from_items_result_field_registration_semantics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "items": "$.data.items",
                            },
                        },
                        "result_preview_keys": ["hit_count"],
                        "result_output_keys": ["hit_count"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": {
                        "items": [
                            {"title": "alpha"},
                            {"title": "beta"},
                            {"title": "gamma"},
                        ],
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "capacity plan"},
                prompt="search capacity plan",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["hit_count"], 3)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 3,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 3 hits.",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_answer_from_registration_semantics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_math": {
                        "template": "calc_eval",
                        "label": "Provider Calculator",
                        "kind": "provider_calc",
                        "runtime_semantic_kind": "provider_math",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/calc",
                            "method": "POST",
                            "json_body": {
                                "expression": "$expression",
                            },
                        },
                        "result_preview_keys": ["result"],
                        "result_output_keys": ["result"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {"answer": 7}
            )

            output = run_tool(
                name="provider_math",
                tool_input={"expression": "3+4"},
                prompt="calculate 3+4",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_math"]
        self.assertEqual(output["result"], 7)
        self.assertEqual(
            build_tool_result_output(
                name="provider_math",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "result": 7,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_math",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Calculated result = 7.",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_computed_value_from_registration_semantics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_math": {
                        "template": "calc_eval",
                        "label": "Provider Calculator",
                        "kind": "provider_calc",
                        "runtime_semantic_kind": "provider_math",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/calc",
                            "method": "POST",
                            "json_body": {
                                "expression": "$expression",
                            },
                        },
                        "result_preview_keys": ["result"],
                        "result_output_keys": ["result"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {"computedValue": 42}
            )

            output = run_tool(
                name="provider_math",
                tool_input={"expression": "6*7"},
                prompt="calculate 6*7",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_math"]
        self.assertEqual(output["result"], 42)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_math",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "result": 42,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_math",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Calculated result = 42.",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_value_from_scoped_object_registration_semantics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_math": {
                        "template": "calc_eval",
                        "label": "Provider Calculator",
                        "kind": "provider_calc",
                        "runtime_semantic_kind": "provider_math",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/calc",
                            "method": "POST",
                            "json_body": {
                                "expression": "$expression",
                            },
                            "response_path": "$.data",
                        },
                        "result_preview_keys": ["result"],
                        "result_output_keys": ["result"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {"data": {"value": 9}}
            )

            output = run_tool(
                name="provider_math",
                tool_input={"expression": "4+5"},
                prompt="calculate 4+5",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_math"]
        self.assertEqual(output["result"], 9)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_math",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "result": 9,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_math",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Calculated result = 9.",
        )

    def test_build_tool_registry_extra_tools_from_settings_normalizes_http_json_documents_total_string(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "documents_total": "$.meta.total",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total", "request_id"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "meta": {
                        "total": "2",
                        "request_id": "req-doc-total-string-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["documents_total"], 2)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-doc-total-string-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 documents (request id req-doc-total-string-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_normalizes_http_json_documents_total_decimal_string(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "documents_total": "$.meta.total",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total", "request_id"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "meta": {
                        "total": "2.0",
                        "request_id": "req-doc-total-decimal-string-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["documents_total"], 2)
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-doc-total-decimal-string-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 documents (request id req-doc-total-decimal-string-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_total_records_result_field_as_documents_total(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "totalRecords": "$.meta.totalRecords",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total", "request_id"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "meta": {
                        "totalRecords": "6",
                        "request_id": "req-total-records-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "record count"},
                prompt="search record count",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["documents_total"], 6)
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 6,
                "request_id": "req-total-records-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 6 documents (request id req-total-records-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_total_documents_result_field_as_documents_total(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "totalDocuments": "$.meta.totalDocuments",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total", "request_id"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "meta": {
                        "totalDocuments": "9",
                        "request_id": "req-total-documents-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "document count"},
                prompt="search document count",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["documents_total"], 9)
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 9,
                "request_id": "req-total-documents-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 9 documents (request id req-total-documents-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_normalizes_http_json_hit_count_whole_float(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "hit_count": "$.meta.hit_count",
                                "knowledge_base_id": "$.meta.knowledge_base_id",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["hit_count", "knowledge_base_id"],
                        "result_output_keys": [
                            "hit_count",
                            "knowledge_base_id",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "meta": {
                        "hit_count": 2.0,
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-hit-count-float-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-hit-count-float-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 hits (request id req-hit-count-float-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_total_hits_result_field_as_hit_count(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "totalHits": "$.meta.totalHits",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["hit_count"],
                        "result_output_keys": ["hit_count", "request_id"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "meta": {
                        "totalHits": "5",
                        "request_id": "req-total-hits-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "capacity plan"},
                prompt="search capacity plan",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["hit_count"], 5)
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 5,
                "request_id": "req-total-hits-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 5 hits (request id req-total-hits-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_total_matches_result_field_as_hit_count(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "totalMatches": "$.meta.totalMatches",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["hit_count"],
                        "result_output_keys": ["hit_count", "request_id"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "meta": {
                        "totalMatches": "7",
                        "request_id": "req-total-matches-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "capacity plan"},
                prompt="search capacity plan",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["hit_count"], 7)
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 7,
                "request_id": "req-total-matches-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 7 hits (request id req-total-matches-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_documents_total_from_items_alias(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "items": "$.data.items",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total", "request_id"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": {
                        "items": [
                            {"title": "alpha"},
                            {"title": "beta"},
                        ]
                    },
                    "meta": {
                        "request_id": "req-items-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["documents_total"], 2)
        self.assertEqual(output["items"], [{"title": "alpha"}, {"title": "beta"}])
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-items-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 documents (request id req-items-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_documents_total_from_items_when_documents_is_metadata(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "documents": "$.data.documents",
                                "items": "$.data.items",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total", "request_id"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": {
                        "documents": {"total": 10, "source": "metadata"},
                        "items": [
                            {"title": "alpha"},
                            {"title": "beta"},
                        ],
                    },
                    "meta": {
                        "request_id": "req-items-meta-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["documents_total"], 2)
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-items-meta-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 documents (request id req-items-meta-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_documents_total_from_items_when_total_is_invalid(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "documents_total": "$.meta.total",
                                "items": "$.data.items",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total", "request_id"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": {
                        "items": [
                            {"title": "alpha"},
                            {"title": "beta"},
                        ],
                    },
                    "meta": {
                        "total": "unknown",
                        "request_id": "req-items-invalid-total-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["documents_total"], 2)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-items-invalid-total-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 documents (request id req-items-invalid-total-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_hit_count_from_results_alias(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "results": "$.data.results",
                                "knowledge_base_id": "$.meta.knowledge_base_id",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["hit_count", "knowledge_base_id"],
                        "result_output_keys": [
                            "hit_count",
                            "knowledge_base_id",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": {
                        "results": [
                            {"title": "alpha"},
                            {"title": "beta"},
                            {"title": "gamma"},
                        ]
                    },
                    "meta": {
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-results-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["hit_count"], 3)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 3,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 3,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-results-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 3 hits (request id req-results-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_hit_count_from_matches_alias(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "matches": "$.data.matches",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["hit_count"],
                        "result_output_keys": ["hit_count", "request_id"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": {
                        "matches": [
                            {"id": "vec-1"},
                            {"id": "vec-2"},
                        ]
                    },
                    "meta": {
                        "request_id": "req-matches-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "request_id": "req-matches-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 hits (request id req-matches-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_hit_count_from_matches_when_results_is_metadata(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "results": "$.data.results",
                                "matches": "$.data.matches",
                                "knowledge_base_id": "$.meta.knowledge_base_id",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["hit_count", "knowledge_base_id"],
                        "result_output_keys": [
                            "hit_count",
                            "knowledge_base_id",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": {
                        "results": {"total": 20, "source": "metadata"},
                        "matches": [
                            {"id": "vec-1"},
                            {"id": "vec-2"},
                        ],
                    },
                    "meta": {
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-matches-meta-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-matches-meta-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 hits (request id req-matches-meta-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_infers_http_json_hit_count_from_matches_when_count_is_invalid(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "method": "POST",
                            "json_body": {
                                "query": "$query",
                            },
                            "result_fields": {
                                "hit_count": "$.meta.hit_count",
                                "matches": "$.data.matches",
                                "knowledge_base_id": "$.meta.knowledge_base_id",
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["hit_count", "knowledge_base_id"],
                        "result_output_keys": [
                            "hit_count",
                            "knowledge_base_id",
                            "request_id",
                        ],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {
                    "data": {
                        "matches": [
                            {"id": "vec-1"},
                            {"id": "vec-2"},
                        ],
                    },
                    "meta": {
                        "hit_count": -1,
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-matches-invalid-count-1",
                    },
                }
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        registration = extra_tools["provider_search"]
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-matches-invalid-count-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            "Retrieved 2 hits (request id req-matches-invalid-count-1).",
        )

    def test_build_tool_registry_extra_tools_from_settings_supports_http_json_execution_runtime_template_context(
        self,
    ) -> None:
        settings = SimpleNamespace(
            api_key="sk-runtime",
            base_url="https://gateway.example/v1",
            tool_registry_provider_source="analytics_suite",
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "runtime_semantic_kind": "provider_search",
                        "execution": {
                            "kind": "http_json",
                            "url": "${settings_base_url}/search",
                            "method": "GET",
                            "headers": {
                                "Authorization": "Bearer ${settings_api_key}",
                                "X-Upstream-Base-Url": "${settings_base_url}",
                            },
                            "query_params": {
                                "source": "$tool_registry_provider_source",
                                "q": "$query",
                            },
                            "result_fields": {
                                "documents_total": "$.meta.total",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": ["documents_total"],
                    }
                }
            ),
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)
        self.assertEqual(
            extra_tools["provider_search"].execution_diagnostics,
            (),
        )
        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_origin": "https://gateway.example",
                "url_path": "/v1/search",
                "header_count": 2,
                "query_param_count": 2,
                "result_field_names": ["documents_total"],
            },
        )
        urlopen_calls: list[tuple[object, object]] = []

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append((request, timeout))
                or FakeHttpResponse({"meta": {"total": 3}})
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(len(urlopen_calls), 1)
        request, timeout = urlopen_calls[0]
        self.assertEqual(timeout, 5.0)
        self.assertEqual(
            request.full_url,
            "https://gateway.example/v1/search?source=analytics_suite&q=revenue+trend",
        )
        self.assertEqual(request.headers["Authorization"], "Bearer sk-runtime")
        self.assertEqual(
            request.headers["X-upstream-base-url"],
            "https://gateway.example/v1",
        )
        self.assertEqual(
            output,
            {
                "documents_total": 3,
                "tool_kind": "provider_search",
            },
        )

    def test_get_configured_tool_registry_provider_supports_http_json_execution_runtime_template_context_for_source_extra_tools(
        self,
    ) -> None:
        settings = SimpleNamespace(
            api_key="sk-source",
            base_url="https://gateway.example/v1",
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
                                    "headers": {
                                        "Authorization": "Bearer ${settings_api_key}",
                                    },
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "q": "$query",
                                    },
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

        provider = get_configured_tool_registry_provider(settings=settings)
        urlopen_calls: list[tuple[object, object]] = []

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append((request, timeout))
                or FakeHttpResponse({"meta": {"total": 4}})
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "margin trend"},
                prompt="search margin trend",
                user_id="user-1",
                attempt=0,
                registry_provider=provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(len(urlopen_calls), 1)
        request, timeout = urlopen_calls[0]
        self.assertEqual(timeout, 5.0)
        self.assertEqual(
            request.full_url,
            "https://provider.example/search?source=analytics_suite&q=margin+trend",
        )
        self.assertEqual(request.headers["Authorization"], "Bearer sk-source")
        self.assertEqual(
            output,
            {
                "documents_total": 4,
                "tool_kind": "provider_search",
            },
        )

    def test_get_configured_tool_registry_provider_supports_http_json_execution_runtime_template_context_for_file_source_extra_tools(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "file-source-registry.json"
            root_file.write_text(
                json.dumps(
                    {
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
                                    "headers": {
                                        "Authorization": "Bearer ${settings_api_key}",
                                    },
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "q": "$query",
                                    },
                                    "result_fields": {
                                        "documents_total": "$.meta.total",
                                    },
                                },
                                "result_preview_keys": ["documents_total"],
                                "result_output_keys": ["documents_total"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                api_key="sk-file-source",
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            provider = get_configured_tool_registry_provider(settings=settings)
            urlopen_calls: list[tuple[object, object]] = []

            class FakeHttpResponse:
                def __init__(self, payload: object) -> None:
                    self._payload = json.dumps(payload).encode("utf-8")

                def read(self) -> bytes:
                    return self._payload

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append((request, timeout))
                    or FakeHttpResponse({"meta": {"total": 5}})
                )

                output = run_tool(
                    name="provider_search",
                    tool_input={"query": "cash flow"},
                    prompt="search cash flow",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(len(urlopen_calls), 1)
        request, timeout = urlopen_calls[0]
        self.assertEqual(timeout, 5.0)
        self.assertEqual(
            request.full_url,
            "https://provider.example/search?source=file_source&q=cash+flow",
        )
        self.assertEqual(request.headers["Authorization"], "Bearer sk-file-source")
        self.assertEqual(
            output,
            {
                "documents_total": 5,
                "tool_kind": "provider_search",
            },
        )

    def test_get_configured_tool_registry_provider_supports_http_json_execution_runtime_template_context_for_file_source_overrides(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "file-source-overrides.json"
            root_file.write_text(
                json.dumps(
                    {
                        "overrides": {
                            "task_retrieve": {
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "method": "GET",
                                    "headers": {
                                        "Authorization": "Bearer ${settings_api_key}",
                                    },
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "q": "$query",
                                    },
                                    "result_fields": {
                                        "documents_total": "$.meta.total",
                                    },
                                },
                                "result_preview_keys": ["documents_total"],
                                "result_output_keys": ["documents_total"],
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                api_key="sk-file-override",
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            provider = get_configured_tool_registry_provider(settings=settings)
            urlopen_calls: list[tuple[object, object]] = []

            class FakeHttpResponse:
                def __init__(self, payload: object) -> None:
                    self._payload = json.dumps(payload).encode("utf-8")

                def read(self) -> bytes:
                    return self._payload

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append((request, timeout))
                    or FakeHttpResponse({"meta": {"total": 6}})
                )

                output = run_tool(
                    name="task_retrieve",
                    tool_input={"query": "gross margin"},
                    prompt="search gross margin",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(len(urlopen_calls), 1)
        request, timeout = urlopen_calls[0]
        self.assertEqual(timeout, 5.0)
        self.assertEqual(
            request.full_url,
            "https://provider.example/search?source=file_source&q=gross+margin",
        )
        self.assertEqual(request.headers["Authorization"], "Bearer sk-file-override")
        self.assertEqual(
            output,
            {
                "documents_total": 6,
                "tool_kind": "provider_search",
            },
        )

    def test_build_tool_registry_extra_tools_from_settings_rejects_unknown_execution_kind_without_fallback(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_math": {
                        "template": "calc_eval",
                        "label": "Provider Math",
                        "kind": "provider_calc",
                        "execution": {
                            "kind": "unsupported_transport",
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        with self.assertRaises(MockToolExecutionError) as raised:
            run_tool(
                name="provider_math",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )

        self.assertTrue(raised.exception.fatal)
        self.assertIn("Unsupported tool execution kind", str(raised.exception))

    def test_build_tool_registry_extra_tools_from_settings_rejects_unsupported_runtime_template_variables_without_fallback(self) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "headers": {
                                "Authorization": "Bearer ${settings_api_keey}",
                            },
                            "query_params": {
                                "q": "$query",
                            },
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        with self.assertRaises(MockToolExecutionError) as raised:
            run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )

        self.assertTrue(raised.exception.fatal)
        self.assertIn(
            "unsupported runtime template variable settings_api_keey",
            str(raised.exception),
        )

    def test_build_tool_registry_extra_tools_from_settings_rejects_missing_runtime_template_variables_without_partial_http_request(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "query_params": {
                                "q": "$query",
                                "limit": "$top_k",
                            },
                            "result_fields": {
                                "documents_total": "$.meta.total",
                            },
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {"meta": {"total": 1}}
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="provider_search",
                    tool_input={"query": "revenue trend"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry=extra_tools,
                )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertTrue(raised.exception.fatal)
        self.assertIn("missing runtime template variable top_k", str(raised.exception))
        self.assertIn("query_params.limit", str(raised.exception))

    def test_build_tool_registry_extra_tools_from_settings_rejects_missing_http_json_response_path_without_root_fallback(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "response_path": "$.data.documents",
                            "result_fields": {
                                "documents_total": "$.meta.total",
                            },
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {"meta": {"total": 2}}
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="provider_search",
                    tool_input={"query": "revenue trend"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry=extra_tools,
                )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertTrue(raised.exception.fatal)
        self.assertIn("response_path", str(raised.exception))
        self.assertIn("$.data.documents", str(raised.exception))

    def test_build_tool_registry_extra_tools_from_settings_rejects_http_json_result_fields_when_no_mapping_resolves(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "result_fields": {
                                "documents_total": "$.meta.total",
                                "request_id": "$.meta.request_id",
                            },
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                {"data": {"documents": [{"id": "doc-1"}]}}
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="provider_search",
                    tool_input={"query": "revenue trend"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry=extra_tools,
                )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertTrue(raised.exception.fatal)
        self.assertIn("result_fields", str(raised.exception))
        self.assertIn("documents_total", str(raised.exception))
        self.assertIn("$.meta.total", str(raised.exception))

    def test_build_tool_registry_extra_tools_from_settings_rejects_http_json_result_fields_with_invalid_path_without_fallback(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "result_fields": {
                                "documents_total": 123,
                            },
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        with self.assertRaises(MockToolExecutionError) as raised:
            run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry=extra_tools,
            )

        self.assertTrue(raised.exception.fatal)
        self.assertIn(
            "result_fields.documents_total must be a non-empty string path",
            str(raised.exception),
        )
