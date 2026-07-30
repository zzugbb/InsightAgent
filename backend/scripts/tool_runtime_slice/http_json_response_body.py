from __future__ import annotations

from .context import *


class HttpJsonResponseBodyMixin:
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
