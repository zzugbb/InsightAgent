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

    def test_build_task_export_payload_reuses_shared_task_export_summary_helper_for_trace(
        self,
    ) -> None:
        task = {
            "id": "task-export-shared-trace-loader",
            "session_id": "session-export-shared-trace-loader",
            "prompt": "export shared trace loader",
            "status": "completed",
            "created_at": "2026-06-16T11:00:00",
            "updated_at": "2026-06-16T11:05:00",
            "trace_json": "guarded-trace-json",
            "usage_json": None,
        }
        original_get_task_trace_steps = getattr(
            task_routes_module, "get_task_trace_steps", None
        )
        original_trace_steps_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_steps_from_task",
        )
        original_task_export_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_response_summary",
            None,
        )
        original_trace_export_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_export_summary_from_task",
            None,
        )
        original_get_task_messages = task_routes_module.get_task_messages
        try:
            task_routes_module.get_task_trace_steps = lambda *_args, **_kwargs: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                AssertionError(
                    "task export should load parsed trace steps from the shared task helper instead of refetching by task id"
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "task export route should reuse get_task_export_response_summary(task, message_rows) instead of touching parsed trace steps directly"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "task export route should reuse get_task_export_response_summary(task, message_rows) instead of calling trace export summary helper directly"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda raw_task, _message_rows: {
                    "task": {
                        "id": str(raw_task.get("id", "")),
                        "session_id": str(raw_task.get("session_id", "")),
                        "prompt": str(raw_task.get("prompt", "")),
                        "status": str(raw_task.get("status", "")),
                        "status_normalized": "completed",
                        "status_label": "Completed",
                        "status_rank": 3,
                        "created_at": str(raw_task.get("created_at", "")),
                        "updated_at": str(raw_task.get("updated_at", "")),
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "step_count": 1,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                        "steps": [
                            task_routes_module.TraceStep(  # type: ignore[attr-defined]
                                id="shared-task-step",
                                type="thought",
                                content=f"shared::{raw_task.get('trace_json')}",
                                seq=2,
                            )
                        ],
                    },
                }
            )
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-shared-trace-loader",
            )
        finally:
            if original_get_task_trace_steps is None:
                delattr(task_routes_module, "get_task_trace_steps")
            else:
                task_routes_module.get_task_trace_steps = original_get_task_trace_steps  # type: ignore[attr-defined]
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = original_trace_steps_loader  # type: ignore[attr-defined]
            if original_task_export_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_export_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_export_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_export_response_summary = original_task_export_helper  # type: ignore[attr-defined]
            if original_trace_export_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_export_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_export_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_export_summary_from_task = original_trace_export_helper  # type: ignore[attr-defined]
            task_routes_module.get_task_messages = original_get_task_messages

        self.assertEqual([step.id for step in payload.trace.steps], ["shared-task-step"])
        self.assertEqual(payload.trace.steps[0].content, "shared::guarded-trace-json")

    def test_build_task_export_payload_trusts_service_task_governance_summary(
        self,
    ) -> None:
        task = {
            "id": "task-export-shared-trace-governance",
            "session_id": "session-export-shared-trace-governance",
            "prompt": "export shared trace governance",
            "status": "completed",
            "created_at": "2026-06-16T12:00:00",
            "updated_at": "2026-06-16T12:05:00",
            "trace_json": None,
            "usage_json": None,
            "governance": {
                "profile": "shared_trace_profile",
                "provider_source": "shared_trace_source",
                "allowed_tool_names": ["shared_trace_tool"],
                "allowed_tool_labels": ["Shared Trace Tool"],
            },
        }
        original_trace_steps_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_steps_from_task",
        )
        original_get_task_messages = task_routes_module.get_task_messages
        fake_step = task_routes_module.TraceStep(  # type: ignore[attr-defined]
            id="trace-export-shared-step",
            type="thought",
            content="trace helper",
            seq=1,
        )
        try:
            self.assertFalse(
                hasattr(
                    task_routes_module.chat_persistence_service,
                    "_extract_task_governance_from_task_with_parsed_trace_steps",
                )
            )
            class GuardedGovernanceDict(dict):
                def get(self, *_args, **_kwargs):
                    raise AssertionError(
                        "task export governance should construct outward model directly from the shared task+parsed-trace helper output"
                    )

            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda _task: [fake_step]
            )
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-shared-trace-governance",
            )
        finally:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = original_trace_steps_loader  # type: ignore[attr-defined]
            task_routes_module.get_task_messages = original_get_task_messages

        self.assertIsNotNone(payload.trace.governance)
        assert payload.trace.governance is not None
        self.assertEqual(payload.trace.governance.profile, "shared_trace_profile")
        self.assertEqual(
            payload.trace.governance.provider_source, "shared_trace_source"
        )
        self.assertEqual(payload.trace.governance.allowed_tool_names, ["shared_trace_tool"])
        self.assertEqual(
            payload.trace.governance.allowed_tool_labels, ["Shared Trace Tool"]
        )

    def test_build_task_export_payload_trusts_service_governance_shape(
        self,
    ) -> None:
        task = {
            "id": "task-export-builder-persisted-governance",
            "session_id": "session-export-builder-persisted-governance",
            "prompt": "export builder governance fallback",
            "status": "completed",
            "created_at": "2026-06-16T13:00:00",
            "updated_at": "2026-06-16T13:05:00",
            "governance": None,
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
            class GuardedGovernanceDict(dict):
                def get(self, *_args, **_kwargs):
                    raise AssertionError(
                        "task export should construct outward model directly from the service governance dict"
                    )

            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda _task: []
            )
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []
            task["governance"] = GuardedGovernanceDict(
                profile="builder_profile",
                provider_source="builder_source",
                allowed_tool_names=["builder_tool"],
                allowed_tool_labels=["Builder Tool"],
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-builder-persisted-governance",
            )
        finally:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = original_trace_steps_loader  # type: ignore[attr-defined]
            task_routes_module.get_task_messages = original_get_task_messages
        self.assertIsNotNone(payload.trace.governance)
        assert payload.trace.governance is not None
        self.assertEqual(payload.trace.governance.profile, "builder_profile")
        self.assertEqual(payload.trace.governance.provider_source, "builder_source")
        self.assertEqual(payload.trace.governance.allowed_tool_names, ["builder_tool"])
        self.assertEqual(
            payload.trace.governance.allowed_tool_labels, ["Builder Tool"]
        )

    def test_build_task_export_payload_reuses_shared_task_export_response_summary_helper_for_governance(
        self,
    ) -> None:
        task = {
            "id": "task-export-plain-clone-helper",
            "session_id": "session-export-plain-clone-helper",
            "prompt": "export plain clone helper",
            "status": "completed",
            "created_at": "2026-06-18T12:00:00",
            "updated_at": "2026-06-18T12:05:00",
            "trace_json": None,
            "usage_json": None,
            "governance": {
                "profile": "poisoned_profile",
                "provider_source": "poisoned_source",
                "allowed_tool_names": ["poisoned_tool"],
                "allowed_tool_labels": ["Poisoned Tool"],
            },
        }
        original_trace_steps_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_steps_from_task",
        )
        original_get_task_messages = task_routes_module.get_task_messages
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_response_summary",
            None,
        )
        original_task_export_trace = task_routes_module.TaskExportTrace
        original_json_response = task_routes_module.TaskExportJsonResponse
        cloned_governance = {
            "profile": "planning_only",
            "provider_source": "planning_suite",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        shared_message = task_routes_module.TaskExportMessage(
            id="message-shared-model",
            task_id="task-export-plain-clone-helper",
            role="assistant",
            content="shared message model",
            created_at="2026-06-18T12:01:00",
        )
        shared_trace = original_task_export_trace(
            governance=cloned_governance,
            step_count=0,
            rag_hit_count=0,
            rag_knowledge_base_ids=[],
            rag_chunks=[],
            steps=[],
        )
        captured: list[dict[str, object]] = []
        try:
            self.assertFalse(hasattr(task_routes_module, "_plain_clone_dict"))
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda _task: (_ for _ in ()).throw(
                    AssertionError(
                        "task export route should reuse get_task_export_response_summary(task, message_rows) for governance instead of touching parsed trace steps directly"
                    )
                )
            )
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda _task, _message_rows: {
                    "task": {
                        "id": "task-export-plain-clone-helper",
                        "session_id": "session-export-plain-clone-helper",
                        "prompt": "export plain clone helper",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 3,
                        "created_at": "2026-06-18T12:00:00",
                        "updated_at": "2026-06-18T12:05:00",
                    },
                    "usage": None,
                    "messages": [shared_message],
                    "trace": shared_trace,
                }
            )
            task_routes_module.TaskExportTrace = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "task export route should reuse TaskExportJsonResponse(task=..., trace=...) with shared response summary instead of manually constructing TaskExportTrace(...)"
                )
            )
            task_routes_module.TaskExportJsonResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-plain-clone-helper",
            )
        finally:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = original_trace_steps_loader  # type: ignore[attr-defined]
            task_routes_module.get_task_messages = original_get_task_messages
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_export_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_export_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_export_response_summary = original_response_helper  # type: ignore[attr-defined]
            task_routes_module.TaskExportTrace = original_task_export_trace
            task_routes_module.TaskExportJsonResponse = original_json_response

        self.assertEqual(len(captured), 1)
        self.assertIs(captured[0]["trace"], shared_trace)
        self.assertIs(captured[0]["messages"][0], shared_message)

    def test_build_task_export_payload_reuses_shared_task_export_response_summary_helper_for_usage(
        self,
    ) -> None:
        task = {
            "id": "task-export-usage-parser",
            "session_id": "session-export-usage-parser",
            "prompt": "export usage parser",
            "status": "completed",
            "created_at": "2026-06-16T14:00:00",
            "updated_at": "2026-06-16T14:05:00",
            "trace_json": None,
            "usage_json": "usage-json-guarded",
        }
        original_trace_steps_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_steps_from_task",
        )
        original_get_task_messages = task_routes_module.get_task_messages
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_response_summary",
            None,
        )
        original_payload_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_payload_summary",
            None,
        )
        original_usage_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_usage_from_task",
            None,
        )
        original_parser = task_routes_module.chat_persistence_service._parse_usage_json_blob  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda _task: []
            )
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []
            task_routes_module.chat_persistence_service._parse_usage_json_blob = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "task export route should reuse get_task_export_summary_from_task(task) instead of the private usage json parser"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_usage_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "task export route should reuse get_task_export_summary_from_task(task) instead of calling task usage helper directly"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "task export route should reuse get_task_export_response_summary(task, message_rows) instead of calling get_task_export_payload_summary(task, message_rows) directly"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda raw_task, _message_rows: captured.append(raw_task.get("usage_json"))
                or {
                    "task": {
                        "id": str(raw_task.get("id", "")),
                        "session_id": str(raw_task.get("session_id", "")),
                        "prompt": str(raw_task.get("prompt", "")),
                        "status": str(raw_task.get("status", "")),
                        "status_normalized": "completed",
                        "status_label": "Completed",
                        "status_rank": 3,
                        "created_at": str(raw_task.get("created_at", "")),
                        "updated_at": str(raw_task.get("updated_at", "")),
                    },
                    "usage": {
                        "prompt_tokens": 21,
                        "completion_tokens": 34,
                        "cost_estimate": 0.2,
                    },
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                        "steps": [],
                    },
                }
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-usage-parser",
            )
        finally:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = original_trace_steps_loader  # type: ignore[attr-defined]
            task_routes_module.get_task_messages = original_get_task_messages
            task_routes_module.chat_persistence_service._parse_usage_json_blob = original_parser  # type: ignore[attr-defined]
            if original_response_helper is None:
                if hasattr(task_routes_module.chat_persistence_service, "get_task_export_summary_from_task"):
                    delattr(task_routes_module.chat_persistence_service, "get_task_export_response_summary")
            else:
                task_routes_module.chat_persistence_service.get_task_export_response_summary = original_response_helper  # type: ignore[attr-defined]
            if original_payload_helper is None:
                if hasattr(task_routes_module.chat_persistence_service, "get_task_export_payload_summary"):
                    delattr(task_routes_module.chat_persistence_service, "get_task_export_payload_summary")
            else:
                task_routes_module.chat_persistence_service.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]
            if original_usage_helper is None:
                if hasattr(task_routes_module.chat_persistence_service, "get_task_usage_from_task"):
                    delattr(task_routes_module.chat_persistence_service, "get_task_usage_from_task")
            else:
                task_routes_module.chat_persistence_service.get_task_usage_from_task = original_usage_helper  # type: ignore[attr-defined]

        self.assertEqual(captured, ["usage-json-guarded"])
        self.assertEqual(
            payload.usage,
            {
                "prompt_tokens": 21,
                "completion_tokens": 34,
                "cost_estimate": 0.2,
            },
        )

    def test_build_task_export_payload_reuses_shared_task_export_response_summary_helper_for_task_meta(
        self,
    ) -> None:
        task = {
            "id": "task-export-meta-helper",
            "session_id": "session-export-meta-helper",
            "prompt": "poisoned prompt",
            "status": "poisoned_status",
            "created_at": "poisoned_created_at",
            "updated_at": "poisoned_updated_at",
            "trace_json": None,
            "usage_json": None,
        }
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_response_summary",
            None,
        )
        original_with_status_meta = getattr(task_routes_module, "_with_status_meta", None)
        original_get_task_messages = task_routes_module.get_task_messages
        original_task_export_task = task_routes_module.TaskExportTask
        original_json_response = task_routes_module.TaskExportJsonResponse
        shared_task = original_task_export_task(
            id="task-export-meta-helper",
            session_id="session-export-meta-helper",
            prompt="export summary prompt",
            status="completed",
            status_normalized="normalized::completed",
            status_label="label::completed",
            status_rank=29,
            created_at="2026-06-22T12:00:00",
            updated_at="2026-06-22T12:05:00",
        )
        captured: list[dict[str, object]] = []
        try:
            self.assertFalse(hasattr(task_routes_module, "_with_status_meta"))
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda _task, _message_rows: {
                    "task": shared_task,
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": None,
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                        "steps": [],
                    },
                }
            )
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []
            task_routes_module.TaskExportTask = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "task export route should reuse TaskExportJsonResponse(task=..., trace=...) with shared response summary instead of manually constructing TaskExportTask(...)"
                )
            )
            task_routes_module.TaskExportJsonResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-meta-helper",
            )
        finally:
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_export_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_export_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_export_response_summary = original_response_helper  # type: ignore[attr-defined]
            if original_with_status_meta is not None:
                task_routes_module._with_status_meta = original_with_status_meta  # type: ignore[attr-defined]
            task_routes_module.get_task_messages = original_get_task_messages
            task_routes_module.TaskExportTask = original_task_export_task
            task_routes_module.TaskExportJsonResponse = original_json_response

        self.assertEqual(len(captured), 1)
        self.assertIs(captured[0]["task"], shared_task)

    def test_build_task_export_payload_reuses_shared_trace_export_summary_helper_for_rag(
        self,
    ) -> None:
        task = {
            "id": "task-export-rag-summary",
            "session_id": "session-export-rag-summary",
            "prompt": "export rag summary",
            "status": "completed",
            "created_at": "2026-06-17T16:00:00",
            "updated_at": "2026-06-17T16:05:00",
            "trace_json": "guarded-trace-json",
            "usage_json": None,
            "governance": None,
        }
        original_trace_export_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_export_summary_from_task",
            None,
        )
        original_trace_steps_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_steps_from_task",
        )
        original_rag_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_trace_rag_export_summary",
            None,
        )
        original_get_task_messages = task_routes_module.get_task_messages
        try:
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "task export route should not read parsed trace steps directly when the shared trace export helper is available"
                    )
                )
            )
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []
            task_routes_module.chat_persistence_service.get_trace_rag_export_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "task export route should not call get_trace_rag_export_summary(trace_steps) directly after trace export summary is centralized in the service"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [],
                    "step_count": 1,
                    "rag_hit_count": 1,
                    "rag_knowledge_base_ids": ["kb-shared"],
                    "rag_chunks": [
                        {
                            "step_id": "shared-rag-step",
                            "knowledge_base_id": "kb-shared",
                            "content": "chunk-shared",
                        }
                    ],
                }
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-rag-summary",
            )
        finally:
            task_routes_module.get_task_messages = original_get_task_messages
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = original_trace_steps_loader  # type: ignore[attr-defined]
            if original_trace_export_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_export_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_export_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_export_summary_from_task = original_trace_export_helper  # type: ignore[attr-defined]
            if original_rag_helper is None:
                if hasattr(task_routes_module.chat_persistence_service, "get_trace_rag_export_summary"):
                    delattr(task_routes_module.chat_persistence_service, "get_trace_rag_export_summary")
            else:
                task_routes_module.chat_persistence_service.get_trace_rag_export_summary = original_rag_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.trace.rag_hit_count, 1)
        self.assertEqual(payload.trace.rag_knowledge_base_ids, ["kb-shared"])
        self.assertEqual(len(payload.trace.rag_chunks), 1)
        self.assertEqual(payload.trace.rag_chunks[0].content, "chunk-shared")

    def test_get_task_detail_does_not_fallback_to_row_parser_without_service_governance(
        self,
    ) -> None:
        self.assertTrue(hasattr(task_routes_module, "chat_persistence_service"))
        original_get_task = task_routes_module.get_task
        original_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-no-fallback-governance-route",
                "session_id": "session-no-fallback-governance-route",
                "prompt": "no fallback governance route task",
                "status": "completed",
                "trace_json": None,
                "usage_json": None,
                "tool_registry_profile": "poisoned_profile",
                "tool_registry_provider_source": "poisoned_source",
                "allowed_tool_names_json": json.dumps(["poisoned_tool"]),
                "allowed_tool_labels_json": json.dumps(["Poisoned Tool"]),
                "created_at": "2026-06-11T12:00:00",
                "updated_at": "2026-06-11T12:01:00",
            }
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: (_ for _ in ()).throw(
                    AssertionError(
                        "get_task_detail should not fall back to the shared row parser when service governance is absent"
                    )
                )
            )
            response = task_routes_module.get_task_detail(
                "task-no-fallback-governance-route",
                current_user={"id": "user-no-fallback-governance-route"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_parser
            )

        self.assertIsNone(response.governance)

    def test_get_task_trace_detail_reuses_shared_task_trace_response_summary_helper(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        original_trace_loader = (
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task
        )
        original_trace_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_response_summary_from_task",
            None,
        )
        original_trace_export_helper = (
            task_routes_module.chat_persistence_service.get_task_trace_export_summary_from_task
        )
        original_normalize = task_routes_module.normalize_task_status
        original_label_exists = hasattr(task_routes_module, "task_status_label")
        original_rank_exists = hasattr(task_routes_module, "task_status_rank")
        original_label = getattr(task_routes_module, "task_status_label", None)
        original_rank = getattr(task_routes_module, "task_status_rank", None)
        try:
            self.assertFalse(hasattr(task_routes_module, "get_task_trace_steps"))
            task = {
                "id": "task-trace-detail-shared-loader",
                "session_id": "session-trace-detail-shared-loader",
                "status": "completed",
                "trace_json": "guarded-trace-json",
            }
            task_routes_module.get_task = lambda _task_id, _user_id: dict(task)
            task_routes_module.get_task_trace_steps = lambda *_args, **_kwargs: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                AssertionError(
                    "get_task_trace_detail should reuse get_task_trace_export_summary_from_task(task) instead of refetching trace by task id"
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda _raw_task: (_ for _ in ()).throw(
                    AssertionError(
                        "get_task_trace_detail should reuse get_task_trace_response_summary_from_task(task) instead of touching parsed trace steps directly"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                lambda _raw_task: (_ for _ in ()).throw(
                    AssertionError(
                        "get_task_trace_detail should reuse get_task_trace_response_summary_from_task(task) instead of calling get_task_trace_export_summary_from_task(task) directly"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda raw_task: {
                    "steps": [
                        task_routes_module.TraceStep(  # type: ignore[attr-defined]
                            id=f"shared::{raw_task.get('trace_json')}",
                            type="thought",
                            content="shared trace detail",
                            seq=9,
                        )
                    ],
                    "status": "completed",
                    "status_normalized": "normalized::completed",
                    "status_label": "label::completed",
                    "status_rank": 31,
                }
            )
            task_routes_module.normalize_task_status = lambda _status: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                AssertionError(
                    "get_task_trace_detail should reuse get_task_trace_response_summary_from_task(task) for status meta instead of calling normalize_task_status(status)"
                )
            )
            task_routes_module.task_status_label = lambda _status: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                AssertionError(
                    "get_task_trace_detail should reuse get_task_trace_response_summary_from_task(task) for status meta instead of calling task_status_label(status)"
                )
            )
            task_routes_module.task_status_rank = lambda _status: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                AssertionError(
                    "get_task_trace_detail should reuse get_task_trace_response_summary_from_task(task) for status meta instead of calling task_status_rank(status)"
                )
            )
            payload = task_routes_module.get_task_trace_detail(
                "task-trace-detail-shared-loader",
                current_user={"id": "user-trace-detail-shared-loader"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if hasattr(task_routes_module, "get_task_trace_steps"):
                delattr(task_routes_module, "get_task_trace_steps")
            task_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                original_trace_loader
            )
            if original_trace_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = original_trace_response_helper  # type: ignore[attr-defined]
            task_routes_module.chat_persistence_service.get_task_trace_export_summary_from_task = (  # type: ignore[attr-defined]
                original_trace_export_helper
            )
            task_routes_module.normalize_task_status = original_normalize  # type: ignore[attr-defined]
            if original_label_exists:
                task_routes_module.task_status_label = original_label  # type: ignore[attr-defined]
            elif hasattr(task_routes_module, "task_status_label"):
                delattr(task_routes_module, "task_status_label")
            if original_rank_exists:
                task_routes_module.task_status_rank = original_rank  # type: ignore[attr-defined]
            elif hasattr(task_routes_module, "task_status_rank"):
                delattr(task_routes_module, "task_status_rank")

        self.assertEqual([step.id for step in payload.steps], ["shared::guarded-trace-json"])
        self.assertEqual(payload.status, "completed")
        self.assertEqual(payload.status_normalized, "normalized::completed")
        self.assertEqual(payload.status_label, "label::completed")
        self.assertEqual(payload.status_rank, 31)

    def test_get_task_trace_detail_reuses_shared_task_trace_response_summary_for_outward_model(
        self,
    ) -> None:
        class GuardedTraceSummary(dict[str, object]):
            def get(self, _key: object, _default: object = None) -> object:
                raise AssertionError(
                    "get_task_trace_detail should pass the shared trace response summary directly into TaskTraceResponse(...) instead of re-reading fields with trace_summary.get(...)"
                )

        original_get_task = task_routes_module.get_task
        original_trace_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_response_summary_from_task",
            None,
        )
        original_trace_response_model = task_routes_module.TaskTraceResponse
        captured: list[dict[str, object]] = []
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-trace-outward-model",
                "session_id": "session-trace-outward-model",
                "status": "completed",
                "trace_json": "trace-outward-model",
            }
            task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: GuardedTraceSummary(
                    {
                        "steps": [
                            task_routes_module.TraceStep(  # type: ignore[attr-defined]
                                id="trace-outward-step",
                                type="thought",
                                content="trace outward",
                                seq=1,
                            )
                        ],
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 7,
                    }
                )
            )
            task_routes_module.TaskTraceResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.get_task_trace_detail(
                "task-trace-outward-model",
                current_user={"id": "user-trace-outward-model"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_trace_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = original_trace_response_helper  # type: ignore[attr-defined]
            task_routes_module.TaskTraceResponse = original_trace_response_model

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["task_id"], "task-trace-outward-model")
        self.assertEqual(captured[0]["status_rank"], 7)
        self.assertEqual(captured[0]["steps"][0].id, "trace-outward-step")

    def test_get_task_trace_detail_redacts_http_json_steps_from_response_summary(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="task-trace-route-http-json-step"
        )
        original_get_task = task_routes_module.get_task
        original_trace_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_response_summary_from_task",
            None,
        )
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-trace-route-http-json",
                "session_id": "session-trace-route-http-json",
                "status": "completed",
                "trace_json": "guarded-trace-json",
            }
            task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "steps": [raw_step],
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 3,
                }
            )
            payload = task_routes_module.get_task_trace_detail(
                "task-trace-route-http-json",
                current_user={"id": "user-trace-route-http-json"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_trace_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_response_summary_from_task = original_trace_response_helper  # type: ignore[attr-defined]

        serialized = json.dumps(
            [step.model_dump(exclude_none=True) for step in payload.steps],
            ensure_ascii=False,
        )

        self.assertIn("gateway token=[redacted]", serialized)
        self.assertIn("preview token=[redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_get_task_trace_delta_detail_reuses_shared_delta_snapshot_helper(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        original_delta_snapshot_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_snapshot_from_task",
            None,
        )
        try:
            self.assertFalse(hasattr(task_routes_module, "_latest_seq_from_task"))
            self.assertFalse(hasattr(task_routes_module, "get_task_trace_delta_steps_from_task"))
            task = {
                "id": "task-trace-delta-shared-loader",
                "session_id": "session-trace-delta-shared-loader",
                "status": "completed",
                "trace_json": "guarded-trace-json",
            }
            task_routes_module.get_task = lambda _task_id, _user_id: dict(task)
            task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = (  # type: ignore[attr-defined]
                lambda raw_task, after_seq=0, limit=200: (
                    [
                        task_routes_module.TraceStep(  # type: ignore[attr-defined]
                            id=f"shared-delta::{raw_task.get('trace_json')}",
                            type="thought",
                            content="shared trace delta",
                            seq=9,
                        )
                    ],
                    9,
                    False,
                    11,
                    "shared-delta::guarded-trace-json",
                )
            )
            payload = task_routes_module.get_task_trace_delta_detail(
                "task-trace-delta-shared-loader",
                after_seq=3,
                limit=50,
                current_user={"id": "user-trace-delta-shared-loader"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_delta_snapshot_loader is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_snapshot_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_snapshot_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = original_delta_snapshot_loader  # type: ignore[attr-defined]

        self.assertEqual([step.id for step in payload.steps], ["shared-delta::guarded-trace-json"])
        self.assertEqual(payload.next_cursor, 9)
        self.assertFalse(payload.has_more)
        self.assertEqual(payload.lag_seq, 2)

    def test_get_task_trace_delta_detail_reuses_shared_delta_response_summary_for_outward_model(
        self,
    ) -> None:
        class GuardedDeltaSummary(dict[str, object]):
            def get(self, _key: object, _default: object = None) -> object:
                raise AssertionError(
                    "get_task_trace_delta_detail should pass the shared delta response summary directly into TaskTraceDeltaResponse(...) instead of re-reading fields with delta_summary.get(...)"
                )

        original_get_task = task_routes_module.get_task
        original_delta_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_response_summary_from_task",
            None,
        )
        original_delta_snapshot_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_snapshot_from_task",
            None,
        )
        original_trace_delta_model = task_routes_module.TaskTraceDeltaResponse
        captured: list[dict[str, object]] = []
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-trace-delta-outward-model",
                "session_id": "session-trace-delta-outward-model",
                "status": "completed",
                "trace_json": "trace-delta-outward-model",
            }
            task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "get_task_trace_delta_detail should reuse get_task_trace_delta_response_summary_from_task(task, after_seq, limit) instead of calling get_task_trace_delta_snapshot_from_task(...) directly"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_trace_delta_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task, after_seq=0, limit=200: GuardedDeltaSummary(
                    {
                        "steps": [
                            task_routes_module.TraceStep(  # type: ignore[attr-defined]
                                id=f"delta::{after_seq}::{limit}",
                                type="thought",
                                content="delta outward",
                                seq=4,
                            )
                        ],
                        "next_cursor": 4,
                        "has_more": False,
                        "lag_seq": 6,
                        "dropped": False,
                    }
                )
            )
            task_routes_module.TaskTraceDeltaResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.get_task_trace_delta_detail(
                "task-trace-delta-outward-model",
                after_seq=2,
                limit=40,
                current_user={"id": "user-trace-delta-outward-model"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_delta_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_response_summary_from_task = original_delta_response_helper  # type: ignore[attr-defined]
            if original_delta_snapshot_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_snapshot_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_snapshot_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = original_delta_snapshot_helper  # type: ignore[attr-defined]
            task_routes_module.TaskTraceDeltaResponse = original_trace_delta_model

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["task_id"], "task-trace-delta-outward-model")
        self.assertEqual(captured[0]["next_cursor"], 4)
        self.assertEqual(captured[0]["lag_seq"], 6)
        self.assertFalse(captured[0]["has_more"])
        self.assertFalse(captured[0]["dropped"])
        self.assertEqual(captured[0]["steps"][0].id, "delta::2::40")
        self.assertIsInstance(captured[0]["server_time"], str)

    def test_get_task_trace_delta_detail_redacts_http_json_steps_from_response_summary(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="task-trace-delta-route-http-json-step"
        )
        original_get_task = task_routes_module.get_task
        original_delta_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_response_summary_from_task",
            None,
        )
        try:
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-trace-delta-route-http-json",
                "session_id": "session-trace-delta-route-http-json",
                "status": "completed",
                "trace_json": "guarded-trace-json",
            }
            task_routes_module.chat_persistence_service.get_task_trace_delta_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task, **_kwargs: {
                    "steps": [raw_step],
                    "next_cursor": 3,
                    "has_more": False,
                    "lag_seq": 0,
                    "dropped": False,
                }
            )
            payload = task_routes_module.get_task_trace_delta_detail(
                "task-trace-delta-route-http-json",
                after_seq=0,
                limit=40,
                current_user={"id": "user-trace-delta-route-http-json"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            if original_delta_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_response_summary_from_task = original_delta_response_helper  # type: ignore[attr-defined]

        serialized = json.dumps(
            [step.model_dump(exclude_none=True) for step in payload.steps],
            ensure_ascii=False,
        )

        self.assertIn("gateway token=[redacted]", serialized)
        self.assertIn("preview token=[redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_get_tasks_route_trusts_service_governance_for_items(
        self,
    ) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        original_response_builder = getattr(task_routes_module, "_build_task_response", None)
        try:
            if original_response_builder is not None:
                task_routes_module._build_task_response = lambda _task: (_ for _ in ()).throw(  # type: ignore[attr-defined]
                    AssertionError(
                        "get_tasks should build item governance directly from the shared row parser"
                    )
                )
            task_routes_module.get_session = lambda session_id, user_id: {
                "id": session_id,
                "user_id": user_id,
                "title": "Task Builder Session",
            }
            task_routes_module.list_tasks = lambda **_kwargs: [
                {
                    "id": "task-list-service-governance",
                    "session_id": "session-list-service-governance",
                    "prompt": "service governance list task",
                    "status": "completed",
                    "trace_json": None,
                    "usage_json": None,
                    "governance": GuardedGovernanceDict(
                        profile="guarded_profile",
                        provider_source="guarded_source",
                        allowed_tool_names=["guarded_tool"],
                        allowed_tool_labels=["Guarded Tool"],
                    ),
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "default",
                    "allowed_tool_names_json": json.dumps(["task_plan"]),
                    "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                    "created_at": "2026-06-16T19:00:00",
                    "updated_at": "2026-06-16T19:01:00",
                }
            ]
            task_routes_module.count_tasks = lambda *_args, **_kwargs: 1
            class GuardedGovernanceDict(dict):
                def get(self, *_args, **_kwargs):
                    raise AssertionError(
                        "get_tasks should construct item governance directly from the shared row parser output"
                    )
            original_row_parser = (
                task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
            )
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: (_ for _ in ()).throw(
                    AssertionError(
                        "get_tasks should trust service governance instead of reusing the shared row parser"
                    )
                )
            )
            payload = task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-list-builder-governance",
                query=None,
                tool_registry_profile=None,
                tool_registry_provider_source=None,
                current_user={"id": "user-list-builder-governance"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )
            if original_response_builder is None:
                if hasattr(task_routes_module, "_build_task_response"):
                    delattr(task_routes_module, "_build_task_response")
            else:
                task_routes_module._build_task_response = original_response_builder  # type: ignore[attr-defined]

        self.assertEqual(len(payload.items), 1)
        self.assertIsNotNone(payload.items[0].governance)
        assert payload.items[0].governance is not None
        self.assertEqual(payload.items[0].governance.profile, "guarded_profile")
        self.assertEqual(payload.items[0].governance.provider_source, "guarded_source")
        self.assertEqual(payload.items[0].governance.allowed_tool_names, ["guarded_tool"])
        self.assertEqual(
            payload.items[0].governance.allowed_tool_labels, ["Guarded Tool"]
        )

    def test_get_tasks_route_does_not_fallback_item_governance_from_row(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        original_row_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            task_routes_module.get_session = lambda session_id, user_id: {
                "id": session_id,
                "user_id": user_id,
                "title": "Task No Fallback Session",
            }
            task_routes_module.list_tasks = lambda **_kwargs: [
                {
                    "id": "task-list-no-fallback-governance",
                    "session_id": "session-list-no-fallback-governance",
                    "prompt": "list governance without service summary",
                    "status": "completed",
                    "trace_json": None,
                    "usage_json": None,
                    "tool_registry_profile": "poisoned_profile",
                    "tool_registry_provider_source": "poisoned_source",
                    "allowed_tool_names_json": json.dumps(["poisoned_tool"]),
                    "allowed_tool_labels_json": json.dumps(["Poisoned Tool"]),
                    "created_at": "2026-06-16T20:00:00",
                    "updated_at": "2026-06-16T20:01:00",
                }
            ]
            task_routes_module.count_tasks = lambda *_args, **_kwargs: 1
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _task: (_ for _ in ()).throw(
                    AssertionError(
                        "get_tasks should not fall back to the shared row parser when service governance is absent"
                    )
                )
            )
            payload = task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-list-no-fallback-governance",
                query=None,
                tool_registry_profile=None,
                tool_registry_provider_source=None,
                current_user={"id": "user-list-no-fallback-governance"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )

        self.assertEqual(len(payload.items), 1)
        self.assertIsNone(payload.items[0].governance)

    def test_get_tasks_passes_raw_governance_dict_to_task_response(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        original_task_response = task_routes_module.TaskResponse
        original_list_response = task_routes_module.TaskListResponse
        task = {
            "id": "task-list-raw-governance",
            "session_id": "session-list-raw-governance",
            "prompt": "list raw governance summary",
            "status": "completed",
            "trace_json": None,
            "usage_json": None,
            "governance": {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
            "created_at": "2026-06-18T10:10:00",
            "updated_at": "2026-06-18T10:11:00",
        }
        captured: list[dict[str, object]] = []
        try:
            task_routes_module.get_session = lambda session_id, user_id: {
                "id": session_id,
                "user_id": user_id,
                "title": "Task Raw Governance Session",
            }
            task_routes_module.list_tasks = lambda **_kwargs: [task]
            task_routes_module.count_tasks = lambda *_args, **_kwargs: 1
            task_routes_module.TaskResponse = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks should reuse TaskListResponse(items=...) with shared task summaries instead of manually constructing TaskResponse(...) per item"
                )
            )
            task_routes_module.TaskListResponse = (
                lambda **kwargs: captured.extend(kwargs["items"]) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-list-raw-governance",
                query=None,
                tool_registry_profile=None,
                tool_registry_provider_source=None,
                current_user={"id": "user-list-raw-governance"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks
            task_routes_module.TaskResponse = original_task_response
            task_routes_module.TaskListResponse = original_list_response

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["governance"], task["governance"])

    def test_get_tasks_reuses_shared_task_response_summary_helper(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        original_with_status_meta = getattr(task_routes_module, "_with_status_meta", None)
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_response_summary_from_task",
            None,
        )
        original_task_response = task_routes_module.TaskResponse
        original_list_response = task_routes_module.TaskListResponse
        cloned_governance = {
            "profile": "planning_only",
            "provider_source": "planning_suite",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        captured: list[dict[str, object]] = []
        try:
            self.assertFalse(hasattr(task_routes_module, "_with_status_meta"))
            task_routes_module.get_session = lambda session_id, user_id: {
                "id": session_id,
                "user_id": user_id,
                "title": "Task Governance Helper Session",
            }
            task_routes_module.list_tasks = lambda **_kwargs: [
                {
                    "id": "task-list-governance-helper",
                    "session_id": "session-list-governance-helper",
                    "prompt": "list governance helper",
                    "status": "completed",
                    "trace_json": None,
                    "usage_json": None,
                    "created_at": "2026-06-18T11:10:00",
                    "updated_at": "2026-06-18T11:11:00",
                }
            ]
            task_routes_module.count_tasks = lambda *_args, **_kwargs: 1
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                "id": "task-list-governance-helper",
                "session_id": "session-list-governance-helper",
                "prompt": "list governance helper",
                "status": "completed",
                "status_normalized": "completed",
                "status_label": "Completed",
                "status_rank": 3,
                "trace_json": None,
                "usage_json": None,
                "created_at": "2026-06-18T11:10:00",
                "updated_at": "2026-06-18T11:11:00",
                "governance": cloned_governance,
            }
            )
            task_routes_module.TaskResponse = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks should reuse TaskListResponse(items=...) with shared task summaries instead of manually constructing TaskResponse(...) per item"
                )
            )
            task_routes_module.TaskListResponse = (
                lambda **kwargs: captured.extend(kwargs["items"]) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-list-governance-helper",
                query=None,
                tool_registry_profile=None,
                tool_registry_provider_source=None,
                current_user={"id": "user-list-governance-helper"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_response_summary_from_task = original_response_helper  # type: ignore[attr-defined]
            if original_with_status_meta is not None:
                task_routes_module._with_status_meta = original_with_status_meta  # type: ignore[attr-defined]
            task_routes_module.TaskResponse = original_task_response
            task_routes_module.TaskListResponse = original_list_response

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["governance"], cloned_governance)

    def test_get_tasks_reuses_top_level_response_model_for_items(self) -> None:
        original_get_session = task_routes_module.get_session
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_response_summary_from_task",
            None,
        )
        original_task_response = task_routes_module.TaskResponse
        original_list_response = task_routes_module.TaskListResponse
        captured: list[dict[str, object]] = []
        try:
            task_routes_module.get_session = lambda session_id, user_id: {
                "id": session_id,
                "user_id": user_id,
                "title": "Task List Outward Model Session",
            }
            task_routes_module.list_tasks = lambda **_kwargs: [{"id": "task-list-outward-model"}]
            task_routes_module.count_tasks = lambda *_args, **_kwargs: 1
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda _task: {
                    "id": "task-list-outward-model",
                    "session_id": "session-list-outward-model",
                    "prompt": "task list outward model",
                    "status": "completed",
                    "status_normalized": "normalized::completed",
                    "status_label": "label::completed",
                    "status_rank": 5,
                    "governance": {
                        "profile": "planning_only",
                        "provider_source": "planning_suite",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner Suite"],
                    },
                    "trace_json": None,
                    "usage_json": None,
                    "created_at": "2026-06-23T16:00:00",
                    "updated_at": "2026-06-23T16:01:00",
                }
            )
            task_routes_module.TaskResponse = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks should reuse TaskListResponse(items=...) with shared task summaries instead of manually constructing TaskResponse(...) per item"
                )
            )
            task_routes_module.TaskListResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id="session-list-outward-model",
                query=None,
                tool_registry_profile=None,
                tool_registry_provider_source=None,
                current_user={"id": "user-list-outward-model"},
            )
        finally:
            task_routes_module.get_session = original_get_session
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_response_summary_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_response_summary_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_response_summary_from_task = original_response_helper  # type: ignore[attr-defined]
            task_routes_module.TaskResponse = original_task_response
            task_routes_module.TaskListResponse = original_list_response

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["total"], 1)
        self.assertEqual(captured[0]["items"][0]["id"], "task-list-outward-model")
        self.assertEqual(
            captured[0]["items"][0]["governance"]["provider_source"],
            "planning_suite",
        )

    def test_get_sessions_reuses_top_level_response_model_for_items(self) -> None:
        original_list_sessions = session_routes_module.list_sessions
        original_count_sessions = session_routes_module.count_sessions
        original_session_response = session_routes_module.SessionResponse
        original_list_response = session_routes_module.SessionListResponse
        captured: list[dict[str, object]] = []
        try:
            session_routes_module.list_sessions = lambda **_kwargs: [
                {
                    "id": "session-list-outward-model",
                    "title": "Session List Outward Model",
                    "created_at": "2026-06-23T16:20:00",
                    "updated_at": "2026-06-23T16:21:00",
                }
            ]
            session_routes_module.count_sessions = lambda *_args, **_kwargs: 1
            session_routes_module.SessionResponse = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_sessions should reuse SessionListResponse(items=...) instead of manually constructing SessionResponse(...) per item"
                )
            )
            session_routes_module.SessionListResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            session_routes_module.get_sessions(
                limit=20,
                offset=0,
                current_user={"id": "user-session-list-outward-model"},
            )
        finally:
            session_routes_module.list_sessions = original_list_sessions
            session_routes_module.count_sessions = original_count_sessions
            session_routes_module.SessionResponse = original_session_response
            session_routes_module.SessionListResponse = original_list_response

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["items"][0]["id"], "session-list-outward-model")
        self.assertEqual(captured[0]["total"], 1)
        self.assertFalse(captured[0]["has_more"])

    def test_get_session_messages_detail_reuses_top_level_response_model_for_nested_payload(
        self,
    ) -> None:
        original_get_session = session_routes_module.get_session
        original_get_messages = session_routes_module.get_session_messages
        original_session_response = session_routes_module.SessionResponse
        original_message_response = session_routes_module.MessageResponse
        original_messages_response = session_routes_module.SessionMessagesResponse
        captured: list[dict[str, object]] = []
        try:
            session_routes_module.get_session = lambda _session_id, _user_id: {
                "id": "session-messages-outward-model",
                "title": "Messages Outward Model",
                "created_at": "2026-06-23T16:30:00",
                "updated_at": "2026-06-23T16:31:00",
            }
            session_routes_module.get_session_messages = lambda _session_id, _user_id: [
                {
                    "id": "message-outward-model",
                    "session_id": "session-messages-outward-model",
                    "task_id": None,
                    "role": "assistant",
                    "content": "hello",
                    "created_at": "2026-06-23T16:31:30",
                }
            ]
            session_routes_module.SessionResponse = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_session_messages_detail should reuse SessionMessagesResponse(session=..., messages=...) instead of manually constructing SessionResponse(...)"
                )
            )
            session_routes_module.MessageResponse = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_session_messages_detail should reuse SessionMessagesResponse(session=..., messages=...) instead of manually constructing MessageResponse(...)"
                )
            )
            session_routes_module.SessionMessagesResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            session_routes_module.get_session_messages_detail(
                "session-messages-outward-model",
                current_user={"id": "user-session-messages-outward-model"},
            )
        finally:
            session_routes_module.get_session = original_get_session
            session_routes_module.get_session_messages = original_get_messages
            session_routes_module.SessionResponse = original_session_response
            session_routes_module.MessageResponse = original_message_response
            session_routes_module.SessionMessagesResponse = original_messages_response

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["session"]["id"], "session-messages-outward-model")
        self.assertEqual(captured[0]["messages"][0]["id"], "message-outward-model")
        self.assertEqual(captured[0]["messages"][0]["role"], "assistant")

    def test_build_session_export_payload_surfaces_service_governance_summary(
        self,
    ) -> None:
        session = {
            "id": "session-export-governance",
            "title": "Governance Session",
            "created_at": "2026-06-05T10:00:00",
            "updated_at": "2026-06-05T10:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-1",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-05T10:00:00",
                    "updated_at": "2026-06-05T10:01:00",
                    "usage_json": None,
                    "governance": {
                        "profile": "planning_only",
                        "provider_source": "default",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "trace_json": json.dumps(
                        [
                            {
                                "id": "trace-1",
                                "type": "thought",
                                "content": "planning only",
                                "seq": 1,
                                "meta": {
                                    "tool_registry_profile": "planning_only",
                                    "tool_registry_provider_source": "default",
                                    "allowed_tool_names": ["task_plan"],
                                    "allowed_tool_labels": ["Task Planner"],
                                },
                            }
                        ]
                    ),
                },
                {
                    "id": "task-2",
                    "prompt": "task two",
                    "status": "completed",
                    "created_at": "2026-06-05T10:02:00",
                    "updated_at": "2026-06-05T10:03:00",
                    "usage_json": None,
                    "governance": {
                        "profile": "retrieval_only",
                        "provider_source": "suite_a",
                        "allowed_tool_names": ["task_retrieve"],
                        "allowed_tool_labels": ["Knowledge Retrieval"],
                    },
                    "trace_json": json.dumps(
                        [
                            {
                                "id": "trace-2",
                                "type": "thought",
                                "content": "retrieval only",
                                "seq": 1,
                                "meta": {
                                    "tool_registry_profile": "retrieval_only",
                                    "tool_registry_provider_source": "suite_a",
                                    "allowed_tool_names": ["task_retrieve"],
                                    "allowed_tool_labels": ["Knowledge Retrieval"],
                                },
                            }
                        ]
                    ),
                },
            ]
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-governance",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(
            payload.governance.profiles,
            ["planning_only", "retrieval_only"],
        )
        self.assertEqual(payload.governance.provider_sources, ["default", "suite_a"])
        self.assertEqual(
            payload.governance.allowed_tool_labels,
            ["Knowledge Retrieval", "Task Planner"],
        )

    def test_build_session_export_payload_trusts_service_task_governance_summary(
        self,
    ) -> None:
        session = {
            "id": "session-shared-trace-governance",
            "title": "Shared Trace Governance Session",
            "created_at": "2026-06-11T13:00:00",
            "updated_at": "2026-06-11T13:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_trace_loader = (
            session_routes_module.chat_persistence_service.get_task_trace_steps_from_task
        )
        try:
            self.assertFalse(
                hasattr(
                    session_routes_module.chat_persistence_service,
                    "_extract_task_governance_from_task_with_parsed_trace_steps",
                )
            )
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-shared-trace-governance",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-11T13:00:00",
                    "updated_at": "2026-06-11T13:01:00",
                    "usage_json": None,
                    "governance": {
                        "profile": "shared_trace_profile",
                        "provider_source": "shared_trace_source",
                        "allowed_tool_names": ["shared_trace_tool"],
                        "allowed_tool_labels": ["Shared Trace Tool"],
                    },
                    "trace_json": "guarded-trace-json",
                },
            ]
            session_routes_module.chat_persistence_service.get_task_trace_steps_from_task = (  # type: ignore[attr-defined]
                lambda _task: [
                    session_routes_module.chat_persistence_service.TraceStep(  # type: ignore[attr-defined]
                        id="trace-shared-governance-1",
                        type="thought",
                        content="trace governance",
                        seq=1,
                        meta={},
                    )
                ]
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-shared-trace-governance",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.chat_persistence_service.get_task_trace_steps_from_task = original_trace_loader  # type: ignore[attr-defined]

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(payload.governance.profiles, ["shared_trace_profile"])
        self.assertEqual(payload.governance.provider_sources, ["shared_trace_source"])
        self.assertEqual(payload.governance.allowed_tool_names, ["shared_trace_tool"])
        self.assertEqual(payload.governance.allowed_tool_labels, ["Shared Trace Tool"])
        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(payload.tasks[0].governance.profile, "shared_trace_profile")
        self.assertEqual(payload.tasks[0].governance.provider_source, "shared_trace_source")
        self.assertEqual(payload.tasks[0].governance.allowed_tool_names, ["shared_trace_tool"])
        self.assertEqual(payload.tasks[0].governance.allowed_tool_labels, ["Shared Trace Tool"])

    def test_build_session_export_payload_reuses_shared_task_rows_export_summary_helper_for_governance(
        self,
    ) -> None:
        session = {
            "id": "session-shared-governance-summary",
            "title": "Shared Governance Summary Session",
            "created_at": "2026-06-11T14:00:00",
            "updated_at": "2026-06-11T14:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_export_summary_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_task_rows_export_summary",
            None,
        )
        original_summary_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_task_rows_governance_summary",
            None,
        )
        original_trace_preview_batch_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_task_rows_trace_preview_summary",
            None,
        )
        original_merge = session_routes_module.chat_persistence_service._merge_session_governance_summary
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-shared-governance-summary",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-11T14:00:00",
                    "updated_at": "2026-06-11T14:01:00",
                    "usage_json": None,
                    "governance": {
                        "profile": "planning_only",
                        "provider_source": "default",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "trace_json": None,
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "default",
                    "allowed_tool_names_json": json.dumps(["task_plan"]),
                    "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                },
            ]
            session_routes_module.chat_persistence_service._merge_session_governance_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should not merge governance row-by-row after task-row export summary is centralized in the service"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_task_rows_governance_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should reuse get_task_rows_export_summary(task_rows) instead of calling governance batch helper directly"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_task_rows_trace_preview_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should reuse get_task_rows_export_summary(task_rows) instead of calling trace preview batch helper directly"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_task_rows_export_summary = (  # type: ignore[attr-defined]
                lambda _task_rows, preview_limit=3: {
                    "tasks": [
                        {
                            "task_id": "task-shared-governance-summary",
                            "trace_step_count": 0,
                            "rag_hit_count": 0,
                            "trace_preview": [],
                        }
                    ],
                    "trace_step_count": 0,
                    "rag_hit_count": 0,
                    "governance": {
                        "profiles": ["shared_summary_profile"],
                        "provider_sources": ["shared_summary_source"],
                        "allowed_tool_names": ["shared_summary_tool"],
                        "allowed_tool_labels": ["Shared Summary Tool"],
                    },
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-shared-governance-summary",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.chat_persistence_service._merge_session_governance_summary = original_merge  # type: ignore[attr-defined]
            if original_export_summary_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_task_rows_export_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_task_rows_export_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_task_rows_export_summary = original_export_summary_helper  # type: ignore[attr-defined]
            if original_summary_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_task_rows_governance_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_task_rows_governance_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_task_rows_governance_summary = original_summary_helper  # type: ignore[attr-defined]
            if original_trace_preview_batch_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_task_rows_trace_preview_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_task_rows_trace_preview_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_task_rows_trace_preview_summary = original_trace_preview_batch_helper  # type: ignore[attr-defined]

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(payload.governance.profiles, ["shared_summary_profile"])
        self.assertEqual(payload.governance.provider_sources, ["shared_summary_source"])
        self.assertEqual(payload.governance.allowed_tool_names, ["shared_summary_tool"])
        self.assertEqual(payload.governance.allowed_tool_labels, ["Shared Summary Tool"])

    def test_session_route_module_does_not_expose_dead_clone_builders(self) -> None:
        self.assertFalse(
            hasattr(
                session_routes_module,
                "_build_session_export_task_governance_summary_from_clone",
            )
        )
        self.assertFalse(
            hasattr(
                session_routes_module,
                "_build_session_export_governance_summary_from_clone",
            )
        )

    def test_session_route_module_does_not_expose_dead_local_clone_helpers(self) -> None:
        self.assertFalse(hasattr(session_routes_module, "_clone_task_governance"))
        self.assertFalse(
            hasattr(session_routes_module, "_clone_session_governance_summary")
        )

    def test_session_route_module_does_not_expose_dead_trace_json_governance_collector(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(session_routes_module, "_collect_task_governance_from_trace_json")
        )

    def test_session_route_module_does_not_expose_dead_task_row_governance_collector(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(session_routes_module, "_collect_task_governance_from_task_row")
        )

    def test_session_route_module_does_not_expose_dead_trace_steps_governance_collector(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(session_routes_module, "_collect_task_governance_from_trace_steps")
        )

    def test_session_route_module_does_not_expose_dead_trace_step_title_helper(
        self,
    ) -> None:
        self.assertFalse(hasattr(session_routes_module, "_trace_step_title"))

    def test_session_route_module_does_not_expose_dead_session_export_assembly_helpers(
        self,
    ) -> None:
        self.assertFalse(hasattr(session_routes_module, "_build_session_task_summary"))
        self.assertFalse(
            hasattr(session_routes_module, "_collect_session_governance_summary")
        )

    def test_session_route_module_does_not_expose_dead_session_export_governance_helpers(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(
                session_routes_module,
                "_build_session_export_task_governance_summary_from_dict",
            )
        )
        self.assertFalse(
            hasattr(
                session_routes_module,
                "_build_session_export_governance_summary_from_dict",
            )
        )
        self.assertFalse(
            hasattr(session_routes_module, "_collect_task_governance_from_task")
        )

    def test_session_route_module_does_not_expose_dead_session_usage_blob_parser(
        self,
    ) -> None:
        self.assertFalse(hasattr(session_routes_module, "_parse_usage_blob"))

    def test_build_session_export_payload_trusts_service_task_governance_rows(
        self,
    ) -> None:
        session = {
            "id": "session-export-governance-columns",
            "title": "Governance Columns Session",
            "created_at": "2026-06-10T10:00:00",
            "updated_at": "2026-06-10T10:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        try:
            self.assertFalse(
                hasattr(
                    session_routes_module.chat_persistence_service,
                    "_extract_task_governance_from_task_with_parsed_trace_steps",
                )
            )
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 2,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-columns-1",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-10T10:00:00",
                    "updated_at": "2026-06-10T10:01:00",
                    "usage_json": None,
                    "governance": {
                        "profile": "planning_only",
                        "provider_source": "default",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "trace_json": None,
                    "tool_registry_profile": "poisoned_profile",
                    "tool_registry_provider_source": "poisoned_source",
                    "allowed_tool_names_json": json.dumps(["poisoned_tool"]),
                    "allowed_tool_labels_json": json.dumps(["Poisoned Tool"]),
                },
                {
                    "id": "task-columns-2",
                    "prompt": "task two",
                    "status": "completed",
                    "created_at": "2026-06-10T10:02:00",
                    "updated_at": "2026-06-10T10:03:00",
                    "usage_json": None,
                    "governance": {
                        "profile": "retrieval_only",
                        "provider_source": "suite_a",
                        "allowed_tool_names": ["task_retrieve"],
                        "allowed_tool_labels": ["Knowledge Retrieval"],
                    },
                    "trace_json": None,
                    "tool_registry_profile": "poisoned_profile_2",
                    "tool_registry_provider_source": "poisoned_source_2",
                    "allowed_tool_names_json": json.dumps(["poisoned_tool_2"]),
                    "allowed_tool_labels_json": json.dumps(["Poisoned Tool 2"]),
                },
            ]
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-governance-columns",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(
            payload.governance.profiles,
            ["planning_only", "retrieval_only"],
        )
        self.assertEqual(payload.governance.provider_sources, ["default", "suite_a"])
        self.assertEqual(
            payload.governance.allowed_tool_labels,
            ["Knowledge Retrieval", "Task Planner"],
        )
        self.assertEqual(len(payload.tasks), 2)
        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(payload.tasks[0].governance.profile, "planning_only")
        self.assertEqual(payload.tasks[0].governance.provider_source, "default")
        self.assertEqual(payload.tasks[0].governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(payload.tasks[0].governance.allowed_tool_labels, ["Task Planner"])
        self.assertIsNotNone(payload.tasks[1].governance)
        assert payload.tasks[1].governance is not None
        self.assertEqual(payload.tasks[1].governance.profile, "retrieval_only")
        self.assertEqual(payload.tasks[1].governance.provider_source, "suite_a")
        self.assertEqual(payload.tasks[1].governance.allowed_tool_names, ["task_retrieve"])
        self.assertEqual(
            payload.tasks[1].governance.allowed_tool_labels,
            ["Knowledge Retrieval"],
        )

    def test_build_session_export_payload_passes_raw_governance_dicts_to_export_models(
        self,
    ) -> None:
        session = {
            "id": "session-export-raw-governance",
            "title": "Raw Governance Session",
            "created_at": "2026-06-18T10:30:00",
            "updated_at": "2026-06-18T10:35:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )
        original_task_summary = session_routes_module.SessionExportTaskSummary
        original_json_response = session_routes_module.SessionExportJsonResponse
        captured: dict[str, list[object] | object | None] = {
            "tasks": [],
            "payload_governance": None,
        }
        task_governance = {
            "profile": "planning_only",
            "provider_source": "planning_suite",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        session_governance = {
            "profiles": ["planning_only"],
            "provider_sources": ["planning_suite"],
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-export-raw-governance",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-18T10:30:00",
                    "updated_at": "2026-06-18T10:31:00",
                    "usage_json": None,
                    "trace_json": None,
                    "governance": task_governance,
                }
            ]
            session_routes_module.SessionExportTaskSummary = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "session export route should reuse SessionExportJsonResponse(tasks=...) with shared response summary instead of manually constructing SessionExportTaskSummary(...)"
                )
            )
            session_routes_module.SessionExportJsonResponse = (
                lambda **kwargs: captured.__setitem__("payload_governance", kwargs["governance"])
                or captured.__setitem__("tasks", kwargs["tasks"])
                or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "tasks": [
                        {
                            "id": "task-export-raw-governance",
                            "prompt": "task one",
                            "status": "completed",
                            "status_normalized": "completed",
                            "status_label": "Completed",
                            "status_rank": 3,
                            "created_at": "2026-06-18T10:30:00",
                            "updated_at": "2026-06-18T10:31:00",
                            "usage": None,
                            "trace_step_count": 0,
                            "rag_hit_count": 0,
                            "trace_preview": [],
                            "governance": task_governance,
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "governance": session_governance,
                    "messages": [],
                }
            )
            session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-export-raw-governance",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.SessionExportTaskSummary = original_task_summary
            session_routes_module.SessionExportJsonResponse = original_json_response
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        assert isinstance(captured["tasks"], list)
        self.assertEqual(captured["tasks"][0]["governance"], task_governance)
        self.assertEqual(captured["payload_governance"], session_governance)

    def test_session_route_module_no_longer_exposes_dead_task_status_meta_helper(
        self,
    ) -> None:
        self.assertFalse(hasattr(session_routes_module, "_task_status_meta"))

    def test_session_route_module_does_not_expose_dead_plain_clone_dict_helper(
        self,
    ) -> None:
        self.assertFalse(hasattr(session_routes_module, "_plain_clone_dict"))

    def test_build_session_export_payload_no_longer_reuses_dead_task_status_meta_helper(
        self,
    ) -> None:
        session = {
            "id": "session-export-task-status-helper",
            "title": "Task Status Helper Session",
            "created_at": "2026-06-18T11:20:00",
            "updated_at": "2026-06-18T11:25:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_session_export_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )
        original_payload_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_task_rows_session_export_summary",
            None,
        )
        original_task_summary = session_routes_module.SessionExportTaskSummary
        original_json_response = session_routes_module.SessionExportJsonResponse
        cloned_governance = {
            "profile": "planning_only",
            "provider_source": "planning_suite",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        captured: list[dict[str, object]] = []
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-export-task-status-helper",
                    "prompt": "poisoned prompt",
                    "status": "poisoned_status",
                    "created_at": "poisoned_created_at",
                    "updated_at": "poisoned_updated_at",
                    "usage_json": None,
                    "trace_json": None,
                    "governance": {
                        "profile": "poisoned_profile",
                        "provider_source": "poisoned_source",
                        "allowed_tool_names": ["poisoned_tool"],
                        "allowed_tool_labels": ["Poisoned Tool"],
                    },
                }
            ]
            session_routes_module.chat_persistence_service.get_task_rows_session_export_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should reuse get_session_export_response_summary(...) instead of calling get_task_rows_session_export_summary(task_rows) directly"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "tasks": [
                        {
                            "id": "task-export-task-status-helper",
                            "prompt": "task one",
                            "status": "completed",
                            "status_normalized": "normalized::completed",
                            "status_label": "label::completed",
                            "status_rank": 3,
                            "created_at": "2026-06-18T11:20:00",
                            "updated_at": "2026-06-18T11:21:00",
                            "usage": None,
                            "trace_step_count": 0,
                            "rag_hit_count": 0,
                            "trace_preview": [],
                            "governance": cloned_governance,
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            session_routes_module.SessionExportTaskSummary = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "session export route should reuse SessionExportJsonResponse(tasks=...) with shared response summary instead of manually constructing SessionExportTaskSummary(...)"
                )
            )
            session_routes_module.SessionExportJsonResponse = (
                lambda **kwargs: captured.extend(kwargs["tasks"]) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-export-task-status-helper",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            if original_session_export_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_session_export_helper  # type: ignore[attr-defined]
            if original_payload_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_task_rows_session_export_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_task_rows_session_export_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_task_rows_session_export_summary = original_payload_helper  # type: ignore[attr-defined]
            session_routes_module.SessionExportTaskSummary = original_task_summary
            session_routes_module.SessionExportJsonResponse = original_json_response

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["governance"], cloned_governance)
        self.assertEqual(captured[0]["prompt"], "task one")
        self.assertEqual(captured[0]["status"], "completed")
        self.assertEqual(captured[0]["status_normalized"], "normalized::completed")
        self.assertEqual(captured[0]["status_label"], "label::completed")

    def test_build_session_export_payload_reuses_shared_session_export_response_summary_helper_for_outward_models(
        self,
    ) -> None:
        session = {
            "id": "session-export-outward-models",
            "title": "Outward Models Session",
            "created_at": "2026-06-23T10:00:00",
            "updated_at": "2026-06-23T10:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )
        original_session_model = session_routes_module.SessionResponse
        original_usage_summary_model = session_routes_module.SessionUsageSummaryResponse
        original_task_summary_model = session_routes_module.SessionExportTaskSummary
        original_stats_model = session_routes_module.SessionExportStats
        original_message_model = session_routes_module.SessionExportMessage
        original_json_response = session_routes_module.SessionExportJsonResponse
        shared_message = original_message_model(
            id="message-1",
            task_id=None,
            role="assistant",
            content="hello",
            created_at="2026-06-23T10:01:00",
        )
        shared_task = original_task_summary_model(
            id="task-1",
            prompt="shared task model",
            status="completed",
            status_normalized="completed",
            status_label="Completed",
            status_rank=3,
            created_at="2026-06-23T10:00:00",
            updated_at="2026-06-23T10:02:00",
            usage=None,
            trace_step_count=0,
            rag_hit_count=0,
            trace_preview=[],
            governance=None,
        )
        captured: list[dict[str, object]] = []
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "tasks": [shared_task],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [shared_message],
                }
            )
            session_routes_module.SessionResponse = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "session export route should reuse SessionExportJsonResponse(session=...) with the raw session summary instead of manually constructing SessionResponse(...)"
                )
            )
            session_routes_module.SessionUsageSummaryResponse = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "session export route should reuse SessionExportJsonResponse(...) with shared response summary instead of manually constructing SessionUsageSummaryResponse(...)"
                )
            )
            session_routes_module.SessionExportTaskSummary = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "session export route should reuse SessionExportJsonResponse(...) with shared response summary instead of manually constructing SessionExportTaskSummary(...)"
                )
            )
            session_routes_module.SessionExportStats = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "session export route should reuse SessionExportJsonResponse(...) with shared response summary instead of manually constructing SessionExportStats(...)"
                )
            )
            session_routes_module.SessionExportMessage = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "session export route should reuse SessionExportJsonResponse(...) with shared response summary instead of manually constructing SessionExportMessage(...)"
                )
            )
            session_routes_module.SessionExportJsonResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-export-outward-models",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]
            session_routes_module.SessionResponse = original_session_model
            session_routes_module.SessionUsageSummaryResponse = original_usage_summary_model
            session_routes_module.SessionExportTaskSummary = original_task_summary_model
            session_routes_module.SessionExportStats = original_stats_model
            session_routes_module.SessionExportMessage = original_message_model
            session_routes_module.SessionExportJsonResponse = original_json_response

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["session"]["id"], "session-export-outward-models")
        self.assertEqual(captured[0]["usage_summary"]["tasks_total"], 1)
        self.assertEqual(captured[0]["stats"]["task_count"], 1)
        self.assertIs(captured[0]["messages"][0], shared_message)
        self.assertIs(captured[0]["tasks"][0], shared_task)

    def test_build_session_export_payload_reuses_shared_session_export_response_summary_helper_for_session_governance(
        self,
    ) -> None:
        session = {
            "id": "session-export-summary-clone-helper",
            "title": "Summary Clone Helper Session",
            "created_at": "2026-06-18T12:20:00",
            "updated_at": "2026-06-18T12:25:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )
        original_payload_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_payload_summary",
            None,
        )
        original_json_response = session_routes_module.SessionExportJsonResponse
        cloned_governance = {
            "profiles": ["planning_only"],
            "provider_sources": ["planning_suite"],
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        captured: list[dict[str, object]] = []
        try:
            self.assertFalse(hasattr(session_routes_module, "_plain_clone_dict"))
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []
            session_routes_module.chat_persistence_service.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should reuse get_session_export_response_summary(...) for governance instead of calling get_session_export_payload_summary(...) directly"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": {
                        "tasks_total": 0,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "tasks": [],
                    "stats": {
                        "task_count": 0,
                        "message_count": 0,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "governance": cloned_governance,
                    "messages": [],
                }
            )
            session_routes_module.SessionExportJsonResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-export-summary-clone-helper",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]
            if original_payload_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_payload_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_payload_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]
            session_routes_module.SessionExportJsonResponse = original_json_response

        self.assertEqual(len(captured), 1)
        self.assertIs(captured[0]["governance"], cloned_governance)

    def test_build_session_export_payload_reuses_shared_task_rows_session_export_summary_helper_for_usage(
        self,
    ) -> None:
        session = {
            "id": "session-export-usage-parser",
            "title": "Usage Parser Session",
            "created_at": "2026-06-16T15:00:00",
            "updated_at": "2026-06-16T15:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_session_export_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )
        original_payload_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_task_rows_session_export_summary",
            None,
        )
        original_usage_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_task_usage_from_task",
            None,
        )
        original_parser = session_routes_module.chat_persistence_service._parse_usage_json_blob  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-usage-parser",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-16T15:00:00",
                    "updated_at": "2026-06-16T15:01:00",
                    "usage_json": "usage-json-guarded",
                    "trace_json": None,
                }
            ]
            session_routes_module.chat_persistence_service._parse_usage_json_blob = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should reuse get_task_rows_session_export_summary(task_rows) instead of the private usage json parser"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_task_usage_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should reuse get_task_rows_session_export_summary(task_rows) instead of calling task usage helper directly"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_task_rows_session_export_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should reuse get_session_export_response_summary(...) instead of calling get_task_rows_session_export_summary(task_rows) directly"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **kwargs: captured.append(kwargs["task_rows"][0].get("usage_json"))
                or {
                    "usage_summary": kwargs["usage_summary"],
                    "tasks": [
                        {
                            "id": "task-usage-parser",
                            "prompt": "task one",
                            "status": "completed",
                            "status_normalized": "completed",
                            "status_label": "Completed",
                            "status_rank": 3,
                            "created_at": "2026-06-16T15:00:00",
                            "updated_at": "2026-06-16T15:01:00",
                            "usage": {
                                "prompt_tokens": 18,
                                "completion_tokens": 9,
                                "cost_estimate": 0.04,
                            },
                            "trace_step_count": 0,
                            "rag_hit_count": 0,
                            "trace_preview": [],
                            "governance": None,
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-usage-parser",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.chat_persistence_service._parse_usage_json_blob = original_parser  # type: ignore[attr-defined]
            if original_session_export_helper is None:
                if hasattr(session_routes_module.chat_persistence_service, "get_session_export_response_summary"):
                    delattr(session_routes_module.chat_persistence_service, "get_session_export_response_summary")
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_session_export_helper  # type: ignore[attr-defined]
            if original_payload_helper is None:
                if hasattr(session_routes_module.chat_persistence_service, "get_task_rows_session_export_summary"):
                    delattr(session_routes_module.chat_persistence_service, "get_task_rows_session_export_summary")
            else:
                session_routes_module.chat_persistence_service.get_task_rows_session_export_summary = original_payload_helper  # type: ignore[attr-defined]
            if original_usage_helper is None:
                if hasattr(session_routes_module.chat_persistence_service, "get_task_usage_from_task"):
                    delattr(session_routes_module.chat_persistence_service, "get_task_usage_from_task")
            else:
                session_routes_module.chat_persistence_service.get_task_usage_from_task = original_usage_helper  # type: ignore[attr-defined]

        self.assertEqual(captured, ["usage-json-guarded"])
        self.assertEqual(
            payload.tasks[0].usage,
            {
                "prompt_tokens": 18,
                "completion_tokens": 9,
                "cost_estimate": 0.04,
            },
        )

    def test_build_session_export_payload_reuses_shared_task_rows_session_export_summary_helper_for_task_trace_and_stats(
        self,
    ) -> None:
        session = {
            "id": "session-export-task-trace-stats-helper",
            "title": "Task Trace Stats Helper Session",
            "created_at": "2026-06-22T13:00:00",
            "updated_at": "2026-06-22T13:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_session_export_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )
        original_payload_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_task_rows_session_export_summary",
            None,
        )
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: [
                {
                    "id": "message-1",
                    "task_id": "task-poisoned-raw-row",
                    "role": "assistant",
                    "content": "hello",
                    "created_at": "2026-06-22T13:01:00",
                }
            ]
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-poisoned-raw-row",
                    "prompt": "poisoned prompt",
                    "status": "poisoned_status",
                    "created_at": "poisoned_created_at",
                    "updated_at": "poisoned_updated_at",
                    "usage_json": None,
                    "trace_json": None,
                    "governance": {
                        "profile": "poisoned_profile",
                        "provider_source": "poisoned_source",
                        "allowed_tool_names": ["poisoned_tool"],
                        "allowed_tool_labels": ["Poisoned Tool"],
                    },
                }
            ]
            session_routes_module.chat_persistence_service.get_task_rows_session_export_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should reuse get_session_export_response_summary(...) instead of calling get_task_rows_session_export_summary(task_rows) directly"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **kwargs: {
                    "usage_summary": kwargs["usage_summary"],
                    "tasks": [
                        {
                            "id": "task-nested-summary",
                            "prompt": "shared summary prompt",
                            "status": "completed",
                            "status_normalized": "normalized::completed",
                            "status_label": "label::completed",
                            "status_rank": 11,
                            "created_at": "2026-06-22T13:02:00",
                            "updated_at": "2026-06-22T13:03:00",
                            "usage": None,
                            "trace_step_count": 7,
                            "rag_hit_count": 4,
                            "trace_preview": [
                                {
                                    "id": "preview-nested-1",
                                    "seq": 7,
                                    "type": "tool_result",
                                    "title": "tool result",
                                    "content_excerpt": "shared preview",
                                }
                            ],
                            "governance": {
                                "profile": "planning_only",
                                "provider_source": "suite_a",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner"],
                            },
                        }
                    ],
                    "stats": {
                        "task_count": 9,
                        "message_count": 1,
                        "trace_step_count": 19,
                        "rag_hit_count": 13,
                    },
                    "governance": {
                        "profiles": ["planning_only"],
                        "provider_sources": ["suite_a"],
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "messages": kwargs["message_rows"],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-task-trace-stats-helper",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            if original_session_export_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_session_export_helper  # type: ignore[attr-defined]
            if original_payload_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_task_rows_session_export_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_task_rows_session_export_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_task_rows_session_export_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.stats.task_count, 9)
        self.assertEqual(payload.stats.message_count, 1)
        self.assertEqual(payload.stats.trace_step_count, 19)
        self.assertEqual(payload.stats.rag_hit_count, 13)
        self.assertEqual(len(payload.tasks), 1)
        self.assertEqual(payload.tasks[0].id, "task-nested-summary")
        self.assertEqual(payload.tasks[0].prompt, "shared summary prompt")
        self.assertEqual(payload.tasks[0].trace_step_count, 7)
        self.assertEqual(payload.tasks[0].rag_hit_count, 4)
        self.assertEqual(payload.tasks[0].trace_preview[0].id, "preview-nested-1")
        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(payload.tasks[0].governance.profile, "planning_only")

    def test_build_session_export_payload_reuses_shared_session_export_response_summary_helper(
        self,
    ) -> None:
        session = {
            "id": "session-export-payload-helper",
            "title": "Payload Helper Session",
            "created_at": "2026-06-22T15:40:00",
            "updated_at": "2026-06-22T15:45:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )
        original_payload_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_payload_summary",
            None,
        )
        captured: list[dict[str, object]] = []
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: [
                {
                    "id": "message-1",
                    "task_id": "task-1",
                    "role": "assistant",
                    "content": "hello",
                    "created_at": "2026-06-22T15:41:00",
                }
            ]
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-raw-1",
                    "prompt": "poisoned prompt",
                    "status": "poisoned_status",
                    "created_at": "poisoned_created_at",
                    "updated_at": "poisoned_updated_at",
                    "usage_json": None,
                    "trace_json": None,
                    "governance": None,
                }
            ]
            session_routes_module.chat_persistence_service.get_session_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should reuse get_session_export_response_summary(...) instead of calling get_session_export_payload_summary(...) directly"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **kwargs: captured.append(kwargs)
                or {
                    "usage_summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 0,
                        "source_tasks_provider": 0,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "avg_total_tokens": None,
                        "avg_cost_estimate": None,
                    },
                    "tasks": [
                        {
                            "id": "task-shared-1",
                            "prompt": "shared prompt",
                            "status": "completed",
                            "status_normalized": "normalized::completed",
                            "status_label": "label::completed",
                            "status_rank": 6,
                            "created_at": "2026-06-22T15:42:00",
                            "updated_at": "2026-06-22T15:43:00",
                            "usage": None,
                            "trace_step_count": 3,
                            "rag_hit_count": 1,
                            "trace_preview": [
                                {
                                    "id": "preview-1",
                                    "seq": 3,
                                    "type": "tool_result",
                                    "title": "tool result",
                                    "content_excerpt": "preview body",
                                }
                            ],
                            "governance": {
                                "profile": "planning_only",
                                "provider_source": "suite_a",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner"],
                            },
                        }
                    ],
                    "stats": {
                        "task_count": 7,
                        "message_count": 1,
                        "trace_step_count": 9,
                        "rag_hit_count": 4,
                    },
                    "governance": {
                        "profiles": ["planning_only"],
                        "provider_sources": ["suite_a"],
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "messages": [
                        {
                            "id": "message-1",
                            "task_id": "task-1",
                            "role": "assistant",
                            "content": "hello",
                            "created_at": "2026-06-22T15:41:00",
                        }
                    ],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-export-payload-helper",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]
            if original_payload_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_payload_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_payload_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(len(captured), 1)
        self.assertEqual(
            captured[0]["usage_summary"]["tasks_total"], 1
        )
        self.assertEqual(len(captured[0]["task_rows"]), 1)
        self.assertEqual(len(captured[0]["message_rows"]), 1)
        self.assertEqual(captured[0]["preview_limit"], 3)
        self.assertEqual(payload.stats.task_count, 7)
        self.assertEqual(payload.stats.message_count, 1)
        self.assertEqual(payload.tasks[0].id, "task-shared-1")
        self.assertEqual(payload.tasks[0].trace_preview[0].id, "preview-1")
        self.assertEqual(payload.messages[0].id, "message-1")

    def test_build_session_export_payload_reuses_shared_task_rows_export_summary_helper_for_trace_preview(
        self,
    ) -> None:
        session = {
            "id": "session-export-trace-preview",
            "title": "Trace Preview Session",
            "created_at": "2026-06-17T15:00:00",
            "updated_at": "2026-06-17T15:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_task_rows_export_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_task_rows_export_summary",
            None,
        )
        original_task_rows_trace_preview_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_task_rows_trace_preview_summary",
            None,
        )
        original_trace_preview_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_task_trace_preview_summary_from_task",
            None,
        )
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-trace-preview",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-17T15:00:00",
                    "updated_at": "2026-06-17T15:01:00",
                    "usage_json": None,
                    "trace_json": "guarded-trace-json",
                    "governance": None,
                }
            ]
            session_routes_module.chat_persistence_service.get_task_trace_preview_summary_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should reuse get_task_rows_export_summary(task_rows) instead of calling per-task trace preview helpers directly"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_task_rows_trace_preview_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "session export route should reuse get_task_rows_export_summary(task_rows) instead of calling trace preview batch helper directly"
                    )
                )
            )
            session_routes_module.chat_persistence_service.get_task_rows_export_summary = (  # type: ignore[attr-defined]
                lambda _task_rows, preview_limit=3: {
                    "trace_step_count": 4,
                    "rag_hit_count": 2,
                    "tasks": [
                        {
                            "task_id": "task-trace-preview",
                            "trace_step_count": 4,
                            "rag_hit_count": 2,
                            "trace_preview": [
                                {
                                    "id": "preview-1",
                                    "seq": 4,
                                    "type": "tool_result",
                                    "title": "tool result",
                                    "content_excerpt": "preview body",
                                }
                            ],
                        }
                    ],
                    "governance": None,
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-trace-preview",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            if original_task_rows_export_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_task_rows_export_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_task_rows_export_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_task_rows_export_summary = original_task_rows_export_helper  # type: ignore[attr-defined]
            if original_task_rows_trace_preview_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_task_rows_trace_preview_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_task_rows_trace_preview_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_task_rows_trace_preview_summary = original_task_rows_trace_preview_helper  # type: ignore[attr-defined]
            if original_trace_preview_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_task_trace_preview_summary_from_task",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_task_trace_preview_summary_from_task",
                    )
            else:
                session_routes_module.chat_persistence_service.get_task_trace_preview_summary_from_task = original_trace_preview_helper  # type: ignore[attr-defined]

        self.assertEqual(payload.stats.trace_step_count, 4)
        self.assertEqual(payload.stats.rag_hit_count, 2)
        self.assertEqual(len(payload.tasks), 1)
        self.assertEqual(payload.tasks[0].trace_step_count, 4)
        self.assertEqual(payload.tasks[0].rag_hit_count, 2)
        self.assertEqual(len(payload.tasks[0].trace_preview), 1)
        self.assertEqual(payload.tasks[0].trace_preview[0].id, "preview-1")

    def test_get_session_export_response_summary_redacts_http_json_trace_preview_url_without_provider_title(
        self,
    ) -> None:
        original_payload_helper = getattr(
            chat_persistence_module,
            "get_session_export_payload_summary",
            None,
        )
        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[assignment]
                lambda **_kwargs: {
                    "usage_summary": {},
                    "tasks": [
                        {
                            "task": {
                                "id": "task-session-export-http-json-url",
                                "prompt": "check callback",
                                "status": "completed",
                                "status_normalized": "done",
                                "status_label": "Done",
                                "status_rank": 40,
                                "created_at": "2026-07-20T09:00:00",
                                "updated_at": "2026-07-20T09:01:00",
                            },
                            "usage": None,
                            "trace": {
                                "step_count": 1,
                                "rag_hit_count": 0,
                                "preview": [
                                    {
                                        "id": "preview-http-json-calc-url",
                                        "seq": 4,
                                        "type": "action",
                                        "title": "Calculator [calculator via http_json]",
                                        "content_excerpt": (
                                            "Calculator: callback "
                                            "https://provider.example/cb?"
                                            "access_token=secret-token&state=ok"
                                            "#client_secret=hidden"
                                        ),
                                    }
                                ],
                            },
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 1,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            summary = chat_persistence_module.get_session_export_response_summary(
                usage_summary={},
                task_rows=[],
                message_rows=[],
            )
        finally:
            if original_payload_helper is None:
                delattr(chat_persistence_module, "get_session_export_payload_summary")
            else:
                chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[assignment]

        serialized = json.dumps(summary, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertIn("callback", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_get_session_export_response_summary_redacts_http_json_trace_preview_title_diagnostics(
        self,
    ) -> None:
        original_payload_helper = getattr(
            chat_persistence_module,
            "get_session_export_payload_summary",
            None,
        )
        try:
            chat_persistence_module.get_session_export_payload_summary = (  # type: ignore[assignment]
                lambda **_kwargs: {
                    "usage_summary": {},
                    "tasks": [
                        {
                            "task": {
                                "id": "task-session-export-service-http-json-title",
                                "prompt": "check callback title",
                                "status": "completed",
                                "status_normalized": "done",
                                "status_label": "Done",
                                "status_rank": 40,
                                "created_at": "2026-07-20T09:00:00",
                                "updated_at": "2026-07-20T09:01:00",
                            },
                            "usage": None,
                            "trace": {
                                "step_count": 1,
                                "rag_hit_count": 0,
                                "preview": [
                                    {
                                        "id": "preview-http-json-title-diagnostic",
                                        "seq": 4,
                                        "type": "action",
                                        "title": (
                                            "Provider token=hidden "
                                            "https://provider.example/cb?"
                                            "access_token=secret-token "
                                            "[provider_status via http_json]"
                                        ),
                                        "content_excerpt": (
                                            'Provider Status: {"message":"ok"}'
                                        ),
                                    }
                                ],
                            },
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 1,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            summary = chat_persistence_module.get_session_export_response_summary(
                usage_summary={},
                task_rows=[],
                message_rows=[],
            )
        finally:
            if original_payload_helper is None:
                delattr(chat_persistence_module, "get_session_export_payload_summary")
            else:
                chat_persistence_module.get_session_export_payload_summary = original_payload_helper  # type: ignore[assignment]

        serialized = json.dumps(summary, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_build_session_export_payload_redacts_http_json_trace_preview_url_without_provider_title(
        self,
    ) -> None:
        session = {
            "id": "session-export-route-http-json-url",
            "title": "HTTP JSON Route Preview",
            "created_at": "2026-07-20T09:00:00",
            "updated_at": "2026-07-20T09:01:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )
        try:
            usage_summary = {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_usage_summary = (
                lambda *_args, **_kwargs: usage_summary
            )
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": usage_summary,
                    "tasks": [
                        {
                            "id": "task-session-export-route-http-json-url",
                            "prompt": "check callback",
                            "status": "completed",
                            "status_normalized": "done",
                            "status_label": "Done",
                            "status_rank": 40,
                            "created_at": "2026-07-20T09:00:00",
                            "updated_at": "2026-07-20T09:01:00",
                            "usage": None,
                            "trace_step_count": 1,
                            "rag_hit_count": 0,
                            "trace_preview": [
                                {
                                    "id": "preview-route-http-json-calc-url",
                                    "seq": 4,
                                    "type": "action",
                                    "title": "Calculator [calculator via http_json]",
                                    "content_excerpt": (
                                        "Calculator: callback "
                                        "https://provider.example/cb?"
                                        "access_token=secret-token&state=ok"
                                        "#client_secret=hidden"
                                    ),
                                }
                            ],
                            "governance": None,
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 1,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-export-route-http-json-url",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        serialized = payload.model_dump_json()
        self.assertIn("[redacted]", serialized)
        self.assertIn("callback", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_build_session_export_payload_redacts_http_json_trace_preview_title_diagnostics(
        self,
    ) -> None:
        session = {
            "id": "session-export-route-http-json-title",
            "title": "HTTP JSON Route Preview Title",
            "created_at": "2026-07-20T09:00:00",
            "updated_at": "2026-07-20T09:01:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )
        try:
            usage_summary = {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_usage_summary = (
                lambda *_args, **_kwargs: usage_summary
            )
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": usage_summary,
                    "tasks": [
                        {
                            "id": "task-session-export-route-http-json-title",
                            "prompt": "check callback title",
                            "status": "completed",
                            "status_normalized": "done",
                            "status_label": "Done",
                            "status_rank": 40,
                            "created_at": "2026-07-20T09:00:00",
                            "updated_at": "2026-07-20T09:01:00",
                            "usage": None,
                            "trace_step_count": 1,
                            "rag_hit_count": 0,
                            "trace_preview": [
                                {
                                    "id": "preview-route-http-json-title",
                                    "seq": 4,
                                    "type": "action",
                                    "title": (
                                        "Provider token=hidden "
                                        "https://provider.example/cb?"
                                        "access_token=secret-token "
                                        "[provider_status via http_json]"
                                    ),
                                    "content_excerpt": (
                                        'Provider Status: {"message":"ok"}'
                                    ),
                                }
                            ],
                            "governance": None,
                        }
                    ],
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 1,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-export-route-http-json-title",
            )
            markdown = session_routes_module._build_session_export_markdown(payload)  # type: ignore[attr-defined]
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        serialized = payload.model_dump_json()
        combined = f"{serialized}\n{markdown}"
        self.assertIn("[redacted]", combined)
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("secret-token", combined)

    def test_build_session_export_payload_redacts_http_json_message_content(
        self,
    ) -> None:
        session = {
            "id": "session-export-route-http-json-message",
            "title": "HTTP JSON Route Message",
            "created_at": "2026-07-20T10:00:00",
            "updated_at": "2026-07-20T10:01:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_response_helper = getattr(
            session_routes_module.chat_persistence_service,
            "get_session_export_response_summary",
            None,
        )
        try:
            usage_summary = {
                "tasks_total": 0,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_usage_summary = (
                lambda *_args, **_kwargs: usage_summary
            )
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda **_kwargs: {
                    "usage_summary": usage_summary,
                    "tasks": [],
                    "stats": {
                        "task_count": 0,
                        "message_count": 1,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "governance": None,
                    "messages": [
                        {
                            "id": "message-session-export-http-json",
                            "task_id": None,
                            "role": "assistant",
                            "content": (
                                "Provider Status [provider_status via http_json] "
                                "callback https://provider.example/cb?"
                                "access_token=secret-token#client_secret=hidden "
                                "Bearer secret-token"
                            ),
                            "created_at": "2026-07-20T10:01:00",
                        }
                    ],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-export-route-http-json-message",
            )
            markdown = session_routes_module._build_session_export_markdown(payload)  # type: ignore[attr-defined]
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            if original_response_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "get_session_export_response_summary",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "get_session_export_response_summary",
                    )
            else:
                session_routes_module.chat_persistence_service.get_session_export_response_summary = original_response_helper  # type: ignore[attr-defined]

        combined = f"{payload.model_dump_json()}\n{markdown}"
        self.assertIn("[redacted]", combined)
        self.assertIn("callback", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("client_secret", combined)
        self.assertNotIn("secret-token", combined)
        self.assertNotIn("Bearer", combined)

    def test_stream_running_task_reconnect_reuses_shared_task_usage_helper_for_done_event(
        self,
    ) -> None:
        original_get_settings = task_routes_module.get_settings
        original_get_task = task_routes_module.get_task
        original_usage_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_usage_from_task",
            None,
        )
        original_parser = task_routes_module.chat_persistence_service._parse_usage_json_blob  # type: ignore[attr-defined]
        original_delta_snapshot_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_snapshot_from_task",
            None,
        )
        captured: list[object] = []
        try:
            task_routes_module.get_settings = lambda: SimpleNamespace(
                stream_reconnect_poll_fast_sec=0.05,
                stream_reconnect_poll_max_sec=0.5,
                stream_reconnect_heartbeat_interval_sec=1.0,
            )
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-reconnect-usage-helper",
                "session_id": "session-reconnect-usage-helper",
                "status": "completed",
                "usage_json": "usage-json-guarded",
                "trace_json": "guarded-trace-json",
            }
            task_routes_module.chat_persistence_service._parse_usage_json_blob = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "reconnect done event should reuse get_task_usage_from_task(task) instead of the private usage json parser"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_usage_from_task = (  # type: ignore[attr-defined]
                lambda task: captured.append(task.get("usage_json"))
                or {
                    "prompt_tokens": 55,
                    "completion_tokens": 34,
                    "cost_estimate": 0.08,
                }
            )
            task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = (  # type: ignore[attr-defined]
                lambda _task, after_seq=0, limit=200: (
                    [],
                    after_seq,
                    False,
                    7,
                    "fallback::guarded-trace-json",
                )
            )

            async def collect_events() -> list[str]:
                events: list[str] = []
                async for event in task_routes_module.stream_running_task_reconnect(
                    "task-reconnect-usage-helper",
                    "user-reconnect-usage-helper",
                ):
                    events.append(event)
                return events

            events = asyncio.run(collect_events())
        finally:
            task_routes_module.get_settings = original_get_settings
            task_routes_module.get_task = original_get_task
            task_routes_module.chat_persistence_service._parse_usage_json_blob = original_parser  # type: ignore[attr-defined]
            if original_usage_helper is None:
                if hasattr(task_routes_module.chat_persistence_service, "get_task_usage_from_task"):
                    delattr(task_routes_module.chat_persistence_service, "get_task_usage_from_task")
            else:
                task_routes_module.chat_persistence_service.get_task_usage_from_task = original_usage_helper  # type: ignore[attr-defined]
            if original_delta_snapshot_loader is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_snapshot_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_snapshot_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = original_delta_snapshot_loader  # type: ignore[attr-defined]

        self.assertEqual(captured, ["usage-json-guarded"])
        done_event = next(event for event in events if event.startswith("event: done"))
        self.assertIn('"prompt_tokens": 55', done_event)
        self.assertIn('"completion_tokens": 34', done_event)

    def test_build_session_export_markdown_includes_governance_summary(self) -> None:
        session = {
            "id": "session-export-governance-md",
            "title": "Governance Session",
            "created_at": "2026-06-05T10:00:00",
            "updated_at": "2026-06-05T10:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-md-1",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-05T10:00:00",
                    "updated_at": "2026-06-05T10:01:00",
                    "usage_json": None,
                    "governance": {
                        "profile": "calculator_only",
                        "provider_source": "default",
                        "allowed_tool_names": ["calc_eval"],
                        "allowed_tool_labels": ["calc_eval"],
                    },
                    "trace_json": json.dumps(
                        [
                            {
                                "id": "trace-md-1",
                                "type": "thought",
                                "content": "calc only",
                                "seq": 1,
                                "meta": {
                                    "tool_registry_profile": "calculator_only",
                                    "tool_registry_provider_source": "default",
                                    "allowed_tool_names": ["calc_eval"],
                                    "allowed_tool_labels": ["calc_eval"],
                                },
                            }
                        ]
                    ),
                },
            ]
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-governance",
            )
            markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
                payload,
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks

        self.assertIn("## Tool Registry Governance", markdown)
        self.assertIn("- Profiles: calculator_only", markdown)
        self.assertIn("- Provider Sources: default", markdown)
        self.assertIn("- Allowed Tools: Calculator", markdown)

    def test_build_session_export_markdown_includes_persisted_governance_summary(self) -> None:
        session = {
            "id": "session-export-governance-columns-md",
            "title": "Governance Columns Session",
            "created_at": "2026-06-10T10:00:00",
            "updated_at": "2026-06-10T10:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-columns-md-1",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-10T10:00:00",
                    "updated_at": "2026-06-10T10:01:00",
                    "usage_json": None,
                    "governance": {
                        "profile": "calculator_only",
                        "provider_source": "default",
                        "allowed_tool_names": ["calc_eval"],
                        "allowed_tool_labels": ["calc_eval"],
                    },
                    "trace_json": None,
                    "tool_registry_profile": "calculator_only",
                    "tool_registry_provider_source": "default",
                    "allowed_tool_names_json": json.dumps(["calc_eval"]),
                    "allowed_tool_labels_json": json.dumps(["calc_eval"]),
                },
            ]
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-governance-columns",
            )
            markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
                payload,
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks

        self.assertIn("## Tool Registry Governance", markdown)
        self.assertIn("- Profiles: calculator_only", markdown)
        self.assertIn("- Provider Sources: default", markdown)
        self.assertIn("- Allowed Tools: Calculator", markdown)
        self.assertIn("- Tool Registry Profile: calculator_only", markdown)
        self.assertIn("- Tool Registry Source: default", markdown)

    def test_build_session_export_markdown_preserves_selected_source_override_label_for_persisted_governance_summary(
        self,
    ) -> None:
        session = {
            "id": "session-export-governance-columns-suite-md",
            "title": "Governance Columns Suite Session",
            "created_at": "2026-06-30T10:00:00",
            "updated_at": "2026-06-30T10:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-columns-suite-md-1",
                    "prompt": "suite task one",
                    "status": "completed",
                    "created_at": "2026-06-30T10:00:00",
                    "updated_at": "2026-06-30T10:01:00",
                    "usage_json": None,
                    "governance": {
                        "profile": "calculator_only",
                        "provider_source": "calculator_suite",
                        "allowed_tool_names": ["calc_eval"],
                        "allowed_tool_labels": ["calc_eval"],
                    },
                    "trace_json": None,
                    "tool_registry_profile": "calculator_only",
                    "tool_registry_provider_source": "calculator_suite",
                    "allowed_tool_names_json": json.dumps(["calc_eval"]),
                    "allowed_tool_labels_json": json.dumps(["calc_eval"]),
                },
            ]
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-session-governance-columns-suite",
            )
            markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
                payload,
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks

        self.assertIn("## Tool Registry Governance", markdown)
        self.assertIn("- Profiles: calculator_only", markdown)
        self.assertIn("- Provider Sources: calculator_suite", markdown)
        self.assertIn("- Allowed Tools: Calculator Suite", markdown)
        self.assertIn("- Tool Registry Profile: calculator_only", markdown)
        self.assertIn("- Tool Registry Source: calculator_suite", markdown)

    def test_build_session_export_markdown_uses_productized_trace_preview_titles_for_real_tools(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-06-29T12:00:00",
            session=session_routes_module.SessionResponse(
                id="session-productized-trace-preview",
                title="Productized Trace Preview Session",
                created_at="2026-06-29T11:59:00",
                updated_at="2026-06-29T12:00:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-productized-trace-preview",
                    prompt="Search the provider index",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-06-29T11:59:30",
                    updated_at="2026-06-29T12:00:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-provider-search",
                            seq=3,
                            type="action",
                            title="Provider Search [provider_search · knowledge_retrieval]",
                            content_excerpt='Provider Search: {"documents_total":2}',
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            'seq=3 · Provider Search [provider_search · knowledge_retrieval] · Retrieved 2 documents.',
            markdown,
        )
        self.assertNotIn('Provider Search: {"documents_total":2}', markdown)
        self.assertNotIn("seq=3 · action · Provider Search", markdown)

    def test_build_session_export_markdown_preserves_safe_output_policy_values_in_trace_preview_excerpt(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-06-30T18:00:00",
            session=session_routes_module.SessionResponse(
                id="session-productized-trace-preview-output",
                title="Productized Trace Preview Output Session",
                created_at="2026-06-30T17:59:00",
                updated_at="2026-06-30T18:00:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-productized-trace-preview-output",
                    prompt="Search the provider index with request id",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-06-30T17:59:30",
                    updated_at="2026-06-30T18:00:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-provider-search-output",
                            seq=4,
                            type="action",
                            title="Provider Search [provider_search · knowledge_retrieval]",
                            content_excerpt='Tool done: Provider Search Preview: {"documents_total":2} Output: {"documents_total":2,"request_id":"req-1"}',
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            'seq=4 · Provider Search [provider_search · knowledge_retrieval] · Retrieved 2 documents (request id req-1). Preview: {"documents_total":2} Output: {"documents_total":2,"request_id":"req-1"}',
            markdown,
        )
        self.assertNotIn("Tool done: Provider Search", markdown)

    def test_build_session_export_markdown_redacts_http_json_message_content(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-22T12:20:00",
            session=session_routes_module.SessionResponse(
                id="session-markdown-message-redact",
                title="Markdown Message Redact Session",
                created_at="2026-07-22T12:19:00",
                updated_at="2026-07-22T12:20:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=0,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=0,
                message_count=1,
                trace_step_count=0,
                rag_hit_count=0,
            ),
            messages=[
                session_routes_module.SessionExportMessage(
                    id="message-session-markdown-http-json",
                    task_id=None,
                    role="assistant",
                    content=(
                        "Provider Search [provider_search via http_json] "
                        "failed response_path=$.data.access_token "
                        "callback https://provider.example/cb?"
                        "access_token=secret-token#client_secret=hidden "
                        "Bearer secret-token"
                    ),
                    created_at="2026-07-22T12:19:30",
                )
            ],
            tasks=[],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn("[redacted]", markdown)
        self.assertIn("response_path=$.data.[redacted]", markdown)
        self.assertNotIn("response_path=$.data.access_token", markdown)
        self.assertNotIn("access_token", markdown)
        self.assertNotIn("client_secret", markdown)
        self.assertNotIn("Bearer", markdown)
        self.assertNotIn("secret-token", markdown)

    def test_build_session_export_markdown_redacts_http_json_generic_trace_preview_excerpt(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-22T12:25:00",
            session=session_routes_module.SessionResponse(
                id="session-markdown-preview-redact",
                title="Markdown Preview Redact Session",
                created_at="2026-07-22T12:24:00",
                updated_at="2026-07-22T12:25:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-session-markdown-preview-redact",
                    prompt="export sensitive generic preview",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-22T12:24:30",
                    updated_at="2026-07-22T12:25:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-session-markdown-generic-http-json",
                            seq=8,
                            type="observation",
                            title="Tool observation",
                            content_excerpt=(
                                "Tool done: Provider Status "
                                "response_path=$.data.access_token "
                                "callback https://provider.example/cb?"
                                "access_token=secret-token#client_secret=hidden "
                                "Bearer secret-token"
                            ),
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn("[redacted]", markdown)
        self.assertIn("response_path=$.data.[redacted]", markdown)
        self.assertNotIn("response_path=$.data.access_token", markdown)
        self.assertNotIn("access_token", markdown)
        self.assertNotIn("client_secret", markdown)
        self.assertNotIn("Bearer", markdown)
        self.assertNotIn("secret-token", markdown)

    def test_build_session_export_markdown_sanitizes_nested_http_json_preview_excerpt(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-17T10:45:00",
            session=session_routes_module.SessionResponse(
                id="session-nested-http-json-preview",
                title="Nested HTTP JSON Preview Session",
                created_at="2026-07-17T10:44:00",
                updated_at="2026-07-17T10:45:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-nested-http-json-preview",
                    prompt="Check provider status",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-17T10:44:30",
                    updated_at="2026-07-17T10:45:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-nested-provider-status",
                            seq=5,
                            type="action",
                            title="Provider Status [provider_status]",
                            content_excerpt=(
                                'Tool done: Provider Status Preview: {"status":"ready",'
                                '"nested":{"access_token":"hidden"},'
                                '"request_id":"Bearer secret-token"} '
                                'Output: {"status":"ready",'
                                '"nested":{"api_key":"hidden"},'
                                '"request_id":"Bearer secret-token"}'
                            ),
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            'seq=5 · Provider Status [provider_status] · Preview: {"status":"ready","nested":{"access_token":"[redacted]"}} Output: {"status":"ready","nested":{"api_key":"[redacted]"}}',
            markdown,
        )
        self.assertNotIn("Tool done: Provider Status", markdown)
        self.assertNotIn("hidden", markdown)
        self.assertNotIn("Bearer", markdown)
        self.assertNotIn("secret-token", markdown)

    def test_build_session_export_markdown_redacts_malformed_http_json_preview_excerpt(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-17T10:48:00",
            session=session_routes_module.SessionResponse(
                id="session-malformed-http-json-preview",
                title="Malformed HTTP JSON Preview Session",
                created_at="2026-07-17T10:47:00",
                updated_at="2026-07-17T10:48:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-malformed-http-json-preview",
                    prompt="Check provider status with malformed preview",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-17T10:47:30",
                    updated_at="2026-07-17T10:48:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-malformed-provider-status",
                            seq=6,
                            type="action",
                            title="Provider Status [provider_status]",
                            content_excerpt=(
                                "Tool done: Provider Status Preview: "
                                "status=ready token=hidden "
                                "query_params.access_token Bearer secret-token"
                            ),
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "status=ready [redacted] [redacted] [redacted]",
            markdown,
        )
        self.assertNotIn("token=hidden", markdown)
        self.assertNotIn("access_token", markdown)
        self.assertNotIn("Bearer", markdown)
        self.assertNotIn("secret-token", markdown)

    def test_build_session_export_markdown_includes_provider_kb_for_real_documents_total_preview(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-16T10:00:00",
            session=session_routes_module.SessionResponse(
                id="session-provider-documents-kb-preview",
                title="Provider Documents KB Preview Session",
                created_at="2026-07-16T09:59:00",
                updated_at="2026-07-16T10:00:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-provider-documents-kb-preview",
                    prompt="Search the hosted provider index",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-16T09:59:30",
                    updated_at="2026-07-16T10:00:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-provider-documents-kb",
                            seq=4,
                            type="action",
                            title="Hosted Search [hosted_search_gateway · knowledge_retrieval]",
                            content_excerpt=(
                                'Tool done: Hosted Search Preview: {"documents_total":2,"knowledge_base_id":"hosted-kb"} '
                                'Output: {"documents_total":2,"knowledge_base_id":"hosted-kb","request_id":"req-hosted-1"}'
                            ),
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            'seq=4 · Hosted Search [hosted_search_gateway · knowledge_retrieval] · Retrieved 2 documents from hosted-kb (request id req-hosted-1).',
            markdown,
        )
        self.assertNotIn("from knowledge base hosted-kb", markdown)
        self.assertNotIn("Tool done: Hosted Search", markdown)

    def test_build_session_export_markdown_infers_provider_kb_for_label_only_real_documents_total_preview(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-16T10:05:00",
            session=session_routes_module.SessionResponse(
                id="session-label-only-provider-documents-kb-preview",
                title="Label Only Provider Documents KB Preview Session",
                created_at="2026-07-16T10:04:00",
                updated_at="2026-07-16T10:05:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-label-only-provider-documents-kb-preview",
                    prompt="Search the hosted provider index",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-16T10:04:30",
                    updated_at="2026-07-16T10:05:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-label-only-provider-documents-kb",
                            seq=4,
                            type="action",
                            title="Hosted Search",
                            content_excerpt=(
                                'Hosted Search: {"documents_total":2,'
                                '"knowledge_base_id":"hosted-kb",'
                                '"request_id":"req-hosted-1"}'
                            ),
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "seq=4 · Hosted Search [retrieval] · Retrieved 2 documents from hosted-kb (request id req-hosted-1).",
            markdown,
        )
        self.assertNotIn("from knowledge base hosted-kb", markdown)
        self.assertNotIn(
            'Hosted Search: {"documents_total":2,"knowledge_base_id":"hosted-kb","request_id":"req-hosted-1"}',
            markdown,
        )

    def test_build_session_export_markdown_does_not_imply_local_kb_for_name_only_real_tool_preview(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-08T10:00:00",
            session=session_routes_module.SessionResponse(
                id="session-name-only-real-tool-preview",
                title="Name-only Real Tool Preview Session",
                created_at="2026-07-08T09:59:00",
                updated_at="2026-07-08T10:00:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-name-only-real-tool-preview",
                    prompt="Search the provider index",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-08T09:59:30",
                    updated_at="2026-07-08T10:00:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-provider-search-name-only",
                            seq=5,
                            type="action",
                            title="Provider Search",
                            content_excerpt='Provider Search: {"hit_count":2,"knowledge_base_id":"provider-kb","request_id":"req-1"}',
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "seq=5 · Provider Search [retrieval] · Retrieved 2 hits (request id req-1).",
            markdown,
        )
        self.assertNotIn("from knowledge base provider-kb", markdown)
        self.assertNotIn(
            'Provider Search: {"hit_count":2,"knowledge_base_id":"provider-kb","request_id":"req-1"}',
            markdown,
        )

    def test_build_session_export_markdown_does_not_imply_local_kb_for_generic_retrieval_title_on_real_tool_preview(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-09T11:00:00",
            session=session_routes_module.SessionResponse(
                id="session-generic-retrieval-title-preview",
                title="Generic Retrieval Title Preview Session",
                created_at="2026-07-09T10:59:00",
                updated_at="2026-07-09T11:00:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-generic-retrieval-title-preview",
                    prompt="Search the provider index",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-09T10:59:30",
                    updated_at="2026-07-09T11:00:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-provider-search-generic-retrieval-title",
                            seq=9,
                            type="action",
                            title="Provider Search [retrieval]",
                            content_excerpt='Provider Search: {"hit_count":2,"knowledge_base_id":"provider-kb","request_id":"req-1"}',
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "seq=9 · Provider Search [retrieval] · Retrieved 2 hits (request id req-1).",
            markdown,
        )
        self.assertNotIn("from knowledge base provider-kb", markdown)
        self.assertNotIn(
            'Provider Search: {"hit_count":2,"knowledge_base_id":"provider-kb","request_id":"req-1"}',
            markdown,
        )

    def test_build_session_export_markdown_normalizes_http_json_aliases_for_real_tool_preview_excerpt(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-09T12:00:00",
            session=session_routes_module.SessionResponse(
                id="session-http-json-alias-preview",
                title="HTTP JSON Alias Preview Session",
                created_at="2026-07-09T11:59:00",
                updated_at="2026-07-09T12:00:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-http-json-alias-preview",
                    prompt="Search provider index with alias fields",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-09T11:59:30",
                    updated_at="2026-07-09T12:00:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-http-json-alias",
                            seq=10,
                            type="action",
                            title="Provider Search [retrieval]",
                            content_excerpt='Provider Search: {"documents_total":"unknown","items":[{"id":"doc-1"},{"id":"doc-2"}],"request_id":"req-items-preview-1"}',
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "seq=10 · Provider Search [retrieval] · Retrieved 2 documents (request id req-items-preview-1).",
            markdown,
        )
        self.assertNotIn("documents_total\":\"unknown", markdown)

    def test_build_session_export_markdown_normalizes_http_json_aliases_for_explicit_preview_and_output(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-09T12:30:00",
            session=session_routes_module.SessionResponse(
                id="session-http-json-explicit-preview-alias",
                title="HTTP JSON Explicit Preview Alias Session",
                created_at="2026-07-09T12:29:00",
                updated_at="2026-07-09T12:30:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-http-json-explicit-preview-alias",
                    prompt="Search provider index with explicit preview and output",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-09T12:29:30",
                    updated_at="2026-07-09T12:30:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-http-json-explicit-alias",
                            seq=11,
                            type="action",
                            title="Provider Search [retrieval]",
                            content_excerpt=(
                                'Tool done: Provider Search Preview: {"documents_total":"unknown",'
                                '"items":[{"id":"doc-1"},{"id":"doc-2"}],"secret":"hidden"} '
                                'Output: {"hit_count":"unknown","matches":[{"id":"vec-1"},'
                                '{"id":"vec-2"}],"request_id":"req-matches-preview-1",'
                                '"secret":"hidden"}'
                            ),
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            'seq=11 · Provider Search [retrieval] · Retrieved 2 hits (request id req-matches-preview-1). '
            'Preview: {"documents_total":2} Output: {"hit_count":2,"request_id":"req-matches-preview-1"}',
            markdown,
        )
        self.assertNotIn('"secret"', markdown)
        self.assertNotIn('"documents_total":"unknown"', markdown)
        self.assertNotIn('"hit_count":"unknown"', markdown)

    def test_build_session_export_markdown_infers_calc_summary_from_structural_kind_preview_without_semantic_family(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-08T11:00:00",
            session=session_routes_module.SessionResponse(
                id="session-structural-kind-calc-preview",
                title="Structural Kind Calc Preview Session",
                created_at="2026-07-08T10:59:00",
                updated_at="2026-07-08T11:00:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-structural-kind-calc-preview",
                    prompt="Calculate provider metric",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-08T10:59:30",
                    updated_at="2026-07-08T11:00:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-provider-math-structural-kind",
                            seq=6,
                            type="action",
                            title="Hosted Math",
                            content_excerpt='Hosted Math: {"kind":"provider_calc","result":7,"request_id":"req-calc-1"}',
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "seq=6 · Hosted Math [calculator] · Calculated result = 7 (request id req-calc-1).",
            markdown,
        )
        self.assertNotIn(
            'Hosted Math: {"kind":"provider_calc","result":7,"request_id":"req-calc-1"}',
            markdown,
        )

    def test_build_session_export_markdown_infers_calc_summary_for_name_only_real_tool_preview(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-09T09:00:00",
            session=session_routes_module.SessionResponse(
                id="session-name-only-real-calc-preview",
                title="Name-only Real Calc Preview Session",
                created_at="2026-07-09T08:59:00",
                updated_at="2026-07-09T09:00:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-name-only-real-calc-preview",
                    prompt="Calculate provider metric",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-09T08:59:30",
                    updated_at="2026-07-09T09:00:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-hosted-math-name-only",
                            seq=7,
                            type="action",
                            title="Hosted Math",
                            content_excerpt='Hosted Math: {"result":7,"request_id":"req-calc-1"}',
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "seq=7 · Hosted Math [calculator] · Calculated result = 7 (request id req-calc-1).",
            markdown,
        )
        self.assertNotIn(
            'Hosted Math: {"result":7,"request_id":"req-calc-1"}',
            markdown,
        )

    def test_build_session_export_markdown_infers_calc_summary_from_quoted_json_safe_output_preview(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-10T09:30:00",
            session=session_routes_module.SessionResponse(
                id="session-quoted-json-safe-output-preview",
                title="Quoted JSON Safe Output Preview Session",
                created_at="2026-07-10T09:29:00",
                updated_at="2026-07-10T09:30:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-quoted-json-safe-output-preview",
                    prompt="Calculate provider metric",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-10T09:29:30",
                    updated_at="2026-07-10T09:30:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-hosted-math-quoted-json-safe-output",
                            seq=10,
                            type="action",
                            title="Hosted Math",
                            content_excerpt='Tool done: Hosted Math Output: "{\\"result\\":7,\\"request_id\\":\\"req-calc-1\\",\\"kind\\":\\"provider_calc\\",\\"secret\\":\\"hidden\\"}"',
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            'seq=10 · Hosted Math [calculator] · Calculated result = 7 (request id req-calc-1). Output: {"result":7,"request_id":"req-calc-1"}',
            markdown,
        )
        self.assertNotIn("Tool done: Hosted Math", markdown)
        self.assertNotIn("secret", markdown)

    def test_build_session_export_markdown_infers_calc_summary_from_quoted_json_label_preview(
        self,
    ) -> None:
        quoted_payload = json.dumps(
            '{"result":7,"request_id":"req-calc-1","kind":"provider_calc","secret":"hidden"}'
        )
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-10T10:30:00",
            session=session_routes_module.SessionResponse(
                id="session-quoted-json-label-preview",
                title="Quoted JSON Label Preview Session",
                created_at="2026-07-10T10:29:00",
                updated_at="2026-07-10T10:30:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-quoted-json-label-preview",
                    prompt="Calculate provider metric",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-10T10:29:30",
                    updated_at="2026-07-10T10:30:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-hosted-math-quoted-json-label",
                            seq=11,
                            type="action",
                            title="Hosted Math",
                            content_excerpt=f"Hosted Math: {quoted_payload}",
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "seq=11 · Hosted Math [calculator] · Calculated result = 7 (request id req-calc-1).",
            markdown,
        )
        self.assertNotIn(f"Hosted Math: {quoted_payload}", markdown)
        self.assertNotIn("secret", markdown)

    def test_build_session_export_markdown_infers_calc_summary_from_legacy_quoted_json_label_preview(
        self,
    ) -> None:
        legacy_quoted_payload = (
            '"{"result":7,"request_id":"req-calc-1","kind":"provider_calc","secret":"hidden"}"'
        )
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-10T10:35:00",
            session=session_routes_module.SessionResponse(
                id="session-legacy-quoted-json-label-preview",
                title="Legacy Quoted JSON Label Preview Session",
                created_at="2026-07-10T10:34:00",
                updated_at="2026-07-10T10:35:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-legacy-quoted-json-label-preview",
                    prompt="Calculate provider metric",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-10T10:34:30",
                    updated_at="2026-07-10T10:35:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-hosted-math-legacy-quoted-json-label",
                            seq=12,
                            type="action",
                            title="Hosted Math",
                            content_excerpt=f"Hosted Math: {legacy_quoted_payload}",
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "seq=12 · Hosted Math [calculator] · Calculated result = 7 (request id req-calc-1).",
            markdown,
        )
        self.assertNotIn(f"Hosted Math: {legacy_quoted_payload}", markdown)
        self.assertNotIn("secret", markdown)

    def test_build_session_export_markdown_infers_planner_title_for_name_only_real_tool_preview(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-09T10:00:00",
            session=session_routes_module.SessionResponse(
                id="session-name-only-real-planner-preview",
                title="Name-only Real Planner Preview Session",
                created_at="2026-07-09T09:59:00",
                updated_at="2026-07-09T10:00:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-name-only-real-planner-preview",
                    prompt="Plan provider workflow",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-09T09:59:30",
                    updated_at="2026-07-09T10:00:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-hosted-planner-name-only",
                            seq=8,
                            type="action",
                            title="Hosted Planner",
                            content_excerpt='Hosted Planner: {"steps":["Analyze request","Synthesize final answer"]}',
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            "seq=8 · Hosted Planner [planner] · Planned steps - Analyze request -> Synthesize final answer.",
            markdown,
        )
        self.assertNotIn(
            'Hosted Planner: {"steps":["Analyze request","Synthesize final answer"]}',
            markdown,
        )

    def test_build_session_export_markdown_redacts_generic_http_json_preview_without_summary(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-10T11:00:00",
            session=session_routes_module.SessionResponse(
                id="session-generic-http-json-safe-preview",
                title="Generic HTTP JSON Safe Preview Session",
                created_at="2026-07-10T10:59:00",
                updated_at="2026-07-10T11:00:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-generic-http-json-safe-preview",
                    prompt="Check provider status",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-10T10:59:30",
                    updated_at="2026-07-10T11:00:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-provider-status-safe",
                            seq=13,
                            type="action",
                            title="Provider Status [provider_status]",
                            content_excerpt=(
                                'Provider Status: {"status":"ready",'
                                '"message":"gateway token=hidden",'
                                '"access_token":"hidden",'
                                '"request_id":"Bearer secret-token"}'
                            ),
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn("seq=13 · Provider Status [provider_status] · Preview: ", markdown)
        self.assertIn('"status":"ready"', markdown)
        self.assertIn('"message":"gateway token=[redacted]"', markdown)
        self.assertIn('"access_token":"[redacted]"', markdown)
        self.assertNotIn("Provider Status: {", markdown)
        self.assertNotIn("request_id", markdown)
        self.assertNotIn("Bearer", markdown)
        self.assertNotIn("secret-token", markdown)
        self.assertNotIn("hidden", markdown)

    def test_build_session_export_markdown_redacts_generic_http_json_explicit_preview_and_output_without_summary(
        self,
    ) -> None:
        payload = session_routes_module.SessionExportJsonResponse(
            version="1",
            exported_at="2026-07-10T11:30:00",
            session=session_routes_module.SessionResponse(
                id="session-generic-http-json-safe-explicit-preview",
                title="Generic HTTP JSON Explicit Safe Preview Session",
                created_at="2026-07-10T11:29:00",
                updated_at="2026-07-10T11:30:00",
            ),
            usage_summary=session_routes_module.SessionUsageSummaryResponse(
                tasks_total=1,
                tasks_with_usage=0,
                source_tasks_provider=0,
                source_tasks_estimated=0,
                source_tasks_mixed=0,
                source_tasks_legacy=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_estimate=0.0,
                avg_total_tokens=None,
                avg_cost_estimate=None,
            ),
            stats=session_routes_module.SessionExportStats(
                task_count=1,
                message_count=0,
                trace_step_count=1,
                rag_hit_count=0,
            ),
            messages=[],
            tasks=[
                session_routes_module.SessionExportTaskSummary(
                    id="task-generic-http-json-safe-explicit-preview",
                    prompt="Check provider status",
                    status="completed",
                    status_normalized="done",
                    status_label="Done",
                    status_rank=40,
                    created_at="2026-07-10T11:29:30",
                    updated_at="2026-07-10T11:30:00",
                    trace_step_count=1,
                    rag_hit_count=0,
                    trace_preview=[
                        session_routes_module.SessionExportTracePreviewStep(
                            id="preview-provider-status-safe-explicit",
                            seq=14,
                            type="action",
                            title="Provider Status [provider_status]",
                            content_excerpt=(
                                'Tool done: Provider Status Preview: '
                                '{"status":"ready","token":"hidden"} Output: '
                                '{"status":"ready","message":"secret=hidden",'
                                '"request_id":"Bearer secret-token"}'
                            ),
                        )
                    ],
                )
            ],
        )

        markdown = session_routes_module._build_session_export_markdown(  # type: ignore[attr-defined]
            payload,
        )

        self.assertIn(
            'seq=14 · Provider Status [provider_status] · Preview: {"status":"ready","token":"[redacted]"} Output: {"status":"ready","message":"secret=[redacted]"}',
            markdown,
        )
        self.assertNotIn("Tool done: Provider Status", markdown)
        self.assertNotIn("request_id", markdown)
        self.assertNotIn("Bearer", markdown)
        self.assertNotIn("secret-token", markdown)
        self.assertNotIn("hidden", markdown)

    def test_build_session_export_payload_trusts_service_task_governance_shape(
        self,
    ) -> None:
        session = {
            "id": "session-shared-governance-columns",
            "title": "Shared Governance Session",
            "created_at": "2026-06-11T12:00:00",
            "updated_at": "2026-06-11T12:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_merger = session_routes_module.chat_persistence_service._merge_session_governance_summary
        try:
            self.assertFalse(
                hasattr(
                    session_routes_module.chat_persistence_service,
                    "_extract_task_governance_from_task_with_parsed_trace_steps",
                )
            )
            class GuardedTaskGovernanceDict(dict):
                def get(self, *_args, **_kwargs):
                    raise AssertionError(
                        "session export task governance should construct outward model directly from the service governance dict"
                    )

            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-shared-governance-session",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-11T12:00:00",
                    "updated_at": "2026-06-11T12:01:00",
                    "usage_json": None,
                    "governance": GuardedTaskGovernanceDict(
                        profile="shared_profile",
                        provider_source="shared_source",
                        allowed_tool_names=["shared_tool"],
                        allowed_tool_labels=["Shared Tool"],
                    ),
                    "trace_json": None,
                },
            ]
            session_routes_module.chat_persistence_service._merge_session_governance_summary = (
                lambda _current, _task_governance: {
                    "profiles": ["shared_profile"],
                    "provider_sources": ["shared_source"],
                    "allowed_tool_names": ["shared_tool"],
                    "allowed_tool_labels": ["Shared Tool"],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-shared-governance-session",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.chat_persistence_service._merge_session_governance_summary = (
                original_merger
            )

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(payload.governance.profiles, ["shared_profile"])
        self.assertEqual(payload.governance.provider_sources, ["shared_source"])
        self.assertEqual(payload.governance.allowed_tool_names, ["shared_tool"])
        self.assertEqual(payload.governance.allowed_tool_labels, ["Shared Tool"])
        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(payload.tasks[0].governance.profile, "shared_profile")
        self.assertEqual(payload.tasks[0].governance.provider_source, "shared_source")
        self.assertEqual(payload.tasks[0].governance.allowed_tool_names, ["shared_tool"])
        self.assertEqual(payload.tasks[0].governance.allowed_tool_labels, ["Shared Tool"])

    def test_build_session_export_payload_does_not_fallback_task_governance_when_service_missing(
        self,
    ) -> None:
        session = {
            "id": "session-no-clone-governance-row",
            "title": "No Clone Governance Session",
            "created_at": "2026-06-16T12:00:00",
            "updated_at": "2026-06-16T12:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        try:
            self.assertFalse(
                hasattr(
                    session_routes_module.chat_persistence_service,
                    "_extract_task_governance_from_task_with_parsed_trace_steps",
                )
            )
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-no-clone-row",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-16T12:00:00",
                    "updated_at": "2026-06-16T12:01:00",
                    "usage_json": None,
                    "trace_json": "[]",
                    "tool_registry_profile": "poisoned_profile",
                    "tool_registry_provider_source": "poisoned_source",
                    "allowed_tool_names_json": json.dumps(["poisoned_tool"]),
                    "allowed_tool_labels_json": json.dumps(["Poisoned Tool"]),
                },
            ]
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-no-clone-governance-row",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks

        self.assertIsNone(payload.tasks[0].governance)
        self.assertIsNone(payload.governance)

    def test_build_session_export_payload_does_not_fallback_task_governance_from_trace(
        self,
    ) -> None:
        session = {
            "id": "session-shared-governance-trace",
            "title": "Shared Trace Governance Session",
            "created_at": "2026-06-12T12:00:00",
            "updated_at": "2026-06-12T12:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        try:
            self.assertFalse(
                hasattr(
                    session_routes_module.chat_persistence_service,
                    "_extract_task_governance_from_task_with_parsed_trace_steps",
                )
            )
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-shared-governance-trace",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-12T12:00:00",
                    "updated_at": "2026-06-12T12:01:00",
                    "usage_json": None,
                    "tool_registry_profile": "poisoned_profile",
                    "tool_registry_provider_source": "poisoned_source",
                    "allowed_tool_names_json": json.dumps(["poisoned_tool"]),
                    "allowed_tool_labels_json": json.dumps(["Poisoned Tool"]),
                    "trace_json": "[]",
                },
            ]
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-shared-governance-trace",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks

        self.assertIsNone(payload.governance)
        self.assertIsNone(payload.tasks[0].governance)

    def test_build_session_export_payload_trusts_normalized_governance_dict_shapes(
        self,
    ) -> None:
        class GuardedTaskGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "session export task governance should construct outward model directly from normalized task governance dict"
                )

        class GuardedSessionGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "session export governance summary should construct outward model directly from normalized session governance dict"
                )

        session = {
            "id": "session-guarded-governance-shape",
            "title": "Guarded Governance Shape Session",
            "created_at": "2026-06-16T23:00:00",
            "updated_at": "2026-06-16T23:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_merger = session_routes_module.chat_persistence_service._merge_session_governance_summary
        try:
            self.assertFalse(
                hasattr(
                    session_routes_module.chat_persistence_service,
                    "_extract_task_governance_from_task_with_parsed_trace_steps",
                )
            )
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-guarded-governance-shape",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-16T23:00:00",
                    "updated_at": "2026-06-16T23:01:00",
                    "usage_json": None,
                    "governance": GuardedTaskGovernanceDict(
                        profile="guarded_profile",
                        provider_source="guarded_source",
                        allowed_tool_names=["guarded_tool"],
                        allowed_tool_labels=["Guarded Tool"],
                    ),
                    "trace_json": None,
                },
            ]
            session_routes_module.chat_persistence_service._merge_session_governance_summary = (  # type: ignore[attr-defined]
                lambda _current, _task_governance: GuardedSessionGovernanceDict(
                    profiles=["guarded_profile"],
                    provider_sources=["guarded_source"],
                    allowed_tool_names=["guarded_tool"],
                    allowed_tool_labels=["Guarded Tool"],
                )
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-guarded-governance-shape",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.chat_persistence_service._merge_session_governance_summary = (
                original_merger
            )

        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(payload.tasks[0].governance.profile, "guarded_profile")
        self.assertEqual(payload.tasks[0].governance.provider_source, "guarded_source")
        self.assertEqual(payload.tasks[0].governance.allowed_tool_names, ["guarded_tool"])
        self.assertEqual(
            payload.tasks[0].governance.allowed_tool_labels, ["Guarded Tool"]
        )
        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(payload.governance.profiles, ["guarded_profile"])
        self.assertEqual(payload.governance.provider_sources, ["guarded_source"])
        self.assertEqual(payload.governance.allowed_tool_names, ["guarded_tool"])
        self.assertEqual(payload.governance.allowed_tool_labels, ["Guarded Tool"])

    def test_build_session_export_payload_does_not_reuse_task_governance_clone_helper_for_service_governance(
        self,
    ) -> None:
        session = {
            "id": "session-no-clone-governance-trace",
            "title": "No Clone Trace Governance Session",
            "created_at": "2026-06-16T13:00:00",
            "updated_at": "2026-06-16T13:05:00",
        }
        original_get_session_usage_summary = session_routes_module.get_session_usage_summary
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_clone_helper = getattr(
            session_routes_module.chat_persistence_service,
            "_clone_task_governance_dict",
            None,
        )
        try:
            session_routes_module.get_session_usage_summary = lambda *_args, **_kwargs: {
                "tasks_total": 1,
                "tasks_with_usage": 0,
                "source_tasks_provider": 0,
                "source_tasks_estimated": 0,
                "source_tasks_mixed": 0,
                "source_tasks_legacy": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_estimate": 0.0,
                "avg_total_tokens": None,
                "avg_cost_estimate": None,
            }
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: [
                {
                    "id": "task-no-clone-trace",
                    "prompt": "task one",
                    "status": "completed",
                    "created_at": "2026-06-16T13:00:00",
                    "updated_at": "2026-06-16T13:01:00",
                    "usage_json": None,
                    "governance": {
                        "profile": "shared_trace_profile",
                        "provider_source": "shared_trace_source",
                        "allowed_tool_names": ["shared_trace_tool"],
                        "allowed_tool_labels": ["Shared Trace Tool"],
                    },
                    "trace_json": "[]",
                },
            ]
            if original_clone_helper is not None:
                session_routes_module.chat_persistence_service._clone_task_governance_dict = (  # type: ignore[attr-defined]
                    lambda _governance: (_ for _ in ()).throw(
                        AssertionError(
                            "session export service governance path should not depend on the shared clone helper"
                        )
                    )
                )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                session,
                "user-no-clone-governance-trace",
            )
        finally:
            session_routes_module.get_session_usage_summary = original_get_session_usage_summary
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            if original_clone_helper is None:
                if hasattr(
                    session_routes_module.chat_persistence_service,
                    "_clone_task_governance_dict",
                ):
                    delattr(
                        session_routes_module.chat_persistence_service,
                        "_clone_task_governance_dict",
                    )
            else:
                session_routes_module.chat_persistence_service._clone_task_governance_dict = original_clone_helper  # type: ignore[attr-defined]

        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(payload.tasks[0].governance.profile, "shared_trace_profile")
        self.assertEqual(payload.tasks[0].governance.provider_source, "shared_trace_source")
        self.assertEqual(payload.tasks[0].governance.allowed_tool_names, ["shared_trace_tool"])
        self.assertEqual(
            payload.tasks[0].governance.allowed_tool_labels, ["Shared Trace Tool"]
        )
        self.assertEqual(payload.tasks[0].governance.profile, "shared_trace_profile")
        self.assertEqual(payload.tasks[0].governance.provider_source, "shared_trace_source")
        self.assertEqual(payload.tasks[0].governance.allowed_tool_names, ["shared_trace_tool"])
        self.assertEqual(payload.tasks[0].governance.allowed_tool_labels, ["Shared Trace Tool"])

    def test_export_assertions_require_session_task_level_governance_json(self) -> None:
        import importlib

        export_assertions_module = importlib.import_module("scripts.e2e_export_assertions")
        payload = {
            "session": {"id": "session-e2e-governance"},
            "tasks": [
                {
                    "id": "task-e2e-governance",
                    "governance": {
                        "profile": "planning_only",
                        "provider_source": "suite_a",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                },
            ],
        }

        task_id, governance = (
            export_assertions_module.assert_session_export_task_level_governance_json(payload)
        )

        self.assertEqual(task_id, "task-e2e-governance")
        self.assertEqual(governance["profile"], "planning_only")
        self.assertEqual(governance["provider_source"], "suite_a")
        self.assertEqual(governance["allowed_tool_names"], ["task_plan"])
        self.assertEqual(governance["allowed_tool_labels"], ["Task Planner"])

    def test_export_assertions_require_session_task_level_governance_markdown(self) -> None:
        import importlib

        export_assertions_module = importlib.import_module("scripts.e2e_export_assertions")
        governance = {
            "profile": "planning_only",
            "provider_source": "suite_a",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner"],
        }
        markdown = "\n".join(
            [
                "# InsightAgent Session Export",
                "## Tasks",
                "### Task 1: task-e2e-governance",
                "- Tool Registry Profile: planning_only",
                "- Tool Registry Source: suite_a",
                "- Allowed Tools: Task Planner",
            ]
        )

        export_assertions_module.assert_session_export_task_level_governance_markdown(
            markdown,
            governance,
        )

    def test_export_assertions_require_task_export_governance_json(self) -> None:
        import importlib

        export_assertions_module = importlib.import_module("scripts.e2e_export_assertions")
        payload = {
            "trace": {
                "governance": {
                    "profile": "calculator_only",
                    "provider_source": "default",
                    "allowed_tool_names": ["calc_eval"],
                    "allowed_tool_labels": ["Calculator"],
                }
            }
        }

        governance = export_assertions_module.assert_task_export_governance_json(payload)

        self.assertEqual(governance["profile"], "calculator_only")
        self.assertEqual(governance["provider_source"], "default")
        self.assertEqual(governance["allowed_tool_names"], ["calc_eval"])
        self.assertEqual(governance["allowed_tool_labels"], ["Calculator"])

    def test_export_assertions_require_task_export_governance_markdown(self) -> None:
        import importlib

        export_assertions_module = importlib.import_module("scripts.e2e_export_assertions")
        governance = {
            "profile": "calculator_only",
            "provider_source": "default",
            "allowed_tool_names": ["calc_eval"],
            "allowed_tool_labels": ["Calculator"],
        }
        markdown = "\n".join(
            [
                "# InsightAgent Task Export",
                "## Trace Summary",
                "- Tool Registry Profile: calculator_only",
                "- Tool Registry Source: default",
                "- Allowed Tools: Calculator",
            ]
        )

        export_assertions_module.assert_task_export_governance_markdown(
            markdown,
            governance,
        )
