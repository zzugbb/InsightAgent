from __future__ import annotations

from .context import *


class ProviderToolExpansionMixin:
    def test_build_tool_plan_provider_accepts_tool_calls_mapping_container(
        self,
    ) -> None:
        class FakeProvider:
            provider = "gateway"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "message": {
                        "tool_calls": {
                            "call_calc_1": {
                                "function": {
                                    "name": "calc_eval",
                                    "arguments": json.dumps(
                                        {"expression": "96/12"},
                                        ensure_ascii=False,
                                    ),
                                }
                            }
                        }
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
            {"expression": "96/12"},
        )

    def test_build_tool_plan_provider_accepts_tool_invocations_container(
        self,
    ) -> None:
        class FakeProvider:
            provider = "ai-sdk"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "message": {
                        "toolInvocations": [
                            {
                                "toolName": "calc_eval",
                                "args": {
                                    "expression": "99/11",
                                },
                                "state": "call",
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
            {"expression": "99/11"},
        )

    def test_build_tool_plan_provider_accepts_tool_input_alias(
        self,
    ) -> None:
        class FakeProvider:
            provider = "langchain"

            def generate(self, prompt: str) -> dict[str, object]:
                del prompt
                return {
                    "tools": [
                        {
                            "tool": "calc_eval",
                            "tool_input": {
                                "expression": "100/25",
                            },
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
            {"expression": "100/25"},
        )

    def test_provider_search_normalizes_estimated_total_hits_alias(self) -> None:
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
                            "url": "https://provider.example/indexes/docs/search",
                            "method": "POST",
                            "json_body": {
                                "q": "$query",
                                "limit": 2,
                            },
                        },
                        "result_preview_keys": ["documents_total", "hit_count"],
                        "result_output_keys": [
                            "documents_total",
                            "hit_count",
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
                    "estimatedTotalHits": 84,
                    "hits": [
                        {"id": "doc-1", "content": "alpha"},
                        {"id": "doc-2", "content": "beta"},
                    ],
                    "processingTimeMs": 3,
                    "metadata": {
                        "request_id": "req-estimated-total-hits-1",
                    },
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
        self.assertEqual(output["documents_total"], 84)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["request_id"], "req-estimated-total-hits-1")
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 84,
                "hit_count": 2,
                "request_id": "req-estimated-total-hits-1",
            },
        )

    def test_provider_search_uses_results_list_count_when_total_is_absent(self) -> None:
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
                                "max_results": 3,
                            },
                        },
                        "result_preview_keys": ["documents_total", "hit_count"],
                        "result_output_keys": [
                            "documents_total",
                            "hit_count",
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
                    "requestId": "req-results-list-total-1",
                    "results": [
                        {"url": "https://example.test/a", "content": "alpha"},
                        {"url": "https://example.test/b", "content": "beta"},
                        {"url": "https://example.test/c", "content": "gamma"},
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
        self.assertEqual(output["documents_total"], 3)
        self.assertEqual(output["hit_count"], 3)
        self.assertEqual(output["request_id"], "req-results-list-total-1")
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 3,
                "hit_count": 3,
            },
        )

    def test_provider_search_uses_organic_results_count_when_total_is_absent(
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
                        "result_preview_keys": ["documents_total", "hit_count"],
                        "result_output_keys": [
                            "documents_total",
                            "hit_count",
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
                        "id": "req-organic-count-1",
                    },
                    "organic_results": [
                        {"title": "alpha", "snippet": "alpha snippet"},
                        {"title": "beta", "snippet": "beta snippet"},
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
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["request_id"], "req-organic-count-1")
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "hit_count": 2,
                "request_id": "req-organic-count-1",
            },
        )

    def test_provider_search_preserves_nested_graphql_connection_total(self) -> None:
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
                            "url": "https://provider.example/graphql",
                            "method": "POST",
                            "json_body": {
                                "query": "query Search($query: String!) { search(q: $query) { pageInfo { totalCount } edges { node { content } } } }",
                                "variables": {
                                    "query": "$query",
                                },
                            },
                        },
                        "result_preview_keys": ["documents_total", "hit_count"],
                        "result_output_keys": [
                            "documents_total",
                            "hit_count",
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
                            "pageInfo": {
                                "totalCount": 37,
                            },
                            "edges": [
                                {"node": {"content": "alpha"}},
                                {"node": {"content": "beta"}},
                            ],
                        }
                    },
                    "extensions": {
                        "requestId": "req-graphql-total-1",
                    },
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
        self.assertEqual(output["documents_total"], 37)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["request_id"], "req-graphql-total-1")
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 37,
                "hit_count": 2,
            },
        )

    def test_provider_search_supports_bracket_quoted_result_field_keys(self) -> None:
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
                            "url": "https://provider.example/odata/search",
                            "method": "GET",
                            "query_params": {
                                "search": "$query",
                            },
                            "result_fields": {
                                "documents_total": "$['@odata.count']",
                                "odata_label": '$["@odata.label"]',
                                "request_id": "$.meta.request_id",
                            },
                        },
                        "result_preview_keys": ["documents_total"],
                        "result_output_keys": [
                            "documents_total",
                            "odata_label",
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
                    "@odata.label": "provider result total",
                    "value": [
                        {"content": "alpha"},
                        {"content": "beta"},
                    ],
                    "meta": {
                        "request_id": "req-odata-bracket-1",
                    },
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
        self.assertEqual(output["documents_total"], 27)
        self.assertEqual(output["odata_label"], "provider result total")
        self.assertEqual(output["request_id"], "req-odata-bracket-1")
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 27,
                "odata_label": "provider result total",
                "request_id": "req-odata-bracket-1",
            },
        )

    def test_provider_search_normalizes_formatted_total_results_count(self) -> None:
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
                        "result_preview_keys": ["documents_total", "hit_count"],
                        "result_output_keys": [
                            "documents_total",
                            "hit_count",
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
                        "id": "req-formatted-total-1",
                    },
                    "search_information": {
                        "totalResults": "1,234",
                    },
                    "items": [
                        {"snippet": "alpha result"},
                        {"snippet": "beta result"},
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
        self.assertEqual(output["documents_total"], 1234)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["request_id"], "req-formatted-total-1")
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 1234,
                "hit_count": 2,
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
                "documents_total": 1234,
                "hit_count": 2,
                "request_id": "req-formatted-total-1",
            },
        )
