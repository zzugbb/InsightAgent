from __future__ import annotations

from .context import *


class RuntimeResultSemanticsMixinPart1:
    def test_normalize_tool_spec_coerces_name_and_defaults_input(self) -> None:
        invocation = normalize_tool_spec(
            {
                "name": 123,
                "input": "not-a-dict",
            }
        )

        self.assertEqual(invocation.name, "123")
        self.assertEqual(invocation.tool_input, {})

    def test_normalize_tool_spec_accepts_mapping_wrappers(self) -> None:
        invocation = normalize_tool_spec(
            UserDict(
                {
                    UserString("name"): UserString("calc_eval"),
                    UserString("input"): UserDict(
                        {UserString("expression"): UserString("1+2")}
                    ),
                }
            )
        )

        self.assertEqual(invocation.name, "calc_eval")
        self.assertEqual(invocation.tool_input, {"expression": "1+2"})

    def test_resolve_tool_registration_exposes_explicit_calc_entry(self) -> None:
        registration = resolve_tool_registration("calc_eval")

        self.assertIsNotNone(registration)
        assert registration is not None
        self.assertEqual(registration.name, "calc_eval")
        self.assertEqual(registration.kind, "local_calculator")
        self.assertEqual(registration.label, "Calculator")
        self.assertTrue(registration.retryable_by_default)
        self.assertEqual(registration.default_timeout_ms, 3_000)
        self.assertTrue(registration.requires_user_context)
        self.assertTrue(registration.supports_result_preview)

    def test_build_tool_result_preview_governs_builtin_calc_preview_fields(self) -> None:
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        self.assertEqual(
            build_tool_result_preview(name="calc_eval", output=output),
            {
                "expression": "1+2*3",
                "result": 7.0,
            },
        )

    def test_build_tool_result_preview_governs_builtin_retrieval_preview_fields(
        self,
    ) -> None:
        output = {
            "chunks": ["alpha", "beta"],
            "hits": [{"content": "alpha"}],
            "hit_count": 2,
            "knowledge_base_id": "demo-kb",
            "collection": "user-demo-kb",
        }

        self.assertEqual(
            build_tool_result_preview(name="task_retrieve", output=output),
            {
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )

    def test_build_tool_result_preview_uses_explicit_result_preview_keys(self) -> None:
        output = {
            "tool_kind": "knowledge_retrieval",
            "chunks": ["alpha", "beta"],
            "hit_count": 2,
            "knowledge_base_id": "demo-kb",
            "raw_documents": [{"id": "doc-1"}],
        }
        registration = ToolRegistration(
            name="task_retrieve_hot",
            kind="knowledge_retrieval",
            label="Hot Retrieval",
            retryable_by_default=True,
            default_timeout_ms=5_000,
            requires_user_context=True,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
            },
            result_preview_keys=("tool_kind", "hit_count", "knowledge_base_id"),
        )

        self.assertEqual(
            build_tool_result_preview(
                name="task_retrieve_hot",
                output=output,
                registration=registration,
            ),
            {
                "tool_kind": "knowledge_retrieval",
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )

    def test_get_tool_semantic_kind_normalizes_extra_provider_planner_kind(self) -> None:
        registration = ToolRegistration(
            name="provider_plan",
            kind="provider_planner",
            label="Provider Planner",
            retryable_by_default=False,
            default_timeout_ms=8_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
            },
        )

        self.assertEqual(
            get_tool_semantic_kind(
                name="provider_plan",
                registration=registration,
            ),
            "task_planner",
        )

    def test_build_tool_result_preview_infers_preview_shape_for_extra_provider_planner_kind(
        self,
    ) -> None:
        output = {
            "plan": "Analyze request -> Synthesize final answer",
            "steps": [
                "Analyze request",
                "Synthesize final answer",
            ],
            "tool_kind": "provider_planner",
            "raw_payload": {"audit": "keep-raw-only"},
        }
        registration = ToolRegistration(
            name="provider_plan",
            kind="provider_planner",
            label="Provider Planner",
            retryable_by_default=False,
            default_timeout_ms=8_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
            },
        )

        self.assertEqual(
            build_tool_result_preview(
                name="provider_plan",
                output=output,
                registration=registration,
            ),
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )

    def test_build_tool_result_preview_infers_preview_shape_for_extra_provider_planner_kind_with_tuple_steps(
        self,
    ) -> None:
        output = {
            "plan": "Analyze request -> Synthesize final answer",
            "steps": (
                "Analyze request",
                "Synthesize final answer",
            ),
            "tool_kind": "provider_planner",
            "raw_payload": {"audit": "keep-raw-only"},
        }
        registration = ToolRegistration(
            name="provider_plan",
            kind="provider_planner",
            label="Provider Planner",
            retryable_by_default=False,
            default_timeout_ms=8_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
            },
        )

        self.assertEqual(
            build_tool_result_preview(
                name="provider_plan",
                output=output,
                registration=registration,
            ),
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )

    def test_tool_runtime_helpers_expose_current_calc_defaults(self) -> None:
        self.assertTrue(tool_requires_user_context("calc_eval"))
        self.assertTrue(is_tool_retryable_by_default("calc_eval"))
        self.assertEqual(get_tool_default_timeout_ms("calc_eval"), 3_000)

    def test_ensure_tool_registration_keeps_unknown_tool_fatal(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            ensure_tool_registration("does_not_exist")

        self.assertTrue(ctx.exception.fatal)
        self.assertIn("unknown tool", str(ctx.exception).lower())

    def test_maybe_raise_tool_execution_error_keeps_transient_semantics(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            maybe_raise_tool_execution_error(
                name="mock_plan",
                prompt="[tool-error]",
                attempt=0,
            )

        self.assertFalse(ctx.exception.fatal)
        self.assertIn("transient error", str(ctx.exception).lower())

    def test_maybe_raise_mock_tool_execution_error_keeps_legacy_marker_compatibility(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            maybe_raise_mock_tool_execution_error(
                name="mock_plan",
                prompt="[mock-tool-error]",
                attempt=0,
            )

        self.assertFalse(ctx.exception.fatal)
        self.assertIn("transient error", str(ctx.exception).lower())

    def test_build_tool_runtime_context_keeps_calc_defaults(self) -> None:
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(ctx.name, "calc_eval")
        self.assertEqual(ctx.user_id, "user-1")
        self.assertEqual(ctx.attempt, 0)
        self.assertEqual(ctx.default_timeout_ms, 3_000)
        self.assertTrue(ctx.retryable_by_default)
        self.assertTrue(ctx.requires_user_context)

    def test_build_tool_runtime_context_accepts_custom_registry_metadata(self) -> None:
        registry = {
            "calc_eval": ToolRegistration(
                name="calc_eval",
                kind="custom_calc",
                label="Custom Calculator",
                retryable_by_default=False,
                default_timeout_ms=9_000,
                requires_user_context=False,
                supports_result_preview=False,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_input": tool_input,
                    "prompt": prompt,
                    "user_id": user_id,
                },
            )
        }

        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="custom-calc",
            user_id="user-1",
            attempt=2,
            registry=registry,
        )

        self.assertEqual(ctx.name, "calc_eval")
        self.assertEqual(ctx.user_id, "")
        self.assertEqual(ctx.attempt, 2)
        self.assertEqual(ctx.default_timeout_ms, 9_000)
        self.assertFalse(ctx.retryable_by_default)
        self.assertFalse(ctx.requires_user_context)
        self.assertEqual(ctx.registration.kind, "custom_calc")

    def test_compute_tool_retry_decision_keeps_current_calc_defaults(self) -> None:
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertTrue(
            compute_tool_retry_decision(
                ctx=ctx,
                exc=MockToolExecutionError("transient", fatal=False),
            )
        )
        self.assertFalse(
            compute_tool_retry_decision(
                ctx=ctx,
                exc=MockToolExecutionError("fatal", fatal=True),
            )
        )

    def test_build_tool_end_payload_keeps_preview_and_retry_shape(self) -> None:
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        self.assertEqual(
            build_tool_end_payload(
                name="calc_eval",
                task_id="task-1",
                step_id="step-1",
                output=output,
                retry_count=0,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "done",
                "latency_ms": 12,
                "output_preview": {
                    "expression": "1+2*3",
                    "result": 7.0,
                },
                "kind": "local_calculator",
                "semantic_kind": "local_calculator",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "retry_count": 0,
            },
        )

    def test_build_tool_end_payload_uses_registration_preview_policy_and_timeout(
        self,
    ) -> None:
        output = {
            "documents": [{"title": "Secret"}],
            "tool_kind": "custom_lookup",
        }
        registration = ToolRegistration(
            name="custom_lookup",
            kind="custom_lookup",
            label="Custom Lookup",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=False,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )

        self.assertEqual(
            build_tool_end_payload(
                name="custom_lookup",
                task_id="task-1",
                step_id="step-1",
                output=output,
                retry_count=0,
                registration=registration,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "done",
                "latency_ms": 48,
                "output_preview": None,
                "kind": "custom_lookup",
                "semantic_kind": "custom_lookup",
                "supports_result_preview": False,
                "effective_result_preview_keys": [],
                "retry_count": 0,
            },
        )

    def test_build_tool_end_payload_includes_safe_output_when_effective_result_output_keys_present(
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
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "request_id"),
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )

        payload = build_tool_end_payload(
            name="provider_search",
            task_id="task-1",
            step_id="step-1",
            output={
                "documents_total": 2,
                "request_id": "req-1",
                "raw_documents": [{"id": "doc-1"}],
            },
            retry_count=0,
            registration=registration,
        )

        self.assertEqual(
            payload["output"],
            {
                "documents_total": 2,
                "request_id": "req-1",
            },
        )
        self.assertEqual(
            payload["output_preview"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            payload["effective_result_output_keys"],
            ["documents_total", "request_id"],
        )
        self.assertNotIn("raw_documents", payload["output"])

    def test_build_tool_success_and_error_meta_keep_tool_shape(self) -> None:
        tool_input = {"expression": "1+2*3"}
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        success_meta = build_tool_success_meta(
            name="calc_eval",
            tool_input=tool_input,
            output=output,
            retry_count=0,
            last_error=None,
        )
        error_meta = build_tool_error_meta(
            name="calc_eval",
            tool_input=tool_input,
            retry_count=1,
            error_message="transient",
        )

        self.assertEqual(success_meta["tool"]["name"], "calc_eval")
        self.assertEqual(success_meta["tool"]["output"], output)
        self.assertEqual(
            success_meta["tool"]["output_preview"],
            {
                "expression": "1+2*3",
                "result": 7.0,
            },
        )
        self.assertEqual(success_meta["tool"]["kind"], "local_calculator")
        self.assertEqual(success_meta["tool"]["semantic_kind"], "local_calculator")
        self.assertTrue(success_meta["tool"]["supports_result_preview"])
        self.assertEqual(
            success_meta["tool"]["effective_result_preview_keys"],
            ["expression", "result"],
        )
        self.assertEqual(success_meta["tool"]["status"], "done")
        self.assertEqual(error_meta["tool"]["name"], "calc_eval")
        self.assertEqual(error_meta["tool"]["kind"], "local_calculator")
        self.assertEqual(error_meta["tool"]["semantic_kind"], "local_calculator")
        self.assertTrue(error_meta["tool"]["supports_result_preview"])
        self.assertEqual(
            error_meta["tool"]["effective_result_preview_keys"],
            ["expression", "result"],
        )
        self.assertEqual(error_meta["tool"]["status"], "error")
        self.assertEqual(error_meta["tool"]["error"], "transient")

    def test_build_tool_success_meta_includes_effective_result_output_keys_for_real_tool(
        self,
    ) -> None:
        success_meta = build_tool_success_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            output={
                "documents_total": 2,
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                "tool_kind": "provider_retrieval",
            },
            retry_count=0,
            last_error=None,
            registration=ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "documents_total": 2,
                    "tool_kind": "provider_retrieval",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            ),
        )

        self.assertEqual(
            success_meta["tool"]["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(success_meta["tool"]["semantic_kind"], "provider_search")
        self.assertEqual(
            success_meta["tool"]["semantic_family"],
            "knowledge_retrieval",
        )

    def test_build_tool_success_meta_redacts_http_json_raw_last_error(
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
            result_preview_keys=("status",),
            result_output_keys=("status",),
        )
        base_step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="provider_status",
            meta=build_action_step_initial_meta(
                name="provider_status",
                tool_input={"query": "status"},
                model="mock-gpt",
                label="tool_1",
                token_count=5,
                registration=registration,
            ),
            registration=registration,
        )

        success_meta = build_tool_success_meta(
            name="provider_status",
            tool_input={"query": "status"},
            output={"status": "ready"},
            retry_count=1,
            last_error="retry failed token=hidden api_key=hidden",
            registration=registration,
        )
        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="provider_status",
            tool_input={"query": "status"},
            output={"status": "ready"},
            retry_count=1,
            token_count=7,
            last_error="retry failed token=hidden api_key=hidden",
            registration=registration,
        )

        self.assertEqual(
            success_meta["tool"]["error"],
            "retry failed [redacted] [redacted]",
        )
        self.assertEqual(
            success_step["meta"]["tool"]["error"],  # type: ignore[index]
            "retry failed [redacted] [redacted]",
        )
        combined = json.dumps(
            {"meta": success_meta, "step": success_step},
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("api_key=hidden", combined)
        self.assertNotIn("hidden", combined)

    def test_build_tool_success_and_end_payload_include_result_summary_for_real_tool(
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
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 2,
                "request_id": "req-1",
                "tool_kind": "provider_retrieval",
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "request_id"),
            runtime_semantic_kind="provider_search",
        )

        success_meta = build_tool_success_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            output={
                "documents_total": 2,
                "request_id": "req-1",
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                "tool_kind": "provider_retrieval",
            },
            retry_count=0,
            last_error=None,
            registration=registration,
        )
        tool_end = build_tool_end_payload(
            name="provider_search",
            task_id="task-1",
            step_id="step-1",
            output={
                "documents_total": 2,
                "request_id": "req-1",
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                "tool_kind": "provider_retrieval",
            },
            retry_count=0,
            registration=registration,
        )

        self.assertEqual(
            success_meta["tool"]["result_summary"],
            "Retrieved 2 documents (request id req-1).",
        )
        self.assertEqual(
            tool_end["result_summary"],
            "Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_result_helpers_support_registry_provider_without_explicit_registration(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Provider Search",
                        retryable_by_default=False,
                        default_timeout_ms=21_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "request_id": "req-1",
                            "tool_kind": "provider_retrieval",
                        },
                        result_preview_keys=("documents_total",),
                        result_output_keys=("documents_total", "request_id"),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )
        output = {
            "documents_total": 2,
            "request_id": "req-1",
            "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
            "tool_kind": "provider_retrieval",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry_provider=provider,
            ),
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry_provider=provider,
            ),
            {
                "documents_total": 2,
                "request_id": "req-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry_provider=provider,
            ),
            "Retrieved 2 documents (request id req-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registry_provider=provider,
            ),
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )

    def test_get_tool_effective_result_key_helpers_support_registry_provider_without_explicit_registration(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Hosted Search",
                        retryable_by_default=False,
                        default_timeout_ms=21_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "request_id": "req-1",
                            "tool_kind": "provider_retrieval",
                        },
                        result_preview_keys=("documents_total",),
                        result_output_keys=("documents_total", "request_id"),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="provider_search",
                registry_provider=provider,
            ),
            ("documents_total",),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="provider_search",
                registry_provider=provider,
            ),
            ("documents_total", "request_id"),
        )

    def test_get_tool_effective_result_key_helpers_include_documents_total_for_runtime_override_real_retrieval_tools(
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
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 2,
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                "tool_kind": "provider_retrieval",
            },
        )

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="provider_search",
                registration=registration,
            ),
            ("documents_total", "hit_count", "knowledge_base_id"),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="provider_search",
                registration=registration,
            ),
            ("documents_total", "hit_count", "knowledge_base_id", "request_id"),
        )

    def test_build_tool_result_helpers_fall_back_to_documents_total_for_runtime_override_real_retrieval_tools(
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
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 2,
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                "request_id": "req-1",
                "tool_kind": "provider_retrieval",
            },
        )
        output = {
            "documents_total": 2,
            "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
            "request_id": "req-1",
            "tool_kind": "provider_retrieval",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 documents (request id req-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_result_helpers_normalize_http_json_items_alias_for_raw_output(
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
            runtime_semantic_kind="provider_search",
            execution_kind="http_json",
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "request_id"),
            runner=lambda *, tool_input, prompt, user_id: {
                "items": [{"id": "doc-1"}, {"id": "doc-2"}],
                "request_id": "req-items-raw-1",
            },
        )
        output = {
            "items": [{"id": "doc-1"}, {"id": "doc-2"}],
            "request_id": "req-items-raw-1",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-items-raw-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 documents (request id req-items-raw-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search: Retrieved 2 documents (request id req-items-raw-1).",
        )

    def test_build_tool_result_helpers_normalize_http_json_matches_when_raw_count_is_invalid(
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
            runtime_semantic_kind="provider_search",
            execution_kind="http_json",
            result_preview_keys=("hit_count", "knowledge_base_id"),
            result_output_keys=("hit_count", "knowledge_base_id", "request_id"),
            runner=lambda *, tool_input, prompt, user_id: {
                "hit_count": "unknown",
                "matches": [{"id": "vec-1"}, {"id": "vec-2"}],
                "knowledge_base_id": "provider-kb",
                "request_id": "req-matches-raw-1",
            },
        )
        output = {
            "hit_count": "unknown",
            "matches": [{"id": "vec-1"}, {"id": "vec-2"}],
            "knowledge_base_id": "provider-kb",
            "request_id": "req-matches-raw-1",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-matches-raw-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 hits (request id req-matches-raw-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search: Retrieved 2 hits (request id req-matches-raw-1).",
        )

    def test_build_tool_result_helpers_do_not_infer_http_json_aliases_for_non_http_json_raw_output(
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
            runtime_semantic_kind="provider_search",
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "request_id"),
            runner=lambda *, tool_input, prompt, user_id: {
                "items": [{"id": "doc-1"}, {"id": "doc-2"}],
                "request_id": "req-items-raw-1",
            },
        )
        output = {
            "items": [{"id": "doc-1"}, {"id": "doc-2"}],
            "request_id": "req-items-raw-1",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {},
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "request_id": "req-items-raw-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search output - request_id=req-items-raw-1.",
        )

    def test_build_tool_result_helpers_preserve_request_id_for_runtime_override_real_retrieval_hit_projection(
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
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-1",
                "tool_kind": "provider_retrieval",
            },
        )
        output = {
            "hit_count": 2,
            "knowledge_base_id": "provider-kb",
            "request_id": "req-1",
            "tool_kind": "provider_retrieval",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 hits (request id req-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search: Retrieved 2 hits (request id req-1).",
        )

    def test_get_tool_effective_result_key_helpers_preserve_request_id_for_http_json_provider_calc_without_explicit_output_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_math",
            kind="provider_calc",
            label="Provider Math",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {
                "result": 7,
                "request_id": "req-calc-1",
                "tool_kind": "provider_calc",
            },
        )

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="provider_math",
                registration=registration,
            ),
            ("expression", "result"),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="provider_math",
                registration=registration,
            ),
            ("expression", "result", "request_id"),
        )

    def test_build_tool_result_helpers_preserve_request_id_for_http_json_provider_calc_without_explicit_output_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_math",
            kind="provider_calc",
            label="Provider Math",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {
                "result": 7,
                "request_id": "req-calc-1",
                "tool_kind": "provider_calc",
            },
        )
        output = {
            "result": 7,
            "request_id": "req-calc-1",
            "tool_kind": "provider_calc",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            {
                "result": 7,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            {
                "result": 7,
                "request_id": "req-calc-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            "Calculated result = 7 (request id req-calc-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            "Provider Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_result_helpers_drop_unsafe_request_id_for_http_json_provider_calc(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_math",
            kind="provider_calc",
            label="Provider Math",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {
                "result": 7,
                "request_id": "Bearer secret-token",
                "tool_kind": "provider_calc",
            },
        )
        output = {
            "result": 7,
            "request_id": "Bearer secret-token",
            "tool_kind": "provider_calc",
        }

        self.assertEqual(
            build_tool_result_output(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            {
                "result": 7,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            "Calculated result = 7.",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            "Provider Math: Calculated result = 7.",
        )

    def test_build_tool_start_and_error_payload_keep_current_shape(self) -> None:
        self.assertEqual(
            build_tool_start_payload(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                retry_count=0,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "name": "calc_eval",
                "display_name": "Calculator",
                "input": {"expression": "1+2*3"},
                "kind": "local_calculator",
                "semantic_kind": "local_calculator",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "retry_count": 0,
            },
        )
        self.assertEqual(
            build_tool_error_payload(
                name="calc_eval",
                task_id="task-1",
                step_id="step-1",
                error_message="transient",
                retry_count=1,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "error",
                "latency_ms": 12,
                "output_preview": {"error": "transient"},
                "kind": "local_calculator",
                "semantic_kind": "local_calculator",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "retry_count": 1,
                "error": "transient",
            },
        )

    def test_build_tool_start_payload_supports_registry_provider_without_explicit_registration(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Provider Search",
                        retryable_by_default=False,
                        default_timeout_ms=21_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "tool_kind": "provider_retrieval",
                        },
                        result_preview_keys=("documents_total",),
                        result_output_keys=("documents_total",),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )

        self.assertEqual(
            build_tool_start_payload(
                task_id="task-1",
                step_id="step-1",
                name="provider_search",
                tool_input={"query": "revenue trend"},
                retry_count=0,
                registry_provider=provider,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "name": "provider_search",
                "display_name": "Provider Search",
                "input": {"query": "revenue trend"},
                "kind": "provider_retrieval",
                "semantic_kind": "provider_search",
                "semantic_family": "knowledge_retrieval",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["documents_total"],
                "effective_result_output_keys": ["documents_total"],
                "retry_count": 0,
            },
        )

    def test_build_tool_start_payload_includes_http_json_execution_summary(
        self,
    ) -> None:
        provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_provider_source="analytics_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "analytics_suite": {
                            "provider": "default",
                            "profile": "default",
                            "disabled_tool_names": [
                                "task_plan",
                                "task_retrieve",
                                "calc_eval",
                            ],
                            "extra_tools": {
                                "provider_search": {
                                    "template": "task_retrieve",
                                    "label": "Provider Search",
                                    "kind": "provider_retrieval",
                                    "runtime_semantic_kind": "provider_search",
                                    "execution": {
                                        "kind": "http_json",
                                        "url": "https://provider.example/search?debug=1",
                                        "method": "POST",
                                        "headers": {"X-Trace-Token": "trace-demo"},
                                        "query_params": {"q": "$query"},
                                        "json_body": {"query": "$query", "limit": "$top_k"},
                                        "response_path": "$.data",
                                        "result_fields": {
                                            "documents_total": "$.meta.total",
                                            "request_id": "$.meta.request_id",
                                        },
                                    },
                                    "result_preview_keys": ["documents_total"],
                                    "result_output_keys": ["documents_total", "request_id"],
                                }
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            build_tool_start_payload(
                task_id="task-1",
                step_id="step-1",
                name="provider_search",
                tool_input={"query": "revenue trend", "top_k": 2},
                retry_count=0,
                registry_provider=provider,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "name": "provider_search",
                "display_name": "Provider Search",
                "input": {"query": "revenue trend", "top_k": 2},
                "kind": "provider_retrieval",
                "semantic_kind": "provider_search",
                "execution_kind": "http_json",
                "execution_summary": {
                    "method": "POST",
                    "url_origin": "https://provider.example",
                    "url_path": "/search",
                    "header_count": 1,
                    "query_param_count": 1,
                    "json_body_field_count": 2,
                    "response_path": "$.data",
                    "result_field_names": ["documents_total", "request_id"],
                },
                "semantic_family": "knowledge_retrieval",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["documents_total"],
                "effective_result_output_keys": ["documents_total", "request_id"],
                "retry_count": 0,
            },
        )

    def test_build_tool_start_and_action_meta_redact_http_json_sensitive_tool_input(
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
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
                "tool_kind": "provider_retrieval",
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )
        tool_input = {
            "query": "revenue trend token=hidden",
            "access_token": "hidden",
            "filters": {
                "client_secret": "hidden",
                "region": "us",
            },
            "headers": [
                {
                    "Authorization": "Bearer hidden",
                    "label": "primary token=hidden",
                }
            ],
        }

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input=tool_input,
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input=tool_input,
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )
        success_meta = build_tool_success_meta(
            name="provider_search",
            tool_input=tool_input,
            output={"documents_total": 1},
            retry_count=0,
            last_error=None,
            registration=registration,
        )
        error_meta = build_tool_error_meta(
            name="provider_search",
            tool_input=tool_input,
            retry_count=0,
            error_message="upstream failed",
            registration=registration,
        )

        expected_safe_input = {
            "query": "revenue trend token=[redacted]",
            "access_token": "[redacted]",
            "filters": {
                "client_secret": "[redacted]",
                "region": "us",
            },
            "headers": [
                {
                    "Authorization": "[redacted]",
                    "label": "primary token=[redacted]",
                }
            ],
        }
        self.assertEqual(
            start_payload["input"],
            expected_safe_input,
        )
        self.assertEqual(action_meta["tool"]["input"], start_payload["input"])  # type: ignore[index]
        self.assertEqual(success_meta["tool"]["input"], expected_safe_input)  # type: ignore[index]
        self.assertEqual(error_meta["tool"]["input"], expected_safe_input)  # type: ignore[index]
        combined = json.dumps(
            {
                "start": start_payload,
                "meta": action_meta,
                "success": success_meta,
                "error": error_meta,
            },
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("Bearer hidden", combined)
        self.assertNotIn("client_secret\": \"hidden", combined)
        self.assertNotIn("access_token\": \"hidden", combined)
