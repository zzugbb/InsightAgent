from __future__ import annotations

from .context import *


class TaskSessionExportPayloadMixinPart2:
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
