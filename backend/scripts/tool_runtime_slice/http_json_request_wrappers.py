from __future__ import annotations

from .context import *


class HttpJsonRequestWrappersMixin:
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
