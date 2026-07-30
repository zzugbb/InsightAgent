from __future__ import annotations

from .context import *


class RuntimeServiceExecutionSemanticsMixin:
    def test_execute_tool_plan_item_service_execution_honors_custom_preview_policy(
        self,
    ) -> None:
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
                    "documents": [{"title": "Secret"}],
                    "tool_kind": "custom_lookup",
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

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
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
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        self.assertEqual(tool_end_event["latency_ms"], 48)
        self.assertIsNone(tool_end_event["output_preview"])

    def test_execute_tool_plan_item_service_execution_applies_custom_preview_keys(
        self,
    ) -> None:
        registry = {
            "task_retrieve_hot": ToolRegistration(
                name="task_retrieve_hot",
                kind="knowledge_retrieval",
                label="Hot Retrieval",
                retryable_by_default=True,
                default_timeout_ms=5_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "knowledge_retrieval",
                    "chunks": ["alpha", "beta"],
                    "hit_count": 2,
                    "knowledge_base_id": "demo-kb",
                    "raw_documents": [{"id": "doc-1"}],
                },
                result_preview_keys=("tool_kind", "hit_count", "knowledge_base_id"),
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_retrieve_hot",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Hot Retrieval",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="task_retrieve_hot",
                tool_input={"query": "demo"},
                prompt="retrieve demo",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "tool_kind": "knowledge_retrieval",
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_keeps_rag_followup_for_projected_retrieval_output(
        self,
    ) -> None:
        registry = {
            "task_retrieve_hot": ToolRegistration(
                name="task_retrieve_hot",
                kind="knowledge_retrieval",
                label="Hot Retrieval",
                retryable_by_default=True,
                default_timeout_ms=5_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "knowledge_retrieval",
                    "chunks": ["alpha", "beta"],
                    "hit_count": 2,
                    "knowledge_base_id": "demo-kb",
                    "raw_documents": [{"id": "doc-1"}],
                },
                result_preview_keys=("hit_count", "knowledge_base_id"),
                result_output_keys=("hit_count", "knowledge_base_id"),
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_retrieve_hot",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Hot Retrieval",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="task_retrieve_hot",
                tool_input={"query": "demo"},
                prompt="retrieve demo",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )
        self.assertEqual(
            [
                (item["kind"], item.get("trace_step", {}).get("id"))
                for item in final_item["result"]["service_actions"]
            ],
            [("trace_write", "step-1"), ("trace_write", "rag-1"), ("continue", None)],
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha", "beta"],
                "knowledge_base_id": "demo-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_uses_runtime_semantic_override_for_real_search_tool(
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
                    "chunks": ["internal retrieval stub"],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_start_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_start"
        )
        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(tool_start_event["semantic_kind"], "provider_search")
        self.assertEqual(tool_end_event["semantic_kind"], "provider_search")
        self.assertEqual(
            tool_start_event["semantic_family"],
            "knowledge_retrieval",
        )
        self.assertEqual(
            tool_end_event["semantic_family"],
            "knowledge_retrieval",
        )
        self.assertEqual(
            tool_start_event["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(
            tool_end_event["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            tool_end_event["output"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 2 documents.",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["loop_result"]["next_action_step"]["meta"]["tool"]["output"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["loop_result"]["next_action_step"]["meta"]["tool"]["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["loop_result"]["next_action_step"]["meta"]["tool"]["semantic_family"],
            "knowledge_retrieval",
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["internal retrieval stub"],
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            [
                (item["kind"], item.get("trace_step", {}).get("id"))
                for item in final_item["result"]["service_actions"]
            ],
            [("trace_write", "step-1"), ("trace_write", "rag-1"), ("continue", None)],
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_documents_for_real_search_tool(
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
                    "documents": [
                        {"snippet": "alpha snippet"},
                        {"content": "beta content"},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha snippet", "beta content"],
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            [
                (item["kind"], item.get("trace_step", {}).get("id"))
                for item in final_item["result"]["service_actions"]
            ],
            [("trace_write", "step-1"), ("trace_write", "rag-1"), ("continue", None)],
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_items_for_real_search_tool(
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
                    "items": [
                        {"snippet": "alpha item snippet"},
                        {"content": "beta item content"},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["content"],
            "Provider Search returned snippets.",
        )
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha item snippet", "beta item content"],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_data_camel_case_text_fields(
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
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "data": [
                        {"documentText": "alpha document text"},
                        {"payload": {"pageContent": "beta page content"}},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "incident timeline"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "incident timeline"},
                prompt="search incident timeline",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha document text", "beta page content"],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_records_text_aliases(
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
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "records": [
                        {"chunkText": "alpha chunk text"},
                        {"passage": "beta passage"},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "capacity plan"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "capacity plan"},
                prompt="search capacity plan",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha chunk text", "beta passage"],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_camel_text_aliases(
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
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "results": [
                        {"snippetText": "alpha snippet text"},
                        {"payload": {"contentText": "beta content text"}},
                        {"metadata": {"textContent": "gamma text content"}},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "incident evidence"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "incident evidence"},
                prompt="search incident evidence",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 3,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": [
                    "alpha snippet text",
                    "beta content text",
                    "gamma text content",
                ],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_builds_rag_followup_from_attribute_containers(
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
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "results": [
                        {"attributes": {"snippetText": "alpha attribute snippet"}},
                        {"source": {"contentText": "beta source content"}},
                        {"fields": {"textContent": "gamma fields text"}},
                    ],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "incident evidence"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "incident evidence"},
                prompt="search incident evidence",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 3,
            },
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": [
                    "alpha attribute snippet",
                    "beta source content",
                    "gamma fields text",
                ],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_rewrites_real_search_tool_kind_to_runtime_semantic_kind(
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
                    "chunks": ["internal retrieval stub"],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("tool_kind", "documents_total"),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "tool_kind": "provider_search",
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"]["tool_kind"],
            "provider_search",
        )

    def test_execute_tool_plan_item_service_execution_falls_back_result_output_keys_to_preview_keys_for_runtime_override_real_search_tool(
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
                    "chunks": ["internal retrieval stub"],
                    "knowledge_base_id": "provider-kb",
                },
                result_preview_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_start_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_start"
        )
        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_start_event["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(
            tool_end_event["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["loop_result"]["next_action_step"]["meta"]["tool"]["output"],
            {
                "documents_total": 2,
            },
        )

    def test_execute_tool_plan_item_service_execution_infers_preview_and_output_keys_from_semantic_family_for_runtime_override_real_search_tool(
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
                    "hit_count": 2,
                    "knowledge_base_id": "provider-kb",
                    "chunks": ["internal retrieval stub"],
                    "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_start_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_start"
        )
        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_start_event["effective_result_preview_keys"],
            ["documents_total", "hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            tool_end_event["effective_result_preview_keys"],
            ["documents_total", "hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            tool_start_event["effective_result_output_keys"],
            ["documents_total", "hit_count", "knowledge_base_id", "request_id"],
        )
        self.assertEqual(
            tool_end_event["effective_result_output_keys"],
            ["documents_total", "hit_count", "knowledge_base_id", "request_id"],
        )
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 2 hits.",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["loop_result"]["next_action_step"]["meta"]["tool"]["output"],
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_execute_tool_plan_item_service_execution_preserves_request_id_in_hit_projection_summary_for_runtime_override_real_search_tool(
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
                    "hit_count": 2,
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-1",
                    "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["result_summary"],
            "Retrieved 2 hits (request id req-1).",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 2 hits (request id req-1).",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-1",
            },
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_preview_for_runtime_override_real_search_tool(
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
                    "request_id": "req-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_start_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_start"
        )
        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_start_event["effective_result_preview_keys"],
            ["documents_total", "hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            tool_end_event["effective_result_preview_keys"],
            ["documents_total", "hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
                "request_id": "req-1",
            },
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_from_provider_total_count(
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
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "total_count": "2",
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-total-count-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-total-count-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 2 documents from provider-kb (request id req-total-count-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_calc_result_from_provider_value(
        self,
    ) -> None:
        registry = {
            "provider_math": ToolRegistration(
                name="provider_math",
                kind="provider_calc",
                label="Provider Calculator",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_calc",
                    "expression": "3+4",
                    "value": "7",
                    "request_id": "req-value-1",
                },
                runtime_semantic_kind="provider_math",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_math",
            tool_input={"expression": "3+4"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Calculator",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_math",
                tool_input={"expression": "3+4"},
                prompt="calculate 3+4",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "expression": "3+4",
                "result": "7",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "expression": "3+4",
                "result": "7",
                "request_id": "req-value-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Calculator: Calculated 3+4 = 7 (request id req-value-1).",
        )

    def test_execute_tool_plan_item_service_execution_normalizes_provider_request_id_aliases(
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
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "documents_total": 1,
                    "knowledge_base_id": "provider-kb",
                    "requestId": "req-camel-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "latency"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "latency"},
                prompt="search latency",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]

        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 1,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-camel-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 1 document from provider-kb (request id req-camel-1).",
        )

    def test_execute_tool_plan_item_service_execution_normalizes_provider_trace_id_alias(
        self,
    ) -> None:
        registry = {
            "provider_math": ToolRegistration(
                name="provider_math",
                kind="provider_calc",
                label="Provider Calculator",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_calc",
                    "expression": "10-3",
                    "answer": 7,
                    "trace_id": "trace-7",
                },
                runtime_semantic_kind="provider_math",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_math",
            tool_input={"expression": "10-3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Calculator",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_math",
                tool_input={"expression": "10-3"},
                prompt="calculate 10-3",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]

        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "expression": "10-3",
                "result": 7,
                "request_id": "trace-7",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Calculator: Calculated 10-3 = 7 (request id trace-7).",
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_from_provider_total_count_camel_case(
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
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "totalCount": 3,
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-total-count-camel-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "throughput"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "throughput"},
                prompt="search throughput",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]

        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 3,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-total-count-camel-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 3 documents from provider-kb (request id req-total-count-camel-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_calc_result_from_provider_computed_value(
        self,
    ) -> None:
        registry = {
            "provider_math": ToolRegistration(
                name="provider_math",
                kind="provider_calc",
                label="Provider Calculator",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_calc",
                    "expression": "6*7",
                    "computedValue": 42,
                    "request_id": "req-computed-1",
                },
                runtime_semantic_kind="provider_math",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_math",
            tool_input={"expression": "6*7"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Calculator",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_math",
                tool_input={"expression": "6*7"},
                prompt="calculate 6*7",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]

        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "expression": "6*7",
                "result": 42,
                "request_id": "req-computed-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Calculator: Calculated 6*7 = 42 (request id req-computed-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_from_provider_documents_total_camel_case(
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
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "documentsTotal": 4,
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-documents-total-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "availability"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "availability"},
                prompt="search availability",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        final_item = items[-1]

        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 4,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-documents-total-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 4 documents from provider-kb (request id req-documents-total-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_from_provider_records_total_alias(
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
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "recordsTotal": "8",
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-records-total-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "records"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "records"},
                prompt="search records",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 8,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 8,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-records-total-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 8 documents from provider-kb (request id req-records-total-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_documents_total_from_provider_doc_count_alias(
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
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "docCount": "10",
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-doc-count-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "documents"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "documents"},
                prompt="search documents",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 10,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "documents_total": 10,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-doc-count-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 10 documents from provider-kb (request id req-doc-count-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_hit_count_from_provider_hit_count_camel_case(
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
                result_preview_keys=("hit_count", "knowledge_base_id"),
                result_output_keys=("hit_count", "knowledge_base_id", "request_id"),
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_kind": "provider_retrieval",
                    "hitCount": 5,
                    "knowledge_base_id": "provider-kb",
                    "request_id": "req-hit-count-1",
                },
                runtime_semantic_kind="provider_search",
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "queue depth"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Provider Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="provider_search",
                tool_input={"query": "queue depth"},
                prompt="search queue depth",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "hit_count": 5,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "hit_count": 5,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-hit-count-1",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Provider Search: Retrieved 5 hits (request id req-hit-count-1).",
        )

    def test_execute_tool_plan_item_service_execution_infers_label_only_real_search_tool_semantics(
        self,
    ) -> None:
        registry = {
            "hosted_search_gateway": ToolRegistration(
                name="hosted_search_gateway",
                kind=None,
                label="Hosted Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {
                    "documents_total": 2,
                    "documents": [
                        {"snippet": "alpha snippet"},
                        {"content": "beta content"},
                    ],
                    "knowledge_base_id": "hosted-kb",
                    "request_id": "req-hosted-1",
                },
            )
        }
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="hosted_search_gateway",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Hosted Search",
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="hosted_search_gateway",
                tool_input={"query": "revenue trend"},
                prompt="search revenue trend",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-1",
                raise_if_should_abort=lambda: None,
                registry=registry,
            )
        )

        tool_start_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_start"
        )
        tool_end_event = next(
            item["data"]
            for item in items
            if item.get("kind") == "event" and item.get("event") == "tool_end"
        )
        final_item = items[-1]

        self.assertEqual(tool_start_event["semantic_kind"], "hosted_search_gateway")
        self.assertEqual(tool_start_event["semantic_family"], "knowledge_retrieval")
        self.assertEqual(
            tool_end_event["output"],
            {
                "documents_total": 2,
                "knowledge_base_id": "hosted-kb",
                "request_id": "req-hosted-1",
            },
        )
        self.assertEqual(
            tool_end_event["output_preview"],
            {
                "documents_total": 2,
                "knowledge_base_id": "hosted-kb",
            },
        )
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["observation"],
            "Hosted Search: Retrieved 2 documents from hosted-kb (request id req-hosted-1).",
        )
        rag_followup = final_item["result"]["loop_execution_result"]["success_effects"][
            "rag_followup"
        ]
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(rag_followup["step"]["content"], "Hosted Search returned snippets.")
        self.assertEqual(
            rag_followup["step"]["meta"]["rag"],
            {
                "chunks": ["alpha snippet", "beta content"],
                "knowledge_base_id": "hosted-kb",
            },
        )

    def test_build_tool_result_summary_does_not_imply_local_kb_for_runtime_override_real_tool_with_hit_projection(
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
            result_preview_keys=("hit_count", "knowledge_base_id"),
            result_output_keys=("hit_count", "knowledge_base_id"),
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "tool_kind": "provider_retrieval",
            },
        )

        output = {
            "hit_count": 2,
            "knowledge_base_id": "provider-kb",
            "tool_kind": "provider_retrieval",
        }

        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 hits.",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search: Retrieved 2 hits.",
        )

    def test_execute_tool_plan_item_service_actions_keeps_continue_shape(self) -> None:
        trace_steps = [{"id": "existing-1", "seq": 2, "content": "Existing"}]
        tool_observations: list[str] = []
        persist_forces: list[bool] = []
        complete_calls: list[dict[str, object]] = []
        failure_calls: list[dict[str, object]] = []
        service_actions = [
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
        ]

        items = list(
            execute_tool_plan_item_service_actions(
                service_actions=service_actions,
                trace_steps=trace_steps,
                tool_observations=tool_observations,
                seq_cursor=3,
                persist_trace_fn=lambda *, force: persist_forces.append(bool(force)),
                complete_task_fn=lambda **kwargs: complete_calls.append(kwargs),
                record_failure_event_fn=lambda **kwargs: failure_calls.append(kwargs),
            )
        )

        self.assertEqual([item["kind"] for item in items], ["event", "result"])
        self.assertEqual(items[0]["event"], "trace")
        self.assertEqual(items[0]["data"]["step_id"], "step-1")
        self.assertEqual(items[1]["result"], {"seq_cursor": 4, "should_return": False})
        self.assertEqual([step["id"] for step in trace_steps], ["existing-1", "step-1"])
        self.assertEqual(tool_observations, ['mock_retrieve: {"chunks": ["alpha"]}'])
        self.assertEqual(persist_forces, [False])
        self.assertEqual(complete_calls, [])
        self.assertEqual(failure_calls, [])

    def test_execute_tool_plan_item_service_actions_redacts_raw_diagnostics(
        self,
    ) -> None:
        trace_steps = [{"id": "existing-1", "seq": 2, "content": "Existing"}]
        tool_observations: list[str] = []
        persist_forces: list[bool] = []
        complete_calls: list[dict[str, object]] = []
        failure_calls: list[dict[str, object]] = []
        service_actions = [
            {
                "kind": "trace_write",
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
            {
                "kind": "continue",
                "tool_observations": [
                    "provider_search: unsupported tool execution kind token=hidden",
                ],
                "seq_increment": 1,
            },
            {
                "kind": "record_failure_event",
                "kwargs": {
                    "event_type": "task_failed",
                    "code": "tool_execution_error",
                    "message": "provider_search failed with secret=hidden",
                    "detail": {
                        "reason": (
                            "provider_search: http_json execution headers.x-api-key must be safe"
                        ),
                    },
                },
            },
            {
                "kind": "emit_state",
                "event": "state",
                "data": {
                    "task_id": "task-1",
                    "phase": "error",
                    "detail": (
                        "provider_search: http_json execution json_body.client_secret must be safe"
                    ),
                },
            },
        ]

        items = list(
            execute_tool_plan_item_service_actions(
                service_actions=service_actions,
                trace_steps=trace_steps,
                tool_observations=tool_observations,
                seq_cursor=3,
                persist_trace_fn=lambda *, force: persist_forces.append(bool(force)),
                complete_task_fn=lambda **kwargs: complete_calls.append(kwargs),
                record_failure_event_fn=lambda **kwargs: failure_calls.append(kwargs),
            )
        )

        serialized = json.dumps(
            {
                "items": items,
                "trace_steps": trace_steps,
                "tool_observations": tool_observations,
                "failure_calls": failure_calls,
            },
            default=str,
        )
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("secret=hidden", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)
        self.assertEqual(persist_forces, [True])
        self.assertEqual(complete_calls, [])
