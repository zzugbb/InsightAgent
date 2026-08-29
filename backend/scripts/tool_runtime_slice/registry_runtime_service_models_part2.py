from __future__ import annotations

from .context import *


class RegistryRuntimeServiceModelsMixinPart2:
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
        captured_aliases: list[dict[str, str] | None] = []

        def record_helper(
            *,
            service_actions: list[dict[str, object]],
            **kwargs: object,
        ) -> object:
            captured.append(len(service_actions))
            provider_source_aliases = kwargs.get("provider_source_aliases")
            captured_aliases.append(
                provider_source_aliases
                if isinstance(provider_source_aliases, dict)
                else None
            )
            return original_helper(service_actions=service_actions, **kwargs)

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
        self.assertEqual(captured_aliases, [{"file_source": "file_source"}])
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
        captured_aliases: list[dict[str, str] | None] = []

        def record_helper(
            service_action: dict[str, object],
            **kwargs: object,
        ) -> object:
            captured.append(len(service_action))
            provider_source_aliases = kwargs.get("provider_source_aliases")
            captured_aliases.append(
                provider_source_aliases
                if isinstance(provider_source_aliases, dict)
                else None
            )
            return original_helper(service_action, **kwargs)

        tool_runtime_module.build_configured_tool_registry_provider_runtime_service_action_model_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
                service_actions=[trace_action.to_dict(), audit_action.to_dict()]
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_runtime_service_action_model_from_dict = original_helper

        self.assertEqual(captured, [4, 2])
        self.assertEqual(captured_aliases, [{}, {}])
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
