from __future__ import annotations

from .context import *


class RegistryRuntimeServiceModelsMixin:
    def test_build_tool_registry_diagnostics_runtime_artifacts_model_keeps_fields(
        self,
    ) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="file_source",
            diagnostics=diagnostics,
        )

        self.assertEqual(result.summary.total, 2)
        self.assertEqual(result.trace_step["id"], "step-1")
        self.assertEqual(result.trace_event["step_id"], "step-1")
        self.assertEqual(result.audit_detail["provider_source"], "file_source")

    def test_tool_registry_diagnostics_runtime_artifacts_model_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-diagnostics-model-http-json-output"
        )
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-diagnostics-model-http-json-output",
            "step": raw_step,
        }
        model = tool_runtime_module.ToolRegistryDiagnosticsRuntimeArtifactsModel(
            summary=build_tool_registry_diagnostics_summary_model(diagnostics={}),
            trace_step=raw_step,
            trace_event=trace_event,
            audit_detail={"trace": trace_event},
        )

        result = model.to_dict()

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_tool_registry_diagnostics_runtime_artifacts_model_redacts_http_json_wrapper_step_and_trace_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-diagnostics-model-http-json-wrapper-output"
        )
        followup_step = self._make_sensitive_http_json_action_step(
            step_id="rag-diagnostics-model-http-json-wrapper-output",
            content="Retrieved snippets",
        )
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-diagnostics-model-http-json-wrapper-output",
            "step": raw_step,
        }
        followup_trace = {
            "task_id": "task-1",
            "step_id": "rag-diagnostics-model-http-json-wrapper-output",
            "step": followup_step,
        }
        model = tool_runtime_module.ToolRegistryDiagnosticsRuntimeArtifactsModel(
            summary=build_tool_registry_diagnostics_summary_model(diagnostics={}),
            trace_step=raw_step,
            trace_event=trace_event,
            audit_detail={
                "rag_followup": {
                    "step": followup_step,
                    "trace": followup_trace,
                },
            },
        )

        result = model.to_dict()

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_registry_diagnostics_runtime_artifacts_keeps_empty_shape(self) -> None:
        diagnostics = {
            "skipped_registry_sources": (),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": (),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="default",
            diagnostics=diagnostics,
        )

        self.assertEqual(
            result["summary"],
            {
                "has_diagnostics": False,
                "skipped_total": 0,
                "missing_total": 0,
                "total": 0,
                "entries": (),
            },
        )
        self.assertIsNone(result["trace_step"])
        self.assertIsNone(result["trace_event"])
        self.assertIsNone(result["audit_detail"])

    def test_build_tool_registry_diagnostics_audit_event_keeps_shape(self) -> None:
        diagnostics_runtime = {
            "summary": {
                "has_diagnostics": True,
                "skipped_total": 1,
                "missing_total": 1,
                "total": 2,
                "entries": (
                    {
                        "kind": "skipped",
                        "target": "registry_sources",
                        "count": 1,
                        "values": ("planning_suite",),
                    },
                    {
                        "kind": "missing",
                        "target": "registry_files",
                        "count": 1,
                        "values": ("/tmp/missing.json",),
                    },
                ),
            },
            "trace_step": None,
            "trace_event": None,
            "audit_detail": {
                "provider_source": "file_source",
                "has_diagnostics": True,
                "skipped_total": 1,
                "missing_total": 1,
                "total": 2,
                "entries": (
                    {
                        "kind": "skipped",
                        "target": "registry_sources",
                        "count": 1,
                        "values": ("planning_suite",),
                    },
                    {
                        "kind": "missing",
                        "target": "registry_files",
                        "count": 1,
                        "values": ("/tmp/missing.json",),
                    },
                ),
            },
        }

        result = build_tool_registry_diagnostics_audit_event(
            diagnostics_runtime=diagnostics_runtime
        )

        self.assertEqual(
            result,
            {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": diagnostics_runtime["audit_detail"],
            },
        )

    def test_build_tool_registry_diagnostics_audit_event_returns_none_without_audit_detail(
        self,
    ) -> None:
        result = build_tool_registry_diagnostics_audit_event(
            diagnostics_runtime={
                "summary": {
                    "has_diagnostics": False,
                    "skipped_total": 0,
                    "missing_total": 0,
                    "total": 0,
                    "entries": (),
                },
                "trace_step": None,
                "trace_event": None,
                "audit_detail": None,
            }
        )

        self.assertIsNone(result)

    def test_build_tool_registry_diagnostics_audit_service_action_keeps_shape(self) -> None:
        audit_event = {
            "event_type": "tool_registry_diagnostics",
            "code": "tool_registry_diagnostics",
            "message": "Tool registry diagnostics detected during configured provider resolution.",
            "detail": {
                "provider_source": "file_source",
                "missing_total": 1,
            },
        }

        result = build_tool_registry_diagnostics_audit_service_action(
            audit_event=audit_event
        )

        self.assertEqual(
            result,
            {
                "kind": "record_audit_event",
                "kwargs": audit_event,
            },
        )

    def test_build_tool_registry_diagnostics_trace_service_action_keeps_shape(
        self,
    ) -> None:
        trace_step = {
            "id": "step-registry",
            "seq": 2,
            "type": "thought",
            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
        }
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-registry",
            "step": trace_step,
        }

        result = build_tool_registry_diagnostics_trace_service_action(
            trace_step=trace_step,
            trace_event=trace_event,
        )

        self.assertEqual(
            result,
            {
                "kind": "internal_trace_write",
                "trace_step": trace_step,
                "trace_event": trace_event,
                "persist_force": True,
            },
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_keeps_shape(
        self,
    ) -> None:
        runtime_artifacts = {
            "diagnostics_runtime": {
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
            },
            "audit_event": {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": {
                    "provider_source": "file_source",
                    "missing_total": 1,
                },
            }
        }

        result = build_configured_tool_registry_provider_runtime_service_actions(
            runtime_artifacts=runtime_artifacts
        )

        self.assertEqual(
            result,
            [
                {
                    "kind": "internal_trace_write",
                    "trace_step": runtime_artifacts["diagnostics_runtime"]["trace_step"],
                    "trace_event": runtime_artifacts["diagnostics_runtime"]["trace_event"],
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": runtime_artifacts["audit_event"],
                },
            ],
        )

    def test_build_task_export_payload_reuses_shared_task_export_response_summary_helper(
        self,
    ) -> None:
        task = {
            "id": "task-export-payload-helper",
            "session_id": "session-export-payload-helper",
            "prompt": "poisoned prompt",
            "status": "poisoned_status",
            "created_at": "poisoned_created_at",
            "updated_at": "poisoned_updated_at",
            "trace_json": "poisoned_trace_json",
            "usage_json": "poisoned_usage_json",
        }
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
        captured: list[object] = []
        try:
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: [
                {
                    "id": "message-1",
                    "session_id": "poisoned-session",
                    "task_id": "task-export-payload-helper",
                    "role": "assistant",
                    "content": "message body",
                    "created_at": "2026-06-22T15:31:00",
                }
            ]
            task_routes_module.chat_persistence_service.get_task_export_payload_summary = (  # type: ignore[attr-defined]
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError(
                        "task export route should reuse get_task_export_response_summary(task, message_rows) instead of calling get_task_export_payload_summary(task, message_rows) directly"
                    )
                )
            )
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda raw_task, message_rows: captured.append((raw_task, message_rows))
                or {
                    "task": {
                        "id": "task-export-payload-helper",
                        "session_id": "session-export-payload-helper",
                        "prompt": "shared prompt",
                        "status": "completed",
                        "status_normalized": "normalized::completed",
                        "status_label": "label::completed",
                        "status_rank": 12,
                        "created_at": "2026-06-22T15:30:00",
                        "updated_at": "2026-06-22T15:35:00",
                    },
                    "usage": {"prompt_tokens": 5},
                    "trace": {
                        "governance": {
                            "profile": "planning_only",
                            "provider_source": "suite_a",
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner"],
                        },
                        "steps": [],
                        "step_count": 2,
                        "rag_hit_count": 1,
                        "rag_knowledge_base_ids": ["kb-1"],
                        "rag_chunks": [
                            {
                                "step_id": "step-1",
                                "knowledge_base_id": "kb-1",
                                "content": "chunk body",
                            }
                        ],
                    },
                    "messages": [
                        {
                            "id": "message-1",
                            "role": "assistant",
                            "content": "message body",
                            "created_at": "2026-06-22T15:31:00",
                        }
                    ],
                }
            )
            payload = task_routes_module._build_task_export_payload(  # type: ignore[attr-defined]
                task,
                "user-export-payload-helper",
            )
        finally:
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
            if original_payload_helper is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_export_payload_summary",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_export_payload_summary",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_export_payload_summary = original_payload_helper  # type: ignore[attr-defined]

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], task)
        self.assertEqual(
            captured[0][1],
            [
                {
                    "id": "message-1",
                    "session_id": "poisoned-session",
                    "task_id": "task-export-payload-helper",
                    "role": "assistant",
                    "content": "message body",
                    "created_at": "2026-06-22T15:31:00",
                }
            ],
        )
        self.assertEqual(payload.task.prompt, "shared prompt")
        self.assertEqual(payload.trace.step_count, 2)
        self.assertEqual(payload.trace.rag_hit_count, 1)
        self.assertEqual(payload.messages[0].id, "message-1")

    def test_build_task_export_payload_redacts_http_json_message_content(
        self,
    ) -> None:
        task = {
            "id": "task-export-route-http-json-message",
            "session_id": "session-export-route-http-json-message",
            "prompt": "task export http json message",
            "status": "completed",
            "created_at": "2026-07-20T11:00:00",
            "updated_at": "2026-07-20T11:01:00",
            "trace_json": None,
            "usage_json": None,
        }
        original_get_task_messages = task_routes_module.get_task_messages
        original_response_helper = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_export_response_summary",
            None,
        )
        try:
            task_routes_module.get_task_messages = lambda *_args, **_kwargs: []
            task_routes_module.chat_persistence_service.get_task_export_response_summary = (  # type: ignore[attr-defined]
                lambda _task, _messages: {
                    "task": {
                        "id": "task-export-route-http-json-message",
                        "session_id": "session-export-route-http-json-message",
                        "prompt": "task export http json message",
                        "status": "completed",
                        "status_normalized": "completed",
                        "status_label": "Completed",
                        "status_rank": 3,
                        "created_at": "2026-07-20T11:00:00",
                        "updated_at": "2026-07-20T11:01:00",
                    },
                    "usage": None,
                    "messages": [
                        {
                            "id": "message-task-export-http-json",
                            "role": "assistant",
                            "content": (
                                "Provider Status [provider_status via http_json] "
                                "callback https://provider.example/cb?"
                                "access_token=secret-token#client_secret=hidden "
                                "Bearer secret-token"
                            ),
                            "created_at": "2026-07-20T11:01:00",
                        }
                    ],
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
                "user-task-export-route-http-json-message",
            )
            markdown = task_routes_module._build_task_export_markdown(payload)  # type: ignore[attr-defined]
        finally:
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

        combined = f"{payload.model_dump_json()}\n{markdown}"
        self.assertIn("[redacted]", combined)
        self.assertIn("callback", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("client_secret", combined)
        self.assertNotIn("secret-token", combined)
        self.assertNotIn("Bearer", combined)

    def test_build_configured_tool_registry_provider_runtime_service_actions_uses_model_helper(
        self,
    ) -> None:
        runtime_artifacts = {
            "diagnostics_runtime": {
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
            },
            "audit_event": {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": {
                    "provider_source": "file_source",
                    "missing_total": 1,
                },
            },
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model
        )
        captured: list[tuple[bool, bool]] = []

        def record_helper(
            *,
            runtime_artifacts: dict[str, object],
        ) -> object:
            captured.append(
                (
                    isinstance(runtime_artifacts.get("diagnostics_runtime"), dict),
                    isinstance(runtime_artifacts.get("audit_event"), dict),
                )
            )
            return original_helper(runtime_artifacts=runtime_artifacts)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions(
                runtime_artifacts=runtime_artifacts
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = original_helper

        self.assertEqual(captured, [(True, True)])
        self.assertEqual(
            tuple(item["kind"] for item in result),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts_redacts_raw_diagnostics(
        self,
    ) -> None:
        result = build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
            service_actions=[
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "content": (
                            "provider_search: unsupported tool execution kind api_key=hidden"
                        ),
                    },
                    "trace_event": {
                        "step": {
                            "content": (
                                "provider_search: http_json execution query_params.access_token must be safe"
                            ),
                        },
                    },
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": {
                        "event_type": "tool_registry_diagnostics",
                        "detail": {
                            "entries": (
                                {
                                    "kind": "invalid",
                                    "target": "tool_executions",
                                    "count": 1,
                                    "values": (
                                        "provider_search: http_json execution headers.x-api-key must be safe",
                                    ),
                                },
                            ),
                        },
                    },
                },
            ],
        )

        serialized = json.dumps(result.to_dict(), default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_runtime_service_action_model_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-service-action-model-http-json-output"
        )
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-service-action-model-http-json-output",
            "step": raw_step,
        }
        model = tool_runtime_module.ConfiguredToolRegistryProviderRuntimeServiceActionModel(
            kind="internal_trace_write",
            trace_step=raw_step,
            trace_event=trace_event,
            persist_force=True,
            kwargs={"trace_step": raw_step, "trace_event": trace_event},
        )

        result = model.to_dict()

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_runtime_service_action_model_from_dict_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-service-action-from-dict-http-json-output"
        )
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-service-action-from-dict-http-json-output",
            "step": raw_step,
        }
        model = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": raw_step,
                "trace_event": trace_event,
                "persist_force": True,
                "kwargs": {"trace_step": raw_step, "trace_event": trace_event},
            }
        )

        result = model.to_dict()

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_runtime_service_action_model_from_dict_redacts_provider_source_fields(
        self,
    ) -> None:
        model = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {
                    "id": "step-registry",
                    "meta": {
                        "tool_registry": {
                            "provider_source": "suite_api_key=hidden",
                        },
                    },
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step": {
                        "meta": {
                            "tool_registry": {
                                "provider_source": "suite_api_key=hidden",
                            },
                        },
                    },
                },
                "persist_force": True,
                "kwargs": {
                    "detail": {
                        "provider_source": "suite_api_key=hidden",
                    },
                },
            }
        )

        self.assertEqual(
            model.trace_step["meta"]["tool_registry"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            model.trace_event["step"]["meta"]["tool_registry"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            model.kwargs["detail"]["provider_source"],
            "suite_[redacted]",
        )
        serialized = json.dumps(model.to_dict(), default=str)
        self.assertNotIn("api_key=hidden", serialized)

    def test_execute_configured_tool_registry_provider_runtime_service_actions_records_audit(
        self,
    ) -> None:
        calls: list[dict[str, object]] = []
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        service_actions = [
            {
                "kind": "internal_trace_write",
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
                "persist_force": True,
            },
            {
                "kind": "record_audit_event",
                "kwargs": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "Tool registry diagnostics detected during configured provider resolution.",
                    "detail": {
                        "provider_source": "file_source",
                        "missing_total": 1,
                    },
                },
            }
        ]

        result = execute_configured_tool_registry_provider_runtime_service_actions(
            service_actions=service_actions,
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: calls.append(kwargs),
        )

        self.assertEqual(trace_steps, [service_actions[0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(calls, [service_actions[1]["kwargs"]])
        self.assertEqual(
            result,
            {
                "trace_write_count": 1,
                "audit_event_count": 1,
            },
        )

    def test_execute_configured_tool_registry_provider_runtime_service_actions_uses_result_model_helper(
        self,
    ) -> None:
        calls: list[dict[str, object]] = []
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        service_actions = [
            {
                "kind": "internal_trace_write",
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
                "persist_force": True,
            },
            {
                "kind": "record_audit_event",
                "kwargs": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "Tool registry diagnostics detected during configured provider resolution.",
                    "detail": {
                        "provider_source": "file_source",
                        "missing_total": 1,
                    },
                },
            },
        ]
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = record_helper
        try:
            result = execute_configured_tool_registry_provider_runtime_service_actions(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(trace_steps, [service_actions[0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(calls, [service_actions[1]["kwargs"]])
        self.assertEqual(
            result,
            {
                "trace_write_count": 1,
                "audit_event_count": 1,
            },
        )

    def test_execute_configured_tool_registry_provider_runtime_service_actions_outputs_uses_result_model_helper(
        self,
    ) -> None:
        calls: list[dict[str, object]] = []
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        service_actions = [
            {
                "kind": "internal_trace_write",
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                },
                "persist_force": True,
            },
            {
                "kind": "record_audit_event",
                "kwargs": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "Tool registry diagnostics detected during configured provider resolution.",
                    "detail": {
                        "provider_source": "file_source",
                        "missing_total": 1,
                    },
                },
            },
        ]
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = record_helper
        try:
            result_model, result_dict = execute_configured_tool_registry_provider_runtime_service_actions_outputs(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 1)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)
        self.assertEqual(trace_steps, [service_actions[0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(calls, [service_actions[1]["kwargs"]])

    def test_build_configured_tool_registry_provider_runtime_artifacts_exposes_selected_source_runtime_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            artifacts = build_configured_tool_registry_provider_runtime_artifacts(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(artifacts["provider_source_name"], "file_source")
        self.assertEqual(
            artifacts["diagnostics_runtime"]["summary"]["missing_total"],
            1,
        )
        self.assertEqual(
            artifacts["diagnostics_runtime"]["trace_event"],
            {
                "task_id": "task-1",
                "step_id": "step-registry",
                "step": artifacts["diagnostics_runtime"]["trace_step"],
            },
        )
        self.assertEqual(
            artifacts["audit_event"],
            {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "Tool registry diagnostics detected during configured provider resolution.",
                "detail": artifacts["diagnostics_runtime"]["audit_detail"],
            },
        )
        self.assertEqual(
            tuple(sorted(artifacts["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_keeps_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = build_configured_tool_registry_provider_runtime_artifacts_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(result.audit_event["event_type"], "tool_registry_diagnostics")
        self.assertEqual(tuple(sorted(result.provider.load_tool_registry())), ("calc_eval_fast",))

    def test_build_configured_tool_registry_provider_service_execution_keeps_shape(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = build_configured_tool_registry_provider_service_execution(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(
            tuple(sorted(result["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            [item["kind"] for item in result["service_actions"]],
            ["internal_trace_write", "record_audit_event"],
        )
        self.assertEqual(
            result["runtime_artifacts"]["diagnostics_runtime"]["summary"]["missing_total"],
            1,
        )

    def test_build_configured_tool_registry_provider_service_execution_model_keeps_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            result = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_execute_configured_tool_registry_provider_service_execution_applies_actions(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {"provider_source_name": "file_source"},
            "service_actions": [
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                        },
                    },
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": {
                        "event_type": "tool_registry_diagnostics",
                        "code": "tool_registry_diagnostics",
                        "message": "Tool registry diagnostics detected during configured provider resolution.",
                        "detail": {
                            "provider_source": "file_source",
                            "missing_total": 1,
                        },
                    },
                },
            ],
        }

        result = execute_configured_tool_registry_provider_service_execution(
            service_execution=service_execution,
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
        )

        self.assertEqual(trace_steps, [service_execution["service_actions"][0]["trace_step"]])
        self.assertEqual(persisted, [True])
        self.assertEqual(audit_calls, [service_execution["service_actions"][1]["kwargs"]])
        self.assertIs(result["provider"], provider)
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(result["trace_write_count"], 1)
        self.assertEqual(result["audit_event_count"], 1)

    def test_execute_configured_tool_registry_provider_service_execution_uses_outputs_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {"provider_source_name": "file_source"},
            "service_actions": [
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                        },
                    },
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": {
                        "event_type": "tool_registry_diagnostics",
                        "code": "tool_registry_diagnostics",
                        "message": "Tool registry diagnostics detected during configured provider resolution.",
                        "detail": {
                            "provider_source": "file_source",
                            "missing_total": 1,
                        },
                    },
                },
            ],
        }
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs
        )
        captured: list[tuple[str, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    len(service_execution["service_actions"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs = record_helper
        try:
            result = execute_configured_tool_registry_provider_service_execution(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs = original_helper

        self.assertEqual(captured, [("file_source", 2)])
        self.assertIs(result["provider"], provider)
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(result["trace_write_count"], 1)
        self.assertEqual(result["audit_event_count"], 1)

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict_uses_result_model_helper(
        self,
    ) -> None:
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict
        )
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            execution_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(execution_result=execution_result)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict(
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict = original_helper

        self.assertEqual(captured, [(1, 2)])
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 2)

    def test_build_configured_tool_registry_provider_service_execution_outputs_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: dict[str, object],
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
        try:
            result_model, result_dict = build_configured_tool_registry_provider_service_execution_outputs(
                service_execution=service_execution,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertIs(result_model.provider, provider)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 2)

    def test_execute_configured_tool_registry_provider_service_execution_outputs_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {"provider_source_name": "file_source"},
            "service_actions": [
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "Tool registry diagnostics: source=file_source skipped=1 missing=1",
                        },
                    },
                    "persist_force": True,
                },
                {
                    "kind": "record_audit_event",
                    "kwargs": {
                        "event_type": "tool_registry_diagnostics",
                        "code": "tool_registry_diagnostics",
                        "message": "Tool registry diagnostics detected during configured provider resolution.",
                        "detail": {
                            "provider_source": "file_source",
                            "missing_total": 1,
                        },
                    },
                },
            ],
        }
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
        )
        captured: list[tuple[str, int]] = []

        def record_helper(
            *,
            service_execution: object,
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    len(getattr(service_execution, "service_actions")),
                )
            )
            return original_helper(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
        try:
            result_model, result_dict = tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs(
                service_execution=service_execution,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 2)])
        self.assertIs(result_model.provider, provider)
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)

    def test_build_configured_tool_registry_provider_service_execution_result_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }
        execution_result = {
            "trace_write_count": 1,
            "audit_event_count": 2,
        }

        result = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution,
            execution_result=execution_result,
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertEqual(result.runtime_artifacts.provider_source_name, "default")

    def test_build_configured_tool_registry_provider_service_execution_result_model_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: dict[str, object],
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
        try:
            result = build_configured_tool_registry_provider_service_execution_result_model(
                service_execution=service_execution,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_service_execution_result_model_uses_default_counts(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "default",
            "runtime_artifacts": runtime_artifacts_model.to_dict(),
            "service_actions": [],
        }

        result = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution,
            execution_result={},
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.trace_write_count, 0)
        self.assertEqual(result.audit_event_count, 0)
        self.assertEqual(result.runtime_artifacts.provider_source_name, "default")

    def test_build_configured_tool_registry_provider_service_execution_result_model_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        runtime_actions_result_model = build_configured_tool_registry_provider_runtime_service_actions_result_model(
            trace_write_count=1,
            audit_event_count=2,
        )

        result = build_configured_tool_registry_provider_service_execution_result_model_from_models(
            service_execution=service_execution_model,
            execution_result=runtime_actions_result_model,
        )

        self.assertIs(result.provider, service_execution_model.provider)
        self.assertEqual(result.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(result.runtime_artifacts.provider_source_name, service_execution_model.runtime_artifacts.provider_source_name)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 1,
                            "skipped_total": 0,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [],
            }
        )

        result = (
            build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model(
                service_execution=service_execution_model,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertTrue(result.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model_uses_outputs_from_models_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 1,
                            "skipped_total": 0,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [],
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(getattr(execution_result, "trace_write_count")),
                    int(getattr(execution_result, "audit_event_count")),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model(
                    service_execution=service_execution_model,
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model_uses_outputs_from_models_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 1,
                            "skipped_total": 0,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [],
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(getattr(execution_result, "trace_write_count")),
                    int(getattr(execution_result, "audit_event_count")),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
                    service_execution=service_execution_model,
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_outputs_from_models = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result_model.provider, provider)
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 2)

    def test_build_tool_registry_diagnostics_trace_service_action_model_keeps_fields(
        self,
    ) -> None:
        trace_step = {
            "id": "step-registry",
            "seq": 2,
            "type": "thought",
            "content": "diagnostics",
        }
        trace_event = {
            "task_id": "task-1",
            "step_id": "step-registry",
            "step": trace_step,
        }

        result = build_tool_registry_diagnostics_trace_service_action_model(
            trace_step=trace_step,
            trace_event=trace_event,
            persist_force=True,
        )

        self.assertEqual(result.kind, "internal_trace_write")
        self.assertEqual(result.trace_step, trace_step)
        self.assertEqual(result.trace_event, trace_event)
        self.assertTrue(result.persist_force)
        self.assertIsNone(result.kwargs)

    def test_build_tool_registry_diagnostics_audit_service_action_model_keeps_fields(
        self,
    ) -> None:
        audit_event = {
            "event_type": "tool_registry_diagnostics",
            "code": "tool_registry_diagnostics",
            "message": "diagnostics detected",
            "detail": {"provider_source": "default"},
        }

        result = build_tool_registry_diagnostics_audit_service_action_model(
            audit_event=audit_event,
        )

        self.assertEqual(result.kind, "record_audit_event")
        self.assertIsNone(result.trace_step)
        self.assertIsNone(result.trace_event)
        self.assertFalse(result.persist_force)
        self.assertEqual(result.kwargs, audit_event)

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="file_source",
            runtime_artifacts={
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 1,
                        "missing_total": 2,
                        "total": 3,
                        "entries": ({"kind": "missing_file"},),
                    },
                    "trace_step": {"id": "step-registry"},
                    "trace_event": {"task_id": "task-1"},
                    "audit_detail": {"provider_source": "file_source"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.diagnostics_runtime.summary.total, 3)
        self.assertEqual(result.audit_event, {"event_type": "tool_registry_diagnostics"})

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict_redacts_raw_diagnostics(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        result = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts={
                "provider_source_name": "provider_suite",
                "selected_source_diagnostics": {
                    "invalid_tool_executions": (
                        "provider_search: unsupported tool execution kind api_key=hidden",
                        "provider_search: http_json execution query_params.access_token must be safe",
                    ),
                },
                "source_diagnostics": {
                    "provider_suite": {
                        "invalid_tool_executions": (
                            "provider_search: unsupported tool execution kind api_key=hidden",
                            "provider_search: http_json execution headers.x-api-key must be safe",
                        ),
                    },
                },
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 0,
                        "missing_total": 0,
                        "total": 2,
                        "entries": (),
                    },
                    "trace_step": None,
                    "trace_event": None,
                    "audit_detail": None,
                },
            },
        )

        self.assertEqual(
            result.selected_source_diagnostics["invalid_tool_executions"],
            (
                "provider_search: unsupported tool execution kind [redacted]",
                "provider_search: http_json execution [redacted] must be safe",
            ),
        )
        self.assertEqual(
            result.source_diagnostics["provider_suite"]["invalid_tool_executions"],
            (
                "provider_search: unsupported tool execution kind [redacted]",
                "provider_search: http_json execution [redacted] must be safe",
            ),
        )
        serialized = json.dumps(result.to_dict(), default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict_redacts_sensitive_provider_source_name(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        result = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="fallback_api_key=hidden",
            runtime_artifacts={
                "provider_source_name": "suite_api_key=hidden",
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 1,
                        "missing_total": 0,
                        "total": 1,
                        "entries": (),
                    },
                    "trace_step": {
                        "meta": {
                            "tool_registry": {
                                "provider_source": "suite_api_key=hidden",
                            },
                        },
                    },
                    "trace_event": None,
                    "audit_detail": {
                        "provider_source": "suite_api_key=hidden",
                    },
                },
                "audit_event": {
                    "event_type": "tool_registry_diagnostics",
                    "detail": {
                        "provider_source": "suite_api_key=hidden",
                    },
                },
            },
        )

        self.assertEqual(result.provider_source_name, "suite_[redacted]")
        self.assertEqual(
            result.diagnostics_runtime.trace_step["meta"]["tool_registry"][
                "provider_source"
            ],
            "suite_[redacted]",
        )
        self.assertEqual(
            result.diagnostics_runtime.audit_detail["provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            result.audit_event["detail"]["provider_source"],
            "suite_[redacted]",
        )
        serialized = json.dumps(result.to_dict(), default=str)
        self.assertNotIn("api_key=hidden", serialized)

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict_redacts_sensitive_source_diagnostics_keys(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        result = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts={
                "provider_source_name": "provider_suite",
                "source_diagnostics": {
                    "suite_api_key=hidden": {
                        "invalid_tool_executions": (
                            "provider_search: unsupported tool execution kind api_key=hidden",
                        ),
                    },
                },
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 0,
                        "missing_total": 0,
                        "total": 1,
                        "entries": (),
                    },
                    "trace_step": None,
                    "trace_event": None,
                    "audit_detail": None,
                },
            },
        )

        self.assertEqual(tuple(result.source_diagnostics), ("suite_[redacted]",))
        self.assertEqual(
            result.source_diagnostics["suite_[redacted]"]["invalid_tool_executions"],
            ("provider_search: unsupported tool execution kind [redacted]",),
        )
        serialized = json.dumps(result.to_dict(), default=str)
        self.assertNotIn("api_key=hidden", serialized)

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict_redacts_diagnostics_runtime_payload(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        result = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts={
                "provider_source_name": "provider_suite",
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 0,
                        "missing_total": 0,
                        "total": 2,
                        "entries": (
                            {
                                "kind": "invalid",
                                "target": "tool_executions",
                                "count": 2,
                                "values": (
                                    "provider_search: unsupported tool execution kind api_key=hidden",
                                    "provider_search: http_json execution query_params.access_token must be safe",
                                ),
                            },
                        ),
                    },
                    "trace_step": {
                        "id": "step-registry",
                        "content": (
                            "provider_search: unsupported tool execution kind api_key=hidden\n"
                            "provider_search: http_json execution headers.x-api-key must be safe"
                        ),
                    },
                    "trace_event": {
                        "step": {
                            "content": (
                                "provider_search: http_json execution query_params.access_token must be safe"
                            ),
                        },
                    },
                    "audit_detail": {
                        "entries": (
                            {
                                "kind": "invalid",
                                "target": "tool_executions",
                                "count": 1,
                                "values": (
                                    "provider_search: unsupported tool execution kind token=hidden",
                                ),
                            },
                        ),
                    },
                },
                "audit_event": {
                    "event_type": "tool_registry_diagnostics",
                    "detail": {
                        "entries": (
                            {
                                "kind": "invalid",
                                "target": "tool_executions",
                                "count": 1,
                                "values": (
                                    "provider_search: http_json execution json_body.client_secret must be safe",
                                ),
                            },
                        ),
                    },
                },
            },
        )

        summary_values = result.diagnostics_runtime.summary.entries[0]["values"]
        self.assertEqual(
            summary_values,
            (
                "provider_search: unsupported tool execution kind [redacted]",
                "provider_search: http_json execution [redacted] must be safe",
            ),
        )
        serialized = json.dumps(result.to_dict(), default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn("client_secret", serialized)

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict_derives_summary_totals_from_sanitized_entries(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        result = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts={
                "provider_source_name": "provider_suite",
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": False,
                        "skipped_total": 99,
                        "missing_total": 42,
                        "total": 141,
                        "entries": (
                            {
                                "kind": "skipped",
                                "target": "registry_sources",
                                "count": 99,
                                "values": (
                                    "provider_search: unsupported tool execution kind api_key=hidden",
                                ),
                            },
                            {
                                "kind": "missing",
                                "target": "registry_files",
                                "count": 42,
                                "values": (
                                    "/tmp/missing.json",
                                    "/tmp/missing.json",
                                ),
                            },
                        ),
                    },
                    "trace_step": None,
                    "trace_event": None,
                    "audit_detail": None,
                },
            },
        )

        summary = result.diagnostics_runtime.summary
        self.assertTrue(summary.has_diagnostics)
        self.assertEqual(summary.skipped_total, 1)
        self.assertEqual(summary.missing_total, 1)
        self.assertEqual(summary.total, 2)
        self.assertEqual(
            summary.entries,
            (
                {
                    "kind": "skipped",
                    "target": "registry_sources",
                    "count": 1,
                    "values": (
                        "provider_search: unsupported tool execution kind [redacted]",
                    ),
                },
                {
                    "kind": "missing",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/missing.json",),
                },
            ),
        )

    def test_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict_safely_coerces_invalid_summary_totals(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        result = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts={
                "provider_source_name": "provider_suite",
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": "not-a-number",
                        "missing_total": object(),
                        "total": "",
                        "entries": (),
                    },
                    "trace_step": None,
                    "trace_event": None,
                    "audit_detail": None,
                },
            },
        )

        summary = result.diagnostics_runtime.summary
        self.assertTrue(summary.has_diagnostics)
        self.assertEqual(summary.skipped_total, 0)
        self.assertEqual(summary.missing_total, 0)
        self.assertEqual(summary.total, 0)
        self.assertEqual(summary.entries, ())

    def test_build_configured_tool_registry_provider_service_execution_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "skipped_total": 0,
                            "missing_total": 1,
                            "total": 1,
                            "entries": (),
                        }
                    }
                },
                "service_actions": [
                    {
                        "kind": "internal_trace_write",
                        "trace_step": {"id": "step-registry"},
                        "trace_event": {"task_id": "task-1"},
                        "persist_force": True,
                    },
                    {
                        "kind": "record_audit_event",
                        "kwargs": {"event_type": "tool_registry_diagnostics"},
                    },
                ],
            }
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_service_execution_model_from_dict_redacts_sensitive_provider_source_name(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        result = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "suite_api_key=hidden",
                "runtime_artifacts": {
                    "provider_source_name": "suite_api_key=hidden",
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "skipped_total": 0,
                            "missing_total": 1,
                            "total": 1,
                            "entries": (),
                        },
                        "trace_step": None,
                        "trace_event": None,
                        "audit_detail": None,
                    },
                },
                "service_actions": [],
            }
        )

        self.assertEqual(result.provider_source_name, "suite_[redacted]")
        self.assertEqual(result.runtime_artifacts.provider_source_name, "suite_[redacted]")
        serialized = json.dumps(result.to_dict(), default=str)
        self.assertNotIn("api_key=hidden", serialized)

    def test_build_configured_tool_registry_provider_service_execution_model_from_dict_accepts_tuple_service_actions(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution={
                "provider": provider,
                "provider_source_name": "file_source",
                "runtime_artifacts": {},
                "service_actions": (
                    {
                        "kind": "internal_trace_write",
                        "trace_step": {"id": "step-registry"},
                        "trace_event": {"task_id": "task-1"},
                        "persist_force": True,
                    },
                    {
                        "kind": "record_audit_event",
                        "kwargs": {"event_type": "tool_registry_diagnostics"},
                    },
                ),
            }
        )

        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_service_execution_model_from_dict_uses_runtime_service_actions_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(service_actions=service_actions)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = record_helper
        try:
            result = build_configured_tool_registry_provider_service_execution_model_from_dict(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "skipped_total": 0,
                                "missing_total": 1,
                                "total": 1,
                                "entries": (),
                            }
                        }
                    },
                    "service_actions": [
                        {
                            "kind": "internal_trace_write",
                            "trace_step": {"id": "step-registry"},
                            "trace_event": {"task_id": "task-1"},
                            "persist_force": True,
                        },
                        {
                            "kind": "record_audit_event",
                            "kwargs": {"event_type": "tool_registry_diagnostics"},
                        },
                    ],
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_service_execution_model_uses_typed_runtime_service_actions_model_helper(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            original_helper = (
                tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model
            )
            captured: list[tuple[str, int]] = []

            def record_helper(
                *,
                runtime_artifacts: object,
            ) -> object:
                captured.append(
                    (
                        str(getattr(runtime_artifacts, "provider_source_name", None)),
                        int(
                            getattr(
                                getattr(runtime_artifacts, "diagnostics_runtime", None),
                                "summary",
                            ).missing_total
                        ),
                    )
                )
                return original_helper(runtime_artifacts=runtime_artifacts)

            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = record_helper
            try:
                result = build_configured_tool_registry_provider_service_execution_model(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                )
            finally:
                tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = original_helper

        self.assertEqual(captured, [("file_source", 1)])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(action.kind for action in result.service_actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_keeps_fields(
        self,
    ) -> None:
        result = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "diagnostics",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "diagnostics",
                        },
                    },
                },
                "audit_event": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "diagnostics detected",
                    "detail": {"provider_source": "file_source"},
                },
            },
        )

        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result.to_dict()),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_uses_typed_runtime_artifacts_helper(
        self,
    ) -> None:
        runtime_artifacts = {
            "diagnostics_runtime": {
                "trace_step": {
                    "id": "step-registry",
                    "seq": 2,
                    "type": "thought",
                    "content": "diagnostics",
                },
                "trace_event": {
                    "task_id": "task-1",
                    "step_id": "step-registry",
                    "step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "diagnostics",
                    },
                },
            },
            "audit_event": {
                "event_type": "tool_registry_diagnostics",
                "code": "tool_registry_diagnostics",
                "message": "diagnostics detected",
                "detail": {"provider_source": "file_source"},
            },
        }
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model
        )
        captured: list[tuple[str, bool]] = []

        def record_helper(
            *, runtime_artifacts: object
        ) -> object:
            captured.append(
                (
                    str(getattr(runtime_artifacts, "provider_source_name", None)),
                    hasattr(runtime_artifacts, "diagnostics_runtime"),
                )
            )
            return original_helper(runtime_artifacts=runtime_artifacts)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_model(
                runtime_artifacts=runtime_artifacts,
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model = original_helper

        self.assertEqual(captured, [("default", True)])
        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(
                service_actions=service_actions_model,
            )
        )

        self.assertIs(result_model, service_actions_model)
        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="file_source",
            runtime_artifacts={
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 0,
                        "missing_total": 1,
                        "total": 1,
                    },
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model(
                runtime_artifacts=runtime_artifacts_model,
            )
        )

        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_uses_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model
        )
        captured: list[tuple[str, bool]] = []

        def record_helper(
            *, runtime_artifacts: dict[str, object]
        ) -> object:
            captured.append(
                (
                    str(runtime_artifacts.get("provider_source_name", "")),
                    runtime_artifacts.get("provider") is provider,
                )
            )
            return original_helper(runtime_artifacts=runtime_artifacts)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_runtime_service_actions_outputs(
                    runtime_artifacts={
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "skipped_total": 0,
                                "missing_total": 1,
                                "total": 1,
                            },
                            "trace_step": {"id": "step-registry", "seq": 2},
                            "trace_event": {"task_id": "task-1"},
                        },
                        "audit_event": {"event_type": "tool_registry_diagnostics"},
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model = original_helper

        self.assertEqual(captured, [("file_source", True)])
        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model_uses_service_action_builders(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        runtime_artifacts_model = build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name="file_source",
            runtime_artifacts={
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                        "skipped_total": 0,
                        "missing_total": 1,
                        "total": 1,
                    },
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )
        original_trace_helper = (
            tool_runtime_module.build_tool_registry_diagnostics_trace_service_action_model
        )
        original_audit_helper = (
            tool_runtime_module.build_tool_registry_diagnostics_audit_service_action_model
        )
        captured: list[str] = []

        def record_helper(
            **kwargs: object,
        ) -> object:
            captured.append("trace")
            return original_trace_helper(**kwargs)

        def record_audit_helper(
            **kwargs: object,
        ) -> object:
            captured.append("audit")
            return original_audit_helper(**kwargs)

        tool_runtime_module.build_tool_registry_diagnostics_trace_service_action_model = record_helper
        tool_runtime_module.build_tool_registry_diagnostics_audit_service_action_model = record_audit_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model(
                runtime_artifacts=runtime_artifacts_model,
            )
        finally:
            tool_runtime_module.build_tool_registry_diagnostics_trace_service_action_model = original_trace_helper
            tool_runtime_module.build_tool_registry_diagnostics_audit_service_action_model = original_audit_helper

        self.assertEqual(captured, ["trace", "audit"])
        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_model_keeps_fields(
        self,
    ) -> None:
        result = build_configured_tool_registry_provider_runtime_service_actions_result_model(
            trace_write_count=1,
            audit_event_count=2,
        )

        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict_uses_result_model_builder(
        self,
    ) -> None:
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model
        )
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            trace_write_count: int,
            audit_event_count: int,
        ) -> object:
            captured.append(
                (
                    int(trace_write_count),
                    int(audit_event_count),
                )
            )
            return original_helper(
                trace_write_count=trace_write_count,
                audit_event_count=audit_event_count,
            )

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict(
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_result_model = original_helper

        self.assertEqual(captured, [(1, 2)])
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models(
                execution_result=build_configured_tool_registry_provider_runtime_service_actions_result_model(
                    trace_write_count=1,
                    audit_event_count=2,
                )
            )
        )

        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(
            result_dict,
            {
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict_keeps_fields(
        self,
    ) -> None:
        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict(
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        )

        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 2)
        self.assertEqual(
            result_dict,
            {
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

    def test_execute_configured_tool_registry_provider_runtime_service_actions_outputs_redacts_provider_source_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []

        result_model, result_dict = (
            execute_configured_tool_registry_provider_runtime_service_actions_outputs(
                service_actions=[
                    {
                        "kind": "internal_trace_write",
                        "trace_step": {
                            "id": "step-registry",
                            "meta": {
                                "tool_registry": {
                                    "provider_source": "suite_api_key=hidden",
                                },
                            },
                        },
                        "trace_event": {
                            "task_id": "task-1",
                            "step": {
                                "meta": {
                                    "tool_registry": {
                                        "provider_source": "suite_api_key=hidden",
                                    },
                                },
                            },
                        },
                        "persist_force": True,
                    },
                    {
                        "kind": "record_audit_event",
                        "kwargs": {
                            "event_type": "tool_registry_diagnostics",
                            "detail": {
                                "provider_source": "suite_api_key=hidden",
                            },
                        },
                    },
                ],
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(
                    bool(kwargs["force"])
                ),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        )

        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_dict["audit_event_count"], 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(
            trace_steps[0]["meta"]["tool_registry"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            audit_calls[0]["detail"]["provider_source"],
            "suite_[redacted]",
        )
        serialized = json.dumps(
            {"trace_steps": trace_steps, "audit_calls": audit_calls},
            default=str,
        )
        self.assertNotIn("api_key=hidden", serialized)

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts_keeps_fields(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )

        result = build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
            service_actions=[trace_action.to_dict(), audit_action.to_dict()]
        )

        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertTrue(result.actions[0].persist_force)
        self.assertEqual(
            result.actions[1].kwargs,
            {"event_type": "tool_registry_diagnostics"},
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts_redacts_provider_source_fields(
        self,
    ) -> None:
        result = build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
            service_actions=[
                {
                    "kind": "internal_trace_write",
                    "trace_step": {
                        "id": "step-registry",
                        "meta": {
                            "tool_registry": {
                                "provider_source": "suite_api_key=hidden",
                            },
                        },
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step": {
                            "meta": {
                                "tool_registry": {
                                    "provider_source": "suite_api_key=hidden",
                                },
                            },
                        },
                    },
                    "persist_force": True,
                    "kwargs": {
                        "detail": {
                            "provider_source": "suite_api_key=hidden",
                        },
                    },
                },
            ]
        )

        self.assertEqual(len(result.actions), 1)
        action = result.actions[0]
        self.assertEqual(
            action.trace_step["meta"]["tool_registry"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            action.trace_event["step"]["meta"]["tool_registry"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            action.kwargs["detail"]["provider_source"],
            "suite_[redacted]",
        )
        serialized = json.dumps(result.to_dict(), default=str)
        self.assertNotIn("api_key=hidden", serialized)

    def test_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts_uses_action_model_builder(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_action_model_from_dict
        )
        captured: list[int] = []

        def record_helper(
            service_action: dict[str, object],
        ) -> object:
            captured.append(len(service_action))
            return original_helper(service_action)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_action_model_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
                service_actions=[trace_action.to_dict(), audit_action.to_dict()]
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_action_model_from_dict = original_helper

        self.assertEqual(captured, [4, 2])
        self.assertEqual(
            tuple(action.kind for action in result.actions),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts_uses_model_helper(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts
        )
        captured: list[int] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
        ) -> object:
            captured.append(len(service_actions))
            return original_helper(service_actions=service_actions)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = record_helper
        try:
            result_model, result_dict = (
                build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts(
                    service_actions=[trace_action.to_dict(), audit_action.to_dict()]
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts = original_helper

        self.assertEqual(captured, [2])
        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts_keeps_fields(
        self,
    ) -> None:
        trace_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "internal_trace_write",
                "trace_step": {"id": "step-registry", "seq": 2},
                "trace_event": {"task_id": "task-1"},
                "persist_force": True,
            }
        )
        audit_action = build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
            {
                "kind": "record_audit_event",
                "kwargs": {"event_type": "tool_registry_diagnostics"},
            }
        )

        result_model, result_dict = (
            build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts(
                service_actions=[trace_action.to_dict(), audit_action.to_dict()]
            )
        )

        self.assertEqual(
            tuple(action.kind for action in result_model.actions),
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(
            tuple(item["kind"] for item in result_dict),
            ("internal_trace_write", "record_audit_event"),
        )

    def test_execute_configured_tool_registry_provider_runtime_service_actions_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {
                        "id": "step-registry",
                        "seq": 2,
                        "type": "thought",
                        "content": "diagnostics",
                    },
                    "trace_event": {
                        "task_id": "task-1",
                        "step_id": "step-registry",
                        "step": {
                            "id": "step-registry",
                            "seq": 2,
                            "type": "thought",
                            "content": "diagnostics",
                        },
                    },
                },
                "audit_event": {
                    "event_type": "tool_registry_diagnostics",
                    "code": "tool_registry_diagnostics",
                    "message": "diagnostics detected",
                    "detail": {"provider_source": "file_source"},
                },
            },
        )

        result = execute_configured_tool_registry_provider_runtime_service_actions_model(
            service_actions=service_actions_model,
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
        )

        self.assertEqual(trace_steps, [service_actions_model.actions[0].trace_step])
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)

    def test_execute_configured_tool_registry_provider_runtime_service_actions_model_redacts_raw_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-configured-provider-runtime-action-http-json-output"
        )
        service_actions_model = (
            tool_runtime_module.ConfiguredToolRegistryProviderRuntimeServiceActionsModel(
                actions=(
                    tool_runtime_module.ConfiguredToolRegistryProviderRuntimeServiceActionModel(
                        kind="internal_trace_write",
                        trace_step=raw_step,
                        persist_force=True,
                    ),
                )
            )
        )
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []

        result = execute_configured_tool_registry_provider_runtime_service_actions_model(
            service_actions=service_actions_model,
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: None,
        )

        serialized = json.dumps(trace_steps, ensure_ascii=False)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(persisted, [True])
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_execute_configured_tool_registry_provider_runtime_service_actions_model_uses_result_model_from_models_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )
        original_helper = (
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models
        )
        captured: list[tuple[str, ...]] = []

        def record_helper(
            *,
            service_actions: object,
            trace_steps: list[dict[str, object]],
            persist_trace_fn: object,
            record_audit_event_fn: object,
        ) -> object:
            captured.append(tuple(action.kind for action in getattr(service_actions, "actions")))
            return original_helper(
                service_actions=service_actions,
                trace_steps=trace_steps,
                persist_trace_fn=persist_trace_fn,
                record_audit_event_fn=record_audit_event_fn,
            )

        tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models = record_helper
        try:
            result = execute_configured_tool_registry_provider_runtime_service_actions_model(
                service_actions=service_actions_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        finally:
            tool_runtime_module.execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models = original_helper

        self.assertEqual(captured, [("internal_trace_write", "record_audit_event")])
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
            runtime_artifacts={
                "diagnostics_runtime": {
                    "trace_step": {"id": "step-registry", "seq": 2},
                    "trace_event": {"task_id": "task-1"},
                },
                "audit_event": {"event_type": "tool_registry_diagnostics"},
            },
        )

        result_model, result_dict = (
            execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(
                service_actions=service_actions_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )
        )

        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 1)
        self.assertEqual(
            result_dict,
            {
                "trace_write_count": 1,
                "audit_event_count": 1,
            },
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_model_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )
            original_helper = (
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
            )
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, dict[str, object]]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        tuple(action.kind for action in getattr(service_execution, "service_actions")),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("internal_trace_write", "record_audit_event"))])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )

            result_model, result_dict = (
                execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            )

        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result_model.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model_uses_outputs_from_models_helper(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )
            original_helper = (
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_models
            )
            captured: list[tuple[str, int, int]] = []

            def record_helper(
                *,
                service_execution: object,
                execution_result: object,
            ) -> tuple[object, dict[str, object]]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        int(getattr(execution_result, "trace_write_count")),
                        int(getattr(execution_result, "audit_event_count")),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    execution_result=execution_result,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_models = record_helper
            try:
                result_model, result_dict = (
                    execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
                        service_execution=service_execution_model,
                        trace_steps=trace_steps,
                        persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                        record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                    )
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_models = original_helper

        self.assertEqual(
            captured,
            [("file_source", 1, 1)],
        )
        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(result_dict["trace_write_count"], 1)
        self.assertEqual(result_dict["audit_event_count"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_service_execution_model_uses_outputs_from_service_execution_model_helper_for_trace_execution(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )
            service_execution_model = build_configured_tool_registry_provider_service_execution_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
            )
            original_helper = (
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
            )
            captured: list[tuple[int, int]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, dict[str, object]]:
                captured.append(
                    (
                        len(getattr(service_execution, "service_actions", ())),
                        len(trace_steps),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = record_helper
            try:
                result_model = execute_configured_tool_registry_provider_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [(2, 0)])
        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(result_model.trace_write_count, 1)
        self.assertEqual(result_model.audit_event_count, 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
