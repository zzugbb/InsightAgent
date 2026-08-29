from __future__ import annotations

from .context import *


class RuntimeRagExecutionMixinPart1:
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
