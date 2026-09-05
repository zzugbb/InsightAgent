from __future__ import annotations

from .context import *


class RuntimeResultSemanticsMixinPart2:
    def test_build_tool_start_and_error_payload_include_execution_diagnostics_for_invalid_real_tool_execution(
        self,
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

        self.assertEqual(
            build_tool_start_payload(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                retry_count=0,
                registry_provider=registry_provider,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "name": "calc_eval",
                "display_name": "Provider Calculator",
                "input": {"expression": "1+2*3"},
                "kind": "provider_calc",
                "semantic_kind": "local_calculator",
                "execution_kind": "unsupported_transport",
                "execution_diagnostics": [
                    "unsupported tool execution kind unsupported_transport",
                ],
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "effective_result_output_keys": ["expression", "result"],
                "retry_count": 0,
            },
        )
        self.assertEqual(
            build_tool_error_payload(
                name="calc_eval",
                task_id="task-1",
                step_id="step-1",
                error_message="Unsupported tool execution kind: unsupported_transport",
                retry_count=0,
                registry_provider=registry_provider,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "error",
                "latency_ms": 12,
                "output_preview": {
                    "error": "Unsupported tool execution kind: unsupported_transport",
                },
                "kind": "provider_calc",
                "semantic_kind": "local_calculator",
                "execution_kind": "unsupported_transport",
                "execution_diagnostics": [
                    "unsupported tool execution kind unsupported_transport",
                ],
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "effective_result_output_keys": ["expression", "result"],
                "retry_count": 0,
                "error": "Unsupported tool execution kind: unsupported_transport",
            },
        )

    def test_build_tool_runtime_semantics_meta_redacts_sensitive_execution_diagnostics(
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
            execution_kind="http_json",
            execution_diagnostics=(
                "unsupported tool execution kind api_key=hidden",
                "http_json execution query_params.access_token must be safe",
            ),
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        self.assertEqual(
            start_payload["execution_diagnostics"],
            [
                "unsupported tool execution kind [redacted]",
                "http_json execution [redacted] must be safe",
            ],
        )
        self.assertEqual(
            action_meta["tool"]["execution_diagnostics"],  # type: ignore[index]
            start_payload["execution_diagnostics"],
        )
        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertNotIn("api_key=hidden", combined)
        self.assertNotIn("access_token", combined)

    def test_build_tool_runtime_semantics_meta_redacts_wrapped_execution_diagnostics(
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
            execution_kind="http_json",
            execution_diagnostics=(
                UserString("unsupported tool execution kind api_key=hidden"),
                UserString("unsupported tool execution kind api_key=hidden"),
                UserString(
                    "http_json execution query_params.access_token must be safe"
                ),
            ),
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        self.assertEqual(
            start_payload["execution_diagnostics"],
            [
                "unsupported tool execution kind [redacted]",
                "http_json execution [redacted] must be safe",
            ],
        )
        self.assertEqual(
            action_meta["tool"]["execution_diagnostics"],  # type: ignore[index]
            start_payload["execution_diagnostics"],
        )
        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertNotIn("api_key=hidden", combined)
        self.assertNotIn("access_token", combined)

    def test_build_tool_runtime_semantics_meta_infers_label_only_real_tool_family(
        self,
    ) -> None:
        registrations = {
            "hosted_math_gateway": ToolRegistration(
                name="hosted_math_gateway",
                kind="",
                label="Hosted Math",
                retryable_by_default=False,
                default_timeout_ms=12_000,
                requires_user_context=False,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {},
            ),
            "hosted_search_gateway": ToolRegistration(
                name="hosted_search_gateway",
                kind="",
                label="Hosted Search",
                retryable_by_default=False,
                default_timeout_ms=12_000,
                requires_user_context=False,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {},
            ),
            "hosted_planner_gateway": ToolRegistration(
                name="hosted_planner_gateway",
                kind="",
                label="Hosted Planner",
                retryable_by_default=False,
                default_timeout_ms=12_000,
                requires_user_context=False,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {},
            ),
        }

        math_meta = build_tool_runtime_semantics_meta(
            name="hosted_math_gateway",
            registration=registrations["hosted_math_gateway"],
        )
        search_meta = build_tool_runtime_semantics_meta(
            name="hosted_search_gateway",
            registration=registrations["hosted_search_gateway"],
        )
        planner_meta = build_tool_runtime_semantics_meta(
            name="hosted_planner_gateway",
            registration=registrations["hosted_planner_gateway"],
        )

        self.assertEqual(math_meta["semantic_kind"], "hosted_math_gateway")
        self.assertEqual(math_meta["semantic_family"], "local_calculator")
        self.assertEqual(math_meta["effective_result_preview_keys"], ["expression", "result"])
        self.assertEqual(
            math_meta["effective_result_output_keys"],
            ["expression", "result", "request_id"],
        )
        self.assertEqual(search_meta["semantic_kind"], "hosted_search_gateway")
        self.assertEqual(search_meta["semantic_family"], "knowledge_retrieval")
        self.assertEqual(
            search_meta["effective_result_preview_keys"],
            ["documents_total", "hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            search_meta["effective_result_output_keys"],
            ["documents_total", "hit_count", "knowledge_base_id", "request_id"],
        )
        self.assertEqual(planner_meta["semantic_kind"], "hosted_planner_gateway")
        self.assertEqual(planner_meta["semantic_family"], "task_planner")
        self.assertEqual(planner_meta["effective_result_preview_keys"], ["plan", "steps"])
        self.assertEqual(planner_meta["effective_result_output_keys"], ["plan", "steps"])

    def test_build_tool_runtime_semantics_meta_accepts_kind_string_wrapper(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="typed_gateway",
            kind=UserString("provider_retrieval"),
            label="Typed Gateway",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        meta = build_tool_runtime_semantics_meta(
            name="typed_gateway",
            registration=registration,
        )

        self.assertEqual(meta["semantic_kind"], "typed_gateway")
        self.assertEqual(meta["semantic_family"], "knowledge_retrieval")

    def test_build_tool_runtime_semantics_meta_accepts_runtime_kind_string_wrapper(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_gateway",
            kind="provider_retrieval",
            label="Provider Gateway",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            runtime_semantic_kind=UserString("provider_search"),
        )

        meta = build_tool_runtime_semantics_meta(
            name="provider_gateway",
            registration=registration,
        )

        self.assertEqual(meta["semantic_kind"], "provider_search")
        self.assertEqual(meta["semantic_family"], "knowledge_retrieval")

    def test_label_only_real_retrieval_with_explicit_preview_keys_infers_output_diagnostic_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("documents_total",),
        )
        output = {
            "documents_total": 2,
            "knowledge_base_id": "hosted-kb",
            "request_id": "req-hosted-1",
            "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total",),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total", "knowledge_base_id", "request_id"),
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "knowledge_base_id": "hosted-kb",
                "request_id": "req-hosted-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 documents from hosted-kb (request id req-hosted-1).",
        )

    def test_label_only_real_retrieval_preview_only_output_keys_filter_sensitive_legacy_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("documents_total", "access_token"),
        )

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total",),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total", "knowledge_base_id", "request_id"),
        )
        self.assertEqual(
            build_tool_runtime_semantics_meta(
                name="hosted_search_gateway",
                registration=registration,
            ),
            {
                "kind": None,
                "semantic_kind": "hosted_search_gateway",
                "execution_kind": "http_json",
                "semantic_family": "knowledge_retrieval",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["documents_total"],
                "effective_result_output_keys": [
                    "documents_total",
                    "knowledge_base_id",
                    "request_id",
                ],
            },
        )

    def test_label_only_real_retrieval_result_key_wrappers_filter_sensitive_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=UserList(
                [UserString("documents_total"), UserString("access_token")]
            ),
            result_output_keys=UserList(
                [
                    UserString("documents_total"),
                    UserString("access_token"),
                    UserString("request_id"),
                ]
            ),
        )
        output = {
            "documents_total": 2,
            "access_token": "secret-token",
            "request_id": "req-hosted-1",
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total",),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total", "request_id"),
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
            {
                "documents_total": 2,
                "request_id": "req-hosted-1",
            },
        )
        meta = build_tool_runtime_semantics_meta(
            name="hosted_search_gateway",
            registration=registration,
        )
        self.assertEqual(meta["effective_result_preview_keys"], ["documents_total"])
        self.assertEqual(
            meta["effective_result_output_keys"],
            ["documents_total", "request_id"],
        )
        self.assertNotIn("access_token", json.dumps(meta, ensure_ascii=False))

    def test_label_only_real_retrieval_sensitive_only_result_key_wrappers_do_not_fallback(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=UserList([UserString("access_token")]),
            result_output_keys=UserList([UserString("access_token")]),
        )
        output = {
            "documents_total": 2,
            "knowledge_base_id": "hosted-kb",
            "access_token": "secret-token",
            "request_id": "req-hosted-1",
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            (),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            (),
        )
        self.assertEqual(
            build_tool_result_preview(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {},
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {},
        )

    def test_label_only_real_retrieval_explicit_output_keys_filter_sensitive_legacy_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "access_token", "request_id"),
        )
        output = {
            "documents_total": 2,
            "access_token": "secret-token",
            "request_id": "req-hosted-1",
        }

        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total", "request_id"),
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-hosted-1",
            },
        )
        self.assertEqual(
            build_tool_runtime_semantics_meta(
                name="hosted_search_gateway",
                registration=registration,
            )["effective_result_output_keys"],
            ["documents_total", "request_id"],
        )

    def test_label_only_real_retrieval_sensitive_only_preview_keys_do_not_fallback_to_default_projection(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("access_token",),
        )
        output = {
            "documents_total": 2,
            "knowledge_base_id": "hosted-kb",
            "access_token": "secret-token",
            "request_id": "req-hosted-1",
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            (),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            (),
        )
        self.assertEqual(
            build_tool_result_preview(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {},
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {},
        )

    def test_label_only_real_retrieval_sensitive_only_output_keys_do_not_fallback_to_default_projection(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("documents_total",),
            result_output_keys=("access_token",),
        )
        output = {
            "documents_total": 2,
            "knowledge_base_id": "hosted-kb",
            "access_token": "secret-token",
            "request_id": "req-hosted-1",
        }

        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            (),
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {},
        )
        success_meta = build_tool_success_meta(
            name="hosted_search_gateway",
            tool_input={"query": "quarterly revenue"},
            output=output,
            retry_count=0,
            last_error=None,
            registration=registration,
        )
        self.assertEqual(success_meta["tool"]["output"], {})
        self.assertNotIn("result_summary", success_meta["tool"])

    def test_label_only_real_http_json_output_normalization_does_not_emit_null_tool_kind(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        output = normalize_tool_output_for_registration(
            output={
                "documents_total": 2,
                "access_token": "secret-token",
                "message": "gateway token=hidden",
            },
            registration=registration,
        )

        self.assertEqual(output["documents_total"], 2)
        self.assertEqual(output["access_token"], "[redacted]")
        self.assertEqual(output["message"], "gateway token=[redacted]")
        self.assertNotIn("tool_kind", output)

    def test_label_only_real_planner_with_explicit_preview_keys_infers_output_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_planner_gateway",
            kind=None,
            label="Hosted Planner",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("plan",),
        )
        output = {
            "plan": "Analyze request -> Synthesize final answer",
            "steps": ["Analyze request", "Synthesize final answer"],
            "debug": "ignored",
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_planner_gateway",
                registration=registration,
            ),
            ("plan",),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_planner_gateway",
                registration=registration,
            ),
            ("plan",),
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_planner_gateway",
                output=output,
                registration=registration,
            ),
            {
                "plan": "Analyze request -> Synthesize final answer",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="hosted_planner_gateway",
                output=output,
                registration=registration,
            ),
            "Planned steps - Analyze request -> Synthesize final answer.",
        )

    def test_preflight_tool_details_infer_label_only_real_tool_family(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "hosted_math_gateway": ToolRegistration(
                    name="hosted_math_gateway",
                    kind="",
                    label="Hosted Math",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    execution_kind="http_json",
                    runner=lambda *, tool_input, prompt, user_id: {},
                ),
                "hosted_search_gateway": ToolRegistration(
                    name="hosted_search_gateway",
                    kind="",
                    label="Hosted Search",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    execution_kind="http_json",
                    runner=lambda *, tool_input, prompt, user_id: {},
                ),
            }
        )

        details = {
            item["name"]: item
            for item in build_configured_tool_registry_provider_preflight_tool_details(
                provider=provider
            )
        }

        self.assertEqual(
            details["hosted_math_gateway"]["semantic_kind"],
            "hosted_math_gateway",
        )
        self.assertEqual(
            details["hosted_math_gateway"]["semantic_family"],
            "local_calculator",
        )
        self.assertEqual(
            details["hosted_math_gateway"]["effective_result_preview_keys"],
            ("expression", "result"),
        )
        self.assertEqual(
            details["hosted_math_gateway"]["effective_result_output_keys"],
            ("expression", "result", "request_id"),
        )
        self.assertEqual(
            details["hosted_search_gateway"]["semantic_kind"],
            "hosted_search_gateway",
        )
        self.assertEqual(
            details["hosted_search_gateway"]["semantic_family"],
            "knowledge_retrieval",
        )
        self.assertEqual(
            details["hosted_search_gateway"]["effective_result_preview_keys"],
            ("documents_total", "hit_count", "knowledge_base_id"),
        )
        self.assertEqual(
            details["hosted_search_gateway"]["effective_result_output_keys"],
            ("documents_total", "hit_count", "knowledge_base_id", "request_id"),
        )

    def test_build_tool_runtime_semantics_meta_redacts_sensitive_execution_summary(
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
            execution_kind="http_json",
            execution_summary={
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/v1/token=hidden/api_key/secret/search",
                "response_path": "$.data.access_token",
                "result_field_names": ["documents_total", "access_token"],
            },
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        expected_summary = {
            "method": "GET",
            "url_origin": "https://provider.example",
            "url_path": "/v1/[redacted]/[redacted]/[redacted]/search",
            "response_path": "$.data.[redacted]",
            "result_field_names": ["documents_total", "[redacted]"],
        }
        self.assertEqual(start_payload["execution_summary"], expected_summary)
        self.assertEqual(
            action_meta["tool"]["execution_summary"],  # type: ignore[index]
            expected_summary,
        )
        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("api_key/secret", combined)

    def test_build_tool_runtime_semantics_meta_redacts_wrapped_execution_summary(
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
            execution_kind="http_json",
            execution_summary={
                UserString("method"): UserString("POST"),
                UserString("url_origin"): UserString("https://provider.example"),
                UserString("url_path"): UserString(
                    "/v1/token=hidden/api_key/secret/search"
                ),
                UserString("response_path"): UserString("$.data.access_token"),
                UserString("result_field_names"): UserList(
                    [UserString("documents_total"), UserString("access_token")]
                ),
            },
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        expected_summary = {
            "method": "POST",
            "url_origin": "https://provider.example",
            "url_path": "/v1/[redacted]/[redacted]/[redacted]/search",
            "response_path": "$.data.[redacted]",
            "result_field_names": ["documents_total", "[redacted]"],
        }
        self.assertEqual(start_payload["execution_summary"], expected_summary)
        self.assertEqual(
            action_meta["tool"]["execution_summary"],  # type: ignore[index]
            expected_summary,
        )
        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("api_key/secret", combined)

    def test_build_tool_runtime_semantics_meta_redacts_nested_url_execution_summary_path(
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
            execution_kind="http_json",
            execution_summary={
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": (
                    "/cb/https%3A%2F%2Fuser%3Apass%40inner.example%2Fcb/"
                    "https://api_key:secret@next.example/cb"
                ),
                "response_path": "$.data.value",
            },
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", combined)
        self.assertNotIn("user:pass", combined)
        self.assertNotIn("user%3Apass", combined)
        self.assertNotIn("api_key:secret", combined)
        self.assertNotIn("api_key", combined)
        self.assertNotIn("secret@next", combined)

    def test_build_tool_runtime_semantics_meta_redacts_relative_query_fragment_execution_summary_path(
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
            execution_kind="http_json",
            execution_summary={
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": (
                    "/cb?access_token=secret-token&state=ok"
                    "#client_secret=hidden"
                ),
            },
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("secret-token", combined)
        self.assertNotIn("client_secret", combined)
        self.assertNotIn("hidden", combined)

    def test_build_tool_runtime_semantics_meta_redacts_http_json_label_diagnostics(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label=(
                "Provider token=hidden "
                "https://provider.example/cb?access_token=secret-token"
            ),
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )
        provider = StaticToolRegistryProvider(
            registry={
                "provider_status": registration,
            }
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_status",
            tool_input={"query": "demo"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_status",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            registration=registration,
        )
        tool_details = build_configured_tool_registry_provider_preflight_tool_details(
            provider=provider,
        )

        combined = json.dumps(
            {
                "start": start_payload,
                "action_meta": action_meta,
                "tool_details": tool_details,
            },
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", combined)
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("secret-token", combined)

    def test_build_tool_runtime_semantics_meta_redacts_http_json_explicit_display_name_diagnostics(
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
            result_output_keys=("message",),
        )
        display_name = (
            "Provider token=hidden "
            "https://provider.example/cb?access_token=secret-token"
        )

        success_meta = build_tool_success_meta(
            name="provider_status",
            tool_input={"query": "demo"},
            output={"message": "ok"},
            retry_count=0,
            last_error=None,
            display_name=display_name,
            registration=registration,
        )
        error_meta = build_tool_error_meta(
            name="provider_status",
            tool_input={"query": "demo"},
            retry_count=0,
            error_message="failed",
            display_name=display_name,
            registration=registration,
        )
        result_summary = build_tool_result_summary(
            name="provider_status",
            output={"message": "ok"},
            display_name=display_name,
            registration=registration,
        )
        observation_entry = build_tool_observation_entry(
            name="provider_status",
            output={"message": "ok"},
            display_name=display_name,
            registration=registration,
        )

        combined = json.dumps(
            {
                "success_meta": success_meta,
                "error_meta": error_meta,
                "result_summary": result_summary,
                "observation_entry": observation_entry,
            },
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", combined)
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("secret-token", combined)

    def test_build_tool_error_payload_and_meta_redact_http_json_raw_error_message(
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

        error_meta = build_tool_error_meta(
            name="provider_status",
            tool_input={"query": "demo"},
            retry_count=0,
            error_message="upstream failed token=hidden",
            registration=registration,
        )
        error_payload = build_tool_error_payload(
            name="provider_status",
            task_id="task-1",
            step_id="step-1",
            error_message="upstream failed api_key=hidden",
            retry_count=0,
            registration=registration,
        )

        self.assertEqual(
            error_meta["tool"]["error"],
            "upstream failed [redacted]",
        )
        self.assertEqual(
            error_payload["output_preview"],
            {"error": "upstream failed [redacted]"},
        )
        self.assertEqual(error_payload["error"], "upstream failed [redacted]")
        combined = json.dumps(
            {"meta": error_meta, "payload": error_payload},
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("api_key=hidden", combined)
        self.assertNotIn("hidden", combined)

    def test_build_tool_error_payload_and_meta_redact_http_json_error_field_paths_and_bearer(
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

        error_meta = build_tool_error_meta(
            name="provider_status",
            tool_input={"query": "demo"},
            retry_count=0,
            error_message="upstream failed query_params.access_token Bearer secret-token",
            registration=registration,
        )
        error_payload = build_tool_error_payload(
            name="provider_status",
            task_id="task-1",
            step_id="step-1",
            error_message="upstream failed json_body.client_secret Bearer secret-token",
            retry_count=0,
            registration=registration,
        )

        combined = json.dumps(
            {"meta": error_meta, "payload": error_payload},
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("client_secret", combined)
        self.assertNotIn("Bearer", combined)
        self.assertNotIn("secret-token", combined)

    def test_sse_error_payload_redacts_http_json_message_and_detail_diagnostics(
        self,
    ) -> None:
        payload = chat_execution_module.sse_error_payload(
            task_id="task-sse-redact",
            message=(
                "upstream failed response_path=$.data.access_token "
                "Bearer secret-token"
            ),
            code="task_stream_failure",
            fatal=True,
            retry_count=0,
            detail=(
                "callback https://provider.example/cb?access_token=secret-token"
                "#client_secret=hidden"
            ),
            status_code=502,
        )

        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertEqual(payload["task_id"], "task-sse-redact")
        self.assertEqual(payload["code"], "task_stream_failure")
        self.assertEqual(payload["status_code"], 502)

    def test_sanitize_tool_registry_artifact_payload_redacts_bare_bearer_text(
        self,
    ) -> None:
        payload = {
            "last_error": "gateway failed Bearer secret-token",
            "trace_event": {
                "step": {
                    "meta": {
                        "tool": {
                            "error": "provider failed query_params.access_token Bearer secret-token",
                        }
                    }
                }
            },
        }

        sanitized = tool_runtime_module.sanitize_tool_registry_diagnostics_artifact_payload(
            payload
        )

        serialized = json.dumps(sanitized, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
