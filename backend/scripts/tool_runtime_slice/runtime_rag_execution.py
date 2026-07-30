from __future__ import annotations

from .context import *


class RuntimeRagExecutionMixin:
    def test_build_tool_rag_followup_keeps_current_shape(self) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="mock_retrieve",
            output={
                "chunks": ["a", "b"],
                "knowledge_base_id": "demo",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"],
            {
                "id": "rag-1",
                "seq": 4,
                "type": "thought",
                "content": "Knowledge Retrieval returned snippets from the selected knowledge base.",
                "meta": {
                    "model": "mock-gpt",
                    "step_type": "rag_retrieval",
                    "tokens": 2,
                    "cost_estimate": None,
                    "rag": {
                        "chunks": ["a", "b"],
                        "knowledge_base_id": "demo",
                    },
                },
            },
        )
        self.assertEqual(
            followup["trace"],
            {
                "task_id": "task-1",
                "step_id": "rag-1",
                "step": followup["step"],
            },
        )

    def test_build_tool_rag_followup_supports_extra_retrieval_kind_and_label(self) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="task_retrieve_hot",
            tool_kind="hot_knowledge_retrieval",
            display_name="Hot Retrieval",
            output={
                "chunks": ["a", "b"],
                "knowledge_base_id": "demo",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["content"],
            "Hot Retrieval returned snippets from the selected knowledge base.",
        )
        self.assertEqual(
            followup["step"]["meta"]["rag"]["knowledge_base_id"],
            "demo",
        )

    def test_build_tool_rag_followup_supports_runtime_semantic_override_retrieval_family(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "chunks": ["a", "b"],
                "knowledge_base_id": "demo",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            followup["step"]["meta"]["rag"]["knowledge_base_id"],
            "demo",
        )

    def test_build_tool_rag_followup_accepts_tuple_chunks_for_runtime_override_real_tool(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "chunks": ("a", "b"),
                "knowledge_base_id": "demo",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            followup["step"]["meta"]["rag"],
            {
                "chunks": ["a", "b"],
                "knowledge_base_id": "demo",
            },
        )

    def test_build_tool_rag_followup_extracts_chunks_from_documents_for_runtime_override_real_tool(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "documents": [
                    {"snippet": "alpha snippet"},
                    {"content": "beta content"},
                    {"text": "gamma text"},
                    {"excerpt": "delta excerpt"},
                    {"summary": "epsilon summary"},
                    {"description": "zeta description"},
                    "delta string",
                    {"title": "ignored title only"},
                ],
                "knowledge_base_id": "demo",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            followup["step"]["meta"]["rag"],
            {
                "chunks": [
                    "alpha snippet",
                    "beta content",
                    "gamma text",
                    "delta excerpt",
                    "epsilon summary",
                    "zeta description",
                    "delta string",
                ],
                "knowledge_base_id": "demo",
            },
        )

    def test_build_tool_rag_followup_extracts_chunks_from_http_json_list_aliases_for_real_tool(
        self,
    ) -> None:
        for alias_name in ("items", "results", "matches"):
            with self.subTest(alias_name=alias_name):
                followup = build_tool_rag_followup(
                    task_id="task-1",
                    step_id="rag-1",
                    seq=4,
                    model="mock-gpt",
                    tool_name="provider_search",
                    tool_kind="provider_search",
                    tool_semantic_family="knowledge_retrieval",
                    display_name="Provider Search",
                    output={
                        alias_name: [
                            {"snippet": "alpha snippet"},
                            {"content": "beta content"},
                            {"excerpt": "gamma excerpt"},
                            {"summary": "delta summary"},
                            "gamma string",
                            {"title": "ignored title only"},
                        ],
                        "knowledge_base_id": "provider-kb",
                    },
                    token_count=2,
                )

                self.assertIsNotNone(followup)
                assert followup is not None
                self.assertEqual(
                    followup["step"]["content"],
                    "Provider Search returned snippets.",
                )
                self.assertEqual(
                    followup["step"]["meta"]["rag"],
                    {
                        "chunks": [
                            "alpha snippet",
                            "beta content",
                            "gamma excerpt",
                            "delta summary",
                            "gamma string",
                        ],
                        "knowledge_base_id": "provider-kb",
                    },
                )

    def test_build_tool_rag_followup_extracts_chunks_from_http_json_scalar_value_list_for_real_tool(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "value": [
                    {"snippetText": "alpha response-path snippet"},
                    {"source": {"contentText": "beta response-path content"}},
                    "gamma response-path string",
                ],
                "knowledge_base_id": "provider-kb",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            followup["step"]["meta"]["rag"],
            {
                "chunks": [
                    "alpha response-path snippet",
                    "beta response-path content",
                    "gamma response-path string",
                ],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_build_tool_rag_followup_extracts_chunks_from_http_json_summary_fields_for_real_tool(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "items": [
                    {"excerpt": "alpha excerpt"},
                    {"summary": "beta summary"},
                    {"description": "gamma description"},
                ],
                "knowledge_base_id": "provider-kb",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["meta"]["rag"],
            {
                "chunks": [
                    "alpha excerpt",
                    "beta summary",
                    "gamma description",
                ],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_build_tool_rag_followup_extracts_chunks_from_nested_http_json_match_fields_for_real_tool(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "matches": [
                    {"metadata": {"text": "alpha metadata text"}},
                    {"metadata": {"summary": "beta metadata summary"}},
                    {"document": {"content": "gamma document content"}},
                    {"metadata": {"title": "ignored title only"}},
                ],
                "knowledge_base_id": "provider-kb",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["meta"]["rag"],
            {
                "chunks": [
                    "alpha metadata text",
                    "beta metadata summary",
                    "gamma document content",
                ],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_build_tool_rag_followup_extracts_chunks_from_http_json_attribute_containers_for_real_tool(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "matches": [
                    {"attributes": {"snippetText": "alpha attribute snippet"}},
                    {"source": {"contentText": "beta source content"}},
                    {"fields": {"textContent": "gamma fields text"}},
                ],
                "knowledge_base_id": "provider-kb",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["meta"]["rag"],
            {
                "chunks": [
                    "alpha attribute snippet",
                    "beta source content",
                    "gamma fields text",
                ],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_build_tool_rag_followup_redacts_http_json_chunk_field_paths(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "chunks": [
                    "alpha query_params.access_token",
                    "beta Bearer secret-token",
                ],
                "knowledge_base_id": "provider-kb",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        rag_json = json.dumps(followup, ensure_ascii=False)
        self.assertEqual(
            followup["step"]["meta"]["rag"]["chunks"],
            [
                "alpha [redacted]",
                "beta [redacted]",
            ],
        )
        self.assertNotIn("query_params.access_token", rag_json)
        self.assertNotIn("Bearer", rag_json)
        self.assertNotIn("secret-token", rag_json)

    def test_build_tool_plan_item_execution_redacts_http_json_rag_followup_chunks_from_raw_adapter_output(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
            execution_kind="http_json",
        )
        registry = {"provider_search": registration}
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
            registry=registry,
        )
        runtime_ctx = build_tool_runtime_context(
            name="provider_search",
            prompt="search demo",
            user_id="user-1",
            attempt=0,
            registry=registry,
        )

        execution = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="provider_search",
            tool_input={"query": "demo"},
            output={
                "documents_total": 2,
                "chunks": [
                    "alpha token=hidden",
                    "beta secret=hidden",
                ],
                "access_token": "hidden",
                "request_id": "Bearer secret-token",
            },
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-1",
            rag_token_count=2,
            registry=registry,
        )

        rag_followup = execution["success_effects"]["rag_followup"]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        rag_json = json.dumps(rag_followup, ensure_ascii=False)
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"]["chunks"],
            [
                "alpha token=[redacted]",
                "beta secret=[redacted]",
            ],
        )
        self.assertNotIn("token=hidden", rag_json)
        self.assertNotIn("secret=hidden", rag_json)
        self.assertNotIn("access_token", rag_json)
        self.assertNotIn("secret-token", rag_json)

    def test_build_tool_rag_followup_extracts_chunks_from_deep_nested_http_json_match_fields_for_real_tool(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "matches": [
                    {"metadata": {"chunk": {"text": "alpha nested chunk text"}}},
                    {"payload": {"document": {"content": "beta payload document"}}},
                    {"node": {"metadata": {"summary": "gamma node summary"}}},
                ],
                "knowledge_base_id": "provider-kb",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["meta"]["rag"],
            {
                "chunks": [
                    "alpha nested chunk text",
                    "beta payload document",
                    "gamma node summary",
                ],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_build_tool_rag_followup_falls_back_to_http_json_alias_when_documents_have_no_snippets_for_real_tool(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "documents": [
                    {"id": "doc-1", "title": "Metadata only"},
                ],
                "matches": [
                    {"metadata": {"text": "fallback match text"}},
                ],
                "knowledge_base_id": "provider-kb",
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["meta"]["rag"],
            {
                "chunks": ["fallback match text"],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_build_tool_rag_followup_supports_registry_provider_without_explicit_semantic_inputs(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Provider Search",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "chunks": ["a", "b"],
                            "knowledge_base_id": "demo",
                        },
                        result_preview_keys=("documents_total",),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )

        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            display_name="Provider Search",
            output={
                "chunks": ["a", "b"],
                "knowledge_base_id": "demo",
            },
            token_count=2,
            registry_provider=provider,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            followup["step"]["meta"]["rag"]["knowledge_base_id"],
            "demo",
        )

    def test_build_tool_rag_followup_does_not_fallback_to_default_kb_for_runtime_override_real_tool_without_knowledge_base_id(
        self,
    ) -> None:
        followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=4,
            model="mock-gpt",
            tool_name="provider_search",
            tool_kind="provider_search",
            tool_semantic_family="knowledge_retrieval",
            display_name="Provider Search",
            output={
                "chunks": ["a", "b"],
            },
            token_count=2,
        )

        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual(
            followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            followup["step"]["meta"]["rag"],
            {
                "chunks": ["a", "b"],
            },
        )

    def test_build_tool_iteration_execution_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        execution = build_tool_iteration_execution(
            task_id="task-1",
            step_id="step-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(
            execution["start_events"],
            {
                "tool_start": {
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
                "state": {
                    "task_id": "task-1",
                    "phase": "tool_running",
                },
            },
        )
        self.assertEqual(execution["outcome"]["outcome"], "success")
        self.assertEqual(execution["outcome"]["events"]["tool_end"]["status"], "done")
        self.assertEqual(
            execution["success_artifacts"]["trace"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": execution["outcome"]["action_step"],
            },
        )
        self.assertIsNone(execution["terminal_failure"])

    def test_build_tool_iteration_execution_uses_productized_label_and_preview_for_builtin_calculator_observation(
        self,
    ) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        execution = build_tool_iteration_execution(
            task_id="task-1",
            step_id="step-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(
            execution["success_artifacts"]["observation"],
            'Calculator: {"expression": "1+2*3", "result": 7.0}',
        )
        self.assertEqual(
            execution["start_events"]["tool_start"]["display_name"],
            "Calculator",
        )

    def test_build_tool_iteration_execution_keeps_terminal_error_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        execution = build_tool_iteration_execution(
            task_id="task-1",
            step_id="step-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
        )

        self.assertEqual(execution["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(execution["outcome"]["outcome"], "error")
        self.assertFalse(execution["outcome"]["retryable"])
        self.assertIsNone(execution["success_artifacts"])
        self.assertIsNotNone(execution["terminal_failure"])
        assert execution["terminal_failure"] is not None
        self.assertEqual(execution["terminal_failure"]["status"], "failed")
        self.assertEqual(execution["terminal_failure"]["state"]["phase"], "error")

    def test_build_tool_iteration_execution_uses_current_action_step_on_retry(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        current_step = build_tool_step_error_update(
            action_step=iteration_ctx["action_step"],
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            retry_count=1,
            token_count=9,
            error_message="transient",
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        execution = build_tool_iteration_execution(
            task_id="task-1",
            step_id="step-1",
            iteration_ctx=iteration_ctx,
            action_step=current_step,
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error="transient",
        )

        self.assertEqual(execution["start_events"]["tool_start"]["retry_count"], 1)
        self.assertEqual(execution["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(
            execution["outcome"]["action_step"]["meta"]["tool"]["error"],
            "transient",
        )
        self.assertEqual(
            execution["outcome"]["action_step"]["meta"]["tool"]["retry_count"],
            1,
        )

    def test_build_tool_plan_item_success_bundle_keeps_current_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )

        bundle = build_tool_plan_item_success_bundle(
            success_artifacts=success_artifacts,
            rag_followup=None,
        )

        self.assertEqual(bundle["trace"], success_artifacts["trace"])
        self.assertEqual(bundle["observation"], success_artifacts["observation"])
        self.assertEqual(bundle["output"], success_artifacts["output"])
        self.assertIsNone(bundle["rag_followup"])

    def test_build_tool_plan_item_result_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )

        result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=None,
            ),
            terminal_failure=None,
        )

        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(result["last_error"])
        self.assertIsNotNone(result["success_bundle"])
        self.assertIsNone(result["terminal_failure"])

    def test_build_tool_plan_item_result_keeps_terminal_failure_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_failure = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            error_message="transient",
            retry_count=2,
        )

        result = build_tool_plan_item_result(
            outcome="terminal_failure",
            action_step=action_step,
            last_error="transient",
            success_bundle=None,
            terminal_failure=terminal_failure,
        )

        self.assertEqual(result["outcome"], "terminal_failure")
        self.assertEqual(result["last_error"], "transient")
        self.assertIsNone(result["success_bundle"])
        self.assertEqual(result["terminal_failure"]["status"], "failed")

    def test_build_tool_plan_item_result_redacts_terminal_failure_payload(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": (
                "provider_search: unsupported tool execution kind api_key=hidden"
            ),
        }
        terminal_failure = {
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    **action_step,
                    "content": (
                        "provider_search: http_json execution headers.x-api-key must be safe"
                    ),
                },
            },
            "audit_detail": {
                "step_id": "step-1",
                "retry_count": 2,
                "message": "json_body.client_secret is invalid",
            },
            "state": {
                "task_id": "task-1",
                "phase": "error",
                "message": "api_key=hidden",
            },
            "status": "failed",
            "error_message": "provider_search failed with token=hidden",
        }

        result = build_tool_plan_item_result(
            outcome="terminal_failure",
            action_step=action_step,
            last_error="provider_search failed with token=hidden",
            success_bundle=None,
            terminal_failure=terminal_failure,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_result_redacts_http_json_success_bundle_trace_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-plan-item-result-http-json-output"
        )
        rag_followup_step = self._make_sensitive_http_json_action_step(
            step_id="rag-plan-item-result-http-json-output",
            content="Retrieved snippets",
        )

        result = build_tool_plan_item_result(
            outcome="success",
            action_step=raw_step,
            last_error=None,
            success_bundle={
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-plan-item-result-http-json-output",
                    "step": raw_step,
                },
                "observation": "Provider Status: ok",
                "output": {"status": "ready"},
                "rag_followup": {
                    "step": rag_followup_step,
                    "trace": {
                        "task_id": "task-1",
                        "step_id": "rag-plan-item-result-http-json-output",
                        "step": rag_followup_step,
                    },
                },
            },
            terminal_failure=None,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_plan_item_execution_result_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )
        iteration_execution = {
            "outcome": {
                "action_step": action_step,
                "error_message": None,
            },
            "success_artifacts": success_artifacts,
            "terminal_failure": None,
        }

        result = build_tool_plan_item_execution_result(
            iteration_execution=iteration_execution,
            rag_followup=None,
        )

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["success_bundle"]["trace"], success_artifacts["trace"])
        self.assertIsNone(result["terminal_failure"])

    def test_build_tool_plan_item_execution_result_keeps_terminal_failure_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_failure = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            error_message="transient",
            retry_count=2,
        )
        iteration_execution = {
            "outcome": {
                "action_step": action_step,
                "error_message": "transient",
            },
            "success_artifacts": None,
            "terminal_failure": terminal_failure,
        }

        result = build_tool_plan_item_execution_result(
            iteration_execution=iteration_execution,
            rag_followup=None,
        )

        self.assertEqual(result["outcome"], "terminal_failure")
        self.assertEqual(result["last_error"], "transient")
        self.assertIsNone(result["success_bundle"])
        self.assertEqual(result["terminal_failure"]["status"], "failed")

    def test_build_tool_plan_item_execution_result_redacts_terminal_failure_payload(
        self,
    ) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": (
                "provider_search: unsupported tool execution kind api_key=hidden"
            ),
        }
        terminal_failure = {
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    **action_step,
                    "content": (
                        "provider_search: http_json execution query_params.access_token must be safe"
                    ),
                },
            },
            "audit_detail": {
                "step_id": "step-1",
                "retry_count": 2,
                "message": "headers.x-api-key is invalid",
            },
            "state": {
                "task_id": "task-1",
                "phase": "error",
                "message": "api_key=hidden",
            },
            "status": "failed",
            "error_message": "provider_search failed with token=hidden",
        }
        iteration_execution = {
            "outcome": {
                "action_step": action_step,
                "error_message": "provider_search failed with token=hidden",
            },
            "success_artifacts": None,
            "terminal_failure": terminal_failure,
        }

        result = build_tool_plan_item_execution_result(
            iteration_execution=iteration_execution,
            rag_followup=None,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_execution_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["plan_item_result"]["outcome"], "success")
        self.assertEqual(result["start_events"]["state"]["phase"], "tool_running")
        self.assertEqual(
            result["plan_item_result"]["success_bundle"]["trace"]["step"]["content"],
            "Tool done: Calculator",
        )
        self.assertEqual(result["tool_end_event"]["status"], "done")
        self.assertFalse(bool(result["retryable"]))
        self.assertIsNone(result["error_event"])
        self.assertIsNotNone(result["postprocess"])
        self.assertIsNotNone(result["success_effects"])
        self.assertIsNone(result["terminal_effects"])
        self.assertEqual(
            result["success_effects"]["trace"]["step"]["content"],
            "Tool done: Calculator",
        )
        self.assertEqual(
            result["next_action_step"]["content"],
            "Tool done: Calculator",
        )
        self.assertIsNone(result["terminal_failure"])

    def test_build_tool_plan_item_execution_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["plan_item_result"]["outcome"], "terminal_failure")
        self.assertEqual(result["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(result["last_error"], "transient")
        self.assertEqual(result["tool_end_event"]["status"], "error")
        self.assertFalse(bool(result["retryable"]))
        self.assertEqual(result["error_event"]["code"], "tool_execution_error")
        self.assertIsNone(result["postprocess"])
        self.assertIsNone(result["success_effects"])
        self.assertIsNotNone(result["terminal_effects"])
        self.assertEqual(result["terminal_effects"]["state"]["phase"], "error")
        self.assertIsNotNone(result["terminal_failure"])
        assert result["terminal_failure"] is not None
        self.assertEqual(result["terminal_failure"]["status"], "failed")

    def test_build_tool_plan_item_execution_builds_rag_followup_for_retrieve(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="mock_retrieve",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="mock_retrieve",
            prompt="检索 demo",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "chunks": ["alpha", "beta"],
            "knowledge_base_id": "demo-kb",
            "hit_count": 2,
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="mock_retrieve",
            tool_input={"query": "demo"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-1",
            rag_token_count=2,
        )

        rag_followup = result["plan_item_result"]["success_bundle"]["rag_followup"]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(rag_followup["step"]["id"], "rag-1")
        self.assertEqual(
            rag_followup["step"]["content"],
            "Knowledge Retrieval returned snippets from the selected knowledge base.",
        )
        self.assertEqual(rag_followup["step"]["meta"]["tokens"], 2)
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"]["knowledge_base_id"],
            "demo-kb",
        )

    def test_build_tool_plan_item_execution_uses_extra_retrieve_display_and_rag_followup(
        self,
    ) -> None:
        provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "task_retrieve_hot": {
                            "template": "task_retrieve",
                            "label": "Hot Retrieval",
                            "kind": "hot_knowledge_retrieval",
                        }
                    }
                ),
            )
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_retrieve_hot",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            display_name="Hot Retrieval",
        )
        runtime_ctx = build_tool_runtime_context(
            name="task_retrieve_hot",
            prompt="检索 demo",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        output = {
            "chunks": ["alpha", "beta"],
            "knowledge_base_id": "demo-kb",
            "hit_count": 2,
            "tool_kind": "hot_knowledge_retrieval",
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="task_retrieve_hot",
            tool_input={"query": "demo"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-1",
            rag_token_count=2,
        )

        success_bundle = result["plan_item_result"]["success_bundle"]
        self.assertIsNotNone(success_bundle)
        assert success_bundle is not None
        self.assertEqual(
            result["iteration_execution"]["start_events"]["tool_start"]["display_name"],
            "Hot Retrieval",
        )
        self.assertEqual(
            success_bundle["trace"]["step"]["content"],
            "Tool done: Hot Retrieval",
        )
        self.assertEqual(
            success_bundle["observation"],
            "Hot Retrieval: Retrieved 2 hits from knowledge base demo-kb.",
        )
        self.assertIsNotNone(success_bundle["rag_followup"])
        assert success_bundle["rag_followup"] is not None
        self.assertEqual(
            success_bundle["rag_followup"]["step"]["content"],
            "Hot Retrieval returned snippets from the selected knowledge base.",
        )

    def test_build_tool_plan_item_execution_infers_preview_and_rag_followup_for_extra_provider_retrieval_kind(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Provider Search",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "query": str(tool_input.get("query", "")),
                            "hit_count": 2,
                            "knowledge_base_id": "demo-kb",
                            "chunks": ["alpha", "beta"],
                        },
                    )
                }
            )
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            display_name="Provider Search",
        )
        runtime_ctx = build_tool_runtime_context(
            name="provider_search",
            prompt="检索 demo",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        output = {
            "chunks": ["alpha", "beta"],
            "knowledge_base_id": "demo-kb",
            "hit_count": 2,
            "tool_kind": "provider_retrieval",
            "raw_documents": [{"id": "doc-1"}],
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="provider_search",
            tool_input={"query": "demo"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-1",
            rag_token_count=2,
        )

        success_bundle = result["plan_item_result"]["success_bundle"]
        self.assertIsNotNone(success_bundle)
        assert success_bundle is not None
        self.assertEqual(
            success_bundle["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )
        self.assertEqual(
            success_bundle["trace"]["step"]["meta"]["tool"]["kind"],
            "provider_retrieval",
        )
        self.assertEqual(
            success_bundle["trace"]["step"]["meta"]["tool"]["semantic_kind"],
            "provider_search",
        )
        self.assertEqual(
            success_bundle["trace"]["step"]["meta"]["tool"]["semantic_family"],
            "knowledge_retrieval",
        )
        self.assertTrue(
            success_bundle["trace"]["step"]["meta"]["tool"]["supports_result_preview"]
        )
        self.assertEqual(
            success_bundle["trace"]["step"]["meta"]["tool"]["effective_result_preview_keys"],
            ["hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            success_bundle["trace"]["step"]["meta"]["tool"]["effective_result_output_keys"],
            ["hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            success_bundle["observation"],
            "Provider Search: Retrieved 2 hits.",
        )
        self.assertIsNotNone(success_bundle["rag_followup"])
        assert success_bundle["rag_followup"] is not None
        self.assertEqual(
            success_bundle["rag_followup"]["step"]["content"],
            "Provider Search returned snippets.",
        )

    def test_build_tool_plan_item_execution_rewrites_manual_real_search_output_to_runtime_semantic_kind(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Provider Search",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        result_preview_keys=("tool_kind", "documents_total"),
                        runtime_semantic_kind="provider_search",
                        runner=lambda *, tool_input, prompt, user_id: {
                            "query": str(tool_input.get("query", "")),
                            "documents_total": 2,
                            "documents": [{"id": "doc-1"}],
                            "knowledge_base_id": "demo-kb",
                            "chunks": ["alpha", "beta"],
                        },
                    )
                }
            )
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            display_name="Provider Search",
        )
        runtime_ctx = build_tool_runtime_context(
            name="provider_search",
            prompt="检索 demo",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        output = {
            "documents_total": 2,
            "documents": [{"id": "doc-1"}],
            "knowledge_base_id": "demo-kb",
            "chunks": ["alpha", "beta"],
            "tool_kind": "provider_retrieval",
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="provider_search",
            tool_input={"query": "demo"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=2,
        )

        success_bundle = result["plan_item_result"]["success_bundle"]
        self.assertIsNotNone(success_bundle)
        assert success_bundle is not None
        self.assertEqual(
            success_bundle["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "tool_kind": "provider_search",
                "documents_total": 2,
            },
        )
        self.assertEqual(
            success_bundle["trace"]["step"]["meta"]["tool"]["output"]["tool_kind"],
            "provider_search",
        )
        self.assertEqual(
            success_bundle["output"]["tool_kind"],
            "provider_search",
        )
        self.assertIsNotNone(success_bundle["rag_followup"])
        assert success_bundle["rag_followup"] is not None
        self.assertEqual(
            success_bundle["rag_followup"]["step"]["content"],
            "Provider Search returned snippets.",
        )

    def test_build_tool_plan_item_execution_preserves_output_policy_fields_in_observation_for_runtime_override_real_tool(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Provider Search",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        result_preview_keys=("documents_total",),
                        result_output_keys=("documents_total", "request_id"),
                        runtime_semantic_kind="provider_search",
                        runner=lambda *, tool_input, prompt, user_id: {
                            "query": str(tool_input.get("query", "")),
                            "documents_total": 2,
                            "request_id": "req-1",
                            "documents": [{"id": "doc-1"}],
                        },
                    )
                }
            )
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            display_name="Provider Search",
        )
        runtime_ctx = build_tool_runtime_context(
            name="provider_search",
            prompt="检索 demo",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        output = {
            "documents_total": 2,
            "request_id": "req-1",
            "documents": [{"id": "doc-1"}],
            "tool_kind": "provider_retrieval",
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="provider_search",
            tool_input={"query": "demo"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=2,
        )

        success_bundle = result["plan_item_result"]["success_bundle"]
        self.assertIsNotNone(success_bundle)
        assert success_bundle is not None
        self.assertEqual(
            success_bundle["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            success_bundle["trace"]["step"]["meta"]["tool"]["output"],
            {
                "documents_total": 2,
                "request_id": "req-1",
            },
        )
        self.assertEqual(
            success_bundle["observation"],
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )
        self.assertIsNone(success_bundle["rag_followup"])

    def test_build_tool_plan_item_execution_keeps_canonical_override_retrieval_rag_followup_semantics(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "task_retrieve": ToolRegistration(
                        name="task_retrieve",
                        kind="provider_retrieval",
                        label="Provider Retrieval",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "query": str(tool_input.get("query", "")),
                            "hit_count": 1,
                            "knowledge_base_id": "demo-kb",
                            "chunks": ["alpha"],
                        },
                    )
                }
            )
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_retrieve",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            display_name="Provider Retrieval",
        )
        runtime_ctx = build_tool_runtime_context(
            name="task_retrieve",
            prompt="检索 demo",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        output = {
            "chunks": ["alpha"],
            "knowledge_base_id": "demo-kb",
            "hit_count": 1,
            "tool_kind": "provider_retrieval",
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="task_retrieve",
            tool_input={"query": "demo"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-1",
            rag_token_count=2,
        )

        success_bundle = result["plan_item_result"]["success_bundle"]
        self.assertIsNotNone(success_bundle)
        assert success_bundle is not None
        self.assertIsNotNone(success_bundle["rag_followup"])
        assert success_bundle["rag_followup"] is not None
        self.assertEqual(
            success_bundle["rag_followup"]["step"]["content"],
            "Provider Retrieval returned snippets from the selected knowledge base.",
        )

    def test_build_tool_plan_item_execution_exposes_iteration_execution_bundle(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        result = build_tool_plan_item_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            runtime_ctx=runtime_ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(
            result["iteration_execution"]["outcome"]["events"]["tool_end"]["status"],
            "done",
        )
        self.assertEqual(
            result["iteration_execution"]["start_events"]["state"]["phase"],
            "tool_running",
        )

    def test_build_tool_plan_item_postprocess_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )
        plan_item_result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=None,
            ),
            terminal_failure=None,
        )

        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )

        self.assertEqual(postprocess["trace"], success_artifacts["trace"])
        self.assertEqual(
            postprocess["observation"],
            'Calculator: {"expression": "1+2*3", "result": 7.0}',
        )
        self.assertEqual(postprocess["output"], success_artifacts["output"])
        self.assertIsNone(postprocess["rag_followup"])

    def test_build_tool_plan_item_success_effects_keep_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )
        plan_item_result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=None,
            ),
            terminal_failure=None,
        )
        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )

        effects = build_tool_plan_item_success_effects(
            action_step=action_step,
            postprocess=postprocess,
        )

        self.assertEqual(effects["trace_step"]["id"], "step-1")
        self.assertEqual(effects["trace"]["step"]["content"], "Tool done: calc_eval")
        self.assertEqual(
            effects["observation"],
            'Calculator: {"expression": "1+2*3", "result": 7.0}',
        )
        self.assertIsNone(effects["rag_followup"])

    def test_build_tool_plan_item_postprocess_keeps_rag_followup_shape(self) -> None:
        rag_followup = {
            "step": {
                "id": "rag-1",
                "seq": 4,
            },
            "trace": {
                "task_id": "task-1",
                "step_id": "rag-1",
                "step": {
                    "id": "rag-1",
                    "seq": 4,
                },
            },
        }
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: mock_retrieve",
            "meta": {
                "tool": {
                    "name": "mock_retrieve",
                    "status": "done",
                    "output": {
                        "chunks": ["alpha"],
                        "knowledge_base_id": "demo-kb",
                    },
                }
            },
        }
        success_artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="mock_retrieve",
        )
        plan_item_result = build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=None,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=rag_followup,
            ),
            terminal_failure=None,
        )

        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )

        self.assertEqual(postprocess["rag_followup"], rag_followup)

    def test_build_tool_plan_item_terminal_effects_keep_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_failure = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            error_message="transient",
            retry_count=2,
        )

        effects = build_tool_plan_item_terminal_effects(
            action_step=action_step,
            terminal_failure=terminal_failure,
        )

        self.assertEqual(effects["trace_step"]["id"], "step-1")
        self.assertEqual(effects["trace"]["step"]["content"], "Tool error: calc_eval")
        self.assertEqual(effects["status"], "failed")
        self.assertEqual(effects["error_message"], "transient")
        self.assertEqual(effects["state"]["phase"], "error")

    def test_build_tool_plan_item_stream_effects_keeps_success_shape(self) -> None:
        loop_execution_result = {
            "trace_event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
            },
            "success_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": "Tool done: mock_retrieve",
                    },
                },
                "observation": 'mock_retrieve: {"chunks": ["alpha"]}',
                "rag_followup": {
                    "step": {
                        "id": "rag-1",
                        "seq": 4,
                        "content": "Retrieved snippets",
                    },
                    "trace": {
                        "task_id": "task-1",
                        "step_id": "rag-1",
                        "step": {
                            "id": "rag-1",
                            "seq": 4,
                            "content": "Retrieved snippets",
                        },
                    },
                },
            },
            "terminal_effects": None,
            "should_return": False,
        }

        result = build_tool_plan_item_stream_effects(
            loop_execution_result=loop_execution_result,
        )

        self.assertFalse(bool(result["should_return"]))
        self.assertEqual(result["seq_increment"], 1)
        self.assertEqual(
            result["tool_observations"],
            ['mock_retrieve: {"chunks": ["alpha"]}'],
        )
        self.assertEqual(result["observation"], 'mock_retrieve: {"chunks": ["alpha"]}')
        self.assertIsNone(result["terminal_effects"])
        self.assertEqual([step["id"] for step in result["trace_steps"]], ["step-1", "rag-1"])
        self.assertEqual([event["step_id"] for event in result["trace_events"]], ["step-1", "rag-1"])

    def test_build_tool_plan_item_stream_effects_keeps_terminal_shape(self) -> None:
        terminal_effects = {
            "trace_step": {
                "id": "step-1",
                "seq": 3,
                "content": "Tool error: calc_eval",
            },
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool error: calc_eval",
                },
            },
            "status": "failed",
            "error_message": "fatal",
            "audit_detail": {"step_id": "step-1", "retry_count": 1},
            "state": {"task_id": "task-1", "phase": "error"},
        }
        loop_execution_result = {
            "trace_event": terminal_effects["trace"],
            "success_effects": None,
            "terminal_effects": terminal_effects,
            "should_return": True,
        }

        result = build_tool_plan_item_stream_effects(
            loop_execution_result=loop_execution_result,
        )

        self.assertTrue(bool(result["should_return"]))
        self.assertEqual(result["seq_increment"], 0)
        self.assertEqual(result["tool_observations"], [])
        self.assertIsNone(result["observation"])
        self.assertEqual(result["terminal_effects"], terminal_effects)
        self.assertEqual([step["id"] for step in result["trace_steps"]], ["step-1"])
        self.assertEqual([event["step_id"] for event in result["trace_events"]], ["step-1"])

    def test_build_tool_plan_item_stream_effects_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = {
            "id": "step-http-json-stream-output",
            "seq": 3,
            "type": "action",
            "content": "Tool done: Provider Status",
            "meta": {
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "status": "done",
                    "execution_kind": "http_json",
                    "effective_result_output_keys": ["status", "message"],
                    "output": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                    "output_preview": {
                        "status": "ready",
                        "message": "preview token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        }
        loop_execution_result = {
            "trace_event": {
                "task_id": "task-1",
                "step_id": "step-http-json-stream-output",
                "step": raw_step,
            },
            "success_effects": {
                "trace_step": raw_step,
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-http-json-stream-output",
                    "step": raw_step,
                },
                "observation": "Provider Status: ok",
                "rag_followup": None,
            },
            "terminal_effects": None,
            "should_return": False,
        }

        result = build_tool_plan_item_stream_effects(
            loop_execution_result=loop_execution_result,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_plan_item_stream_effects_redacts_raw_diagnostics_payload(
        self,
    ) -> None:
        loop_execution_result = {
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
            "success_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": (
                        "provider_search: unsupported tool execution kind api_key=hidden"
                    ),
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": (
                            "provider_search: http_json execution headers.x-api-key must be safe"
                        ),
                    },
                },
                "observation": "provider_search failed with token=hidden",
                "rag_followup": None,
            },
            "terminal_effects": None,
            "should_return": False,
        }

        result = build_tool_plan_item_stream_effects(
            loop_execution_result=loop_execution_result,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_terminal_return_effects_keeps_shape(self) -> None:
        terminal_effects = {
            "trace_step": {
                "id": "step-1",
                "seq": 3,
                "content": "Tool error: calc_eval",
            },
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool error: calc_eval",
                },
            },
            "status": "failed",
            "error_message": "fatal",
            "audit_detail": {"step_id": "step-1", "retry_count": 1},
            "state": {"task_id": "task-1", "phase": "error"},
        }

        result = build_tool_plan_item_terminal_return_effects(
            terminal_effects=terminal_effects,
        )

        self.assertEqual(result["task_status"], "failed")
        self.assertEqual(result["state_event"]["phase"], "error")
        self.assertEqual(result["failure_event"]["event_type"], "task_failed")
        self.assertEqual(result["failure_event"]["code"], "tool_execution_error")
        self.assertEqual(result["failure_event"]["message"], "fatal")
        self.assertEqual(
            result["failure_event"]["detail"],
            {"step_id": "step-1", "retry_count": 1},
        )

    def test_build_tool_plan_item_terminal_return_effects_redacts_raw_diagnostics_payload(
        self,
    ) -> None:
        terminal_effects = {
            "trace_step": {
                "id": "step-1",
                "seq": 3,
                "content": (
                    "provider_search: unsupported tool execution kind api_key=hidden"
                ),
            },
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": (
                        "provider_search: http_json execution headers.x-api-key must be safe"
                    ),
                },
            },
            "status": "failed",
            "error_message": "provider_search failed with token=hidden",
            "audit_detail": {
                "path": "query_params.access_token",
                "message": "json_body.client_secret is invalid",
            },
            "state": {
                "task_id": "task-1",
                "phase": "error",
                "message": "api_key=hidden",
            },
        }

        result = build_tool_plan_item_terminal_return_effects(
            terminal_effects=terminal_effects,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("provider_search failed with [redacted]", serialized)
        self.assertIn("[redacted] is invalid", serialized)

    def test_build_tool_plan_item_return_action_keeps_shape(self) -> None:
        terminal_return_effects = {
            "task_status": "failed",
            "state_event": {"task_id": "task-1", "phase": "error"},
            "failure_event": {
                "event_type": "task_failed",
                "code": "tool_execution_error",
                "message": "fatal",
                "detail": {"step_id": "step-1", "retry_count": 1},
            },
        }
        trace_steps = [
            {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
        ]

        result = build_tool_plan_item_return_action(
            task_id="task-1",
            trace_steps=trace_steps,
            user_id="user-1",
            terminal_return_effects=terminal_return_effects,
        )

        self.assertEqual(
            result["complete_task_kwargs"],
            {
                "task_id": "task-1",
                "trace_steps": trace_steps,
                "user_id": "user-1",
                "status": "failed",
            },
        )
        self.assertEqual(
            result["failure_event_kwargs"],
            terminal_return_effects["failure_event"],
        )
        self.assertEqual(
            result["state_event"],
            terminal_return_effects["state_event"],
        )

    def test_build_tool_plan_item_trace_write_action_keeps_shape(self) -> None:
        trace_write = {
            "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
            "event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
            },
            "force_persist": False,
        }

        result = build_tool_plan_item_trace_write_action(trace_write=trace_write)

        self.assertEqual(result["trace_step"], trace_write["step"])
        self.assertEqual(result["trace_event"], trace_write["event"])
        self.assertEqual(result["persist_force"], False)

    def test_build_tool_plan_item_continue_action_keeps_shape(self) -> None:
        continue_update = {
            "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
            "seq_increment": 1,
        }

        result = build_tool_plan_item_continue_action(
            continue_update=continue_update,
        )

        self.assertEqual(
            result,
            {
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
        )

    def test_build_tool_plan_item_next_action_execution_keeps_continue_shape(self) -> None:
        next_action = {
            "kind": "continue",
            "continue_update": {
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
            "terminal_return_effects": None,
        }

        result = build_tool_plan_item_next_action_execution(
            task_id="task-1",
            trace_steps=[{"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"}],
            user_id="user-1",
            next_action=next_action,
        )

        self.assertEqual(
            result,
            {
                "kind": "continue",
                "continue_update": next_action["continue_update"],
                "continue_action": next_action["continue_update"],
                "return_action": None,
            },
        )

    def test_build_tool_plan_item_next_action_execution_keeps_return_shape(self) -> None:
        next_action = {
            "kind": "return",
            "continue_update": {
                "tool_observations": [],
                "seq_increment": 0,
            },
            "terminal_return_effects": {
                "task_status": "failed",
                "state_event": {"task_id": "task-1", "phase": "error"},
                "failure_event": {
                    "event_type": "task_failed",
                    "code": "tool_execution_error",
                    "message": "fatal",
                    "detail": {"step_id": "step-1", "retry_count": 1},
                },
            },
        }
        trace_steps = [
            {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
        ]

        result = build_tool_plan_item_next_action_execution(
            task_id="task-1",
            trace_steps=trace_steps,
            user_id="user-1",
            next_action=next_action,
        )

        self.assertEqual(result["kind"], "return")
        self.assertEqual(result["continue_update"], next_action["continue_update"])
        self.assertEqual(
            result["continue_action"],
            next_action["continue_update"],
        )
        self.assertEqual(
            result["return_action"],
            {
                "complete_task_kwargs": {
                    "task_id": "task-1",
                    "trace_steps": trace_steps,
                    "user_id": "user-1",
                    "status": "failed",
                },
                "failure_event_kwargs": next_action["terminal_return_effects"]["failure_event"],
                "state_event": next_action["terminal_return_effects"]["state_event"],
            },
        )

    def test_build_tool_plan_item_next_action_execution_redacts_raw_diagnostics_payload(
        self,
    ) -> None:
        next_action = {
            "kind": "return",
            "continue_update": {
                "tool_observations": [
                    "provider_search failed with token=hidden",
                ],
                "seq_increment": 0,
            },
            "terminal_return_effects": {
                "task_status": "failed",
                "state_event": {
                    "task_id": "task-1",
                    "phase": "error",
                    "message": "api_key=hidden",
                },
                "failure_event": {
                    "event_type": "task_failed",
                    "code": "tool_execution_error",
                    "message": (
                        "provider_search: http_json execution query_params.access_token must be safe"
                    ),
                    "detail": {
                        "path": "headers.x-api-key",
                        "message": "json_body.client_secret is invalid",
                    },
                },
            },
        }
        trace_steps = [
            {
                "id": "step-1",
                "seq": 3,
                "content": (
                    "provider_search: unsupported tool execution kind api_key=hidden"
                ),
            },
        ]

        result = build_tool_plan_item_next_action_execution(
            task_id="task-1",
            trace_steps=trace_steps,
            user_id="user-1",
            next_action=next_action,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_trace_write_service_action_keeps_shape(self) -> None:
        trace_write_action = {
            "trace_step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
            "trace_event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
            },
            "persist_force": False,
        }

        result = build_tool_plan_item_trace_write_service_action(
            trace_write_action=trace_write_action,
        )

        self.assertEqual(
            result,
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
        )

    def test_build_tool_plan_item_continue_service_action_keeps_shape(self) -> None:
        continue_action = {
            "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
            "seq_increment": 1,
        }

        result = build_tool_plan_item_continue_service_action(
            continue_action=continue_action,
        )

        self.assertEqual(
            result,
            {
                "kind": "continue",
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
        )

    def test_build_tool_plan_item_return_service_actions_keep_shape(self) -> None:
        return_action = {
            "complete_task_kwargs": {
                "task_id": "task-1",
                "trace_steps": [{"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"}],
                "user_id": "user-1",
                "status": "failed",
            },
            "failure_event_kwargs": {
                "event_type": "task_failed",
                "code": "tool_execution_error",
                "message": "fatal",
                "detail": {"step_id": "step-1", "retry_count": 1},
            },
            "state_event": {"task_id": "task-1", "phase": "error"},
        }

        result = build_tool_plan_item_return_service_actions(
            return_action=return_action,
        )

        self.assertEqual(
            result,
            [
                {
                    "kind": "complete_task",
                    "kwargs": return_action["complete_task_kwargs"],
                },
                {
                    "kind": "record_failure_event",
                    "kwargs": return_action["failure_event_kwargs"],
                },
                {
                    "kind": "emit_state",
                    "event": "state",
                    "data": return_action["state_event"],
                },
                {
                    "kind": "return",
                },
            ],
        )

    def test_build_tool_plan_item_service_actions_keep_continue_order(self) -> None:
        service_execution = {
            "trace_write_actions": [
                {
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    },
                    "persist_force": False,
                },
            ],
            "next_action_execution": {
                "kind": "continue",
                "continue_update": {
                    "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                    "seq_increment": 1,
                },
                "continue_action": {
                    "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                    "seq_increment": 1,
                },
                "return_action": None,
            },
        }

        result = build_tool_plan_item_service_actions(
            service_execution=service_execution,
        )

        self.assertEqual(
            result,
            [
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
            ],
        )

    def test_build_tool_plan_item_service_actions_keep_return_order(self) -> None:
        service_execution = {
            "trace_write_actions": [
                {
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    },
                    "persist_force": True,
                },
            ],
            "next_action_execution": {
                "kind": "return",
                "continue_update": {
                    "tool_observations": [],
                    "seq_increment": 0,
                },
                "continue_action": {
                    "tool_observations": [],
                    "seq_increment": 0,
                },
                "return_action": {
                    "complete_task_kwargs": {
                        "task_id": "task-1",
                        "trace_steps": [{"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"}],
                        "user_id": "user-1",
                        "status": "failed",
                    },
                    "failure_event_kwargs": {
                        "event_type": "task_failed",
                        "code": "tool_execution_error",
                        "message": "fatal",
                        "detail": {"step_id": "step-1", "retry_count": 1},
                    },
                    "state_event": {"task_id": "task-1", "phase": "error"},
                },
            },
        }

        result = build_tool_plan_item_service_actions(
            service_execution=service_execution,
        )

        self.assertEqual(
            result,
            [
                {
                    "kind": "trace_write",
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    },
                    "persist_force": True,
                },
                {
                    "kind": "complete_task",
                    "kwargs": service_execution["next_action_execution"]["return_action"]["complete_task_kwargs"],
                },
                {
                    "kind": "record_failure_event",
                    "kwargs": service_execution["next_action_execution"]["return_action"]["failure_event_kwargs"],
                },
                {
                    "kind": "emit_state",
                    "event": "state",
                    "data": service_execution["next_action_execution"]["return_action"]["state_event"],
                },
                {
                    "kind": "return",
                },
            ],
        )

    def test_build_tool_plan_item_service_actions_redacts_raw_diagnostics_payload(
        self,
    ) -> None:
        service_execution = {
            "trace_write_actions": [
                {
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
            ],
            "next_action_execution": {
                "kind": "return",
                "continue_update": {
                    "tool_observations": [],
                    "seq_increment": 0,
                },
                "continue_action": {
                    "tool_observations": [],
                    "seq_increment": 0,
                },
                "return_action": {
                    "complete_task_kwargs": {
                        "task_id": "task-1",
                        "trace_steps": [
                            {
                                "id": "step-1",
                                "seq": 3,
                                "content": (
                                    "provider_search failed with token=hidden"
                                ),
                            },
                        ],
                        "user_id": "user-1",
                        "status": "failed",
                    },
                    "failure_event_kwargs": {
                        "event_type": "task_failed",
                        "code": "tool_execution_error",
                        "message": (
                            "provider_search: http_json execution headers.x-api-key must be safe"
                        ),
                        "detail": {
                            "path": "json_body.client_secret",
                            "message": "api_key=hidden",
                        },
                    },
                    "state_event": {
                        "task_id": "task-1",
                        "phase": "error",
                        "message": "token=hidden",
                    },
                },
            },
        }

        result = build_tool_plan_item_service_actions(
            service_execution=service_execution,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_service_effects_execution_keeps_continue_shape(self) -> None:
        service_effects = {
            "trace_write_actions": [
                {
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"},
                    },
                    "persist_force": False,
                },
            ],
            "next_action": {
                "kind": "continue",
                "continue_update": {
                    "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                    "seq_increment": 1,
                },
                "terminal_return_effects": None,
            },
        }

        result = build_tool_plan_item_service_effects_execution(
            task_id="task-1",
            trace_steps=[{"id": "step-1", "seq": 3, "content": "Tool done: mock_retrieve"}],
            user_id="user-1",
            service_effects=service_effects,
        )

        self.assertEqual(result["trace_write_actions"], service_effects["trace_write_actions"])
        self.assertEqual(result["next_action_execution"]["kind"], "continue")
        self.assertEqual(
            result["next_action_execution"]["continue_update"],
            service_effects["next_action"]["continue_update"],
        )
        self.assertEqual(
            result["next_action_execution"]["continue_action"],
            service_effects["next_action"]["continue_update"],
        )
        self.assertIsNone(result["next_action_execution"]["return_action"])
        self.assertEqual(
            result["service_actions"],
            [
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
            ],
        )

    def test_build_tool_plan_item_service_effects_execution_keeps_return_shape(self) -> None:
        service_effects = {
            "trace_write_actions": [
                {
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    },
                    "persist_force": True,
                },
            ],
            "next_action": {
                "kind": "return",
                "continue_update": {
                    "tool_observations": [],
                    "seq_increment": 0,
                },
                "terminal_return_effects": {
                    "task_status": "failed",
                    "state_event": {"task_id": "task-1", "phase": "error"},
                    "failure_event": {
                        "event_type": "task_failed",
                        "code": "tool_execution_error",
                        "message": "fatal",
                        "detail": {"step_id": "step-1", "retry_count": 1},
                    },
                },
            },
        }
        trace_steps = [{"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"}]

        result = build_tool_plan_item_service_effects_execution(
            task_id="task-1",
            trace_steps=trace_steps,
            user_id="user-1",
            service_effects=service_effects,
        )

        self.assertEqual(result["trace_write_actions"], service_effects["trace_write_actions"])
        self.assertEqual(result["next_action_execution"]["kind"], "return")
        self.assertEqual(
            result["next_action_execution"]["continue_action"],
            service_effects["next_action"]["continue_update"],
        )
        self.assertEqual(
            result["next_action_execution"]["return_action"],
            {
                "complete_task_kwargs": {
                    "task_id": "task-1",
                    "trace_steps": trace_steps,
                    "user_id": "user-1",
                    "status": "failed",
                },
                "failure_event_kwargs": service_effects["next_action"]["terminal_return_effects"]["failure_event"],
                "state_event": service_effects["next_action"]["terminal_return_effects"]["state_event"],
            },
        )
        self.assertEqual(
            result["service_actions"],
            [
                {
                    "kind": "trace_write",
                    "trace_step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "step": {"id": "step-1", "seq": 3, "content": "Tool error: calc_eval"},
                    },
                    "persist_force": True,
                },
                {
                    "kind": "complete_task",
                    "kwargs": result["next_action_execution"]["return_action"]["complete_task_kwargs"],
                },
                {
                    "kind": "record_failure_event",
                    "kwargs": result["next_action_execution"]["return_action"]["failure_event_kwargs"],
                },
                {
                    "kind": "emit_state",
                    "event": "state",
                    "data": result["next_action_execution"]["return_action"]["state_event"],
                },
                {
                    "kind": "return",
                },
            ],
        )

    def test_build_tool_plan_item_service_effects_execution_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-service-effects-execution-http-json-output"
        )
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-service-effects-execution-http-json-output",
            "step": raw_step,
        }
        service_effects = {
            "trace_write_actions": [
                {
                    "trace_step": raw_step,
                    "trace_event": trace_event,
                    "persist_force": False,
                },
            ],
            "next_action": {
                "kind": "continue",
                "continue_update": {
                    "tool_observations": ["Provider Status: ok"],
                    "seq_increment": 0,
                },
                "terminal_return_effects": None,
            },
        }

        result = build_tool_plan_item_service_effects_execution(
            task_id="task-1",
            trace_steps=[raw_step],
            user_id="user-1",
            service_effects=service_effects,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_plan_item_service_execution_keeps_success_shape(self) -> None:
        loop_execution_result = {
            "trace_event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
            },
            "success_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": "Tool done: mock_retrieve",
                    },
                },
                "observation": 'mock_retrieve: {"chunks": ["alpha"]}',
                "rag_followup": {
                    "step": {
                        "id": "rag-1",
                        "seq": 4,
                        "content": "Retrieved snippets",
                    },
                    "trace": {
                        "task_id": "task-1",
                        "step_id": "rag-1",
                        "step": {
                            "id": "rag-1",
                            "seq": 4,
                            "content": "Retrieved snippets",
                        },
                    },
                },
            },
            "terminal_effects": None,
            "should_return": False,
        }

        result = build_tool_plan_item_service_execution(
            task_id="task-1",
            trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
            user_id="user-1",
            loop_execution_result=loop_execution_result,
        )

        self.assertEqual(
            [(item["trace_step"]["id"], item["trace_event"]["step_id"], item["persist_force"]) for item in result["trace_write_actions"]],
            [("step-1", "step-1", False), ("rag-1", "rag-1", False)],
        )
        self.assertEqual(result["next_action_execution"]["kind"], "continue")
        self.assertEqual(
            result["next_action_execution"]["continue_update"],
            {
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
        )

    def test_build_tool_plan_item_service_execution_keeps_terminal_shape(self) -> None:
        loop_execution_result = {
            "trace_event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool error: calc_eval",
                },
            },
            "success_effects": None,
            "terminal_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool error: calc_eval",
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": "Tool error: calc_eval",
                    },
                },
                "status": "failed",
                "error_message": "fatal",
                "audit_detail": {"step_id": "step-1", "retry_count": 1},
                "state": {"task_id": "task-1", "phase": "error"},
            },
            "should_return": True,
        }

        result = build_tool_plan_item_service_execution(
            task_id="task-1",
            trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
            user_id="user-1",
            loop_execution_result=loop_execution_result,
        )

        self.assertEqual(
            [(item["trace_step"]["id"], item["trace_event"]["step_id"], item["persist_force"]) for item in result["trace_write_actions"]],
            [("step-1", "step-1", True)],
        )
        self.assertEqual(result["next_action_execution"]["kind"], "return")
        self.assertEqual(
            result["next_action_execution"]["return_action"]["complete_task_kwargs"]["status"],
            "failed",
        )

    def test_build_tool_plan_item_service_execution_redacts_raw_diagnostics_payload(
        self,
    ) -> None:
        loop_execution_result = {
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
            "success_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": (
                        "provider_search: unsupported tool execution kind api_key=hidden"
                    ),
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": (
                            "provider_search: http_json execution headers.x-api-key must be safe"
                        ),
                    },
                },
                "observation": "provider_search failed with token=hidden",
                "rag_followup": None,
            },
            "terminal_effects": None,
            "should_return": False,
        }

        result = build_tool_plan_item_service_execution(
            task_id="task-1",
            trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
            user_id="user-1",
            loop_execution_result=loop_execution_result,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_service_effects_keeps_success_shape(self) -> None:
        loop_execution_result = {
            "trace_event": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
            },
            "success_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool done: mock_retrieve",
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": "Tool done: mock_retrieve",
                    },
                },
                "observation": 'mock_retrieve: {"chunks": ["alpha"]}',
                "rag_followup": {
                    "step": {
                        "id": "rag-1",
                        "seq": 4,
                        "content": "Retrieved snippets",
                    },
                    "trace": {
                        "task_id": "task-1",
                        "step_id": "rag-1",
                        "step": {
                            "id": "rag-1",
                            "seq": 4,
                            "content": "Retrieved snippets",
                        },
                    },
                },
            },
            "terminal_effects": None,
            "should_return": False,
        }

        result = build_tool_plan_item_service_effects(
            loop_execution_result=loop_execution_result,
        )

        self.assertFalse(bool(result["should_return"]))
        self.assertEqual(
            [(item["step"]["id"], item["event"]["step_id"], item["force_persist"]) for item in result["trace_writes"]],
            [("step-1", "step-1", False), ("rag-1", "rag-1", False)],
        )
        self.assertEqual(
            [(item["trace_step"]["id"], item["trace_event"]["step_id"], item["persist_force"]) for item in result["trace_write_actions"]],
            [("step-1", "step-1", False), ("rag-1", "rag-1", False)],
        )
        self.assertEqual(
            result["continue_update"],
            {
                "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                "seq_increment": 1,
            },
        )
        self.assertEqual(
            result["next_action"],
            {
                "kind": "continue",
                "continue_update": {
                    "tool_observations": ['mock_retrieve: {"chunks": ["alpha"]}'],
                    "seq_increment": 1,
                },
                "terminal_return_effects": None,
            },
        )
        self.assertEqual(result["terminal_return_effects"], None)
        self.assertEqual(result["tool_observations"], ['mock_retrieve: {"chunks": ["alpha"]}'])
        self.assertEqual(result["seq_increment"], 1)
        self.assertEqual([step["id"] for step in result["trace_steps"]], ["step-1", "rag-1"])
        self.assertEqual([event["step_id"] for event in result["trace_events"]], ["step-1", "rag-1"])

    def test_build_tool_plan_item_service_effects_redacts_raw_diagnostics_payload(
        self,
    ) -> None:
        loop_execution_result = {
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
            "success_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": (
                        "provider_search: unsupported tool execution kind api_key=hidden"
                    ),
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": (
                            "provider_search: http_json execution headers.x-api-key must be safe"
                        ),
                    },
                },
                "observation": "provider_search failed with token=hidden",
                "rag_followup": None,
            },
            "terminal_effects": None,
            "should_return": False,
        }

        result = build_tool_plan_item_service_effects(
            loop_execution_result=loop_execution_result,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_service_effects_keeps_terminal_shape(self) -> None:
        terminal_effects = {
            "trace_step": {
                "id": "step-1",
                "seq": 3,
                "content": "Tool error: calc_eval",
            },
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": "Tool error: calc_eval",
                },
            },
            "status": "failed",
            "error_message": "fatal",
            "audit_detail": {"step_id": "step-1", "retry_count": 1},
            "state": {"task_id": "task-1", "phase": "error"},
        }
        loop_execution_result = {
            "trace_event": terminal_effects["trace"],
            "success_effects": None,
            "terminal_effects": terminal_effects,
            "should_return": True,
        }

        result = build_tool_plan_item_service_effects(
            loop_execution_result=loop_execution_result,
        )

        self.assertTrue(bool(result["should_return"]))
        self.assertEqual(
            [(item["step"]["id"], item["event"]["step_id"], item["force_persist"]) for item in result["trace_writes"]],
            [("step-1", "step-1", True)],
        )
        self.assertEqual(
            [(item["trace_step"]["id"], item["trace_event"]["step_id"], item["persist_force"]) for item in result["trace_write_actions"]],
            [("step-1", "step-1", True)],
        )
        self.assertEqual(
            result["continue_update"],
            {
                "tool_observations": [],
                "seq_increment": 0,
            },
        )
        self.assertEqual(
            result["next_action"],
            {
                "kind": "return",
                "continue_update": {
                    "tool_observations": [],
                    "seq_increment": 0,
                },
                "terminal_return_effects": result["terminal_return_effects"],
            },
        )
        self.assertEqual(result["tool_observations"], [])
        self.assertEqual(result["seq_increment"], 0)
        self.assertEqual(
            result["terminal_return_effects"]["failure_event"]["message"],
            "fatal",
        )
        self.assertEqual(
            result["terminal_return_effects"]["state_event"]["phase"],
            "error",
        )

    def test_execute_tool_plan_item_retry_loop_yields_start_events_before_runner(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="mock_retrieve",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        runner_calls: list[tuple[int, str]] = []

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            runner_calls.append((attempt, user_id))
            return {
                "chunks": ["alpha", "beta"],
                "knowledge_base_id": "demo-kb",
                "hit_count": 2,
            }

        items = execute_tool_plan_item_retry_loop(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            initial_action_step=iteration_ctx["action_step"],
            tool_name="mock_retrieve",
            tool_input={"query": "demo"},
            prompt="检索 demo",
            user_id="user-1",
            model="mock-gpt",
            estimate_token_count=lambda text: len(text.strip()) or 0,
            make_step_id=lambda: "rag-1",
            raise_if_should_abort=lambda: None,
            run_tool_fn=fake_run_tool,
        )

        first = next(items)
        second = next(items)
        self.assertEqual(runner_calls, [])
        third = next(items)
        final_item = next(items)

        self.assertEqual(first["kind"], "event")
        self.assertEqual(first["event"], "tool_start")
        self.assertEqual(first["data"]["kind"], "knowledge_retrieval")
        self.assertEqual(first["data"]["semantic_kind"], "knowledge_retrieval")
        self.assertTrue(first["data"]["supports_result_preview"])
        self.assertEqual(
            first["data"]["effective_result_preview_keys"],
            ["hit_count", "knowledge_base_id"],
        )
        self.assertEqual(second["kind"], "event")
        self.assertEqual(second["event"], "state")
        self.assertEqual(third["kind"], "event")
        self.assertEqual(third["event"], "tool_end")
        self.assertEqual(runner_calls, [(0, "user-1")])
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(final_item["result"]["retry_loop_result"]["outcome"], "success")
        self.assertFalse(bool(final_item["result"]["should_return"]))
        self.assertEqual(
            final_item["result"]["trace_event"]["step"]["content"],
            "Tool done: Knowledge Retrieval",
        )
        self.assertIsNone(final_item["result"]["terminal_effects"])
        self.assertEqual(
            final_item["result"]["success_effects"]["rag_followup"]["step"]["id"],
            "rag-1",
        )

    def test_execute_tool_plan_item_retry_loop_keeps_retry_then_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempts: list[int] = []

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            attempts.append(attempt)
            if attempt == 0:
                raise MockToolExecutionError("transient", fatal=False)
            return {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            }

        items = list(
            execute_tool_plan_item_retry_loop(
                task_id="task-1",
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                run_tool_fn=fake_run_tool,
            )
        )

        self.assertEqual(attempts, [0, 1])
        self.assertEqual(
            [item["event"] for item in items if item["kind"] == "event"],
            ["tool_start", "state", "tool_end", "error", "tool_start", "state", "tool_end"],
        )
        self.assertEqual(items[2]["data"]["status"], "error")
        self.assertTrue(bool(items[3]["data"]["retryable"]))
        self.assertEqual(items[4]["data"]["retry_count"], 1)
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(final_item["result"]["retry_loop_result"]["outcome"], "success")
        self.assertEqual(
            final_item["result"]["loop_result"]["next_action_step"]["meta"]["tool"]["error"],
            "transient",
        )

    def test_execute_tool_plan_item_retry_loop_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            raise MockToolExecutionError("fatal", fatal=True)

        items = list(
            execute_tool_plan_item_retry_loop(
                task_id="task-1",
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                run_tool_fn=fake_run_tool,
            )
        )

        self.assertEqual(
            [item["event"] for item in items if item["kind"] == "event"],
            ["tool_start", "state", "tool_end", "error"],
        )
        self.assertTrue(bool(items[3]["data"]["fatal"]))
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            final_item["result"]["retry_loop_result"]["outcome"],
            "terminal_failure",
        )
        self.assertTrue(bool(final_item["result"]["should_return"]))
        self.assertIsNone(final_item["result"]["success_effects"])
        self.assertEqual(
            final_item["result"]["trace_event"]["step"]["content"],
            "Tool error: Calculator",
        )
        self.assertEqual(
            final_item["result"]["terminal_effects"]["state"]["phase"],
            "error",
        )

    def test_execute_tool_plan_item_retry_loop_accepts_custom_registry_retry_policy(self) -> None:
        attempt_calls: list[tuple[int, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            del tool_input, prompt
            attempt_calls.append((0, user_id))
            raise MockToolExecutionError("transient", fatal=False)

        registry = build_tool_registry(
            overrides={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="custom_calc",
                    label="Custom Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=9_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        items = list(
            execute_tool_plan_item_retry_loop(
                task_id="task-1",
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        self.assertEqual(attempt_calls, [(0, "")])
        self.assertEqual(
            [item["event"] for item in items if item["kind"] == "event"],
            ["tool_start", "state", "tool_end", "error"],
        )
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(final_item["result"]["outcome"], "terminal_failure")
        self.assertTrue(bool(final_item["result"]["should_return"]))

    def test_execute_tool_plan_item_retry_loop_honors_custom_error_timeout(self) -> None:
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
                    "tool_input": tool_input,
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

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            raise MockToolExecutionError("fatal", fatal=True)

        items = list(
            execute_tool_plan_item_retry_loop(
                task_id="task-1",
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
                run_tool_fn=fake_run_tool,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        self.assertEqual(tool_end_event["latency_ms"], 48)
        self.assertEqual(tool_end_event["output_preview"], {"error": "fatal"})

    def test_execute_tool_plan_item_service_execution_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="mock_retrieve",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            return {
                "chunks": ["alpha", "beta"],
                "knowledge_base_id": "demo-kb",
                "hit_count": 2,
            }

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="mock_retrieve",
                tool_input={"query": "demo"},
                prompt="检索 demo",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                run_tool_fn=fake_run_tool,
            )
        )

        self.assertEqual(
            [item["event"] for item in items if item["kind"] == "event"],
            ["tool_start", "state", "tool_end"],
        )
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            [(item["kind"], item.get("trace_step", {}).get("id")) for item in final_item["result"]["service_actions"]],
            [("trace_write", "step-1"), ("trace_write", "rag-1"), ("continue", None)],
        )
        self.assertEqual(final_item["result"]["next_action_execution"]["kind"], "continue")

    def test_execute_tool_plan_item_service_execution_keeps_terminal_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            raise MockToolExecutionError("fatal", fatal=True)

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                run_tool_fn=fake_run_tool,
            )
        )

        self.assertEqual(
            [item["event"] for item in items if item["kind"] == "event"],
            ["tool_start", "state", "tool_end", "error"],
        )
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            [item["kind"] for item in final_item["result"]["service_actions"]],
            ["trace_write", "complete_task", "record_failure_event", "emit_state", "return"],
        )
        self.assertEqual(final_item["result"]["next_action_execution"]["kind"], "return")

    def test_execute_tool_plan_item_service_execution_accepts_custom_registry(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "custom-ok",
                "tool_kind": "custom_calc",
            }

        registry = build_tool_registry(
            overrides={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="custom_calc",
                    label="Custom Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=9_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        self.assertEqual(runner_calls, [({"expression": "1+2*3"}, "calc", "")])
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "result": "custom-ok",
            },
        )

    def test_execute_tool_plan_item_service_execution_accepts_custom_registry_loader(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "loader-ok",
                "tool_kind": "loader_calc",
            }

        def custom_loader() -> dict[str, ToolRegistration]:
            return {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }

        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry_loader=custom_loader,
            )
        )

        self.assertEqual(runner_calls, [({"expression": "1+2*3"}, "calc", "")])
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "result": "loader-ok",
            },
        )

    def test_execute_tool_plan_item_service_execution_accepts_custom_registry_provider(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "provider-ok",
                "tool_kind": "provider_calc",
            }

        provider = StaticToolRegistryProvider(
            registry={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="provider_calc",
                    label="Provider Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=13_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=custom_runner,
                )
            }
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry_provider=provider,
            )
        )

        self.assertEqual(runner_calls, [({"expression": "1+2*3"}, "calc", "")])
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "result": "provider-ok",
            },
        )

    def test_execute_tool_plan_item_retry_loop_normalizes_task_plan_input_for_tool_start_and_runner(
        self,
    ) -> None:
        runner_calls: list[tuple[dict[str, object], str, str, int]] = []
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        },
                        "mock_plan_brief": {
                            "template": "mock_plan",
                            "label": "Brief Planner",
                        },
                    }
                ),
                tool_registry_overrides_json=None,
            )
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_plan",
            tool_input={
                "prompt_preview": "please plan",
                "planned_tool_names": ["mock_plan_brief", "calc_eval_fast"],
            },
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            registry_provider=registry_provider,
        )

        def fake_run_tool(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id, attempt))
            return {
                "plan": "Analyze request -> Evaluate calculation -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Evaluate calculation",
                    "Synthesize final answer",
                ],
                "prompt_preview": str(tool_input.get("prompt_preview", "")),
                "echo": True,
            }

        items = list(
            execute_tool_plan_item_retry_loop(
                task_id="task-1",
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="task_plan",
                tool_input={
                    "prompt_preview": "please plan",
                    "planned_tool_names": ["mock_plan_brief", "calc_eval_fast"],
                },
                prompt="please plan",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                run_tool_fn=fake_run_tool,
                registry_provider=registry_provider,
            )
        )

        tool_start_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_start"
        )
        normalized_input = {
            "prompt_preview": "please plan",
            "planned_tool_names": ["calc_eval_fast"],
            "planned_tool_labels": ["Fast Calculator"],
            "planned_tool_kinds": ["local_calculator"],
            "planned_tool_execution_kinds": [""],
        }

        self.assertEqual(tool_start_event["input"], normalized_input)
        self.assertEqual(
            runner_calls,
            [(normalized_input, "please plan", "user-1", 0)],
        )
        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_result"]["next_action_step"]["meta"]["tool"]["input"],
            normalized_input,
        )

    def test_run_tool_canonical_calc_override_injects_registration_kind_when_runner_omits_tool_kind(
        self,
    ) -> None:
        registry = build_tool_registry(
            overrides={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="provider_calc",
                    label="Provider Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=13_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "result": "provider-ok",
                        "expression": str(tool_input.get("expression", "")),
                    },
                )
            }
        )

        output = run_tool(
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry=registry,
        )

        self.assertEqual(
            output,
            {
                "result": "provider-ok",
                "expression": "1+2*3",
                "tool_kind": "provider_calc",
            },
        )

    def test_run_tool_canonical_calc_override_rewrites_builtin_tool_kind_to_registration_kind(
        self,
    ) -> None:
        registry = build_tool_registry(
            overrides={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="provider_calc",
                    label="Provider Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=13_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "result": "provider-ok",
                        "expression": str(tool_input.get("expression", "")),
                        "tool_kind": "local_calculator",
                    },
                )
            }
        )

        output = run_tool(
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry=registry,
        )

        self.assertEqual(
            output,
            {
                "result": "provider-ok",
                "expression": "1+2*3",
                "tool_kind": "provider_calc",
            },
        )

    def test_run_tool_real_search_override_rewrites_tool_kind_to_runtime_semantic_kind(
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
                },
                runtime_semantic_kind="provider_search",
            )
        }

        output = run_tool(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            prompt="search revenue trend",
            user_id="user-1",
            attempt=0,
            registry=registry,
        )

        self.assertEqual(
            output,
            {
                "tool_kind": "provider_search",
                "documents_total": 2,
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
            },
        )
