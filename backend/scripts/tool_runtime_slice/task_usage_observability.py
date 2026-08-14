from __future__ import annotations

from .context import *


class TaskUsageObservabilityMixin:
    def test_get_tasks_usage_dashboard_top_task_surfaces_failure_hint(
        self,
    ) -> None:
        rows = [
            {
                "id": "task-usage-failure-hint",
                "session_id": "session-usage-failure-hint",
                "prompt": "usage dashboard should surface failed top task",
                "status": "failed",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 7,
                        "completion_tokens": 9,
                        "cost_estimate": 0.03,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "tool-step-failed",
                            "type": "action",
                            "content": "Tool call failed.",
                            "seq": 1,
                            "meta": {
                                "tool": {
                                    "name": "provider_search",
                                    "error": "upstream timed out after 30s",
                                }
                            },
                        }
                    ]
                ),
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["provider_search"]),
                "allowed_tool_labels_json": json.dumps(["Provider Search"]),
                "created_at": "2026-08-14T10:00:00",
                "updated_at": "2026-08-14T10:05:00",
                "session_title": "Usage Failure Session",
            }
        ]

        class FakeCursor:
            def fetchall(self):
                return rows

        class FakeConnection:
            def execute(self, _query, _params=()):
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-failure-hint"
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(len(payload["top_tasks"]), 1)
        top_task = payload["top_tasks"][0]
        self.assertEqual(top_task["failure_hint"], "upstream timed out after 30s")
        self.assertEqual(top_task["failure_source"], "tool_error")
        self.assertNotIn("trace_json", top_task)

    def test_get_tasks_usage_dashboard_response_preserves_failure_hint(
        self,
    ) -> None:
        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(
            {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 7,
                    "completion_tokens": 9,
                    "total_tokens": 16,
                    "cost_estimate": 0.03,
                    "avg_total_tokens": 16.0,
                    "avg_cost_estimate": 0.03,
                },
                "trend": [],
                "by_session": [],
                "top_tasks": [
                    {
                        "task_id": "task-usage-failure-hint",
                        "session_id": "session-usage-failure-hint",
                        "session_title": "Usage Failure Session",
                        "prompt_excerpt": "usage dashboard should surface failed top task",
                        "total_tokens": 16,
                        "cost_estimate": 0.03,
                        "created_at": "2026-08-14T10:00:00",
                        "updated_at": "2026-08-14T10:05:00",
                        "source_kind": "provider",
                        "failure_hint": "upstream timed out after 30s",
                        "failure_source": "tool_error",
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "planning_suite",
                            "allowed_tool_names": ["provider_search"],
                            "allowed_tool_labels": ["Provider Search"],
                        },
                    }
                ],
            }
        )

        self.assertEqual(
            payload["top_tasks"][0]["failure_hint"], "upstream timed out after 30s"
        )
        self.assertEqual(payload["top_tasks"][0]["failure_source"], "tool_error")
        response = task_routes_module.TaskUsageDashboardResponse(**payload)
        self.assertEqual(
            response.top_tasks[0].failure_hint,  # type: ignore[attr-defined]
            "upstream timed out after 30s",
        )
        self.assertEqual(
            response.top_tasks[0].failure_source,  # type: ignore[attr-defined]
            "tool_error",
        )
