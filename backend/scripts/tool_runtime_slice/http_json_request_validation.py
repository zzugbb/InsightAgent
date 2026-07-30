from __future__ import annotations

from .context import *


class HttpJsonRequestValidationMixin:
    def test_run_tool_canonical_override_rejects_http_json_get_with_json_body_without_dropping_body(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "GET",
                                "json_body": {
                                    "expression": "$expression",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("GET json_body must fail before dropping request body")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={"expression": "1+2*3"},
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

        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn(
            "GET method must not define json_body",
            str(raised.exception),
        )

    def test_tool_registry_execution_diagnostics_reject_http_json_get_with_json_body(
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
                                "method": "GET",
                                "json_body": {
                                    "query": "$query",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution GET method must not "
                "define json_body; use query_params or a body-capable method",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_http_json_header_and_query_value_shapes(
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
                                    "X-Bad": {"token": "secret"},
                                },
                                "query_params": {
                                    "filter": {"status": "open"},
                                    "tags": ["ok", {"bad": True}],
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.X-Bad must be a "
                "string, number, or boolean",
                "provider_search: http_json execution query_params.filter must "
                "be a string, number, boolean, or list of those values",
                "provider_search: http_json execution query_params.tags must be "
                "a string, number, boolean, or list of those values",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_http_json_query_param_protocol_names(
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
                                    "bad&name": "open",
                                    "access_token=secret": "hidden",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution query_params.bad&name must use safe query parameter names",
                "provider_search: http_json execution query_params.[redacted] must use safe query parameter names",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("access_token", joined_diagnostics)
        self.assertNotIn("secret", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_header_protocol_shapes(
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
                                    "Bad Header": "demo",
                                    "X-Trace": "ok\r\nX-Injected: yes",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers must use valid HTTP header names",
                "provider_search: http_json execution headers.X-Trace must not contain CR or LF",
            ),
        )
        self.assertNotIn("Injected", "\n".join(diagnostics["invalid_tool_executions"]))

    def test_tool_registry_execution_diagnostics_reject_http_json_duplicate_header_names(
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
                                    "Accept": "application/json",
                                    "accept": "text/html; token=hidden",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers must not include duplicate HTTP header names",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_body_non_json_content_type(
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
                                "method": "POST",
                                "headers": {
                                    "Content-Type": "text/plain; token=hidden",
                                },
                                "json_body": {
                                    "query": "$query",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Content-Type must be application/json or a +json media type when json_body is defined: text/plain; [redacted]",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_body_non_utf8_content_type_charset(
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
                                "method": "POST",
                                "headers": {
                                    "Content-Type": (
                                        "application/json; charset=utf-16; "
                                        "token=hidden"
                                    ),
                                },
                                "json_body": {
                                    "query": "$query",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Content-Type charset must be utf-8 when json_body is defined: application/json; charset=utf-16; [redacted]",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_body_conflicting_content_type_charset(
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
                                "method": "POST",
                                "headers": {
                                    "Content-Type": (
                                        "application/json; charset=utf-8; "
                                        "charset=latin-1; token=hidden"
                                    ),
                                },
                                "json_body": {
                                    "query": "$query",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Content-Type charset must be utf-8 when json_body is defined: application/json; charset=utf-8; charset=latin-1; [redacted]",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_body_malformed_content_type_charset(
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
                                "method": "POST",
                                "headers": {
                                    "Content-Type": (
                                        "application/json; charset; token=hidden"
                                    ),
                                },
                                "json_body": {
                                    "query": "$query",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Content-Type charset must be utf-8 when json_body is defined: application/json; charset; [redacted]",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_accept_http_json_body_duplicate_utf8_content_type_charset(
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
                                "method": "POST",
                                "headers": {
                                    "Content-Type": (
                                        "application/json; charset=utf-8; "
                                        "charset=UTF8"
                                    ),
                                },
                                "json_body": {
                                    "query": "$query",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(diagnostics["invalid_tool_executions"], ())

    def test_tool_registry_execution_diagnostics_accept_http_json_content_type_quoted_charset_parameter(
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
                                "method": "POST",
                                "headers": {
                                    "Content-Type": (
                                        'application/json; profile="demo;'
                                        'charset=utf-16"'
                                    ),
                                },
                                "json_body": {
                                    "query": "$query",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(diagnostics["invalid_tool_executions"], ())

    def test_tool_registry_execution_diagnostics_reject_http_json_content_type_unclosed_quote_parameter(
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
                                "method": "POST",
                                "headers": {
                                    "Content-Type": (
                                        'application/json; profile="demo;'
                                        'charset=latin-1; token=hidden'
                                    ),
                                },
                                "json_body": {
                                    "query": "$query",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Content-Type must use balanced quoted parameters: application/json; profile=\"demo;charset=latin-1; [redacted]",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_non_json_accept_header(
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
                                    "Accept": "text/html; token=hidden",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Accept must allow application/json or a +json media type: text/html; [redacted]",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_zero_quality_accept_header(
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
                                    "Accept": "application/json; q=0; token=hidden, text/html",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Accept must allow application/json or a +json media type: application/json; q=0; [redacted], text/html",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_zero_quality_accept_masked_by_wildcard(
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
                                    "Accept": (
                                        "application/json; q=0; token=hidden, */*"
                                    ),
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Accept must allow application/json or a +json media type: application/json; q=0; [redacted], */*",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_invalid_quality_accept_header(
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
                                    "Accept": (
                                        "application/json; q=2; token=hidden, "
                                        "text/html"
                                    ),
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Accept must allow application/json or a +json media type: application/json; q=2; [redacted], text/html",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_malformed_quality_accept_header(
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
                                    "Accept": (
                                        "application/json; q; token=hidden, */*"
                                    ),
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Accept must allow application/json or a +json media type: application/json; q; [redacted], */*",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_invalid_quality_accept_masked_by_wildcard(
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
                                    "Accept": (
                                        "application/json; q=nan; "
                                        "token=hidden, */*"
                                    ),
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Accept must allow application/json or a +json media type: application/json; q=nan; [redacted], */*",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_conflicting_quality_accept_header(
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
                                    "Accept": (
                                        "application/json; q=1; q=0; "
                                        "token=hidden, text/html"
                                    ),
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Accept must allow application/json or a +json media type: application/json; q=1; q=0; [redacted], text/html",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_accept_http_json_duplicate_valid_quality_accept_header(
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
                                    "Accept": "application/json; q=1; q=0.7",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(diagnostics["invalid_tool_executions"], ())

    def test_tool_registry_execution_diagnostics_accept_http_json_quoted_accept_quality_parameter(
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
                                    "Accept": (
                                        'application/json; profile="demo;q=0", '
                                        "text/html"
                                    ),
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(diagnostics["invalid_tool_executions"], ())

    def test_tool_registry_execution_diagnostics_reject_http_json_accept_unclosed_quote_parameter(
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
                                    "Accept": (
                                        'application/json; profile="demo;'
                                        'q=0; token=hidden, */*'
                                    ),
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Accept must use balanced quoted parameters: application/json; profile=\"demo;q=0; [redacted], */*",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_body_non_finite_values(
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
                                "method": "POST",
                                "json_body": {
                                    "query": "$query",
                                    "score": float("nan"),
                                    "filters": [
                                        {"boost": float("inf")},
                                    ],
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution json_body.score must be valid JSON",
                "provider_search: http_json execution json_body.filters[0].boost must be valid JSON",
            ),
        )

    def test_run_tool_canonical_override_rejects_rendered_http_json_query_param_object_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "query_params": {
                                    "filter": "$filter",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered object query param must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "filter": {"status": "open"},
                    },
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

        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("query_params.filter", str(raised.exception))
        self.assertIn("string, number, boolean, or list", str(raised.exception))

    def test_run_tool_canonical_override_rejects_http_json_query_param_protocol_name_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "query_params": {
                                    "api_key&token": "$expression",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("invalid query param name must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={"expression": "1+2*3"},
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn(
            "query_params.[redacted] must use safe query parameter names",
            message,
        )
        self.assertNotIn("api_key", message)
        self.assertNotIn("token", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_header_injection_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "X-Trace": "$trace_header",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered header injection must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "trace_header": "ok\r\nX-Injected: yes",
                    },
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

        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.X-Trace must not contain CR or LF", str(raised.exception))
        self.assertNotIn("Injected", str(raised.exception))

    def test_run_tool_canonical_override_rejects_rendered_http_json_header_control_characters_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "X-Trace": "$trace_header",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered header control character must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "trace_header": "ok\x00bad",
                    },
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

        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.X-Trace must not contain control characters", str(raised.exception))
        self.assertNotIn("ok\x00bad", str(raised.exception))

    def test_run_tool_canonical_override_rejects_rendered_http_json_body_non_json_content_type_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "POST",
                                "headers": {
                                    "Content-Type": "$content_type",
                                },
                                "json_body": {
                                    "expression": "$expression",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered non-json content-type must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "content_type": "text/plain; secret=hidden",
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Content-Type must be application/json", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_body_non_utf8_content_type_charset_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "POST",
                                "headers": {
                                    "Content-Type": "$content_type",
                                },
                                "json_body": {
                                    "expression": "$expression",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered non-utf8 content-type charset must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "content_type": "application/problem+json; charset=latin-1; secret=hidden",
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Content-Type charset must be utf-8", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_body_conflicting_content_type_charset_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "POST",
                                "headers": {
                                    "Content-Type": "$content_type",
                                },
                                "json_body": {
                                    "expression": "$expression",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("conflicting content-type charset must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "content_type": (
                            "application/json; charset=utf-8; "
                            "charset=latin-1; secret=hidden"
                        ),
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Content-Type charset must be utf-8", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_body_malformed_content_type_charset_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "POST",
                                "headers": {
                                    "Content-Type": "$content_type",
                                },
                                "json_body": {
                                    "expression": "$expression",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("malformed content-type charset must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "content_type": "application/json; charset; secret=hidden",
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Content-Type charset must be utf-8", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_rendered_http_json_body_duplicate_utf8_content_type_charset(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "POST",
                                "headers": {
                                    "Content-Type": "$content_type",
                                },
                                "json_body": {
                                    "expression": "$expression",
                                },
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
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":7}}'

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
                name="calc_eval",
                tool_input={
                    "expression": "1+2*3",
                    "content_type": "application/json; charset=utf-8; charset=UTF8",
                },
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

        self.assertEqual(output["result"], 7)
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_accepts_rendered_http_json_content_type_quoted_charset_parameter(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "POST",
                                "headers": {
                                    "Content-Type": "$content_type",
                                },
                                "json_body": {
                                    "expression": "$expression",
                                },
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
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":7}}'

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
                name="calc_eval",
                tool_input={
                    "expression": "1+2*3",
                    "content_type": (
                        'application/problem+json; profile="demo;'
                        'charset=latin-1"'
                    ),
                },
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

        self.assertEqual(output["result"], 7)
        self.assertEqual(len(urlopen_calls), 1)
        self.assertEqual(
            urlopen_calls[0].headers["Content-type"],
            'application/problem+json; profile="demo;charset=latin-1"',
        )

    def test_run_tool_canonical_override_rejects_rendered_http_json_content_type_unclosed_quote_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "POST",
                                "headers": {
                                    "Content-Type": "$content_type",
                                },
                                "json_body": {
                                    "expression": "$expression",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("unclosed content-type quote must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "content_type": (
                            'application/json; profile="demo;'
                            "charset=latin-1; secret=hidden"
                        ),
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Content-Type must use balanced quoted parameters", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_non_json_accept_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "Accept": "$accept",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered non-json accept must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "accept": "text/html; secret=hidden",
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Accept must allow application/json", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_zero_quality_accept_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "Accept": "$accept",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered q=0 accept must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "accept": "application/json; q=0; secret=hidden, text/html",
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Accept must allow application/json", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_zero_quality_accept_masked_by_wildcard_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "Accept": "$accept",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered q=0 accept must fail before wildcard request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "accept": "application/json; q=0; secret=hidden, */*",
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Accept must allow application/json", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_invalid_quality_accept_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "Accept": "$accept",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered invalid q accept must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "accept": "application/json; q=nan; secret=hidden, text/html",
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Accept must allow application/json", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_malformed_quality_accept_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "Accept": "$accept",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered malformed q accept must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "accept": "application/json; q; secret=hidden, */*",
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Accept must allow application/json", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_invalid_quality_accept_masked_by_wildcard_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "Accept": "$accept",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered invalid q accept must fail before wildcard request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "accept": "application/json; q=nan; secret=hidden, */*",
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Accept must allow application/json", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_conflicting_quality_accept_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "Accept": "$accept",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("rendered conflicting q accept must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "accept": (
                            "application/json; q=1; q=0; secret=hidden, "
                            "text/html"
                        ),
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Accept must allow application/json", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_rendered_http_json_duplicate_valid_quality_accept_header(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "Accept": "$accept",
                                },
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
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":7}}'

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
                name="calc_eval",
                tool_input={
                    "expression": "1+2*3",
                    "accept": "application/json; q=1; q=0.7",
                },
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

        self.assertEqual(output["result"], 7)
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_accepts_rendered_http_json_quoted_accept_quality_parameter(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "Accept": "$accept",
                                },
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
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":7}}'

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
                name="calc_eval",
                tool_input={
                    "expression": "1+2*3",
                    "accept": 'application/json; profile="demo;q=0", text/html',
                },
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

        self.assertEqual(output["result"], 7)
        self.assertEqual(len(urlopen_calls), 1)
        self.assertEqual(
            urlopen_calls[0].headers["Accept"],
            'application/json; profile="demo;q=0", text/html',
        )

    def test_run_tool_canonical_override_rejects_rendered_http_json_accept_unclosed_quote_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "headers": {
                                    "Accept": "$accept",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("unclosed accept quote must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "accept": (
                            'application/json; profile="demo;'
                            "q=0; secret=hidden, */*"
                        ),
                    },
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers.Accept must use balanced quoted parameters", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_duplicate_header_names_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "POST",
                                "headers": {
                                    "Content-Type": "application/json",
                                    "content-type": "text/plain; secret=hidden",
                                },
                                "json_body": {
                                    "expression": "$expression",
                                },
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
        urlopen_calls: list[object] = []

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("duplicate header names must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={"expression": "1+2*3"},
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

        message = str(raised.exception)
        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("headers must not include duplicate HTTP header names", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)
