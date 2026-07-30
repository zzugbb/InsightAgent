from __future__ import annotations

from .context import *


class RuntimeHttpJsonExecutionMixin:
    def test_run_tool_canonical_override_supports_http_json_execution(self) -> None:
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
                                },
                                "result_fields": {
                                    "result": "$.data.value",
                                    "request_id": "$.meta.request_id",
                                },
                            },
                            "result_preview_keys": ["result"],
                            "result_output_keys": ["result", "request_id"],
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
                        "meta": {"request_id": "req-calc-1"},
                        "data": {"value": 7},
                    }
                )
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

        self.assertEqual(len(urlopen_calls), 1)
        request, timeout = urlopen_calls[0]
        self.assertEqual(timeout, 3.0)
        self.assertEqual(request.full_url, "https://provider.example/calc")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"expression": "1+2*3"},
        )
        self.assertEqual(
            output,
            {
                "result": 7,
                "request_id": "req-calc-1",
                "tool_kind": "provider_calc",
            },
        )

    def test_run_tool_canonical_override_inherits_http_json_header_request_id_for_success_output(
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
            headers = {
                "Content-Type": "application/json",
                "X-Request-ID": "req-header-1",
            }

            def read(self) -> bytes:
                return b'{"data":{"value":7}}'

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse()  # type: ignore[attr-defined]

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

        self.assertEqual(
            output,
            {
                "result": 7,
                "request_id": "req-header-1",
                "tool_kind": "provider_calc",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="calc_eval",
                output=output,
                registration=registry_provider.load_tool_registry()["calc_eval"],
            ),
            "Calculated result = 7 (request id req-header-1).",
        )

    def test_run_tool_canonical_override_does_not_inherit_sensitive_http_json_header_request_id_for_success_output(
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
            headers = {
                "Content-Type": "application/json",
                "X-Request-ID": "req-secret=hidden",
            }

            def read(self) -> bytes:
                return b'{"data":{"value":7}}'

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse()  # type: ignore[attr-defined]

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

        self.assertEqual(
            output,
            {
                "result": 7,
                "tool_kind": "provider_calc",
            },
        )

    def test_run_tool_canonical_override_prefers_safe_http_json_header_request_id_over_sensitive_body_request_id(
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
                                    "request_id": "$.data.request_id",
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
            headers = {
                "Content-Type": "application/json",
                "X-Request-ID": "req-header-safe-1",
            }

            def read(self) -> bytes:
                return b'{"data":{"value":7,"request_id":"token=hidden"}}'

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse()  # type: ignore[attr-defined]

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

        self.assertEqual(
            output,
            {
                "result": 7,
                "request_id": "req-header-safe-1",
                "tool_kind": "provider_calc",
            },
        )
        self.assertNotIn("token=", json.dumps(output))

    def test_run_tool_canonical_override_drops_sensitive_http_json_body_request_id_without_safe_header(
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
                                    "request_id": "$.data.request_id",
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
            headers = {
                "Content-Type": "application/json",
            }

            def read(self) -> bytes:
                return b'{"data":{"value":7,"request_id":"api_key=hidden"}}'

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse()  # type: ignore[attr-defined]

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

        self.assertEqual(
            output,
            {
                "result": 7,
                "tool_kind": "provider_calc",
            },
        )
        self.assertNotIn("api_key", json.dumps(output))

    def test_run_tool_canonical_override_redacts_http_json_success_payload_sensitive_diagnostic_keys(
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
            headers = {
                "Content-Type": "application/json",
            }

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "data": {
                            "value": 7,
                            "response_path=$.data.access_token": "missing",
                            (
                                "callback https://provider.example/cb?"
                                "access_token=secret-token"
                            ): "bad",
                            "nested": {
                                "response_path=$['data']['client_secret']": "missing"
                            },
                        }
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

        output_json = json.dumps(output)
        self.assertEqual(output["value"], 7)
        self.assertEqual(output["[redacted]"], "[redacted]")
        self.assertEqual(output["nested"]["[redacted]"], "[redacted]")
        self.assertNotIn("response_path=$.data.access_token", output_json)
        self.assertNotIn("response_path=$['data']['client_secret']", output_json)
        self.assertNotIn("access_token", output_json)
        self.assertNotIn("client_secret", output_json)
        self.assertNotIn("secret-token", output_json)

    def test_run_tool_canonical_override_rejects_bearer_like_http_json_body_request_id(
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
                                    "request_id": "$.data.request_id",
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
            headers = {
                "Content-Type": "application/json",
                "X-Request-ID": "req-header-safe-2",
            }

            def read(self) -> bytes:
                return b'{"data":{"value":7,"request_id":"Bearer secret-token"}}'

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = lambda request, timeout=0: FakeHttpResponse()  # type: ignore[attr-defined]

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

        self.assertEqual(
            output,
            {
                "result": 7,
                "request_id": "req-header-safe-2",
                "tool_kind": "provider_calc",
            },
        )
        self.assertNotIn("Bearer", json.dumps(output))
