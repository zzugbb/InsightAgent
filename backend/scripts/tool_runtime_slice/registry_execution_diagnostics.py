from __future__ import annotations

from .context import *


class RegistryExecutionDiagnosticsMixin:
    def test_build_tool_registry_diagnostics_summary_keeps_shape(self) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": ("/tmp/base.json",),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": ("/tmp/missing-dir",),
        }

        result = build_tool_registry_diagnostics_summary(diagnostics=diagnostics)

        self.assertTrue(result["has_diagnostics"])
        self.assertEqual(result["skipped_total"], 2)
        self.assertEqual(result["missing_total"], 2)
        self.assertEqual(result["total"], 4)
        self.assertEqual(
            result["entries"],
            (
                {
                    "kind": "skipped",
                    "target": "registry_sources",
                    "count": 1,
                    "values": ("planning_suite",),
                },
                {
                    "kind": "skipped",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/base.json",),
                },
                {
                    "kind": "missing",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/missing.json",),
                },
                {
                    "kind": "missing",
                    "target": "registry_dirs",
                    "count": 1,
                    "values": ("/tmp/missing-dir",),
                },
            ),
        )

    def test_build_tool_registry_diagnostics_summary_includes_invalid_tool_execution_entries(
        self,
    ) -> None:
        diagnostics = {
            "skipped_registry_sources": (),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": (),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
            "invalid_tool_executions": (
                "provider_search: unsupported tool execution kind unsupported_transport",
            ),
        }

        result = build_tool_registry_diagnostics_summary(diagnostics=diagnostics)

        self.assertTrue(result["has_diagnostics"])
        self.assertEqual(result["skipped_total"], 0)
        self.assertEqual(result["missing_total"], 0)
        self.assertEqual(result["total"], 1)
        self.assertEqual(
            result["entries"],
            (
                {
                    "kind": "invalid",
                    "target": "tool_executions",
                    "count": 1,
                    "values": (
                        "provider_search: unsupported tool execution kind unsupported_transport",
                    ),
                },
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_accepts_renderable_http_json_url_template(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                base_url="https://gateway.example/v1",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "${settings_base_url}/search",
                                "query_params": {
                                    "q": "$query",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(diagnostics["invalid_tool_executions"], ())

    def test_build_tool_registry_settings_execution_diagnostics_redacts_sensitive_execution_kind(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "token=hidden",
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: unsupported tool execution kind [redacted]",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_build_tool_registry_settings_execution_diagnostics_rejects_http_json_url_credentials_without_summary_leak(
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
                            "url": "https://token:secret@provider.example/search",
                        },
                    }
                }
            )
        )

        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=settings
        )
        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution url must not include credentials",
            ),
        )
        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
            },
        )
        self.assertNotIn(
            "token",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "secret",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )

    def test_build_tool_registry_settings_execution_diagnostics_rejects_http_json_url_invalid_port_without_summary_crash(
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
                            "url": "https://provider.example:bad/search",
                        },
                    }
                }
            )
        )

        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=settings
        )
        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution url must include a valid port when port is provided",
            ),
        )
        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_path": "/search",
            },
        )

    def test_build_tool_registry_settings_execution_diagnostics_rejects_http_json_url_control_characters_without_echo(
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
                            "url": "https://provider.example/search path",
                        },
                    }
                }
            )
        )

        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=settings
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution url must not contain control characters or spaces",
            ),
        )
        self.assertNotIn(
            "search path",
            "\n".join(diagnostics["invalid_tool_executions"]),
        )

    def test_build_tool_registry_settings_execution_diagnostics_rejects_rendered_http_json_header_injection_without_echo(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                api_key="sk-live\r\nX-Injected: yes",
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
                                    "Authorization": "Bearer ${settings_api_key}",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Authorization must not contain CR or LF",
            ),
        )
        self.assertNotIn("Injected", "\n".join(diagnostics["invalid_tool_executions"]))

    def test_build_tool_registry_settings_execution_diagnostics_rejects_http_json_header_control_characters_without_echo(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
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
                                    "X-Trace": "ok\x00bad",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.X-Trace must not contain control characters",
            ),
        )
        self.assertNotIn("ok\x00bad", "\n".join(diagnostics["invalid_tool_executions"]))

    def test_build_tool_registry_settings_execution_diagnostics_redacts_sensitive_request_field_paths(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
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
                                    "api_key": {"raw": "bad"},
                                },
                                "json_body": {
                                    "access_token": float("nan"),
                                    "filters": [
                                        {
                                            "client_secret": float("inf"),
                                        }
                                    ],
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution query_params.[redacted] must be a string, number, boolean, or list of those values",
                "provider_search: http_json execution json_body.[redacted] must be valid JSON",
                "provider_search: http_json execution json_body.filters[0].[redacted] must be valid JSON",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("api_key", joined_diagnostics)
        self.assertNotIn("access_token", joined_diagnostics)
        self.assertNotIn("client_secret", joined_diagnostics)

    def test_build_tool_registry_settings_execution_diagnostics_accept_http_json_query_params_root_template(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "query_params": "$params",
                                "result_fields": {
                                    "documents_total": "$.meta.total",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(diagnostics["invalid_tool_executions"], ())

    def test_build_tool_registry_settings_execution_diagnostics_reject_http_json_query_params_literal_string(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "query_params": "q=margin",
                                "result_fields": {
                                    "documents_total": "$.meta.total",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution query_params must be an object",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_accept_http_json_headers_root_template(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "headers": "$headers",
                                "result_fields": {
                                    "documents_total": "$.meta.total",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(diagnostics["invalid_tool_executions"], ())

    def test_build_tool_registry_settings_execution_diagnostics_reject_http_json_headers_literal_string(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "headers": "Authorization: Bearer token",
                                "result_fields": {
                                    "documents_total": "$.meta.total",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers must be an object",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_redacts_sensitive_missing_template_reference_paths(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
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
                                    "api_key": "$tool_registry_api_key_typo",
                                },
                                "json_body": {
                                    "access_token": "$settings_access_token_typo",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution references unsupported runtime template variable [redacted] in query_params.[redacted]",
                "provider_search: http_json execution references unsupported runtime template variable [redacted] in json_body.[redacted]",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("tool_registry_api_key_typo", joined_diagnostics)
        self.assertNotIn("settings_access_token_typo", joined_diagnostics)
        self.assertNotIn("query_params.api_key", joined_diagnostics)
        self.assertNotIn("json_body.access_token", joined_diagnostics)

    def test_build_tool_registry_settings_execution_summary_redacts_http_json_url_path_sensitive_assignment(
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
                            "url": "https://provider.example/v1/token=hidden/search/api_key/secret-value",
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/v1/[redacted]/search/[redacted]/[redacted]",
            },
        )
        self.assertNotIn(
            "token",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "api_key",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "hidden",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "secret-value",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )

    def test_build_tool_registry_settings_execution_summary_redacts_http_json_percent_encoded_sensitive_url_path(
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
                            "url": "https://provider.example/v1/api_key%2Fsecret-value/search",
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/v1/[redacted]/[redacted]/search",
            },
        )
        summary_json = json.dumps(extra_tools["provider_search"].execution_summary)
        self.assertNotIn("api_key", summary_json)
        self.assertNotIn("secret-value", summary_json)

    def test_build_tool_registry_settings_execution_summary_redacts_http_json_sensitive_result_field_names(
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
                                "access_token": "$.meta.token",
                                "api_key": "$.meta.api_key",
                            },
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "result_field_names": [
                    "documents_total",
                    "[redacted]",
                    "[redacted]",
                ],
            },
        )
        self.assertNotIn(
            "access_token",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "api_key",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )

    def test_build_tool_registry_settings_execution_summary_redacts_http_json_sensitive_response_path(
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
                            "response_path": "$.data.token=hidden",
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "response_path": "$.data.[redacted]",
            },
        )
        self.assertNotIn(
            "hidden",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "token",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )

    def test_build_tool_execution_summary_accepts_http_json_typed_request_values(
        self,
    ) -> None:
        class HeaderMapping:
            def model_dump(self) -> UserDict:
                return UserDict(
                    {
                        UserString("Content-Type"): "application/json",
                        "X-Provider": "typed-source",
                    }
                )

        class QueryMapping:
            def to_json(self) -> UserString:
                return UserString('{"source":"analytics","tag":["fresh","typed"]}')

        class BodyPayload:
            def to_dict(self) -> UserDict:
                return UserDict(
                    {
                        UserString("expression"): "1+2*3",
                        "filters": UserList(["provider", "fresh"]),
                    }
                )

        execution_summary = (
            tool_runtime_module._build_tool_execution_summary_from_spec(  # type: ignore[attr-defined]
                {
                    "kind": "http_json",
                    "url": "https://provider.example/search",
                    "method": "POST",
                    "headers": HeaderMapping(),
                    "query_params": QueryMapping(),
                    "json_body": BodyPayload(),
                    "response_path": UserString("$.data"),
                    "result_fields": UserDict(
                        {
                            UserString("result"): UserString("$.data.value"),
                        }
                    ),
                }
            )
        )

        self.assertEqual(
            execution_summary,
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "header_count": 2,
                "query_param_count": 2,
                "json_body_field_count": 2,
                "response_path": "$.data",
                "result_field_names": ["result"],
            },
        )

    def test_build_tool_execution_summary_accepts_http_json_typed_template_result_fields(
        self,
    ) -> None:
        class ResultFields:
            def model_dump(self) -> UserDict:
                return UserDict(
                    {
                        UserString("documents_total"): UserString("$.meta.total"),
                        "request_id": UserString("$.meta.request_id"),
                    }
                )

        execution_summary = (
            tool_runtime_module._build_tool_execution_summary_from_spec(  # type: ignore[attr-defined]
                {
                    "kind": "http_json",
                    "url": "https://provider.example/search",
                    "result_fields": "$settings_model",
                },
                template_context={
                    "settings_model": ResultFields(),
                },
            )
        )

        self.assertEqual(
            execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "result_field_names": ["documents_total", "request_id"],
            },
        )

    def test_build_tool_execution_summary_accepts_http_json_control_field_string_wrappers(
        self,
    ) -> None:
        execution_summary = (
            tool_runtime_module._build_tool_execution_summary_from_spec(  # type: ignore[attr-defined]
                {
                    "kind": UserString("http_json"),
                    "url": UserString("https://provider.example/search"),
                    "method": UserString("POST"),
                    "json_body": {
                        "query": "$query",
                    },
                }
            )
        )

        self.assertEqual(
            execution_summary,
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "json_body_field_count": 1,
            },
        )

    def test_build_tool_execution_summary_accepts_http_json_kind_string_wrapper(
        self,
    ) -> None:
        execution_summary = (
            tool_runtime_module._build_tool_execution_summary_from_spec(  # type: ignore[attr-defined]
                {
                    "kind": UserString("http_json"),
                    "url": "https://provider.example/search",
                }
            )
        )

        self.assertEqual(
            execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
            },
        )

    def test_build_tool_execution_summary_renders_http_json_method_template(
        self,
    ) -> None:
        execution_summary = (
            tool_runtime_module._build_tool_execution_summary_from_spec(  # type: ignore[attr-defined]
                {
                    "kind": "http_json",
                    "url": "https://provider.example/search",
                    "method": "$settings_mode",
                    "json_body": {
                        "query": "$query",
                    },
                },
                template_context={
                    "settings_mode": UserString("PATCH"),
                },
            )
        )

        self.assertEqual(
            execution_summary,
            {
                "method": "PATCH",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "json_body_field_count": 1,
            },
        )

    def test_build_tool_registry_extra_tools_from_settings_filters_sensitive_result_preview_and_output_keys(
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
                            "kind": "http_json",
                            "url": "https://provider.example/calc",
                            "result_fields": {
                                "result": "$.data.value",
                                "access_token": "$.meta.token",
                                "api_key": "$.meta.api_key",
                            },
                        },
                        "result_preview_keys": ["result", "access_token"],
                        "result_output_keys": ["result", "api_key"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(extra_tools["provider_math"].result_preview_keys, ("result",))
        self.assertEqual(extra_tools["provider_math"].result_output_keys, ("result",))

    def test_build_tool_registry_extra_tools_from_settings_does_not_fallback_when_only_sensitive_result_keys_are_declared(
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
                            "kind": "http_json",
                            "url": "https://provider.example/calc",
                            "result_fields": {
                                "access_token": "$.meta.token",
                            },
                        },
                        "result_preview_keys": ["access_token"],
                        "result_output_keys": ["api_key"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(extra_tools["provider_math"].result_preview_keys, ())
        self.assertEqual(extra_tools["provider_math"].result_output_keys, ())

    def test_build_tool_registry_settings_execution_diagnostics_reports_unsupported_runtime_template_variables(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
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
                                    "source": "$tool_registry_provider_sourcee",
                                    "q": "$query",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution references unsupported runtime template variable settings_api_keey in headers.Authorization",
                "provider_search: http_json execution references unsupported runtime template variable tool_registry_provider_sourcee in query_params.source",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_reports_invalid_result_field_paths(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
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
                                    "request_id": " ",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution result_fields.documents_total must be a non-empty string path",
                "provider_search: http_json execution result_fields.request_id must be a non-empty string path",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_redacts_sensitive_result_field_names(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
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
                                    "access_token": 123,
                                    "api_key": "$.data.documents[-1]",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution result_fields.[redacted] must be a non-empty string path",
                "provider_search: http_json execution result_fields.[redacted] must use dot fields and numeric indexes",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("access_token", joined_diagnostics)
        self.assertNotIn("api_key", joined_diagnostics)

    def test_build_tool_registry_settings_execution_diagnostics_reports_blank_result_field_names(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
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
                                    " ": "$.meta.total",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution result_fields must include at least one non-empty field name",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_reports_mixed_blank_result_field_names(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
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
                                    " ": "$.meta.total",
                                    "documents_total": "$.meta.total",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution result_fields must not include blank field names",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_reports_empty_result_fields_mapping(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "result_fields": {},
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution result_fields must include at least one field mapping",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_reports_blank_response_path(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "response_path": " ",
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution response_path must be a non-empty string when provided",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_reports_blank_request_field_names(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
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
                                    " ": "Bearer demo",
                                },
                                "query_params": {
                                    " ": "$query",
                                },
                                "json_body": {
                                    " ": "$query",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers must not include blank field names",
                "provider_search: http_json execution headers must include at least one non-empty field name when provided",
                "provider_search: http_json execution query_params must not include blank field names",
                "provider_search: http_json execution query_params must include at least one non-empty field name when provided",
                "provider_search: http_json execution json_body must not include blank field names",
                "provider_search: http_json execution json_body must include at least one non-empty field name when provided",
            ),
        )

    def test_merge_tool_registry_file_diagnostics_accepts_list_values(self) -> None:
        diagnostics = tool_runtime_module._merge_tool_registry_file_diagnostics(  # type: ignore[attr-defined]
            {
                "skipped_registry_sources": ["planning_suite", "planning_suite"],
                "missing_registry_sources": [],
                "skipped_registry_files": ["/tmp/base.json"],
                "missing_registry_files": ["/tmp/missing.json"],
                "skipped_registry_dirs": [],
                "missing_registry_dirs": ["/tmp/missing-dir"],
            },
            {
                "skipped_registry_sources": ["planning_suite", "planning_suite_2"],
                "missing_registry_sources": [],
                "skipped_registry_files": [],
                "missing_registry_files": ["/tmp/missing.json", "/tmp/missing-2.json"],
                "skipped_registry_dirs": [],
                "missing_registry_dirs": [],
            },
        )

        self.assertEqual(
            diagnostics,
            {
                "skipped_registry_sources": ("planning_suite", "planning_suite_2"),
                "missing_registry_sources": (),
                "skipped_registry_files": ("/tmp/base.json",),
                "missing_registry_files": (
                    "/tmp/missing.json",
                    "/tmp/missing-2.json",
                ),
                "skipped_registry_dirs": (),
                "missing_registry_dirs": ("/tmp/missing-dir",),
                "invalid_tool_executions": (),
            },
        )

    def test_build_tool_registry_diagnostics_summary_accepts_list_values(self) -> None:
        diagnostics = {
            "skipped_registry_sources": ["planning_suite"],
            "missing_registry_sources": [],
            "skipped_registry_files": ["/tmp/base.json"],
            "missing_registry_files": ["/tmp/missing.json"],
            "skipped_registry_dirs": [],
            "missing_registry_dirs": ["/tmp/missing-dir"],
        }

        result = build_tool_registry_diagnostics_summary(diagnostics=diagnostics)

        self.assertTrue(result["has_diagnostics"])
        self.assertEqual(result["skipped_total"], 2)
        self.assertEqual(result["missing_total"], 2)
        self.assertEqual(result["total"], 4)
        self.assertEqual(
            result["entries"],
            (
                {
                    "kind": "skipped",
                    "target": "registry_sources",
                    "count": 1,
                    "values": ("planning_suite",),
                },
                {
                    "kind": "skipped",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/base.json",),
                },
                {
                    "kind": "missing",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/missing.json",),
                },
                {
                    "kind": "missing",
                    "target": "registry_dirs",
                    "count": 1,
                    "values": ("/tmp/missing-dir",),
                },
            ),
        )

    def test_build_tool_registry_diagnostics_summary_deduplicates_safe_values(
        self,
    ) -> None:
        diagnostics = {
            "skipped_registry_sources": (
                "planning_suite",
                "planning_suite",
            ),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": (
                "/tmp/missing.json",
                "/tmp/missing.json",
            ),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_summary(diagnostics=diagnostics)

        self.assertTrue(result["has_diagnostics"])
        self.assertEqual(result["skipped_total"], 1)
        self.assertEqual(result["missing_total"], 1)
        self.assertEqual(result["total"], 2)
        self.assertEqual(
            result["entries"],
            (
                {
                    "kind": "skipped",
                    "target": "registry_sources",
                    "count": 1,
                    "values": ("planning_suite",),
                },
                {
                    "kind": "missing",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/missing.json",),
                },
            ),
        )

    def test_build_tool_registry_diagnostics_summary_model_keeps_fields(self) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_summary_model(diagnostics=diagnostics)

        self.assertTrue(result.has_diagnostics)
        self.assertEqual(result.skipped_total, 1)
        self.assertEqual(result.missing_total, 1)
        self.assertEqual(result.total, 2)
        self.assertEqual(result.entries[0]["kind"], "skipped")
        self.assertEqual(result.entries[1]["kind"], "missing")

    def test_build_tool_registry_diagnostics_runtime_artifacts_keep_shape(self) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="file_source",
            diagnostics=diagnostics,
        )

        self.assertTrue(result["summary"]["has_diagnostics"])
        self.assertEqual(
            result["trace_step"],
            {
                "id": "step-1",
                "seq": 4,
                "type": "observation",
                "content": (
                    "Tool registry diagnostics: source=file_source skipped=1 missing=1\n"
                    "skipped registry sources: planning_suite\n"
                    "missing registry files: /tmp/missing.json"
                ),
                "meta": {
                    "model": "mock-gpt",
                    "step_type": "tool_registry_diagnostics",
                    "tokens": None,
                    "cost_estimate": None,
                    "tool_registry": {
                        "provider_source": "file_source",
                        "has_diagnostics": True,
                        "skipped_total": 1,
                        "missing_total": 1,
                        "total": 2,
                        "entries": (
                            {
                                "kind": "skipped",
                                "target": "registry_sources",
                                "count": 1,
                                "values": ("planning_suite",),
                            },
                            {
                                "kind": "missing",
                                "target": "registry_files",
                                "count": 1,
                                "values": ("/tmp/missing.json",),
                            },
                        ),
                    },
                },
            },
        )
        self.assertEqual(
            result["trace_event"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": result["trace_step"],
            },
        )
        self.assertEqual(
            result["audit_detail"],
            {
                "provider_source": "file_source",
                "has_diagnostics": True,
                "skipped_total": 1,
                "missing_total": 1,
                "total": 2,
                "entries": (
                    {
                        "kind": "skipped",
                        "target": "registry_sources",
                        "count": 1,
                        "values": ("planning_suite",),
                    },
                    {
                        "kind": "missing",
                        "target": "registry_files",
                        "count": 1,
                        "values": ("/tmp/missing.json",),
                    },
                ),
            },
        )

    def test_build_tool_registry_diagnostics_runtime_artifacts_redacts_sensitive_values(
        self,
    ) -> None:
        diagnostics = {
            "skipped_registry_sources": (),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": (),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
            "invalid_tool_executions": (
                "provider_status: unsupported tool execution kind api_key=hidden",
                "provider_search: http_json execution query_params.access_token must be safe",
                "provider_search: http_json execution result_fields['access_token'] must be safe",
            ),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="file_source",
            diagnostics=diagnostics,
        )

        self.assertTrue(result["summary"]["has_diagnostics"])
        self.assertEqual(
            result["summary"]["entries"][0]["values"],
            (
                "provider_status: unsupported tool execution kind [redacted]",
                "provider_search: http_json execution [redacted] must be safe",
            ),
        )
        content = result["trace_step"]["content"]
        self.assertIn("unsupported tool execution kind [redacted]", content)
        self.assertIn("http_json execution [redacted] must be safe", content)
        self.assertNotIn("api_key=hidden", content)
        self.assertNotIn("access_token", content)

    def test_build_tool_registry_diagnostics_runtime_artifacts_redacts_sensitive_provider_source_name(
        self,
    ) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": (),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="suite_api_key=hidden",
            diagnostics=diagnostics,
        )

        self.assertEqual(
            result["trace_step"]["meta"]["tool_registry"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertIn("source=suite_[redacted]", result["trace_step"]["content"])
        self.assertEqual(
            result["audit_detail"]["provider_source"],
            "suite_[redacted]",
        )
        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
