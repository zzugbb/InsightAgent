from __future__ import annotations

from .context import *


class ProviderToolExpansionMixin:
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
