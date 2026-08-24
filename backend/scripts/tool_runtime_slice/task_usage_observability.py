from __future__ import annotations

from .context import *


class TaskUsageObservabilityMixin:
    def test_get_task_response_summary_surfaces_failure_hint(self) -> None:
        payload = chat_persistence_module.get_task_response_summary_from_task(
            {
                "id": "task-detail-failure-hint",
                "session_id": "session-detail-failure-hint",
                "prompt": "task detail should surface failed task hint",
                "status": "failed",
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
                "usage_json": None,
                "created_at": "2026-08-14T10:00:00",
                "updated_at": "2026-08-14T10:05:00",
            }
        )

        self.assertEqual(payload["failure_hint"], "upstream timed out after 30s")
        self.assertEqual(payload["failure_source"], "tool_error")

    def test_task_response_model_preserves_failure_hint(self) -> None:
        response = task_routes_module.TaskResponse(
            id="task-detail-failure-hint",
            session_id="session-detail-failure-hint",
            prompt="task detail should surface failed task hint",
            status="failed",
            status_normalized="failed",
            status_label="Failed",
            status_rank=5,
            trace_json=None,
            usage_json=None,
            failure_hint="upstream timed out after 30s",
            failure_source="tool_error",
            created_at="2026-08-14T10:00:00",
            updated_at="2026-08-14T10:05:00",
        )

        self.assertEqual(
            response.failure_hint,  # type: ignore[attr-defined]
            "upstream timed out after 30s",
        )
        self.assertEqual(
            response.failure_source,  # type: ignore[attr-defined]
            "tool_error",
        )

    def test_get_task_recovers_failure_hint_from_task_failed_audit_event(self) -> None:
        task_row = {
            "id": "task-detail-audit-failure",
            "session_id": "session-detail-audit-failure",
            "prompt": "task detail should recover audit failure hint",
            "status": "failed",
            "trace_json": "[]",
            "usage_json": None,
            "tool_registry_profile": None,
            "tool_registry_provider_source": None,
            "allowed_tool_names_json": None,
            "allowed_tool_labels_json": None,
            "created_at": "2026-08-14T10:00:00",
            "updated_at": "2026-08-14T10:05:00",
        }
        audit_row = {
            "event_detail_json": json.dumps(
                {
                    "task_id": "task-detail-audit-failure",
                    "code": "remote_provider_network_error",
                    "message": "Remote provider stream network error",
                }
            )
        }

        class FakeCursor:
            def __init__(self, row):
                self._row = row

            def fetchone(self):
                return self._row

        class FakeConnection:
            def execute(self, query, _params=()):
                if "FROM tasks" in query:
                    return FakeCursor(task_row)
                if "FROM audit_logs" in query:
                    return FakeCursor(audit_row)
                raise AssertionError(f"unexpected query: {query}")

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            task = chat_persistence_module.get_task(
                "task-detail-audit-failure",
                "user-detail-audit-failure",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual(task["failure_hint"], "remote_provider_network_error")
        self.assertEqual(task["failure_source"], "error_event")

    def test_list_tasks_recovers_failure_hint_from_task_failed_audit_events(
        self,
    ) -> None:
        task_rows = [
            {
                "id": "task-list-audit-failure",
                "session_id": "session-list-audit-failure",
                "prompt": "task center should recover audit failure hint",
                "status": "failed",
                "trace_json": "[]",
                "usage_json": None,
                "tool_registry_profile": None,
                "tool_registry_provider_source": None,
                "allowed_tool_names_json": None,
                "allowed_tool_labels_json": None,
                "created_at": "2026-08-14T10:00:00",
                "updated_at": "2026-08-14T10:05:00",
            },
            {
                "id": "task-list-completed",
                "session_id": "session-list-audit-failure",
                "prompt": "completed task should stay clean",
                "status": "completed",
                "trace_json": "[]",
                "usage_json": None,
                "tool_registry_profile": None,
                "tool_registry_provider_source": None,
                "allowed_tool_names_json": None,
                "allowed_tool_labels_json": None,
                "created_at": "2026-08-14T10:00:00",
                "updated_at": "2026-08-14T10:04:00",
            },
        ]
        audit_rows = [
            {
                "event_detail_json": json.dumps(
                    {
                        "task_id": "task-list-audit-failure",
                        "code": "remote_provider_network_error",
                        "message": "Remote provider stream network error",
                    }
                )
            }
        ]

        class FakeCursor:
            def __init__(self, rows):
                self._rows = rows

            def fetchall(self):
                return self._rows

        class FakeConnection:
            def execute(self, query, _params=()):
                if "FROM tasks" in query:
                    return FakeCursor(task_rows)
                if "FROM audit_logs" in query:
                    return FakeCursor(audit_rows)
                raise AssertionError(f"unexpected query: {query}")

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            tasks = chat_persistence_module.list_tasks(
                "user-list-audit-failure",
                limit=10,
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(tasks[0]["failure_hint"], "remote_provider_network_error")
        self.assertEqual(tasks[0]["failure_source"], "error_event")
        self.assertNotIn("failure_hint", tasks[1])

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
