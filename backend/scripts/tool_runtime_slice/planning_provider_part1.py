from __future__ import annotations

from .context import *


class PlanningProviderMixinPart1:
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

    def test_build_tool_plan_provider_accepts_top_level_message_tool_calls(
        self,
    ) -> None:
        class FakeProvider:
            provider = "cohere"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "calc_eval",
                                    "arguments": json.dumps(
                                        {"expression": "32/4"},
                                        ensure_ascii=False,
                                    ),
                                }
                            }
                        ]
                    }
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
            {"expression": "32/4"},
        )

    def test_build_tool_plan_provider_accepts_serialized_tool_calls_field(
        self,
    ) -> None:
        class FakeProvider:
            provider = "gateway"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "message": {
                        "tool_calls": json.dumps(
                            [
                                {
                                    "function": {
                                        "name": "calc_eval",
                                        "arguments": json.dumps(
                                            {"expression": "54/9"},
                                            ensure_ascii=False,
                                        ),
                                    }
                                }
                            ],
                            ensure_ascii=False,
                        )
                    }
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
            {"expression": "54/9"},
        )

    def test_build_tool_plan_provider_accepts_camel_case_message_tool_calls(
        self,
    ) -> None:
        class FakeProvider:
            provider = "ai-sdk"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "message": {
                        "toolCalls": [
                            {
                                "function": {
                                    "name": "calc_eval",
                                    "arguments": json.dumps(
                                        {"expression": "36/6"},
                                        ensure_ascii=False,
                                    ),
                                }
                            }
                        ]
                    }
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

    def test_build_tool_plan_provider_accepts_camel_case_tool_name(
        self,
    ) -> None:
        class FakeProvider:
            provider = "ai-sdk"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "message": {
                        "toolCalls": [
                            {
                                "toolName": "calc_eval",
                                "args": {
                                    "expression": "40/8",
                                },
                            }
                        ]
                    }
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
            {"expression": "40/8"},
        )

    def test_build_tool_plan_provider_accepts_camel_case_function_name(
        self,
    ) -> None:
        class FakeProvider:
            provider = "ai-sdk"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "message": {
                        "toolCalls": [
                            {
                                "functionName": "calc_eval",
                                "args": {
                                    "expression": "45/9",
                                },
                            }
                        ]
                    }
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
            {"expression": "45/9"},
        )

    def test_build_tool_plan_provider_accepts_gemini_function_call_parts(
        self,
    ) -> None:
        class FakeProvider:
            provider = "gemini"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "functionCall": {
                                            "name": "calc_eval",
                                            "args": {"expression": "27/3"},
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
            {"expression": "27/3"},
        )

    def test_build_tool_plan_provider_accepts_gemini_function_call_string_args(
        self,
    ) -> None:
        class FakeProvider:
            provider = "gemini"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "functionCall": {
                                            "name": "calc_eval",
                                            "args": json.dumps(
                                                {"expression": "45/5"},
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
            {"expression": "45/5"},
        )

    def test_build_tool_plan_provider_accepts_bedrock_tool_use_content(
        self,
    ) -> None:
        class FakeProvider:
            provider = "bedrock"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "toolu_calc_1",
                                "name": "calc_eval",
                                "input": {
                                    "expression": "64/8",
                                },
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
            {"expression": "64/8"},
        )

    def test_build_tool_plan_provider_accepts_anthropic_tool_use_with_text_content(
        self,
    ) -> None:
        class FakeProvider:
            provider = "anthropic"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "I will calculate that now.",
                        },
                        {
                            "type": "tool_use",
                            "id": "toolu_calc_3",
                            "name": "calc_eval",
                            "input": {
                                "expression": "88/11",
                            },
                        },
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
            {"expression": "88/11"},
        )

    def test_build_tool_plan_provider_accepts_tool_use_string_input(
        self,
    ) -> None:
        class FakeProvider:
            provider = "bedrock"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "toolu_calc_2",
                                "name": "calc_eval",
                                "input": json.dumps(
                                    {"expression": "72/9"},
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
            {"expression": "72/9"},
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
