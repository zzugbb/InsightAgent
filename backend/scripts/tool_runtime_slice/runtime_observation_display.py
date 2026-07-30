from __future__ import annotations

from .context import *


class RuntimeObservationDisplayMixin:
    def test_build_tool_observation_entry_prefers_preview_shape_for_builtin_calculator(self) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="calc_eval",
                output={
                    "expression": "1+2*3",
                    "result": 7.0,
                    "tool_kind": "local_calculator",
                },
            ),
            'Calculator: {"expression": "1+2*3", "result": 7.0}',
        )

    def test_build_tool_observation_entry_prefers_result_summary_for_runtime_override_real_tool(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=13_000,
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

        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output={
                    "documents_total": 2,
                    "request_id": "req-1",
                    "documents": [{"id": "doc-1"}],
                    "tool_kind": "provider_retrieval",
                },
                registration=registration,
            ),
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_observation_entry_reuses_step_meta_preview_without_registry_context(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="custom_lookup",
                output={
                    "tool_kind": "custom_lookup",
                    "hit_count": 1,
                    "secret": "do-not-preview",
                },
                step_tool_meta={
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "status": "done",
                    "output": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                        "secret": "do-not-preview",
                    },
                    "output_preview": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                    },
                },
            ),
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )

    def test_build_tool_observation_entry_reuses_step_meta_result_summary_without_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "result_summary": "Retrieved 2 documents (request id req-1).",
                    "output_preview": {
                        "documents_total": 2,
                    },
                },
            ),
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_observation_entry_redacts_http_json_step_meta_result_summary(
        self,
    ) -> None:
        observation = build_tool_observation_entry(
            name="provider_status",
            output=None,
            step_tool_meta={
                "name": "provider_status",
                "label": "Provider Status",
                "status": "done",
                "execution_kind": "http_json",
                "result_summary": (
                    "Provider Status output - status=ready, "
                    "message=query_params.access_token Bearer secret-token."
                ),
            },
        )

        self.assertEqual(
            observation,
            "Provider Status: Provider Status output - status=ready, "
            "message=[redacted] [redacted]",
        )
        self.assertNotIn("access_token", observation)
        self.assertNotIn("Bearer", observation)
        self.assertNotIn("secret-token", observation)

    def test_build_tool_observation_entry_infers_result_summary_from_step_meta_safe_output_without_output(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=13_000,
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

        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                registration=registration,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "effective_result_output_keys": [
                        "documents_total",
                        "request_id",
                    ],
                    "output": {
                        "documents_total": 2,
                        "request_id": "req-1",
                        "documents": [{"id": "doc-1"}],
                    },
                    "output_preview": {
                        "documents_total": 2,
                    },
                },
            ),
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_observation_entry_infers_result_summary_from_step_meta_preview_without_output(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="task_plan",
            kind="planner",
            label="Task Planner",
            retryable_by_default=False,
            default_timeout_ms=13_000,
            requires_user_context=True,
            supports_result_preview=True,
            result_preview_keys=("plan",),
            result_output_keys=("plan",),
            runtime_semantic_kind="task_planner",
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )

        self.assertEqual(
            build_tool_observation_entry(
                name="task_plan",
                output=None,
                registration=registration,
                step_tool_meta={
                    "name": "task_plan",
                    "label": "Task Planner",
                    "status": "done",
                    "output_preview": {
                        "plan": "Analyze request -> Synthesize final answer",
                    },
                },
            ),
            "Task Planner: Planned steps - Analyze request -> Synthesize final answer.",
        )

    def test_build_tool_observation_entry_infers_result_summary_from_step_meta_safe_output_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_search",
                output=None,
                step_tool_meta={
                    "name": "hosted_search",
                    "label": "Hosted Search",
                    "status": "done",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "effective_result_output_keys": [
                        "documents_total",
                        "request_id",
                    ],
                    "output": {
                        "documents_total": 2,
                        "request_id": "req-1",
                        "documents": [{"id": "doc-1"}],
                    },
                    "output_preview": {
                        "documents_total": 2,
                    },
                },
            ),
            "Hosted Search: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_observation_entry_infers_result_summary_from_step_meta_preview_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_planner",
                output=None,
                step_tool_meta={
                    "name": "provider_planner",
                    "label": "Provider Planner",
                    "status": "done",
                    "semantic_kind": "provider_planner",
                    "semantic_family": "task_planner",
                    "output_preview": {
                        "plan": "Analyze request -> Synthesize final answer",
                    },
                },
            ),
            "Provider Planner: Planned steps - Analyze request -> Synthesize final answer.",
        )

    def test_build_tool_observation_entry_infers_result_summary_from_noncanonical_semantic_kind_and_output_keys_without_semantic_family(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_lookup",
                output=None,
                step_tool_meta={
                    "name": "hosted_lookup",
                    "label": "Hosted Lookup",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "status": "done",
                    "effective_result_output_keys": [
                        "documents_total",
                        "request_id",
                    ],
                    "output": {
                        "documents_total": 2,
                        "request_id": "req-1",
                        "documents": [{"id": "doc-1"}],
                    },
                    "output_preview": {
                        "documents_total": 2,
                    },
                },
            ),
            "Hosted Lookup: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_observation_entry_infers_calc_summary_from_noncanonical_semantic_kind_and_output_keys_without_semantic_family(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math",
                output=None,
                step_tool_meta={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "kind": "provider_calc",
                    "semantic_kind": "provider_math",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": {
                        "result": 7,
                        "request_id": "req-calc-1",
                    },
                    "output_preview": {
                        "result": 7,
                    },
                },
            ),
            "Hosted Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_does_not_imply_local_kb_for_name_only_real_tool_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "effective_result_output_keys": [
                        "hit_count",
                        "knowledge_base_id",
                        "request_id",
                    ],
                    "output": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-1",
                    },
                    "output_preview": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                    },
                },
            ),
            "Provider Search: Retrieved 2 hits (request id req-1).",
        )

    def test_build_tool_observation_entry_normalizes_numeric_string_counts_from_step_meta_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "status": "done",
                    "effective_result_output_keys": [
                        "hit_count",
                        "knowledge_base_id",
                        "request_id",
                    ],
                    "output": {
                        "hit_count": "2",
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-string-count-1",
                    },
                    "output_preview": {
                        "hit_count": "2",
                        "knowledge_base_id": "provider-kb",
                    },
                },
            ),
            "Provider Search: Retrieved 2 hits (request id req-string-count-1).",
        )

    def test_build_tool_observation_entry_normalizes_http_json_aliases_from_step_meta_output_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "execution_kind": "http_json",
                    "status": "done",
                    "effective_result_output_keys": [
                        "hit_count",
                        "knowledge_base_id",
                        "request_id",
                    ],
                    "output": {
                        "hit_count": "unknown",
                        "matches": [
                            {"id": "vec-1"},
                            {"id": "vec-2"},
                        ],
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-step-matches-1",
                    },
                },
            ),
            "Provider Search: Retrieved 2 hits (request id req-step-matches-1).",
        )

    def test_build_tool_observation_entry_normalizes_http_json_aliases_from_step_meta_preview_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "execution_kind": "http_json",
                    "status": "done",
                    "output_preview": {
                        "items": [
                            {"id": "doc-1"},
                            {"id": "doc-2"},
                        ],
                        "request_id": "req-step-items-1",
                    },
                },
            ),
            "Provider Search: Retrieved 2 documents (request id req-step-items-1).",
        )

    def test_build_tool_observation_entry_does_not_imply_local_kb_for_productized_retrieval_label_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search [retrieval]",
                    "status": "done",
                    "effective_result_output_keys": [
                        "hit_count",
                        "knowledge_base_id",
                        "request_id",
                    ],
                    "output": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-1",
                    },
                    "output_preview": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                    },
                },
            ),
            "Provider Search [retrieval]: Retrieved 2 hits (request id req-1).",
        )

    def test_build_tool_observation_entry_infers_calc_summary_for_name_only_real_tool_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math",
                output=None,
                step_tool_meta={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": {
                        "result": 7,
                        "request_id": "req-calc-1",
                    },
                    "output_preview": {
                        "result": 7,
                    },
                },
            ),
            "Hosted Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_infers_calc_summary_for_productized_calculator_label_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="custom_math_runner",
                output=None,
                step_tool_meta={
                    "name": "custom_math_runner",
                    "label": "Hosted Math [calculator]",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": {
                        "result": 7,
                        "request_id": "req-calc-1",
                    },
                    "output_preview": {
                        "result": 7,
                    },
                },
            ),
            "Hosted Math [calculator]: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_reuses_step_meta_preview_without_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="custom_lookup",
                output=None,
                step_tool_meta={
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "status": "done",
                    "output_preview": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                    },
                },
            ),
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )

    def test_build_tool_observation_entry_redacts_http_json_step_meta_preview_fallback(
        self,
    ) -> None:
        observation = build_tool_observation_entry(
            name="provider_status",
            output=None,
            step_tool_meta={
                "name": "provider_status",
                "label": "Provider Status",
                "status": "done",
                "execution_kind": "http_json",
                "output_preview": {
                    "status": "ready",
                    "access_token": "hidden",
                    "message": "gateway token=hidden",
                    "request_id": "Bearer secret-token",
                },
            },
        )

        self.assertEqual(
            observation,
            'Provider Status: {"status": "ready", "access_token": "[redacted]", "message": "gateway token=[redacted]"}',
        )
        self.assertNotIn("Bearer", observation)
        self.assertNotIn("secret-token", observation)
        self.assertNotIn("hidden", observation)

    def test_build_tool_observation_entry_redacts_malformed_http_json_step_meta_preview(
        self,
    ) -> None:
        observation = build_tool_observation_entry(
            name="provider_status",
            output=None,
            step_tool_meta={
                "name": "provider_status",
                "label": "Provider Status",
                "status": "done",
                "execution_kind": "http_json",
                "output_preview": (
                    "status=ready token=hidden "
                    "query_params.access_token Bearer secret-token"
                ),
            },
        )

        self.assertEqual(
            observation,
            'Provider Status: "status=ready [redacted] [redacted] [redacted]"',
        )
        self.assertNotIn("token=hidden", observation)
        self.assertNotIn("access_token", observation)
        self.assertNotIn("Bearer", observation)
        self.assertNotIn("secret-token", observation)

    def test_build_tool_observation_entry_redacts_http_json_direct_output_fallback(
        self,
    ) -> None:
        observation = build_tool_observation_entry(
            name="provider_status",
            output={
                "status": "ready",
                "api_key": "sk-hidden",
                "message": "gateway secret=hidden",
                "request_id": "Bearer secret-token",
            },
            step_tool_meta={
                "name": "provider_status",
                "label": "Provider Status",
                "status": "done",
                "execution_kind": "http_json",
            },
        )

        self.assertEqual(
            observation,
            'Provider Status: {"status": "ready", "api_key": "[redacted]", "message": "gateway secret=[redacted]"}',
        )
        self.assertNotIn("Bearer", observation)
        self.assertNotIn("secret-token", observation)
        self.assertNotIn("sk-hidden", observation)
        self.assertNotIn("hidden", observation)

    def test_build_tool_result_summary_redacts_generic_payload_sensitive_fields(
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
            result_output_keys=("status", "message", "access_token"),
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        summary = build_tool_result_summary(
            name="provider_status",
            output={
                "status": "ready",
                "message": "gateway token=hidden",
                "access_token": "hidden",
            },
            registration=registration,
        )

        self.assertEqual(
            summary,
            "Provider Status output - status=ready, message=gateway [redacted].",
        )
        self.assertNotIn("access_token", summary or "")
        self.assertNotIn("hidden", summary or "")

    def test_build_tool_observation_entry_infers_summary_from_json_string_step_meta_preview_without_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math",
                output=None,
                step_tool_meta={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "output_preview": '{"result":7,"request_id":"req-calc-1"}',
                },
            ),
            "Hosted Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_infers_summary_from_json_string_step_meta_safe_output_without_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math",
                output=None,
                step_tool_meta={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": '{"result":7,"request_id":"req-calc-1","kind":"provider_calc","secret":"hidden"}',
                },
            ),
            "Hosted Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_infers_summary_from_quoted_json_string_step_meta_safe_output_without_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math",
                output=None,
                step_tool_meta={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": json.dumps(
                        '{"result":7,"request_id":"req-calc-1","secret":"hidden"}'
                    ),
                },
            ),
            "Hosted Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_accepts_tuple_effective_result_output_keys_from_step_meta(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="custom_lookup",
                output={
                    "tool_kind": "custom_lookup",
                    "hit_count": 1,
                    "secret": "do-not-preview",
                },
                step_tool_meta={
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "status": "done",
                    "effective_result_output_keys": (
                        "tool_kind",
                        "hit_count",
                    ),
                    "output": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                        "secret": "do-not-preview",
                    },
                },
            ),
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )

    def test_get_trace_step_display_content_prefers_tool_result_summary_over_generic_done_content(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-provider-search-summary",
            seq=4,
            type="action",
            content="Tool done: Provider Search",
            meta=SimpleNamespace(
                tool={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "result_summary": "Retrieved 2 documents (request id req-1).",
                    "effective_result_preview_keys": ["documents_total"],
                    "effective_result_output_keys": ["documents_total", "request_id"],
                    "output_preview": {"documents_total": 2},
                    "output": {
                        "documents_total": 2,
                        "request_id": "req-1",
                    },
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Retrieved 2 documents (request id req-1).\nPreview: {"documents_total":2}\nOutput: {"documents_total":2,"request_id":"req-1"}',
        )
        self.assertNotIn("Tool done: Provider Search", content)

    def test_get_trace_step_display_content_infers_result_summary_from_json_string_output_preview(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-hosted-math-preview-string",
            seq=5,
            type="action",
            content="Tool done: Hosted Math",
            meta=SimpleNamespace(
                tool={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "output_preview": '{"result":7,"request_id":"req-calc-1"}',
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Calculated result = 7 (request id req-calc-1).\nPreview: {"result":7,"request_id":"req-calc-1"}',
        )
        self.assertNotIn("Tool done: Hosted Math", content)

    def test_get_trace_step_display_content_infers_result_summary_from_quoted_json_string_output_preview(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-hosted-math-preview-quoted-string",
            seq=5,
            type="action",
            content="Tool done: Hosted Math",
            meta=SimpleNamespace(
                tool={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "output_preview": json.dumps(
                        '{"result":7,"request_id":"req-calc-1"}'
                    ),
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Calculated result = 7 (request id req-calc-1).\nPreview: {"result":7,"request_id":"req-calc-1"}',
        )
        self.assertNotIn("Tool done: Hosted Math", content)
        self.assertNotIn('\\"result\\"', content)

    def test_get_trace_step_display_content_infers_planner_summary_from_wrapped_output(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-hosted-planner-wrapped-output",
            seq=5,
            type="action",
            content="Tool done: Hosted Planner",
            meta=SimpleNamespace(
                tool={
                    "name": "hosted_planner_gateway",
                    "label": "Hosted Planner",
                    "semantic_kind": UserString("hosted_planner_gateway"),
                    "semantic_family": UserString("task_planner"),
                    "status": "done",
                    "effective_result_output_keys": UserList(
                        [UserString("plan"), UserString("steps")]
                    ),
                    "output": {
                        "plan": UserString("gather -> calculate"),
                        "steps": UserList(
                            [UserString("gather"), UserString("calculate")]
                        ),
                    },
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Planned steps - gather -> calculate.\nOutput: {"plan":"gather -> calculate","steps":["gather","calculate"]}',
        )
        self.assertNotIn("Tool done: Hosted Planner", content)

    def test_get_trace_step_markdown_meta_backfills_planner_summary_from_wrapped_output(
        self,
    ) -> None:
        class WrappedMeta:
            def model_dump(self, *, exclude_none: bool = True) -> dict[str, object]:
                del exclude_none
                return {
                    "tool": {
                        "name": "hosted_planner_gateway",
                        "label": "Hosted Planner",
                        "semantic_kind": UserString("hosted_planner_gateway"),
                        "semantic_family": UserString("task_planner"),
                        "status": "done",
                        "effective_result_output_keys": UserList(
                            [UserString("plan"), UserString("steps")]
                        ),
                        "output": {
                            "steps": UserList(
                                [UserString("gather"), UserString("calculate")]
                            ),
                        },
                    }
                }

        step = SimpleNamespace(
            id="step-hosted-planner-wrapped-meta",
            seq=5,
            type="action",
            content="Tool done: Hosted Planner",
            meta=WrappedMeta(),
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(step)

        self.assertIsNotNone(markdown_meta)
        self.assertEqual(
            markdown_meta["tool"]["result_summary"],  # type: ignore[index]
            "Planned steps - gather -> calculate.",
        )

    def test_get_trace_step_display_content_infers_retrieval_result_summary_from_safe_output_without_explicit_result_summary(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-provider-search-summary-inferred",
            seq=5,
            type="action",
            content="Tool done: Provider Search",
            meta=SimpleNamespace(
                tool={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "status": "done",
                    "effective_result_preview_keys": [
                        "hit_count",
                        "knowledge_base_id",
                    ],
                    "effective_result_output_keys": [
                        "hit_count",
                        "knowledge_base_id",
                        "request_id",
                    ],
                    "output_preview": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                    },
                    "output": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-1",
                    },
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Retrieved 2 hits (request id req-1).\nPreview: {"hit_count":2,"knowledge_base_id":"provider-kb"}\nOutput: {"hit_count":2,"knowledge_base_id":"provider-kb","request_id":"req-1"}',
        )
        self.assertNotIn("Tool done: Provider Search", content)

    def test_get_trace_step_display_content_infers_calc_result_summary_from_safe_output_without_explicit_result_summary(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-provider-math-summary-inferred",
            seq=6,
            type="action",
            content="Tool done: Provider Math",
            meta=SimpleNamespace(
                tool={
                    "name": "provider_math",
                    "label": "Provider Math",
                    "kind": "provider_calc",
                    "semantic_kind": "local_calculator",
                    "status": "done",
                    "effective_result_preview_keys": ["result"],
                    "effective_result_output_keys": ["result", "request_id"],
                    "output_preview": {
                        "result": 7,
                    },
                    "output": {
                        "result": 7,
                        "request_id": "req-calc-1",
                    },
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Calculated result = 7 (request id req-calc-1).\nPreview: {"result":7}\nOutput: {"result":7,"request_id":"req-calc-1"}',
        )
        self.assertNotIn("Tool done: Provider Math", content)

    def test_get_trace_step_display_content_drops_unsafe_request_id_from_old_safe_output(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-provider-math-unsafe-request-id",
            seq=7,
            type="action",
            content="Tool done: Provider Math",
            meta=SimpleNamespace(
                tool={
                    "name": "provider_math",
                    "label": "Provider Math",
                    "kind": "provider_calc",
                    "semantic_kind": "local_calculator",
                    "status": "done",
                    "effective_result_preview_keys": ["result"],
                    "effective_result_output_keys": ["result", "request_id"],
                    "output_preview": {
                        "result": 7,
                    },
                    "output": {
                        "result": 7,
                        "request_id": "Bearer secret-token",
                    },
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Calculated result = 7.\nPreview: {"result":7}',
        )
        self.assertNotIn("Bearer", content)
        self.assertNotIn("secret-token", content)

    def test_get_trace_step_display_content_appends_tool_registry_diagnostics_entries(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-tool-registry-diagnostics",
            seq=5,
            type="observation",
            content="Tool registry diagnostics: source=file_source skipped=1 missing=1",
            meta=SimpleNamespace(
                tool_registry={
                    "provider_source": "file_source",
                    "has_diagnostics": True,
                    "skipped_total": 1,
                    "missing_total": 1,
                    "total": 2,
                    "entries": (
                        {
                            "kind": "skipped",
                            "target": "registry_sources",
                            "count": 1,
                            "values": ("planning_suite",),
                        },
                        {
                            "kind": "missing",
                            "target": "registry_files",
                            "count": 1,
                            "values": ("/tmp/missing-registry.json",),
                        },
                    ),
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            "Tool registry diagnostics: source=file_source skipped=1 missing=1\n"
            "skipped registry sources: planning_suite\n"
            "missing registry files: /tmp/missing-registry.json",
        )

    def test_get_trace_step_display_content_redacts_tool_registry_diagnostics_values(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-tool-registry-diagnostics-sensitive",
            seq=5,
            type="observation",
            content="Tool registry diagnostics: source=file_source skipped=0 missing=0",
            meta=SimpleNamespace(
                tool_registry={
                    "provider_source": "file_source",
                    "has_diagnostics": True,
                    "skipped_total": 0,
                    "missing_total": 0,
                    "total": 1,
                    "entries": (
                        {
                            "kind": "invalid",
                            "target": "tool_executions",
                            "count": 1,
                            "values": (
                                "provider_status: unsupported tool execution kind token=hidden",
                            ),
                        },
                    ),
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            "Tool registry diagnostics: source=file_source skipped=0 missing=0\n"
            "invalid tool executions: "
            "provider_status: unsupported tool execution kind [redacted]",
        )
        self.assertNotIn("token=hidden", content)

    def test_build_tool_step_updates_and_observation_use_display_label_for_mock_plan(
        self,
    ) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Task Planner",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "mock_plan",
                    "label": "Task Planner",
                    "input": {"prompt_preview": "请帮我规划"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "plan": "Analyze request -> retrieve context -> synthesize answer.",
            "echo": True,
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="mock_plan",
            tool_input={"prompt_preview": "请帮我规划"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(success_step["content"], "Tool done: Task Planner")
        self.assertEqual(success_step["meta"]["tool"]["label"], "Task Planner")
        self.assertEqual(
            build_tool_observation_entry(name="mock_plan", output=output),
            'Task Planner: {"plan": "Analyze request -> retrieve context -> synthesize answer."}',
        )

    def test_build_tool_step_updates_observation_and_rag_followup_use_display_label_for_mock_retrieve(
        self,
    ) -> None:
        base_step = {
            "id": "step-2",
            "seq": 4,
            "type": "action",
            "content": "Tool running: Knowledge Retrieval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_2",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "mock_retrieve",
                    "label": "Knowledge Retrieval",
                    "input": {"query": "检索 demo"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "chunks": ["alpha", "beta"],
            "knowledge_base_id": "demo-kb",
            "hit_count": 2,
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="mock_retrieve",
            tool_input={"query": "检索 demo"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )
        rag_followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=5,
            model="mock-gpt",
            tool_name="mock_retrieve",
            output=output,
            token_count=2,
        )

        self.assertEqual(success_step["content"], "Tool done: Knowledge Retrieval")
        self.assertEqual(success_step["meta"]["tool"]["name"], "task_retrieve")
        self.assertEqual(
            build_tool_observation_entry(name="mock_retrieve", output=output),
            'Knowledge Retrieval: {"hit_count": 2, "knowledge_base_id": "demo-kb"}',
        )
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["content"],
            "Knowledge Retrieval returned snippets from the selected knowledge base.",
        )
