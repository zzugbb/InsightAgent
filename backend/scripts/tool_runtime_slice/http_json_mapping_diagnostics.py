from __future__ import annotations

from .context import *


class HttpJsonMappingDiagnosticsMixin:
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
