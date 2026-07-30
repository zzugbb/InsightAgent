from __future__ import annotations

from .context import *


class TaskSessionExportMarkdownMixin:
    def test_build_task_export_markdown_includes_registry_governance_summary(self) -> None:
        task = {
            "id": "task-export-governance-md",
            "session_id": "session-export-governance-md",
            "prompt": "export markdown governance summary",
            "status": "completed",
            "created_at": "2026-06-05T10:00:00",
            "updated_at": "2026-06-05T10:05:00",
            "trace_json": None,
            "usage_json": None,
            "governance": {
                "profile": "retrieval_only",
                "provider_source": "default",
                "allowed_tool_names": ["task_retrieve"],
                "allowed_tool_labels": ["Knowledge Retrieval"],
            },
        }
        original_trace_steps_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_steps_from_task",
        )
        original_get_task_messages = task_routes_module.get_task_messages
        try:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda _task: [
                task_routes_module.TraceStep(  # type: ignore[attr-defined]
                    id="trace-plan-2",
                    type="thought",
                    content="Planner constrained the tool set.",
                    seq=1,
                    meta={
                        "tool_registry_profile": "retrieval_only",
                        "tool_registry_provider_source": "default",
                        "allowed_tool_names": ["task_retrieve"],
                        "allowed_tool_labels": ["Knowledge Retrieval"],
                    },
                )
                ]
            )
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []

            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-governance",
            )
            markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
                payload,
            )
        finally:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = original_trace_steps_loader  # type: ignore[attr-defined]
            task_routes_module.get_task_messages = original_get_task_messages

        self.assertIn("- Tool Registry Profile: retrieval_only", markdown)
        self.assertIn("- Tool Registry Source: default", markdown)
        self.assertIn("- Allowed Tools: Knowledge Retrieval", markdown)

    def test_build_task_export_payload_does_not_fallback_governance_when_service_missing(
        self,
    ) -> None:
        task = {
            "id": "task-export-governance-columns",
            "session_id": "session-export-governance-columns",
            "prompt": "export governance summary from persisted columns",
            "status": "completed",
            "created_at": "2026-06-11T10:00:00",
            "updated_at": "2026-06-11T10:05:00",
            "tool_registry_profile": "planning_only",
            "tool_registry_provider_source": "planning_suite",
            "allowed_tool_names_json": json.dumps(["task_plan"]),
            "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
            "trace_json": None,
            "usage_json": None,
        }
        original_trace_steps_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_steps_from_task",
        )
        original_get_task_messages = task_routes_module.get_task_messages
        try:
            self.assertFalse(
                hasattr(
                    task_routes_module.chat_persistence_service,
                    "_extract_task_governance_from_task_with_parsed_trace_steps",
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda _task: []
            )
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []

            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-governance-columns",
            )
        finally:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = original_trace_steps_loader  # type: ignore[attr-defined]
            task_routes_module.get_task_messages = original_get_task_messages

        self.assertIsNone(payload.trace.governance)

    def test_task_route_module_does_not_expose_dead_task_export_governance_dict_builder(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_build_task_export_governance_from_dict"))

    def test_build_task_export_markdown_includes_persisted_governance_summary(self) -> None:
        task = {
            "id": "task-export-governance-columns-md",
            "session_id": "session-export-governance-columns-md",
            "prompt": "export markdown governance summary from persisted columns",
            "status": "completed",
            "created_at": "2026-06-11T10:00:00",
            "updated_at": "2026-06-11T10:05:00",
            "governance": {
                "profile": "retrieval_only",
                "provider_source": "default",
                "allowed_tool_names": ["task_retrieve"],
                "allowed_tool_labels": ["Knowledge Retrieval"],
            },
            "tool_registry_profile": "retrieval_only",
            "tool_registry_provider_source": "default",
            "allowed_tool_names_json": json.dumps(["task_retrieve"]),
            "allowed_tool_labels_json": json.dumps(["Knowledge Retrieval"]),
            "trace_json": None,
            "usage_json": None,
        }
        original_trace_steps_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_steps_from_task",
        )
        original_get_task_messages = task_routes_module.get_task_messages
        try:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda _task: []
            )
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []

            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-governance-columns",
            )
            markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
                payload,
            )
        finally:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = original_trace_steps_loader  # type: ignore[attr-defined]
            task_routes_module.get_task_messages = original_get_task_messages

        self.assertIn("- Tool Registry Profile: retrieval_only", markdown)
        self.assertIn("- Tool Registry Source: default", markdown)
        self.assertIn("- Allowed Tools: Knowledge Retrieval", markdown)

    def test_build_task_export_markdown_prefers_inferred_result_summary_from_preview_only_action_steps(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-06-27T12:00:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-preview-md",
                session_id="session-export-preview-md",
                prompt="show me the export markdown preview",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-06-27T11:59:00",
                updated_at="2026-06-27T12:00:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=1,
                rag_hit_count=0,
                rag_knowledge_base_ids=[],
                rag_chunks=[],
                steps=[
                    task_routes_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-preview-tool",
                        seq=3,
                        type="action",
                        content="Tool done: Hot Retrieval",
                        meta={
                            "tool": {
                                "name": "task_retrieve_hot",
                                "label": "Hot Retrieval",
                                "status": "done",
                                "output_preview": {
                                    "tool_kind": "hot_knowledge_retrieval",
                                    "hit_count": 2,
                                    "knowledge_base_id": "demo-kb",
                                },
                            }
                        },
                    )
                ],
            ),
        )

        markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn("Retrieved 2 hits from knowledge base demo-kb.", markdown)
        self.assertNotIn("Tool done: Hot Retrieval", markdown)
        self.assertIn('Preview: {"tool_kind":"hot_knowledge_retrieval","hit_count":2,"knowledge_base_id":"demo-kb"}', markdown)
        self.assertIn('"hit_count":2', markdown)
        self.assertIn('"knowledge_base_id":"demo-kb"', markdown)

    def test_build_task_export_markdown_reuses_shared_trace_display_content_helper(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-06-27T12:10:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-display-helper-md",
                session_id="session-export-display-helper-md",
                prompt="reuse trace display helper",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-06-27T12:05:00",
                updated_at="2026-06-27T12:10:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=1,
                rag_hit_count=0,
                rag_knowledge_base_ids=[],
                rag_chunks=[],
                steps=[
                    task_routes_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-display-helper",
                        seq=1,
                        type="action",
                        content="Tool done: Helper Check",
                        meta={},
                    )
                ],
            ),
        )
        original_display_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_trace_step_display_content",
            None,
        )
        try:
            task_routes_module.chat_persistence_service.get_trace_step_display_content = (  # type: ignore[attr-defined]
                lambda _step: "shared display body"
            )

            markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
                payload,
            )
        finally:
            if original_display_helper is None:
                delattr(
                    task_routes_module.chat_persistence_service,
                    "get_trace_step_display_content",
                )
            else:
                task_routes_module.chat_persistence_service.get_trace_step_display_content = original_display_helper  # type: ignore[attr-defined]

        self.assertIn("shared display body", markdown)

    def test_build_task_export_markdown_uses_productized_tool_title_for_real_tool_steps(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-06-29T12:10:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-title-helper-md",
                session_id="session-export-title-helper-md",
                prompt="reuse trace title helper",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-06-29T12:05:00",
                updated_at="2026-06-29T12:10:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=1,
                rag_hit_count=0,
                rag_knowledge_base_ids=[],
                rag_chunks=[],
                steps=[
                    task_routes_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-provider-search",
                        seq=3,
                        type="action",
                        content="Tool done: Provider Search",
                        meta={
                            "tool": {
                                "name": "provider_search",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "semantic_kind": "provider_search",
                                "semantic_family": "knowledge_retrieval",
                                "status": "done",
                                "output_preview": {
                                    "hit_count": 2,
                                    "knowledge_base_id": "demo-kb",
                                },
                            }
                        },
                    )
                ],
            ),
        )

        markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "### 1. seq=3 · Provider Search [provider_search · knowledge_retrieval] · step-provider-search",
            markdown,
        )

    def test_build_task_export_markdown_humanizes_unlabeled_real_tool_title_for_trace_steps(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-06-30T12:10:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-humanized-title-md",
                session_id="session-export-humanized-title-md",
                prompt="humanize unlabeled tool title",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-06-30T12:05:00",
                updated_at="2026-06-30T12:10:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=1,
                rag_hit_count=0,
                rag_knowledge_base_ids=[],
                rag_chunks=[],
                steps=[
                    task_routes_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-provider-search-unlabeled",
                        seq=4,
                        type="action",
                        content="Tool done: provider_search",
                        meta={
                            "tool": {
                                "name": "provider_search",
                                "kind": "provider_retrieval",
                                "semantic_kind": "provider_search",
                                "semantic_family": "knowledge_retrieval",
                                "status": "done",
                            }
                        },
                    )
                ],
            ),
        )

        markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "### 1. seq=4 · Provider Search [provider_search · knowledge_retrieval] · step-provider-search-unlabeled",
            markdown,
        )

    def test_build_task_export_markdown_does_not_leak_raw_output_when_preview_exists(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-06-27T12:20:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-sanitized-meta-md",
                session_id="session-export-sanitized-meta-md",
                prompt="sanitize export markdown meta",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-06-27T12:15:00",
                updated_at="2026-06-27T12:20:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=1,
                rag_hit_count=0,
                rag_knowledge_base_ids=[],
                rag_chunks=[],
                steps=[
                    task_routes_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-sanitized-meta",
                        seq=2,
                        type="action",
                        content="Tool done: Hot Retrieval",
                        meta={
                            "tool": {
                                "name": "task_retrieve_hot",
                                "label": "Hot Retrieval",
                                "status": "done",
                                "output": {
                                    "tool_kind": "hot_knowledge_retrieval",
                                    "hit_count": 2,
                                    "chunks": ["alpha", "beta"],
                                    "raw_documents": [{"id": "doc-1"}],
                                },
                                "output_preview": {
                                    "tool_kind": "hot_knowledge_retrieval",
                                    "hit_count": 2,
                                    "knowledge_base_id": "demo-kb",
                                },
                            }
                        },
                    )
                ],
            ),
        )

        markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn('"output_preview"', markdown)
        self.assertNotIn("raw_documents", markdown)
        self.assertNotIn('"chunks"', markdown)

    def test_build_task_export_markdown_preserves_safe_tool_output_when_effective_result_output_keys_present(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-06-30T16:20:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-output-policy-md",
                session_id="session-export-output-policy-md",
                prompt="preserve output policy fields in markdown export",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-06-30T16:15:00",
                updated_at="2026-06-30T16:20:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=1,
                rag_hit_count=0,
                rag_knowledge_base_ids=[],
                rag_chunks=[],
                steps=[
                    task_routes_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-output-policy-meta",
                        seq=5,
                        type="action",
                        content="Tool done: Provider Search",
                        meta={
                            "tool": {
                                "name": "provider_search",
                                "label": "Provider Search",
                                "status": "done",
                                "effective_result_output_keys": [
                                    "documents_total",
                                    "request_id",
                                ],
                                "output_preview": {
                                    "documents_total": 2,
                                },
                                "output": {
                                    "documents_total": 2,
                                    "request_id": "req-1",
                                },
                            }
                        },
                    )
                ],
            ),
        )

        markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn('Preview: {"documents_total":2}', markdown)
        self.assertIn('Output: {"documents_total":2,"request_id":"req-1"}', markdown)
        self.assertIn('"request_id": "req-1"', markdown)

    def test_build_task_export_markdown_appends_tuple_tool_output_preview_for_action_steps(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-06-30T16:20:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-output-preview-tuple",
                session_id="session-export-output-preview-tuple",
                prompt="export output preview tuple",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-06-30T16:15:00",
                updated_at="2026-06-30T16:20:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=1,
                rag_hit_count=0,
                rag_knowledge_base_ids=[],
                rag_chunks=[],
                steps=[
                    task_routes_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-output-preview-tuple",
                        seq=6,
                        type="action",
                        content="Tool done: Provider Search",
                        meta={
                            "tool": {
                                "name": "provider_search",
                                "label": "Provider Search",
                                "status": "done",
                                "output_preview": (
                                    "alpha",
                                    "beta",
                                ),
                            }
                        },
                    )
                ],
            ),
        )

        markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn('Preview: ["alpha","beta"]', markdown)

    def test_build_task_export_markdown_does_not_label_external_rag_chunks_as_default_kb_when_missing_knowledge_base_id(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-07-01T10:20:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-rag-external",
                session_id="session-export-rag-external",
                prompt="export external provider snippets",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-07-01T10:15:00",
                updated_at="2026-07-01T10:20:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=0,
                rag_hit_count=1,
                rag_knowledge_base_ids=[],
                rag_chunks=[
                    task_routes_module.TaskExportRagChunk(  # type: ignore[attr-defined]
                        step_id="rag-1",
                        knowledge_base_id=None,
                        content="external provider snippet",
                    )
                ],
                steps=[],
            ),
        )

        markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn("### 1. step=rag-1", markdown)
        self.assertNotIn("kb=default", markdown)
        self.assertNotIn("selected knowledge base", markdown)

    def test_build_task_export_markdown_redacts_http_json_message_content(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-07-22T12:00:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-markdown-message-redact",
                session_id="session-export-markdown-message-redact",
                prompt="export sensitive message",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-07-22T11:55:00",
                updated_at="2026-07-22T12:00:00",
            ),
            usage=None,
            messages=[
                task_routes_module.TaskExportMessage(  # type: ignore[attr-defined]
                    id="message-task-markdown-http-json",
                    role="assistant",
                    content=(
                        "Provider Search [provider_search via http_json] "
                        "failed response_path=$.data.access_token "
                        "callback https://provider.example/cb?"
                        "access_token=secret-token#client_secret=hidden "
                        "Bearer secret-token"
                    ),
                    created_at="2026-07-22T11:59:00",
                )
            ],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=0,
                rag_hit_count=0,
                rag_knowledge_base_ids=[],
                rag_chunks=[],
                steps=[],
            ),
        )

        markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn("[redacted]", markdown)
        self.assertIn("response_path=$.data.[redacted]", markdown)
        self.assertNotIn("response_path=$.data.access_token", markdown)
        self.assertNotIn("access_token", markdown)
        self.assertNotIn("client_secret", markdown)
        self.assertNotIn("Bearer", markdown)
        self.assertNotIn("secret-token", markdown)

    def test_build_task_export_markdown_redacts_http_json_rag_chunk_content(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-07-22T12:10:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-markdown-rag-redact",
                session_id="session-export-markdown-rag-redact",
                prompt="export sensitive rag chunk",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-07-22T12:05:00",
                updated_at="2026-07-22T12:10:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=0,
                rag_hit_count=1,
                rag_knowledge_base_ids=["kb-http-json"],
                rag_chunks=[
                    task_routes_module.TaskExportRagChunk(  # type: ignore[attr-defined]
                        step_id="step-markdown-rag-http-json",
                        knowledge_base_id="kb-http-json",
                        content=(
                            "Matched snippet query_params.access_token "
                            "response_path=$.data.access_token "
                            "Bearer secret-token"
                        ),
                    )
                ],
                steps=[],
            ),
        )

        markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn("[redacted]", markdown)
        self.assertIn("response_path=$.data.[redacted]", markdown)
        self.assertNotIn("query_params.access_token", markdown)
        self.assertNotIn("response_path=$.data.access_token", markdown)
        self.assertNotIn("access_token", markdown)
        self.assertNotIn("Bearer", markdown)
        self.assertNotIn("secret-token", markdown)

    def test_get_trace_step_markdown_meta_preserves_safe_tool_output_when_effective_result_output_keys_present(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-safe-output-meta",
            seq=6,
            type="action",
            content="Tool done: Provider Search",
            meta={
                "tool": {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "effective_result_output_keys": [
                        "documents_total",
                        "request_id",
                    ],
                    "output_preview": {
                        "documents_total": 2,
                    },
                    "output": {
                        "documents_total": 2,
                        "request_id": "req-1",
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        self.assertEqual(
            markdown_meta["tool"]["output"],
            {  # type: ignore[index]
                "documents_total": 2,
                "request_id": "req-1",
            },
        )

    def test_get_trace_step_markdown_meta_filters_safe_tool_output_to_effective_result_output_keys_subset(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-safe-output-meta-filtered",
            seq=7,
            type="action",
            content="Tool done: Provider Search",
            meta={
                "tool": {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "effective_result_output_keys": [
                        "documents_total",
                        "request_id",
                    ],
                    "output_preview": {
                        "documents_total": 2,
                    },
                    "output": {
                        "documents_total": 2,
                        "request_id": "req-1",
                        "raw_documents": [{"id": "doc-1"}],
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        self.assertEqual(
            markdown_meta["tool"]["output"],
            {  # type: ignore[index]
                "documents_total": 2,
                "request_id": "req-1",
            },
        )
        self.assertNotIn("raw_documents", markdown_meta["tool"]["output"])  # type: ignore[index]

    def test_get_trace_step_markdown_meta_accepts_tuple_effective_result_output_keys(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-safe-output-meta-tuple",
            seq=8,
            type="action",
            content="Tool done: Provider Search",
            meta={
                "tool": {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "effective_result_output_keys": (
                        "documents_total",
                        "request_id",
                    ),
                    "output_preview": {
                        "documents_total": 2,
                    },
                    "output": {
                        "documents_total": 2,
                        "request_id": "req-1",
                        "raw_documents": [{"id": "doc-1"}],
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        self.assertEqual(
            markdown_meta["tool"]["output"],
            {  # type: ignore[index]
                "documents_total": 2,
                "request_id": "req-1",
            },
        )
        self.assertNotIn("raw_documents", markdown_meta["tool"]["output"])  # type: ignore[index]

    def test_get_trace_step_markdown_meta_reuses_preview_as_output_without_safe_output(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-preview-output-meta",
            seq=9,
            type="action",
            content="Tool done: Provider Search",
            meta={
                "tool": {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "output_preview": {
                        "documents_total": 2,
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        self.assertEqual(
            markdown_meta["tool"]["output"],  # type: ignore[index]
            {
                "documents_total": 2,
            },
        )

    def test_get_trace_step_markdown_meta_normalizes_http_json_aliases_for_safe_output(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-http-json-safe-output-alias-meta",
            seq=10,
            type="action",
            content="Tool done: Provider Search",
            meta={
                "tool": {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "execution_kind": "http_json",
                    "effective_result_output_keys": [
                        "documents_total",
                        "request_id",
                    ],
                    "output": {
                        "documents_total": "unknown",
                        "items": [
                            {"id": "doc-1"},
                            {"id": "doc-2"},
                        ],
                        "request_id": "req-meta-items-1",
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        self.assertEqual(
            markdown_meta["tool"]["output"],  # type: ignore[index]
            {
                "documents_total": 2,
                "request_id": "req-meta-items-1",
            },
        )

    def test_get_trace_step_markdown_meta_normalizes_http_json_aliases_for_preview_fallback(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-http-json-preview-alias-meta",
            seq=11,
            type="action",
            content="Tool done: Provider Search",
            meta={
                "tool": {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "execution_kind": "http_json",
                    "output_preview": {
                        "hit_count": "unknown",
                        "matches": [
                            {"id": "vec-1"},
                            {"id": "vec-2"},
                        ],
                        "knowledge_base_id": "provider-kb",
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        self.assertEqual(
            markdown_meta["tool"]["output"],  # type: ignore[index]
            {
                "hit_count": 2,
                "matches": [
                    {"id": "vec-1"},
                    {"id": "vec-2"},
                ],
                "knowledge_base_id": "provider-kb",
            },
        )

    def test_get_trace_step_display_content_normalizes_http_json_aliases_for_preview_and_output(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-http-json-display-content-alias-meta",
            seq=12,
            type="action",
            content="Tool done: Provider Search",
            meta={
                "tool": {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "execution_kind": "http_json",
                    "effective_result_output_keys": [
                        "hit_count",
                        "request_id",
                    ],
                    "output_preview": {
                        "documents_total": "unknown",
                        "items": [
                            {"id": "doc-1"},
                            {"id": "doc-2"},
                        ],
                        "secret": "hidden",
                    },
                    "output": {
                        "hit_count": "unknown",
                        "matches": [
                            {"id": "vec-1"},
                            {"id": "vec-2"},
                        ],
                        "request_id": "req-display-matches-1",
                        "secret": "hidden",
                    },
                }
            },
        )

        content = chat_persistence_module.get_trace_step_display_content(  # type: ignore[attr-defined]
            step,
        )

        self.assertIn(
            "Retrieved 2 hits (request id req-display-matches-1).",
            content,
        )
        self.assertIn('Preview: {"documents_total":2}', content)
        self.assertIn(
            'Output: {"hit_count":2,"request_id":"req-display-matches-1"}',
            content,
        )
        self.assertNotIn('"secret"', content)
        self.assertNotIn('"documents_total":"unknown"', content)
        self.assertNotIn('"hit_count":"unknown"', content)

    def test_get_trace_step_display_content_normalizes_http_json_records_aliases_for_custom_real_search_tool(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-http-json-custom-search-records-alias-meta",
            seq=13,
            type="action",
            content="Tool done: Custom Search",
            meta={
                "tool": {
                    "name": "custom_search",
                    "label": "Custom Search",
                    "status": "done",
                    "execution_kind": "http_json",
                    "semantic_family": "knowledge_retrieval",
                    "effective_result_preview_keys": [
                        "documents_total",
                    ],
                    "effective_result_output_keys": [
                        "documents_total",
                        "request_id",
                    ],
                    "output_preview": {
                        "totalRecords": "6",
                        "access_token": "secret-token",
                    },
                    "output": {
                        "totalRecords": "6",
                        "request_id": "req-custom-records-1",
                        "access_token": "secret-token",
                    },
                }
            },
        )

        content = chat_persistence_module.get_trace_step_display_content(  # type: ignore[attr-defined]
            step,
        )

        self.assertIn(
            "Retrieved 6 documents (request id req-custom-records-1).",
            content,
        )
        self.assertIn('Preview: {"documents_total":6}', content)
        self.assertIn(
            'Output: {"documents_total":6,"request_id":"req-custom-records-1"}',
            content,
        )
        self.assertNotIn("totalRecords", content)
        self.assertNotIn("access_token", content)
        self.assertNotIn("secret-token", content)

    def test_get_trace_step_display_content_redacts_raw_http_json_preview_without_projection_keys(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-http-json-display-content-safe-preview-meta",
            seq=13,
            type="action",
            content="Tool done: Provider Status",
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "status": "done",
                    "execution_kind": "http_json",
                    "output_preview": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                        "nested": {"api_key": "hidden"},
                    },
                }
            },
        )

        content = chat_persistence_module.get_trace_step_display_content(  # type: ignore[attr-defined]
            step,
        )

        self.assertIn("Preview:", content)
        self.assertIn('"status":"ready"', content)
        self.assertIn('"message":"gateway token=[redacted]"', content)
        self.assertIn('"access_token":"[redacted]"', content)
        self.assertIn('"nested":{"api_key":"[redacted]"}', content)
        self.assertNotIn("Bearer", content)
        self.assertNotIn("secret-token", content)
        self.assertNotIn("hidden", content)

    def test_get_trace_step_markdown_meta_filters_json_string_safe_output(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-json-string-safe-output-meta",
            seq=10,
            type="action",
            content="Tool done: Hosted Math",
            meta={
                "tool": {
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": '{"result":7,"request_id":"req-calc-1","kind":"provider_calc","secret":"hidden"}',
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        self.assertEqual(
            markdown_meta["tool"]["output"],  # type: ignore[index]
            {
                "result": 7,
                "request_id": "req-calc-1",
            },
        )
        self.assertNotIn("secret", markdown_meta["tool"]["output"])  # type: ignore[index]

    def test_get_trace_step_markdown_meta_redacts_raw_http_json_preview_without_projection_keys(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-http-json-markdown-meta-safe-preview",
            seq=10,
            type="action",
            content="Tool done: Provider Status",
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "status": "done",
                    "execution_kind": "http_json",
                    "output_preview": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        output = markdown_meta["tool"]["output"]  # type: ignore[index]
        self.assertEqual(output["status"], "ready")  # type: ignore[index]
        self.assertEqual(output["message"], "gateway token=[redacted]")  # type: ignore[index]
        self.assertEqual(output["access_token"], "[redacted]")  # type: ignore[index]
        self.assertNotIn("request_id", output)  # type: ignore[operator]
        self.assertNotIn("hidden", json.dumps(output))
        self.assertNotIn("Bearer", json.dumps(output))

    def test_get_trace_step_markdown_meta_redacts_malformed_http_json_preview_string(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-http-json-markdown-meta-malformed-preview",
            seq=11,
            type="action",
            content="Tool done: Provider Status",
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "status": "done",
                    "execution_kind": "http_json",
                    "output_preview": (
                        "status=ready token=hidden "
                        "query_params.access_token Bearer secret-token"
                    ),
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )
        content = chat_persistence_module.get_trace_step_display_content(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        self.assertEqual(
            markdown_meta["tool"]["output"],  # type: ignore[index]
            "status=ready [redacted] [redacted] [redacted]",
        )
        self.assertIn(
            'Preview: status=ready [redacted] [redacted] [redacted]',
            content,
        )
        serialized = json.dumps(markdown_meta) + content
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_redacts_provider_tool_input_without_execution_kind(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-provider-input-half-migrated",
            seq=12,
            type="action",
            content="Tool done: Hosted Math",
            meta={
                "tool": {
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "input": {
                        "expression": "1+1",
                        "json_body": {
                            "client_secret": "top-secret",
                        },
                        "query_params": {
                            "access_token": "secret-token",
                        },
                    },
                    "output": {
                        "result": 2,
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("top-secret", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_treats_wrapped_execution_kind_as_http_json(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-http-json-wrapped-kind-redacted",
            seq=13,
            type="action",
            content="Tool done: Acme Lookup",
            meta={
                "tool": {
                    "name": "acme_lookup",
                    "label": "Acme Lookup",
                    "status": "done",
                    "execution_kind": UserString("http_json"),
                    "effective_result_preview_keys": UserList([UserString("status")]),
                    "effective_result_output_keys": UserList([UserString("status")]),
                    "input": {
                        "query": "demo",
                        "access_token": "secret-token",
                    },
                    "output_preview": {
                        "status": "ready",
                        "access_token": "secret-token",
                    },
                    "output": {
                        "status": "ready",
                        "access_token": "secret-token",
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        self.assertEqual(
            markdown_meta["tool"]["input"],  # type: ignore[index]
            {
                "query": "demo",
                "access_token": "[redacted]",
            },
        )
        self.assertEqual(markdown_meta["tool"]["output_preview"], {"status": "ready"})  # type: ignore[index]
        self.assertEqual(markdown_meta["tool"]["output"], {"status": "ready"})  # type: ignore[index]
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_display_content_redacts_provider_content_without_execution_kind(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-provider-content-half-migrated",
            seq=13,
            type="action",
            content=(
                "Upstream diagnostic: query_params.access_token "
                "json_body.client_secret Bearer secret-token"
            ),
            meta={
                "tool": {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "error",
                }
            },
        )

        content = chat_persistence_module.get_trace_step_display_content(  # type: ignore[attr-defined]
            step,
        )

        self.assertIn("[redacted]", content)
        self.assertNotIn("access_token", content)
        self.assertNotIn("client_secret", content)
        self.assertNotIn("Bearer", content)
        self.assertNotIn("secret-token", content)

    def test_get_trace_step_display_content_redacts_provider_content_urls_without_execution_kind(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-provider-content-url-half-migrated",
            seq=13,
            type="action",
            content=(
                "Upstream callback https://provider.example/cb?"
                "access_token=secret-token&state=ok#client_secret=hidden "
                "path https://provider.example/api_key/secret-value/cb"
            ),
            meta={
                "tool": {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "error",
                }
            },
        )

        content = chat_persistence_module.get_trace_step_display_content(  # type: ignore[attr-defined]
            step,
        )

        self.assertIn("[redacted]", content)
        self.assertIn("Upstream callback", content)
        self.assertNotIn("access_token", content)
        self.assertNotIn("client_secret", content)
        self.assertNotIn("secret-token", content)
        self.assertNotIn("api_key", content)
        self.assertNotIn("secret-value", content)

    def test_get_trace_step_display_content_redacts_http_json_label_only_url(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-display-http-json-label-only-url",
            seq=14,
            type="action",
            content=(
                "Calculator [calculator via http_json]: callback "
                "https://provider.example/cb?"
                "access_token=secret-token&state=ok"
                "#client_secret=hidden"
            ),
            meta={
                "label": "Calculator [calculator via http_json]",
            },
        )

        content = chat_persistence_module.get_trace_step_display_content(  # type: ignore[attr-defined]
            step,
        )

        self.assertIn("callback", content)
        self.assertIn("[redacted]", content)
        self.assertNotIn("access_token", content)
        self.assertNotIn("client_secret", content)
        self.assertNotIn("secret-token", content)

    def test_get_trace_step_display_content_redacts_provider_result_summary(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-provider-result-summary-leak",
            seq=14,
            type="action",
            content="Tool done: Provider Status",
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "status": "done",
                    "result_summary": (
                        "gateway query_params.access_token Bearer secret-token"
                    ),
                }
            },
        )

        content = chat_persistence_module.get_trace_step_display_content(  # type: ignore[attr-defined]
            step,
        )

        self.assertIn("[redacted]", content)
        self.assertNotIn("access_token", content)
        self.assertNotIn("Bearer", content)
        self.assertNotIn("secret-token", content)

    def test_get_trace_step_markdown_meta_redacts_provider_result_summary(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-provider-result-summary-meta",
            seq=15,
            type="action",
            content="Tool done: Provider Status",
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "status": "done",
                    "result_summary": (
                        "gateway query_params.access_token Bearer secret-token"
                    ),
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_redacts_provider_nested_rag_chunks(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-provider-nested-rag",
            seq=16,
            type="action",
            content="Tool done: Provider Search",
            meta={
                "tool": {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                },
                "rag": {
                    "knowledge_base_id": "kb-provider",
                    "chunks": [
                        "Matched snippet query_params.access_token Bearer secret-token"
                    ],
                },
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_redacts_wrapped_rag_chunks(
        self,
    ) -> None:
        class WrappedMeta:
            def model_dump(self, *, exclude_none: bool = True) -> dict[str, object]:
                del exclude_none
                return {
                    "rag": UserDict(
                        {
                            UserString("chunks"): UserList(
                                [
                                    UserString(
                                        "chunk query_params.access_token Bearer secret-token"
                                    ),
                                    UserDict(
                                        {
                                            UserString("content"): UserString(
                                                "nested json_body.client_secret hidden"
                                            ),
                                            UserString("score"): 0.9,
                                        }
                                    ),
                                ]
                            ),
                            UserString("knowledge_base_id"): UserString("provider-kb"),
                        }
                    )
                }

        step = SimpleNamespace(
            id="step-provider-rag-chunks-wrapped-meta",
            seq=16,
            type="tool_result",
            content="Retrieved chunks",
            meta=WrappedMeta(),
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(step)

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        self.assertEqual(
            markdown_meta["rag"]["chunks"],  # type: ignore[index]
            [
                "chunk [redacted] [redacted]",
                {"content": "nested [redacted] hidden", "score": 0.9},
            ],
        )
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_redacts_tool_registry_diagnostics_values(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-markdown-meta-tool-registry-diagnostics",
            seq=17,
            type="thought",
            content="Tool registry diagnostics: source=file_source invalid=1",
            meta={
                "tool_registry": {
                    "provider_source": "file_source",
                    "has_diagnostics": True,
                    "invalid_total": 1,
                    "entries": [
                        {
                            "kind": "invalid",
                            "target": "tool_executions",
                            "count": 1,
                            "values": [
                                (
                                    "provider_search: http_json execution "
                                    "query_params.access_token Bearer secret-token"
                                )
                            ],
                        }
                    ],
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("query_params.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_redacts_diagnostics_runtime_values(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-markdown-meta-diagnostics-runtime",
            seq=18,
            type="thought",
            content="Tool registry diagnostics: source=file_source invalid=1",
            meta={
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "invalid_total": 1,
                        "entries": [
                            {
                                "kind": "invalid",
                                "target": "tool_executions",
                                "count": 1,
                                "values": [
                                    (
                                        "provider_search: http_json execution "
                                        "query_params.access_token Bearer secret-token"
                                    )
                                ],
                            }
                        ],
                    },
                    "trace_step": None,
                    "trace_event": None,
                    "audit_detail": None,
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("query_params.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_redacts_runtime_artifacts_diagnostics_values(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-markdown-meta-runtime-artifacts-diagnostics",
            seq=19,
            type="thought",
            content="Tool registry diagnostics: source=file_source invalid=1",
            meta={
                "runtime_artifacts": {
                    "provider_source_name": "file_source",
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "invalid_total": 1,
                            "entries": [
                                {
                                    "kind": "invalid",
                                    "target": "tool_executions",
                                    "count": 1,
                                    "values": [
                                        (
                                            "provider_search: http_json execution "
                                            "query_params.access_token Bearer secret-token"
                                        )
                                    ],
                                }
                            ],
                        },
                        "trace_step": None,
                        "trace_event": None,
                        "audit_detail": None,
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("query_params.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_redacts_service_execution_diagnostics_values(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-markdown-meta-service-execution-diagnostics",
            seq=20,
            type="thought",
            content="Tool registry diagnostics: source=file_source invalid=1",
            meta={
                "service_execution": {
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "provider_source_name": "file_source",
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "invalid_total": 1,
                                "entries": [
                                    {
                                        "kind": "invalid",
                                        "target": "tool_executions",
                                        "count": 1,
                                        "values": [
                                            (
                                                "provider_search: http_json execution "
                                                "query_params.access_token Bearer secret-token"
                                            )
                                        ],
                                    }
                                ],
                            },
                            "trace_step": None,
                            "trace_event": None,
                            "audit_detail": None,
                        },
                    },
                    "service_actions": [],
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("query_params.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_redacts_preflight_result_diagnostics_values(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-markdown-meta-preflight-result-diagnostics",
            seq=21,
            type="thought",
            content="Tool registry preflight diagnostics: source=file_source invalid=1",
            meta={
                "preflight_result": {
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "provider_source_name": "file_source",
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "invalid_total": 1,
                                "entries": [
                                    {
                                        "kind": "invalid",
                                        "target": "tool_executions",
                                        "count": 1,
                                        "values": [
                                            (
                                                "provider_search: http_json execution "
                                                "query_params.access_token Bearer secret-token"
                                            )
                                        ],
                                    }
                                ],
                            },
                            "trace_step": None,
                            "trace_event": None,
                            "audit_detail": None,
                        },
                    },
                    "service_execution": {
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {},
                        "service_actions": [],
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("query_params.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_redacts_execution_result_diagnostics_values(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-markdown-meta-execution-result-diagnostics",
            seq=22,
            type="thought",
            content="Tool registry execution result diagnostics: source=file_source invalid=1",
            meta={
                "execution_result": {
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "provider_source_name": "file_source",
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "invalid_total": 1,
                                "entries": [
                                    {
                                        "kind": "invalid",
                                        "target": "tool_executions",
                                        "count": 1,
                                        "values": [
                                            (
                                                "provider_search: http_json execution "
                                                "query_params.access_token Bearer secret-token"
                                            )
                                        ],
                                    }
                                ],
                            },
                            "trace_step": None,
                            "trace_event": None,
                            "audit_detail": None,
                        },
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 1,
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("query_params.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_redacts_audit_event_diagnostics_values(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-markdown-meta-audit-event-diagnostics",
            seq=23,
            type="thought",
            content="Tool registry audit diagnostics: source=file_source invalid=1",
            meta={
                "audit_event": {
                    "event_type": "tool_registry_diagnostics",
                    "event_detail": {
                        "provider_source_name": "file_source",
                        "summary": {
                            "has_diagnostics": True,
                            "invalid_total": 1,
                            "entries": [
                                {
                                    "kind": "invalid",
                                    "target": "tool_executions",
                                    "count": 1,
                                    "values": [
                                        (
                                            "provider_search: http_json execution "
                                            "query_params.access_token Bearer secret-token"
                                        )
                                    ],
                                }
                            ],
                        },
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("query_params.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_redacts_provider_output_preview_without_execution_kind(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-provider-preview-half-migrated",
            seq=17,
            type="action",
            content="Tool done: Provider Status",
            meta={
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "status": "done",
                    "output_preview": {
                        "message": "gateway token=hidden",
                        "access_token": "hidden",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        assert markdown_meta is not None
        serialized = json.dumps(markdown_meta, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"access_token": "hidden"', serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_trace_step_markdown_meta_filters_quoted_json_string_safe_output(
        self,
    ) -> None:
        step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="step-quoted-json-string-safe-output-meta",
            seq=10,
            type="action",
            content="Tool done: Hosted Math",
            meta={
                "tool": {
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": json.dumps(
                        '{"result":7,"request_id":"req-calc-1","kind":"provider_calc","secret":"hidden"}'
                    ),
                }
            },
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(  # type: ignore[attr-defined]
            step,
        )

        self.assertIsNotNone(markdown_meta)
        self.assertEqual(
            markdown_meta["tool"]["output"],  # type: ignore[index]
            {
                "result": 7,
                "request_id": "req-calc-1",
            },
        )
        self.assertNotIn("secret", markdown_meta["tool"]["output"])  # type: ignore[index]

    def test_build_task_export_markdown_reuses_shared_markdown_meta_helper(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-06-27T12:25:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-meta-helper-md",
                session_id="session-export-meta-helper-md",
                prompt="reuse markdown meta helper",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-06-27T12:20:00",
                updated_at="2026-06-27T12:25:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=1,
                rag_hit_count=0,
                rag_knowledge_base_ids=[],
                rag_chunks=[],
                steps=[
                    task_routes_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-meta-helper",
                        seq=1,
                        type="action",
                        content="Tool done: Helper Check",
                        meta={"tool": {"name": "helper_tool", "status": "done"}},
                    )
                ],
            ),
        )
        original_meta_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_trace_step_markdown_meta",
            None,
        )
        try:
            task_routes_module.chat_persistence_service.get_trace_step_markdown_meta = (  # type: ignore[attr-defined]
                lambda _step: {"sanitized": True}
            )

            markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
                payload,
            )
        finally:
            if original_meta_helper is None:
                delattr(
                    task_routes_module.chat_persistence_service,
                    "get_trace_step_markdown_meta",
                )
            else:
                task_routes_module.chat_persistence_service.get_trace_step_markdown_meta = original_meta_helper  # type: ignore[attr-defined]

        self.assertIn('"sanitized": true', markdown)

    def test_build_task_export_markdown_infers_calc_summary_from_json_string_safe_output_without_preview(
        self,
    ) -> None:
        payload = task_routes_module.TaskExportJsonResponse(  # type: ignore[attr-defined]
            version="1.0",
            exported_at="2026-07-10T10:20:00",
            task=task_routes_module.TaskExportTask(  # type: ignore[attr-defined]
                id="task-export-json-string-safe-output-md",
                session_id="session-export-json-string-safe-output-md",
                prompt="export quoted safe output",
                status="completed",
                status_normalized="completed",
                status_label="Completed",
                status_rank=4,
                created_at="2026-07-10T10:15:00",
                updated_at="2026-07-10T10:20:00",
            ),
            usage=None,
            messages=[],
            trace=task_routes_module.TaskExportTrace(  # type: ignore[attr-defined]
                governance=None,
                step_count=1,
                rag_hit_count=0,
                rag_knowledge_base_ids=[],
                rag_chunks=[],
                steps=[
                    task_routes_module.TraceStep(  # type: ignore[attr-defined]
                        id="step-json-string-safe-output-md",
                        seq=11,
                        type="action",
                        content="Tool done: Hosted Math",
                        meta={
                            "tool": {
                                "name": "hosted_math",
                                "label": "Hosted Math",
                                "status": "done",
                                "effective_result_output_keys": [
                                    "result",
                                    "request_id",
                                ],
                                "output": '{"result":7,"request_id":"req-calc-1","kind":"provider_calc","secret":"hidden"}',
                            }
                        },
                    )
                ],
            ),
        )

        markdown = task_routes_module._build_task_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn("Calculated result = 7 (request id req-calc-1).", markdown)
        self.assertIn('"result": 7', markdown)
        self.assertIn('"request_id": "req-calc-1"', markdown)
        self.assertNotIn('"secret": "hidden"', markdown)
        self.assertNotIn("Tool done: Hosted Math\n", markdown)
