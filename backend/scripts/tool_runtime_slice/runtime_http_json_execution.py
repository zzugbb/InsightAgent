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

    def test_run_tool_canonical_override_accepts_http_json_problem_json_content_type(
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
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def getheader(self, name: str, default: object = None) -> object:
                return "application/problem+json; charset=utf-8" if name.lower() == "content-type" else default

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

    def test_run_tool_canonical_override_rejects_http_json_non_json_content_type_with_body_preview(
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
            def __init__(self, payload: object) -> None:
                self._payload = json.dumps(payload).encode("utf-8")

            def getheader(self, name: str, default: object = None) -> object:
                return "text/html; charset=utf-8" if name.lower() == "content-type" else default

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
                    "message": "login expired token=hidden",
                    "secret": "hidden",
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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type: text/html", message)
        self.assertIn("login expired", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_bytes_content_type_before_mapping(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                return b"text/html; charset=utf-8" if name.lower() == "content-type" else default

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type: text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_required_default_getheader_content_type(
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
            status = 200

            def getheader(self, name: str, default: object) -> object:
                return "text/html; charset=utf-8" if name.lower() == "content-type" else default

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type: text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_bytes_header_key_content_type_before_mapping(
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
            status = 200
            headers = {b"CONTENT-TYPE": b"text/html; charset=utf-8"}

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type: text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_uses_http_json_headers_when_getheader_fails(
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
            status = 200
            headers = {"Content-Type": "text/html; charset=utf-8"}

            def getheader(self, name: str, default: object = None) -> object:
                raise RuntimeError("adapter getheader failed token=hidden")

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type: text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("getheader failed", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_uses_http_json_header_items_when_get_fails(
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

        class FakeHeaderMapping:
            def get(self, name: str, default: object = None) -> object:
                raise RuntimeError("mapping get failed api_key=hidden")

            def items(self) -> list[tuple[str, str]]:
                return [
                    ("Content-Encoding", "gzip"),
                    ("Content-Type", "application/json"),
                ]

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":610}}')

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

        self.assertEqual(output["result"], 610)

    def test_run_tool_canonical_override_uses_http_json_header_items_after_malformed_entries(
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

        class FakeHeaderMapping:
            def items(self) -> list[object]:
                return [
                    ("malformed",),
                    "also-malformed",
                    ("Content-Type", "text/html; charset=utf-8"),
                ]

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type: text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_uses_http_json_bytes_header_get_candidate(
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

        class FakeHeaderMapping:
            def get(self, name: object, default: object = None) -> object:
                if name == b"content-type":
                    return b"text/html; charset=utf-8"
                return default

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login secret=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type: text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_uses_http_json_info_when_headers_attr_fails(
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
            status = 200

            @property
            def headers(self) -> object:
                raise RuntimeError("headers attr failed secret=hidden")

            def info(self) -> dict[str, str]:
                return {"Content-Type": "text/html; charset=utf-8"}

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type: text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("headers attr failed", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_ignores_http_json_failing_info_without_headers(
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
            status = 200

            def info(self) -> object:
                raise RuntimeError("info failed token=hidden")

            def read(self) -> bytes:
                return b'{"data":{"value":987}}'

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

        self.assertEqual(output["result"], 987)

    def test_run_tool_canonical_override_accepts_http_json_gzip_response_body(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                if name.lower() == "content-encoding":
                    return "gzip"
                if name.lower() == "content-type":
                    return "application/json"
                return default

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":7}}')

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

        self.assertEqual(output["result"], 7)

    def test_run_tool_canonical_override_accepts_http_json_bytes_header_key_gzip_response_body(
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

        class FakeHeaderMapping:
            def items(self) -> list[tuple[bytes, bytes]]:
                return [
                    (b"CONTENT-ENCODING", b"gzip"),
                    (b"CONTENT-TYPE", b"application/json"),
                ]

        class FakeHttpResponse:
            status = 200

            def info(self) -> FakeHeaderMapping:
                return FakeHeaderMapping()

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":377}}')

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

        self.assertEqual(output["result"], 377)

    def test_run_tool_canonical_override_accepts_http_json_required_default_getheader_gzip_response_body(
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
            status = 200

            def getheader(self, name: str, default: object) -> object:
                if name.lower() == "content-encoding":
                    return "gzip"
                if name.lower() == "content-type":
                    return "application/json"
                return default

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":1597}}')

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

        self.assertEqual(output["result"], 1597)

    def test_run_tool_canonical_override_accepts_http_json_gzip_identity_response_body(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                if name.lower() == "content-encoding":
                    return "gzip, identity"
                if name.lower() == "content-type":
                    return "application/json"
                return default

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":9}}')

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

        self.assertEqual(output["result"], 9)

    def test_run_tool_canonical_override_accepts_http_json_deflate_response_body(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                if name.lower() == "content-encoding":
                    return "deflate"
                if name.lower() == "content-type":
                    return "application/json"
                return default

            def read(self) -> bytes:
                return zlib.compress(b'{"data":{"value":8}}')

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

        self.assertEqual(output["result"], 8)

    def test_run_tool_canonical_override_accepts_http_json_raw_deflate_response_body(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                if name.lower() == "content-encoding":
                    return "deflate"
                if name.lower() == "content-type":
                    return "application/json"
                return default

            def read(self) -> bytes:
                compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
                return compressor.compress(b'{"data":{"value":2584}}') + compressor.flush()

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

        self.assertEqual(output["result"], 2584)

    def test_run_tool_canonical_override_rejects_http_json_unsupported_content_encoding(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                if name.lower() == "content-encoding":
                    return b"br"
                if name.lower() == "content-type":
                    return "application/json"
                return default

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("unsupported response content-encoding: br", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_invalid_gzip_body_with_redacted_preview(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                if name.lower() == "content-encoding":
                    return "gzip"
                if name.lower() == "content-type":
                    return "application/json"
                return default

            def read(self) -> bytes:
                return b"not gzip secret=hidden"

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid gzip response body", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_multiple_content_encodings_with_redacted_preview(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                if name.lower() == "content-encoding":
                    return "gzip, br"
                if name.lower() == "content-type":
                    return "application/json"
                return default

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"api_key=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("unsupported response content-encoding: gzip,br", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_http_json_utf16_charset_response_body(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                return "application/json; charset=utf-16" if name.lower() == "content-type" else default

            def read(self) -> bytes:
                return '{"data":{"value":9}}'.encode("utf-16")

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

        self.assertEqual(output["result"], 9)

    def test_run_tool_canonical_override_accepts_http_json_quoted_uppercase_charset_response_body(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                return 'application/json; profile="calc"; charset="UTF-16"' if name.lower() == "content-type" else default

            def read(self) -> bytes:
                return '{"data":{"value":13}}'.encode("utf-16")

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

        self.assertEqual(output["result"], 13)

    def test_run_tool_canonical_override_rejects_http_json_conflicting_charset_parameters(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                if name.lower() == "content-type":
                    return (
                        "application/json; charset=utf-8; "
                        "charset=utf-16; token=hidden"
                    )
                return default

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"secret=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response charset", message)
        self.assertIn("ambiguous response charset", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_http_json_duplicate_same_charset_parameters(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                if name.lower() == "content-type":
                    return "application/json; charset=utf_8; charset=UTF-8"
                return default

            def read(self) -> bytes:
                return b'{"data":{"value":21}}'

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

        self.assertEqual(output["result"], 21)

    def test_run_tool_canonical_override_rejects_http_json_unknown_charset_with_redacted_preview(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                return "application/json; charset=secret=hidden" if name.lower() == "content-type" else default

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response charset", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_unknown_charset_header_hints_safely(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class FakeHttpResponse:
            status = 200
            headers = {
                "Content-Type": "application/json; charset=x-upstream-private",
                "X-Request-ID": "req-charset-1",
                "X-Correlation-ID": "corr-secret=hidden",
                "Location": "https://login.example/callback?token=hidden",
            }

            def read(self) -> bytes:
                return b'{"message":"gateway token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response charset", message)
        self.assertIn("request id: req-charset-1", message)
        self.assertIn("correlation id: corr-[redacted]", message)
        self.assertIn("gateway", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("Location", message)
        self.assertNotIn("login.example", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_http_json_declared_charset_decode_error(
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
            status = 200

            def getheader(self, name: str, default: object = None) -> object:
                return "application/json; charset=utf-16" if name.lower() == "content-type" else default

            def read(self) -> bytes:
                return b"\xff<html>secret=hidden</html>"

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response", message)
        self.assertIn("invalid utf-16 response body", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_charset_decode_header_hints_safely(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class FakeHttpResponse:
            status = 200
            headers = {
                "Content-Type": "application/json; charset=utf-16",
                "X-Request-ID": "req-decode-1",
                "X-Correlation-ID": "corr-secret=hidden",
            }

            def read(self) -> bytes:
                return b"\xff<html>secret=hidden</html>"

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response", message)
        self.assertIn("invalid utf-16 response body", message)
        self.assertIn("request id: req-decode-1", message)
        self.assertIn("correlation id: corr-[redacted]", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_uppercase_content_type_header(
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
            status = 200
            headers = {
                "CONTENT-TYPE": "text/html; token=hidden",
            }

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login api_key=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_http_json_uppercase_content_encoding_header(
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
            status = 200
            headers = {
                "CONTENT-ENCODING": "gzip",
                "CONTENT-TYPE": "application/json",
            }

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":11}}')

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

        self.assertEqual(output["result"], 11)

    def test_run_tool_canonical_override_rejects_http_json_uppercase_info_content_type_header(
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
            status = 200

            def info(self) -> dict[str, str]:
                return {
                    "CONTENT-TYPE": "text/html",
                }

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login secret=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_sequence_content_type_header(
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
            status = 200
            headers = {
                "Content-Type": ["text/html; secret=hidden"],
            }

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_http_json_sequence_content_encoding_header(
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
            status = 200
            headers = {
                "Content-Encoding": (b"gzip",),
                "Content-Type": ("application/json",),
            }

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":12}}')

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

        self.assertEqual(output["result"], 12)

    def test_run_tool_canonical_override_uses_http_json_header_get_default_signature(
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

        class FakeHeaderMapping:
            def get(self, name: object, default: object) -> object:
                if isinstance(name, str) and name.lower() == "content-type":
                    return "text/html; token=hidden"
                return default

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login secret=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_pair_list_content_type_header(
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
            status = 200
            headers = [
                ("malformed",),
                ("Content-Type", "text/html; api_key=hidden"),
            ]

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_http_json_pair_list_content_encoding_header(
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
            status = 200
            headers = (
                (b"Content-Encoding", b"gzip"),
                (b"Content-Type", b"application/json"),
            )

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":341}}')

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

        self.assertEqual(output["result"], 341)

    def test_run_tool_canonical_override_rejects_http_json_info_pair_list_content_type_header(
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
            status = 200

            def info(self) -> list[tuple[str, str]]:
                return [
                    ("Content-Type", "text/html; secret=hidden"),
                ]

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_http_json_raw_items_content_encoding_header(
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

        class FakeHeaderMapping:
            def raw_items(self) -> list[tuple[bytes, bytes]]:
                return [
                    (b"Content-Encoding", b"gzip"),
                    (b"Content-Type", b"application/json"),
                ]

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":677}}')

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

        self.assertEqual(output["result"], 677)

    def test_run_tool_canonical_override_rejects_http_json_multi_items_content_type_header(
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

        class FakeHeaderMapping:
            def multi_items(self) -> list[tuple[str, str]]:
                return [
                    ("Content-Type", "text/html; token=hidden"),
                ]

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login secret=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_info_raw_items_content_type_header(
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

        class FakeInfoHeaders:
            def raw_items(self) -> list[tuple[str, str]]:
                return [
                    ("Content-Type", "text/html; api_key=hidden"),
                ]

        class FakeHttpResponse:
            status = 200

            def info(self) -> FakeInfoHeaders:
                return FakeInfoHeaders()

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_duplicate_pair_list_content_type_header(
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
            status = 200
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Type", "text/html; token=hidden"),
            ]

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login secret=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("application/json, text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_http_json_duplicate_pair_list_content_encoding_header(
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
            status = 200
            headers = [
                ("Content-Encoding", "identity"),
                ("Content-Encoding", "gzip"),
                ("Content-Type", "application/json"),
            ]

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":782}}')

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

        self.assertEqual(output["result"], 782)

    def test_run_tool_canonical_override_rejects_http_json_duplicate_raw_items_content_type_header(
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

        class FakeHeaderMapping:
            def get(self, name: object, default: object = None) -> object:
                if isinstance(name, str) and name.lower() == "content-type":
                    return "application/json"
                return default

            def raw_items(self) -> list[tuple[bytes, bytes]]:
                return [
                    (b"Content-Type", b"application/json"),
                    (b"Content-Type", b"text/html; api_key=hidden"),
                ]

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("application/json, text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_http_json_duplicate_multi_items_content_encoding_header(
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

        class FakeHeaderMapping:
            def multi_items(self) -> list[tuple[str, str]]:
                return [
                    ("Content-Encoding", "identity"),
                    ("Content-Encoding", "gzip"),
                    ("Content-Type", "application/json"),
                ]

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":783}}')

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

        self.assertEqual(output["result"], 783)

    def test_run_tool_canonical_override_rejects_http_json_duplicate_info_content_type_header(
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
            status = 200

            def info(self) -> list[tuple[str, str]]:
                return [
                    ("Content-Type", "application/json"),
                    ("Content-Type", "text/html; secret=hidden"),
                ]

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("application/json, text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_http_json_get_all_duplicate_content_type_header(
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

        class FakeHeaderMapping:
            def get_all(self, name: object, default: object = None) -> object:
                if isinstance(name, str) and name.lower() == "content-type":
                    return ["application/json", "text/html; api_key=hidden"]
                return default

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("application/json, text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_http_json_get_all_duplicate_content_encoding_header(
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

        class FakeHeaderMapping:
            def get_all(self, name: object, default: object = None) -> object:
                if isinstance(name, str) and name.lower() == "content-encoding":
                    return ["identity", "gzip"]
                if isinstance(name, str) and name.lower() == "content-type":
                    return ["application/json"]
                return default

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return gzip.compress(b'{"data":{"value":784}}')

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

        self.assertEqual(output["result"], 784)

    def test_run_tool_canonical_override_rejects_http_json_info_getheaders_duplicate_content_type_header(
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

        class FakeInfoHeaders:
            def getheaders(self, name: object) -> list[str]:
                if isinstance(name, str) and name.lower() == "content-type":
                    return ["application/json", "text/html; secret=hidden"]
                return []

        class FakeHttpResponse:
            status = 200

            def info(self) -> FakeInfoHeaders:
                return FakeInfoHeaders()

            def read(self) -> bytes:
                return b'{"data":{"value":7},"message":"login token=hidden"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("application/json, text/html", message)
        self.assertIn("login", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_accepts_http_json_duplicate_same_content_type_header(
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
            status = 200
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Type", "application/json"),
            ]

            def read(self) -> bytes:
                return b'{"data":{"value":785}}'

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

        self.assertEqual(output["result"], 785)

    def test_run_tool_canonical_override_accepts_http_json_duplicate_json_suffix_content_type_header(
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

        class FakeHeaderMapping:
            def get_all(self, name: object, default: object = None) -> object:
                if isinstance(name, str) and name.lower() == "content-type":
                    return ["application/problem+json", "application/json"]
                return default

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return b'{"data":{"value":786}}'

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

        self.assertEqual(output["result"], 786)

    def test_run_tool_canonical_override_accepts_http_json_duplicate_same_charset_content_type_header(
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

        class FakeInfoHeaders:
            def getheaders(self, name: object) -> list[str]:
                if isinstance(name, str) and name.lower() == "content-type":
                    return [
                        'application/json; charset="UTF-16"',
                        "application/json; charset=utf_16",
                    ]
                return []

        class FakeHttpResponse:
            status = 200

            def info(self) -> FakeInfoHeaders:
                return FakeInfoHeaders()

            def read(self) -> bytes:
                return '{"data":{"value":787}}'.encode("utf-16")

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

        self.assertEqual(output["result"], 787)

    def test_run_tool_canonical_override_rejects_http_json_malformed_charset_content_type_header(
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
            status = 200
            headers = {"Content-Type": "application/json; charset; token=hidden"}

            def read(self) -> bytes:
                return b'{"data":{"value":792},"message":"token=body-secret"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response charset", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token=hidden", message)
        self.assertNotIn("token=body-secret", message)

    def test_run_tool_canonical_override_rejects_http_json_malformed_charset_duplicate_content_type_header(
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

        class FakeHeaderMapping:
            def get_all(self, name: object, default: object = None) -> object:
                if isinstance(name, str) and name.lower() == "content-type":
                    return [
                        "application/json; charset; api_key=hidden",
                        "application/json; charset=utf-8",
                    ]
                return default

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return b'{"data":{"value":793},"message":"api_key=body-secret"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response charset", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("api_key=hidden", message)
        self.assertNotIn("api_key=body-secret", message)

    def test_run_tool_canonical_override_ignores_http_json_quoted_profile_charset_parameter(
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
            status = 200
            headers = {
                "Content-Type": (
                    'application/json; profile="demo;charset=utf-16"; '
                    "charset=utf-8"
                )
            }

            def read(self) -> bytes:
                return b'{"data":{"value":788}}'

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

        self.assertEqual(output["result"], 788)

    def test_run_tool_canonical_override_rejects_http_json_unclosed_quote_content_type_header(
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
            status = 200
            headers = {
                "Content-Type": (
                    'application/json; profile="demo, text/html; token=hidden'
                )
            }

            def read(self) -> bytes:
                return b'{"data":{"value":790},"message":"token=body-secret"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn("application/json; profile=\"demo, text/html", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token=hidden", message)
        self.assertNotIn("token=body-secret", message)

    def test_run_tool_canonical_override_accepts_http_json_quoted_semicolon_duplicate_content_type_header(
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

        class FakeHeaderMapping:
            def get_all(self, name: object, default: object = None) -> object:
                if isinstance(name, str) and name.lower() == "content-type":
                    return [
                        'application/problem+json; profile="a;b,c"',
                        "application/json; charset=utf-8",
                    ]
                return default

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return b'{"data":{"value":789}}'

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

        self.assertEqual(output["result"], 789)

    def test_run_tool_canonical_override_rejects_http_json_unclosed_quote_duplicate_content_type_header(
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

        class FakeHeaderMapping:
            def get_all(self, name: object, default: object = None) -> object:
                if isinstance(name, str) and name.lower() == "content-type":
                    return [
                        'application/problem+json; profile="a;b,c',
                        "application/json; charset=utf-8",
                    ]
                return default

        class FakeHttpResponse:
            status = 200
            headers = FakeHeaderMapping()

            def read(self) -> bytes:
                return b'{"data":{"value":791},"message":"api_key=body-secret"}'

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
        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response content-type", message)
        self.assertIn('application/problem+json; profile="a;b,c', message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("api_key=body-secret", message)

    def test_run_tool_canonical_override_accepts_http_json_string_response_body_from_adapter(
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
            status = 200

            def read(self) -> str:
                return '{"data":{"value":7}}'

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

        self.assertEqual(output["result"], 7)

    def test_run_tool_canonical_override_accepts_http_json_chunked_read_response_body_from_adapter(
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
            status = 200
            headers = {"Content-Type": "application/json"}

            def __init__(self) -> None:
                self._chunks = [
                    b'{"data":',
                    b'{"value":423}}',
                    b"",
                ]

            def read(self, amt: int) -> bytes:
                if amt <= 0:
                    raise AssertionError("chunk size must be positive")
                return self._chunks.pop(0)

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

        self.assertEqual(output["result"], 423)

    def test_run_tool_canonical_override_accepts_http_json_chunked_read_none_eof_response_body_from_adapter(
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
            status = 200
            headers = {"Content-Type": "application/json"}

            def __init__(self) -> None:
                self._chunks = [
                    b'{"data":',
                    b'{"value":432}}',
                    None,
                ]

            def read(self, amt: int) -> bytes | None:
                if amt <= 0:
                    raise AssertionError("chunk size must be positive")
                return self._chunks.pop(0)

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

        self.assertEqual(output["result"], 432)

    def test_run_tool_canonical_override_falls_back_http_json_content_attr_when_chunked_read_returns_empty_body(
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
            status = 200
            headers = {"Content-Type": "application/json"}
            content = b'{"data":{"value":479}}'

            def read(self, amt: int | None = None) -> bytes:
                if amt is None:
                    raise TypeError("chunk size is required")
                if amt <= 0:
                    raise AssertionError("chunk size must be positive")
                return b""

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

        self.assertEqual(output["result"], 479)

    def test_run_tool_canonical_override_falls_back_http_json_json_method_when_chunked_read_returns_empty_body(
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
            status = 200
            headers = {"Content-Type": "application/json"}

            def read(self, amt: int | None = None) -> bytes:
                if amt is None:
                    raise TypeError("chunk size is required")
                if amt <= 0:
                    raise AssertionError("chunk size must be positive")
                return b""

            def json(self) -> dict[str, object]:
                return {"data": {"value": 480}}

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

        self.assertEqual(output["result"], 480)

    def test_run_tool_canonical_override_falls_back_http_json_content_attr_when_read_returns_empty_body(
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
            status = 200
            headers = {"Content-Type": "application/json"}
            content = b'{"data":{"value":477}}'

            def read(self) -> bytes:
                return b""

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

        self.assertEqual(output["result"], 477)

    def test_run_tool_canonical_override_accepts_http_json_chunked_read_when_default_read_returns_empty_body(
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
            status = 200
            headers = {"Content-Type": "application/json"}

            def __init__(self) -> None:
                self._chunks = [
                    b'{"data":',
                    b'{"value":487}}',
                    b"",
                ]

            def read(self, amt: int | None = None) -> bytes:
                if amt is None:
                    return b""
                if amt <= 0:
                    raise AssertionError("chunk size must be positive")
                return self._chunks.pop(0)

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

        self.assertEqual(output["result"], 487)

    def test_run_tool_canonical_override_accepts_http_json_chunked_read_when_default_text_read_returns_empty_body(
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
            status = 200
            headers = {"Content-Type": "application/json"}

            def __init__(self) -> None:
                self._chunks = [
                    '{"data":',
                    '{"value":488}}',
                    "",
                ]

            def read(self, amt: int | None = None) -> str:
                if amt is None:
                    return ""
                if amt <= 0:
                    raise AssertionError("chunk size must be positive")
                return self._chunks.pop(0)

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

        self.assertEqual(output["result"], 488)

    def test_run_tool_canonical_override_keeps_http_json_chunked_read_bad_chunk_fatal_after_body_started(
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
            status = 200
            headers = {"Content-Type": "application/json"}
            content = b'{"data":{"value":489}}'

            def __init__(self) -> None:
                self._chunks: list[object] = [
                    b'{"data":',
                    object(),
                ]

            def read(self, amt: int | None = None) -> object:
                if amt is None:
                    raise TypeError("chunk size is required")
                if amt <= 0:
                    raise AssertionError("chunk size must be positive")
                return self._chunks.pop(0)

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

        self.assertIn("response body must be bytes or text", str(raised.exception))

    def test_run_tool_canonical_override_keeps_http_json_chunked_read_runtime_error_fatal_after_body_started(
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
            status = 200
            headers = {"Content-Type": "application/json"}
            content = b'{"data":{"value":490}}'

            def __init__(self) -> None:
                self._chunks = [b'{"data":']

            def read(self, amt: int | None = None) -> bytes:
                if amt is None:
                    raise TypeError("chunk size is required")
                if amt <= 0:
                    raise AssertionError("chunk size must be positive")
                if self._chunks:
                    return self._chunks.pop(0)
                raise RuntimeError("upstream stream broke")

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

        self.assertIn(
            "response read failed: upstream stream broke",
            str(raised.exception),
        )

    def test_run_tool_canonical_override_falls_back_http_json_json_method_when_read_returns_empty_body(
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
            status = 200
            headers = {"Content-Type": "application/json"}

            def read(self) -> str:
                return ""

            def json(self) -> dict[str, object]:
                return {"data": {"value": 478}}

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

        self.assertEqual(output["result"], 478)

    def test_run_tool_canonical_override_accepts_http_json_content_attr_response_body_from_adapter(
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
            status = 200
            headers = {"Content-Type": "application/json"}
            content = b'{"data":{"value":421}}'

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

        self.assertEqual(output["result"], 421)

    def test_run_tool_canonical_override_falls_back_http_json_body_attr_when_content_attr_is_empty(
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
            status = 200
            headers = {"Content-Type": "application/json"}
            content = b""
            body = b'{"data":{"value":484}}'

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

        self.assertEqual(output["result"], 484)

    def test_run_tool_canonical_override_falls_back_http_json_data_attr_when_body_attr_is_empty(
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
            status = 200
            headers = {"Content-Type": "application/json"}
            body = ""
            data = {"data": {"value": 485}}

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

        self.assertEqual(output["result"], 485)

    def test_run_tool_canonical_override_falls_back_http_json_json_method_when_text_attr_is_empty(
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
            status = 200
            headers = {"Content-Type": "application/json"}
            text = ""

            def json(self) -> dict[str, object]:
                return {"data": {"value": 486}}

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

        self.assertEqual(output["result"], 486)

    def test_run_tool_canonical_override_falls_back_http_json_body_attr_when_content_attr_unavailable(
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
            status = 200
            headers = {"Content-Type": "application/json"}
            content = object()
            body = b'{"data":{"value":471}}'

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

        self.assertEqual(output["result"], 471)

    def test_run_tool_canonical_override_keeps_http_json_body_attr_error_when_iterable_is_empty(
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
            status = 200
            headers = {"Content-Type": "application/json"}
            content = object()

            def __iter__(self):
                if False:
                    yield b"unreachable"

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
        self.assertIn("transport error", message)
        self.assertIn("response body must be bytes or text", message)
        self.assertNotIn("empty JSON response", message)

    def test_run_tool_canonical_override_falls_back_http_json_data_attr_when_body_attr_unavailable(
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
            status = 200
            headers = {"Content-Type": "application/json"}
            body = object()
            data = {"data": {"value": 472}}

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

        self.assertEqual(output["result"], 472)

    def test_execute_tool_plan_item_service_execution_honors_custom_preview_policy(
        self,
    ) -> None:
        registry = {
            "custom_lookup": ToolRegistration(
                name="custom_lookup",
                kind="custom_lookup",
                label="Custom Lookup",
                retryable_by_default=False,
                default_timeout_ms=12_000,
                requires_user_context=False,
                supports_result_preview=False,
                runner=lambda *, tool_input, prompt, user_id: {
                    "documents": [{"title": "Secret"}],
                    "tool_kind": "custom_lookup",
                },
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="custom_lookup",
            tool_input={"query": "secret"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Custom Lookup",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="custom_lookup",
                tool_input={"query": "secret"},
                prompt="lookup",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        self.assertEqual(tool_end_event["latency_ms"], 48)
        self.assertIsNone(tool_end_event["output_preview"])

    def test_execute_tool_plan_item_service_execution_applies_custom_preview_keys(
        self,
    ) -> None:
        registry = {
            "task_retrieve_hot": ToolRegistration(
                name="task_retrieve_hot",
                kind="knowledge_retrieval",
                label="Hot Retrieval",
                retryable_by_default=True,
                default_timeout_ms=5_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "knowledge_retrieval",
                    "chunks": ["alpha", "beta"],
                    "hit_count": 2,
                    "knowledge_base_id": "demo-kb",
                    "raw_documents": [{"id": "doc-1"}],
                },
                result_preview_keys=("tool_kind", "hit_count", "knowledge_base_id"),
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_retrieve_hot",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Hot Retrieval",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="task_retrieve_hot",
                tool_input={"query": "demo"},
                prompt="retrieve demo",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "tool_kind": "knowledge_retrieval",
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_keeps_rag_followup_for_projected_retrieval_output(
        self,
    ) -> None:
        registry = {
            "task_retrieve_hot": ToolRegistration(
                name="task_retrieve_hot",
                kind="knowledge_retrieval",
                label="Hot Retrieval",
                retryable_by_default=True,
                default_timeout_ms=5_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "knowledge_retrieval",
                    "chunks": ["alpha", "beta"],
                    "hit_count": 2,
                    "knowledge_base_id": "demo-kb",
                    "raw_documents": [{"id": "doc-1"}],
                },
                result_preview_keys=("hit_count", "knowledge_base_id"),
                result_output_keys=("hit_count", "knowledge_base_id"),
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_retrieve_hot",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Hot Retrieval",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="task_retrieve_hot",
                tool_input={"query": "demo"},
                prompt="retrieve demo",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )
        self.assertEqual(
            [
                (item["kind"], item.get("trace_step", {}).get("id"))
                for item in final_item["result"]["service_actions"]
            ],
            [("trace_write", "step-1"), ("trace_write", "rag-1"), ("continue", None)],
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha", "beta"],
                "knowledge_base_id": "demo-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_uses_runtime_semantic_override_for_real_search_tool(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "documents_total": 2,
                    "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                    "chunks": ["internal retrieval stub"],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_start_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_start"
        )
        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(tool_start_event["semantic_kind"], "provider_search")
        self.assertEqual(tool_end_event["semantic_kind"], "provider_search")
        self.assertEqual(
            tool_start_event["semantic_family"],
            "knowledge_retrieval",
        )
        self.assertEqual(
            tool_end_event["semantic_family"],
            "knowledge_retrieval",
        )
        self.assertEqual(
            tool_start_event["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(
            tool_end_event["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            tool_end_event["output"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 2 documents.",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["loop_result"]["next_action_step"]["meta"]["tool"]["output"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["loop_result"]["next_action_step"]["meta"]["tool"]["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["loop_result"]["next_action_step"]["meta"]["tool"]["semantic_family"],
            "knowledge_retrieval",
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["internal retrieval stub"],
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            [
                (item["kind"], item.get("trace_step", {}).get("id"))
                for item in final_item["result"]["service_actions"]
            ],
            [("trace_write", "step-1"), ("trace_write", "rag-1"), ("continue", None)],
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_documents_for_real_search_tool(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "documents_total": 2,
                    "documents": [
                        {"snippet": "alpha snippet"},
                        {"content": "beta content"},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha snippet", "beta content"],
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            [
                (item["kind"], item.get("trace_step", {}).get("id"))
                for item in final_item["result"]["service_actions"]
            ],
            [("trace_write", "step-1"), ("trace_write", "rag-1"), ("continue", None)],
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_items_for_real_search_tool(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "documents_total": 2,
                    "items": [
                        {"snippet": "alpha item snippet"},
                        {"content": "beta item content"},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha item snippet", "beta item content"],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_data_camel_case_text_fields(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "data": [
                        {"documentText": "alpha document text"},
                        {"payload": {"pageContent": "beta page content"}},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "incident timeline"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "incident timeline"},
                prompt="search incident timeline",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha document text", "beta page content"],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_records_text_aliases(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "records": [
                        {"chunkText": "alpha chunk text"},
                        {"passage": "beta passage"},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "capacity plan"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "capacity plan"},
                prompt="search capacity plan",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha chunk text", "beta passage"],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_camel_text_aliases(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "results": [
                        {"snippetText": "alpha snippet text"},
                        {"payload": {"contentText": "beta content text"}},
                        {"metadata": {"textContent": "gamma text content"}},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "incident evidence"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "incident evidence"},
                prompt="search incident evidence",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 3,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": [
                    "alpha snippet text",
                    "beta content text",
                    "gamma text content",
                ],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_attribute_containers(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "results": [
                        {"attributes": {"snippetText": "alpha attribute snippet"}},
                        {"source": {"contentText": "beta source content"}},
                        {"fields": {"textContent": "gamma fields text"}},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "incident evidence"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "incident evidence"},
                prompt="search incident evidence",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 3,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": [
                    "alpha attribute snippet",
                    "beta source content",
                    "gamma fields text",
                ],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_rewrites_real_search_tool_kind_to_runtime_semantic_kind(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "documents_total": 2,
                    "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                    "chunks": ["internal retrieval stub"],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("tool_kind", "documents_total"),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "tool_kind": "provider_search",
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"]["tool_kind"],
            "provider_search",
        )

    def test_execute_tool_plan_item_service_execution_falls_back_result_output_keys_to_preview_keys_for_runtime_override_real_search_tool(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "documents_total": 2,
                    "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                    "chunks": ["internal retrieval stub"],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_start_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_start"
        )
        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_start_event["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(
            tool_end_event["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["loop_result"]["next_action_step"]["meta"]["tool"]["output"],
            {
                "documents_total": 2,
            },
        )

    def test_execute_tool_plan_item_service_execution_infers_preview_and_output_keys_from_semantic_family_for_runtime_override_real_search_tool(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "hit_count": 2,
                    "knowledge_base_id": "provider-kb",
                    "chunks": ["internal retrieval stub"],
                    "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_start_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_start"
        )
        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_start_event["effective_result_preview_keys"],
            ["documents_total", "hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            tool_end_event["effective_result_preview_keys"],
            ["documents_total", "hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            tool_start_event["effective_result_output_keys"],
            ["documents_total", "hit_count", "knowledge_base_id", "request_id"],
        )
        self.assertEqual(
            tool_end_event["effective_result_output_keys"],
            ["documents_total", "hit_count", "knowledge_base_id", "request_id"],
        )
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 2 hits.",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["loop_result"]["next_action_step"]["meta"]["tool"]["output"],
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_preserves_request_id_in_hit_projection_summary_for_runtime_override_real_search_tool(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "hit_count": 2,
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-1",
                    "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["result_summary"],
            "Retrieved 2 hits (request id req-1).",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 2 hits (request id req-1).",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-1",
            },
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_preview_for_runtime_override_real_search_tool(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "documents_total": 2,
                    "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                    "request_id": "req-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_start_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_start"
        )
        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_start_event["effective_result_preview_keys"],
            ["documents_total", "hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            tool_end_event["effective_result_preview_keys"],
            ["documents_total", "hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
                "request_id": "req-1",
            },
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_from_provider_total_count(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "total_count": "2",
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-total-count-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-total-count-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 2 documents from provider-kb (request id req-total-count-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_calc_result_from_provider_value(
        self,
    ) -> None:
        registry = {
            "provider_math": ToolRegistration(
                name="provider_math",
                kind="provider_calc",
                label="Provider Calculator",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_calc",
                    "expression": "3+4",
                    "value": "7",
                    "request_id": "req-value-1",
                },
                runtime_semantic_kind="provider_math",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_math",
            tool_input={"expression": "3+4"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Calculator",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_math",
                tool_input={"expression": "3+4"},
                prompt="calculate 3+4",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "expression": "3+4",
                "result": "7",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "expression": "3+4",
                "result": "7",
                "request_id": "req-value-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Calculator: Calculated 3+4 = 7 (request id req-value-1).",
        )

    def test_execute_tool_plan_item_service_execution_normalizes_provider_request_id_aliases(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "documents_total": 1,
                    "knowledge_base_id": "provider-kb",
                    "requestId": "req-camel-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "latency"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "latency"},
                prompt="search latency",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]

        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 1,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-camel-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 1 document from provider-kb (request id req-camel-1).",
        )

    def test_execute_tool_plan_item_service_execution_normalizes_provider_trace_id_alias(
        self,
    ) -> None:
        registry = {
            "provider_math": ToolRegistration(
                name="provider_math",
                kind="provider_calc",
                label="Provider Calculator",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_calc",
                    "expression": "10-3",
                    "answer": 7,
                    "trace_id": "trace-7",
                },
                runtime_semantic_kind="provider_math",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_math",
            tool_input={"expression": "10-3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Calculator",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_math",
                tool_input={"expression": "10-3"},
                prompt="calculate 10-3",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]

        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "expression": "10-3",
                "result": 7,
                "request_id": "trace-7",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Calculator: Calculated 10-3 = 7 (request id trace-7).",
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_from_provider_total_count_camel_case(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "totalCount": 3,
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-total-count-camel-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "throughput"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "throughput"},
                prompt="search throughput",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]

        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 3,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-total-count-camel-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 3 documents from provider-kb (request id req-total-count-camel-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_calc_result_from_provider_computed_value(
        self,
    ) -> None:
        registry = {
            "provider_math": ToolRegistration(
                name="provider_math",
                kind="provider_calc",
                label="Provider Calculator",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_calc",
                    "expression": "6*7",
                    "computedValue": 42,
                    "request_id": "req-computed-1",
                },
                runtime_semantic_kind="provider_math",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_math",
            tool_input={"expression": "6*7"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Calculator",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_math",
                tool_input={"expression": "6*7"},
                prompt="calculate 6*7",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]

        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "expression": "6*7",
                "result": 42,
                "request_id": "req-computed-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Calculator: Calculated 6*7 = 42 (request id req-computed-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_from_provider_documents_total_camel_case(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "documentsTotal": 4,
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-documents-total-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "availability"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "availability"},
                prompt="search availability",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]

        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 4,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-documents-total-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 4 documents from provider-kb (request id req-documents-total-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_from_provider_records_total_alias(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "recordsTotal": "8",
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-records-total-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "records"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "records"},
                prompt="search records",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 8,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 8,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-records-total-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 8 documents from provider-kb (request id req-records-total-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_from_provider_doc_count_alias(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "docCount": "10",
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-doc-count-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "documents"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "documents"},
                prompt="search documents",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 10,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 10,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-doc-count-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 10 documents from provider-kb (request id req-doc-count-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_hit_count_from_provider_hit_count_camel_case(
        self,
    ) -> None:
        registry = {
            "provider_search": ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                result_preview_keys=("hit_count", "knowledge_base_id"),
                result_output_keys=("hit_count", "knowledge_base_id", "request_id"),
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "hitCount": 5,
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-hit-count-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "queue depth"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "queue depth"},
                prompt="search queue depth",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "hit_count": 5,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "hit_count": 5,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-hit-count-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 5 hits (request id req-hit-count-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_label_only_real_search_tool_semantics(
        self,
    ) -> None:
        registry = {
            "hosted_search_gateway": ToolRegistration(
                name="hosted_search_gateway",
                kind=None,
                label="Hosted Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "documents_total": 2,
                    "documents": [
                        {"snippet": "alpha snippet"},
                        {"content": "beta content"},
                    ],
                    "knowledge_base_id": "hosted-kb",
                    "request_id": "req-hosted-1",
                },
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="hosted_search_gateway",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Hosted Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="hosted_search_gateway",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_start_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_start"
        )
        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(tool_start_event["semantic_kind"], "hosted_search_gateway")
        self.assertEqual(tool_start_event["semantic_family"], "knowledge_retrieval")
        self.assertEqual(
            tool_end_event["output"],
            {
                "documents_total": 2,
                "knowledge_base_id": "hosted-kb",
                "request_id": "req-hosted-1",
            },
        )
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 2,
                "knowledge_base_id": "hosted-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Hosted Search: Retrieved 2 documents from hosted-kb (request id req-hosted-1).",
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(rag_followup["step"]["content"], "Hosted Search returned snippets.")
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha snippet", "beta content"],
                "knowledge_base_id": "hosted-kb",
            },
        )

    def test_build_tool_result_summary_does_not_imply_local_kb_for_runtime_override_real_tool_with_hit_projection(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            result_preview_keys=("hit_count", "knowledge_base_id"),
            result_output_keys=("hit_count", "knowledge_base_id"),
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "tool_kind": "provider_retrieval",
            },
        )

        output = {
            "hit_count": 2,
            "knowledge_base_id": "provider-kb",
            "tool_kind": "provider_retrieval",
        }

        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 hits.",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search: Retrieved 2 hits.",
        )

    def test_execute_tool_plan_item_service_actions_keeps_continue_shape(self) -> None:
        trace_steps = [{"id": "existing-1", "seq": 2, "content": "Existing"}]
        tool_observations: list[str] = []
        persist_forces: list[bool] = []
        complete_calls: list[dict[str, object]] = []
        failure_calls: list[dict[str, object]] = []
        service_actions = [
            {
                "kind": "trace_write",
                "trace_step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                },
                "persist_force": False,
            },
            {
                "kind": "continue",
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
        ]

        items = list(
            execute_tool_plan_item_service_actions(
                service_actions=service_actions,
                trace_steps=trace_steps,
                tool_observations=tool_observations,
                seq_cursor=3,
                persist_trace_fn=lambda *, force: persist_forces.append(bool(force)),
                complete_task_fn=lambda **kwargs: complete_calls.append(kwargs),
                record_failure_event_fn=lambda **kwargs: failure_calls.append(kwargs),
            )
        )

        self.assertEqual([item["kind"] for item in items], ["event", "result"])
        self.assertEqual(items[0]["event"], "trace")
        self.assertEqual(items[0]["data"]["step_id"], "step-1")
        self.assertEqual(items[1]["result"], {"seq_cursor": 4, "should_return": False})
        self.assertEqual([step["id"] for step in trace_steps], ["existing-1", "step-1"])
        self.assertEqual(tool_observations, ['mock_retrieve: {"chunks": ["alpha"]}'])
        self.assertEqual(persist_forces, [False])
        self.assertEqual(complete_calls, [])
        self.assertEqual(failure_calls, [])

    def test_execute_tool_plan_item_service_actions_redacts_raw_diagnostics(
        self,
    ) -> None:
        trace_steps = [{"id": "existing-1", "seq": 2, "content": "Existing"}]
        tool_observations: list[str] = []
        persist_forces: list[bool] = []
        complete_calls: list[dict[str, object]] = []
        failure_calls: list[dict[str, object]] = []
        service_actions = [
            {
                "kind": "trace_write",
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": (
                        "provider_search: unsupported tool execution kind api_key=hidden"
                    ),
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": (
                            "provider_search: http_json execution query_params.access_token must be safe"
                        ),
                    },
                },
                "persist_force": True,
            },
            {
                "kind": "continue",
                "tool_observations": [
                    "provider_search: unsupported tool execution kind token=hidden",
                ],
                "seq_increment": 1,
            },
            {
                "kind": "record_failure_event",
                "kwargs": {
                    "event_type": "task_failed",
                    "code": "tool_execution_error",
                    "message": "provider_search failed with secret=hidden",
                    "detail": {
                        "reason": (
                            "provider_search: http_json execution headers.x-api-key must be safe"
                        ),
                    },
                },
            },
            {
                "kind": "emit_state",
                "event": "state",
                "data": {
                    "task_id": "task-1",
                    "phase": "error",
                    "detail": (
                        "provider_search: http_json execution json_body.client_secret must be safe"
                    ),
                },
            },
        ]

        items = list(
            execute_tool_plan_item_service_actions(
                service_actions=service_actions,
                trace_steps=trace_steps,
                tool_observations=tool_observations,
                seq_cursor=3,
                persist_trace_fn=lambda *, force: persist_forces.append(bool(force)),
                complete_task_fn=lambda **kwargs: complete_calls.append(kwargs),
                record_failure_event_fn=lambda **kwargs: failure_calls.append(kwargs),
            )
        )

        serialized = json.dumps(
            {
                "items": items,
                "trace_steps": trace_steps,
                "tool_observations": tool_observations,
                "failure_calls": failure_calls,
            },
            default=str,
        )
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("secret=hidden", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)
        self.assertEqual(persist_forces, [True])
        self.assertEqual(complete_calls, [])
