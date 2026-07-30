from __future__ import annotations

from .context import *


class ProviderStreamingMixin:
    def test_stream_task_execution_uses_stored_registry_settings_for_planning_and_preflight(
        self,
    ) -> None:
        runtime_settings = StoredSettings(
            mode="mock",
            provider="mock",
            model="mock-gpt",
            tool_registry_profile="planning_only",
            tool_registry_provider_source="suite_a",
        )
        planning_settings_seen: list[object | None] = []
        preflight_settings_seen: list[object | None] = []

        class FakeProvider:
            provider = "mock"
            model = "mock-gpt"

            def stream_generate(self, prompt: str):
                del prompt
                yield "This is a mock response from InsightAgent"

        original_get_stored_settings = getattr(
            chat_execution_module,
            "get_stored_settings",
            None,
        )
        original_get_llm_provider = chat_execution_module.get_llm_provider
        original_get_configured_tool_registry_provider = (
            chat_execution_module.get_configured_tool_registry_provider
        )
        original_build_tool_plan_artifacts = chat_execution_module.build_tool_plan_artifacts
        original_execute_preflight = (
            chat_execution_module.execute_configured_tool_registry_provider_preflight
        )
        original_update_task_status = chat_execution_module.update_task_status
        original_get_task = chat_execution_module.get_task
        original_update_task_trace_steps = chat_execution_module.update_task_trace_steps
        original_complete_task = chat_execution_module.complete_task
        original_create_message = chat_execution_module.create_message
        original_try_append_task_memory = chat_execution_module.try_append_task_memory
        original_safe_record_audit_event = chat_execution_module.safe_record_audit_event

        def fake_get_stored_settings(user_id: str) -> StoredSettings:
            self.assertEqual(user_id, "user-1")
            return runtime_settings

        def fake_get_llm_provider(user_id: str) -> FakeProvider:
            self.assertEqual(user_id, "user-1")
            return FakeProvider()

        def fake_get_configured_tool_registry_provider(*, settings=None):
            planning_settings_seen.append(settings)
            return StaticToolRegistryProvider(
                {"task_plan": get_default_tool_registry()["task_plan"]}
            )

        def fake_build_tool_plan_artifacts(
            prompt: str,
            *,
            provider: object | None = None,
            registry_provider: object | None = None,
        ) -> SimpleNamespace:
            del prompt, provider, registry_provider
            return SimpleNamespace(
                tool_plan=[],
                planning_prompt=None,
                provider_usage=None,
                planning_provider_attempted=False,
                planning_provider_used=False,
                allowed_tool_names=("task_plan",),
                allowed_tool_labels=("Task Planner",),
            )

        def fake_execute_preflight(
            *,
            task_id: str,
            step_id: str,
            seq: int,
            model: str,
            trace_steps: list[dict[str, object]],
            persist_trace_fn,
            record_audit_event_fn,
            settings=None,
        ) -> dict[str, object]:
            del task_id, step_id, seq, model, trace_steps, persist_trace_fn, record_audit_event_fn
            preflight_settings_seen.append(settings)
            return {
                "provider": StaticToolRegistryProvider({}),
                "provider_source_name": "suite_a",
            }

        try:
            chat_execution_module.get_stored_settings = fake_get_stored_settings
            chat_execution_module.get_llm_provider = fake_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                fake_get_configured_tool_registry_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                fake_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                fake_execute_preflight
            )
            chat_execution_module.update_task_status = lambda *args, **kwargs: None
            chat_execution_module.get_task = lambda *args, **kwargs: {"status": "running"}
            chat_execution_module.update_task_trace_steps = lambda *args, **kwargs: None
            chat_execution_module.complete_task = lambda *args, **kwargs: None
            chat_execution_module.create_message = lambda *args, **kwargs: None
            chat_execution_module.try_append_task_memory = lambda *args, **kwargs: None
            chat_execution_module.safe_record_audit_event = lambda *args, **kwargs: None

            events = list(
                chat_execution_module.stream_task_execution(
                    task_id="task-1",
                    session_id="session-1",
                    user_id="user-1",
                    prompt="please plan with user-scoped registry settings",
                )
            )
        finally:
            if original_get_stored_settings is not None:
                chat_execution_module.get_stored_settings = original_get_stored_settings
            chat_execution_module.get_llm_provider = original_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                original_get_configured_tool_registry_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                original_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                original_execute_preflight
            )
            chat_execution_module.update_task_status = original_update_task_status
            chat_execution_module.get_task = original_get_task
            chat_execution_module.update_task_trace_steps = original_update_task_trace_steps
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.create_message = original_create_message
            chat_execution_module.try_append_task_memory = original_try_append_task_memory
            chat_execution_module.safe_record_audit_event = original_safe_record_audit_event

        self.assertEqual(planning_settings_seen, [runtime_settings])
        self.assertEqual(preflight_settings_seen, [runtime_settings])
        trace_payload = next(
            json.loads(event.split("data: ", 1)[1])
            for event in events
            if event.startswith("event: trace\n")
        )
        meta = trace_payload["step"]["meta"]
        self.assertEqual(meta["tool_registry_profile"], "planning_only")
        self.assertEqual(meta["tool_registry_provider_source"], "suite_a")
        self.assertEqual(meta["allowed_tool_labels"], ["Task Planner"])

    def test_mock_llm_provider_generate_summarizes_tool_observations(self) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Task Planner: {"plan": "Analyze request -> Evaluate calculation -> Synthesize final answer"}\n'
            'Calculator: {"expression": "1+2", "result": 3.0}\n'
            'Provider Search: {"hit_count": 2, "knowledge_base_id": "demo-kb"}'
        )

        self.assertIn("This is a mock response from InsightAgent.", result.content)
        self.assertIn(
            "Summary: Planned steps - Analyze request -> Evaluate calculation -> Synthesize final answer. "
            "Calculated 1+2 = 3.0. Retrieved 2 hits.",
            result.content,
        )
        self.assertNotIn("from knowledge base demo-kb", result.content)
        self.assertIn("Prompt received: need answer", result.content)
        self.assertNotIn("Tool observations:", result.content)
        self.assertNotIn(
            'Calculator: {"expression": "1+2", "result": 3.0}',
            result.content,
        )
        self.assertNotIn(
            'Provider Search: {"hit_count": 2, "knowledge_base_id": "demo-kb"}',
            result.content,
        )

    def test_mock_llm_provider_generate_summarizes_structured_plan_steps_and_projected_retrieval_outputs(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Task Planner Suite: {"steps": ["Analyze request", "Retrieve supporting context", "Synthesize final answer"]}\n'
            'Provider Search: {"documents_total": 2}'
        )

        self.assertIn("This is a mock response from InsightAgent.", result.content)
        self.assertIn(
            "Summary: Planned steps - Analyze request -> Retrieve supporting context -> Synthesize final answer. "
            "Retrieved 2 documents.",
            result.content,
        )
        self.assertIn("Prompt received: need answer", result.content)
        self.assertNotIn(
            'Task Planner Suite: {"steps": ["Analyze request", "Retrieve supporting context", "Synthesize final answer"]}',
            result.content,
        )
        self.assertNotIn(
            'Provider Search: {"documents_total": 2}',
            result.content,
        )

    def test_mock_llm_provider_generate_redacts_sensitive_text_in_structured_plan_steps(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Task Planner Suite: {"steps": ["Analyze request", "Call gateway token=hidden", "Auth Bearer secret-token"]}'
        )

        self.assertIn(
            "Summary: Planned steps - Analyze request -> Call gateway token=[redacted] -> Auth [redacted].",
            result.content,
        )
        self.assertNotIn("token=hidden", result.content)
        self.assertNotIn("Bearer", result.content)
        self.assertNotIn("secret-token", result.content)

    def test_mock_provider_normalize_plan_steps_accepts_tuple(self) -> None:
        self.assertEqual(
            mock_provider_module._normalize_plan_steps(  # type: ignore[attr-defined]
                (" Analyze request ", "", "Synthesize final answer")
            ),
            [
                "Analyze request",
                "Synthesize final answer",
            ],
        )

    def test_mock_llm_provider_generate_preserves_request_id_for_projected_retrieval_outputs(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Search: {"documents_total": 2, "request_id": "req-1"}'
        )

        self.assertIn(
            "Summary: Retrieved 2 documents (request id req-1).",
            result.content,
        )
        self.assertNotIn("Provider Search completed.", result.content)
        self.assertNotIn(
            'Provider Search: {"documents_total": 2, "request_id": "req-1"}',
            result.content,
        )

    def test_mock_llm_provider_generate_includes_provider_kb_for_real_documents_total_outputs(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Hosted Search: {"semantic_kind": "hosted_search_gateway", "semantic_family": "knowledge_retrieval", '
            '"documents_total": 2, "knowledge_base_id": "hosted-kb", "request_id": "req-hosted-1"}'
        )

        self.assertIn(
            "Summary: Retrieved 2 documents from hosted-kb (request id req-hosted-1).",
            result.content,
        )
        self.assertNotIn("from knowledge base hosted-kb", result.content)
        self.assertNotIn(
            'Hosted Search: {"semantic_kind": "hosted_search_gateway"',
            result.content,
        )

    def test_mock_llm_provider_generate_infers_provider_kb_for_label_only_real_documents_total_outputs(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Hosted Search: {"documents_total": 2, "knowledge_base_id": "hosted-kb", "request_id": "req-hosted-1"}'
        )

        self.assertIn(
            "Summary: Retrieved 2 documents from hosted-kb (request id req-hosted-1).",
            result.content,
        )
        self.assertNotIn("from knowledge base hosted-kb", result.content)
        self.assertNotIn(
            'Hosted Search: {"documents_total": 2, "knowledge_base_id": "hosted-kb", "request_id": "req-hosted-1"}',
            result.content,
        )

    def test_mock_llm_provider_generate_does_not_imply_local_kb_for_runtime_override_real_tool_observation(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Search: {"tool_kind": "provider_search", "hit_count": 2, "knowledge_base_id": "provider-kb"}'
        )

        self.assertIn("This is a mock response from InsightAgent.", result.content)
        self.assertIn("Summary: Retrieved 2 hits.", result.content)
        self.assertNotIn("from knowledge base provider-kb", result.content)

    def test_mock_llm_provider_generate_does_not_imply_local_kb_for_name_only_real_tool_observation(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Search: {"hit_count": 2, "knowledge_base_id": "provider-kb", "request_id": "req-1"}'
        )

        self.assertIn(
            "Summary: Retrieved 2 hits (request id req-1).",
            result.content,
        )
        self.assertNotIn("from knowledge base provider-kb", result.content)

    def test_mock_llm_provider_generate_does_not_imply_local_kb_for_productized_retrieval_label_on_real_tool_observation(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Search [retrieval]: {"hit_count": 2, "knowledge_base_id": "provider-kb", "request_id": "req-1"}'
        )

        self.assertIn(
            "Summary: Retrieved 2 hits (request id req-1).",
            result.content,
        )
        self.assertNotIn("from knowledge base provider-kb", result.content)

    def test_mock_llm_provider_generate_keeps_local_kb_summary_for_builtin_retrieval_name_only_observation(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Knowledge Retrieval: {"hit_count": 2, "knowledge_base_id": "demo-kb", "request_id": "req-1"}'
        )

        self.assertIn(
            "Summary: Retrieved 2 hits from knowledge base demo-kb (request id req-1).",
            result.content,
        )

    def test_mock_llm_provider_generate_preserves_request_id_for_runtime_override_real_retrieval_hit_projection(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Search: {"tool_kind": "provider_search", "hit_count": 2, "knowledge_base_id": "provider-kb", "request_id": "req-1"}'
        )

        self.assertIn(
            "Summary: Retrieved 2 hits (request id req-1).",
            result.content,
        )
        self.assertNotIn(
            'Provider Search: {"tool_kind": "provider_search", "hit_count": 2, "knowledge_base_id": "provider-kb", "request_id": "req-1"}',
            result.content,
        )
        self.assertNotIn("from knowledge base provider-kb", result.content)

    def test_mock_llm_provider_generate_preserves_request_id_for_projected_calc_outputs(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Math: {"result": 7, "request_id": "req-calc-1", "tool_kind": "provider_calc"}'
        )

        self.assertIn(
            "Summary: Calculated result = 7 (request id req-calc-1).",
            result.content,
        )
        self.assertNotIn(
            'Provider Math: {"result": 7, "request_id": "req-calc-1", "tool_kind": "provider_calc"}',
            result.content,
        )

    def test_mock_llm_provider_generate_drops_unsafe_request_id_for_projected_calc_outputs(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Math: {"result": 7, "request_id": "Bearer secret-token", "tool_kind": "provider_calc"}'
        )

        self.assertIn(
            "Summary: Calculated result = 7.",
            result.content,
        )
        self.assertNotIn("request id Bearer", result.content)
        self.assertNotIn("secret-token", result.content)
        self.assertNotIn(
            'Provider Math: {"result": 7, "request_id": "Bearer secret-token", "tool_kind": "provider_calc"}',
            result.content,
        )

    def test_mock_llm_provider_generate_infers_calc_summary_for_productized_calculator_label_without_semantic_hints(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Hosted Math [calculator]: {"result": 7, "request_id": "req-calc-1"}'
        )

        self.assertIn(
            "Summary: Calculated result = 7 (request id req-calc-1).",
            result.content,
        )
        self.assertNotIn(
            'Hosted Math [calculator]: {"result": 7, "request_id": "req-calc-1"}',
            result.content,
        )

    def test_mock_llm_provider_generate_infers_retrieval_summary_from_structural_kind_without_semantic_family(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Hosted Search: {"kind": "provider_retrieval", "hit_count": 2, "knowledge_base_id": "provider-kb", "request_id": "req-1"}'
        )

        self.assertIn(
            "Summary: Retrieved 2 hits (request id req-1).",
            result.content,
        )
        self.assertNotIn("from knowledge base provider-kb", result.content)
        self.assertNotIn(
            'Hosted Search: {"kind": "provider_retrieval", "hit_count": 2, "knowledge_base_id": "provider-kb", "request_id": "req-1"}',
            result.content,
        )

    def test_mock_llm_provider_generate_infers_calc_summary_from_structural_kind_without_semantic_family(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Hosted Math: {"kind": "provider_calc", "result": 7, "request_id": "req-calc-1"}'
        )

        self.assertIn(
            "Summary: Calculated result = 7 (request id req-calc-1).",
            result.content,
        )
        self.assertNotIn(
            'Hosted Math: {"kind": "provider_calc", "result": 7, "request_id": "req-calc-1"}',
            result.content,
        )

    def test_mock_llm_provider_generate_infers_calc_summary_for_name_only_real_tool_observation(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Hosted Math: {"result": 7, "request_id": "req-calc-1"}'
        )

        self.assertIn(
            "Summary: Calculated result = 7 (request id req-calc-1).",
            result.content,
        )
        self.assertNotIn(
            'Hosted Math: {"result": 7, "request_id": "req-calc-1"}',
            result.content,
        )

    def test_mock_llm_provider_generate_infers_calc_summary_from_quoted_json_observation_payloads(
        self,
    ) -> None:
        provider = MockLLMProvider()

        observation_payloads = [
            json.dumps('{"result":7,"request_id":"req-calc-1","secret":"hidden"}'),
            '"{"result":7,"request_id":"req-calc-1","secret":"hidden"}"',
        ]

        for observation_payload in observation_payloads:
            with self.subTest(observation_payload=observation_payload):
                result = provider.generate(
                    "need answer\n\nTool observations:\n"
                    f"Hosted Math: {observation_payload}"
                )

                self.assertIn(
                    "Summary: Calculated result = 7 (request id req-calc-1).",
                    result.content,
                )
                self.assertNotIn(
                    f"Hosted Math: {observation_payload}",
                    result.content,
                )
                self.assertNotIn("Tool context:", result.content)
                self.assertNotIn("secret", result.content)

    def test_mock_llm_provider_generate_infers_summary_from_nested_preview_observation_payload(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            "Hosted Math: "
            + json.dumps(
                {
                    "output_preview": json.dumps(
                        {
                            "result": 7,
                            "request_id": "req-calc-1",
                            "secret": "hidden",
                        }
                    ),
                    "semantic_family": "local_calculator",
                }
            )
        )

        self.assertIn(
            "Summary: Calculated result = 7 (request id req-calc-1).",
            result.content,
        )
        self.assertNotIn("output_preview=", result.content)
        self.assertNotIn("secret", result.content)

    def test_mock_llm_provider_generate_redacts_malformed_observation_text_field_paths(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            "Provider Status: status=ready token=hidden "
            "query_params.access_token Bearer secret-token"
        )

        self.assertIn(
            "Summary: status=ready token=[redacted] [redacted] [redacted]",
            result.content,
        )
        self.assertNotIn("token=hidden", result.content)
        self.assertNotIn("access_token", result.content)
        self.assertNotIn("Bearer", result.content)
        self.assertNotIn("secret-token", result.content)

    def test_mock_llm_provider_generate_keeps_real_retrieval_semantics_from_nested_safe_output(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            "Provider Search: "
            + json.dumps(
                {
                    "safe_output": json.dumps(
                        {
                            "hit_count": 2,
                            "knowledge_base_id": "provider-kb",
                        }
                    ),
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "request_id": "req-1",
                }
            )
        )

        self.assertIn(
            "Summary: Retrieved 2 hits (request id req-1).",
            result.content,
        )
        self.assertNotIn("from knowledge base provider-kb", result.content)
        self.assertNotIn("safe_output=", result.content)

    def test_mock_llm_provider_generate_summarizes_human_readable_retrieval_observations(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            "Provider Search: Retrieved 2 documents (request id req-1)."
        )

        self.assertIn(
            "Summary: Retrieved 2 documents (request id req-1).",
            result.content,
        )
        self.assertNotIn(
            "Tool context: Provider Search: Retrieved 2 documents (request id req-1).",
            result.content,
        )

    def test_mock_llm_provider_generate_summarizes_generic_structured_tool_outputs_before_completed_fallback(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Status: {"status": "ready", "provider_source": "suite_a"}'
        )

        self.assertIn(
            "Summary: Provider Status output - status=ready, provider_source=suite_a.",
            result.content,
        )
        self.assertNotIn("Provider Status completed.", result.content)
        self.assertNotIn(
            'Provider Status: {"status": "ready", "provider_source": "suite_a"}',
            result.content,
        )

    def test_mock_llm_provider_generate_drops_unsafe_request_id_from_generic_structured_outputs(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Status: {"status": "ready", "request_id": "Bearer secret-token", "provider_source": "suite_a"}'
        )

        self.assertIn(
            "Summary: Provider Status output - status=ready, provider_source=suite_a.",
            result.content,
        )
        self.assertNotIn("Bearer", result.content)
        self.assertNotIn("secret-token", result.content)
        self.assertNotIn("request_id=Bearer", result.content)

    def test_mock_llm_provider_generate_drops_sensitive_keys_from_generic_structured_outputs(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Status: {"status": "ready", "access_token": "hidden", "api_key": "sk-hidden", "provider_source": "suite_a"}'
        )

        self.assertIn(
            "Summary: Provider Status output - status=ready, provider_source=suite_a.",
            result.content,
        )
        self.assertNotIn("access_token", result.content)
        self.assertNotIn("api_key", result.content)
        self.assertNotIn("sk-hidden", result.content)
        self.assertNotIn("hidden", result.content)

    def test_mock_llm_provider_generate_drops_compound_secret_keys_from_generic_structured_outputs(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Status: {"status": "ready", "client_secret": "cs-hidden", "provider_source": "suite_a"}'
        )

        self.assertIn(
            "Summary: Provider Status output - status=ready, provider_source=suite_a.",
            result.content,
        )
        self.assertNotIn("client_secret", result.content)
        self.assertNotIn("cs-hidden", result.content)

    def test_mock_llm_provider_generate_redacts_sensitive_assignments_in_generic_structured_outputs(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Status: {"status": "ready", "message": "gateway token=hidden"}'
        )

        self.assertIn(
            "Summary: Provider Status output - status=ready, message=gateway token=[redacted].",
            result.content,
        )
        self.assertNotIn("token=hidden", result.content)
        self.assertNotIn("hidden", result.content)

    def test_mock_llm_provider_generate_redacts_access_token_assignments_in_generic_structured_outputs(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            'Provider Status: {"status": "ready", "message": "access_token=hidden"}'
        )

        self.assertIn(
            "Summary: Provider Status output - status=ready, message=access_token=[redacted].",
            result.content,
        )
        self.assertNotIn("access_token=hidden", result.content)
        self.assertNotIn("hidden", result.content)

    def test_mock_llm_provider_generate_redacts_sensitive_assignments_in_text_observation_summary(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            "Provider Status: upstream gateway token=hidden"
        )

        self.assertIn(
            "Summary: upstream gateway token=[redacted]",
            result.content,
        )
        self.assertNotIn("token=hidden", result.content)
        self.assertNotIn("hidden", result.content)

    def test_mock_llm_provider_generate_redacts_sensitive_assignments_in_tool_context_fallback(
        self,
    ) -> None:
        provider = MockLLMProvider()

        result = provider.generate(
            "need answer\n\nTool observations:\n"
            "unstructured upstream secret=hidden"
        )

        self.assertIn(
            "Tool context: unstructured upstream secret=[redacted]",
            result.content,
        )
        self.assertNotIn("secret=hidden", result.content)
        self.assertNotIn("hidden", result.content)

    def test_openai_compatible_provider_generate_accepts_output_text_message_parts(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )
        provider._request_json = lambda payload: {  # type: ignore[method-assign]
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "output_text", "text": "structured answer"}
                        ]
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 7,
                "completion_tokens": 2,
                "total_tokens": 9,
            },
        }

        result = provider.generate("hello")

        self.assertEqual(result.content, "structured answer")
        self.assertIsNotNone(result.usage)
        assert result.usage is not None
        self.assertEqual(result.usage.total_tokens, 9)

    def test_openai_compatible_provider_generate_accepts_raw_responses_output_payload(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )
        provider._request_json = lambda payload: {  # type: ignore[method-assign]
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "responses answer"}
                    ]
                }
            ],
            "usage": {
                "input_tokens": 6,
                "output_tokens": 3,
            },
        }

        result = provider.generate("hello")

        self.assertEqual(result.content, "responses answer")
        self.assertIsNotNone(result.usage)
        assert result.usage is not None
        self.assertEqual(result.usage.prompt_tokens, 6)
        self.assertEqual(result.usage.completion_tokens, 3)
        self.assertIsNone(result.usage.total_tokens)

    def test_openai_compatible_provider_generate_accepts_top_level_output_text(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )
        provider._request_json = lambda payload: {  # type: ignore[method-assign]
            "output_text": "top level answer",
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 2,
                "total_tokens": 7,
            },
        }

        result = provider.generate("hello")

        self.assertEqual(result.content, "top level answer")
        self.assertIsNotNone(result.usage)
        assert result.usage is not None
        self.assertEqual(result.usage.total_tokens, 7)

    def test_openai_compatible_provider_generate_accepts_top_level_content_text(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )
        provider._request_json = lambda payload: {  # type: ignore[method-assign]
            "content": {"text": "nested top level answer"},
        }

        result = provider.generate("hello")

        self.assertEqual(result.content, "nested top level answer")

    def test_openai_compatible_provider_generate_accepts_typed_chat_completions_response_object(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )
        provider._request_json = lambda payload: {  # type: ignore[method-assign]
            "choices": [
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=[
                            SimpleNamespace(
                                type="output_text",
                                text="typed chat completion answer",
                            )
                        ]
                    )
                )
            ]
        }

        result = provider.generate("hello")

        self.assertEqual(result.content, "typed chat completion answer")

    def test_openai_compatible_provider_generate_accepts_typed_responses_output_object(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )
        provider._request_json = lambda payload: {  # type: ignore[method-assign]
            "output": [
                SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            type="output_text",
                            text="typed responses answer",
                        )
                    ]
                )
            ]
        }

        result = provider.generate("hello")

        self.assertEqual(result.content, "typed responses answer")

    def test_openai_compatible_provider_generate_accepts_fully_typed_response_object(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )
        provider._request_json = lambda payload: SimpleNamespace(  # type: ignore[method-assign]
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="fully typed root answer")
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=5,
                completion_tokens=2,
                total_tokens=7,
            ),
        )

        result = provider.generate("hello")

        self.assertEqual(result.content, "fully typed root answer")
        self.assertIsNotNone(result.usage)
        assert result.usage is not None
        self.assertEqual(result.usage.total_tokens, 7)

    def test_openai_compatible_provider_generate_accepts_typed_usage_object(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )
        provider._request_json = lambda payload: {  # type: ignore[method-assign]
            "content": "typed usage answer",
            "usage": SimpleNamespace(
                input_tokens=8,
                output_tokens="4",
                total_tokens=12,
            ),
        }

        result = provider.generate("hello")

        self.assertEqual(result.content, "typed usage answer")
        self.assertIsNotNone(result.usage)
        assert result.usage is not None
        self.assertEqual(result.usage.prompt_tokens, 8)
        self.assertEqual(result.usage.completion_tokens, 4)
        self.assertEqual(result.usage.total_tokens, 12)

    def test_openai_compatible_provider_extract_delta_content_accepts_output_text_parts(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )

        delta = provider._extract_delta_content(  # type: ignore[attr-defined]
            {
                "choices": [
                    {
                        "delta": {
                            "content": [
                                {"type": "output_text", "text": "chunk-a"},
                                {"type": "text", "text": "chunk-b"},
                            ]
                        }
                    }
                ]
            }
        )

        self.assertEqual(delta, "chunk-achunk-b")

    def test_openai_compatible_provider_extract_delta_content_accepts_delta_text_field(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )

        delta = provider._extract_delta_content(  # type: ignore[attr-defined]
            {"delta": {"text": "delta-text-answer"}}
        )

        self.assertEqual(delta, "delta-text-answer")

    def test_openai_compatible_provider_extract_delta_content_accepts_typed_delta_object(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )

        delta = provider._extract_delta_content(  # type: ignore[attr-defined]
            {
                "choices": [
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content=[
                                SimpleNamespace(
                                    type="output_text",
                                    text="typed-delta-a",
                                ),
                                SimpleNamespace(type="text", text="typed-delta-b"),
                            ]
                        )
                    )
                ]
            }
        )

        self.assertEqual(delta, "typed-delta-atyped-delta-b")

    def test_openai_compatible_provider_extract_delta_content_accepts_top_level_output_text(
        self,
    ) -> None:
        provider = OpenAICompatibleLLMProvider(
            model="gpt-4.1-mini",
            provider="openai",
            base_url="https://example.test/v1",
            api_key="sk-test",
        )

        delta = provider._extract_delta_content(  # type: ignore[attr-defined]
            {"output_text": "top-level-stream-chunk"}
        )

        self.assertEqual(delta, "top-level-stream-chunk")

    def test_stream_task_execution_with_mock_provider_surfaces_tool_observation_summary_in_final_answer(
        self,
    ) -> None:
        runtime_settings = StoredSettings(
            mode="mock",
            provider="mock",
            model="mock-gpt",
            tool_registry_profile="default",
            tool_registry_provider_source="default",
        )
        completed_trace_steps: list[dict[str, object]] = []

        original_get_stored_settings = getattr(
            chat_execution_module,
            "get_stored_settings",
            None,
        )
        original_get_llm_provider = chat_execution_module.get_llm_provider
        original_get_configured_tool_registry_provider = (
            chat_execution_module.get_configured_tool_registry_provider
        )
        original_build_tool_plan_artifacts = chat_execution_module.build_tool_plan_artifacts
        original_execute_preflight = (
            chat_execution_module.execute_configured_tool_registry_provider_preflight
        )
        original_execute_tool_plan_item_service_execution = (
            chat_execution_module.execute_tool_plan_item_service_execution
        )
        original_execute_tool_plan_item_service_actions = (
            chat_execution_module.execute_tool_plan_item_service_actions
        )
        original_update_task_status = chat_execution_module.update_task_status
        original_get_task = chat_execution_module.get_task
        original_update_task_trace_steps = chat_execution_module.update_task_trace_steps
        original_complete_task = chat_execution_module.complete_task
        original_create_message = chat_execution_module.create_message
        original_try_append_task_memory = chat_execution_module.try_append_task_memory
        original_safe_record_audit_event = chat_execution_module.safe_record_audit_event

        def fake_get_stored_settings(user_id: str) -> StoredSettings:
            self.assertEqual(user_id, "user-1")
            return runtime_settings

        def fake_get_llm_provider(user_id: str) -> MockLLMProvider:
            self.assertEqual(user_id, "user-1")
            return MockLLMProvider()

        def fake_build_tool_plan_artifacts(
            prompt: str,
            *,
            provider: object | None = None,
            registry_provider: object | None = None,
        ) -> SimpleNamespace:
            del prompt, provider, registry_provider
            return SimpleNamespace(
                tool_plan=[{"name": "calc_eval", "input": {"expression": "1+2"}}],
                planning_prompt=None,
                provider_usage=None,
                planning_provider_attempted=False,
                planning_provider_used=False,
                allowed_tool_names=("calc_eval",),
                allowed_tool_labels=("Calculator",),
            )

        def fake_execute_preflight(
            *,
            task_id: str,
            step_id: str,
            seq: int,
            model: str,
            trace_steps: list[dict[str, object]],
            persist_trace_fn,
            record_audit_event_fn,
            settings=None,
        ) -> dict[str, object]:
            del task_id, step_id, seq, model, trace_steps, persist_trace_fn, record_audit_event_fn, settings
            return {
                "provider": StaticToolRegistryProvider(
                    {"calc_eval": get_default_tool_registry()["calc_eval"]}
                ),
                "provider_source_name": "default",
            }

        def fake_execute_tool_plan_item_service_execution(**kwargs):
            del kwargs
            yield {
                "kind": "result",
                "result": {
                    "service_actions": [],
                },
            }

        def fake_execute_tool_plan_item_service_actions(**kwargs):
            kwargs["tool_observations"].append(
                'Task Planner: {"plan": "Analyze request -> Evaluate calculation -> Synthesize final answer"}'
            )
            kwargs["tool_observations"].append(
                'Calculator: {"expression": "1+2", "result": 3.0}'
            )
            yield {
                "kind": "result",
                "result": {
                    "seq_cursor": int(kwargs["seq_cursor"]),
                    "should_return": False,
                },
            }

        try:
            chat_execution_module.get_stored_settings = fake_get_stored_settings
            chat_execution_module.get_llm_provider = fake_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                lambda *, settings=None: StaticToolRegistryProvider(
                    {"calc_eval": get_default_tool_registry()["calc_eval"]}
                )
            )
            chat_execution_module.build_tool_plan_artifacts = (
                fake_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                fake_execute_preflight
            )
            chat_execution_module.execute_tool_plan_item_service_execution = (
                fake_execute_tool_plan_item_service_execution
            )
            chat_execution_module.execute_tool_plan_item_service_actions = (
                fake_execute_tool_plan_item_service_actions
            )
            chat_execution_module.update_task_status = lambda *args, **kwargs: None
            chat_execution_module.get_task = lambda *args, **kwargs: {"status": "running"}
            chat_execution_module.update_task_trace_steps = lambda *args, **kwargs: None
            chat_execution_module.complete_task = (
                lambda *, trace_steps, **kwargs: completed_trace_steps.extend(trace_steps)
            )
            chat_execution_module.create_message = lambda *args, **kwargs: None
            chat_execution_module.try_append_task_memory = lambda *args, **kwargs: None
            chat_execution_module.safe_record_audit_event = lambda *args, **kwargs: None

            list(
                chat_execution_module.stream_task_execution(
                    task_id="task-1",
                    session_id="session-1",
                    user_id="user-1",
                    prompt="please calculate with mock tool observations",
                )
            )
        finally:
            if original_get_stored_settings is not None:
                chat_execution_module.get_stored_settings = original_get_stored_settings
            chat_execution_module.get_llm_provider = original_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                original_get_configured_tool_registry_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                original_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                original_execute_preflight
            )
            chat_execution_module.execute_tool_plan_item_service_execution = (
                original_execute_tool_plan_item_service_execution
            )
            chat_execution_module.execute_tool_plan_item_service_actions = (
                original_execute_tool_plan_item_service_actions
            )
            chat_execution_module.update_task_status = original_update_task_status
            chat_execution_module.get_task = original_get_task
            chat_execution_module.update_task_trace_steps = original_update_task_trace_steps
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.create_message = original_create_message
            chat_execution_module.try_append_task_memory = original_try_append_task_memory
            chat_execution_module.safe_record_audit_event = original_safe_record_audit_event

        final_answer_step = completed_trace_steps[-1]
        self.assertIn(
            "This is a mock response from InsightAgent.",
            final_answer_step["content"],
        )
        self.assertIn(
            "Summary: Planned steps - Analyze request -> Evaluate calculation -> Synthesize final answer. Calculated 1+2 = 3.0.",
            final_answer_step["content"],
        )
        self.assertIn(
            "Prompt received: please calculate with mock tool observations",
            final_answer_step["content"],
        )
        self.assertNotIn("Tool observations:", final_answer_step["content"])
        self.assertNotIn(
            'Calculator: {"expression": "1+2", "result": 3.0}',
            final_answer_step["content"],
        )

    def test_stream_task_execution_with_mock_provider_summarizes_structured_plan_steps_and_projected_real_retrieval_outputs(
        self,
    ) -> None:
        runtime_settings = StoredSettings(
            mode="mock",
            provider="mock",
            model="mock-gpt",
            tool_registry_profile="default",
            tool_registry_provider_source="default",
        )
        completed_trace_steps: list[dict[str, object]] = []

        original_get_stored_settings = getattr(
            chat_execution_module,
            "get_stored_settings",
            None,
        )
        original_get_llm_provider = chat_execution_module.get_llm_provider
        original_get_configured_tool_registry_provider = (
            chat_execution_module.get_configured_tool_registry_provider
        )
        original_build_tool_plan_artifacts = chat_execution_module.build_tool_plan_artifacts
        original_execute_preflight = (
            chat_execution_module.execute_configured_tool_registry_provider_preflight
        )
        original_execute_tool_plan_item_service_execution = (
            chat_execution_module.execute_tool_plan_item_service_execution
        )
        original_execute_tool_plan_item_service_actions = (
            chat_execution_module.execute_tool_plan_item_service_actions
        )
        original_update_task_status = chat_execution_module.update_task_status
        original_get_task = chat_execution_module.get_task
        original_update_task_trace_steps = chat_execution_module.update_task_trace_steps
        original_complete_task = chat_execution_module.complete_task
        original_create_message = chat_execution_module.create_message
        original_try_append_task_memory = chat_execution_module.try_append_task_memory
        original_safe_record_audit_event = chat_execution_module.safe_record_audit_event

        def fake_get_stored_settings(user_id: str) -> StoredSettings:
            self.assertEqual(user_id, "user-1")
            return runtime_settings

        def fake_get_llm_provider(user_id: str) -> MockLLMProvider:
            self.assertEqual(user_id, "user-1")
            return MockLLMProvider()

        def fake_build_tool_plan_artifacts(
            prompt: str,
            *,
            provider: object | None = None,
            registry_provider: object | None = None,
        ) -> SimpleNamespace:
            del prompt, provider, registry_provider
            return SimpleNamespace(
                tool_plan=[
                    {"name": "task_plan", "input": {"prompt_preview": "plan and retrieve"}},
                    {"name": "provider_search", "input": {"query": "revenue trend"}},
                ],
                planning_prompt=None,
                provider_usage=None,
                planning_provider_attempted=False,
                planning_provider_used=False,
                allowed_tool_names=("task_plan", "provider_search"),
                allowed_tool_labels=("Task Planner Suite", "Provider Search"),
            )

        def fake_execute_preflight(
            *,
            task_id: str,
            step_id: str,
            seq: int,
            model: str,
            trace_steps: list[dict[str, object]],
            persist_trace_fn,
            record_audit_event_fn,
            settings=None,
        ) -> dict[str, object]:
            del task_id, step_id, seq, model, trace_steps, persist_trace_fn, record_audit_event_fn, settings
            return {
                "provider": StaticToolRegistryProvider(
                    {
                        "task_plan": get_default_tool_registry()["task_plan"],
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
                            },
                            result_preview_keys=("documents_total",),
                            result_output_keys=("documents_total",),
                            runtime_semantic_kind="provider_search",
                        ),
                    }
                ),
                "provider_source_name": "default",
            }

        def fake_execute_tool_plan_item_service_execution(**kwargs):
            del kwargs
            yield {
                "kind": "result",
                "result": {
                    "service_actions": [],
                },
            }

        def fake_execute_tool_plan_item_service_actions(**kwargs):
            kwargs["tool_observations"].append(
                'Task Planner Suite: {"steps": ["Analyze request", "Retrieve supporting context", "Synthesize final answer"]}'
            )
            kwargs["tool_observations"].append(
                'Provider Search: {"documents_total": 2}'
            )
            yield {
                "kind": "result",
                "result": {
                    "seq_cursor": int(kwargs["seq_cursor"]),
                    "should_return": False,
                },
            }

        try:
            chat_execution_module.get_stored_settings = fake_get_stored_settings
            chat_execution_module.get_llm_provider = fake_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                lambda *, settings=None: StaticToolRegistryProvider(
                    {"task_plan": get_default_tool_registry()["task_plan"]}
                )
            )
            chat_execution_module.build_tool_plan_artifacts = (
                fake_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                fake_execute_preflight
            )
            chat_execution_module.execute_tool_plan_item_service_execution = (
                fake_execute_tool_plan_item_service_execution
            )
            chat_execution_module.execute_tool_plan_item_service_actions = (
                fake_execute_tool_plan_item_service_actions
            )
            chat_execution_module.update_task_status = lambda *args, **kwargs: None
            chat_execution_module.get_task = lambda *args, **kwargs: {"status": "running"}
            chat_execution_module.update_task_trace_steps = lambda *args, **kwargs: None
            chat_execution_module.complete_task = (
                lambda *, trace_steps, **kwargs: completed_trace_steps.extend(trace_steps)
            )
            chat_execution_module.create_message = lambda *args, **kwargs: None
            chat_execution_module.try_append_task_memory = lambda *args, **kwargs: None
            chat_execution_module.safe_record_audit_event = lambda *args, **kwargs: None

            list(
                chat_execution_module.stream_task_execution(
                    task_id="task-1",
                    session_id="session-1",
                    user_id="user-1",
                    prompt="please plan and search with mock tool observations",
                )
            )
        finally:
            if original_get_stored_settings is not None:
                chat_execution_module.get_stored_settings = original_get_stored_settings
            chat_execution_module.get_llm_provider = original_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                original_get_configured_tool_registry_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                original_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                original_execute_preflight
            )
            chat_execution_module.execute_tool_plan_item_service_execution = (
                original_execute_tool_plan_item_service_execution
            )
            chat_execution_module.execute_tool_plan_item_service_actions = (
                original_execute_tool_plan_item_service_actions
            )
            chat_execution_module.update_task_status = original_update_task_status
            chat_execution_module.get_task = original_get_task
            chat_execution_module.update_task_trace_steps = original_update_task_trace_steps
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.create_message = original_create_message
            chat_execution_module.try_append_task_memory = original_try_append_task_memory
            chat_execution_module.safe_record_audit_event = original_safe_record_audit_event

        final_answer_step = completed_trace_steps[-1]
        self.assertIn(
            "Summary: Planned steps - Analyze request -> Retrieve supporting context -> Synthesize final answer. Retrieved 2 documents.",
            final_answer_step["content"],
        )
        self.assertNotIn(
            'Task Planner Suite: {"steps": ["Analyze request", "Retrieve supporting context", "Synthesize final answer"]}',
            final_answer_step["content"],
        )
        self.assertNotIn(
            'Provider Search: {"documents_total": 2}',
            final_answer_step["content"],
        )

    def test_stream_task_execution_reuses_runtime_provider_identity_when_provider_object_has_no_attrs(
        self,
    ) -> None:
        runtime_settings = StoredSettings(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com/v1",
            api_key="sk-runtime",
            tool_registry_profile="default",
            tool_registry_provider_source="default",
        )
        preflight_models_seen: list[str] = []
        iteration_models_seen: list[str] = []
        completed_trace_steps: list[dict[str, object]] = []

        class ProviderWithoutIdentity:
            def stream_generate(self, prompt: str):
                del prompt
                yield "runtime-backed answer"

        original_get_stored_settings = getattr(
            chat_execution_module,
            "get_stored_settings",
            None,
        )
        original_get_llm_provider = chat_execution_module.get_llm_provider
        original_get_configured_tool_registry_provider = (
            chat_execution_module.get_configured_tool_registry_provider
        )
        original_build_tool_plan_artifacts = chat_execution_module.build_tool_plan_artifacts
        original_execute_preflight = (
            chat_execution_module.execute_configured_tool_registry_provider_preflight
        )
        original_execute_tool_plan_item_service_execution = (
            chat_execution_module.execute_tool_plan_item_service_execution
        )
        original_execute_tool_plan_item_service_actions = (
            chat_execution_module.execute_tool_plan_item_service_actions
        )
        original_update_task_status = chat_execution_module.update_task_status
        original_get_task = chat_execution_module.get_task
        original_update_task_trace_steps = chat_execution_module.update_task_trace_steps
        original_complete_task = chat_execution_module.complete_task
        original_create_message = chat_execution_module.create_message
        original_try_append_task_memory = chat_execution_module.try_append_task_memory
        original_safe_record_audit_event = chat_execution_module.safe_record_audit_event

        def fake_get_stored_settings(user_id: str) -> StoredSettings:
            self.assertEqual(user_id, "user-1")
            return runtime_settings

        def fake_get_llm_provider(user_id: str) -> ProviderWithoutIdentity:
            self.assertEqual(user_id, "user-1")
            return ProviderWithoutIdentity()

        def fake_build_tool_plan_artifacts(
            prompt: str,
            *,
            provider: object | None = None,
            registry_provider: object | None = None,
        ) -> SimpleNamespace:
            del prompt, provider, registry_provider
            return SimpleNamespace(
                tool_plan=[{"name": "calc_eval", "input": {"expression": "1+2"}}],
                planning_prompt=None,
                provider_usage=None,
                planning_provider_attempted=False,
                planning_provider_used=False,
                allowed_tool_names=("calc_eval",),
                allowed_tool_labels=("Calculator",),
            )

        def fake_execute_preflight(
            *,
            task_id: str,
            step_id: str,
            seq: int,
            model: str,
            trace_steps: list[dict[str, object]],
            persist_trace_fn,
            record_audit_event_fn,
            settings=None,
        ) -> dict[str, object]:
            del task_id, step_id, seq, trace_steps, persist_trace_fn, record_audit_event_fn, settings
            preflight_models_seen.append(model)
            return {
                "provider": StaticToolRegistryProvider(
                    {"calc_eval": get_default_tool_registry()["calc_eval"]}
                ),
                "provider_source_name": "default",
            }

        def fake_execute_tool_plan_item_service_execution(**kwargs):
            iteration_models_seen.append(str(kwargs["model"]))
            yield {
                "kind": "result",
                "result": {
                    "service_actions": [],
                },
            }

        def fake_execute_tool_plan_item_service_actions(**kwargs):
            yield {
                "kind": "result",
                "result": {
                    "seq_cursor": int(kwargs["seq_cursor"]),
                    "should_return": False,
                },
            }

        try:
            chat_execution_module.get_stored_settings = fake_get_stored_settings
            chat_execution_module.get_llm_provider = fake_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                lambda *, settings=None: StaticToolRegistryProvider(
                    {"calc_eval": get_default_tool_registry()["calc_eval"]}
                )
            )
            chat_execution_module.build_tool_plan_artifacts = (
                fake_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                fake_execute_preflight
            )
            chat_execution_module.execute_tool_plan_item_service_execution = (
                fake_execute_tool_plan_item_service_execution
            )
            chat_execution_module.execute_tool_plan_item_service_actions = (
                fake_execute_tool_plan_item_service_actions
            )
            chat_execution_module.update_task_status = lambda *args, **kwargs: None
            chat_execution_module.get_task = lambda *args, **kwargs: {"status": "running"}
            chat_execution_module.update_task_trace_steps = lambda *args, **kwargs: None
            chat_execution_module.complete_task = (
                lambda *, trace_steps, **kwargs: completed_trace_steps.extend(trace_steps)
            )
            chat_execution_module.create_message = lambda *args, **kwargs: None
            chat_execution_module.try_append_task_memory = lambda *args, **kwargs: None
            chat_execution_module.safe_record_audit_event = lambda *args, **kwargs: None

            events = list(
                chat_execution_module.stream_task_execution(
                    task_id="task-1",
                    session_id="session-1",
                    user_id="user-1",
                    prompt="please calculate with runtime identity fallback",
                )
            )
        finally:
            if original_get_stored_settings is not None:
                chat_execution_module.get_stored_settings = original_get_stored_settings
            chat_execution_module.get_llm_provider = original_get_llm_provider
            chat_execution_module.get_configured_tool_registry_provider = (
                original_get_configured_tool_registry_provider
            )
            chat_execution_module.build_tool_plan_artifacts = (
                original_build_tool_plan_artifacts
            )
            chat_execution_module.execute_configured_tool_registry_provider_preflight = (
                original_execute_preflight
            )
            chat_execution_module.execute_tool_plan_item_service_execution = (
                original_execute_tool_plan_item_service_execution
            )
            chat_execution_module.execute_tool_plan_item_service_actions = (
                original_execute_tool_plan_item_service_actions
            )
            chat_execution_module.update_task_status = original_update_task_status
            chat_execution_module.get_task = original_get_task
            chat_execution_module.update_task_trace_steps = original_update_task_trace_steps
            chat_execution_module.complete_task = original_complete_task
            chat_execution_module.create_message = original_create_message
            chat_execution_module.try_append_task_memory = original_try_append_task_memory
            chat_execution_module.safe_record_audit_event = original_safe_record_audit_event

        start_payload = next(
            json.loads(event.split("data: ", 1)[1])
            for event in events
            if event.startswith("event: start\n")
        )
        planning_trace_payload = next(
            json.loads(event.split("data: ", 1)[1])
            for event in events
            if event.startswith("event: trace\n")
        )

        self.assertEqual(start_payload["provider"], "openai")
        self.assertEqual(start_payload["model"], "gpt-4.1-mini")
        self.assertEqual(planning_trace_payload["step"]["meta"]["model"], "gpt-4.1-mini")
        self.assertEqual(preflight_models_seen, ["gpt-4.1-mini"])
        self.assertEqual(iteration_models_seen, ["gpt-4.1-mini"])
        final_answer_step = completed_trace_steps[-1]
        self.assertEqual(final_answer_step["meta"]["model"], "gpt-4.1-mini")
        self.assertEqual(final_answer_step["content"], "runtime-backed answer")

    def test_build_tool_plan_summary_uses_display_labels(self) -> None:
        plan = build_tool_plan("请帮我检索知识库并计算 [calc:1+2*3] [kb:demo]")

        self.assertEqual(
            build_tool_plan_summary(plan),
            "Planned tools: Knowledge Retrieval, Calculator",
        )
