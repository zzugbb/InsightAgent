from __future__ import annotations

from .context import *


class TaskUsageDashboardMixin:
    def test_get_tasks_usage_dashboard_response_summary_plain_clones_governance_dicts(
        self,
    ) -> None:
        class GuardedTopTaskGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "get_tasks_usage_dashboard_response_summary should plain-clone top-task governance dicts before outward model validation"
                )

        class GuardedSessionGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "get_tasks_usage_dashboard_response_summary should plain-clone session governance dicts before outward model validation"
                )

        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(  # type: ignore[attr-defined]
            {
                "window_days": 14,
                "summary": {"tasks_total": 1},
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-summary",
                        "session_title": "Usage Summary Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "last_task_at": "2026-06-22T20:00:00",
                        "governance": GuardedSessionGovernanceDict(
                            profiles=["planning_only"],
                            provider_sources=["planning_suite"],
                            allowed_tool_names=["task_plan"],
                            allowed_tool_labels=["Task Planner Suite"],
                        ),
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-usage-summary",
                        "session_id": "session-usage-summary",
                        "session_title": "Usage Summary Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-22T20:00:00",
                        "updated_at": "2026-06-22T20:05:00",
                        "source_kind": "provider",
                        "governance": GuardedTopTaskGovernanceDict(
                            profile="planning_only",
                            provider_source="planning_suite",
                            allowed_tool_names=["task_plan"],
                            allowed_tool_labels=["Task Planner Suite"],
                        ),
                    }
                ],
            }
        )

        self.assertIsInstance(payload["by_session"][0]["governance"], dict)
        self.assertNotIsInstance(
            payload["by_session"][0]["governance"],
            GuardedSessionGovernanceDict,
        )
        self.assertEqual(
            payload["by_session"][0]["governance"],
            {
                "profiles": ["planning_only"],
                "provider_sources": ["planning_suite"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )
        self.assertIsInstance(payload["top_tasks"][0]["governance"], dict)
        self.assertNotIsInstance(
            payload["top_tasks"][0]["governance"],
            GuardedTopTaskGovernanceDict,
        )
        self.assertEqual(
            payload["top_tasks"][0]["governance"],
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_response_summary_coerces_response_ready_models(
        self,
    ) -> None:
        class ResponseReadyBlock:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(  # type: ignore[attr-defined]
            {
                "window_days": 14,
                "summary": ResponseReadyBlock(
                    {
                        "tasks_total": 2,
                        "tasks_with_usage": 2,
                    }
                ),
                "trend": [
                    ResponseReadyBlock(
                        {
                            "date": "2026-06-22",
                            "tasks_with_usage": 2,
                            "total_tokens": 123,
                            "cost_estimate": 0.45,
                        }
                    )
                ],
                "by_session": [
                    ResponseReadyBlock(
                        {
                            "session_id": "session-ready-model",
                            "session_title": "Ready Model Session",
                            "tasks_with_usage": 2,
                            "total_tokens": 123,
                            "cost_estimate": 0.45,
                            "last_task_at": "2026-06-22T20:00:00",
                            "governance": {
                                "profiles": ["planning_only"],
                                "provider_sources": ["planning_suite"],
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    )
                ],
                "top_tasks": [
                    ResponseReadyBlock(
                        {
                            "task_id": "task-ready-model",
                            "session_id": "session-ready-model",
                            "session_title": "Ready Model Session",
                            "prompt_excerpt": "ready model task",
                            "total_tokens": 123,
                            "cost_estimate": 0.45,
                            "created_at": "2026-06-22T20:00:00",
                            "updated_at": "2026-06-22T20:05:00",
                            "source_kind": "provider",
                            "governance": {
                                "profile": "planning_only",
                                "provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    )
                ],
            }
        )

        self.assertEqual(
            payload["summary"],
            {
                "tasks_total": 2,
                "tasks_with_usage": 2,
            },
        )
        self.assertEqual(payload["trend"][0]["date"], "2026-06-22")
        self.assertEqual(payload["by_session"][0]["session_id"], "session-ready-model")
        self.assertEqual(payload["by_session"][0]["total_tokens"], 123)
        self.assertEqual(payload["top_tasks"][0]["task_id"], "task-ready-model")
        self.assertEqual(payload["top_tasks"][0]["source_kind"], "provider")
        self.assertEqual(
            payload["top_tasks"][0]["governance"]["profile"],
            "planning_only",
        )

    def test_get_tasks_usage_dashboard_response_summary_normalizes_plain_wrapped_rows(
        self,
    ) -> None:
        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(  # type: ignore[attr-defined]
            {
                "window_days": 14,
                "summary": {
                    "tasks_total": 2,
                    "source_tasks_provider": 1,
                },
                "trend": [
                    {
                        "date": UserString("2026-06-22"),
                        "tasks_with_usage": 2,
                        "total_tokens": 123,
                        "cost_estimate": 0.45,
                    }
                ],
                "by_session": [
                    {
                        "session_id": UserString("session-plain-wrapped"),
                        "session_title": UserString("Plain Wrapped Session"),
                        "tasks_with_usage": 2,
                        "total_tokens": 123,
                        "cost_estimate": 0.45,
                        "last_task_at": UserString("2026-06-22T20:00:00"),
                        "governance": {
                            "profiles": [UserString("planning_only")],
                            "provider_sources": [UserString("planning_suite")],
                            "allowed_tool_names": [UserString("task_plan")],
                            "allowed_tool_labels": [UserString("Task Planner Suite")],
                        },
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": UserString("task-plain-wrapped"),
                        "session_id": UserString("session-plain-wrapped"),
                        "session_title": UserString("Plain Wrapped Session"),
                        "prompt_excerpt": UserString("plain wrapped task"),
                        "total_tokens": 123,
                        "cost_estimate": 0.45,
                        "created_at": UserString("2026-06-22T20:00:00"),
                        "updated_at": UserString("2026-06-22T20:05:00"),
                        "source_kind": UserString("provider"),
                        "governance": {
                            "profile": UserString("planning_only"),
                            "provider_source": UserString("planning_suite"),
                            "allowed_tool_names": [UserString("task_plan")],
                            "allowed_tool_labels": [UserString("Task Planner Suite")],
                        },
                    }
                ],
            }
        )

        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertEqual(payload["trend"][0]["date"], "2026-06-22")
        self.assertEqual(payload["by_session"][0]["session_title"], "Plain Wrapped Session")
        self.assertEqual(payload["by_session"][0]["governance"]["profiles"], ["planning_only"])
        self.assertEqual(payload["top_tasks"][0]["task_id"], "task-plain-wrapped")
        self.assertEqual(payload["top_tasks"][0]["source_kind"], "provider")
        self.assertNotIn("UserString", serialized)

    def test_get_tasks_usage_dashboard_response_summary_coerces_governance_models(
        self,
    ) -> None:
        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        session_governance = ResponseReadyGovernance(
            {
                "profiles": ["planning_only"],
                "provider_sources": ["planning_suite"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            }
        )
        task_governance = ResponseReadyGovernance(
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            }
        )
        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(  # type: ignore[attr-defined]
            {
                "window_days": 14,
                "summary": {},
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-governance-model",
                        "tasks_with_usage": 1,
                        "total_tokens": 10,
                        "cost_estimate": 0.1,
                        "governance": session_governance,
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-governance-model",
                        "session_id": "session-governance-model",
                        "prompt_excerpt": "governance model",
                        "total_tokens": 10,
                        "cost_estimate": 0.1,
                        "created_at": "2026-06-22T20:00:00",
                        "updated_at": "2026-06-22T20:05:00",
                        "governance": task_governance,
                    }
                ],
            }
        )

        self.assertIsInstance(payload["by_session"][0]["governance"], dict)
        self.assertIsNot(payload["by_session"][0]["governance"], session_governance)
        self.assertEqual(
            payload["by_session"][0]["governance"]["profiles"],
            ["planning_only"],
        )
        self.assertIsInstance(payload["top_tasks"][0]["governance"], dict)
        self.assertIsNot(payload["top_tasks"][0]["governance"], task_governance)
        self.assertEqual(
            payload["top_tasks"][0]["governance"]["profile"],
            "planning_only",
        )

    def test_get_tasks_usage_dashboard_response_summary_normalizes_governance_models_with_provider_source_context(
        self,
    ) -> None:
        class ResponseReadyGovernance:
            def __init__(self, payload):
                self._payload = payload

            def model_dump(self):
                return dict(self._payload)

        session_governance = ResponseReadyGovernance(
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )
        task_governance = ResponseReadyGovernance(
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["calc_eval"],
            }
        )
        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(  # type: ignore[attr-defined]
            {
                "window_days": 14,
                "summary": {},
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-governance-source-model",
                        "tasks_with_usage": 1,
                        "total_tokens": 10,
                        "cost_estimate": 0.1,
                        "governance": session_governance,
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-governance-source-model",
                        "session_id": "session-governance-source-model",
                        "prompt_excerpt": "governance source model",
                        "total_tokens": 10,
                        "cost_estimate": 0.1,
                        "created_at": "2026-06-22T20:00:00",
                        "updated_at": "2026-06-22T20:05:00",
                        "governance": task_governance,
                    }
                ],
            }
        )

        self.assertEqual(
            payload["by_session"][0]["governance"],
            {
                "profiles": ["calculator_only"],
                "provider_sources": ["calculator_suite"],
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )
        self.assertEqual(
            payload["top_tasks"][0]["governance"],
            {
                "profile": "calculator_only",
                "provider_source": "calculator_suite",
                "allowed_tool_names": ["calc_eval"],
                "allowed_tool_labels": ["Calculator Suite"],
            },
        )

    def test_task_route_module_does_not_expose_dead_clone_builders(self) -> None:
        self.assertFalse(
            hasattr(task_routes_module, "_build_task_governance_summary_from_clone")
        )
        self.assertFalse(
            hasattr(
                task_routes_module,
                "_build_task_usage_session_governance_summary_from_clone",
            )
        )

    def test_task_route_module_does_not_expose_dead_local_clone_helpers(self) -> None:
        self.assertFalse(hasattr(task_routes_module, "_clone_task_governance"))
        self.assertFalse(hasattr(task_routes_module, "_clone_session_governance_summary"))

    def test_task_route_module_does_not_expose_dead_trace_json_governance_collector(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_collect_task_governance_from_trace_json"))

    def test_task_route_module_does_not_expose_dead_task_response_builder(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_build_task_response"))

    def test_task_response_route_coercion_redacts_http_json_trace_json(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="task-response-route-http-json-trace-json"
        )

        payload = task_routes_module._coerce_task_response_summary(  # type: ignore[attr-defined]
            {
                "id": "task-response-route-trace-json-safe",
                "session_id": "session-response-route-trace-json-safe",
                "prompt": "response route trace json safe",
                "status": "completed",
                "trace_json": json.dumps([raw_step], ensure_ascii=False),
                "usage_json": None,
                "created_at": "2026-07-20T10:00:00",
                "updated_at": "2026-07-20T10:01:00",
            }
        )

        serialized = str(payload["trace_json"])
        parsed = json.loads(serialized)

        self.assertIsInstance(payload["trace_json"], str)
        self.assertIn("gateway token=[redacted]", serialized)
        self.assertIn("preview token=[redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)
        self.assertEqual(parsed[0]["id"], "task-response-route-http-json-trace-json")

    def test_task_route_module_does_not_expose_dead_status_meta_helper(self) -> None:
        self.assertFalse(hasattr(task_routes_module, "_with_status_meta"))

    def test_task_route_module_does_not_expose_dead_task_governance_collector(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_collect_task_governance_from_task"))

    def test_task_route_module_does_not_expose_dead_trace_governance_export_helper(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_collect_trace_governance_export"))

    def test_task_route_module_does_not_expose_dead_usage_row_builders(self) -> None:
        self.assertFalse(hasattr(task_routes_module, "_build_task_usage_top_task_row"))
        self.assertFalse(hasattr(task_routes_module, "_build_task_usage_by_session_row"))

    def test_task_route_module_does_not_expose_dead_task_export_governance_helpers(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(task_routes_module, "_collect_task_governance_summary_from_trace_steps")
        )
        self.assertFalse(
            hasattr(task_routes_module, "_build_task_export_governance_from_summary")
        )

    def test_task_route_module_does_not_expose_dead_task_usage_blob_parser(
        self,
    ) -> None:
        self.assertFalse(hasattr(task_routes_module, "_parse_task_usage_blob"))

    def test_get_tasks_usage_dashboard_top_task_surfaces_governance_summary(self) -> None:
        rows = [
            {
                "id": "task-usage-governance-1",
                "session_id": "session-usage-governance",
                "prompt": "usage dashboard governance task",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 12,
                        "completion_tokens": 34,
                        "cost_estimate": 0.12,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-governance-1",
                            "type": "thought",
                            "content": "Planner constrained the task.",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "planning_only",
                                "tool_registry_provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T10:00:00",
                "updated_at": "2026-06-09T10:05:00",
                "session_title": "Usage Governance Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-governance",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        top_tasks = payload["top_tasks"]
        self.assertEqual(len(top_tasks), 1)
        row = top_tasks[0]
        self.assertEqual(row["task_id"], "task-usage-governance-1")
        self.assertEqual(row["source_kind"], "provider")
        self.assertEqual(
            row["governance"],
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_summary_reuses_shared_usage_json_parser(self) -> None:
        rows = [
            {"usage_json": "usage-json-1"},
            {"usage_json": "usage-json-2"},
        ]

        class FakeCursor:
            def fetchall(self) -> list[dict]:
                return rows

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_parser = chat_persistence_module._parse_usage_json_blob  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._parse_usage_json_blob = lambda raw: captured.append(raw) or {  # type: ignore[attr-defined]
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "cost_estimate": 0.05,
                "usage_source": "provider",
            }
            payload = chat_persistence_module.get_tasks_usage_summary("user-usage-parser")
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._parse_usage_json_blob = original_parser  # type: ignore[attr-defined]

        self.assertEqual(captured, ["usage-json-1", "usage-json-2"])
        self.assertEqual(payload["tasks_with_usage"], 2)
        self.assertEqual(payload["source_tasks_provider"], 2)
        self.assertEqual(payload["prompt_tokens"], 20)
        self.assertEqual(payload["completion_tokens"], 30)
        self.assertEqual(payload["total_tokens"], 50)

    def test_get_tasks_usage_dashboard_top_task_prefers_persisted_governance_columns(self) -> None:
        rows = [
            {
                "id": "task-usage-governance-columns-1",
                "session_id": "session-usage-governance-columns",
                "prompt": "usage dashboard governance task with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 12,
                        "completion_tokens": 34,
                        "cost_estimate": 0.12,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Usage Governance Columns Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-governance-columns",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        top_tasks = payload["top_tasks"]
        self.assertEqual(len(top_tasks), 1)
        row = top_tasks[0]
        self.assertEqual(
            row["governance"],
            {
                "profile": "planning_only",
                "provider_source": "planning_suite",
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_reuses_with_task_governance_helper(self) -> None:
        rows = [
            {
                "id": "task-usage-shared-row-helper-1",
                "session_id": "session-usage-shared-row-helper",
                "prompt": "usage dashboard should reuse shared task row helper",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 8,
                        "completion_tokens": 5,
                        "cost_estimate": 0.02,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": "poisoned-trace-json",
                "tool_registry_profile": "poisoned_profile",
                "tool_registry_provider_source": "poisoned_source",
                "allowed_tool_names_json": json.dumps(["poisoned_tool"]),
                "allowed_tool_labels_json": json.dumps(["Poisoned Tool"]),
                "created_at": "2026-06-17T22:00:00",
                "updated_at": "2026-06-17T22:05:00",
                "session_title": "Usage Shared Row Helper Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_with_task_governance = chat_persistence_module._with_task_governance  # type: ignore[attr-defined]
        original_extractor = chat_persistence_module._extract_task_governance_from_task_row  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._with_task_governance = (  # type: ignore[attr-defined]
                lambda task: captured.append(task)
                or {
                    "id": task["id"],
                    "session_id": task["session_id"],
                    "prompt": task["prompt"],
                    "usage_json": task["usage_json"],
                    "trace_json": task["trace_json"],
                    "created_at": task["created_at"],
                    "updated_at": task["updated_at"],
                    "session_title": task["session_title"],
                    "governance": {
                        "profile": "shared_profile",
                        "provider_source": "shared_source",
                        "allowed_tool_names": ["shared_tool"],
                        "allowed_tool_labels": ["Shared Tool"],
                    },
                }
            )
            chat_persistence_module._extract_task_governance_from_task_row = (  # type: ignore[attr-defined]
                lambda _task: (_ for _ in ()).throw(
                    AssertionError(
                        "usage dashboard should reuse _with_task_governance instead of directly reusing the row governance extractor"
                    )
                )
            )
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-shared-row-helper"
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._with_task_governance = original_with_task_governance  # type: ignore[attr-defined]
            chat_persistence_module._extract_task_governance_from_task_row = original_extractor  # type: ignore[attr-defined]

        self.assertEqual(captured, [rows[0]])
        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertEqual(
            payload["top_tasks"][0]["governance"],
            {
                "profile": "shared_profile",
                "provider_source": "shared_source",
                "allowed_tool_names": ["shared_tool"],
                "allowed_tool_labels": ["Shared Tool"],
            },
        )
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(
            payload["by_session"][0]["governance"],
            {
                "profiles": ["shared_profile"],
                "provider_sources": ["shared_source"],
                "allowed_tool_names": ["shared_tool"],
                "allowed_tool_labels": ["Shared Tool"],
            },
        )

    def test_get_tasks_usage_dashboard_reuses_shared_usage_json_parser(self) -> None:
        rows = [
            {
                "id": "task-usage-parser-1",
                "session_id": "session-usage-parser-1",
                "prompt": "usage parser task",
                "usage_json": "usage-json-1",
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-16T10:00:00",
                "updated_at": "2026-06-16T10:05:00",
                "session_title": "Usage Parser Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_parser = chat_persistence_module._parse_usage_json_blob  # type: ignore[attr-defined]
        captured: list[object] = []
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._parse_usage_json_blob = lambda raw: captured.append(raw) or {  # type: ignore[attr-defined]
                "prompt_tokens": 11,
                "completion_tokens": 13,
                "cost_estimate": 0.07,
                "usage_source": "provider",
            }
            payload = chat_persistence_module.get_tasks_usage_dashboard("user-usage-parser")
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._parse_usage_json_blob = original_parser  # type: ignore[attr-defined]

        self.assertEqual(captured, ["usage-json-1"])
        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(payload["summary"]["prompt_tokens"], 11)
        self.assertEqual(payload["summary"]["completion_tokens"], 13)
        self.assertEqual(payload["summary"]["total_tokens"], 24)
        self.assertEqual(len(payload["top_tasks"]), 1)

    def test_get_tasks_usage_dashboard_top_tasks_do_not_expose_dead_trace_json(
        self,
    ) -> None:
        rows = [
            {
                "id": "task-usage-no-trace-json-1",
                "session_id": "session-usage-no-trace-json",
                "prompt": "usage top tasks should not surface dead trace json",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 7,
                        "completion_tokens": 9,
                        "cost_estimate": 0.03,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": "poisoned-trace-json",
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner"]),
                "created_at": "2026-06-17T21:00:00",
                "updated_at": "2026-06-17T21:05:00",
                "session_title": "Usage No Trace JSON Session",
            }
        ]
        original_get_db_connection = chat_persistence_module.get_db_connection

        class FakeCursor:
            def fetchall(self):
                return rows

        class FakeConnection:
            def execute(self, _query, _params):
                return FakeCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-no-trace-json"
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertNotIn("trace_json", payload["top_tasks"][0])

    def test_get_tasks_usage_dashboard_route_surfaces_top_task_governance_summary(self) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [],
                "top_tasks": [
                    {
                        "task_id": "task-usage-governance-1",
                        "session_id": "session-usage-governance",
                        "session_title": "Usage Governance Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-09T10:00:00",
                        "updated_at": "2026-06-09T10:05:00",
                        "source_kind": "provider",
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "planning_suite",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
            }

            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-governance"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard

        self.assertEqual(len(payload.top_tasks), 1)
        row = payload.top_tasks[0]
        self.assertEqual(row.source_kind, "provider")
        self.assertIsNotNone(row.governance)
        assert row.governance is not None
        self.assertEqual(row.governance.profile, "planning_only")
        self.assertEqual(row.governance.provider_source, "planning_suite")
        self.assertEqual(row.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(row.governance.allowed_tool_labels, ["Task Planner Suite"])

    def test_get_tasks_usage_dashboard_route_trusts_top_task_governance_shape(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        try:
            class GuardedGovernanceDict(dict):
                def get(self, *_args, **_kwargs):
                    raise AssertionError(
                        "usage top-task route should construct outward model directly from service governance dict"
                    )

            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [],
                "top_tasks": [
                    {
                        "task_id": "task-usage-top-dict-builder-1",
                        "session_id": "session-usage-top-dict-builder",
                        "session_title": "Usage Governance Dict Builder Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-15T18:00:00",
                        "updated_at": "2026-06-15T18:05:00",
                        "source_kind": "provider",
                        "governance": GuardedGovernanceDict(
                            profile="guarded_profile",
                            provider_source="guarded_source",
                            allowed_tool_names=["guarded_tool"],
                            allowed_tool_labels=["Guarded Tool"],
                        ),
                        "trace_json": None,
                    }
                ],
            }
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-top-dict-builder"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
        self.assertIsNotNone(payload.top_tasks[0].governance)
        assert payload.top_tasks[0].governance is not None
        self.assertEqual(payload.top_tasks[0].governance.profile, "guarded_profile")
        self.assertEqual(
            payload.top_tasks[0].governance.provider_source, "guarded_source"
        )
        self.assertEqual(
            payload.top_tasks[0].governance.allowed_tool_names, ["guarded_tool"]
        )
        self.assertEqual(
            payload.top_tasks[0].governance.allowed_tool_labels, ["Guarded Tool"]
        )

    def test_get_tasks_usage_dashboard_route_trusts_service_top_task_governance(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_row_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            class GuardedGovernanceDict(dict):
                def get(self, *_args, **_kwargs):
                    raise AssertionError(
                        "usage top-task route should construct outward model directly from the service governance dict"
                    )

            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [],
                "top_tasks": [
                    {
                        "task_id": "task-usage-top-persisted-builder-1",
                        "session_id": "session-usage-top-persisted-builder",
                        "session_title": "Usage Persisted Governance Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-16T18:00:00",
                        "updated_at": "2026-06-16T18:05:00",
                        "source_kind": "provider",
                        "governance": GuardedGovernanceDict(
                            profile="guarded_profile",
                            provider_source="guarded_source",
                            allowed_tool_names=["guarded_tool"],
                            allowed_tool_labels=["Guarded Tool"],
                        ),
                        "tool_registry_profile": "poisoned_profile",
                        "tool_registry_provider_source": "poisoned_source",
                        "allowed_tool_names_json": json.dumps(["poisoned_tool"]),
                        "allowed_tool_labels_json": json.dumps(["Poisoned Tool"]),
                        "trace_json": "poisoned-trace-json",
                    }
                ],
            }
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _row: (_ for _ in ()).throw(
                    AssertionError(
                        "usage top-task route should not fall back to the shared row parser when service governance is already present"
                    )
                )
            )
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-top-persisted-builder"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )

        self.assertIsNotNone(payload.top_tasks[0].governance)
        assert payload.top_tasks[0].governance is not None
        self.assertEqual(payload.top_tasks[0].governance.profile, "guarded_profile")
        self.assertEqual(
            payload.top_tasks[0].governance.provider_source, "guarded_source"
        )
        self.assertEqual(
            payload.top_tasks[0].governance.allowed_tool_names, ["guarded_tool"]
        )
        self.assertEqual(
            payload.top_tasks[0].governance.allowed_tool_labels, ["Guarded Tool"]
        )

    def test_get_tasks_usage_dashboard_route_does_not_fallback_top_task_governance_from_row(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_row_parser = (
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row
        )
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [],
                "top_tasks": [
                    {
                        "task_id": "task-usage-top-no-fallback-1",
                        "session_id": "session-usage-top-no-fallback",
                        "session_title": "Usage No Fallback Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-17T08:00:00",
                        "updated_at": "2026-06-17T08:05:00",
                        "source_kind": "provider",
                        "tool_registry_profile": "poisoned_profile",
                        "tool_registry_provider_source": "poisoned_source",
                        "allowed_tool_names_json": json.dumps(["poisoned_tool"]),
                        "allowed_tool_labels_json": json.dumps(["Poisoned Tool"]),
                        "trace_json": "poisoned-trace-json",
                    }
                ],
            }
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                lambda _row: (_ for _ in ()).throw(
                    AssertionError(
                        "usage top-task route should not fall back to the shared row parser when service governance is absent"
                    )
                )
            )
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-top-no-fallback"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            task_routes_module.chat_persistence_service._extract_task_governance_from_task_row = (
                original_row_parser
            )

        self.assertIsNone(payload.top_tasks[0].governance)

    def test_get_tasks_usage_dashboard_route_passes_raw_governance_dicts_to_usage_models(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_by_session_row = task_routes_module.TaskUsageBySessionRow
        original_top_task_row = task_routes_module.TaskUsageTopTaskRow
        original_dashboard_model = task_routes_module.TaskUsageDashboardResponse
        captured: dict[str, list[object]] = {"by_session": [], "top_tasks": []}
        by_session_governance = {
            "profiles": ["planning_only"],
            "provider_sources": ["planning_suite"],
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        top_task_governance = {
            "profile": "planning_only",
            "provider_source": "planning_suite",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-raw-governance",
                        "session_title": "Usage Raw Governance Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "last_task_at": "2026-06-18T10:20:00",
                        "governance": by_session_governance,
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-usage-raw-governance",
                        "session_id": "session-usage-raw-governance",
                        "session_title": "Usage Raw Governance Session",
                        "prompt_excerpt": "usage dashboard governance task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-18T10:20:00",
                        "updated_at": "2026-06-18T10:25:00",
                        "source_kind": "provider",
                        "governance": top_task_governance,
                    }
                ],
            }
            task_routes_module.TaskUsageBySessionRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageBySessionRow(...)"
                )
            )
            task_routes_module.TaskUsageTopTaskRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageTopTaskRow(...)"
                )
            )
            task_routes_module.TaskUsageDashboardResponse = (
                lambda **kwargs: captured.__setitem__(
                    "by_session",
                    [row["governance"] for row in kwargs["by_session"]],
                )
                or captured.__setitem__(
                    "top_tasks",
                    [row["governance"] for row in kwargs["top_tasks"]],
                )
                or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-raw-governance"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            task_routes_module.TaskUsageBySessionRow = original_by_session_row
            task_routes_module.TaskUsageTopTaskRow = original_top_task_row
            task_routes_module.TaskUsageDashboardResponse = original_dashboard_model

        self.assertEqual(captured["by_session"], [by_session_governance])
        self.assertEqual(captured["top_tasks"], [top_task_governance])

    def test_get_tasks_usage_dashboard_route_reuses_shared_response_summary_helper_for_governance(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_tasks_usage_dashboard_response_summary",
            None,
        )
        original_by_session_row = task_routes_module.TaskUsageBySessionRow
        original_top_task_row = task_routes_module.TaskUsageTopTaskRow
        original_dashboard_model = task_routes_module.TaskUsageDashboardResponse
        cloned_by_session = {
            "profiles": ["planning_only"],
            "provider_sources": ["planning_suite"],
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        cloned_top_task = {
            "profile": "planning_only",
            "provider_source": "planning_suite",
            "allowed_tool_names": ["task_plan"],
            "allowed_tool_labels": ["Task Planner Suite"],
        }
        captured: dict[str, list[object]] = {"by_session": [], "top_tasks": []}
        try:
            self.assertFalse(hasattr(task_routes_module, "_plain_clone_dict"))
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                    "cost_estimate": 0.12,
                    "avg_total_tokens": 46.0,
                    "avg_cost_estimate": 0.12,
                },
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-clone-helper",
                        "session_title": "Usage Clone Helper Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "last_task_at": "2026-06-18T12:10:00",
                        "governance": {
                            "profiles": ["poisoned_profile"],
                            "provider_sources": ["poisoned_source"],
                        },
                    }
                ],
                "top_tasks": [
                    {
                        "task_id": "task-usage-clone-helper",
                        "session_id": "session-usage-clone-helper",
                        "session_title": "Usage Clone Helper Session",
                        "prompt_excerpt": "usage clone helper task",
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "created_at": "2026-06-18T12:10:00",
                        "updated_at": "2026-06-18T12:15:00",
                        "source_kind": "provider",
                        "governance": {
                            "profile": "poisoned_profile",
                            "provider_source": "poisoned_source",
                        },
                    }
                ],
            }
            task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = (  # type: ignore[attr-defined]
                lambda payload: {
                    **payload,
                    "by_session": [
                        {
                            "session_id": "session-usage-clone-helper",
                            "session_title": "Usage Clone Helper Session",
                            "tasks_with_usage": 1,
                            "total_tokens": 46,
                            "cost_estimate": 0.12,
                            "last_task_at": "2026-06-18T12:10:00",
                            "governance": cloned_by_session,
                        }
                    ],
                    "top_tasks": [
                        {
                            "task_id": "task-usage-clone-helper",
                            "session_id": "session-usage-clone-helper",
                            "session_title": "Usage Clone Helper Session",
                            "prompt_excerpt": "usage clone helper task",
                            "total_tokens": 46,
                            "cost_estimate": 0.12,
                            "created_at": "2026-06-18T12:10:00",
                            "updated_at": "2026-06-18T12:15:00",
                            "source_kind": "provider",
                            "governance": cloned_top_task,
                        }
                    ],
                }
            )
            task_routes_module.TaskUsageBySessionRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageBySessionRow(...)"
                )
            )
            task_routes_module.TaskUsageTopTaskRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageTopTaskRow(...)"
                )
            )
            task_routes_module.TaskUsageDashboardResponse = (
                lambda **kwargs: captured.__setitem__(
                    "by_session",
                    [row["governance"] for row in kwargs["by_session"]],
                )
                or captured.__setitem__(
                    "top_tasks",
                    [row["governance"] for row in kwargs["top_tasks"]],
                )
                or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-clone-helper"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_tasks_usage_dashboard_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_tasks_usage_dashboard_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = original_response_helper  # type: ignore[attr-defined]
            task_routes_module.TaskUsageBySessionRow = original_by_session_row
            task_routes_module.TaskUsageTopTaskRow = original_top_task_row
            task_routes_module.TaskUsageDashboardResponse = original_dashboard_model

        self.assertEqual(captured["by_session"], [cloned_by_session])
        self.assertEqual(captured["top_tasks"], [cloned_top_task])

    def test_get_tasks_usage_dashboard_route_reuses_top_level_response_model_for_outward_models(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_tasks_usage_dashboard_response_summary",
            None,
        )
        original_usage_summary_model = task_routes_module.TaskUsageSummaryResponse
        original_trend_point_model = task_routes_module.TaskUsageTrendPoint
        original_by_session_model = task_routes_module.TaskUsageBySessionRow
        original_top_task_model = task_routes_module.TaskUsageTopTaskRow
        original_dashboard_model = task_routes_module.TaskUsageDashboardResponse
        captured: list[dict[str, object]] = []
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "ignored": True
            }
            task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = (  # type: ignore[attr-defined]
                lambda _payload: {
                    "window_days": 14,
                    "summary": {
                        "tasks_total": 1,
                        "tasks_with_usage": 1,
                        "source_tasks_provider": 1,
                        "source_tasks_estimated": 0,
                        "source_tasks_mixed": 0,
                        "source_tasks_legacy": 0,
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                        "cost_estimate": 0.12,
                        "avg_total_tokens": 30.0,
                        "avg_cost_estimate": 0.12,
                    },
                    "trend": [
                        {
                            "day": "2026-06-23",
                            "tasks_total": 1,
                            "tasks_with_usage": 1,
                            "prompt_tokens": 10,
                            "completion_tokens": 20,
                            "total_tokens": 30,
                            "cost_estimate": 0.12,
                        }
                    ],
                    "by_session": [
                        {
                            "session_id": "session-usage-outward-model",
                            "session_title": "Usage Session",
                            "tasks_with_usage": 1,
                            "total_tokens": 30,
                            "cost_estimate": 0.12,
                            "last_task_at": "2026-06-23T16:10:00",
                            "governance": {
                                "profiles": ["planning_only"],
                                "provider_sources": ["planning_suite"],
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ],
                    "top_tasks": [
                        {
                            "task_id": "task-usage-outward-model",
                            "session_id": "session-usage-outward-model",
                            "session_title": "Usage Session",
                            "prompt_excerpt": "usage outward model",
                            "total_tokens": 30,
                            "cost_estimate": 0.12,
                            "created_at": "2026-06-23T16:10:00",
                            "updated_at": "2026-06-23T16:11:00",
                            "source_kind": "provider",
                            "governance": {
                                "profile": "planning_only",
                                "provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ],
                }
            )
            task_routes_module.TaskUsageSummaryResponse = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageSummaryResponse(...)"
                )
            )
            task_routes_module.TaskUsageTrendPoint = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageTrendPoint(...)"
                )
            )
            task_routes_module.TaskUsageBySessionRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageBySessionRow(...)"
                )
            )
            task_routes_module.TaskUsageTopTaskRow = lambda **_kwargs: (_ for _ in ()).throw(  # type: ignore[assignment]
                AssertionError(
                    "get_tasks_usage_dashboard_route should reuse TaskUsageDashboardResponse(...) with shared response summary instead of manually constructing TaskUsageTopTaskRow(...)"
                )
            )
            task_routes_module.TaskUsageDashboardResponse = (
                lambda **kwargs: captured.append(kwargs) or SimpleNamespace(**kwargs)
            )  # type: ignore[assignment]
            task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=8,
                top_tasks=12,
                source_kind="all",
                current_user={"id": "user-usage-outward-model"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            if original_response_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_tasks_usage_dashboard_response_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_tasks_usage_dashboard_response_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_tasks_usage_dashboard_response_summary = original_response_helper  # type: ignore[attr-defined]
            task_routes_module.TaskUsageSummaryResponse = original_usage_summary_model
            task_routes_module.TaskUsageTrendPoint = original_trend_point_model
            task_routes_module.TaskUsageBySessionRow = original_by_session_model
            task_routes_module.TaskUsageTopTaskRow = original_top_task_model
            task_routes_module.TaskUsageDashboardResponse = original_dashboard_model

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["window_days"], 14)
        self.assertEqual(captured[0]["summary"]["tasks_total"], 1)
        self.assertEqual(captured[0]["trend"][0]["day"], "2026-06-23")
        self.assertEqual(
            captured[0]["by_session"][0]["governance"]["provider_sources"],
            ["planning_suite"],
        )
        self.assertEqual(
            captured[0]["top_tasks"][0]["governance"]["provider_source"],
            "planning_suite",
        )

    def test_get_tasks_usage_dashboard_by_session_surfaces_governance_summary(self) -> None:
        rows = [
            {
                "id": "task-usage-session-governance-1",
                "session_id": "session-usage-governance",
                "prompt": "usage session governance task",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 20,
                        "completion_tokens": 30,
                        "cost_estimate": 0.15,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-session-governance-1",
                            "type": "thought",
                            "content": "Planner constrained the task.",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "planning_only",
                                "tool_registry_provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T10:00:00",
                "updated_at": "2026-06-09T10:05:00",
                "session_title": "Usage Governance Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-session-governance",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        by_session = payload["by_session"]
        self.assertEqual(len(by_session), 1)
        row = by_session[0]
        self.assertEqual(row["session_id"], "session-usage-governance")
        self.assertEqual(
            row["governance"],
            {
                "profiles": ["planning_only"],
                "provider_sources": ["planning_suite"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_by_session_prefers_persisted_governance_columns(self) -> None:
        rows = [
            {
                "id": "task-usage-session-governance-columns-1",
                "session_id": "session-usage-governance-columns",
                "prompt": "usage session governance task with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 20,
                        "completion_tokens": 30,
                        "cost_estimate": 0.15,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Usage Governance Columns Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-session-governance-columns",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        by_session = payload["by_session"]
        self.assertEqual(len(by_session), 1)
        row = by_session[0]
        self.assertEqual(
            row["governance"],
            {
                "profiles": ["planning_only"],
                "provider_sources": ["planning_suite"],
                "allowed_tool_names": ["task_plan"],
                "allowed_tool_labels": ["Task Planner Suite"],
            },
        )

    def test_get_tasks_usage_dashboard_route_surfaces_session_governance_summary(self) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 20,
                    "completion_tokens": 30,
                    "total_tokens": 50,
                    "cost_estimate": 0.15,
                    "avg_total_tokens": 50.0,
                    "avg_cost_estimate": 0.15,
                },
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-governance",
                        "session_title": "Usage Governance Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 50,
                        "cost_estimate": 0.15,
                        "last_task_at": "2026-06-09T10:05:00",
                        "governance": {
                            "profiles": ["planning_only"],
                            "provider_sources": ["planning_suite"],
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "top_tasks": [],
            }

            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-session-governance"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard

        self.assertEqual(len(payload.by_session), 1)
        row = payload.by_session[0]
        self.assertIsNotNone(row.governance)
        assert row.governance is not None
        self.assertEqual(row.governance.profiles, ["planning_only"])
        self.assertEqual(row.governance.provider_sources, ["planning_suite"])
        self.assertEqual(row.governance.allowed_tool_names, ["task_plan"])
        self.assertEqual(row.governance.allowed_tool_labels, ["Task Planner Suite"])

    def test_get_tasks_usage_dashboard_route_trusts_service_session_governance_summary(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_normalizer = getattr(
            task_routes_module.chat_persistence_service,
            "_normalize_session_governance_summary_dict",
            None,
        )
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 20,
                    "completion_tokens": 30,
                    "total_tokens": 50,
                    "cost_estimate": 0.15,
                    "avg_total_tokens": 50.0,
                    "avg_cost_estimate": 0.15,
                },
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-dict-builder",
                        "session_title": "Usage Governance Dict Builder Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 50,
                        "cost_estimate": 0.15,
                        "last_task_at": "2026-06-15T18:05:00",
                        "governance": {
                            "profiles": ["planning_only"],
                            "provider_sources": ["planning_suite"],
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "top_tasks": [],
            }
            task_routes_module.chat_persistence_service._normalize_session_governance_summary_dict = (  # type: ignore[attr-defined]
                lambda _governance: (_ for _ in ()).throw(
                    AssertionError(
                        "usage by-session route should trust the normalized governance dict from the service"
                    )
                )
            )
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-session-dict-builder"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            if original_normalizer is None:
                delattr(
                    task_routes_module.chat_persistence_service,
                    "_normalize_session_governance_summary_dict",
                )
            else:
                task_routes_module.chat_persistence_service._normalize_session_governance_summary_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertIsNotNone(payload.by_session[0].governance)
        assert payload.by_session[0].governance is not None
        self.assertEqual(payload.by_session[0].governance.profiles, ["planning_only"])
        self.assertEqual(
            payload.by_session[0].governance.provider_sources,
            ["planning_suite"],
        )
        self.assertEqual(
            payload.by_session[0].governance.allowed_tool_names,
            ["task_plan"],
        )
        self.assertEqual(
            payload.by_session[0].governance.allowed_tool_labels,
            ["Task Planner Suite"],
        )

    def test_get_tasks_usage_dashboard_route_trusts_normalized_session_governance_shape(
        self,
    ) -> None:
        class GuardedSessionGovernanceDict(dict):
            def get(self, *_args, **_kwargs):
                raise AssertionError(
                    "usage by-session route should construct outward model directly from normalized session governance dict"
                )

        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_normalizer = getattr(
            task_routes_module.chat_persistence_service,
            "_normalize_session_governance_summary_dict",
            None,
        )
        try:
            task_routes_module.get_tasks_usage_dashboard = lambda *_args, **_kwargs: {
                "window_days": 14,
                "summary": {
                    "tasks_total": 1,
                    "tasks_with_usage": 1,
                    "source_tasks_provider": 1,
                    "source_tasks_estimated": 0,
                    "source_tasks_mixed": 0,
                    "source_tasks_legacy": 0,
                    "prompt_tokens": 20,
                    "completion_tokens": 30,
                    "total_tokens": 50,
                    "cost_estimate": 0.15,
                    "avg_total_tokens": 50.0,
                    "avg_cost_estimate": 0.15,
                },
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-guarded-dict",
                        "session_title": "Usage Guarded Governance Session",
                        "tasks_with_usage": 1,
                        "total_tokens": 50,
                        "cost_estimate": 0.15,
                        "last_task_at": "2026-06-16T22:00:00",
                        "governance": GuardedSessionGovernanceDict(
                            profiles=["guarded_profile"],
                            provider_sources=["guarded_source"],
                            allowed_tool_names=["guarded_tool"],
                            allowed_tool_labels=["Guarded Tool"],
                        ),
                    }
                ],
                "top_tasks": [],
            }
            task_routes_module.chat_persistence_service._normalize_session_governance_summary_dict = (  # type: ignore[attr-defined]
                lambda _governance: (_ for _ in ()).throw(
                    AssertionError(
                        "usage by-session route should not re-normalize service governance dicts"
                    )
                )
            )
            payload = task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                current_user={"id": "user-usage-guarded-dict"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            if original_normalizer is None:
                delattr(
                    task_routes_module.chat_persistence_service,
                    "_normalize_session_governance_summary_dict",
                )
            else:
                task_routes_module.chat_persistence_service._normalize_session_governance_summary_dict = original_normalizer  # type: ignore[attr-defined]

        self.assertEqual(len(payload.by_session), 1)
        self.assertIsNotNone(payload.by_session[0].governance)
        assert payload.by_session[0].governance is not None
        self.assertEqual(payload.by_session[0].governance.profiles, ["guarded_profile"])
        self.assertEqual(
            payload.by_session[0].governance.provider_sources, ["guarded_source"]
        )
        self.assertEqual(
            payload.by_session[0].governance.allowed_tool_names, ["guarded_tool"]
        )
        self.assertEqual(
            payload.by_session[0].governance.allowed_tool_labels, ["Guarded Tool"]
        )

    def test_task_route_module_does_not_expose_dead_usage_session_governance_summary_builder(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(
                task_routes_module,
                "_build_task_usage_session_governance_summary_from_dict",
            )
        )

    def test_get_tasks_usage_dashboard_filters_by_profile_and_provider_source(self) -> None:
        rows = [
            {
                "id": "task-usage-filtered-1",
                "session_id": "session-usage-filtered-1",
                "prompt": "planning suite dashboard row",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-filtered-1",
                            "type": "thought",
                            "content": "planner constrained task",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "planning_only",
                                "tool_registry_provider_source": "planning_suite",
                                "allowed_tool_names": ["task_plan"],
                                "allowed_tool_labels": ["Task Planner Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T10:00:00",
                "updated_at": "2026-06-09T10:05:00",
                "session_title": "Planning Session",
            },
            {
                "id": "task-usage-filtered-2",
                "session_id": "session-usage-filtered-2",
                "prompt": "retrieval suite dashboard row",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 8,
                        "completion_tokens": 12,
                        "cost_estimate": 0.03,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": json.dumps(
                    [
                        {
                            "id": "trace-usage-filtered-2",
                            "type": "thought",
                            "content": "retrieval constrained task",
                            "seq": 1,
                            "meta": {
                                "tool_registry_profile": "retrieval_only",
                                "tool_registry_provider_source": "retrieval_suite",
                                "allowed_tool_names": ["task_retrieve"],
                                "allowed_tool_labels": ["Knowledge Retrieval Suite"],
                            },
                        }
                    ]
                ),
                "created_at": "2026-06-09T11:00:00",
                "updated_at": "2026-06-09T11:05:00",
                "session_title": "Retrieval Session",
            },
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered",
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(payload["by_session"][0]["session_id"], "session-usage-filtered-1")
        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertEqual(payload["top_tasks"][0]["task_id"], "task-usage-filtered-1")

    def test_get_tasks_usage_dashboard_filters_by_persisted_profile_and_provider_source(self) -> None:
        rows = [
            {
                "id": "task-usage-filtered-columns-1",
                "session_id": "session-usage-filtered-columns-1",
                "prompt": "planning suite dashboard row with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Planning Session",
            },
            {
                "id": "task-usage-filtered-columns-2",
                "session_id": "session-usage-filtered-columns-2",
                "prompt": "retrieval suite dashboard row with persisted columns",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 8,
                        "completion_tokens": 12,
                        "cost_estimate": 0.03,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "retrieval_only",
                "tool_registry_provider_source": "retrieval_suite",
                "allowed_tool_names_json": json.dumps(["task_retrieve"]),
                "allowed_tool_labels_json": json.dumps(["Knowledge Retrieval Suite"]),
                "created_at": "2026-06-10T11:00:00",
                "updated_at": "2026-06-10T11:05:00",
                "session_title": "Retrieval Session",
            },
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered-columns",
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection

        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(
            payload["by_session"][0]["session_id"],
            "session-usage-filtered-columns-1",
        )
        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertEqual(
            payload["top_tasks"][0]["task_id"],
            "task-usage-filtered-columns-1",
        )

    def test_get_tasks_usage_dashboard_reuses_shared_governance_filter_normalizer_for_task_match(
        self,
    ) -> None:
        rows = [
            {
                "id": "task-usage-filtered-normalizer-1",
                "session_id": "session-usage-filtered-normalizer-1",
                "prompt": "planning suite dashboard row with shared normalizer",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Planning Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter
        )
        captured: dict[str, object] = {"normalize_inputs": []}
        try:
            def fake_normalize_governance_filter(value):
                captured["normalize_inputs"].append(value)
                if value in {
                    " Planning_Only ",
                    "planning_only",
                    "profile::normalized",
                }:
                    return "profile::normalized"
                if value in {
                    " Planning_Suite ",
                    "planning_suite",
                    "provider::normalized",
                }:
                    return "provider::normalized"
                return None

            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._normalize_governance_filter = (
                fake_normalize_governance_filter
            )
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered-normalizer",
                tool_registry_profile_filter=" Planning_Only ",
                tool_registry_provider_source_filter=" Planning_Suite ",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module._normalize_governance_filter = (
                original_normalize_governance_filter
            )

        normalize_inputs = list(captured["normalize_inputs"])
        self.assertEqual(
            normalize_inputs[:4],
            [
                " Planning_Only ",
                " Planning_Suite ",
                "planning_only",
                "planning_suite",
            ],
        )
        self.assertGreaterEqual(normalize_inputs.count("profile::normalized"), 1)
        self.assertGreaterEqual(normalize_inputs.count("provider::normalized"), 1)
        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(len(payload["top_tasks"]), 1)

    def test_get_tasks_usage_dashboard_resolves_unique_redacted_provider_source_alias_filter(
        self,
    ) -> None:
        rows = [
            {
                "id": "task-usage-filtered-alias-1",
                "session_id": "session-usage-filtered-alias-1",
                "prompt": "alias-filtered dashboard row",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "suite_api_key=hidden",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Alias Filter Session",
            }
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_get_settings = chat_persistence_module.get_settings
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.get_settings = lambda: SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_api_key=hidden": {
                            "provider": "default",
                            "profile": "planning_only",
                        }
                    }
                )
            )
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered-alias",
                tool_registry_provider_source_filter="suite_[redacted]",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module.get_settings = original_get_settings

        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(
            payload["by_session"][0]["session_id"],
            "session-usage-filtered-alias-1",
        )
        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertEqual(
            payload["top_tasks"][0]["task_id"],
            "task-usage-filtered-alias-1",
        )

    def test_get_tasks_usage_dashboard_reuses_shared_task_governance_filter_matcher(
        self,
    ) -> None:
        rows = [
            {
                "id": "task-usage-filtered-matcher-1",
                "session_id": "session-usage-filtered-matcher-1",
                "prompt": "planning suite dashboard row with matcher",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 10,
                        "completion_tokens": 15,
                        "cost_estimate": 0.05,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "planning_only",
                "tool_registry_provider_source": "planning_suite",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-15T20:00:00",
                "updated_at": "2026-06-15T20:05:00",
                "session_title": "Planning Session",
            },
            {
                "id": "task-usage-filtered-matcher-2",
                "session_id": "session-usage-filtered-matcher-2",
                "prompt": "retrieval suite dashboard row with matcher",
                "usage_json": json.dumps(
                    {
                        "prompt_tokens": 8,
                        "completion_tokens": 12,
                        "cost_estimate": 0.03,
                        "usage_source": "provider",
                    }
                ),
                "trace_json": None,
                "tool_registry_profile": "retrieval_only",
                "tool_registry_provider_source": "retrieval_suite",
                "allowed_tool_names_json": json.dumps(["task_retrieve"]),
                "allowed_tool_labels_json": json.dumps(["Knowledge Retrieval Suite"]),
                "created_at": "2026-06-15T21:00:00",
                "updated_at": "2026-06-15T21:05:00",
                "session_title": "Retrieval Session",
            },
        ]

        class FakeCursor:
            def __init__(self, payload: list[dict]):
                self._payload = payload

            def fetchall(self) -> list[dict]:
                return self._payload

        class FakeConnection:
            def execute(self, _query: str, _params=()):
                return FakeCursor(rows)

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        original_get_db_connection = chat_persistence_module.get_db_connection
        original_matcher = getattr(
            chat_persistence_module,
            "_task_governance_matches_filters",
            None,
        )
        captured: list[tuple[object, object, object]] = []
        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module._task_governance_matches_filters = (  # type: ignore[attr-defined]
                lambda governance, profile_filter, provider_source_filter: captured.append(
                    (governance, profile_filter, provider_source_filter)
                )
                or (
                    isinstance(governance, dict)
                    and governance.get("profile") == "planning_only"
                    and governance.get("provider_source") == "planning_suite"
                )
            )
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered-matcher",
                tool_registry_profile_filter="planning_only",
                tool_registry_provider_source_filter="planning_suite",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            if original_matcher is None:
                delattr(chat_persistence_module, "_task_governance_matches_filters")
            else:
                chat_persistence_module._task_governance_matches_filters = original_matcher  # type: ignore[attr-defined]

        self.assertEqual(
            captured,
            [
                (
                    {
                        "profile": "planning_only",
                        "provider_source": "planning_suite",
                        "allowed_tool_names": ["task_plan"],
                        "allowed_tool_labels": ["Task Planner Suite"],
                    },
                    "planning_only",
                    "planning_suite",
                ),
                (
                    {
                        "profile": "retrieval_only",
                        "provider_source": "retrieval_suite",
                        "allowed_tool_names": ["task_retrieve"],
                        "allowed_tool_labels": ["Knowledge Retrieval Suite"],
                    },
                    "planning_only",
                    "planning_suite",
                ),
            ],
        )
        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(len(payload["top_tasks"]), 1)

    def test_get_tasks_usage_dashboard_route_trusts_service_governance_filter_normalizer(
        self,
    ) -> None:
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        original_normalize_governance_filter = (
            task_routes_module.chat_persistence_service._normalize_governance_filter  # type: ignore[attr-defined]
        )
        captured: dict[str, object] = {}
        try:
            def fake_get_tasks_usage_dashboard(user_id, **kwargs):
                captured["user_id"] = user_id
                captured.update(kwargs)
                return {
                    "window_days": 14,
                    "summary": {
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
                    "trend": [],
                    "by_session": [],
                    "top_tasks": [],
                }

            task_routes_module.get_tasks_usage_dashboard = fake_get_tasks_usage_dashboard
            task_routes_module.chat_persistence_service._normalize_governance_filter = (  # type: ignore[attr-defined]
                lambda _value: (_ for _ in ()).throw(
                    AssertionError(
                        "usage dashboard route should trust service-layer governance filter normalization"
                    )
                )
            )

            task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                tool_registry_profile=" Planning_Only ",
                tool_registry_provider_source=" Planning_Suite ",
                current_user={"id": "user-usage-filtered"},
            )
        finally:
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard
            task_routes_module.chat_persistence_service._normalize_governance_filter = (  # type: ignore[attr-defined]
                original_normalize_governance_filter
            )

        self.assertEqual(captured["user_id"], "user-usage-filtered")
        self.assertEqual(
            captured["tool_registry_profile_filter"],
            " Planning_Only ",
        )
        self.assertEqual(
            captured["tool_registry_provider_source_filter"],
            " Planning_Suite ",
        )

    def test_get_tasks_usage_dashboard_route_resolves_unique_redacted_provider_source_alias_filter(
        self,
    ) -> None:
        original_get_settings = task_routes_module.get_settings
        original_get_tasks_usage_dashboard = task_routes_module.get_tasks_usage_dashboard
        captured: dict[str, object] = {}
        try:
            task_routes_module.get_settings = lambda: SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_api_key=hidden": {
                            "provider": "default",
                            "profile": "planning_only",
                        }
                    }
                )
            )

            def fake_get_tasks_usage_dashboard(user_id, **kwargs):
                captured["user_id"] = user_id
                captured.update(kwargs)
                return {
                    "window_days": 14,
                    "summary": {
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
                    "trend": [],
                    "by_session": [],
                    "top_tasks": [],
                }

            task_routes_module.get_tasks_usage_dashboard = fake_get_tasks_usage_dashboard

            task_routes_module.get_tasks_usage_dashboard_route(
                session_id=None,
                window_days=14,
                top_sessions=10,
                top_tasks=14,
                source_kind="all",
                tool_registry_profile=None,
                tool_registry_provider_source="suite_[redacted]",
                current_user={"id": "user-usage-alias-filter"},
            )
        finally:
            task_routes_module.get_settings = original_get_settings
            task_routes_module.get_tasks_usage_dashboard = original_get_tasks_usage_dashboard

        self.assertEqual(captured["user_id"], "user-usage-alias-filter")
        self.assertEqual(
            captured["tool_registry_provider_source_filter"],
            "suite_api_key=hidden",
        )
