from __future__ import annotations

from .context import *


class RegistryProviderSourceAliasesMixin:
    def test_settings_summary_disambiguates_colliding_redacted_provider_source_aliases(
        self,
    ) -> None:
        summary = _build_settings_summary_response(
            settings=StoredSettings(
                mode="mock",
                provider="mock",
                model="mock-gpt",
                base_url=None,
                api_key=None,
                tool_registry_profile="default",
                tool_registry_provider_source="suite_api_key=one",
            ),
            runtime_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_access_token=two": {
                            "profile": "retrieval_only",
                        },
                        "suite_api_key=one": {
                            "profile": "planning_only",
                        },
                    },
                    ensure_ascii=False,
                ),
                task_queue_max_concurrent=1,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.25,
            ),
            database_locator="postgresql://demo",
        )
        payload = summary.model_dump()

        self.assertEqual(
            payload["tool_registry_provider_source"],
            "suite_[redacted]#2",
        )
        self.assertEqual(
            payload["available_tool_registry_provider_sources"],
            ["default", "suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertEqual(
            [
                detail["name"]
                for detail in payload["available_tool_registry_provider_source_details"]
            ],
            ["default", "suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertNotIn("api_key=one", json.dumps(payload, default=str))
        self.assertNotIn("access_token=two", json.dumps(payload, default=str))

    def test_validate_settings_accepts_disambiguated_redacted_provider_source_alias(
        self,
    ) -> None:
        original_get_stored_settings = settings_routes_module.get_stored_settings
        original_get_settings = settings_routes_module.get_settings
        original_safe_record_audit_event = settings_routes_module.safe_record_audit_event
        audit_details: list[dict[str, object]] = []
        try:
            settings_routes_module.get_stored_settings = lambda _user_id: StoredSettings(
                mode="mock",
                provider="mock",
                model="mock-gpt",
                base_url=None,
                api_key=None,
                tool_registry_profile="default",
                tool_registry_provider_source="default",
            )
            settings_routes_module.get_settings = lambda: SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_access_token=two": {
                            "profile": "retrieval_only",
                        },
                        "suite_api_key=one": {
                            "profile": "planning_only",
                        },
                    },
                    ensure_ascii=False,
                ),
            )
            settings_routes_module.safe_record_audit_event = (
                lambda **kwargs: audit_details.append(dict(kwargs.get("detail", {})))
            )

            result = settings_routes_module.validate_settings(
                settings_routes_module.SettingsUpdateRequest(
                    mode="mock",
                    provider="mock",
                    model="mock-gpt",
                    tool_registry_provider_source="suite_[redacted]#2",
                ),
                current_user={"id": "user-1"},
            )
        finally:
            settings_routes_module.get_stored_settings = original_get_stored_settings
            settings_routes_module.get_settings = original_get_settings
            settings_routes_module.safe_record_audit_event = (
                original_safe_record_audit_event
            )

        payload = result.model_dump()
        self.assertTrue(result.ok)
        self.assertEqual(payload["tool_registry_provider_source"], "suite_[redacted]#2")
        self.assertEqual(
            [
                detail["name"]
                for detail in payload["available_tool_registry_provider_source_details"]
            ],
            ["default", "suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertEqual(
            audit_details[-1]["tool_registry_provider_source"],
            "suite_api_key=one",
        )
        self.assertNotIn("api_key=one", json.dumps(payload, default=str))
        self.assertNotIn("access_token=two", json.dumps(payload, default=str))

    def test_update_settings_saves_disambiguated_redacted_provider_source_alias_as_raw_source(
        self,
    ) -> None:
        original_get_stored_settings = settings_routes_module.get_stored_settings
        original_get_settings = settings_routes_module.get_settings
        original_save_settings = settings_routes_module.save_settings
        original_build_settings_summary_response = (
            settings_routes_module._build_settings_summary_response
        )
        original_safe_record_audit_event = settings_routes_module.safe_record_audit_event
        saved_settings: list[StoredSettings] = []
        try:
            settings_routes_module.get_stored_settings = lambda _user_id: StoredSettings(
                mode="mock",
                provider="mock",
                model="mock-gpt",
                base_url=None,
                api_key=None,
                tool_registry_profile="default",
                tool_registry_provider_source="default",
            )
            settings_routes_module.get_settings = lambda: SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_access_token=two": {
                            "profile": "retrieval_only",
                        },
                        "suite_api_key=one": {
                            "profile": "planning_only",
                        },
                    },
                    ensure_ascii=False,
                ),
            )
            settings_routes_module.save_settings = lambda _user_id, settings: (
                saved_settings.append(settings) or settings
            )
            settings_routes_module._build_settings_summary_response = (
                lambda *, settings, runtime_settings=None, database_locator=None, **_kwargs: settings
            )
            settings_routes_module.safe_record_audit_event = lambda **_kwargs: None

            result = settings_routes_module.update_settings(
                settings_routes_module.SettingsUpdateRequest(
                    mode="mock",
                    provider="mock",
                    model="mock-gpt",
                    tool_registry_provider_source="suite_[redacted]#1",
                ),
                current_user={"id": "user-1"},
            )
        finally:
            settings_routes_module.get_stored_settings = original_get_stored_settings
            settings_routes_module.get_settings = original_get_settings
            settings_routes_module.save_settings = original_save_settings
            settings_routes_module._build_settings_summary_response = (
                original_build_settings_summary_response
            )
            settings_routes_module.safe_record_audit_event = (
                original_safe_record_audit_event
            )

        self.assertEqual(len(saved_settings), 1)
        self.assertEqual(
            saved_settings[0].tool_registry_provider_source,
            "suite_access_token=two",
        )
        self.assertEqual(result.tool_registry_provider_source, "suite_access_token=two")

    def test_task_list_queries_resolve_disambiguated_redacted_provider_source_alias_filter(
        self,
    ) -> None:
        original_get_db_connection = chat_persistence_module.get_db_connection
        original_get_settings = chat_persistence_module.get_settings
        captured: dict[str, list[tuple[object, ...]]] = {"params": []}

        class FakeListCursor:
            def fetchall(self) -> list[dict]:
                return []

        class FakeCountCursor:
            def fetchone(self) -> dict[str, int]:
                return {"n": 0}

        class FakeConnection:
            def execute(self, query: str, params=()):
                captured["params"].append(tuple(params))
                if "COUNT(*)" in query:
                    return FakeCountCursor()
                return FakeListCursor()

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, exc_type, exc, tb):
                return False

        try:
            chat_persistence_module.get_db_connection = lambda: FakeContextManager()
            chat_persistence_module.get_settings = lambda: SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_access_token=two": {
                            "profile": "retrieval_only",
                        },
                        "suite_api_key=one": {
                            "profile": "planning_only",
                        },
                    }
                )
            )
            chat_persistence_module.list_tasks(
                user_id="user-governance-alias",
                limit=20,
                session_id="session-governance-alias",
                offset=0,
                tool_registry_provider_source_filter="suite_[redacted]#2",
            )
            chat_persistence_module.count_tasks(
                user_id="user-governance-alias",
                session_id="session-governance-alias",
                tool_registry_provider_source_filter="suite_[redacted]#2",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module.get_settings = original_get_settings

        self.assertEqual(
            captured["params"],
            [
                (
                    "user-governance-alias",
                    "session-governance-alias",
                    "suite_api_key=one",
                    20,
                    0,
                ),
                (
                    "user-governance-alias",
                    "session-governance-alias",
                    "suite_api_key=one",
                ),
            ],
        )

    def test_get_tasks_usage_dashboard_resolves_disambiguated_redacted_provider_source_alias_filter(
        self,
    ) -> None:
        rows = [
            {
                "id": "task-usage-filtered-disambiguated-alias-1",
                "session_id": "session-usage-filtered-disambiguated-alias-1",
                "prompt": "disambiguated alias-filtered dashboard row",
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
                "tool_registry_provider_source": "suite_api_key=one",
                "allowed_tool_names_json": json.dumps(["task_plan"]),
                "allowed_tool_labels_json": json.dumps(["Task Planner Suite"]),
                "created_at": "2026-06-10T10:00:00",
                "updated_at": "2026-06-10T10:05:00",
                "session_title": "Disambiguated Alias Filter Session",
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
                        "suite_access_token=two": {
                            "profile": "retrieval_only",
                        },
                        "suite_api_key=one": {
                            "profile": "planning_only",
                        },
                    }
                )
            )
            payload = chat_persistence_module.get_tasks_usage_dashboard(
                "user-usage-filtered-disambiguated-alias",
                tool_registry_provider_source_filter="suite_[redacted]#2",
            )
        finally:
            chat_persistence_module.get_db_connection = original_get_db_connection
            chat_persistence_module.get_settings = original_get_settings

        self.assertEqual(payload["summary"]["tasks_with_usage"], 1)
        self.assertEqual(len(payload["by_session"]), 1)
        self.assertEqual(
            payload["by_session"][0]["session_id"],
            "session-usage-filtered-disambiguated-alias-1",
        )
        self.assertEqual(len(payload["top_tasks"]), 1)
        self.assertEqual(
            payload["top_tasks"][0]["task_id"],
            "task-usage-filtered-disambiguated-alias-1",
        )

    def test_session_governance_export_disambiguates_colliding_redacted_provider_source_aliases(
        self,
    ) -> None:
        payload = (
            chat_persistence_module._sanitize_session_governance_provider_source_values_for_export(
                {
                    "profiles": ["planning_only", "retrieval_only"],
                    "provider_sources": [
                        "suite_access_token=two",
                        "suite_api_key=one",
                    ],
                    "allowed_tool_names": ["task_plan"],
                    "allowed_tool_labels": ["Task Planner Suite"],
                }
            )
        )

        self.assertIsInstance(payload, dict)
        self.assertEqual(
            payload["provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertNotIn("api_key=one", json.dumps(payload, default=str))
        self.assertNotIn("access_token=two", json.dumps(payload, default=str))

    def test_usage_dashboard_summary_disambiguates_colliding_session_provider_source_aliases(
        self,
    ) -> None:
        payload = chat_persistence_module.get_tasks_usage_dashboard_response_summary(
            {
                "window_days": 14,
                "summary": {"tasks_total": 2},
                "trend": [],
                "by_session": [
                    {
                        "session_id": "session-usage-disambiguated-summary",
                        "session_title": "Disambiguated Usage Summary",
                        "tasks_with_usage": 2,
                        "total_tokens": 46,
                        "cost_estimate": 0.12,
                        "last_task_at": "2026-06-22T20:00:00",
                        "governance": {
                            "profiles": ["planning_only", "retrieval_only"],
                            "provider_sources": [
                                "suite_access_token=two",
                                "suite_api_key=one",
                            ],
                            "allowed_tool_names": ["task_plan"],
                            "allowed_tool_labels": ["Task Planner Suite"],
                        },
                    }
                ],
                "top_tasks": [],
            }
        )

        governance = payload["by_session"][0]["governance"]
        self.assertIsInstance(governance, dict)
        self.assertEqual(
            governance["provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertNotIn("api_key=one", json.dumps(payload, default=str))
        self.assertNotIn("access_token=two", json.dumps(payload, default=str))

    def test_audit_detail_disambiguates_colliding_redacted_provider_source_aliases(
        self,
    ) -> None:
        payload = audit_service_module.sanitize_audit_event_detail(
            {
                "diagnostics": {
                    "provider_sources": [
                        "suite_access_token=two",
                        "suite_api_key=one",
                    ],
                    "tool_registry_provider_sources": [
                        "suite_access_token=two",
                        "suite_api_key=one",
                    ],
                },
            }
        )

        self.assertIsInstance(payload, dict)
        assert isinstance(payload, dict)
        self.assertEqual(
            payload["diagnostics"]["provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertEqual(
            payload["diagnostics"]["tool_registry_provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertNotIn("api_key=one", json.dumps(payload, default=str))
        self.assertNotIn("access_token=two", json.dumps(payload, default=str))

    def test_trace_meta_disambiguates_colliding_redacted_provider_source_aliases(
        self,
    ) -> None:
        step = chat_persistence_module.TraceStep(  # type: ignore[attr-defined]
            id="trace-source-alias-disambiguation",
            type="thought",
            content="trace provider source alias disambiguation",
            seq=1,
            meta={
                "provider_sources": [
                    "suite_access_token=two",
                    "suite_api_key=one",
                ],
                "nested": {
                    "tool_registry_provider_sources": [
                        "suite_access_token=two",
                        "suite_api_key=one",
                    ],
                },
            },
        )

        sanitized = chat_persistence_module._sanitize_trace_step_for_export(step)  # type: ignore[attr-defined]
        payload = sanitized.model_dump()

        self.assertEqual(
            payload["meta"]["provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertEqual(
            payload["meta"]["nested"]["tool_registry_provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertNotIn("api_key=one", json.dumps(payload, default=str))
        self.assertNotIn("access_token=two", json.dumps(payload, default=str))

    def test_runtime_artifact_sanitizer_disambiguates_colliding_redacted_provider_source_aliases(
        self,
    ) -> None:
        payload = (
            tool_runtime_module._sanitize_tool_runtime_provider_source_fields_for_artifact(
                {
                    "provider_sources": [
                        "suite_access_token=two",
                        "suite_api_key=one",
                    ],
                    "nested": {
                        "tool_registry_provider_sources": [
                            "suite_access_token=two",
                            "suite_api_key=one",
                        ],
                    },
                }
            )
        )

        self.assertEqual(
            payload["provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertEqual(
            payload["nested"]["tool_registry_provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertNotIn("api_key=one", json.dumps(payload, default=str))
        self.assertNotIn("access_token=two", json.dumps(payload, default=str))

    def test_registry_artifact_sanitizer_disambiguates_colliding_redacted_provider_source_aliases(
        self,
    ) -> None:
        registry_module = __import__(
            "app.services.tool_runtime_registry",
            fromlist=["_impl__sanitize_tool_registry_provider_source_fields_for_artifact"],
        )

        payload = registry_module._impl__sanitize_tool_registry_provider_source_fields_for_artifact(
            {
                "provider_sources": [
                    "suite_access_token=two",
                    "suite_api_key=one",
                ],
                "nested": {
                    "tool_registry_provider_sources": [
                        "suite_access_token=two",
                        "suite_api_key=one",
                    ],
                },
            }
        )

        self.assertEqual(
            payload["provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertEqual(
            payload["nested"]["tool_registry_provider_sources"],
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertNotIn("api_key=one", json.dumps(payload, default=str))
        self.assertNotIn("access_token=two", json.dumps(payload, default=str))

    def test_provider_sources_dict_sanitizer_preserves_colliding_redacted_aliases(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )

        payload = (
            tool_runtime_module._sanitize_tool_runtime_provider_sources_for_artifact(
                {
                    "suite_access_token=two": provider,
                    "suite_api_key=one": provider,
                }
            )
        )

        self.assertEqual(
            list(payload.keys()),
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertEqual(list(payload.values()), [provider, provider])
        self.assertNotIn("api_key=one", json.dumps(list(payload.keys()), default=str))
        self.assertNotIn(
            "access_token=two",
            json.dumps(list(payload.keys()), default=str),
        )

    def test_runtime_artifacts_to_dict_preserves_colliding_provider_source_alias_keys(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        diagnostics_runtime = tool_runtime_module.ToolRegistryDiagnosticsRuntimeArtifactsModel(
            summary=build_tool_registry_diagnostics_summary_model(diagnostics={}),
            trace_step=None,
            trace_event=None,
            audit_detail=None,
        )
        model = tool_runtime_module.ConfiguredToolRegistryProviderRuntimeArtifactsModel(
            provider=provider,
            provider_source_name="suite_api_key=one",
            provider_sources={
                "suite_access_token=two": provider,
                "suite_api_key=one": provider,
            },
            selected_source_diagnostics={},
            source_diagnostics={
                "suite_access_token=two": {
                    "skipped_registry_sources": ("suite_access_token=two",),
                    "missing_registry_sources": (),
                    "skipped_registry_files": (),
                    "missing_registry_files": (),
                    "skipped_registry_dirs": (),
                    "missing_registry_dirs": (),
                },
                "suite_api_key=one": {
                    "skipped_registry_sources": (),
                    "missing_registry_sources": ("suite_api_key=one",),
                    "skipped_registry_files": (),
                    "missing_registry_files": (),
                    "skipped_registry_dirs": (),
                    "missing_registry_dirs": (),
                },
            },
            diagnostics_runtime=diagnostics_runtime,
            audit_event=None,
        )

        payload = model.to_dict()

        self.assertEqual(
            list(payload["provider_sources"].keys()),
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertEqual(
            list(payload["source_diagnostics"].keys()),
            ["suite_[redacted]#1", "suite_[redacted]#2"],
        )
        self.assertEqual(
            payload["source_diagnostics"]["suite_[redacted]#1"][
                "skipped_registry_sources"
            ],
            ("suite_[redacted]",),
        )
        self.assertEqual(
            payload["source_diagnostics"]["suite_[redacted]#2"][
                "missing_registry_sources"
            ],
            ("suite_[redacted]",),
        )
        self.assertNotIn("api_key=one", json.dumps(payload, default=str))
        self.assertNotIn("access_token=two", json.dumps(payload, default=str))
