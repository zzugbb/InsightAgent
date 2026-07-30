from __future__ import annotations

from .context import *


class HttpJsonErrorHandlingMixin:
    def test_run_tool_canonical_override_redacts_http_json_root_output_without_result_fields(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
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
                    "result": 7,
                    "access_token": "hidden",
                    "message": "upstream token=hidden",
                    "nested": {"api_key": "hidden"},
                }
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

        output_json = json.dumps(output)
        self.assertEqual(output["result"], 7)
        self.assertEqual(output["access_token"], "[redacted]")
        self.assertEqual(output["nested"], {"api_key": "[redacted]"})
        self.assertIn("token=[redacted]", output["message"])
        self.assertNotIn("hidden", output_json)

    def test_run_tool_canonical_override_redacts_http_json_scoped_output_without_result_fields(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
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
                        "value": 7,
                        "secret": "hidden",
                        "notes": ["ok", "password=hidden"],
                    },
                    "meta": {"request_id": "req-1"},
                }
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

        output_json = json.dumps(output)
        self.assertEqual(output["value"], 7)
        self.assertEqual(output["secret"], "[redacted]")
        self.assertEqual(output["notes"], ["ok", "password=[redacted]"])
        self.assertNotIn("hidden", output_json)

    def test_run_tool_canonical_override_redacts_http_json_mapped_sensitive_output(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
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
                                    "access_token": "$.meta.token",
                                    "message": "$.meta.message",
                                },
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
                    "data": {"value": 7},
                    "meta": {
                        "token": "hidden",
                        "message": "secret=hidden",
                    },
                }
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

        output_json = json.dumps(output)
        self.assertEqual(output["result"], 7)
        self.assertEqual(output["access_token"], "[redacted]")
        self.assertEqual(output["message"], "secret=[redacted]")
        self.assertNotIn("hidden", output_json)

    def test_run_tool_canonical_override_redacts_http_json_scalar_output_assignment(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "response_path": "$.message",
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
                {"message": "token=hidden"}
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

        self.assertEqual(output, {"value": "token=[redacted]", "tool_kind": "provider_calc"})
        self.assertNotIn("hidden", json.dumps(output))

    def test_build_tool_result_output_redacts_raw_http_json_helper_output(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        output = build_tool_result_output(
            name="provider_status",
            output={
                "status": "ready",
                "access_token": "hidden",
                "message": "upstream token=hidden",
                "request_id": "Bearer secret-token",
                "nested": {"api_key": "hidden"},
            },
            registration=registration,
        )

        output_json = json.dumps(output)
        self.assertEqual(output["status"], "ready")
        self.assertEqual(output["access_token"], "[redacted]")
        self.assertEqual(output["message"], "upstream token=[redacted]")
        self.assertEqual(output["nested"], {"api_key": "[redacted]"})
        self.assertNotIn("request_id", output)
        self.assertNotIn("hidden", output_json)
        self.assertNotIn("Bearer", output_json)
        self.assertNotIn("secret-token", output_json)

    def test_build_tool_result_output_redacts_http_json_text_value_field_paths(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        output = build_tool_result_output(
            name="provider_status",
            output={
                "status": "ready",
                "message": "gateway query_params.access_token Bearer secret-token",
            },
            registration=registration,
        )

        output_json = json.dumps(output)
        self.assertEqual(output["status"], "ready")
        self.assertEqual(output["message"], "gateway [redacted] [redacted]")
        self.assertNotIn("query_params.access_token", output_json)
        self.assertNotIn("Bearer", output_json)
        self.assertNotIn("secret-token", output_json)

    def test_build_tool_result_output_redacts_http_json_text_value_urls(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        output = build_tool_result_output(
            name="provider_status",
            output={
                "status": "ready",
                "message": (
                    "callback https://provider.example/cb?"
                    "access_token=secret-token&state=ok#client_secret=hidden"
                ),
            },
            registration=registration,
        )

        output_json = json.dumps(output)
        self.assertEqual(output["status"], "ready")
        self.assertIn("callback", output["message"])
        self.assertIn("[redacted]", output["message"])
        self.assertNotIn("access_token", output_json)
        self.assertNotIn("client_secret", output_json)
        self.assertNotIn("secret-token", output_json)

    def test_build_tool_result_output_redacts_http_json_text_value_nested_url_userinfo(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        output = build_tool_result_output(
            name="provider_status",
            output={
                "status": "ready",
                "message": (
                    "callback https://provider.example/cb?"
                    "next=https%3A%2F%2Fuser%3Apass%40inner.example%2Fcb"
                    "&state=ok"
                ),
            },
            registration=registration,
        )

        output_json = json.dumps(output)
        self.assertEqual(output["status"], "ready")
        self.assertIn("callback", output["message"])
        self.assertIn("[redacted]", output["message"])
        self.assertNotIn("user:pass", output_json)
        self.assertNotIn("user%3Apass", output_json)

    def test_build_tool_result_output_redacts_http_json_text_value_nested_url_userinfo_in_path_and_fragment(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        output = build_tool_result_output(
            name="provider_status",
            output={
                "status": "ready",
                "message": (
                    "path https://provider.example/cb/"
                    "https%3A%2F%2Fuser%3Apass%40inner.example%2Fcb "
                    "fragment https://provider.example/cb#next="
                    "https%3A%2F%2Fuser%3Apass%40inner.example%2Fcb"
                ),
            },
            registration=registration,
        )

        output_json = json.dumps(output)
        self.assertEqual(output["status"], "ready")
        self.assertIn("[redacted]", output["message"])
        self.assertNotIn("user:pass", output_json)
        self.assertNotIn("user%3Apass", output_json)

    def test_build_tool_result_output_redacts_http_json_sensitive_diagnostic_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        output = build_tool_result_output(
            name="provider_status",
            output={
                "status": "ready",
                "response_path=$.data.access_token": "missing",
                (
                    "callback https://provider.example/cb?"
                    "access_token=secret-token"
                ): "bad",
                "details": {
                    "response_path=$['data']['client_secret']": "missing",
                    "ok": "fine",
                },
            },
            registration=registration,
        )

        output_json = json.dumps(output)
        self.assertEqual(output["status"], "ready")
        self.assertIn("[redacted]", output)
        self.assertEqual(output["[redacted]"], "[redacted]")
        self.assertEqual(output["details"]["[redacted]"], "[redacted]")
        self.assertNotIn("response_path=$.data.access_token", output_json)
        self.assertNotIn("response_path=$['data']['client_secret']", output_json)
        self.assertNotIn("access_token", output_json)
        self.assertNotIn("client_secret", output_json)
        self.assertNotIn("secret-token", output_json)

    def test_build_tool_result_output_redacts_half_migrated_http_json_execution_kind(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind=" HTTP_JSON ",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        output = build_tool_result_output(
            name="provider_status",
            output={
                "status": "ready",
                "access_token": "hidden",
                "message": "gateway token=hidden",
                "request_id": "Bearer secret-token",
            },
            registration=registration,
        )

        output_json = json.dumps(output)
        self.assertEqual(output["status"], "ready")
        self.assertEqual(output["access_token"], "[redacted]")
        self.assertEqual(output["message"], "gateway token=[redacted]")
        self.assertNotIn("request_id", output)
        self.assertNotIn("hidden", output_json)
        self.assertNotIn("Bearer", output_json)
        self.assertNotIn("secret-token", output_json)

    def test_build_tool_result_preview_redacts_raw_http_json_helper_output(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        preview = build_tool_result_preview(
            name="provider_status",
            output={
                "status": "ready",
                "message": "gateway secret=hidden",
                "nested": {"password": "hidden"},
            },
            registration=registration,
        )

        self.assertIsNotNone(preview)
        assert preview is not None
        preview_json = json.dumps(preview)
        self.assertEqual(preview["status"], "ready")
        self.assertEqual(preview["message"], "gateway secret=[redacted]")
        self.assertEqual(preview["nested"], {"password": "[redacted]"})
        self.assertNotIn("hidden", preview_json)

    def test_build_tool_result_summary_redacts_raw_http_json_generic_payload(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            result_output_keys=("status", "message", "request_id"),
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        summary = build_tool_result_summary(
            name="provider_status",
            output={
                "status": "ready",
                "message": "gateway token=hidden",
                "request_id": "Bearer secret-token",
            },
            registration=registration,
        )

        self.assertEqual(
            summary,
            "Provider Status output - status=ready, message=gateway [redacted].",
        )

    def test_build_tool_result_summary_redacts_http_json_generic_text_field_paths(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            result_output_keys=("status", "message"),
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        summary = build_tool_result_summary(
            name="provider_status",
            output={
                "status": "ready",
                "message": "gateway query_params.access_token Bearer secret-token",
            },
            registration=registration,
        )

        self.assertEqual(
            summary,
            "Provider Status output - status=ready, message=gateway [redacted] [redacted].",
        )
        self.assertNotIn("query_params.access_token", summary)
        self.assertNotIn("Bearer", summary)
        self.assertNotIn("secret-token", summary)

    def test_build_tool_result_summary_uses_label_for_untyped_real_calc_tool(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_math_gateway",
            kind="",
            label="Hosted Math",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            result_output_keys=("result", "request_id"),
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        self.assertEqual(
            build_tool_result_summary(
                name="hosted_math_gateway",
                output={"result": 7, "request_id": "req-calc-1"},
                registration=registration,
            ),
            "Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_result_helpers_infer_keys_for_untyped_real_calc_label(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_math_gateway",
            kind="",
            label="Hosted Math",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )
        output = {
            "expression": "1+2*3",
            "result": 7,
            "request_id": "req-calc-1",
            "access_token": "hidden",
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_math_gateway",
                registration=registration,
            ),
            ("expression", "result"),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_math_gateway",
                registration=registration,
            ),
            ("expression", "result", "request_id"),
        )
        self.assertEqual(
            build_tool_result_preview(
                name="hosted_math_gateway",
                output=output,
                registration=registration,
            ),
            {"expression": "1+2*3", "result": 7},
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_math_gateway",
                output=output,
                registration=registration,
            ),
            {"expression": "1+2*3", "result": 7, "request_id": "req-calc-1"},
        )
        self.assertEqual(
            build_tool_result_summary(
                name="hosted_math_gateway",
                output=output,
                registration=registration,
            ),
            "Calculated 1+2*3 = 7 (request id req-calc-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math_gateway",
                output=output,
                registration=registration,
            ),
            "Hosted Math: Calculated 1+2*3 = 7 (request id req-calc-1).",
        )

    def test_build_tool_result_summary_accepts_calc_output_string_wrappers(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_math_gateway",
            kind="",
            label="Hosted Math",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )
        output = {
            "expression": UserString("1+2*3"),
            "result": 7,
            "request_id": UserString("req-calc-1"),
        }

        self.assertEqual(
            build_tool_result_summary(
                name="hosted_math_gateway",
                output=output,
                registration=registration,
            ),
            "Calculated 1+2*3 = 7 (request id req-calc-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math_gateway",
                output=output,
                registration=registration,
            ),
            "Hosted Math: Calculated 1+2*3 = 7 (request id req-calc-1).",
        )

    def test_build_tool_result_helpers_infer_keys_for_untyped_real_retrieval_label(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind="",
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )
        output = {
            "documents_total": 2,
            "request_id": "req-search-1",
            "access_token": "hidden",
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total", "hit_count", "knowledge_base_id"),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total", "hit_count", "knowledge_base_id", "request_id"),
        )
        self.assertEqual(
            build_tool_result_preview(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {"documents_total": 2},
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {"documents_total": 2, "request_id": "req-search-1"},
        )
        self.assertEqual(
            build_tool_result_summary(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 documents (request id req-search-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            "Hosted Search: Retrieved 2 documents (request id req-search-1).",
        )

    def test_build_tool_result_summary_accepts_retrieval_output_string_wrappers(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind="",
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )
        output = {
            "documents_total": 2,
            "knowledge_base_id": UserString("hosted-kb"),
            "request_id": UserString("req-search-1"),
        }

        self.assertEqual(
            build_tool_result_summary(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 documents from hosted-kb (request id req-search-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            "Hosted Search: Retrieved 2 documents from hosted-kb (request id req-search-1).",
        )

    def test_build_tool_result_helpers_infer_keys_for_untyped_real_planner_label(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_planner_gateway",
            kind="",
            label="Hosted Planner",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )
        output = {
            "steps": ["gather", "calculate"],
            "request_id": "req-plan-1",
            "access_token": "hidden",
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_planner_gateway",
                registration=registration,
            ),
            ("plan", "steps"),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_planner_gateway",
                registration=registration,
            ),
            ("plan", "steps"),
        )
        self.assertEqual(
            build_tool_result_preview(
                name="hosted_planner_gateway",
                output=output,
                registration=registration,
            ),
            {"steps": ["gather", "calculate"]},
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_planner_gateway",
                output=output,
                registration=registration,
            ),
            {"steps": ["gather", "calculate"]},
        )
        self.assertEqual(
            build_tool_result_summary(
                name="hosted_planner_gateway",
                output=output,
                registration=registration,
            ),
            "Planned steps - gather -> calculate.",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_planner_gateway",
                output=output,
                registration=registration,
            ),
            "Hosted Planner: Planned steps - gather -> calculate.",
        )

    def test_build_tool_result_summary_accepts_planner_output_string_wrappers(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_planner_gateway",
            kind="",
            label="Hosted Planner",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )
        output = {
            "steps": UserList([UserString("gather"), UserString("calculate")]),
            "access_token": "hidden",
        }

        self.assertEqual(
            build_tool_result_output(
                name="hosted_planner_gateway",
                output=output,
                registration=registration,
            ),
            {"steps": ["gather", "calculate"]},
        )
        self.assertEqual(
            build_tool_result_summary(
                name="hosted_planner_gateway",
                output=output,
                registration=registration,
            ),
            "Planned steps - gather -> calculate.",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_planner_gateway",
                output=output,
                registration=registration,
            ),
            "Hosted Planner: Planned steps - gather -> calculate.",
        )

    def test_run_tool_canonical_override_rejects_unknown_execution_kind_without_fallback(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "unsupported_transport",
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
        self.assertIn("Unsupported tool execution kind", str(raised.exception))

    def test_run_tool_canonical_override_redacts_sensitive_unknown_execution_kind(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "api_key=hidden",
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

        message = str(raised.exception)
        self.assertTrue(raised.exception.fatal)
        self.assertIn("Unsupported tool execution kind [redacted]", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_invalid_http_json_method_without_get_fallback(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "POTS",
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
                or self.fail("invalid http_json method must fail before request")
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
            "execution method must be one of",
            str(raised.exception),
        )

    def test_run_tool_canonical_override_accepts_http_json_method_runtime_template(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "$request_method",
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
                return b'{"data":{"value":457}}'

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
                    "request_method": "POST",
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

        self.assertEqual(output["result"], 457)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"expression": "1+2*3"},
        )

    def test_run_tool_canonical_override_rejects_http_json_method_runtime_template_invalid_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "$request_method",
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
                or self.fail("invalid rendered method must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={"request_method": "FETCH"},
                    prompt="calc",
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
        self.assertIn("execution method must be one of", str(raised.exception))

    def test_run_tool_canonical_override_rejects_http_json_method_runtime_template_get_body_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc",
                                "method": "$request_method",
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
                or self.fail("rendered GET json_body must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "request_method": "GET",
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
        self.assertIn("GET method must not define json_body", str(raised.exception))

    def test_tool_registry_execution_diagnostics_accept_http_json_method_root_template(
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
                                "method": "$request_method",
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

    def test_tool_registry_execution_diagnostics_reject_http_json_method_timeout_unsupported_runtime_templates(
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
                                "method": "$settings_method_typo",
                                "timeout_ms": "$tool_registry_timeout_typo",
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
                "provider_search: http_json execution references unsupported runtime template variable settings_method_typo in method",
                "provider_search: http_json execution references unsupported runtime template variable tool_registry_timeout_typo in timeout_ms",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_invalid_http_json_method(
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
                                "method": "FETCH",
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
                "provider_search: http_json execution method must be one of "
                "GET, POST, PUT, PATCH, DELETE",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_unsupported_http_json_url_scheme(
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
                                "url": "ftp://provider.example/search",
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
                "provider_search: http_json execution url must be an absolute "
                "http(s) URL",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_relative_http_json_url(
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
                                "url": "/search",
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
                "provider_search: http_json execution url must be an absolute "
                "http(s) URL",
            ),
        )

    def test_tool_registry_execution_diagnostics_reject_http_json_url_fragment_without_echo(
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
                                "url": "https://provider.example/search#token=hidden",
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
                "provider_search: http_json execution url must not include fragments",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_url_query_protocol_names_without_echo(
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
                                "url": (
                                    "https://provider.example/search?"
                                    "bad%26name=open&access_token%3Dsecret=hidden"
                                ),
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
                "provider_search: http_json execution url query parameters must use safe query parameter names",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("access_token", joined_diagnostics)
        self.assertNotIn("secret", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_duplicate_url_query_names_without_echo(
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
                                "url": (
                                    "https://provider.example/search?"
                                    "access_token=hidden&access_token=again"
                                ),
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
                "provider_search: http_json execution url query must not define duplicate parameter names",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("access_token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)
        self.assertNotIn("again", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_url_query_control_value_without_echo(
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
                                "url": (
                                    "https://provider.example/search?"
                                    "q=alpha%00secret%3Dhidden"
                                ),
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
                "provider_search: http_json execution url query parameter values must not contain control characters",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("secret", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_duplicate_url_query_and_query_params_without_echo(
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
                                "url": (
                                    "https://provider.example/search?"
                                    "access_token=hidden"
                                ),
                                "query_params": {
                                    "access_token": "$query",
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
                "provider_search: http_json execution url query and query_params must not define duplicate parameter names",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("access_token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_url_path_encoded_control_without_echo(
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
                                "url": (
                                    "https://provider.example/search/"
                                    "%00secret%3Dhidden"
                                ),
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
                "provider_search: http_json execution url path must not contain encoded control characters",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("secret", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_tool_registry_execution_diagnostics_reject_http_json_url_path_dot_segments_without_echo(
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
                                "url": (
                                    "https://provider.example/v1/%2e%2e/"
                                    "secret%3Dhidden/search"
                                ),
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
                "provider_search: http_json execution url path must not include dot segments",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("secret", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_run_tool_canonical_override_rejects_rendered_relative_http_json_url_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "$base_url",
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
                or self.fail("rendered relative url must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "base_url": "/calc",
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
        self.assertIn("url must be an absolute http(s) URL", str(raised.exception))

    def test_run_tool_canonical_override_rejects_rendered_duplicate_http_json_url_query_and_query_params_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "$base_url",
                                "query_params": {
                                    "access_token": "$expression",
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
                or self.fail("duplicate query names must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "base_url": (
                            "https://provider.example/calc?"
                            "access_token=hidden"
                        ),
                        "expression": "1+2*3",
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
        self.assertIn(
            "url query and query_params must not define duplicate parameter names",
            message,
        )
        self.assertNotIn("access_token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_duplicate_http_json_url_query_names_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "$base_url",
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
                or self.fail("duplicate url query names must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "base_url": (
                            "https://provider.example/calc?"
                            "access_token=hidden&access_token=again"
                        ),
                        "expression": "1+2*3",
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
        self.assertIn(
            "url query must not define duplicate parameter names",
            message,
        )
        self.assertNotIn("access_token", message)
        self.assertNotIn("hidden", message)
        self.assertNotIn("again", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_url_fragment_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/calc#$fragment",
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
                or self.fail("rendered url fragment must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "fragment": "secret=hidden",
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
        self.assertIn("url must not include fragments", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_url_query_protocol_name_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "$base_url",
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
                or self.fail("rendered url query protocol name must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "base_url": (
                            "https://provider.example/calc?"
                            "api_key%26token=hidden"
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
        self.assertIn("url query parameters must use safe query parameter names", message)
        self.assertNotIn("api_key", message)
        self.assertNotIn("token", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_url_query_control_value_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "$base_url",
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
                or self.fail("rendered url query control value must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "base_url": (
                            "https://provider.example/calc?"
                            "q=alpha%00secret%3Dhidden"
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
        self.assertIn(
            "url query parameter values must not contain control characters",
            message,
        )
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_url_path_encoded_control_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "$base_url",
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
                or self.fail("rendered url path encoded control must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "base_url": (
                            "https://provider.example/calc/"
                            "%00secret%3Dhidden"
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
        self.assertIn("url path must not contain encoded control characters", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_url_path_dot_segments_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "$base_url",
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
                or self.fail("rendered url path dot segments must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "base_url": (
                            "https://provider.example/calc/%2e/"
                            "secret%3Dhidden"
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
        self.assertIn("url path must not include dot segments", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("hidden", message)

    def test_run_tool_canonical_override_rejects_rendered_http_json_url_credentials_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "$base_url",
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
                or self.fail("rendered url credentials must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "base_url": "https://token:secret@provider.example/calc",
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
        self.assertIn("url must not include credentials", str(raised.exception))
        self.assertNotIn("token", str(raised.exception))
        self.assertNotIn("secret", str(raised.exception))

    def test_run_tool_canonical_override_rejects_rendered_http_json_url_invalid_port_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "$base_url",
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
                or self.fail("rendered invalid url port must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "base_url": "https://provider.example:99999/calc",
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
        self.assertIn("url must include a valid port", str(raised.exception))

    def test_run_tool_canonical_override_rejects_rendered_http_json_url_control_characters_without_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "http_json",
                                "url": "$base_url",
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
                or self.fail("rendered url control characters must fail before request")
            )

            with self.assertRaises(MockToolExecutionError) as raised:
                run_tool(
                    name="calc_eval",
                    tool_input={
                        "expression": "1+2*3",
                        "base_url": "https://provider.example/calc path",
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
        self.assertIn("url must not contain control characters or spaces", str(raised.exception))
        self.assertNotIn("calc path", str(raised.exception))

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
