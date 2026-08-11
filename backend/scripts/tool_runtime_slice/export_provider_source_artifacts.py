from __future__ import annotations

from .context import *


class ExportProviderSourceArtifactsMixin:
    def test_task_export_payload_redacts_sensitive_provider_source_values(
        self,
    ) -> None:
        original_get_task_messages = task_routes_module.get_task_messages
        original_export_summary = (
            task_routes_module.chat_persistence_service.get_task_export_response_summary
        )
        try:
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "task": {
                        "id": "task-export-source-redaction",
                        "session_id": "session-export-source-redaction",
                        "prompt": "provider source export redaction",
                        "status": "completed",
                        "status_normalized": "completed",
                        "status_label": "Completed",
                        "status_rank": 30,
                        "created_at": "2026-08-10T10:00:00",
                        "updated_at": "2026-08-10T10:01:00",
                    },
                    "usage": None,
                    "messages": [],
                    "trace": {
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "suite_api_key=hidden",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        },
                        "steps": [],
                        "step_count": 0,
                        "rag_hit_count": 0,
                        "rag_knowledge_base_ids": [],
                        "rag_chunks": [],
                    },
                }
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                {
                    "id": "task-export-source-redaction",
                    "session_id": "session-export-source-redaction",
                    "prompt": "provider source export redaction",
                    "status": "completed",
                    "created_at": "2026-08-10T10:00:00",
                    "updated_at": "2026-08-10T10:01:00",
                },
                "user-export-source-redaction",
            )
        finally:
            task_routes_module.get_task_messages = original_get_task_messages
            task_routes_module.chat_persistence_service.get_task_export_response_summary = original_export_summary  # type: ignore[attr-defined]

        self.assertIsNotNone(payload.trace.governance)
        assert payload.trace.governance is not None
        self.assertEqual(
            payload.trace.governance.provider_source,
            "suite_[redacted]",
        )
        markdown = task_routes_module._build_task_export_markdown(payload)  # type: ignore[attr-defined]
        artifact_blob = json.dumps(payload.model_dump(), default=str) + markdown
        self.assertNotIn("api_key=hidden", artifact_blob)
        self.assertIn("suite_[redacted]", artifact_blob)

    def test_session_export_payload_redacts_sensitive_provider_source_values(
        self,
    ) -> None:
        original_get_session_usage_summary = (
            session_routes_module.get_session_usage_summary
        )
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_export_summary = (
            session_routes_module.chat_persistence_service.get_session_export_response_summary
        )
        try:
            session_routes_module.get_session_usage_summary = (
                lambda *_args, **_kwargs: {
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
            )
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "session": {
                        "id": "session-export-source-redaction",
                        "title": "Provider Source Redaction",
                        "created_at": "2026-08-10T10:00:00",
                        "updated_at": "2026-08-10T10:01:00",
                    },
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
                    "governance": {
                        "profiles": ["planning_only"],
                        "provider_sources": [
                            "suite_api_key=hidden",
                            "fallback_access_token=hidden",
                        ],
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "messages": [],
                    "tasks": [
                        {
                            "id": "task-export-source-redaction",
                            "prompt": "provider source export redaction",
                            "status": "completed",
                            "status_normalized": "completed",
                            "status_label": "Completed",
                            "status_rank": 30,
                            "created_at": "2026-08-10T10:00:00",
                            "updated_at": "2026-08-10T10:01:00",
                            "usage": None,
                            "trace_step_count": 0,
                            "rag_hit_count": 0,
                            "trace_preview": [],
                            "governance": {
                                "profile": "planning_only",
                                "provider_source": "suite_api_key=hidden",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner"],
                            },
                        }
                    ],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                {
                    "id": "session-export-source-redaction",
                    "title": "Provider Source Redaction",
                    "created_at": "2026-08-10T10:00:00",
                    "updated_at": "2026-08-10T10:01:00",
                },
                "user-export-source-redaction",
            )
        finally:
            session_routes_module.get_session_usage_summary = (
                original_get_session_usage_summary
            )
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.chat_persistence_service.get_session_export_response_summary = original_export_summary  # type: ignore[attr-defined]

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(
            payload.governance.provider_sources,
            ["suite_[redacted]", "fallback_[redacted]"],
        )
        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(
            payload.tasks[0].governance.provider_source,
            "suite_[redacted]",
        )
        markdown = session_routes_module._build_session_export_markdown(payload)  # type: ignore[attr-defined]
        artifact_blob = json.dumps(payload.model_dump(), default=str) + markdown
        self.assertNotIn("api_key=hidden", artifact_blob)
        self.assertNotIn("access_token=hidden", artifact_blob)
        self.assertIn("suite_[redacted]", artifact_blob)
        self.assertIn("fallback_[redacted]", artifact_blob)

    def test_session_export_payload_preserves_colliding_provider_source_aliases(
        self,
    ) -> None:
        original_get_session_usage_summary = (
            session_routes_module.get_session_usage_summary
        )
        original_get_session_messages = session_routes_module.get_session_messages
        original_get_session_tasks = session_routes_module.get_session_tasks
        original_export_summary = (
            session_routes_module.chat_persistence_service.get_session_export_response_summary
        )
        try:
            session_routes_module.get_session_usage_summary = (
                lambda *_args, **_kwargs: {
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
            )
            session_routes_module.get_session_messages = lambda *_args, **_kwargs: []
            session_routes_module.get_session_tasks = lambda *_args, **_kwargs: []
            session_routes_module.chat_persistence_service.get_session_export_response_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "session": {
                        "id": "session-export-source-alias",
                        "title": "Provider Source Alias",
                        "created_at": "2026-08-10T10:00:00",
                        "updated_at": "2026-08-10T10:01:00",
                    },
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
                    "governance": {
                        "profiles": ["planning_only"],
                        "provider_sources": [
                            "suite_access_token=two",
                            "suite_api_key=one",
                        ],
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "stats": {
                        "task_count": 1,
                        "message_count": 0,
                        "trace_step_count": 0,
                        "rag_hit_count": 0,
                    },
                    "messages": [],
                    "tasks": [
                        {
                            "id": "task-export-source-alias",
                            "prompt": "provider source export alias",
                            "status": "completed",
                            "status_normalized": "completed",
                            "status_label": "Completed",
                            "status_rank": 30,
                            "created_at": "2026-08-10T10:00:00",
                            "updated_at": "2026-08-10T10:01:00",
                            "usage": None,
                            "trace_step_count": 0,
                            "rag_hit_count": 0,
                            "trace_preview": [],
                            "governance": {
                                "profile": "planning_only",
                                "provider_source": "suite_api_key=one",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner"],
                            },
                        }
                    ],
                }
            )
            payload = session_routes_module._build_session_export_payload(  # type: ignore[attr-defined]
                {
                    "id": "session-export-source-alias",
                    "title": "Provider Source Alias",
                    "created_at": "2026-08-10T10:00:00",
                    "updated_at": "2026-08-10T10:01:00",
                },
                "user-export-source-alias",
            )
        finally:
            session_routes_module.get_session_usage_summary = (
                original_get_session_usage_summary
            )
            session_routes_module.get_session_messages = original_get_session_messages
            session_routes_module.get_session_tasks = original_get_session_tasks
            session_routes_module.chat_persistence_service.get_session_export_response_summary = original_export_summary  # type: ignore[attr-defined]

        self.assertIsNotNone(payload.governance)
        assert payload.governance is not None
        self.assertEqual(
            payload.governance.provider_sources,
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertIsNotNone(payload.tasks[0].governance)
        assert payload.tasks[0].governance is not None
        self.assertEqual(
            payload.tasks[0].governance.provider_source,
            "suite_[redacted]#2",
        )
        markdown = session_routes_module._build_session_export_markdown(payload)  # type: ignore[attr-defined]
        artifact_blob = json.dumps(payload.model_dump(), default=str) + markdown
        self.assertNotIn("api_key=one", artifact_blob)
        self.assertNotIn("access_token=two", artifact_blob)
        self.assertIn("suite_[redacted]#1", artifact_blob)
        self.assertIn("suite_[redacted]#2", artifact_blob)
