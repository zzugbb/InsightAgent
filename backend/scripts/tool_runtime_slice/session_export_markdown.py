from __future__ import annotations

from .context import *


class SessionExportMarkdownMixin:
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
