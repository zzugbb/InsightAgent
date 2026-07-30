from __future__ import annotations

from .context import *


class RegistryRuntimeModelsMixin:
    def test_execute_configured_tool_registry_provider_preflight_keeps_shape(
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

            result = execute_configured_tool_registry_provider_preflight(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(
            tuple(sorted(result["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            result["service_execution"]["runtime_artifacts"]["diagnostics_runtime"]["summary"]["missing_total"],
            1,
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
        self.assertEqual(result["trace_write_count"], 1)
        self.assertEqual(result["audit_event_count"], 1)
        self.assertEqual(
            result["summary"],
            {
                "provider_source_name": "file_source",
                "tool_count": 1,
                "tool_names": ("calc_eval_fast",),
                "tool_details": (
                    {
                        "name": "calc_eval_fast",
                        "label": "Fast Calculator",
                        "kind": "local_calculator",
                        "semantic_kind": "local_calculator",
                        "retryable_by_default": True,
                        "default_timeout_ms": 3_000,
                        "requires_user_context": True,
                        "supports_result_preview": True,
                        "effective_result_preview_keys": ("expression", "result"),
                    },
                ),
                "service_action_count": 2,
                "service_action_kinds": ("internal_trace_write", "record_audit_event"),
                "trace_write_count": 1,
                "audit_event_count": 1,
                "has_diagnostics": True,
                "diagnostics_total": 1,
                "skipped_total": 0,
                "missing_total": 1,
                "diagnostics_summary": {
                    "has_diagnostics": True,
                    "skipped_total": 0,
                    "missing_total": 1,
                    "total": 1,
                    "entries": (
                        {
                            "kind": "missing",
                            "target": "registry_files",
                            "count": 1,
                            "values": (
                                str(missing_file.resolve()),
                            ),
                        },
                    ),
                },
            },
        )

    def test_execute_configured_tool_registry_provider_service_execution_model_keeps_fields(
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

            result = execute_configured_tool_registry_provider_service_execution_model(
                service_execution=service_execution_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(trace_steps, [service_execution_model.service_actions[0].trace_step])
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 1)

    def test_build_configured_tool_registry_provider_preflight_result_keeps_shape(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                    }
                }
            },
            "service_actions": [],
        }
        execution_result = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": service_execution["runtime_artifacts"],
            "trace_write_count": 1,
            "audit_event_count": 2,
        }

        result = build_configured_tool_registry_provider_preflight_result(
            service_execution=service_execution,
            execution_result=execution_result,
        )

        self.assertIs(result["provider"], provider)
        self.assertEqual(result["service_execution"]["provider_source_name"], "file_source")
        self.assertEqual(result["service_execution"]["service_actions"], [])
        self.assertEqual(
            result["summary"],
            {
                "provider_source_name": "file_source",
                "tool_count": 1,
                "tool_names": ("calc_eval",),
                "tool_details": (
                    {
                        "name": "calc_eval",
                        "label": "Calculator",
                        "kind": "local_calculator",
                        "semantic_kind": "local_calculator",
                        "retryable_by_default": True,
                        "default_timeout_ms": 3_000,
                        "requires_user_context": True,
                        "supports_result_preview": True,
                        "effective_result_preview_keys": ("expression", "result"),
                    },
                ),
                "service_action_count": 0,
                "service_action_kinds": (),
                "trace_write_count": 1,
                "audit_event_count": 2,
                "has_diagnostics": True,
                "diagnostics_total": 0,
                "skipped_total": 0,
                "missing_total": 0,
                "diagnostics_summary": {
                    "has_diagnostics": True,
                    "skipped_total": 0,
                    "missing_total": 0,
                    "total": 0,
                    "entries": (),
                },
            },
        )

    def test_build_configured_tool_registry_provider_preflight_result_uses_result_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": True,
                    }
                }
            },
            "service_actions": [],
        }
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            execution_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result(
                service_execution=service_execution,
                execution_result={
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": service_execution["runtime_artifacts"],
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result["provider"], provider)
        self.assertEqual(result["summary"]["tool_names"], ("calc_eval",))

    def test_build_configured_tool_registry_provider_preflight_summary_keeps_shape(
        self,
    ) -> None:
        preflight_result = {
            "provider_source_name": "default",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": False,
                    }
                }
            },
            "trace_write_count": 0,
            "audit_event_count": 1,
        }

        result = build_configured_tool_registry_provider_preflight_summary(
            preflight_result=preflight_result
        )

        self.assertEqual(
            result,
            {
                "provider_source_name": "default",
                "tool_count": 0,
                "tool_names": (),
                "tool_details": (),
                "service_action_count": 0,
                "service_action_kinds": (),
                "trace_write_count": 0,
                "audit_event_count": 1,
                "has_diagnostics": False,
                "diagnostics_total": 0,
                "skipped_total": 0,
                "missing_total": 0,
                "diagnostics_summary": {
                    "has_diagnostics": False,
                    "skipped_total": 0,
                    "missing_total": 0,
                    "total": 0,
                    "entries": (),
                },
            },
        )

    def test_build_configured_tool_registry_provider_preflight_summary_uses_summary_model_helper(
        self,
    ) -> None:
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary(
                preflight_result={
                    "provider_source_name": "default",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "trace_write_count": 0,
                    "audit_event_count": 1,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model = original_helper

        self.assertEqual(captured, [(0, 1)])
        self.assertEqual(result["provider_source_name"], "default")
        self.assertEqual(result["audit_event_count"], 1)

    def test_build_configured_tool_registry_provider_preflight_summary_model_includes_productized_tool_details_for_real_provider_kinds(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_math": ToolRegistration(
                    name="provider_math",
                    kind="provider_calc",
                    label="Provider Math",
                    retryable_by_default=True,
                    default_timeout_ms=13_000,
                    requires_user_context=True,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "expression": str(tool_input.get("expression", "")),
                        "result": 7.0,
                    },
                ),
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="Provider Search",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "hit_count": 1,
                        "knowledge_base_id": "demo-kb",
                        "chunks": ["alpha"],
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=SimpleNamespace(
                    tool_registry_provider_source="provider_suite",
                    tool_registry_provider_sources_json=json.dumps({}),
                )
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        self.assertEqual(
            result.tool_details,
            (
                {
                    "name": "provider_math",
                    "label": "Provider Math",
                    "kind": "provider_calc",
                    "semantic_kind": "local_calculator",
                    "retryable_by_default": True,
                    "default_timeout_ms": 13_000,
                    "requires_user_context": True,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ("expression", "result"),
                    "effective_result_output_keys": ("expression", "result"),
                },
                {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "knowledge_retrieval",
                    "retryable_by_default": False,
                    "default_timeout_ms": 15_000,
                    "requires_user_context": False,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": (
                        "hit_count",
                        "knowledge_base_id",
                    ),
                    "effective_result_output_keys": (
                        "hit_count",
                        "knowledge_base_id",
                    ),
                },
            ),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_includes_diagnostics_summary_entries(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="file_source",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
                provider=provider,
                provider_source_name="file_source",
                runtime_artifacts={
                    "provider_source_name": "file_source",
                    "diagnostics_runtime": {
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
                        "audit_detail": None,
                    },
                },
            ),
            service_actions=(),
            trace_write_count=1,
            audit_event_count=2,
        )

        self.assertEqual(
            result.diagnostics_summary,
            {
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
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_includes_per_tool_invalid_execution_diagnostics(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_math": ToolRegistration(
                    name="provider_math",
                    kind="provider_calc",
                    label="Provider Math",
                    retryable_by_default=True,
                    default_timeout_ms=13_000,
                    requires_user_context=True,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "expression": str(tool_input.get("expression", "")),
                        "result": 7.0,
                    },
                ),
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="Provider Search",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "hit_count": 1,
                        "knowledge_base_id": "demo-kb",
                        "chunks": ["alpha"],
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
                provider=provider,
                provider_source_name="provider_suite",
                runtime_artifacts={
                    "provider_source_name": "provider_suite",
                    "selected_source_diagnostics": {
                        "invalid_tool_executions": (
                            "provider_search: http_json execution response_path must not be blank",
                        ),
                    },
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "skipped_total": 0,
                            "missing_total": 0,
                            "total": 1,
                            "entries": (
                                {
                                    "kind": "invalid",
                                    "target": "tool_executions",
                                    "count": 1,
                                    "values": (
                                        "provider_search: http_json execution response_path must not be blank",
                                    ),
                                },
                            ),
                        },
                        "trace_step": None,
                        "trace_event": None,
                        "audit_detail": None,
                    },
                },
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        self.assertEqual(
            result.tool_details,
            (
                {
                    "name": "provider_math",
                    "label": "Provider Math",
                    "kind": "provider_calc",
                    "semantic_kind": "local_calculator",
                    "retryable_by_default": True,
                    "default_timeout_ms": 13_000,
                    "requires_user_context": True,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ("expression", "result"),
                    "effective_result_output_keys": ("expression", "result"),
                },
                {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "knowledge_retrieval",
                    "retryable_by_default": False,
                    "default_timeout_ms": 15_000,
                    "requires_user_context": False,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": (
                        "hit_count",
                        "knowledge_base_id",
                    ),
                    "effective_result_output_keys": (
                        "hit_count",
                        "knowledge_base_id",
                    ),
                    "execution_diagnostics": (
                        "http_json execution response_path must not be blank",
                    ),
                },
            ),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_redacts_sensitive_execution_diagnostics(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="Provider Search",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "hit_count": 1,
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
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
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        provider_search = result.tool_details[0]
        self.assertEqual(
            provider_search["execution_diagnostics"],
            (
                "unsupported tool execution kind [redacted]",
                "http_json execution [redacted] must be safe",
            ),
        )
        joined_diagnostics = "\n".join(provider_search["execution_diagnostics"])
        self.assertNotIn("api_key=hidden", joined_diagnostics)
        self.assertNotIn("access_token", joined_diagnostics)

    def test_build_configured_tool_registry_provider_preflight_summary_model_humanizes_unlabeled_real_tool_names(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_math": ToolRegistration(
                    name="provider_math",
                    kind="provider_calc",
                    label="",
                    retryable_by_default=True,
                    default_timeout_ms=13_000,
                    requires_user_context=True,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "expression": str(tool_input.get("expression", "")),
                        "result": 7.0,
                    },
                ),
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "hit_count": 1,
                        "knowledge_base_id": "demo-kb",
                        "chunks": ["alpha"],
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=SimpleNamespace(
                    tool_registry_provider_source="provider_suite",
                    tool_registry_provider_sources_json=json.dumps({}),
                ),
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        self.assertEqual(
            tuple(detail["label"] for detail in result.tool_details),
            ("Provider Math", "Provider Search"),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_includes_result_output_keys_for_real_provider_tools(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="Provider Search",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    result_preview_keys=("documents_total",),
                    result_output_keys=("documents_total",),
                    runtime_semantic_kind="provider_search",
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "documents_total": 1,
                        "documents": [{"id": "doc-1"}],
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=SimpleNamespace(
                    tool_registry_provider_source="provider_suite",
                    tool_registry_provider_sources_json=json.dumps({}),
                ),
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        self.assertEqual(
            result.tool_details,
            (
                {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "retryable_by_default": False,
                    "default_timeout_ms": 15_000,
                    "requires_user_context": False,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ("documents_total",),
                    "effective_result_output_keys": ("documents_total",),
                },
            ),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_falls_back_result_output_keys_to_preview_keys_for_runtime_override_real_tools(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "provider_search": ToolRegistration(
                    name="provider_search",
                    kind="provider_retrieval",
                    label="Provider Search",
                    retryable_by_default=False,
                    default_timeout_ms=15_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    result_preview_keys=("documents_total",),
                    runtime_semantic_kind="provider_search",
                    runner=lambda *, tool_input, prompt, user_id: {
                        "query": str(tool_input.get("query", "")),
                        "documents_total": 1,
                        "documents": [{"id": "doc-1"}],
                    },
                ),
            }
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=provider,
            provider_source_name="provider_suite",
            runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model(
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=SimpleNamespace(
                    tool_registry_provider_source="provider_suite",
                    tool_registry_provider_sources_json=json.dumps({}),
                ),
            ),
            service_actions=(),
            trace_write_count=0,
            audit_event_count=0,
        )

        self.assertEqual(
            result.tool_details,
            (
                {
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "retryable_by_default": False,
                    "default_timeout_ms": 15_000,
                    "requires_user_context": False,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ("documents_total",),
                    "effective_result_output_keys": ("documents_total",),
                },
            ),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_keeps_fields(
        self,
    ) -> None:
        preflight_result = {
            "provider_source_name": "default",
            "runtime_artifacts": {
                "diagnostics_runtime": {
                    "summary": {
                        "has_diagnostics": False,
                        "total": 0,
                        "skipped_total": 0,
                        "missing_total": 0,
                    }
                }
            },
            "provider": StaticToolRegistryProvider({}),
            "service_execution": {"service_actions": []},
            "trace_write_count": 0,
            "audit_event_count": 1,
        }

        result = build_configured_tool_registry_provider_preflight_summary_model(
            preflight_result=preflight_result
        )

        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.tool_count, 0)
        self.assertEqual(result.tool_names, ())
        self.assertEqual(result.service_action_kinds, ())
        self.assertEqual(result.audit_event_count, 1)

    def test_build_configured_tool_registry_provider_preflight_summary_model_uses_summary_model_from_dict_helper(
        self,
    ) -> None:
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model_from_dict
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary_model(
                preflight_result={
                    "provider_source_name": "default",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "provider": StaticToolRegistryProvider({}),
                    "service_execution": {"service_actions": []},
                    "trace_write_count": 0,
                    "audit_event_count": 1,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_summary_model_from_dict = original_helper

        self.assertEqual(captured, [(0, 1)])
        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(result.audit_event_count, 1)

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_dict_uses_service_execution_defaults(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_preflight_summary_model_from_dict(
            preflight_result={
                "service_execution": {
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
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.tool_names, ("calc_eval",))
        self.assertEqual(result.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertEqual(result.missing_total, 1)
        self.assertEqual(
            result.tool_details,
            (
                {
                    "name": "calc_eval",
                    "label": "Calculator",
                    "kind": "local_calculator",
                    "semantic_kind": "local_calculator",
                    "retryable_by_default": True,
                    "default_timeout_ms": 3_000,
                    "requires_user_context": True,
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ("expression", "result"),
                },
            ),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_dict_uses_result_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    str(preflight_result["service_execution"]["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary_model_from_dict(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.tool_names, ("calc_eval",))
        self.assertEqual(result.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_service_execution_model_from_dict_merges_runtime_artifacts(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "provider_source_name": "top_level_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "service_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "service_source")
        self.assertEqual(result.service_actions[0].kind, "record_audit_event")
        self.assertTrue(result.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.total, 2)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.skipped_total, 1)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_model_from_dict_uses_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict
        )
        captured: list[tuple[str, int]] = []

        def record_helper(*, preflight_result: dict[str, object]) -> dict[str, object]:
            service_execution = original_helper(preflight_result=preflight_result)
            runtime_artifacts = service_execution["runtime_artifacts"]
            summary = runtime_artifacts["diagnostics_runtime"]["summary"]
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(summary["missing_total"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "provider_source_name": "top_level_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "service_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict = original_helper

        self.assertEqual(captured, [("service_source", 1)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "service_source")
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = (
            build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict(
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertTrue(result.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict_uses_service_execution_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict
        )
        captured: list[tuple[str, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            service_execution_model = original_helper(preflight_result=preflight_result)
            captured.append(
                (
                    str(getattr(service_execution_model, "provider_source_name", None)),
                    int(
                        service_execution_model.runtime_artifacts.diagnostics_runtime.summary.missing_total
                    ),
                )
            )
            return service_execution_model

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict(
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                        "service_execution": {
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
                            "service_actions": [{"kind": "record_audit_event"}],
                        },
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )
        result = (
            build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
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
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.total, 2)
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model_uses_service_execution_result_model_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    execution_result["trace_write_count"],
                    execution_result["audit_event_count"],
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
                    service_execution=service_execution_model,
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model, execution_result_model = (
            build_configured_tool_registry_provider_preflight_execution_models_from_dict(
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(service_execution_model.service_actions[0].kind, "record_audit_event")
        self.assertTrue(
            service_execution_model.runtime_artifacts.diagnostics_runtime.summary.has_diagnostics
        )
        self.assertEqual(
            service_execution_model.runtime_artifacts.diagnostics_runtime.summary.total, 2
        )
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1
        )

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_dict_uses_service_execution_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict
        captured: list[tuple[str, int]] = []

        def record_models_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            service_execution_model = original_helper(preflight_result=preflight_result)
            captured.append(
                (
                    str(getattr(service_execution_model, "provider_source_name", None)),
                    int(
                        service_execution_model.runtime_artifacts.diagnostics_runtime.summary.missing_total
                    ),
                )
            )
            return service_execution_model

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = record_models_helper
        try:
            service_execution_model, execution_result_model = (
                build_configured_tool_registry_provider_preflight_execution_models_from_dict(
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                        "service_execution": {
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
                            "service_actions": [{"kind": "record_audit_event"}],
                        },
                    }
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_model_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_payload_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_payload(
            service_execution={
                "provider": provider,
                "provider_source_name": "service_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [{"kind": "record_audit_event"}],
            },
            preflight_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload_uses_service_execution_result_model_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = record_helper
        try:
            service_execution_model, execution_result_model = (
                tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload(
                    service_execution={
                        "provider": provider,
                        "provider_source_name": "service_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": True,
                                    "total": 2,
                                    "skipped_total": 1,
                                    "missing_total": 1,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = original_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_payload_uses_execution_models_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            preflight_result: dict[str, object],
        ) -> tuple[object, object]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_payload(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload = original_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_dict(
            preflight_result={
                "provider_source_name": "top_level_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "service_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(summary_model.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_model.missing_total, 1)
        self.assertEqual(result_model.provider_source_name, "service_source")
        self.assertEqual(result_model.summary.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_dict_uses_execution_models_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_dict
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *, preflight_result: dict[str, object]
        ) -> tuple[object, object]:
            captured.append(
                (
                    str(preflight_result["service_execution"]["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_dict = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_dict(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_dict = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        service_execution_model_out, execution_result_model = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1
        )

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model_uses_service_execution_result_model_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                )
            )
            return original_helper(service_execution=service_execution, preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = record_helper
        try:
            service_execution_model_out, execution_result_model = (
                tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model(
                    service_execution=service_execution_model,
                    preflight_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_models_uses_models_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = original_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_model_uses_execution_models_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
        )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                )
            )
            return original_helper(service_execution=service_execution, preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = record_helper
        try:
            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        (
            service_execution_model_out,
            execution_result_model,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
            service_execution=service_execution_model,
            preflight_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model.provider, provider)
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(summary_model.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result_model.provider_source_name, "file_source")
        self.assertEqual(result_model.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_models_from_service_execution_model_uses_models_from_models_helper_via_typed_path(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_models
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    getattr(execution_result, "trace_write_count"),
                    getattr(execution_result, "audit_event_count"),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_models = record_helper
        try:
            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
            ) = build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_models = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_parts_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
            provider=service_execution_result_model.provider,
            provider_source_name=service_execution_result_model.provider_source_name,
            runtime_artifacts=service_execution_result_model.runtime_artifacts,
            service_actions=service_execution_model.service_actions,
            trace_write_count=service_execution_result_model.trace_write_count,
            audit_event_count=service_execution_result_model.audit_event_count,
        )

        self.assertEqual(result.provider_source_name, "default")
        self.assertEqual(
            result.tool_names,
            tuple(sorted(service_execution_result_model.provider.load_tool_registry())),
        )
        self.assertEqual(result.service_action_kinds, ())
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_result_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
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
            "service_actions": [{"kind": "record_audit_event"}],
        }
        execution_result = {
            "provider": provider,
            "provider_source_name": "file_source",
            "runtime_artifacts": service_execution["runtime_artifacts"],
            "trace_write_count": 1,
            "audit_event_count": 2,
        }

        result = build_configured_tool_registry_provider_preflight_result_model(
            service_execution=service_execution,
            execution_result=execution_result,
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_uses_models_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
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
            "service_actions": [{"kind": "record_audit_event"}],
        }
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    str(service_execution["provider_source_name"]),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result_model(
                service_execution=service_execution,
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_payload = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_execution": {
                        "provider": provider,
                        "provider_source_name": "file_source",
                        "runtime_artifacts": {
                            "diagnostics_runtime": {
                                "summary": {
                                    "has_diagnostics": False,
                                    "total": 0,
                                    "skipped_total": 0,
                                    "missing_total": 0,
                                }
                            }
                        },
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                }
            )
        )

        result = (
            build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model(
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
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model_uses_models_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
        )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_model = record_helper
        try:
            result = (
                build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model(
                    service_execution=service_execution_model,
                    execution_result={
                        "trace_write_count": 1,
                        "audit_event_count": 2,
                    },
                )
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_result_model_uses_service_execution_defaults(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution = {
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
            "service_actions": [{"kind": "record_audit_event"}],
        }

        result = build_configured_tool_registry_provider_preflight_result_model(
            service_execution=service_execution,
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload_fills_missing_metadata_from_execution_result(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        service_execution_model, execution_result_model = (
            build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload(
                service_execution={
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                preflight_result={
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
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(
            service_execution_model.runtime_artifacts.diagnostics_runtime.summary.missing_total,
            1,
        )
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total,
            1,
        )
        self.assertEqual(execution_result_model.trace_write_count, 1)
        self.assertEqual(execution_result_model.audit_event_count, 2)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload_overlays_execution_result_runtime_artifacts(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
            service_execution={
                "provider": provider,
                "provider_source_name": "service_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": False,
                            "total": 0,
                            "skipped_total": 0,
                            "missing_total": 0,
                        }
                    }
                },
                "service_actions": [{"kind": "record_audit_event"}],
            },
            execution_result={
                "provider_source_name": "result_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertEqual(service_execution_model.provider_source_name, "service_source")
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.provider_source_name, "service_source")
        self.assertEqual(result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.missing_total, 1)
        self.assertEqual(
            execution_result_model.runtime_artifacts.diagnostics_runtime.summary.missing_total,
            1,
        )
        self.assertEqual(result_dict["provider_source_name"], "service_source")
        self.assertEqual(summary_dict["missing_total"], 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_preflight_result_model_from_dict(
            preflight_result={
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
                "service_execution": {
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
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_dict_uses_service_execution_defaults(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        result = build_configured_tool_registry_provider_preflight_result_model_from_dict(
            preflight_result={
                "service_execution": {
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
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(result.provider, provider)
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.summary.provider_source_name, "file_source")
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(result.summary.missing_total, 1)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_dict_uses_outputs_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_models_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict
        captured: list[tuple[int, int, str]] = []

        def record_models_helper(
            *, preflight_result: dict[str, object]
        ) -> tuple[object, object, object, object, dict[str, object], dict[str, object]]:
            captured.append(
                (
                    preflight_result["trace_write_count"],
                    preflight_result["audit_event_count"],
                    str(preflight_result["service_execution"]["provider_source_name"]),
                )
            )
            return original_models_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = record_models_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result_model_from_dict(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = original_models_helper

        self.assertEqual(captured, [(1, 2, "file_source")])
        self.assertIs(result.provider, provider)
        self.assertEqual(result.summary.tool_names, ("calc_eval",))
        self.assertEqual(result.summary.service_action_kinds, ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_dicts_uses_result_model_from_dict_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict
        captured: list[tuple[int, int]] = []

        def record_helper(
            *,
            preflight_result: dict[str, object],
        ) -> object:
            captured.append(
                (
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = record_helper
        try:
            summary_dict, result_dict = build_configured_tool_registry_provider_preflight_dicts(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_dict = original_helper

        self.assertEqual(captured, [(1, 2)])
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(
            result_dict["summary"]["service_action_kinds"],
            ("record_audit_event",),
        )

    def test_build_configured_tool_registry_provider_preflight_result_model_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        result = build_configured_tool_registry_provider_preflight_result_model_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        self.assertIs(result.provider, service_execution_model.provider)
        self.assertEqual(
            result.runtime_artifacts.provider_source_name,
            service_execution_model.runtime_artifacts.provider_source_name,
        )
        self.assertEqual(
            result.service_execution.provider_source_name,
            service_execution_model.provider_source_name,
        )
        self.assertEqual(result.trace_write_count, 1)
        self.assertEqual(result.audit_event_count, 2)
        self.assertEqual(result.summary.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            result.summary.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )
        self.assertEqual(result.summary.service_action_kinds, ())

    def test_build_configured_tool_registry_provider_preflight_models_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        (
            service_execution_model_out,
            execution_result_model_out,
            summary_model,
            result_model,
        ) = build_configured_tool_registry_provider_preflight_models_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model_out, service_execution_result_model)
        self.assertEqual(summary_model.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            summary_model.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )
        self.assertEqual(result_model.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(result_model.summary.tool_names, summary_model.tool_names)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_models_keeps_fields(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        (
            service_execution_model_out,
            execution_result_model_out,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertIs(execution_result_model_out, service_execution_result_model)
        self.assertEqual(summary_dict["provider_source_name"], summary_model.provider_source_name)
        self.assertEqual(summary_dict["tool_names"], summary_model.tool_names)
        self.assertIs(result_dict["provider"], result_model.provider)
        self.assertEqual(result_dict["summary"]["tool_names"], result_model.summary.tool_names)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
            service_execution={
                "provider": provider,
                "provider_source_name": "service_source",
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_actions": [{"kind": "record_audit_event"}],
            },
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_uses_outputs_from_service_execution_payload_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload
        )
        captured: list[tuple[int, int, str]] = []

        def record_helper(
            *,
            service_execution: dict[str, object],
            execution_result: dict[str, object],
        ) -> tuple[object, object, object, object, object, object]:
            captured.append(
                (
                    int(execution_result["trace_write_count"]),
                    int(execution_result["audit_event_count"]),
                    str(service_execution["provider_source_name"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload = original_helper

        self.assertEqual(captured, [(1, 2, "service_source")])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model
        original_dict_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object, object, object]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = record_helper
        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = (
            lambda **kwargs: (_ for _ in ()).throw(
                AssertionError("outputs_from_service_execution_payload should not call outputs_from_dict")
            )
        )
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
                service_execution={
                    "provider": provider,
                    "provider_source_name": "service_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": True,
                                "total": 2,
                                "skipped_total": 1,
                                "missing_total": 1,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                execution_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = original_helper
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_dict = original_dict_helper

        self.assertEqual(captured, [("service_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "service_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
            )
        )

        (
            service_execution_model_out,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
            service_execution=service_execution_model,
            preflight_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_uses_execution_models_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        service_execution_model = (
            build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    }
                }
        )
        )
        original_helper = (
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model
        )
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(service_execution=service_execution, preflight_result=preflight_result)

        tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = record_helper
        try:
            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
                service_execution=service_execution_model,
                preflight_result={
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                },
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_outputs_from_dict_keeps_fields(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        (
            service_execution_model,
            execution_result_model,
            summary_model,
            result_model,
            summary_dict,
            result_dict,
        ) = build_configured_tool_registry_provider_preflight_outputs_from_dict(
            preflight_result={
                "runtime_artifacts": {
                    "diagnostics_runtime": {
                        "summary": {
                            "has_diagnostics": True,
                            "total": 2,
                            "skipped_total": 1,
                            "missing_total": 1,
                        }
                    }
                },
                "service_execution": {
                    "provider": provider,
                    "provider_source_name": "file_source",
                    "runtime_artifacts": {
                        "diagnostics_runtime": {
                            "summary": {
                                "has_diagnostics": False,
                                "total": 0,
                                "skipped_total": 0,
                                "missing_total": 0,
                            }
                        }
                    },
                    "service_actions": [{"kind": "record_audit_event"}],
                },
                "trace_write_count": 1,
                "audit_event_count": 2,
            }
        )

        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)

    def test_build_configured_tool_registry_provider_preflight_outputs_from_dict_uses_outputs_from_service_execution_model_helper(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            preflight_result: dict[str, object],
        ) -> tuple[object, object, object, object, dict[str, object], dict[str, object]]:
            captured.append(
                (
                    str(getattr(service_execution, "provider_source_name", None)),
                    int(preflight_result["trace_write_count"]),
                    int(preflight_result["audit_event_count"]),
                )
            )
            return original_helper(
                service_execution=service_execution,
                preflight_result=preflight_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = record_helper
        try:
            (
                service_execution_model,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = build_configured_tool_registry_provider_preflight_outputs_from_dict(
                preflight_result={
                    "service_execution": {
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
                        "service_actions": [{"kind": "record_audit_event"}],
                    },
                    "trace_write_count": 1,
                    "audit_event_count": 2,
                }
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", 1, 2)])
        self.assertIs(service_execution_model.provider, provider)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval",))
        self.assertEqual(result_model.summary.service_action_kinds, ("record_audit_event",))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval",))
        self.assertEqual(result_dict["summary"]["service_action_kinds"], ("record_audit_event",))

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_models_uses_result_model_from_models_helper(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_models
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> object:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    getattr(execution_result, "trace_write_count"),
                    getattr(execution_result, "audit_event_count"),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_models = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_summary_model_from_models(
                service_execution=service_execution_model,
                execution_result=service_execution_result_model,
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_result_model_from_models = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertEqual(result.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            result.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )

    def test_build_configured_tool_registry_provider_preflight_summary_model_from_result_model_returns_existing_summary(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )
        preflight_result_model = build_configured_tool_registry_provider_preflight_result_model_from_models(
            service_execution=service_execution_model,
            execution_result=service_execution_result_model,
        )

        result = build_configured_tool_registry_provider_preflight_summary_model_from_result_model(
            preflight_result=preflight_result_model,
        )

        self.assertIs(result, preflight_result_model.summary)

    def test_build_configured_tool_registry_provider_preflight_result_model_from_models_uses_outputs_from_models_helper(
        self,
    ) -> None:
        service_execution_model = build_configured_tool_registry_provider_service_execution_model(
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            settings=SimpleNamespace(),
        )
        service_execution_result_model = build_configured_tool_registry_provider_service_execution_result_model(
            service_execution=service_execution_model.to_dict(),
            execution_result={
                "trace_write_count": 1,
                "audit_event_count": 2,
            },
        )
        original_helper = tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_models
        captured: list[tuple[str, int, int]] = []

        def record_helper(
            *,
            service_execution: object,
            execution_result: object,
        ) -> tuple[object, object, object, object, dict[str, object], dict[str, object]]:
            captured.append(
                (
                    getattr(service_execution, "provider_source_name"),
                    getattr(execution_result, "trace_write_count"),
                    getattr(execution_result, "audit_event_count"),
                )
            )
            return original_helper(
                service_execution=service_execution,
                execution_result=execution_result,
            )

        tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_models = record_helper
        try:
            result = build_configured_tool_registry_provider_preflight_result_model_from_models(
                service_execution=service_execution_model,
                execution_result=service_execution_result_model,
            )
        finally:
            tool_runtime_module.build_configured_tool_registry_provider_preflight_outputs_from_models = original_helper

        self.assertEqual(captured, [("default", 1, 2)])
        self.assertEqual(result.provider_source_name, service_execution_model.provider_source_name)
        self.assertEqual(
            result.summary.tool_names,
            tuple(sorted(service_execution_model.provider.load_tool_registry())),
        )

    def test_execute_configured_tool_registry_provider_preflight_model_keeps_fields(
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

            result = execute_configured_tool_registry_provider_preflight_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result.runtime_artifacts.diagnostics_runtime.summary.missing_total, 1)
        self.assertEqual(result.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_model_surfaces_invalid_tool_execution_diagnostics(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        settings = SimpleNamespace(
            tool_registry_provider_source="analytics_suite",
            tool_registry_provider_sources_json=json.dumps(
                {
                    "analytics_suite": {
                        "provider": "default",
                        "profile": "default",
                        "disabled_tool_names": [
                            "task_plan",
                            "task_retrieve",
                            "calc_eval",
                        ],
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "unsupported_transport",
                                },
                            }
                        },
                    }
                }
            ),
        )

        result = execute_configured_tool_registry_provider_preflight_model(
            settings=settings,
            task_id="task-1",
            step_id="step-registry",
            seq=2,
            model="mock-gpt",
            trace_steps=trace_steps,
            persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
            record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
        )

        self.assertEqual(result.provider_source_name, "analytics_suite")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("provider_search",),
        )
        self.assertTrue(result.summary.has_diagnostics)
        self.assertEqual(result.summary.skipped_total, 0)
        self.assertEqual(result.summary.missing_total, 0)
        self.assertEqual(result.summary.diagnostics_total, 1)
        self.assertEqual(
            result.summary.diagnostics_summary["entries"],
            (
                {
                    "kind": "invalid",
                    "target": "tool_executions",
                    "count": 1,
                    "values": (
                        "provider_search: unsupported tool execution kind unsupported_transport",
                    ),
                },
            ),
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_model_surfaces_file_backed_real_calc_diagnostics(
        self,
    ) -> None:
        trace_steps: list[dict[str, object]] = []
        persisted: list[bool] = []
        audit_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "calc-diagnostics-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_math": {
                                "template": "calc_eval",
                                "label": "Provider Calculator",
                                "kind": "provider_calc",
                                "execution": {
                                    "kind": "http_json",
                                    "method": "POST",
                                    "url": "https://provider.example/calc",
                                    "headers": {
                                        "Authorization": "Bearer ${settings_api_keey}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "json_body": {
                                        "expression": "$expression",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "result": "$.value",
                                    },
                                },
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="calculator_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "calculator_suite": {
                            "registry_file": str(registry_file),
                            "profile": "calculator_only",
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
            )

            result = execute_configured_tool_registry_provider_preflight_model(
                settings=settings,
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        expected_diagnostic = (
            "provider_math: http_json execution references unsupported runtime "
            "template variable settings_api_keey in [redacted]"
        )
        expected_tool_diagnostic = (
            "http_json execution references unsupported runtime template variable "
            "settings_api_keey in [redacted]"
        )
        self.assertEqual(result.provider_source_name, "calculator_suite")
        self.assertTrue(result.summary.has_diagnostics)
        self.assertEqual(result.summary.diagnostics_total, 1)
        self.assertEqual(
            result.summary.diagnostics_summary["entries"],
            (
                {
                    "kind": "invalid",
                    "target": "tool_executions",
                    "count": 1,
                    "values": (expected_diagnostic,),
                },
            ),
        )
        provider_math_detail = next(
            detail for detail in result.summary.tool_details if detail["name"] == "provider_math"
        )
        self.assertEqual(
            provider_math_detail["execution_diagnostics"],
            (expected_tool_diagnostic,),
        )
        self.assertEqual(
            result.runtime_artifacts.selected_source_diagnostics["invalid_tool_executions"],
            (expected_diagnostic,),
        )
        self.assertEqual(
            trace_steps[0]["meta"]["tool_registry"]["total"],
            1,
        )
        self.assertEqual(
            trace_steps[0]["meta"]["tool_registry"]["entries"],
            (
                {
                    "kind": "invalid",
                    "target": "tool_executions",
                    "count": 1,
                    "values": (expected_diagnostic,),
                },
            ),
        )
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_keeps_fields(
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
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=settings,
            )

            (
                service_execution_model_out,
                execution_result_model,
                summary_model,
                result_model,
                summary_dict,
                result_dict,
            ) = tool_runtime_module.execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
                service_execution=service_execution_model,
                trace_steps=trace_steps,
                persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
            )

        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval_fast",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model_uses_models_from_service_execution_model_helper(
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
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=settings,
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        tuple(sorted(getattr(service_execution, "provider").load_tool_registry())),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = record_helper
            try:
                (
                    service_execution_model_out,
                    execution_result_model,
                    summary_model,
                    result_model,
                    summary_dict,
                    result_dict,
                ) = tool_runtime_module.execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("calc_eval_fast",))])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval_fast",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_models_from_service_execution_model_uses_service_execution_outputs_from_service_execution_model_helper(
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
                task_id="task-1",
                step_id="step-registry",
                seq=2,
                model="mock-gpt",
                settings=settings,
            )
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model
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
                        tuple(sorted(getattr(service_execution, "provider").load_tool_registry())),
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
                (
                    service_execution_model_out,
                    execution_result_model,
                    summary_model,
                    result_model,
                ) = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model(
                    service_execution=service_execution_model,
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("calc_eval_fast",))])
        self.assertIs(service_execution_model_out, service_execution_model)
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_outputs_uses_models_helper(
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
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        task_id,
                        (step_id, str(seq), model),
                    )
                )
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = record_helper
            try:
                (
                    service_execution_model,
                    execution_result_model,
                    summary_model,
                    result_model,
                    summary_dict,
                    result_dict,
                ) = execute_configured_tool_registry_provider_preflight_outputs(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = original_helper

        self.assertEqual(captured, [("task-1", ("step-registry", "2", "mock-gpt"))])
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(summary_dict["tool_names"], ("calc_eval_fast",))
        self.assertEqual(result_dict["summary"]["missing_total"], 1)
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_models_uses_models_from_service_execution_model_helper(
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
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                service_execution: object,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        str(getattr(service_execution, "provider_source_name", None)),
                        tuple(sorted(getattr(service_execution, "provider").load_tool_registry())),
                    )
                )
                return original_helper(
                    service_execution=service_execution,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = record_helper
            try:
                (
                    service_execution_model,
                    execution_result_model,
                    summary_model,
                    result_model,
                ) = execute_configured_tool_registry_provider_preflight_models(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models_from_service_execution_model = original_helper

        self.assertEqual(captured, [("file_source", ("calc_eval_fast",))])
        self.assertEqual(service_execution_model.provider_source_name, "file_source")
        self.assertEqual(execution_result_model.provider_source_name, "file_source")
        self.assertEqual(summary_model.tool_names, ("calc_eval_fast",))
        self.assertEqual(result_model.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_summary_model_uses_model_helper(
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
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_model
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append(
                    (
                        task_id,
                        tuple(),
                    )
                )
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight_summary_model(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = original_helper

        self.assertEqual(captured, [("task-1", ())])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(result.tool_names, ("calc_eval_fast",))
        self.assertEqual(result.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_summary_uses_summary_model_helper(
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
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_summary_model
            captured: list[tuple[str, int, str]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append((task_id, seq, model))
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_summary_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight_summary(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_summary_model = original_helper

        self.assertEqual(captured, [("task-1", 2, "mock-gpt")])
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(result["tool_names"], ("calc_eval_fast",))
        self.assertEqual(
            result["service_action_kinds"],
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_model_uses_models_helper(
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
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_models
            captured: list[tuple[str, tuple[str, ...]]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> tuple[object, object, object, object]:
                captured.append(
                    (
                        task_id,
                        tuple(),
                    )
                )
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight_model(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_models = original_helper

        self.assertEqual(captured, [("task-1", ())])
        self.assertEqual(result.provider_source_name, "file_source")
        self.assertEqual(
            tuple(sorted(result.provider.load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(result.summary.service_action_kinds, ("internal_trace_write", "record_audit_event"))
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_uses_model_helper(
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
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_model
            captured: list[tuple[str, int, str]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append((task_id, seq, model))
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = record_helper
            try:
                result = execute_configured_tool_registry_provider_preflight(
                    settings=settings,
                    task_id="task-1",
                    step_id="step-registry",
                    seq=2,
                    model="mock-gpt",
                    trace_steps=trace_steps,
                    persist_trace_fn=lambda **kwargs: persisted.append(bool(kwargs["force"])),
                    record_audit_event_fn=lambda **kwargs: audit_calls.append(kwargs),
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = original_helper

        self.assertEqual(captured, [("task-1", 2, "mock-gpt")])
        self.assertEqual(result["provider_source_name"], "file_source")
        self.assertEqual(
            tuple(sorted(result["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            result["summary"]["service_action_kinds"],
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)

    def test_execute_configured_tool_registry_provider_preflight_dicts_uses_model_helper(
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
            original_helper = tool_runtime_module.execute_configured_tool_registry_provider_preflight_model
            captured: list[tuple[str, int, str]] = []

            def record_helper(
                *,
                task_id: str,
                step_id: str,
                seq: int,
                model: str,
                trace_steps: list[dict[str, object]],
                persist_trace_fn: object,
                record_audit_event_fn: object,
                settings: object | None = None,
            ) -> object:
                captured.append((task_id, seq, model))
                return original_helper(
                    task_id=task_id,
                    step_id=step_id,
                    seq=seq,
                    model=model,
                    trace_steps=trace_steps,
                    persist_trace_fn=persist_trace_fn,
                    record_audit_event_fn=record_audit_event_fn,
                    settings=settings,
                )

            tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = record_helper
            try:
                summary_dict, result_dict = (
                    execute_configured_tool_registry_provider_preflight_dicts(
                        settings=settings,
                        task_id="task-1",
                        step_id="step-registry",
                        seq=2,
                        model="mock-gpt",
                        trace_steps=trace_steps,
                        persist_trace_fn=lambda **kwargs: persisted.append(
                            bool(kwargs["force"])
                        ),
                        record_audit_event_fn=lambda **kwargs: audit_calls.append(
                            kwargs
                        ),
                    )
                )
            finally:
                tool_runtime_module.execute_configured_tool_registry_provider_preflight_model = original_helper

        self.assertEqual(captured, [("task-1", 2, "mock-gpt")])
        self.assertEqual(summary_dict["provider_source_name"], "file_source")
        self.assertEqual(result_dict["provider_source_name"], "file_source")
        self.assertEqual(
            result_dict["summary"]["service_action_kinds"],
            ("internal_trace_write", "record_audit_event"),
        )
        self.assertEqual(len(trace_steps), 1)
        self.assertEqual(persisted, [True])
        self.assertEqual(len(audit_calls), 1)
