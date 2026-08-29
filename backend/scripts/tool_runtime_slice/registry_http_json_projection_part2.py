from __future__ import annotations

from .context import *


class RegistryHttpJsonProjectionMixinPart2:
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
