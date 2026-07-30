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

    def test_run_tool_canonical_override_accepts_http_json_lowercase_plus_json_content_type(
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
                                    "content-type": "application/problem+json; charset=utf-8",
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

        self.assertEqual(output["result"], 7)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"expression": "1+2*3"},
        )

    def test_run_tool_canonical_override_accepts_http_json_request_body_userdict_root(
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
                                "json_body": "$payload",
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
                return b'{"data":{"value":450}}'

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
                    "payload": UserDict(
                        {
                            "expression": "1+2*3",
                            "filters": UserList(["provider", "fresh"]),
                        }
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

        self.assertEqual(output["result"], 450)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"expression": "1+2*3", "filters": ["provider", "fresh"]},
        )

    def test_run_tool_canonical_override_accepts_http_json_request_body_nested_model_dump(
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
                                "json_body": {
                                    "expression": "$expression",
                                    "payload": "$payload",
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
        model_dump_kwargs: list[dict[str, object]] = []

        class FakeRequestPayload:
            def model_dump(self, *args, **kwargs) -> dict[str, object]:
                model_dump_kwargs.append(dict(kwargs))
                return {"value": 451, "tags": UserList(["typed"])}

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":451}}'

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
                    "payload": FakeRequestPayload(),
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

        self.assertEqual(output["result"], 451)
        self.assertEqual(model_dump_kwargs, [{"mode": "json"}])
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "expression": "1+2*3",
                "payload": {"value": 451, "tags": ["typed"]},
            },
        )

    def test_run_tool_canonical_override_accepts_http_json_request_body_nested_model_dump_json(
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
                                "json_body": {
                                    "payload": "$payload",
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

        class FakeRequestPayload:
            def model_dump_json(self) -> bytes:
                return b'{"value":452,"items":[{"kind":"json-dump"}]}'

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":452}}'

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
                    "payload": FakeRequestPayload(),
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

        self.assertEqual(output["result"], 452)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"payload": {"value": 452, "items": [{"kind": "json-dump"}]}},
        )

    def test_run_tool_canonical_override_accepts_http_json_request_body_nested_dump_json_when_signature_metadata_fails(
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
                                "json_body": {
                                    "payload": "$payload",
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

        class BrokenSignatureDump:
            @property
            def __signature__(self) -> object:
                raise RuntimeError("request body signature metadata exploded")

            def __call__(self) -> bytes:
                return b'{"value":482,"items":[{"kind":"json-dump"}]}'

        class FakeRequestPayload:
            model_dump_json = BrokenSignatureDump()

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":482}}'

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
                    "payload": FakeRequestPayload(),
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

        self.assertEqual(output["result"], 482)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"payload": {"value": 482, "items": [{"kind": "json-dump"}]}},
        )

    def test_run_tool_canonical_override_accepts_http_json_request_body_nested_userstring_dump_json(
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
                                "json_body": {
                                    "payload": "$payload",
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

        class FakeRequestPayload:
            def model_dump_json(self) -> UserString:
                return UserString('{"value":487,"items":[{"kind":"json-dump"}]}')

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":487}}'

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
                    "payload": FakeRequestPayload(),
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

        self.assertEqual(output["result"], 487)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"payload": {"value": 487, "items": [{"kind": "json-dump"}]}},
        )

    def test_run_tool_canonical_override_accepts_http_json_query_params_userdict_root(
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
                                "query_params": "$params",
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
                return b'{"data":{"value":453}}'

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
                    "params": UserDict(
                        {
                            "q": "1+2*3",
                            "tag": UserList(["math", "typed"]),
                        }
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

        self.assertEqual(output["result"], 453)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/calc?q=1%2B2%2A3&tag=math&tag=typed",
        )

    def test_run_tool_canonical_override_accepts_http_json_query_params_nested_to_json_list(
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
                                    "q": "$expression",
                                    "tag": "$tags",
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

        class FakeQueryTags:
            def to_json(self) -> str:
                return '["fresh","provider"]'

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":454}}'

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
                    "expression": "margin trend",
                    "tags": FakeQueryTags(),
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

        self.assertEqual(output["result"], 454)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/calc?q=margin+trend&tag=fresh&tag=provider",
        )

    def test_run_tool_canonical_override_accepts_http_json_query_params_nested_dump_json_when_signature_metadata_fails(
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
                                    "q": "$expression",
                                    "tag": "$tags",
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

        class BrokenSignatureDump:
            @property
            def __signature__(self) -> object:
                raise RuntimeError("query signature metadata exploded")

            def __call__(self) -> str:
                return '["fresh","provider"]'

        class FakeQueryTags:
            to_json = BrokenSignatureDump()

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":483}}'

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
                    "expression": "margin trend",
                    "tags": FakeQueryTags(),
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

        self.assertEqual(output["result"], 483)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/calc?q=margin+trend&tag=fresh&tag=provider",
        )

    def test_run_tool_canonical_override_accepts_http_json_query_params_nested_userstring_dump_json(
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
                                    "q": "$expression",
                                    "tag": "$tags",
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

        class FakeQueryTags:
            def to_json(self) -> UserString:
                return UserString('["fresh","provider"]')

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":488}}'

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
                    "expression": "margin trend",
                    "tags": FakeQueryTags(),
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

        self.assertEqual(output["result"], 488)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/calc?q=margin+trend&tag=fresh&tag=provider",
        )

    def test_run_tool_canonical_override_rejects_http_json_query_params_nested_object_without_request(
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
                                    "payload": "$payload",
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

        class FakeQueryPayload:
            def model_dump(self, *args, **kwargs) -> dict[str, object]:
                del args, kwargs
                return {"value": "object-query"}

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("object query param must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "payload": FakeQueryPayload(),
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
        self.assertIn(
            "query_params.payload must be a string, number, boolean, or list",
            str(raised.exception),
        )

    def test_run_tool_canonical_override_accepts_http_json_headers_userdict_root(
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
                                "headers": "$headers",
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
                return b'{"data":{"value":455}}'

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
                    "headers": UserDict(
                        {
                            "Authorization": "Bearer sk-runtime",
                            "X-Provider": "typed-source",
                        }
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

        self.assertEqual(output["result"], 455)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(request.headers["Authorization"], "Bearer sk-runtime")
        self.assertEqual(request.headers["X-provider"], "typed-source")

    def test_run_tool_accepts_http_json_literal_request_field_name_string_wrappers(
        self,
    ) -> None:
        runner = tool_runtime_module._build_tool_runner_from_execution_spec(  # type: ignore[attr-defined]
            execution_spec={
                "kind": "http_json",
                "url": "https://provider.example/calc",
                "method": "POST",
                "headers": {
                    UserString("Content-Type"): "application/json",
                    UserString("X-Provider"): "typed-source",
                },
                "query_params": {
                    UserString("q"): "$expression",
                    UserString("tag"): ["math", "typed"],
                },
                "json_body": {
                    UserString("expression"): "$expression",
                },
                "result_fields": {
                    "result": "$.data.value",
                },
            },
            fallback_runner=lambda *, tool_input, prompt, user_id: {},
            default_timeout_ms=30_000,
        )
        registry_provider = StaticToolRegistryProvider(
            {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="provider_calc",
                    label="Provider Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=30_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=runner,
                    execution_kind="http_json",
                )
            }
        )
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":469}}'

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

        self.assertEqual(output["result"], 469)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/calc?q=1%2B2%2A3&tag=math&tag=typed",
        )
        self.assertEqual(request.headers["X-provider"], "typed-source")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"expression": "1+2*3"},
        )

    def test_run_tool_canonical_override_accepts_http_json_headers_nested_to_json_scalar(
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
                                    "X-Provider": "$provider_header",
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

        class FakeHeaderValue:
            def to_json(self) -> str:
                return '"typed-provider"'

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":456}}'

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
                    "provider_header": FakeHeaderValue(),
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

        self.assertEqual(output["result"], 456)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(request.headers["X-provider"], "typed-provider")

    def test_run_tool_canonical_override_accepts_http_json_headers_nested_dump_json_when_signature_metadata_fails(
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
                                    "X-Provider": "$provider_header",
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

        class BrokenSignatureDump:
            @property
            def __signature__(self) -> object:
                raise RuntimeError("header signature metadata exploded")

            def __call__(self) -> str:
                return '"typed-provider"'

        class FakeHeaderValue:
            to_json = BrokenSignatureDump()

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":484}}'

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
                    "provider_header": FakeHeaderValue(),
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

        self.assertEqual(output["result"], 484)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(request.headers["X-provider"], "typed-provider")

    def test_run_tool_canonical_override_accepts_http_json_headers_nested_userstring_dump_json(
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
                                    "X-Provider": "$provider_header",
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

        class FakeHeaderValue:
            def to_json(self) -> UserString:
                return UserString('"typed-provider"')

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":489}}'

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
                    "provider_header": FakeHeaderValue(),
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

        self.assertEqual(output["result"], 489)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(request.headers["X-provider"], "typed-provider")

    def test_run_tool_canonical_override_rejects_http_json_headers_nested_object_without_request(
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
                                    "X-Provider": "$provider_header",
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

        class FakeHeaderValue:
            def model_dump(self, *args, **kwargs) -> dict[str, object]:
                del args, kwargs
                return {"value": "object-header"}

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                urlopen_calls.append(request)
                or self.fail("object header must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "provider_header": FakeHeaderValue(),
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
        self.assertIn(
            "headers.X-Provider must be a string, number, or boolean",
            str(raised.exception),
        )

    def test_run_tool_canonical_override_accepts_http_json_plus_json_accept_header(
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
                                    "accept": "application/vnd.api+json; charset=utf-8",
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

        self.assertEqual(output["result"], 7)
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_accepts_http_json_plus_json_accept_with_quality(
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
                                    "Accept": "text/html, application/problem+json; q=0.7",
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

        self.assertEqual(output["result"], 7)
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_rejects_rendered_http_json_body_non_finite_without_request(
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
                                "json_body": {
                                    "expression": "$expression",
                                    "score": "$score",
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
                or self.fail("rendered non-finite json_body must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "score": float("nan"),
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
        self.assertIn("json_body.score must be valid JSON", str(raised.exception))

    def test_run_tool_canonical_override_rejects_rendered_http_json_body_unsupported_value_without_request(
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
                                "json_body": {
                                    "expression": "$expression",
                                    "payload": "$payload",
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
                or self.fail("rendered unsupported json_body must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "payload": object(),
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
        self.assertIn("json_body.payload must be valid JSON", str(raised.exception))

    def test_tool_registry_execution_diagnostics_reject_invalid_http_json_response_path_syntax(
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
                                "response_path": "$.data.documents[-1]",
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
                "provider_search: http_json execution response_path must use "
                "dot fields and numeric indexes",
            ),
        )

    def test_run_tool_canonical_override_accepts_http_json_response_path_runtime_template(
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
                                "response_path": "$response_path",
                                "result_fields": {
                                    "result": "$.value",
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
                return b'{"data":{"value":459},"other":{"value":1}}'

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
                tool_input={"response_path": "$.data"},
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

        self.assertEqual(output["result"], 459)
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_rejects_http_json_response_path_runtime_template_invalid_without_request(
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
                                "response_path": "$response_path",
                                "result_fields": {
                                    "result": "$.value",
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
                or self.fail("invalid rendered response_path must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={"response_path": "$.data[]"},
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
        self.assertIn("response_path must use dot fields", str(raised.exception))

    def test_run_tool_canonical_override_accepts_http_json_response_path_interpolation_template(
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
                                "response_path": "$.${scope}",
                                "result_fields": {
                                    "result": "$.value",
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
                return b'{"data":{"value":462},"other":{"value":1}}'

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
                tool_input={"scope": "data"},
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

        self.assertEqual(output["result"], 462)
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_accepts_http_json_response_path_string_wrapper_runtime_template(
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
                                "response_path": "$response_path",
                                "result_fields": {
                                    "result": "$.value",
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
                return b'{"data":{"value":464}}'

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
                tool_input={"response_path": UserString("$.data")},
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

        self.assertEqual(output["result"], 464)
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_accepts_http_json_literal_response_path_string_wrapper(
        self,
    ) -> None:
        runner = tool_runtime_module._build_tool_runner_from_execution_spec(  # type: ignore[attr-defined]
            execution_spec={
                "kind": "http_json",
                "url": "https://provider.example/calc",
                "response_path": UserString("$.data"),
                "result_fields": {
                    "result": "$.value",
                },
            },
            fallback_runner=lambda *, tool_input, prompt, user_id: {},
            default_timeout_ms=30_000,
        )
        registry_provider = StaticToolRegistryProvider(
            {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="provider_calc",
                    label="Provider Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=30_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=runner,
                    execution_kind="http_json",
                )
            }
        )
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":467}}'

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
                tool_input={},
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

        self.assertEqual(output["result"], 467)
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_rejects_http_json_response_path_interpolation_missing_without_request(
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
                                "response_path": "$.${scope}",
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
                or self.fail("missing response_path template must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={},
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
        message = str(raised.exception)
        self.assertIn("missing runtime template variable scope in response_path", message)
        self.assertNotIn(".${scope}", message)

    def test_tool_registry_execution_diagnostics_accept_http_json_response_path_root_template(
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
                                "response_path": "$response_path",
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

    def test_tool_registry_execution_diagnostics_reject_invalid_http_json_result_field_path_syntax(
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
                                    "documents_total": "$.data.documents[]",
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
                "provider_search: http_json execution "
                "result_fields.documents_total must use dot fields and numeric "
                "indexes",
            ),
        )

    def test_run_tool_canonical_override_accepts_http_json_result_fields_root_mapping_template(
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
                                "result_fields": "$fields",
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
                return b'{"data":{"value":460},"meta":{"request_id":"req-460"}}'

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
                    "fields": UserDict(
                        {
                            "result": "$.data.value",
                            "request_id": "$.meta.request_id",
                        }
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

        self.assertEqual(output["result"], 460)
        self.assertEqual(output["request_id"], "req-460")
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_accepts_http_json_result_fields_root_mapping_string_wrappers(
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
                                "result_fields": "$fields",
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
                return b'{"data":{"value":466},"meta":{"request_id":"req-466"}}'

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
                    "fields": UserDict(
                        {
                            UserString("result"): UserString("$.data.value"),
                            "request_id": UserString("$.meta.request_id"),
                        }
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

        self.assertEqual(output["result"], 466)
        self.assertEqual(output["request_id"], "req-466")
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_accepts_http_json_literal_result_fields_string_wrappers(
        self,
    ) -> None:
        runner = tool_runtime_module._build_tool_runner_from_execution_spec(  # type: ignore[attr-defined]
            execution_spec={
                "kind": "http_json",
                "url": "https://provider.example/calc",
                "result_fields": {
                    UserString("result"): UserString("$.data.value"),
                    "request_id": UserString("$.meta.request_id"),
                },
            },
            fallback_runner=lambda *, tool_input, prompt, user_id: {},
            default_timeout_ms=30_000,
        )
        registry_provider = StaticToolRegistryProvider(
            {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="provider_calc",
                    label="Provider Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=30_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=runner,
                    execution_kind="http_json",
                )
            }
        )
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":468},"meta":{"request_id":"req-468"}}'

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
                tool_input={},
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

        self.assertEqual(output["result"], 468)
        self.assertEqual(output["request_id"], "req-468")
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_rejects_http_json_result_fields_root_mapping_string_wrapper_invalid_path_without_request(
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
                                "result_fields": "$fields",
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
                or self.fail("invalid result_fields path wrapper must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "fields": UserDict(
                            {"result": UserString("$.data[]")}
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

        self.assertEqual(urlopen_calls, [])
        self.assertTrue(raised.exception.fatal)
        self.assertIn("result_fields.result must use dot fields", str(raised.exception))

    def test_run_tool_canonical_override_accepts_http_json_result_field_path_runtime_template(
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
                                "result_fields": {
                                    "result": "$result_path",
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
                return b'{"data":{"value":461}}'

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
                tool_input={"result_path": "$.data.value"},
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

        self.assertEqual(output["result"], 461)
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_accepts_http_json_result_field_interpolation_template(
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
                                "result_fields": {
                                    "result": "$.${scope}.value",
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
                return b'{"data":{"value":463}}'

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
                tool_input={"scope": "data"},
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

        self.assertEqual(output["result"], 463)
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_accepts_http_json_result_field_string_wrapper_runtime_template(
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
                                "result_fields": {
                                    "result": "$result_path",
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
                return b'{"data":{"value":465}}'

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
                tool_input={"result_path": UserString("$.data.value")},
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

        self.assertEqual(output["result"], 465)
        self.assertEqual(len(urlopen_calls), 1)

    def test_run_tool_canonical_override_rejects_http_json_result_field_path_runtime_template_invalid_without_request(
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
                                "result_fields": {
                                    "result": "$result_path",
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
                or self.fail("invalid rendered result_fields path must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={"result_path": "$.data[]"},
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
        self.assertIn("result_fields.result must use dot fields", str(raised.exception))

    def test_tool_registry_execution_diagnostics_reject_http_json_mapping_interpolation_unsupported_runtime_template(
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
                                "response_path": "$.${settings_response_scope_typo}",
                                "result_fields": {
                                    "documents_total": "$.${tool_registry_result_scope_typo}.total",
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
                "provider_search: http_json execution references unsupported runtime template variable settings_response_scope_typo in response_path",
                "provider_search: http_json execution references unsupported runtime template variable tool_registry_result_scope_typo in result_fields.documents_total",
            ),
        )

    def test_tool_execution_spec_validation_rejects_http_json_result_fields_mapping_wrapper_unsupported_runtime_template(
        self,
    ) -> None:
        validation_errors = (
            tool_runtime_module._describe_tool_execution_spec_validation_errors(  # type: ignore[attr-defined]
                {
                    "kind": "http_json",
                    "url": "https://provider.example/search",
                    "result_fields": UserDict(
                        {
                            UserString("documents_total"): UserString(
                                "$.${tool_registry_result_scope_typo}.total"
                            ),
                        }
                    ),
                }
            )
        )

        self.assertEqual(
            validation_errors,
            (
                "http_json execution references unsupported runtime template variable tool_registry_result_scope_typo in result_fields.documents_total",
            ),
        )

    def test_tool_execution_spec_validation_rejects_http_json_request_mapping_wrappers_unsupported_runtime_templates(
        self,
    ) -> None:
        validation_errors = (
            tool_runtime_module._describe_tool_execution_spec_validation_errors(  # type: ignore[attr-defined]
                {
                    "kind": "http_json",
                    "url": "https://provider.example/search",
                    "headers": UserDict(
                        {
                            "Authorization": "Bearer ${settings_api_keey}",
                        }
                    ),
                    "query_params": UserDict(
                        {
                            "source": "$tool_registry_provider_sourcee",
                        }
                    ),
                    "json_body": UserDict(
                        {
                            "filters": UserList(
                                [
                                    UserDict(
                                        {
                                            "rank": "$settings_rank_typo",
                                        }
                                    )
                                ]
                            ),
                        }
                    ),
                }
            )
        )

        self.assertEqual(
            validation_errors,
            (
                "http_json execution references unsupported runtime template variable settings_api_keey in headers.Authorization",
                "http_json execution references unsupported runtime template variable tool_registry_provider_sourcee in query_params.source",
                "http_json execution references unsupported runtime template variable settings_rank_typo in json_body.filters[0].rank",
            ),
        )

    def test_tool_execution_spec_validation_accepts_http_json_typed_request_values(
        self,
    ) -> None:
        class HeaderValue:
            def to_json(self) -> UserString:
                return UserString('"typed-provider"')

        class QueryTags:
            def model_dump_json(self) -> UserString:
                return UserString('["fresh","provider"]')

        class BodyPayload:
            def model_dump_json(self) -> UserString:
                return UserString(
                    '{"expression":"1+2*3","filters":[{"kind":"provider"}]}'
                )

        validation_errors = (
            tool_runtime_module._describe_tool_execution_spec_validation_errors(  # type: ignore[attr-defined]
                {
                    "kind": "http_json",
                    "url": "https://provider.example/search",
                    "method": "POST",
                    "headers": UserDict(
                        {
                            UserString("Content-Type"): "application/json",
                            "X-Provider": HeaderValue(),
                        }
                    ),
                    "query_params": UserDict(
                        {
                            UserString("tag"): QueryTags(),
                        }
                    ),
                    "json_body": BodyPayload(),
                }
            )
        )

        self.assertEqual(validation_errors, ())

    def test_tool_execution_spec_validation_accepts_http_json_typed_template_request_values(
        self,
    ) -> None:
        class HeaderValue:
            def model_dump_json(self) -> UserString:
                return UserString('"typed-provider"')

        class QueryTags:
            def to_json(self) -> UserString:
                return UserString('["fresh","provider"]')

        class BodyPayload:
            def to_dict(self) -> UserDict:
                return UserDict(
                    {
                        UserString("expression"): "1+2*3",
                        "tags": UserList(["math", "typed"]),
                    }
                )

        validation_errors = (
            tool_runtime_module._describe_tool_execution_spec_validation_errors(  # type: ignore[attr-defined]
                {
                    "kind": "http_json",
                    "url": "https://provider.example/search",
                    "method": "POST",
                    "headers": {
                        "Content-Type": "application/json",
                        "X-Provider": "$settings_api_key",
                    },
                    "query_params": {
                        "tag": "$tool_registry_provider_source",
                    },
                    "json_body": "$settings_model",
                },
                template_context={
                    "settings_api_key": HeaderValue(),
                    "tool_registry_provider_source": QueryTags(),
                    "settings_model": BodyPayload(),
                },
            )
        )

        self.assertEqual(validation_errors, ())

    def test_tool_execution_spec_validation_accepts_http_json_control_field_string_wrappers(
        self,
    ) -> None:
        validation_errors = (
            tool_runtime_module._describe_tool_execution_spec_validation_errors(  # type: ignore[attr-defined]
                {
                    "kind": UserString("http_json"),
                    "url": UserString("https://provider.example/search"),
                    "method": UserString("POST"),
                    "timeout_ms": UserString("2500"),
                    "headers": {
                        "Content-Type": "application/json",
                    },
                    "json_body": {
                        "query": "$query",
                    },
                }
            )
        )

        self.assertEqual(validation_errors, ())

    def test_tool_execution_spec_validation_accepts_http_json_kind_string_wrapper(
        self,
    ) -> None:
        validation_errors = (
            tool_runtime_module._describe_tool_execution_spec_validation_errors(  # type: ignore[attr-defined]
                {
                    "kind": UserString("http_json"),
                    "url": "https://provider.example/search",
                }
            )
        )

        self.assertEqual(validation_errors, ())

    def test_build_tool_runner_accepts_http_json_kind_string_wrapper(
        self,
    ) -> None:
        runner = tool_runtime_module._build_tool_runner_from_execution_spec(  # type: ignore[attr-defined]
            execution_spec={
                "kind": UserString("http_json"),
                "url": "https://provider.example/calc",
                "result_fields": {
                    "result": "$.data.value",
                },
            },
            fallback_runner=lambda *, tool_input, prompt, user_id: self.fail(
                "http_json kind wrapper must dispatch to the real runner"
            ),
            default_timeout_ms=30_000,
        )
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":488}}'

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

            output = runner(
                tool_input={},
                prompt="calc",
                user_id="user-1",
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["result"], 488)
        self.assertEqual(len(urlopen_calls), 1)

    def test_tool_execution_spec_validation_rejects_http_json_typed_request_value_unsupported_runtime_templates(
        self,
    ) -> None:
        class HeaderMapping:
            def model_dump(self) -> UserDict:
                return UserDict(
                    {
                        UserString("Authorization"): UserString(
                            "Bearer ${settings_api_keey}"
                        ),
                    }
                )

        class QueryMapping:
            def to_dict(self) -> UserDict:
                return UserDict(
                    {
                        UserString("source"): UserString(
                            "$tool_registry_provider_sourcee"
                        ),
                    }
                )

        class BodyPayload:
            def model_dump_json(self) -> UserString:
                return UserString(
                    '{"filters":[{"rank":"$settings_rank_typo"}]}'
                )

        validation_errors = (
            tool_runtime_module._describe_tool_execution_spec_validation_errors(  # type: ignore[attr-defined]
                {
                    "kind": "http_json",
                    "url": "https://provider.example/search",
                    "method": "POST",
                    "headers": HeaderMapping(),
                    "query_params": QueryMapping(),
                    "json_body": BodyPayload(),
                }
            )
        )

        self.assertEqual(
            validation_errors,
            (
                "http_json execution references unsupported runtime template variable settings_api_keey in headers.Authorization",
                "http_json execution references unsupported runtime template variable tool_registry_provider_sourcee in query_params.source",
                "http_json execution references unsupported runtime template variable settings_rank_typo in json_body.filters[0].rank",
            ),
        )

    def test_tool_registry_execution_diagnostics_accept_http_json_mapping_interpolation_templates(
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
                                "response_path": "$.${collection}",
                                "result_fields": {
                                    "documents_total": "$.${meta_scope}.total",
                                    "documents": "$.${collection}.documents",
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

    def test_tool_registry_execution_diagnostics_accept_http_json_result_fields_templates(
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
                                    "documents_total": "$documents_total_path",
                                },
                            },
                        },
                        "provider_search_alt": {
                            "template": "task_retrieve",
                            "label": "Provider Search Alt",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "result_fields": "$fields",
                            },
                        },
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(diagnostics["invalid_tool_executions"], ())

    def test_tool_registry_execution_diagnostics_reject_http_json_response_mapping_unsupported_runtime_templates(
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
                                "response_path": "$settings_response_path_typo",
                                "result_fields": {
                                    "documents_total": "$tool_registry_result_path_typo",
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
                "provider_search: http_json execution references unsupported runtime template variable settings_response_path_typo in response_path",
                "provider_search: http_json execution references unsupported runtime template variable tool_registry_result_path_typo in result_fields.documents_total",
            ),
        )

    def test_run_tool_canonical_override_rejects_invalid_http_json_timeout_without_request(
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
                                "timeout_ms": "slow",
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
                or self.fail("invalid http_json timeout must fail before request")
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
            "timeout_ms must be a positive number",
            str(raised.exception),
        )

    def test_run_tool_canonical_override_accepts_http_json_timeout_runtime_template(
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
                                "timeout_ms": "$timeout_ms",
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
        urlopen_calls: list[tuple[object, object]] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"value":458}}'

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
                name="calc_eval",
                tool_input={"timeout_ms": 2_500},
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

        self.assertEqual(output["result"], 458)
        self.assertEqual(len(urlopen_calls), 1)
        _request, timeout = urlopen_calls[0]
        self.assertEqual(timeout, 2.5)

    def test_run_tool_canonical_override_rejects_http_json_timeout_runtime_template_invalid_without_request(
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
                                "timeout_ms": "$timeout_ms",
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
                or self.fail("invalid rendered timeout must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={"timeout_ms": "slow"},
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
        self.assertIn("timeout_ms must be a positive number", str(raised.exception))

    def test_tool_registry_execution_diagnostics_accept_http_json_timeout_root_template(
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
                                "timeout_ms": "$timeout_ms",
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

    def test_tool_registry_execution_diagnostics_reject_invalid_http_json_timeout(
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
                                "timeout_ms": 0,
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
                "provider_search: http_json execution timeout_ms must be a "
                "positive number of milliseconds",
            ),
        )

    def test_run_tool_canonical_override_rejects_non_finite_http_json_timeout_without_request(
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
                                "timeout_ms": float("inf"),
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
                or self.fail("non-finite http_json timeout must fail before request")
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
            "timeout_ms must be a positive number",
            str(raised.exception),
        )

    def test_tool_registry_execution_diagnostics_reject_non_finite_http_json_timeout(
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
                                "timeout_ms": float("nan"),
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
                "provider_search: http_json execution timeout_ms must be a "
                "positive number of milliseconds",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_oversized_http_json_timeout(
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
                                "timeout_ms": 10**4000,
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
                "provider_search: http_json execution timeout_ms must be a "
                "positive number of milliseconds",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_submillisecond_http_json_timeout(
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
                                "timeout_ms": 0.5,
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
                "provider_search: http_json execution timeout_ms must be a "
                "positive number of milliseconds",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_fractional_http_json_timeout(
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
                                "timeout_ms": 1.5,
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
                "provider_search: http_json execution timeout_ms must be a "
                "positive number of milliseconds",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_invalid_default_timeout(
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
                            "default_timeout_ms": "slow",
                        }
                    }
                ),
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "default_timeout_ms": 0,
                        }
                    }
                ),
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: tool default_timeout_ms must be a positive "
                "number of milliseconds",
                "calc_eval: tool default_timeout_ms must be a positive number "
                "of milliseconds",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_non_finite_default_timeout(
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
                            "default_timeout_ms": float("inf"),
                        }
                    }
                ),
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "default_timeout_ms": float("nan"),
                        }
                    }
                ),
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: tool default_timeout_ms must be a positive "
                "number of milliseconds",
                "calc_eval: tool default_timeout_ms must be a positive number "
                "of milliseconds",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_oversized_default_timeout(
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
                            "default_timeout_ms": 10**4000,
                        }
                    }
                ),
                tool_registry_overrides_json=json.dumps({}),
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: tool default_timeout_ms must be a positive "
                "number of milliseconds",
            ),
        )

    def test_build_tool_registry_extra_tools_from_settings_diagnoses_submillisecond_default_timeout(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "template": "calc_eval",
                        "label": "Fast Calculator",
                        "default_timeout_ms": 0.5,
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

    def test_build_tool_registry_extra_tools_from_settings_diagnoses_fractional_default_timeout(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "template": "calc_eval",
                        "label": "Fast Calculator",
                        "default_timeout_ms": 1.5,
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

    def test_run_tool_canonical_override_rejects_missing_runtime_template_variables_without_partial_http_request(
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
                                "json_body": {
                                    "expression": "$expression",
                                    "precision": "$precision",
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
                {"data": {"value": 7}}
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

        self.assertTrue(raised.exception.fatal)
        self.assertIn(
            "missing runtime template variable precision",
            str(raised.exception),
        )
        self.assertIn("json_body.precision", str(raised.exception))

    def test_run_tool_canonical_override_redacts_sensitive_missing_runtime_template_variable_path(
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
                                "json_body": {
                                    "access_token": "$runtime_access_token",
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
                or self.fail("missing sensitive template variable must fail before request")
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
            "missing runtime template variable [redacted] in json_body.[redacted]",
            str(raised.exception),
        )
        self.assertNotIn("runtime_access_token", str(raised.exception))
        self.assertNotIn("json_body.access_token", str(raised.exception))

    def test_run_tool_canonical_override_rejects_missing_http_json_response_path_without_root_fallback(
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
                                "response_path": "$.data.result",
                                "result_fields": {
                                    "result": "$.value",
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
                {"data": {"value": 7}}
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

        self.assertTrue(raised.exception.fatal)
        self.assertIn("response_path", str(raised.exception))
        self.assertIn("$.data.result", str(raised.exception))

    def test_run_tool_canonical_override_reports_safe_http_json_response_path_payload_shape(
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
                                "response_path": "$.data.result",
                                "result_fields": {
                                    "result": "$.value",
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
                    "meta": {"count": 1},
                    "items": [{"title": "ok"}],
                    "access_token": "upstream-secret",
                }
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
        self.assertTrue(raised.exception.fatal)
        self.assertIn("response_path", message)
        self.assertIn("$.data.result", message)
        self.assertIn("available response keys: meta, items, [redacted]", message)
        self.assertNotIn("access_token", message)
        self.assertNotIn("upstream-secret", message)

    def test_run_tool_canonical_override_reports_response_path_header_hints_safely(
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
                                "response_path": "$.data.result",
                                "result_fields": {
                                    "result": "$.value",
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

        class FakeHttpResponse:
            status = 200
            headers = {
                "Content-Type": "application/json",
                "X-Request-ID": "req-path-1",
                "X-Correlation-ID": "corr-secret=hidden",
                "Location": "https://login.example/callback?token=hidden",
            }

            def read(self) -> bytes:
                return json.dumps({"meta": {"count": 1}, "items": []}).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse()  # type: ignore[attr-defined]

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
        self.assertTrue(raised.exception.fatal)
        self.assertIn("response_path", message)
        self.assertIn("$.data.result", message)
        self.assertIn("request id: req-path-1", message)
        self.assertIn("correlation id: corr-[redacted]", message)
        self.assertNotIn("Location", message)
        self.assertNotIn("login.example", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_limits_http_json_mapping_payload_shape_summary(
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
                                "response_path": "$.data.result",
                                "result_fields": {
                                    "result": "$.value",
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

        class FakeHttpResponse:
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        payload = {
            f"very_long_response_field_{index}_{'x' * 140}": index
            for index in range(8)
        }
        payload["access_token"] = "upstream-secret"

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse(  # type: ignore[attr-defined]
                payload
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
        self.assertTrue(raised.exception.fatal)
        self.assertIn("available response keys:", message)
        self.assertIn("very_long_response_field_0_", message)
        self.assertIn("and 4 more", message)
        self.assertNotIn("access_token", message)
        self.assertNotIn("upstream-secret", message)
        self.assertNotIn("x" * 80, message)
        self.assertLessEqual(len(message), 520)

    def test_run_tool_canonical_override_rejects_http_json_result_fields_when_no_mapping_resolves(
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
                                "result_fields": {
                                    "result": "$.data.value",
                                    "request_id": "$.meta.request_id",
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
                {"status": "ok"}
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

        self.assertTrue(raised.exception.fatal)
        self.assertIn("result_fields", str(raised.exception))
        self.assertIn("result", str(raised.exception))
        self.assertIn("$.data.value", str(raised.exception))

    def test_run_tool_canonical_override_reports_safe_http_json_result_fields_payload_shape(
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
                                "response_path": "$.data",
                                "result_fields": {
                                    "result": "$.answer",
                                    "request_id": "$.request_id",
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
                        "total": 3,
                        "documents": [{"title": "ok"}],
                        "api_key": "upstream-secret",
                    }
                }
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
        self.assertTrue(raised.exception.fatal)
        self.assertIn("result_fields", message)
        self.assertIn("available response keys: total, documents, [redacted]", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("upstream-secret", message)

    def test_run_tool_canonical_override_reports_result_fields_header_hints_safely(
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
                                "response_path": "$.data",
                                "result_fields": {
                                    "result": "$.answer",
                                    "request_id": "$.request_id",
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

        class FakeHttpResponse:
            status = 200
            headers = {
                "Content-Type": "application/json",
                "X-Request-ID": "req-fields-1",
                "X-Correlation-ID": "corr-secret=hidden",
                "Location": "https://login.example/callback?token=hidden",
            }

            def read(self) -> bytes:
                return json.dumps({"data": {"total": 3, "documents": []}}).encode(
                    "utf-8"
                )

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse()  # type: ignore[attr-defined]

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
        self.assertTrue(raised.exception.fatal)
        self.assertIn("result_fields", message)
        self.assertIn("request id: req-fields-1", message)
        self.assertIn("correlation id: corr-[redacted]", message)
        self.assertNotIn("Location", message)
        self.assertNotIn("login.example", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_http_json_result_fields_list_item_payload_shape(
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
                                "response_path": "$.items",
                                "result_fields": {
                                    "result": "$.answer",
                                    "request_id": "$.request_id",
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
                    "items": [
                        {
                            "title": "ok",
                            "score": 0.9,
                            "api_key": "upstream-secret",
                        },
                        {"title": "next"},
                    ]
                }
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
        self.assertTrue(raised.exception.fatal)
        self.assertIn("response payload is a list with 2 items", message)
        self.assertIn("first item keys: title, score, [redacted]", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("upstream-secret", message)

    def test_run_tool_canonical_override_redacts_http_json_mapping_error_paths(
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
                                "response_path": "$.data.token=hidden",
                                "result_fields": {
                                    "api_key": "$.meta.secret=hidden",
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
                {"status": "ok"}
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
        self.assertTrue(raised.exception.fatal)
        self.assertIn("$.data.[redacted]", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("hidden", message)
        self.assertNotIn("token", message)
        self.assertNotIn("api_key", message)

    def test_run_tool_canonical_override_limits_http_json_result_field_mapping_errors(
        self,
    ) -> None:
        result_fields = {
            f"field_{index}": f"$.missing.value_{index}"
            for index in range(12)
        }
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
                                "result_fields": result_fields,
                            },
                        }
                    }
                ),
                tool_registry_extra_tools_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

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
                {"status": "ok"}
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
        self.assertTrue(raised.exception.fatal)
        self.assertIn("result_fields", message)
        self.assertIn("field_0 -> $.missing.value_0", message)
        self.assertIn("and 7 more", message)
        self.assertNotIn("field_11", message)
        self.assertLessEqual(len(message), 420)

    def test_run_tool_canonical_override_redacts_sensitive_http_json_result_field_mapping_names(
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
                                "result_fields": {
                                    "access_token": "$.missing.token",
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
                {"status": "ok"}
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
        self.assertTrue(raised.exception.fatal)
        self.assertIn("[redacted] -> $.missing.[redacted]", message)
        self.assertNotIn("access_token", message)
        self.assertNotIn("token", message)

    def test_run_tool_canonical_override_redacts_sensitive_http_json_result_field_mapping_paths(
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
                                "result_fields": {
                                    "result": "$.meta.api_key",
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
                {"status": "ok"}
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
        self.assertTrue(raised.exception.fatal)
        self.assertIn("result -> $.meta.[redacted]", message)
        self.assertNotIn("api_key", message)

    def test_run_tool_canonical_override_rejects_http_json_result_fields_with_blank_field_name_without_fallback(
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
                                "result_fields": {
                                    " ": "$.data.value",
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

        with self.assertRaises(MockToolExecutionError) as raised:
            run_tool(
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )

        self.assertTrue(raised.exception.fatal)
        self.assertIn(
            "result_fields must include at least one non-empty field name",
            str(raised.exception),
        )

    def test_run_tool_canonical_override_rejects_http_json_mixed_blank_result_field_names_without_fallback(
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
                                "result_fields": {
                                    " ": "$.meta.request_id",
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

        with self.assertRaises(MockToolExecutionError) as raised:
            run_tool(
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )

        self.assertTrue(raised.exception.fatal)
        self.assertIn(
            "result_fields must not include blank field names",
            str(raised.exception),
        )

    def test_run_tool_canonical_override_rejects_http_json_empty_result_fields_without_fallback(
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
                                "result_fields": {},
                            },
                        }
                    }
                ),
                tool_registry_extra_tools_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
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

        self.assertTrue(raised.exception.fatal)
        self.assertIn(
            "result_fields must include at least one field mapping",
            str(raised.exception),
        )

    def test_run_tool_canonical_override_rejects_http_json_blank_response_path_without_fallback(
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
                                "response_path": " ",
                            },
                        }
                    }
                ),
                tool_registry_extra_tools_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
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

        self.assertTrue(raised.exception.fatal)
        self.assertIn(
            "response_path must be a non-empty string when provided",
            str(raised.exception),
        )

    def test_run_tool_canonical_override_rejects_http_json_blank_query_param_field_name_without_fallback(
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
                                    " ": "$expression",
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

        with self.assertRaises(MockToolExecutionError) as raised:
            run_tool(
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )

        self.assertTrue(raised.exception.fatal)
        self.assertIn(
            "query_params must not include blank field names",
            str(raised.exception),
        )
