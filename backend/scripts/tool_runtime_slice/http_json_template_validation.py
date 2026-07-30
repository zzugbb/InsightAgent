from __future__ import annotations

from .context import *


class HttpJsonTemplateValidationMixin:
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
