from __future__ import annotations

from .context import *


class ResponseProviderSourceArtifactsMixin:
    def test_task_response_summary_redacts_sensitive_provider_source_values(
        self,
    ) -> None:
        payload = chat_persistence_module.get_task_response_summary_from_task(
            {
                "id": "task-response-summary-source-redaction",
                "session_id": "session-response-summary-source-redaction",
                "prompt": "provider source response summary redaction",
                "status": "completed",
                "governance": {
                    "profile": "planning_only",
                    "provider_source": "suite_api_key=hidden",
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner"],
                },
                "trace_json": None,
                "usage_json": None,
                "created_at": "2026-08-10T11:00:00",
                "updated_at": "2026-08-10T11:01:00",
            }
        )

        self.assertEqual(
            payload["governance"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertNotIn("api_key=hidden", json.dumps(payload, default=str))

    def test_task_export_summaries_redact_sensitive_provider_source_values(
        self,
    ) -> None:
        task = {
            "id": "task-export-summary-source-redaction",
            "session_id": "session-export-summary-source-redaction",
            "prompt": "provider source export summary redaction",
            "status": "completed",
            "governance": {
                "profile": "planning_only",
                "provider_source": "suite_api_key=hidden",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner"],
            },
            "trace_json": None,
            "usage_json": None,
            "created_at": "2026-08-10T11:00:00",
            "updated_at": "2026-08-10T11:01:00",
        }

        export_summary = chat_persistence_module.get_task_export_summary_from_task(
            task
        )
        response_summary = chat_persistence_module.get_task_export_response_summary(
            task,
            [],
        )

        self.assertEqual(
            export_summary["trace"]["governance"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            response_summary["trace"]["governance"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertNotIn("api_key=hidden", json.dumps(export_summary, default=str))
        self.assertNotIn("api_key=hidden", json.dumps(response_summary, default=str))

    def test_usage_dashboard_response_summary_redacts_sensitive_provider_source_values(
        self,
    ) -> None:
        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(
            {
                "window_days": 14,
                "summary": {"tasks_total": 1},
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-response-summary-source-redaction",
                        "session_title": "Provider Source Redaction",
                        "tasks_with_usage": 1,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "last_task_at": "2026-08-10T11:01:00",
                        "governance": {
                            "profiles": ["planning_only"],
                            "provider_sources": [
                                "suite_api_key=hidden",
                                "fallback_access_token=hidden",
                            ],
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        },
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-response-summary-source-redaction",
                        "session_id": "session-response-summary-source-redaction",
                        "session_title": "Provider Source Redaction",
                        "prompt_excerpt": "provider source response redaction",
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "created_at": "2026-08-10T11:00:00",
                        "updated_at": "2026-08-10T11:01:00",
                        "source_kind": "provider",
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

        self.assertEqual(
            payload["by_session"][0]["governance"]["provider_sources"],
            ["suite_[redacted]", "fallback_[redacted]"],
        )
        self.assertEqual(
            payload["top_tasks"][0]["governance"]["provider_source"],
            "suite_[redacted]",
        )
        payload_blob = json.dumps(payload, default=str)
        self.assertNotIn("api_key=hidden", payload_blob)
        self.assertNotIn("access_token=hidden", payload_blob)

    def test_usage_dashboard_response_summary_preserves_cross_section_provider_source_aliases(
        self,
    ) -> None:
        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(
            {
                "window_days": 14,
                "summary": {"tasks_total": 2},
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-response-summary-source-alias",
                        "session_title": "Provider Source Alias",
                        "tasks_with_usage": 2,
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "last_task_at": "2026-08-10T12:01:00",
                        "governance": {
                            "profiles": ["planning_only"],
                            "provider_sources": [
                                "suite_access_token=two",
                                "suite_api_key=one",
                            ],
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        },
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-response-summary-api-key",
                        "session_id": "session-response-summary-source-alias",
                        "session_title": "Provider Source Alias",
                        "prompt_excerpt": "provider source alias api key",
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "created_at": "2026-08-10T12:00:00",
                        "updated_at": "2026-08-10T12:01:00",
                        "source_kind": "provider",
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "suite_api_key=one",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        },
                    },
                    {
                        "task_id": "task-response-summary-access-token",
                        "session_id": "session-response-summary-source-alias",
                        "session_title": "Provider Source Alias",
                        "prompt_excerpt": "provider source alias access token",
                        "total_tokens": 0,
                        "cost_estimate": 0.0,
                        "created_at": "2026-08-10T12:00:00",
                        "updated_at": "2026-08-10T12:01:00",
                        "source_kind": "provider",
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "suite_access_token=two",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        },
                    },
                ],
            }
        )

        self.assertEqual(
            payload["by_session"][0]["governance"]["provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertEqual(
            payload["top_tasks"][0]["governance"]["provider_source"],
            "suite_[redacted]#2",
        )
        self.assertEqual(
            payload["top_tasks"][1]["governance"]["provider_source"],
            "suite_[redacted]#1",
        )
        payload_blob = json.dumps(payload, default=str)
        self.assertNotIn("api_key=one", payload_blob)
        self.assertNotIn("access_token=two", payload_blob)

    def test_task_detail_response_redacts_sensitive_provider_source_values(
        self,
    ) -> None:
        original_get_task = task_routes_module.get_task
        original_response_summary = (
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task
        )
        try:
            task_routes_module.get_task = lambda *_args, **_kwargs: {
                "id": "task-response-source-redaction",
            }
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "id": "task-response-source-redaction",
                    "session_id": "session-response-source-redaction",
                    "prompt": "provider source response redaction",
                    "status": "completed",
                    "status_normalized": "completed",
                    "status_label": "Completed",
                    "status_rank": 30,
                    "governance": {
                        "profile": "planning_only",
                        "provider_source": "suite_api_key=hidden",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "trace_json": None,
                    "usage_json": None,
                    "created_at": "2026-08-10T11:00:00",
                    "updated_at": "2026-08-10T11:01:00",
                }
            )

            response = task_routes_module.get_task_detail(
                "task-response-source-redaction",
                current_user={"id": "user-response-source-redaction"},
            )
        finally:
            task_routes_module.get_task = original_get_task
            task_routes_module.chat_persistence_service.get_task_response_summary_from_task = original_response_summary  # type: ignore[attr-defined]

        self.assertIsNotNone(response.governance)
        assert response.governance is not None
        self.assertEqual(response.governance.provider_source, "suite_[redacted]")
        self.assertNotIn(
            "api_key=hidden",
            json.dumps(response.model_dump(), default=str),
        )

    def test_usage_dashboard_response_redacts_sensitive_provider_source_values(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_response_summary = (
            task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary
        )
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {}
            task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: {
                    "window_days": 14,
                    "summary": {
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
                    "trend": [],
                    "by_session": [
                        {
                            "session_id": "session-response-source-redaction",
                            "session_title": "Provider Source Redaction",
                            "tasks_with_usage": 1,
                            "total_tokens": 0,
                            "cost_estimate": 0.0,
                            "last_task_at": "2026-08-10T11:01:00",
                            "governance": {
                                "profiles": ["planning_only"],
                                "provider_sources": [
                                    "suite_api_key=hidden",
                                    "fallback_access_token=hidden",
                                ],
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner"],
                            },
                        }
                    ],
                    "top_tasks": [
                        {
                            "task_id": "task-response-source-redaction",
                            "session_id": "session-response-source-redaction",
                            "session_title": "Provider Source Redaction",
                            "prompt_excerpt": "provider source response redaction",
                            "total_tokens": 0,
                            "cost_estimate": 0.0,
                            "created_at": "2026-08-10T11:00:00",
                            "updated_at": "2026-08-10T11:01:00",
                            "source_kind": "provider",
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

            response = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=8,
                top_tasks=12,
                source_kind="all",
                tool_registry_profile=None,
                tool_registry_provider_source=None,
                current_user={"id": "user-response-source-redaction"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = original_response_summary  # type: ignore[attr-defined]

        self.assertEqual(
            response.by_session[0].governance.provider_sources,
            ["suite_[redacted]", "fallback_[redacted]"],
        )
        self.assertEqual(
            response.top_tasks[0].governance.provider_source,
            "suite_[redacted]",
        )
        response_blob = json.dumps(response.model_dump(), default=str)
        self.assertNotIn("api_key=hidden", response_blob)
        self.assertNotIn("access_token=hidden", response_blob)

    def test_task_list_response_preserves_cross_item_provider_source_aliases(
        self,
    ) -> None:
        original_list_tasks = task_routes_module.list_tasks
        original_count_tasks = task_routes_module.count_tasks
        try:
            task_routes_module.list_tasks = lambda **_kwargs: [
                {
                    "id": "task-list-source-api-key",
                    "session_id": "session-list-source-alias",
                    "prompt": "provider source alias api key",
                    "status": "completed",
                    "governance": {
                        "profile": "planning_only",
                        "provider_source": "suite_api_key=one",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "trace_json": None,
                    "usage_json": None,
                    "created_at": "2026-08-10T13:00:00",
                    "updated_at": "2026-08-10T13:01:00",
                },
                {
                    "id": "task-list-source-access-token",
                    "session_id": "session-list-source-alias",
                    "prompt": "provider source alias access token",
                    "status": "completed",
                    "governance": {
                        "profile": "planning_only",
                        "provider_source": "suite_access_token=two",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner"],
                    },
                    "trace_json": None,
                    "usage_json": None,
                    "created_at": "2026-08-10T13:00:00",
                    "updated_at": "2026-08-10T13:01:00",
                },
            ]
            task_routes_module.count_tasks = lambda *_args, **_kwargs: 2

            response = task_routes_module.get_tasks(
                limit=20,
                offset=0,
                session_id=None,
                query=None,
                tool_registry_profile=None,
                tool_registry_provider_source=None,
                current_user={"id": "user-list-source-alias"},
            )
        finally:
            task_routes_module.list_tasks = original_list_tasks
            task_routes_module.count_tasks = original_count_tasks

        self.assertEqual(
            response.items[0].governance.provider_source,
            "suite_[redacted]#1",
        )
        self.assertEqual(
            response.items[1].governance.provider_source,
            "suite_[redacted]#2",
        )
        response_blob = json.dumps(response.model_dump(), default=str)
        self.assertNotIn("api_key=one", response_blob)
        self.assertNotIn("access_token=two", response_blob)
