from __future__ import annotations

from .context import *


class HttpJsonErrorHandlingMixinPart2:
    def test_run_tool_canonical_override_reports_http_json_http_error_status_and_body(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    429,
                    "Too Many Requests",
                    hdrs=None,
                    fp=io.BytesIO(b'{"error":"rate limited","secret":"hidden"}'),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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

        self.assertFalse(raised.exception.fatal)
        self.assertIn("HTTP 429", str(raised.exception))
        self.assertIn("Too Many Requests", str(raised.exception))
        self.assertIn("rate limited", str(raised.exception))
        self.assertIn("[redacted]", str(raised.exception))
        self.assertNotIn("hidden", str(raised.exception))
        self.assertNotIn("secret", str(raised.exception))

    def test_run_tool_canonical_override_reports_http_json_http_error_read_failure_safely(
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

        class FailingBody:
            def read(self) -> bytes:
                raise RuntimeError("http error body read failed token=hidden")

            def close(self) -> None:
                return None

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    429,
                    "Too Many Requests secret=hidden",
                    hdrs=None,
                    fp=FailingBody(),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 429", message)
        self.assertIn("Too Many Requests", message)
        self.assertIn("response read failed", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_http_json_compressed_http_error_body(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    429,
                    "Too Many Requests",
                    hdrs={
                        "Content-Encoding": "gzip",
                        "Content-Type": "application/json",
                    },
                    fp=io.BytesIO(
                        gzip.compress(
                            b'{"message":"rate limited token=hidden","secret":"hidden"}'
                        )
                    ),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 429", message)
        self.assertIn("Too Many Requests", message)
        self.assertIn("rate limited", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_http_json_http_error_body_with_declared_charset(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()
        error_body = json.dumps(
            {
                "message": "rate limited token=hidden",
                "secret": "hidden",
            }
        ).encode("utf-16")

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    429,
                    "Too Many Requests",
                    hdrs={
                        "Content-Type": "application/json; charset=utf-16",
                    },
                    fp=io.BytesIO(error_body),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 429", message)
        self.assertIn("Too Many Requests", message)
        self.assertIn("rate limited", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_compressed_http_error_body_with_declared_charset(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()
        error_body = json.dumps(
            {
                "message": "rate limited token=hidden",
                "secret": "hidden",
            }
        ).encode("utf-16")

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    429,
                    "Too Many Requests",
                    hdrs={
                        "Content-Encoding": "gzip",
                        "Content-Type": "application/json; charset=utf-16",
                    },
                    fp=io.BytesIO(gzip.compress(error_body)),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 429", message)
        self.assertIn("Too Many Requests", message)
        self.assertIn("rate limited", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_http_json_http_error_retry_header_hints_safely(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    429,
                    "Too Many Requests",
                    hdrs={
                        "Retry-After": "30",
                        "X-Request-ID": "req-upstream-1",
                        "X-Correlation-ID": "corr-secret=hidden",
                        "X-Ignored-Secret": "secret=hidden",
                    },
                    fp=io.BytesIO(b'{"message":"rate limited token=hidden"}'),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 429", message)
        self.assertIn("retry-after: 30", message)
        self.assertIn("request id: req-upstream-1", message)
        self.assertIn("correlation id: corr-[redacted]", message)
        self.assertIn("rate limited", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("X-Ignored-Secret", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret=hidden", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_http_json_standard_rate_limit_header_hints_safely(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    429,
                    "Too Many Requests",
                    hdrs={
                        "RateLimit-Reset": "reset-secret=hidden",
                        "RateLimit-Remaining": "0",
                        "RateLimit-Limit": "100",
                        "Location": "https://login.example/callback?token=hidden",
                    },
                    fp=io.BytesIO(b'{"message":"rate limited token=hidden"}'),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 429", message)
        self.assertIn("rate-limit-reset: reset-[redacted]", message)
        self.assertIn("rate-limit-remaining: 0", message)
        self.assertIn("rate-limit-limit: 100", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("Location", message)
        self.assertNotIn("login.example", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret=hidden", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_http_json_trace_header_hints_safely(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    503,
                    "Service Unavailable",
                    hdrs={
                        "Traceparent": (
                            "00-4bf92f3577b34da6a3ce929d0e0e4736-"
                            "00f067aa0ba902b7-01"
                        ),
                        "X-Trace-ID": "trace-secret=hidden",
                        "Location": "https://login.example/callback?token=hidden",
                    },
                    fp=io.BytesIO(b'{"message":"upstream token=hidden"}'),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 503", message)
        self.assertIn(
            "traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            message,
        )
        self.assertIn("trace id: trace-[redacted]", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("Location", message)
        self.assertNotIn("login.example", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret=hidden", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_skips_unsafe_http_json_request_id_header_hint(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    429,
                    "Too Many Requests",
                    hdrs={
                        "Retry-After": "30",
                        "X-Request-ID": "Bearer secret-token",
                    },
                    fp=io.BytesIO(b'{"message":"rate limited"}'),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 429", message)
        self.assertIn("retry-after: 30", message)
        self.assertNotIn("request id:", message)
        self.assertNotIn("Bearer", message)
        self.assertNotIn("secret-token", message)

    def test_run_tool_canonical_override_reports_non_2xx_body_with_declared_charset(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class FakeHttpResponse:
            status = 503
            reason = "Service Unavailable"
            headers = {
                "Content-Type": "application/json; charset=utf-16",
            }

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "message": "maintenance token=hidden",
                        "secret": "hidden",
                    }
                ).encode("utf-16")

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
        self.assertIn("HTTP 503", message)
        self.assertIn("Service Unavailable", message)
        self.assertIn("maintenance", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_non_2xx_http_json_retry_header_hints_safely(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class FakeHttpResponse:
            status = 503
            reason = "Service Unavailable"
            headers = {
                "Retry-After": "120",
                "X-Request-ID": "req-adapter-1",
                "X-Correlation-ID": "corr-secret=hidden",
                "X-Ignored-Secret": "secret=hidden",
                "Content-Type": "application/json",
            }

            def read(self) -> bytes:
                return b'{"message":"maintenance token=hidden"}'

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
        self.assertIn("HTTP 503", message)
        self.assertIn("retry-after: 120", message)
        self.assertIn("request id: req-adapter-1", message)
        self.assertIn("correlation id: corr-[redacted]", message)
        self.assertIn("maintenance", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("X-Ignored-Secret", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret=hidden", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_invalid_status_body_with_declared_charset(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class FakeHttpResponse:
            status = "OK"
            headers = {
                "Content-Type": "application/json; charset=utf-16",
            }

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "message": "maintenance token=hidden",
                        "secret": "hidden",
                    }
                ).encode("utf-16")

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
        self.assertIn("invalid HTTP response status", message)
        self.assertIn("maintenance", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_invalid_content_type_body_with_declared_charset(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class FakeHttpResponse:
            status = 200
            reason = "OK"
            headers = {
                "Content-Type": "text/html; charset=utf-16",
            }

            def read(self) -> bytes:
                return "<html>login expired secret=hidden</html>".encode("utf-16")

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
        self.assertIn("login expired", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_invalid_content_type_header_hints_safely(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class FakeHttpResponse:
            status = 200
            reason = "OK"
            headers = {
                "Content-Type": "text/html; charset=utf-8",
                "X-Request-ID": "req-html-1",
                "X-Correlation-ID": "corr-secret=hidden",
                "Location": "https://login.example/callback?token=hidden",
            }

            def read(self) -> bytes:
                return b"<html>login expired token=hidden</html>"

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
        self.assertIn("request id: req-html-1", message)
        self.assertIn("correlation id: corr-[redacted]", message)
        self.assertIn("login expired", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("Location", message)
        self.assertNotIn("login.example", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_invalid_json_body_with_declared_charset(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class FakeHttpResponse:
            status = 200
            reason = "OK"
            headers = {
                "Content-Type": "application/json; charset=utf-16",
            }

            def read(self) -> bytes:
                return "<html>login expired secret=hidden</html>".encode("utf-16")

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
        self.assertIn("login expired", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_invalid_json_header_hints_safely(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class FakeHttpResponse:
            status = 200
            reason = "OK"
            headers = {
                "Content-Type": "application/json",
                "X-Request-ID": "req-json-1",
                "X-Correlation-ID": "corr-secret=hidden",
            }

            def read(self) -> bytes:
                return b'{"message":"login expired token=hidden"'

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
        self.assertIn("request id: req-json-1", message)
        self.assertIn("correlation id: corr-[redacted]", message)
        self.assertIn("login expired", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_unsupported_encoding_body_with_declared_charset(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class FakeHttpResponse:
            status = 200
            reason = "OK"
            headers = {
                "Content-Encoding": "br",
                "Content-Type": "application/json; charset=utf-16",
            }

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "message": "gateway token=hidden",
                        "secret": "hidden",
                    }
                ).encode("utf-16")

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
        self.assertIn("gateway", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_success_encoding_error_header_hints_safely(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class FakeHttpResponse:
            status = 200
            reason = "OK"
            headers = {
                "Content-Encoding": "br",
                "Content-Type": "application/json",
                "X-Request-ID": "req-encoding-1",
                "Retry-After": "15",
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
        self.assertIn("unsupported response content-encoding: br", message)
        self.assertIn("retry-after: 15", message)
        self.assertIn("request id: req-encoding-1", message)
        self.assertIn("gateway", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("transport error", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_raw_deflate_http_error_body(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
                raw_body = (
                    compressor.compress(
                        b'{"message":"rate limited token=hidden","secret":"hidden"}'
                    )
                    + compressor.flush()
                )
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    429,
                    "Too Many Requests",
                    hdrs={
                        "Content-Encoding": "deflate",
                        "Content-Type": "application/json",
                    },
                    fp=io.BytesIO(raw_body),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 429", message)
        self.assertIn("Too Many Requests", message)
        self.assertIn("rate limited", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_chained_encoded_http_json_http_error_body_preview(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    429,
                    "Too Many Requests",
                    hdrs={
                        "Content-Encoding": "gzip, identity",
                        "Content-Type": "application/json",
                    },
                    fp=io.BytesIO(
                        gzip.compress(
                            b'{"message":"rate limited token=hidden","secret":"hidden"}'
                        )
                    ),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 429", message)
        self.assertIn("Too Many Requests", message)
        self.assertIn("rate limited", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_invalid_gzip_http_json_http_error_body_preview(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    502,
                    "Bad Gateway",
                    hdrs={
                        "Content-Encoding": "gzip",
                        "Content-Type": "application/json",
                    },
                    fp=io.BytesIO(b"not gzip secret=hidden"),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 502", message)
        self.assertIn("Bad Gateway", message)
        self.assertIn("invalid gzip response body", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_unsupported_encoded_http_json_http_error_body_preview(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    502,
                    "Bad Gateway",
                    hdrs={
                        "Content-Encoding": "br",
                        "Content-Type": "application/json",
                    },
                    fp=io.BytesIO(b'{"message":"upstream token=hidden"}'),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 502", message)
        self.assertIn("Bad Gateway", message)
        self.assertIn("unsupported response content-encoding: br", message)
        self.assertIn("upstream", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_unsupported_success_response_encoding_as_response_error(
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
                "Content-Encoding": "br",
                "Content-Type": "application/json",
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
        self.assertIn("unsupported response content-encoding: br", message)
        self.assertIn("gateway", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("transport error", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_invalid_success_response_gzip_as_response_error(
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
                "Content-Encoding": "gzip",
                "Content-Type": "application/json",
            }

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
        self.assertNotIn("transport error", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_reports_http_json_http_error_reason_safely(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    502,
                    "Bad Gateway token=hidden",
                    hdrs=None,
                    fp=io.BytesIO(b"{}"),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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

        self.assertFalse(raised.exception.fatal)
        self.assertIn("HTTP 502", str(raised.exception))
        self.assertIn("Bad Gateway", str(raised.exception))
        self.assertIn("[redacted]", str(raised.exception))
        self.assertNotIn("hidden", str(raised.exception))

    def test_run_tool_canonical_override_redacts_http_json_error_body_string_assignments(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    401,
                    "Unauthorized",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"message":"upstream token=hidden","errors":["api_key=hidden"]}'
                    ),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 401", message)
        self.assertIn("upstream", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_redacts_http_json_error_body_field_path_text(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    401,
                    "Unauthorized",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"message":"upstream query_params.access_token Bearer secret-token"}'
                    ),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 401", message)
        self.assertIn("upstream", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("query_params.access_token", message)
        self.assertNotIn("Bearer", message)
        self.assertNotIn("secret-token", message)

    def test_run_tool_canonical_override_redacts_http_json_error_body_url_text(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    401,
                    "Unauthorized",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"message":"callback https://provider.example/cb?access_token=secret-token&state=ok#client_secret=hidden and https://provider.example/api_key/secret-value/cb"}'
                    ),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 401", message)
        self.assertIn("callback", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("access_token", message)
        self.assertNotIn("client_secret", message)
        self.assertNotIn("secret-token", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("secret-value", message)

    def test_run_tool_canonical_override_redacts_http_json_error_body_nested_url_userinfo(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    401,
                    "Unauthorized",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"message":"callback https://provider.example/cb?next=https%3A%2F%2Fuser%3Apass%40inner.example%2Fcb&state=ok"}'
                    ),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 401", message)
        self.assertIn("callback", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("user:pass", message)
        self.assertNotIn("user%3Apass", message)

    def test_run_tool_canonical_override_redacts_http_json_error_body_nested_url_userinfo_in_path_and_fragment(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    401,
                    "Unauthorized",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"message":"path https://provider.example/cb/https%3A%2F%2Fuser%3Apass%40inner.example%2Fcb fragment https://provider.example/cb#next=https%3A%2F%2Fuser%3Apass%40inner.example%2Fcb"}'
                    ),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 401", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("user:pass", message)
        self.assertNotIn("user%3Apass", message)

    def test_run_tool_canonical_override_redacts_http_json_error_body_response_path_text(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    401,
                    "Unauthorized",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"message":"upstream response_path.data.access_token Bearer secret-token"}'
                    ),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 401", message)
        self.assertIn("upstream", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("response_path.data.access_token", message)
        self.assertNotIn("Bearer", message)
        self.assertNotIn("secret-token", message)

    def test_run_tool_canonical_override_redacts_http_json_error_body_response_jsonpath_text(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    401,
                    "Unauthorized",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"message":"upstream response_path=$.data.access_token Bearer secret-token"}'
                    ),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 401", message)
        self.assertIn("upstream", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("response_path=$.data.access_token", message)
        self.assertNotIn("$.data.access_token", message)
        self.assertNotIn("Bearer", message)
        self.assertNotIn("secret-token", message)

    def test_run_tool_canonical_override_redacts_http_json_error_body_bracket_jsonpath_text(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    401,
                    "Unauthorized",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"message":"upstream response_path=$[\'data\'][\'access_token\'] Bearer secret-token"}'
                    ),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 401", message)
        self.assertIn("upstream", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("response_path=$['data']['access_token']", message)
        self.assertNotIn("access_token", message)
        self.assertNotIn("Bearer", message)
        self.assertNotIn("secret-token", message)

    def test_run_tool_canonical_override_closes_http_json_http_error_response_wrapper(
        self,
    ) -> None:
        registry_provider = self._make_http_json_calc_registry_provider()

        class TrackableHTTPError(tool_runtime_module.HTTPError):  # type: ignore[misc, name-defined]
            closed_wrapper = False

            def close(self) -> None:
                type(self).closed_wrapper = True
                super().close()

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise TrackableHTTPError(
                    "https://provider.example/calc",
                    401,
                    "Unauthorized",
                    hdrs=None,
                    fp=io.BytesIO(b'{"message":"upstream"}'),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

            with self.assertRaises(MockToolExecutionError):
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

        self.assertTrue(TrackableHTTPError.closed_wrapper)

    def test_run_tool_canonical_override_reports_limited_http_json_http_error_reason(
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
        long_reason = f"Bad Gateway secret=hidden {'x' * 500}"

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_http_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.HTTPError(  # type: ignore[attr-defined]
                    "https://provider.example/calc",
                    503,
                    long_reason,
                    hdrs=None,
                    fp=io.BytesIO(b"{}"),
                )

            tool_runtime_module.urlopen = raise_http_error  # type: ignore[attr-defined]

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
        self.assertIn("HTTP 503", message)
        self.assertIn("Bad Gateway", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("hidden", message)
        self.assertLessEqual(len(message), 320)
        self.assertIn("...", message)

    def test_run_tool_canonical_override_reports_non_json_http_json_response_body_preview(
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
            def read(self) -> bytes:
                return b"<html>login expired secret=hidden</html>"

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

        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response", str(raised.exception))
        self.assertIn("login expired", str(raised.exception))
        self.assertIn("[redacted]", str(raised.exception))
        self.assertNotIn("hidden", str(raised.exception))
        self.assertNotIn("secret", str(raised.exception))

    def test_run_tool_canonical_override_reports_invalid_utf8_http_json_response_body_preview(
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
            def read(self) -> bytes:
                return b"\xff<html>login expired secret=hidden</html>"

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

        self.assertFalse(raised.exception.fatal)
        self.assertIn("invalid JSON response", str(raised.exception))
        self.assertIn("login expired", str(raised.exception))
        self.assertIn("[redacted]", str(raised.exception))
        self.assertNotIn("hidden", str(raised.exception))
        self.assertNotIn("secret", str(raised.exception))

    def test_run_tool_canonical_override_reports_http_json_transport_error_safely(
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

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_transport_error(request, timeout=0):
                del request, timeout
                raise tool_runtime_module.URLError(  # type: ignore[attr-defined]
                    "connection refused api_key=hidden"
                )

            tool_runtime_module.urlopen = raise_transport_error  # type: ignore[attr-defined]

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

        self.assertFalse(raised.exception.fatal)
        self.assertIn("transport error", str(raised.exception))
        self.assertIn("connection refused", str(raised.exception))
        self.assertIn("[redacted]", str(raised.exception))
        self.assertNotIn("api_key", str(raised.exception))
        self.assertNotIn("urlopen error", str(raised.exception))
        self.assertNotIn("hidden", str(raised.exception))

    def test_run_tool_canonical_override_reports_limited_http_json_transport_error_preview(
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
        long_reason = f"gateway timeout token=hidden {'x' * 500}"

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            def raise_transport_error(request, timeout=0):
                del request, timeout
                raise OSError(long_reason)

            tool_runtime_module.urlopen = raise_transport_error  # type: ignore[attr-defined]

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
        self.assertIn("transport error", message)
        self.assertIn("gateway timeout", message)
        self.assertIn("[redacted]", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)
        self.assertLessEqual(len(message), 320)
        self.assertTrue(message.endswith("..."))
