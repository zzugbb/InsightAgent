from __future__ import annotations

from .context import *


class TaskSessionExportPayloadMixinPart1:
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
