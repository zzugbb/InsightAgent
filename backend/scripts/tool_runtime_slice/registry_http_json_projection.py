from __future__ import annotations

from .context import *


class RegistryHttpJsonProjectionMixin:
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

    def test_build_tool_registry_extra_tools_from_settings_prefers_paginated_total_over_page_length(
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
                    "data": [
                        {"documentText": "alpha document text"},
                        {"documentText": "beta document text"},
                    ],
                    "meta": {
                        "page": {
                            "total": "42",
                        },
                        "request_id": "req-paginated-search-1",
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
        self.assertEqual(output["documents_total"], 42)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["request_id"], "req-paginated-search-1")
        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry=extra_tools,
                registration=registration,
            ),
            {
                "documents_total": 42,
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
                "documents_total": 42,
                "hit_count": 2,
                "request_id": "req-paginated-search-1",
            },
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
