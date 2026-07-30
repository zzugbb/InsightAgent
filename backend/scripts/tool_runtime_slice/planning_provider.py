from __future__ import annotations

from .context import *


class PlanningProviderMixin:
    def test_build_tool_plan_keeps_calc_and_retrieve_behavior(self) -> None:
        plan = build_tool_plan("请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]")

        self.assertEqual(plan[0]["name"], "task_plan")
        self.assertEqual(plan[1]["name"], "task_retrieve")
        self.assertEqual(plan[1]["input"]["knowledge_base_id"], "demo")
        self.assertEqual(plan[2]["name"], "calc_eval")
        self.assertEqual(plan[2]["input"]["expression"], "1+2*3")

    def test_build_tool_plan_supports_generic_multi_tool_marker(self) -> None:
        plan = build_tool_plan("请先规划再执行 [multi-tool]")

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "task_retrieve"],
        )

    def test_build_tool_plan_respects_registry_provider_when_retrieve_disabled(self) -> None:
        provider = StaticToolRegistryProvider(
            {
                "task_plan": get_default_tool_registry()["task_plan"],
                "calc_eval": get_default_tool_registry()["calc_eval"],
            }
        )

        plan = build_tool_plan(
            "请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]",
            registry_provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "calc_eval"],
        )

    def test_build_tool_plan_respects_planning_only_registry_provider(self) -> None:
        provider = StaticToolRegistryProvider(
            {
                "task_plan": get_default_tool_registry()["task_plan"],
            }
        )

        plan = build_tool_plan(
            "请帮我检索知识库并计算 [calc:1+2*3] [kb:demo] [multi-tool]",
            registry_provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan"],
        )

    def test_build_tool_plan_supports_extra_calculator_tool_in_rule_based_planning(
        self,
    ) -> None:
        provider = get_configured_tool_registry_provider(
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

        plan = build_tool_plan(
            "请帮我计算 [calc:1+2*3]",
            registry_provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "calc_eval_fast"],
        )
        self.assertEqual(
            plan[1]["input"],
            {"expression": "1+2*3"},
        )

    def test_build_tool_plan_supports_extra_retrieval_tool_in_rule_based_planning(
        self,
    ) -> None:
        provider = get_configured_tool_registry_provider(
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

        plan = build_tool_plan(
            "请先检索背景 [multi-tool] [kb:demo]",
            registry_provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "task_retrieve_hot"],
        )
        self.assertEqual(plan[1]["input"]["knowledge_base_id"], "demo")

    def test_build_tool_plan_prefers_extra_calculator_tool_over_builtin_when_both_enabled(
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
                        }
                    }
                ),
                tool_registry_overrides_json=None,
            )
        )

        plan = build_tool_plan(
            "请帮我计算 [calc:1+2*3]",
            registry_provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "calc_eval_fast"],
        )

    def test_build_tool_plan_prefers_source_extra_retrieval_tool_over_builtin_when_both_enabled(
        self,
    ) -> None:
        provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="hot_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "hot_suite": {
                            "profile": "default",
                            "extra_tools": {
                                "task_retrieve_hot": {
                                    "template": "task_retrieve",
                                    "label": "Hot Retrieval",
                                }
                            },
                        }
                    },
                    ensure_ascii=False,
                ),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
            )
        )

        plan = build_tool_plan(
            "请先检索背景 [multi-tool] [kb:demo]",
            registry_provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "task_retrieve_hot"],
        )

    def test_build_tool_plan_accepts_provider_generated_json_tools(self) -> None:
        class FakeProvider:
            provider = "openai"
            last_prompt = ""

            def generate(self, prompt: str) -> SimpleNamespace:
                self.last_prompt = prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "task_retrieve",
                                    "input": {
                                        "query": "深入检索并整理背景",
                                        "top_k": 5,
                                        "knowledge_base_id": "kb-provider",
                                    },
                                },
                                {
                                    "name": "calc_eval",
                                    "input": {"expression": "6/2"},
                                },
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

        provider = FakeProvider()
        plan = build_tool_plan(
            "请先检索再计算 [calc:1+2] [kb:demo]",
            provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "task_retrieve", "calc_eval"],
        )
        self.assertEqual(plan[1]["input"]["query"], "深入检索并整理背景")
        self.assertEqual(plan[1]["input"]["top_k"], 5)
        self.assertEqual(plan[1]["input"]["knowledge_base_id"], "kb-provider")
        self.assertEqual(plan[2]["input"]["expression"], "6/2")
        self.assertIn("JSON", provider.last_prompt)

    def test_build_tool_plan_accepts_provider_generated_mapping_wrappers(self) -> None:
        class FakeProvider:
            provider = "openai"
            last_prompt = ""

            def generate(self, prompt: str) -> SimpleNamespace:
                self.last_prompt = prompt
                return SimpleNamespace(
                    content=UserDict(
                        {
                            UserString("tools"): UserList(
                                [
                                    UserDict(
                                        {
                                            UserString("name"): UserString("task_retrieve"),
                                            UserString("input"): UserDict(
                                                {
                                                    UserString("query"): UserString(
                                                        "深入检索并整理背景"
                                                    ),
                                                    UserString("top_k"): 5,
                                                    UserString("knowledge_base_id"): UserString(
                                                        "kb-provider"
                                                    ),
                                                }
                                            ),
                                        }
                                    ),
                                    UserDict(
                                        {
                                            UserString("name"): UserString("calc_eval"),
                                            UserString("input"): UserDict(
                                                {
                                                    UserString("expression"): UserString("6/2")
                                                }
                                            ),
                                        }
                                    ),
                                ]
                            )
                        }
                    )
                )

        provider = FakeProvider()
        plan = build_tool_plan(
            "请先检索再计算 [calc:1+2] [kb:demo]",
            provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "task_retrieve", "calc_eval"],
        )
        self.assertEqual(plan[1]["input"]["query"], "深入检索并整理背景")
        self.assertEqual(plan[1]["input"]["top_k"], 5)
        self.assertEqual(plan[1]["input"]["knowledge_base_id"], "kb-provider")
        self.assertEqual(plan[2]["input"]["expression"], "6/2")
        self.assertIn("JSON", provider.last_prompt)

    def test_build_tool_plan_provider_branch_respects_registry_provider(self) -> None:
        class FakeProvider:
            provider = "openai"
            last_prompt = ""

            def generate(self, prompt: str) -> SimpleNamespace:
                self.last_prompt = prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "task_retrieve",
                                    "input": {"query": "应被过滤"},
                                },
                                {
                                    "name": "calc_eval",
                                    "input": {"expression": "6/2"},
                                },
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

        registry_provider = StaticToolRegistryProvider(
            {
                "task_plan": get_default_tool_registry()["task_plan"],
                "calc_eval": get_default_tool_registry()["calc_eval"],
            }
        )
        provider = FakeProvider()
        plan = build_tool_plan(
            "请先检索再计算 [calc:1+2] [kb:demo]",
            provider=provider,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "calc_eval"],
        )
        self.assertNotIn("task_retrieve", provider.last_prompt)
        self.assertIn("Allowed tool names: calc_eval.", provider.last_prompt)
        self.assertEqual(
            plan[0]["input"].get("planned_tool_names"),
            ["calc_eval"],
        )
        self.assertEqual(
            plan[0]["input"].get("planned_tool_labels"),
            ["Calculator"],
        )

    def test_build_tool_plan_provider_branch_accepts_extra_tool_from_registry_provider(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"
            last_prompt = ""

            def generate(self, prompt: str) -> SimpleNamespace:
                self.last_prompt = prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "calc_eval_fast",
                                    "input": {"expression": "6/2"},
                                }
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

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
        provider = FakeProvider()
        plan = build_tool_plan(
            "请先规划再计算 [calc:1+2]",
            provider=provider,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "calc_eval_fast"],
        )
        self.assertEqual(
            plan[1]["input"],
            {"expression": "6/2"},
        )
        self.assertIn("Allowed tool names: calc_eval_fast.", provider.last_prompt)
        self.assertIn("Fast Calculator", provider.last_prompt)

    def test_build_tool_plan_provider_branch_accepts_productized_extra_tool_label_from_registry_provider(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"
            last_prompt = ""

            def generate(self, prompt: str) -> SimpleNamespace:
                self.last_prompt = prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "Fast Calculator [calculator]",
                                    "input": {"expression": "6/2"},
                                }
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

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
        provider = FakeProvider()
        plan = build_tool_plan(
            "请规划一条快速计算路径",
            provider=provider,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "calc_eval_fast"],
        )
        self.assertEqual(
            plan[1]["input"],
            {"expression": "6/2"},
        )

    def test_build_tool_plan_provider_branch_annotates_semantic_family_kind_for_runtime_override_real_retrieval_tool(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
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
                )

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

        plan = build_tool_plan(
            "请先检索 revenue trend",
            provider=FakeProvider(),
            registry_provider=registry_provider,
        )

        self.assertEqual(
            plan[0]["input"].get("planned_tool_names"),
            ["provider_search"],
        )
        self.assertEqual(
            plan[0]["input"].get("planned_tool_labels"),
            ["Provider Search"],
        )
        self.assertEqual(
            plan[0]["input"].get("planned_tool_kinds"),
            ["knowledge_retrieval"],
        )

    def test_get_enabled_planning_tool_names_prefers_extra_planner_and_excludes_builtin_task_plan(
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

        self.assertEqual(
            get_enabled_planning_tool_names(
                registry_provider=registry_provider,
            ),
            ("mock_plan_brief", "calc_eval_fast"),
        )

    def test_build_tool_plan_provider_branch_uses_extra_planner_as_primary_and_hides_it_from_optional_prompt(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"
            last_prompt = ""

            def generate(self, prompt: str) -> SimpleNamespace:
                self.last_prompt = prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "mock_plan_brief",
                                    "input": {"prompt_preview": "should-be-ignored"},
                                },
                                {
                                    "name": "calc_eval_fast",
                                    "input": {"expression": "6/2"},
                                },
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

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
        provider = FakeProvider()

        plan = build_tool_plan(
            "请先规划再计算 [calc:1+2]",
            provider=provider,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["mock_plan_brief", "calc_eval_fast"],
        )
        self.assertEqual(
            plan[0]["input"].get("planned_tool_names"),
            ["calc_eval_fast"],
        )
        self.assertEqual(
            plan[0]["input"].get("planned_tool_labels"),
            ["Fast Calculator"],
        )
        self.assertIn("Allowed tool names: calc_eval_fast.", provider.last_prompt)
        self.assertNotIn("mock_plan_brief", provider.last_prompt)
        self.assertNotIn("Brief Planner", provider.last_prompt)
        self.assertIn("Do not include planner tools in the JSON", provider.last_prompt)

    def test_build_tool_plan_provider_empty_plan_is_respected_without_heuristic_fallback(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    content=json.dumps({"tools": []}, ensure_ascii=False),
                    usage=ProviderUsage(
                        prompt_tokens=9,
                        completion_tokens=4,
                        total_tokens=13,
                    ),
                )

        artifacts = build_tool_plan_artifacts(
            "请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan"],
        )
        self.assertEqual(
            artifacts.tool_plan[0]["input"].get("planned_tool_names"),
            [],
        )
        self.assertEqual(
            artifacts.tool_plan[0]["input"].get("planned_tool_labels"),
            [],
        )
        self.assertIsNotNone(artifacts.provider_usage)
        assert artifacts.provider_usage is not None
        self.assertEqual(artifacts.provider_usage.total_tokens, 13)

    def test_build_tool_plan_provider_accepts_string_tool_items(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {"tools": ["task_retrieve", "calc_eval"]},
                        ensure_ascii=False,
                    )
                )

        artifacts = build_tool_plan_artifacts(
            "请先检索再计算 [calc:1+2*3] [kb:demo]",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {
                "query": "请先检索再计算 [calc:1+2*3] [kb:demo]",
                "top_k": 4,
                "knowledge_base_id": "demo",
            },
        )
        self.assertEqual(
            artifacts.tool_plan[2]["input"],
            {"expression": "1+2*3"},
        )

    def test_build_tool_plan_provider_accepts_tool_and_arguments_aliases(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "tool": "calc_eval",
                                    "arguments": {"expression": "6/2"},
                                }
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "6/2"},
        )

    def test_build_tool_plan_provider_accepts_tool_name_and_parameters_aliases(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "tool_name": "calc_eval",
                                    "parameters": {"expression": "10/2"},
                                }
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "10/2"},
        )

    def test_build_tool_plan_provider_accepts_tool_calls_function_arguments(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "calc_eval",
                                "arguments": json.dumps(
                                    {"expression": "14/2"},
                                    ensure_ascii=False,
                                ),
                            }
                        }
                    ]
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "14/2"},
        )

    def test_build_tool_plan_provider_accepts_chat_completion_tool_calls(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "calc_eval",
                                            "arguments": json.dumps(
                                                {"expression": "18/3"},
                                                ensure_ascii=False,
                                            ),
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "18/3"},
        )

    def test_build_tool_plan_provider_accepts_chat_completion_function_call(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "choices": [
                        {
                            "message": {
                                "function_call": {
                                    "name": "calc_eval",
                                    "arguments": json.dumps(
                                        {"expression": "21/3"},
                                        ensure_ascii=False,
                                    ),
                                }
                            }
                        }
                    ]
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "21/3"},
        )

    def test_build_tool_plan_provider_accepts_flattened_task_retrieve_fields(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "task_retrieve",
                                    "query": "深入检索背景",
                                    "top_k": 2,
                                    "knowledge_base_id": "kb-flat",
                                }
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式检索标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {
                "query": "深入检索背景",
                "top_k": 2,
                "knowledge_base_id": "kb-flat",
            },
        )

    def test_build_tool_plan_provider_accepts_flattened_calc_eval_fields(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "calc_eval",
                                    "expression": "8/4",
                                }
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "8/4"},
        )

    def test_build_tool_plan_provider_accepts_structured_dict_content(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    content={
                        "tools": [
                            {
                                "name": "task_retrieve",
                                "input": {
                                    "query": "深入检索背景",
                                    "top_k": 2,
                                    "knowledge_base_id": "kb-structured",
                                },
                            }
                        ]
                    }
                )

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式检索标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {
                "query": "深入检索背景",
                "top_k": 2,
                "knowledge_base_id": "kb-structured",
            },
        )

    def test_build_tool_plan_provider_accepts_structured_tuple_tools_content(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    content={
                        "tools": (
                            "task_retrieve",
                            {
                                "name": "calc_eval",
                                "input": {"expression": "6/2"},
                            },
                        )
                    }
                )

        artifacts = build_tool_plan_artifacts(
            "请先检索再计算 [kb:demo]",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {
                "query": "请先检索再计算 [kb:demo]",
                "top_k": 4,
                "knowledge_base_id": "demo",
            },
        )
        self.assertEqual(
            artifacts.tool_plan[2]["input"],
            {"expression": "6/2"},
        )

    def test_build_tool_plan_provider_accepts_plain_structured_response_object(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "tools": [
                        {
                            "name": "calc_eval",
                            "input": {"expression": "9/3"},
                        }
                    ]
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "9/3"},
        )

    def test_build_tool_plan_provider_accepts_single_tool_object_response(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "name": "calc_eval",
                    "input": {"expression": "12/4"},
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "12/4"},
        )

    def test_build_tool_plan_provider_accepts_dict_response_envelope_with_usage(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "content": {
                        "tools": [
                            {
                                "name": "task_retrieve",
                                "input": {
                                    "query": "深入检索背景",
                                    "top_k": 3,
                                    "knowledge_base_id": "kb-envelope",
                                },
                            }
                        ]
                    },
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 5,
                        "total_tokens": 17,
                    },
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式检索标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {
                "query": "深入检索背景",
                "top_k": 3,
                "knowledge_base_id": "kb-envelope",
            },
        )
        self.assertIsNotNone(artifacts.provider_usage)
        assert artifacts.provider_usage is not None
        self.assertEqual(artifacts.provider_usage.total_tokens, 17)

    def test_build_tool_plan_provider_accepts_top_level_plan_dict_with_usage(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "tools": [
                        {
                            "name": "calc_eval",
                            "input": {"expression": "15/5"},
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 8,
                        "completion_tokens": 3,
                        "total_tokens": 11,
                    },
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "15/5"},
        )
        self.assertIsNotNone(artifacts.provider_usage)
        assert artifacts.provider_usage is not None
        self.assertEqual(artifacts.provider_usage.total_tokens, 11)

    def test_build_tool_plan_provider_accepts_content_part_list_response_envelope(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "tools": [
                                        {
                                            "name": "calc_eval",
                                            "input": {"expression": "18/6"},
                                        }
                                    ]
                                },
                                ensure_ascii=False,
                            ),
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 4,
                        "total_tokens": 14,
                    },
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "18/6"},
        )
        self.assertIsNotNone(artifacts.provider_usage)
        assert artifacts.provider_usage is not None
        self.assertEqual(artifacts.provider_usage.total_tokens, 14)

    def test_build_tool_plan_provider_accepts_input_output_usage_keys(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "tools": [
                        {
                            "name": "calc_eval",
                            "input": {"expression": "20/5"},
                        }
                    ],
                    "usage": {
                        "input_tokens": 9,
                        "output_tokens": 3,
                    },
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertIsNotNone(artifacts.provider_usage)
        assert artifacts.provider_usage is not None
        self.assertEqual(artifacts.provider_usage.prompt_tokens, 9)
        self.assertEqual(artifacts.provider_usage.completion_tokens, 3)
        self.assertIsNone(artifacts.provider_usage.total_tokens)

    def test_build_tool_plan_provider_ignores_boolean_usage_values(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "tools": [
                        {
                            "name": "calc_eval",
                            "input": {"expression": "21/7"},
                        }
                    ],
                    "usage": {
                        "input_tokens": True,
                        "output_tokens": False,
                        "total_tokens": True,
                    },
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertIsNotNone(artifacts.provider_usage)
        assert artifacts.provider_usage is not None
        self.assertIsNone(artifacts.provider_usage.prompt_tokens)
        self.assertIsNone(artifacts.provider_usage.completion_tokens)
        self.assertIsNone(artifacts.provider_usage.total_tokens)

    def test_build_tool_plan_provider_tolerates_malformed_usage_strings(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "tools": [
                        {
                            "name": "calc_eval",
                            "input": {"expression": "24/6"},
                        }
                    ],
                    "usage": {
                        "prompt_tokens": "oops",
                        "completion_tokens": "4",
                        "total_tokens": "",
                    },
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertIsNotNone(artifacts.provider_usage)
        assert artifacts.provider_usage is not None
        self.assertIsNone(artifacts.provider_usage.prompt_tokens)
        self.assertEqual(artifacts.provider_usage.completion_tokens, 4)
        self.assertIsNone(artifacts.provider_usage.total_tokens)

    def test_build_tool_plan_provider_accepts_output_text_response_envelope(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "output_text": json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "calc_eval",
                                    "input": {"expression": "27/9"},
                                }
                            ]
                        },
                        ensure_ascii=False,
                    ),
                    "usage": {
                        "prompt_tokens": 6,
                        "completion_tokens": 2,
                        "total_tokens": 8,
                    },
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "27/9"},
        )
        self.assertIsNotNone(artifacts.provider_usage)
        assert artifacts.provider_usage is not None
        self.assertEqual(artifacts.provider_usage.total_tokens, 8)

    def test_build_tool_plan_provider_accepts_nested_content_text_payload(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "content": {
                        "text": json.dumps(
                            {
                                "tools": [
                                    {
                                        "name": "task_retrieve",
                                        "input": {
                                            "query": "增长趋势",
                                            "top_k": 2,
                                            "knowledge_base_id": "kb-nested-text",
                                        },
                                    }
                                ]
                            },
                            ensure_ascii=False,
                        )
                    }
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式检索标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {
                "query": "增长趋势",
                "top_k": 2,
                "knowledge_base_id": "kb-nested-text",
            },
        )

    def test_build_tool_plan_provider_accepts_raw_chat_completions_response(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "tools": [
                                            {
                                                "name": "calc_eval",
                                                "input": {"expression": "30/10"},
                                            }
                                        ]
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "30/10"},
        )

    def test_build_tool_plan_provider_accepts_raw_responses_api_output_payload(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(
                                        {
                                            "tools": [
                                                {
                                                    "name": "task_retrieve",
                                                    "input": {
                                                        "query": "季度收入",
                                                        "top_k": 2,
                                                        "knowledge_base_id": "kb-output-array",
                                                    },
                                                }
                                            ]
                                        },
                                        ensure_ascii=False,
                                    ),
                                }
                            ]
                        }
                    ]
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式检索标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {
                "query": "季度收入",
                "top_k": 2,
                "knowledge_base_id": "kb-output-array",
            },
        )

    def test_build_tool_plan_provider_accepts_responses_api_tool_call_content(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "tool_call",
                                    "name": "calc_eval",
                                    "arguments": json.dumps(
                                        {"expression": "36/6"},
                                        ensure_ascii=False,
                                    ),
                                }
                            ]
                        }
                    ]
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "36/6"},
        )

    def test_build_tool_plan_provider_accepts_direct_responses_output_tool_call_list(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> list[dict[str, object]]:
                del prompt
                return [
                    {
                        "content": [
                            {
                                "type": "tool_call",
                                "name": "calc_eval",
                                "arguments": json.dumps(
                                    {"expression": "54/9"},
                                    ensure_ascii=False,
                                ),
                            }
                        ]
                    }
                ]

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "54/9"},
        )

    def test_build_tool_plan_provider_accepts_wrapped_responses_tool_call_payload(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def __init__(self, wrapper_key: str) -> None:
                self.wrapper_key = wrapper_key

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    self.wrapper_key: {
                        "output": [
                            {
                                "content": [
                                    {
                                        "type": "tool_call",
                                        "name": "calc_eval",
                                        "arguments": json.dumps(
                                            {"expression": "72/9"},
                                            ensure_ascii=False,
                                        ),
                                    }
                                ]
                            }
                        ]
                    }
                }

        for wrapper_key in ("response", "data", "result"):
            with self.subTest(wrapper_key=wrapper_key):
                artifacts = build_tool_plan_artifacts(
                    "普通问答，不包含显式计算标记",
                    provider=FakeProvider(wrapper_key),
                )

                self.assertTrue(artifacts.planning_provider_attempted)
                self.assertTrue(artifacts.planning_provider_used)
                self.assertEqual(
                    [item["name"] for item in artifacts.tool_plan],
                    ["task_plan", "calc_eval"],
                )
                self.assertEqual(
                    artifacts.tool_plan[1]["input"],
                    {"expression": "72/9"},
                )

    def test_build_tool_plan_provider_accepts_typed_chat_completions_response_object(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content=json.dumps(
                                    {
                                        "tools": [
                                            {
                                                "name": "calc_eval",
                                                "input": {"expression": "42/6"},
                                            }
                                        ]
                                    },
                                    ensure_ascii=False,
                                )
                            )
                        )
                    ]
                )

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "42/6"},
        )

    def test_build_tool_plan_provider_accepts_typed_responses_output_object(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    output=[
                        SimpleNamespace(
                            content=[
                                SimpleNamespace(
                                    type="output_text",
                                    text=json.dumps(
                                        {
                                            "tools": [
                                                {
                                                    "name": "task_retrieve",
                                                    "input": {
                                                        "query": "typed output",
                                                        "top_k": 2,
                                                        "knowledge_base_id": "kb-typed-output",
                                                    },
                                                }
                                            ]
                                        },
                                        ensure_ascii=False,
                                    ),
                                )
                            ]
                        )
                    ]
                )

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式检索标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {
                "query": "typed output",
                "top_k": 2,
                "knowledge_base_id": "kb-typed-output",
            },
        )

    def test_build_tool_plan_provider_accepts_typed_responses_tool_call_content(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    output=[
                        SimpleNamespace(
                            content=[
                                SimpleNamespace(
                                    type="tool_call",
                                    name="calc_eval",
                                    arguments=json.dumps(
                                        {"expression": "48/8"},
                                        ensure_ascii=False,
                                    ),
                                )
                            ]
                        )
                    ]
                )

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "48/8"},
        )

    def test_build_tool_plan_provider_accepts_typed_direct_responses_output_tool_call_list(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> list[SimpleNamespace]:
                del prompt
                return [
                    SimpleNamespace(
                        content=[
                            SimpleNamespace(
                                type="tool_call",
                                name="calc_eval",
                                arguments=json.dumps(
                                    {"expression": "63/9"},
                                    ensure_ascii=False,
                                ),
                            )
                        ]
                    )
                ]

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "63/9"},
        )

    def test_build_tool_plan_provider_accepts_typed_wrapped_responses_tool_call_payload(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    response=SimpleNamespace(
                        output=[
                            SimpleNamespace(
                                content=[
                                    SimpleNamespace(
                                        type="tool_call",
                                        name="calc_eval",
                                        arguments=json.dumps(
                                            {"expression": "81/9"},
                                            ensure_ascii=False,
                                        ),
                                    )
                                ]
                            )
                        ]
                    )
                )

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[1]["input"],
            {"expression": "81/9"},
        )

    def test_build_tool_plan_provider_accepts_typed_usage_object(
        self,
    ) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "tools": [
                        {
                            "name": "calc_eval",
                            "input": {"expression": "45/9"},
                        }
                    ],
                    "usage": SimpleNamespace(
                        input_tokens=10,
                        output_tokens="3",
                        total_tokens=13,
                    ),
                }

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式计算标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertIsNotNone(artifacts.provider_usage)
        assert artifacts.provider_usage is not None
        self.assertEqual(artifacts.provider_usage.prompt_tokens, 10)
        self.assertEqual(artifacts.provider_usage.completion_tokens, 3)
        self.assertEqual(artifacts.provider_usage.total_tokens, 13)

    def test_build_tool_plan_provider_uses_file_backed_calc_source_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "planner-calc-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_math": {
                                "template": "calc_eval",
                                "label": "Provider Calculator",
                                "kind": "provider_calc",
                                "execution": {
                                    "kind": "http_json",
                                    "method": "POST",
                                    "url": "https://provider.example/calc",
                                    "json_body": {
                                        "expression": "$expression",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "result": "$.value",
                                    },
                                },
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="calculator_suite",
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "calculator_suite": {
                                "registry_file": str(registry_file),
                                "profile": "calculator_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )

        class FakeProvider:
            provider = "openai"

            def __init__(self) -> None:
                self.last_prompt = ""

            def generate(self, prompt: str) -> SimpleNamespace:
                self.last_prompt = prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "provider_math",
                                    "input": {"expression": "8/4"},
                                }
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

        provider = FakeProvider()
        artifacts = build_tool_plan_artifacts(
            "请计算 8/4",
            provider=provider,
            registry_provider=registry_provider,
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertIn("provider_math", artifacts.allowed_tool_names)
        self.assertIn("Provider Calculator", artifacts.allowed_tool_labels)
        self.assertIn("Allowed tool names:", provider.last_prompt)
        self.assertIn("provider_math", provider.last_prompt)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["provider_math"],
        )
        self.assertEqual(
            artifacts.tool_plan[0]["input"],
            {"expression": "8/4"},
        )

    def test_build_tool_plan_provider_branch_annotates_file_backed_real_tool_execution_kinds(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "planner-real-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "method": "POST",
                                    "url": "https://provider.example/search",
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.documents_total",
                                        "request_id": "$.request_id",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            },
                            "provider_math": {
                                "template": "calc_eval",
                                "label": "Provider Calculator",
                                "kind": "provider_calc",
                                "execution": {
                                    "kind": "http_json",
                                    "method": "POST",
                                    "url": "https://provider.example/calc",
                                    "json_body": {
                                        "expression": "$expression",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "result": "$.value",
                                        "request_id": "$.request_id",
                                    },
                                },
                                "runtime_semantic_kind": "provider_math",
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="analytics_suite",
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "analytics_suite": {
                                "registry_file": str(registry_file),
                                "profile": "retrieval_calc",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )

        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "provider_search",
                                    "input": {"query": "revenue trend"},
                                },
                                {
                                    "name": "provider_math",
                                    "input": {"expression": "8/4"},
                                },
                            ]
                        },
                        ensure_ascii=False,
                    )
                )

        plan = build_tool_plan(
            "请先检索 revenue trend，再计算 8/4",
            provider=FakeProvider(),
            registry_provider=registry_provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "provider_search", "provider_math"],
        )
        self.assertEqual(
            plan[0]["input"].get("planned_tool_names"),
            ["provider_search", "provider_math"],
        )
        self.assertEqual(
            plan[0]["input"].get("planned_tool_labels"),
            ["Provider Search", "Provider Calculator"],
        )
        self.assertEqual(
            plan[0]["input"].get("planned_tool_kinds"),
            ["knowledge_retrieval", "local_calculator"],
        )
        self.assertEqual(
            plan[0]["input"].get("planned_tool_execution_kinds"),
            ["http_json", "http_json"],
        )

    def test_build_tool_plan_rule_based_selection_keeps_canonical_override_calculator_semantics(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "calc_eval": ToolRegistration(
                        name="calc_eval",
                        kind="provider_calc",
                        label="Provider Calculator",
                        retryable_by_default=False,
                        default_timeout_ms=13_000,
                        requires_user_context=False,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "expression": str(tool_input.get("expression", "")),
                            "result": 3.0,
                        },
                    )
                }
            )
        )

        plan = build_tool_plan(
            "请计算 [calc:1+2]",
            registry_provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "calc_eval"],
        )
        self.assertEqual(plan[1]["input"], {"expression": "1+2"})

    def test_build_tool_plan_rule_based_selection_keeps_canonical_override_retrieval_semantics(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "task_retrieve": ToolRegistration(
                        name="task_retrieve",
                        kind="provider_retrieval",
                        label="Provider Retrieval",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "query": str(tool_input.get("query", "")),
                            "hit_count": 1,
                            "knowledge_base_id": "demo-kb",
                            "chunks": ["alpha"],
                        },
                    )
                }
            )
        )

        plan = build_tool_plan(
            "请检索 demo",
            registry_provider=provider,
        )

        self.assertEqual(
            [item["name"] for item in plan],
            ["task_plan", "task_retrieve"],
        )
        self.assertEqual(
            plan[1]["input"]["query"],
            "请检索 demo",
        )

    def test_build_provider_tool_plan_prompt_keeps_canonical_override_semantic_input_hints(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "calc_eval": ToolRegistration(
                        name="calc_eval",
                        kind="provider_calc",
                        label="Provider Calculator",
                        retryable_by_default=False,
                        default_timeout_ms=13_000,
                        requires_user_context=False,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "expression": str(tool_input.get("expression", "")),
                        },
                    ),
                    "task_retrieve": ToolRegistration(
                        name="task_retrieve",
                        kind="provider_retrieval",
                        label="Provider Retrieval",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "query": str(tool_input.get("query", "")),
                        },
                    ),
                }
            )
        )

        planning_prompt = tool_runtime_module._build_provider_tool_plan_prompt(
            "请同时检索并计算",
            registry_provider=provider,
        )

        self.assertIn(
            "For calc_eval input, include expression.",
            planning_prompt,
        )
        self.assertIn(
            "For task_retrieve input, include query, optional top_k, optional knowledge_base_id.",
            planning_prompt,
        )

    def test_build_provider_tool_plan_prompt_infers_semantic_input_hints_for_extra_provider_kinds(
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
                            "query": str(tool_input.get("query", "")),
                            "hit_count": 1,
                            "knowledge_base_id": "demo-kb",
                            "chunks": ["alpha"],
                        },
                    ),
                    "provider_math": ToolRegistration(
                        name="provider_math",
                        kind="provider_calc",
                        label="Provider Math",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "expression": str(tool_input.get("expression", "")),
                            "result": 7.0,
                        },
                    ),
                }
            )
        )

        planning_prompt = tool_runtime_module._build_provider_tool_plan_prompt(
            "请先检索，再计算 1+2*3",
            registry_provider=provider,
        )

        self.assertIn(
            "For provider_search input, include query, optional top_k, optional knowledge_base_id.",
            planning_prompt,
        )
        self.assertIn(
            "For provider_math input, include expression.",
            planning_prompt,
        )

    def test_build_tool_plan_provider_accepts_default_tool_labels(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {"tools": ["Knowledge Retrieval"]},
                        ensure_ascii=False,
                    )
                )

        artifacts = build_tool_plan_artifacts(
            "普通问答，不包含显式检索标记",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve"],
        )

    def test_build_tool_plan_provider_accepts_override_tool_labels(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                del prompt
                return SimpleNamespace(
                    content=json.dumps(
                        {"tools": ["Calculator Suite"]},
                        ensure_ascii=False,
                    )
                )

        settings = SimpleNamespace(
            tool_registry_provider_source="calculator_suite",
            tool_registry_provider_sources_json=json.dumps(
                {
                    "calculator_suite": {
                        "profile": "calculator_only",
                        "overrides": {
                            "calc_eval": {
                                "label": "Calculator Suite",
                            }
                        },
                    }
                },
                ensure_ascii=False,
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=None,
            tool_registry_extra_tools_json=None,
            tool_registry_loaders_json=None,
            tool_registry_loader_factories_json=None,
            tool_registry_providers_json=None,
            tool_registry_provider_factories_json=None,
        )

        artifacts = build_tool_plan_artifacts(
            "请计算 [calc:8/4]",
            provider=FakeProvider(),
            registry_provider=get_configured_tool_registry_provider(settings=settings),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["calc_eval"],
        )
        self.assertEqual(
            artifacts.tool_plan[0]["input"],
            {"expression": "8/4"},
        )

    def test_build_tool_plan_artifacts_capture_provider_usage_for_planning(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                return SimpleNamespace(
                    content=json.dumps(
                        {
                            "tools": [
                                {
                                    "name": "task_retrieve",
                                    "input": {"query": "检索", "top_k": 4},
                                }
                            ]
                        },
                        ensure_ascii=False,
                    ),
                    usage=ProviderUsage(
                        prompt_tokens=21,
                        completion_tokens=7,
                        total_tokens=28,
                    ),
                )

        artifacts = build_tool_plan_artifacts(
            "请先检索",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertTrue(artifacts.planning_provider_used)
        self.assertIsNotNone(artifacts.provider_usage)
        self.assertEqual(
            artifacts.allowed_tool_names,
            ("task_plan", "task_retrieve", "calc_eval"),
        )
        self.assertEqual(
            artifacts.allowed_tool_labels,
            ("Task Planner", "Knowledge Retrieval", "Calculator"),
        )
        assert artifacts.provider_usage is not None
        self.assertEqual(artifacts.provider_usage.prompt_tokens, 21)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve"],
        )
        self.assertIn("Allowed tool names", artifacts.planning_prompt or "")

    def test_build_tool_plan_falls_back_when_provider_plan_is_invalid(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                return SimpleNamespace(content="not-json-at-all")

        plan = build_tool_plan(
            "请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]",
            provider=FakeProvider(),
        )

        self.assertEqual(plan[0]["name"], "task_plan")
        self.assertEqual(plan[1]["name"], "task_retrieve")
        self.assertEqual(plan[1]["input"]["knowledge_base_id"], "demo")
        self.assertEqual(plan[2]["name"], "calc_eval")
        self.assertEqual(plan[2]["input"]["expression"], "1+2*3")

    def test_build_tool_plan_artifacts_keep_provider_attempt_metadata_on_fallback(self) -> None:
        class FakeProvider:
            provider = "openai"

            def generate(self, prompt: str) -> SimpleNamespace:
                return SimpleNamespace(
                    content="not-json-at-all",
                    usage=ProviderUsage(
                        prompt_tokens=13,
                        completion_tokens=5,
                        total_tokens=18,
                    ),
                )

        artifacts = build_tool_plan_artifacts(
            "请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]",
            provider=FakeProvider(),
        )

        self.assertTrue(artifacts.planning_provider_attempted)
        self.assertFalse(artifacts.planning_provider_used)
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "task_retrieve", "calc_eval"],
        )
        self.assertEqual(
            artifacts.allowed_tool_names,
            ("task_plan", "task_retrieve", "calc_eval"),
        )
        self.assertIsNotNone(artifacts.provider_usage)
        assert artifacts.provider_usage is not None
        self.assertEqual(artifacts.provider_usage.total_tokens, 18)

    def test_build_tool_plan_artifacts_capture_registry_allowed_tools_metadata(self) -> None:
        registry_provider = StaticToolRegistryProvider(
            {
                "task_plan": get_default_tool_registry()["task_plan"],
                "calc_eval": get_default_tool_registry()["calc_eval"],
            }
        )

        artifacts = build_tool_plan_artifacts(
            "请先检索再计算 [calc:1+2]",
            registry_provider=registry_provider,
        )

        self.assertEqual(
            artifacts.allowed_tool_names,
            ("task_plan", "calc_eval"),
        )
        self.assertEqual(
            artifacts.allowed_tool_labels,
            ("Task Planner", "Calculator"),
        )
        self.assertEqual(
            [item["name"] for item in artifacts.tool_plan],
            ["task_plan", "calc_eval"],
        )
