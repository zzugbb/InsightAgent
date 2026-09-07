from __future__ import annotations

from .context import *


class TaskUsageDashboardMixinPart2:
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
