from __future__ import annotations

from .context import *


class ProviderSourceHttpJsonMixin:
    def _make_http_json_calc_registry_provider(self) -> ConfiguredToolRegistryProvider:
        return get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "result_fields": {
                                    "result": "$.data.value",
                                },
                            },
                        }
                    }
                ),
                tool_registry_extra_tools_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

    def test_run_tool_file_backed_provider_source_uses_source_profile_in_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "source-registry.json"
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
                                    "headers": {
                                        "X-Source": "$tool_registry_provider_source",
                                        "X-Profile": "$tool_registry_profile",
                                    },
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "expression": "$expression",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "expression": "$.expression",
                                        "result": "$.value",
                                        "source": "$.source",
                                        "profile": "$.profile",
                                    },
                                },
                                "result_preview_keys": [
                                    "expression",
                                    "result",
                                    "source",
                                    "profile",
                                ],
                                "result_output_keys": [
                                    "expression",
                                    "result",
                                    "source",
                                    "profile",
                                ],
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
            urlopen_calls: list[tuple[object, object]] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"data":{"expression":"8/4","value":2,"source":"calculator_suite","profile":"calculator_only"}}'

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append((request, timeout))
                    or FakeHttpResponse()
                )

                output = run_tool(
                    name="provider_math",
                    tool_input={"expression": "8/4"},
                    prompt="calc",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(
            output,
            {
                "expression": "8/4",
                "result": 2,
                "source": "calculator_suite",
                "profile": "calculator_only",
                "tool_kind": "provider_calc",
            },
        )
        self.assertEqual(len(urlopen_calls), 1)
        request, timeout = urlopen_calls[0]
        parsed_query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(parsed_query["source"], ["calculator_suite"])
        self.assertEqual(parsed_query["profile"], ["calculator_only"])
        self.assertEqual(request.get_header("X-source"), "calculator_suite")
        self.assertEqual(request.get_header("X-profile"), "calculator_only")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "expression": "8/4",
                "source": "calculator_suite",
                "profile": "calculator_only",
            },
        )
        self.assertEqual(timeout, 3.0)

    def test_run_tool_inline_provider_source_uses_source_profile_in_http_json_search_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="search_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "search_suite": {
                            "profile": "retrieval_only",
                            "extra_tools": {
                                "provider_search": {
                                    "template": "task_retrieve",
                                    "label": "Provider Search",
                                    "kind": "provider_retrieval",
                                    "execution": {
                                        "kind": "http_json",
                                        "url": "https://provider.example/search",
                                        "headers": {
                                            "X-Source": "$tool_registry_provider_source",
                                            "X-Profile": "$tool_registry_profile",
                                        },
                                        "query_params": {
                                            "query": "$query",
                                            "source": "$tool_registry_provider_source",
                                            "profile": "$tool_registry_profile",
                                        },
                                        "response_path": "$.data",
                                        "result_fields": {
                                            "documents_total": "$.total",
                                            "knowledge_base_id": "$.kb",
                                            "request_id": "$.request_id",
                                        },
                                    },
                                    "runtime_semantic_kind": "provider_search",
                                }
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
            )
        )
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"total":3,"kb":"provider-kb","request_id":"req-search-1"}}'

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(
            output,
            {
                "documents_total": 3,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-search-1",
                "tool_kind": "provider_search",
            },
        )
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        parsed_query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(parsed_query["query"], ["revenue trend"])
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        self.assertEqual(request.get_header("X-source"), "search_suite")
        self.assertEqual(request.get_header("X-profile"), "retrieval_only")

    def test_run_tool_inline_provider_source_shorthand_with_profile_uses_source_profile_in_http_json_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="search_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "search_suite": {
                            "profile": "retrieval_only",
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "headers": {
                                        "X-Source": "$tool_registry_provider_source",
                                        "X-Profile": "$tool_registry_profile",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
            )
        )
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"total":9,"kb":"shorthand-kb"}}'

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "profile shorthand"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 9)
        self.assertEqual(output["knowledge_base_id"], "shorthand-kb")
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        parsed_query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(parsed_query["query"], ["profile shorthand"])
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        self.assertEqual(request.get_header("X-source"), "search_suite")
        self.assertEqual(request.get_header("X-profile"), "retrieval_only")

    def test_inline_provider_source_shorthand_overrides_keep_real_http_json_request_mapping(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="search_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "search_suite": {
                            "profile": "retrieval_only",
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Base Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/base-search",
                                    "method": "GET",
                                    "headers": {
                                        "X-Mode": "base",
                                    },
                                    "query_params": {
                                        "q": "$query",
                                        "mode": "base",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            },
                            "overrides": {
                                "provider_search": {
                                    "label": "Source Override Search",
                                    "execution": {
                                        "kind": "http_json",
                                        "url": "https://provider.example/override-search",
                                        "method": "GET",
                                        "headers": {
                                            "X-Mode": "override",
                                            "X-Profile": "$tool_registry_profile",
                                        },
                                        "query_params": {
                                            "q": "$query",
                                            "mode": "override",
                                            "source": "$tool_registry_provider_source",
                                            "profile": "$tool_registry_profile",
                                        },
                                        "response_path": "$.payload",
                                        "result_fields": {
                                            "documents_total": "$.count",
                                            "knowledge_base_id": "$.kb",
                                        },
                                    },
                                    "result_preview_keys": [
                                        "documents_total",
                                        "knowledge_base_id",
                                    ],
                                    "result_output_keys": [
                                        "documents_total",
                                        "knowledge_base_id",
                                    ],
                                    "runtime_semantic_kind": "provider_search",
                                }
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
            )
        )
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"payload":{"count":12,"kb":"override-kb"}}'

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "override mapping"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(
            output,
            {
                "documents_total": 12,
                "knowledge_base_id": "override-kb",
                "tool_kind": "provider_search",
            },
        )
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            (
                "https://provider.example/override-search?"
                "q=override+mapping&mode=override&source=search_suite"
                "&profile=retrieval_only"
            ),
        )
        self.assertEqual(request.headers["X-mode"], "override")
        self.assertEqual(request.headers["X-profile"], "retrieval_only")

    def test_execute_tool_plan_item_file_backed_provider_source_preserves_real_search_projection(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "search-registry.json"
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
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                        "documents": "$.documents",
                                        "request_id": "$.request_id",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                                "result_preview_keys": [
                                    "documents_total",
                                    "knowledge_base_id",
                                ],
                                "result_output_keys": [
                                    "documents_total",
                                    "knowledge_base_id",
                                    "request_id",
                                ],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "registry_file": str(registry_file),
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            iteration_ctx = build_tool_iteration_context(
                step_id="step-1",
                seq=3,
                name="provider_search",
                tool_input={"query": "revenue trend"},
                model="mock-gpt",
                label="tool_1",
                token_count=5,
                display_name="Provider Search",
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return (
                        b'{"data":{"total":2,"kb":"provider-kb",'
                        b'"documents":[{"snippet":"alpha snippet"},{"content":"beta content"}],'
                        b'"request_id":"req-search-2"}}'
                    )

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                items = list(
                    execute_tool_plan_item_service_execution(
                        task_id="task-1",
                        trace_steps=[
                            {"id": "existing-1", "seq": 2, "content": "Existing"}
                        ],
                        iteration_ctx=iteration_ctx,
                        initial_action_step=iteration_ctx["action_step"],
                        tool_name="provider_search",
                        tool_input={"query": "revenue trend"},
                        prompt="search revenue trend",
                        user_id="user-1",
                        model="mock-gpt",
                        estimate_token_count=lambda text: len(text.strip()) or 0,
                        make_step_id=lambda: "rag-1",
                        raise_if_should_abort=lambda: None,
                        registry_provider=registry_provider,
                    )
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        parsed_query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(parsed_query["query"], ["revenue trend"])
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "revenue trend",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )
        self.assertEqual(tool_end_event["semantic_kind"], "provider_search")
        self.assertEqual(tool_end_event["semantic_family"], "knowledge_retrieval")
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 2 documents from provider-kb (request id req-search-2).",
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha snippet", "beta content"],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_file_backed_provider_source_preserves_real_calc_projection(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "calc-registry.json"
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
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "expression": "$expression",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "expression": "$.expression",
                                        "result": "$.value",
                                        "request_id": "$.request_id",
                                        "source": "$.source",
                                        "profile": "$.profile",
                                    },
                                },
                                "runtime_semantic_kind": "provider_math",
                                "result_preview_keys": [
                                    "expression",
                                    "result",
                                    "source",
                                    "profile",
                                ],
                                "result_output_keys": [
                                    "expression",
                                    "result",
                                    "request_id",
                                    "source",
                                    "profile",
                                ],
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
            iteration_ctx = build_tool_iteration_context(
                step_id="step-1",
                seq=3,
                name="provider_math",
                tool_input={"expression": "8/4"},
                model="mock-gpt",
                label="tool_1",
                token_count=5,
                display_name="Provider Calculator",
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return (
                        b'{"data":{"expression":"8/4","value":2,'
                        b'"request_id":"req-calc-1","source":"calculator_suite",'
                        b'"profile":"calculator_only"}}'
                    )

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                items = list(
                    execute_tool_plan_item_service_execution(
                        task_id="task-1",
                        trace_steps=[
                            {"id": "existing-1", "seq": 2, "content": "Existing"}
                        ],
                        iteration_ctx=iteration_ctx,
                        initial_action_step=iteration_ctx["action_step"],
                        tool_name="provider_math",
                        tool_input={"expression": "8/4"},
                        prompt="calculate 8 divided by 4",
                        user_id="user-1",
                        model="mock-gpt",
                        estimate_token_count=lambda text: len(text.strip()) or 0,
                        make_step_id=lambda: "rag-unused",
                        raise_if_should_abort=lambda: None,
                        registry_provider=registry_provider,
                    )
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        parsed_query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(parsed_query["source"], ["calculator_suite"])
        self.assertEqual(parsed_query["profile"], ["calculator_only"])
        self.assertEqual(request.headers["Authorization"], "Bearer calculator_only")
        self.assertEqual(request.headers["X-provider-source"], "calculator_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "expression": "8/4",
                "source": "calculator_suite",
                "profile": "calculator_only",
            },
        )
        self.assertEqual(tool_end_event["semantic_kind"], "provider_math")
        self.assertEqual(tool_end_event["semantic_family"], "local_calculator")
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "expression": "8/4",
                "result": 2,
                "source": "calculator_suite",
                "profile": "calculator_only",
            },
        )
        self.assertEqual(
            tool_end_event["result_summary"],
            "Calculated 8/4 = 2 (request id req-calc-1).",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Calculator: Calculated 8/4 = 2 (request id req-calc-1).",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "expression": "8/4",
                "result": 2,
                "request_id": "req-calc-1",
                "source": "calculator_suite",
                "profile": "calculator_only",
            },
        )

    def test_file_backed_provider_source_preflight_summary_uses_source_profile_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "search-registry.json"
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
                                    "url": "https://provider.example/${tool_registry_profile}/search",
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
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
                    tool_registry_provider_source="search_suite",
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "registry_file": str(registry_file),
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )

        provider_search_detail = next(
            detail
            for detail in build_configured_tool_registry_provider_preflight_tool_details(
                provider=registry_provider
            )
            if detail["name"] == "provider_search"
        )

        self.assertEqual(
            provider_search_detail["execution_summary"],
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/retrieval_only/search",
                "query_param_count": 1,
                "response_path": "$.data",
                "result_field_names": ["documents_total"],
            },
        )

    def test_file_backed_provider_source_manifest_profile_overrides_source_profile_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "search-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "profile": "calculator_only",
                        "extra_tools": {
                            "provider_math": {
                                "template": "calc_eval",
                                "label": "Provider Math",
                                "kind": "provider_calc",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/${tool_registry_profile}/calc",
                                    "result_fields": {
                                        "result": "$.data.value",
                                    },
                                },
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "registry_file": str(registry_file),
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )

        provider_math_detail = next(
            detail
            for detail in build_configured_tool_registry_provider_preflight_tool_details(
                provider=registry_provider
            )
            if detail["name"] == "provider_math"
        )

        self.assertEqual(
            provider_math_detail["execution_summary"]["url_path"],
            "/calculator_only/calc",
        )

    def test_file_backed_provider_source_preflight_summary_uses_calc_source_profile_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "calc-summary-registry.json"
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
                                    "url": "https://provider.example/${tool_registry_profile}/calc",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "expression": "$expression",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "expression": "$.expression",
                                        "result": "$.value",
                                        "request_id": "$.request_id",
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

        provider_math_detail = next(
            detail
            for detail in build_configured_tool_registry_provider_preflight_tool_details(
                provider=registry_provider
            )
            if detail["name"] == "provider_math"
        )

        self.assertEqual(
            provider_math_detail["execution_summary"],
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/calculator_only/calc",
                "header_count": 2,
                "query_param_count": 2,
                "json_body_field_count": 3,
                "response_path": "$.data",
                "result_field_names": ["expression", "result", "request_id"],
            },
        )

    def test_file_backed_provider_source_profile_disabled_tools_match_selected_registry(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "search-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "registry_file": str(registry_file),
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )

        self.assertEqual(
            get_registered_tool_names(registry_provider=registry_provider),
            ("provider_search", "task_retrieve"),
        )

    def test_named_provider_file_backed_source_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "provider-registry.json"
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
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_providers_json=json.dumps(
                        {
                            "search_provider": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "provider": "search_provider",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"data":{"total":4,"kb":"provider-kb"}}'

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                output = run_tool(
                    name="provider_search",
                    tool_input={"query": "margin risk"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 4)
        self.assertEqual(output["knowledge_base_id"], "provider-kb")
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        parsed_query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(parsed_query["query"], ["margin risk"])
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "margin risk",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_named_provider_shorthand_with_profile_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="search_suite",
                tool_registry_providers_json=json.dumps(
                    {
                        "search_provider": {
                            "profile": "retrieval_only",
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            },
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "search_suite": {
                            "provider": "search_provider",
                            "profile": "retrieval_only",
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
            )
        )
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"total":10,"kb":"provider-shorthand-kb"}}'

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "provider shorthand"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 10)
        self.assertEqual(output["knowledge_base_id"], "provider-shorthand-kb")
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        parsed_query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(parsed_query["query"], ["provider shorthand"])
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "provider shorthand",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_http_json_provider_search_counts_nested_web_results(self) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="",
                tool_registry_provider_sources_json=json.dumps({}),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/brave",
                                "method": "GET",
                                "query_params": {"q": "$query"},
                            },
                            "runtime_semantic_kind": "provider_search",
                        }
                    }
                ),
            )
        )

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "web": {
                            "results": [
                                {"title": "Alpha"},
                                {"title": "Beta"},
                            ]
                        },
                        "query": {"original": "nested web"},
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = (  # type: ignore[attr-defined]
                lambda request, timeout=0: FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "nested web"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 2)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["tool_kind"], "provider_search")

    def test_http_json_provider_search_uses_bing_total_estimated_matches(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="",
                tool_registry_provider_sources_json=json.dumps({}),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/bing",
                                "method": "GET",
                                "query_params": {"q": "$query"},
                            },
                            "runtime_semantic_kind": "provider_search",
                        }
                    }
                ),
            )
        )

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "webPages": {
                            "totalEstimatedMatches": "1,234",
                            "value": [
                                {"name": "Alpha"},
                                {"name": "Beta"},
                            ],
                        }
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = (  # type: ignore[attr-defined]
                lambda request, timeout=0: FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "bing nested"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 1234)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["tool_kind"], "provider_search")

    def test_http_json_provider_search_counts_citations_as_hits(self) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="",
                tool_registry_provider_sources_json=json.dumps({}),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/answer-search",
                                "method": "POST",
                                "json_body": {"query": "$query"},
                            },
                            "runtime_semantic_kind": "provider_search",
                        }
                    }
                ),
            )
        )

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "answer": "Alpha and Beta are relevant.",
                        "citations": [
                            "https://example.test/alpha",
                            "https://example.test/beta",
                        ],
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = (  # type: ignore[attr-defined]
                lambda request, timeout=0: FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "answer citations"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 2)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["tool_kind"], "provider_search")

    def test_http_json_provider_search_uses_number_of_results_total(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="",
                tool_registry_provider_sources_json=json.dumps({}),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/searxng",
                                "method": "GET",
                                "query_params": {"q": "$query"},
                            },
                            "runtime_semantic_kind": "provider_search",
                        }
                    }
                ),
            )
        )

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "number_of_results": 42,
                        "results": [
                            {"title": "Alpha"},
                            {"title": "Beta"},
                        ],
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = (  # type: ignore[attr-defined]
                lambda request, timeout=0: FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "searxng total"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 42)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["tool_kind"], "provider_search")

    def test_http_json_provider_search_uses_hyphenated_total_results(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="",
                tool_registry_provider_sources_json=json.dumps({}),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/crossref",
                                "method": "GET",
                                "query_params": {"query": "$query"},
                            },
                            "runtime_semantic_kind": "provider_search",
                        }
                    }
                ),
            )
        )

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "status": "ok",
                        "message": {
                            "total-results": 57,
                            "items": [
                                {"title": ["Alpha"]},
                                {"title": ["Beta"]},
                            ],
                        },
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = (  # type: ignore[attr-defined]
                lambda request, timeout=0: FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "crossref total"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 57)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["tool_kind"], "provider_search")

    def test_http_json_provider_search_uses_esearchresult_count_and_idlist(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="",
                tool_registry_provider_sources_json=json.dumps({}),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/pubmed/esearch",
                                "method": "GET",
                                "query_params": {"term": "$query"},
                            },
                            "runtime_semantic_kind": "provider_search",
                        }
                    }
                ),
            )
        )

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "header": {"type": "esearch"},
                        "esearchresult": {
                            "count": "123",
                            "retmax": "2",
                            "retstart": "0",
                            "idlist": ["31452104", "31437182"],
                        },
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = (  # type: ignore[attr-defined]
                lambda request, timeout=0: FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "pubmed total"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 123)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["tool_kind"], "provider_search")

    def test_http_json_provider_search_uses_result_list_hit_count(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="",
                tool_registry_provider_sources_json=json.dumps({}),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/europepmc/search",
                                "method": "GET",
                                "query_params": {"query": "$query"},
                            },
                            "runtime_semantic_kind": "provider_search",
                        }
                    }
                ),
            )
        )

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "version": "6.9",
                        "hitCount": "321",
                        "resultList": {
                            "result": [
                                {"title": "Alpha"},
                                {"title": "Beta"},
                            ]
                        },
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = (  # type: ignore[attr-defined]
                lambda request, timeout=0: FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "europe pmc total"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 321)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["tool_kind"], "provider_search")

    def test_named_loader_file_backed_source_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-registry.json"
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
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loaders_json=json.dumps(
                        {
                            "search_loader": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader": "search_loader",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"data":{"total":5,"kb":"loader-kb"}}'

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                output = run_tool(
                    name="provider_search",
                    tool_input={"query": "loader risk"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 5)
        self.assertEqual(output["knowledge_base_id"], "loader-kb")
        self.assertEqual(len(urlopen_calls), 1)
        parsed_query = parse_qs(urlparse(urlopen_calls[0].full_url).query)
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        request = urlopen_calls[0]
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "loader risk",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_named_loader_shorthand_with_profile_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="search_suite",
                tool_registry_loaders_json=json.dumps(
                    {
                        "search_loader": {
                            "profile": "retrieval_only",
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            },
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "search_suite": {
                            "loader": "search_loader",
                            "profile": "retrieval_only",
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
            )
        )
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"total":11,"kb":"loader-shorthand-kb"}}'

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "loader shorthand"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 11)
        self.assertEqual(output["knowledge_base_id"], "loader-shorthand-kb")
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        parsed_query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(parsed_query["query"], ["loader shorthand"])
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "loader shorthand",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_named_provider_loader_file_backed_source_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "provider-loader-registry.json"
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
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loaders_json=json.dumps(
                        {
                            "search_loader": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_providers_json=json.dumps(
                        {
                            "search_provider": {
                                "loader": "search_loader",
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "provider": "search_provider",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"data":{"total":6,"kb":"provider-loader-kb"}}'

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                output = run_tool(
                    name="provider_search",
                    tool_input={"query": "loader chain"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 6)
        self.assertEqual(output["knowledge_base_id"], "provider-loader-kb")
        self.assertEqual(len(urlopen_calls), 1)
        parsed_query = parse_qs(urlparse(urlopen_calls[0].full_url).query)
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        request = urlopen_calls[0]
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "loader chain",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_loader_factory_file_backed_source_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-factory-registry.json"
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
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loader_factories_json=json.dumps(
                        {
                            "search_loader_factory": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader_factory": "search_loader_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"data":{"total":7,"kb":"loader-factory-kb"}}'

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                output = run_tool(
                    name="provider_search",
                    tool_input={"query": "factory risk"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 7)
        self.assertEqual(output["knowledge_base_id"], "loader-factory-kb")
        self.assertEqual(len(urlopen_calls), 1)
        parsed_query = parse_qs(urlparse(urlopen_calls[0].full_url).query)
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        request = urlopen_calls[0]
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "factory risk",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_loader_factory_file_backed_source_applies_factory_overrides_to_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-factory-override-registry.json"
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
                                    "url": "https://provider.example/base-search",
                                    "method": "GET",
                                    "headers": {
                                        "X-Mode": "base",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "q": "$query",
                                        "mode": "base",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loader_factories_json=json.dumps(
                        {
                            "search_factory": {
                                "registry_file": str(registry_file),
                                "overrides": {
                                    "provider_search": {
                                        "label": "Factory Override Search",
                                        "execution": {
                                            "kind": "http_json",
                                            "url": "https://provider.example/factory-search",
                                            "method": "GET",
                                            "headers": {
                                                "X-Mode": "factory",
                                                "X-Provider-Source": "$tool_registry_provider_source",
                                                "X-Profile": "$tool_registry_profile",
                                            },
                                            "query_params": {
                                                "q": "$query",
                                                "mode": "factory",
                                                "source": "$tool_registry_provider_source",
                                                "profile": "$tool_registry_profile",
                                            },
                                            "response_path": "$.payload",
                                            "result_fields": {
                                                "documents_total": "$.count",
                                                "knowledge_base_id": "$.kb",
                                            },
                                        },
                                        "result_preview_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "result_output_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "runtime_semantic_kind": "provider_search",
                                    }
                                },
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader_factory": "search_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"payload":{"count":13,"kb":"factory-kb"}}'

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                output = run_tool(
                    name="provider_search",
                    tool_input={"query": "factory override"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(
            output,
            {
                "documents_total": 13,
                "knowledge_base_id": "factory-kb",
                "tool_kind": "provider_search",
            },
        )
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            (
                "https://provider.example/factory-search?"
                "q=factory+override&mode=factory&source=search_suite"
                "&profile=retrieval_only"
            ),
        )
        self.assertEqual(request.headers["X-mode"], "factory")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(request.headers["X-profile"], "retrieval_only")

    def test_loader_factory_alias_file_backed_source_applies_outer_factory_overrides_to_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-factory-alias-registry.json"
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
                                    "url": "https://provider.example/base-search",
                                    "method": "GET",
                                    "headers": {
                                        "X-Mode": "base",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "q": "$query",
                                        "mode": "base",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loader_factories_json=json.dumps(
                        {
                            "outer_search_factory": {
                                "factory": "inner_search_factory",
                                "overrides": {
                                    "provider_search": {
                                        "label": "Outer Factory Search",
                                        "execution": {
                                            "kind": "http_json",
                                            "url": "https://provider.example/outer-factory-search",
                                            "method": "GET",
                                            "headers": {
                                                "X-Mode": "outer-factory",
                                                "X-Provider-Source": "$tool_registry_provider_source",
                                                "X-Profile": "$tool_registry_profile",
                                            },
                                            "query_params": {
                                                "q": "$query",
                                                "mode": "outer-factory",
                                                "source": "$tool_registry_provider_source",
                                                "profile": "$tool_registry_profile",
                                            },
                                            "response_path": "$.payload",
                                            "result_fields": {
                                                "documents_total": "$.count",
                                                "knowledge_base_id": "$.kb",
                                            },
                                        },
                                        "result_preview_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "result_output_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "runtime_semantic_kind": "provider_search",
                                    }
                                },
                            },
                            "inner_search_factory": {
                                "registry_file": str(registry_file),
                            },
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader_factory": "outer_search_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"payload":{"count":15,"kb":"outer-factory-kb"}}'

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                output = run_tool(
                    name="provider_search",
                    tool_input={"query": "factory alias override"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(
            output,
            {
                "documents_total": 15,
                "knowledge_base_id": "outer-factory-kb",
                "tool_kind": "provider_search",
            },
        )
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            (
                "https://provider.example/outer-factory-search?"
                "q=factory+alias+override&mode=outer-factory"
                "&source=search_suite&profile=retrieval_only"
            ),
        )
        self.assertEqual(request.headers["X-mode"], "outer-factory")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(request.headers["X-profile"], "retrieval_only")

    def test_provider_factory_file_backed_source_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "provider-factory-registry.json"
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
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_provider_factories_json=json.dumps(
                        {
                            "search_provider_factory": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "provider_factory": "search_provider_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"data":{"total":8,"kb":"provider-factory-kb"}}'

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                output = run_tool(
                    name="provider_search",
                    tool_input={"query": "provider factory"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 8)
        self.assertEqual(output["knowledge_base_id"], "provider-factory-kb")
        self.assertEqual(len(urlopen_calls), 1)
        parsed_query = parse_qs(urlparse(urlopen_calls[0].full_url).query)
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        request = urlopen_calls[0]
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "provider factory",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_provider_factory_file_backed_source_applies_factory_overrides_to_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "provider-factory-override-registry.json"
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
                                    "url": "https://provider.example/base-provider-search",
                                    "method": "GET",
                                    "headers": {
                                        "X-Mode": "base",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "q": "$query",
                                        "mode": "base",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_provider_factories_json=json.dumps(
                        {
                            "search_factory": {
                                "registry_file": str(registry_file),
                                "overrides": {
                                    "provider_search": {
                                        "label": "Provider Factory Override Search",
                                        "execution": {
                                            "kind": "http_json",
                                            "url": "https://provider.example/provider-factory-search",
                                            "method": "GET",
                                            "headers": {
                                                "X-Mode": "provider-factory",
                                                "X-Provider-Source": "$tool_registry_provider_source",
                                                "X-Profile": "$tool_registry_profile",
                                            },
                                            "query_params": {
                                                "q": "$query",
                                                "mode": "provider-factory",
                                                "source": "$tool_registry_provider_source",
                                                "profile": "$tool_registry_profile",
                                            },
                                            "response_path": "$.payload",
                                            "result_fields": {
                                                "documents_total": "$.count",
                                                "knowledge_base_id": "$.kb",
                                            },
                                        },
                                        "result_preview_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "result_output_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "runtime_semantic_kind": "provider_search",
                                    }
                                },
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "provider_factory": "search_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"payload":{"count":14,"kb":"provider-factory-kb"}}'

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                output = run_tool(
                    name="provider_search",
                    tool_input={"query": "provider factory override"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(
            output,
            {
                "documents_total": 14,
                "knowledge_base_id": "provider-factory-kb",
                "tool_kind": "provider_search",
            },
        )
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            (
                "https://provider.example/provider-factory-search?"
                "q=provider+factory+override&mode=provider-factory"
                "&source=search_suite&profile=retrieval_only"
            ),
        )
        self.assertEqual(request.headers["X-mode"], "provider-factory")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(request.headers["X-profile"], "retrieval_only")

    def test_provider_factory_alias_file_backed_source_applies_outer_factory_overrides_to_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "provider-factory-alias-registry.json"
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
                                    "url": "https://provider.example/base-provider-search",
                                    "method": "GET",
                                    "headers": {
                                        "X-Mode": "base",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "q": "$query",
                                        "mode": "base",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_provider_factories_json=json.dumps(
                        {
                            "outer_search_factory": {
                                "factory": "inner_search_factory",
                                "overrides": {
                                    "provider_search": {
                                        "label": "Outer Provider Factory Search",
                                        "execution": {
                                            "kind": "http_json",
                                            "url": "https://provider.example/outer-provider-factory-search",
                                            "method": "GET",
                                            "headers": {
                                                "X-Mode": "outer-provider-factory",
                                                "X-Provider-Source": "$tool_registry_provider_source",
                                                "X-Profile": "$tool_registry_profile",
                                            },
                                            "query_params": {
                                                "q": "$query",
                                                "mode": "outer-provider-factory",
                                                "source": "$tool_registry_provider_source",
                                                "profile": "$tool_registry_profile",
                                            },
                                            "response_path": "$.payload",
                                            "result_fields": {
                                                "documents_total": "$.count",
                                                "knowledge_base_id": "$.kb",
                                            },
                                        },
                                        "result_preview_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "result_output_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "runtime_semantic_kind": "provider_search",
                                    }
                                },
                            },
                            "inner_search_factory": {
                                "registry_file": str(registry_file),
                            },
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "provider_factory": "outer_search_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"payload":{"count":16,"kb":"outer-provider-factory-kb"}}'

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                output = run_tool(
                    name="provider_search",
                    tool_input={"query": "provider factory alias override"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(
            output,
            {
                "documents_total": 16,
                "knowledge_base_id": "outer-provider-factory-kb",
                "tool_kind": "provider_search",
            },
        )
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            (
                "https://provider.example/outer-provider-factory-search?"
                "q=provider+factory+alias+override&mode=outer-provider-factory"
                "&source=search_suite&profile=retrieval_only"
            ),
        )
        self.assertEqual(request.headers["X-mode"], "outer-provider-factory")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(request.headers["X-profile"], "retrieval_only")

    def test_named_loader_file_backed_source_preflight_summary_uses_selected_source_profile(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-summary-registry.json"
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
                                    "url": "https://provider.example/${tool_registry_profile}/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "request_id": "$.request_id",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loaders_json=json.dumps(
                        {
                            "search_loader": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader": "search_loader",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )

        provider_search_detail = next(
            detail
            for detail in build_configured_tool_registry_provider_preflight_tool_details(
                provider=registry_provider
            )
            if detail["name"] == "provider_search"
        )

        self.assertEqual(
            provider_search_detail["execution_summary"],
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/retrieval_only/search",
                "header_count": 2,
                "query_param_count": 2,
                "json_body_field_count": 3,
                "response_path": "$.data",
                "result_field_names": ["documents_total", "request_id"],
            },
        )

    def test_loader_factory_file_backed_source_preflight_summary_uses_selected_source_profile(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-factory-summary-registry.json"
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
                                    "url": "https://provider.example/${tool_registry_profile}/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "request_id": "$.request_id",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loader_factories_json=json.dumps(
                        {
                            "search_loader_factory": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader_factory": "search_loader_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )

        provider_search_detail = next(
            detail
            for detail in build_configured_tool_registry_provider_preflight_tool_details(
                provider=registry_provider
            )
            if detail["name"] == "provider_search"
        )

        self.assertEqual(
            provider_search_detail["execution_summary"],
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/retrieval_only/search",
                "header_count": 2,
                "query_param_count": 2,
                "json_body_field_count": 3,
                "response_path": "$.data",
                "result_field_names": ["documents_total", "request_id"],
            },
        )
