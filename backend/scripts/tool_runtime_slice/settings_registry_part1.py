from __future__ import annotations

from typing import get_args

from .context import *


class SettingsRegistryMixinPart1:
    def test_settings_summary_response_types_task_queue_diagnostics_contract(
        self,
    ) -> None:
        diagnostics_contract = getattr(
            settings_routes_module,
            "TaskQueueDiagnosticsSummary",
            None,
        )

        self.assertIsNotNone(diagnostics_contract)
        self.assertIs(
            SettingsSummaryResponse.model_fields["task_queue_diagnostics"].annotation,
            diagnostics_contract,
        )
        self.assertIs(
            settings_routes_module._build_task_queue_diagnostics.__annotations__.get(
                "return"
            ),
            diagnostics_contract,
        )

        required_keys = set(
            getattr(diagnostics_contract, "__required_keys__", frozenset())
        )
        for field_name in {
            "max_concurrent",
            "active_count",
            "waiting_count",
            "available_slots",
            "has_waiting_tasks",
            "saturated",
            "pressure_state",
            "max_concurrent_per_user",
            "max_concurrent_per_session",
            "poll_interval_sec",
            "per_user_limit_enabled",
            "per_session_limit_enabled",
            "fairness_limits_enabled",
            "waiting_policy",
            "capacity_aware_fifo_enabled",
        }:
            self.assertIn(field_name, required_keys)

        optional_keys = set(
            getattr(diagnostics_contract, "__optional_keys__", frozenset())
        )
        for field_name in {
            "current_user_active_count",
            "current_user_waiting_count",
            "current_user_available_slots",
            "current_user_limit_reached",
            "current_session_active_count",
            "current_session_waiting_count",
            "current_session_available_slots",
            "current_session_limit_reached",
        }:
            self.assertIn(field_name, optional_keys)
            self.assertNotIn(field_name, required_keys)

        annotations = getattr(diagnostics_contract, "__annotations__", {})
        self.assertEqual(
            set(get_args(annotations["pressure_state"])),
            {"idle", "active", "saturated", "scope_limited"},
        )
        self.assertEqual(
            set(get_args(annotations["waiting_policy"])),
            {"capacity_aware_oldest_eligible_fifo"},
        )

    def test_build_settings_summary_response_captures_registry_profile_source_and_enabled_tools(
        self,
    ) -> None:
        summary = _build_settings_summary_response(
            settings=StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile="planning_only",
                tool_registry_provider_source="suite_a",
            ),
            runtime_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_a": {
                            "profile": "planning_only",
                        },
                        "suite_b": {
                            "profile": "calculator_only",
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
            database_locator="postgresql://demo",
        )

        self.assertEqual(summary.mode, "remote")
        self.assertEqual(summary.provider, "openai")
        self.assertEqual(summary.model, "gpt-4.1-mini")
        self.assertEqual(summary.tool_registry_profile, "planning_only")
        self.assertEqual(summary.tool_registry_provider_source, "suite_a")
        self.assertEqual(summary.enabled_tool_names, ["task_plan"])
        self.assertEqual(summary.enabled_tool_labels, ["Task Planner"])
        self.assertEqual(
            summary.available_tool_registry_profiles,
            ["default", "planning_only", "retrieval_only", "calculator_only"],
        )
        self.assertEqual(
            summary.available_tool_registry_provider_sources,
            ["default", "suite_a", "suite_b"],
        )
        self.assertEqual(
            [
                (
                    detail.name,
                    tuple(detail.enabled_tool_labels),
                )
                for detail in summary.available_tool_registry_profile_details
            ],
            [
                ("default", ("Task Planner", "Knowledge Retrieval", "Calculator")),
                ("planning_only", ("Task Planner",)),
                ("retrieval_only", ("Knowledge Retrieval",)),
                ("calculator_only", ("Calculator",)),
            ],
        )
        calculator_profile_detail = next(
            detail
            for detail in summary.available_tool_registry_profile_details
            if detail.name == "calculator_only"
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    tool.label,
                    tool.kind,
                    tool.semantic_kind,
                    tuple(tool.effective_result_preview_keys),
                )
                for tool in calculator_profile_detail.tool_details
            ],
            [
                (
                    "calc_eval",
                    "Calculator",
                    "local_calculator",
                    "local_calculator",
                    ("expression", "result"),
                )
            ],
        )
        self.assertEqual(
            [
                (
                    detail.name,
                    detail.base_profile,
                    tuple(detail.enabled_tool_labels),
                )
                for detail in summary.available_tool_registry_provider_source_details
            ],
            [
                (
                    "default",
                    "default",
                    ("Task Planner",),
                ),
                (
                    "suite_a",
                    "planning_only",
                    ("Task Planner",),
                ),
                (
                    "suite_b",
                    "calculator_only",
                    ("Calculator",),
                ),
            ],
        )
        suite_b_detail = next(
            detail
            for detail in summary.available_tool_registry_provider_source_details
            if detail.name == "suite_b"
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    tool.label,
                    tool.kind,
                    tool.semantic_kind,
                    tuple(tool.effective_result_preview_keys),
                )
                for tool in suite_b_detail.tool_details
            ],
            [
                (
                    "calc_eval",
                    "Calculator",
                    "local_calculator",
                    "local_calculator",
                    ("expression", "result"),
                )
            ],
        )
        self.assertEqual(summary.database_locator, "postgresql://demo")

    def test_build_settings_summary_response_redacts_sensitive_provider_source_names(
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
                tool_registry_provider_source="suite_api_key=hidden",
            ),
            runtime_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_api_key=hidden": {
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
            "suite_[redacted]",
        )
        self.assertEqual(
            payload["available_tool_registry_provider_sources"],
            ["default", "suite_[redacted]"],
        )
        self.assertEqual(
            [
                detail["name"]
                for detail in payload["available_tool_registry_provider_source_details"]
            ],
            ["default", "suite_[redacted]"],
        )
        self.assertNotIn("api_key=hidden", json.dumps(payload, default=str))

    def test_apply_tool_registry_preview_to_validate_response_redacts_sensitive_provider_source_names(
        self,
    ) -> None:
        result = settings_routes_module._apply_tool_registry_preview_to_validate_response(
            result=SettingsValidateResponse(
                ok=True,
                mode="mock",
                provider="mock",
                model="mock-gpt",
                message="ok",
            ),
            effective_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="suite_api_key=hidden",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_api_key=hidden": {
                            "profile": "planning_only",
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        payload = result.model_dump()

        self.assertEqual(
            payload["tool_registry_provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            [
                detail["name"]
                for detail in payload["available_tool_registry_provider_source_details"]
            ],
            ["default", "suite_[redacted]"],
        )
        self.assertNotIn("api_key=hidden", json.dumps(payload, default=str))

    def test_validate_settings_accepts_unique_redacted_provider_source_alias(
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
                        "suite_api_key=hidden": {
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
                    tool_registry_provider_source="suite_[redacted]",
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
        self.assertEqual(payload["tool_registry_provider_source"], "suite_[redacted]")
        self.assertEqual(
            [
                detail["name"]
                for detail in payload["available_tool_registry_provider_source_details"]
            ],
            ["default", "suite_[redacted]"],
        )
        self.assertEqual(
            audit_details[-1]["tool_registry_provider_source"],
            "suite_api_key=hidden",
        )
        self.assertNotIn("api_key=hidden", json.dumps(payload, default=str))

    def test_update_settings_saves_unique_redacted_provider_source_alias_as_raw_source(
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
                        "suite_api_key=hidden": {
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
                    tool_registry_provider_source="suite_[redacted]",
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
            "suite_api_key=hidden",
        )
        self.assertEqual(result.tool_registry_provider_source, "suite_api_key=hidden")

    def test_build_settings_summary_response_exposes_task_queue_fairness_diagnostics(
        self,
    ) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            active_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="settings-active-task",
                max_concurrent=8,
                user_id="settings-user",
                session_id="settings-session-a",
                max_concurrent_per_user=1,
            )
            self.assertIsNotNone(active_slot)
            waiting_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="settings-waiting-task",
                max_concurrent=8,
                user_id="settings-user",
                session_id="settings-session-b",
                max_concurrent_per_user=1,
            )
            self.assertIsNone(waiting_slot)

            summary = _build_settings_summary_response(
                settings=StoredSettings(
                    mode="mock",
                    provider="mock",
                    model="mock-gpt",
                    base_url=None,
                    api_key=None,
                    tool_registry_profile="default",
                    tool_registry_provider_source="default",
                ),
                runtime_settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="default",
                    tool_registry_provider_sources_json=None,
                    task_queue_max_concurrent=8,
                    task_queue_max_concurrent_per_user=1,
                    task_queue_max_concurrent_per_session=3,
                    task_queue_poll_interval_sec=0.15,
                ),
                database_locator="postgresql://demo",
                current_user_id="settings-user",
                current_session_id="settings-session-a",
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

        self.assertEqual(
            summary.task_queue_diagnostics,
            {
                "max_concurrent": 8,
                "active_count": 1,
                "waiting_count": 1,
                "available_slots": 7,
                "current_user_active_count": 1,
                "current_user_waiting_count": 1,
                "current_user_available_slots": 0,
                "current_user_limit_reached": True,
                "current_session_active_count": 1,
                "current_session_waiting_count": 0,
                "current_session_available_slots": 2,
                "current_session_limit_reached": False,
                "has_waiting_tasks": True,
                "saturated": False,
                "pressure_state": "scope_limited",
                "max_concurrent_per_user": 1,
                "max_concurrent_per_session": 3,
                "poll_interval_sec": 0.15,
                "per_user_limit_enabled": True,
                "per_session_limit_enabled": True,
                "fairness_limits_enabled": True,
                "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                "capacity_aware_fifo_enabled": True,
            },
        )

    def test_build_settings_summary_response_caps_current_user_available_slots_by_global_capacity(
        self,
    ) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            current_user_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="settings-current-user-active",
                max_concurrent=2,
                user_id="settings-user",
                session_id="settings-session-a",
                max_concurrent_per_user=3,
            )
            self.assertIsNotNone(current_user_slot)
            other_user_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="settings-other-user-active",
                max_concurrent=2,
                user_id="settings-other-user",
                session_id="settings-session-b",
                max_concurrent_per_user=3,
            )
            self.assertIsNotNone(other_user_slot)

            summary = _build_settings_summary_response(
                settings=StoredSettings(
                    mode="mock",
                    provider="mock",
                    model="mock-gpt",
                    base_url=None,
                    api_key=None,
                    tool_registry_profile="default",
                    tool_registry_provider_source="default",
                ),
                runtime_settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="default",
                    tool_registry_provider_sources_json=None,
                    task_queue_max_concurrent=2,
                    task_queue_max_concurrent_per_user=3,
                    task_queue_max_concurrent_per_session=0,
                    task_queue_poll_interval_sec=0.15,
                ),
                database_locator="postgresql://demo",
                current_user_id="settings-user",
                current_session_id="settings-session-a",
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

        self.assertEqual(summary.task_queue_diagnostics["available_slots"], 0)
        self.assertEqual(
            summary.task_queue_diagnostics["current_user_available_slots"],
            0,
        )
        self.assertFalse(
            summary.task_queue_diagnostics["current_user_limit_reached"],
        )
        self.assertEqual(
            summary.task_queue_diagnostics["current_session_available_slots"],
            0,
        )
        self.assertFalse(
            summary.task_queue_diagnostics["current_session_limit_reached"],
        )

    def test_build_settings_summary_response_caps_current_session_available_slots_by_session_limit(
        self,
    ) -> None:
        task_queue_module = __import__(
            "app.services.task_queue_service",
            fromlist=[
                "reset_task_queue_state_for_tests",
                "try_acquire_task_execution_slot",
            ],
        )
        task_queue_module.reset_task_queue_state_for_tests()
        try:
            active_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="settings-session-active",
                max_concurrent=8,
                user_id="settings-user-a",
                session_id="settings-session-a",
                max_concurrent_per_session=1,
            )
            self.assertIsNotNone(active_slot)
            waiting_slot = task_queue_module.try_acquire_task_execution_slot(
                task_id="settings-session-waiting",
                max_concurrent=8,
                user_id="settings-user-b",
                session_id="settings-session-a",
                max_concurrent_per_session=1,
            )
            self.assertIsNone(waiting_slot)

            summary = _build_settings_summary_response(
                settings=StoredSettings(
                    mode="mock",
                    provider="mock",
                    model="mock-gpt",
                    base_url=None,
                    api_key=None,
                    tool_registry_profile="default",
                    tool_registry_provider_source="default",
                ),
                runtime_settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="default",
                    tool_registry_provider_sources_json=None,
                    task_queue_max_concurrent=8,
                    task_queue_max_concurrent_per_user=0,
                    task_queue_max_concurrent_per_session=1,
                    task_queue_poll_interval_sec=0.15,
                ),
                database_locator="postgresql://demo",
                current_user_id="settings-user-a",
                current_session_id="settings-session-a",
            )
        finally:
            task_queue_module.reset_task_queue_state_for_tests()

        self.assertEqual(
            summary.task_queue_diagnostics["current_session_active_count"],
            1,
        )
        self.assertEqual(
            summary.task_queue_diagnostics["current_session_waiting_count"],
            1,
        )
        self.assertEqual(
            summary.task_queue_diagnostics["current_session_available_slots"],
            0,
        )
        self.assertTrue(
            summary.task_queue_diagnostics["current_session_limit_reached"],
        )

    def test_get_settings_summary_passes_owned_session_id_to_queue_diagnostics(
        self,
    ) -> None:
        original_get_stored_settings = settings_routes_module.get_stored_settings
        original_get_session = settings_routes_module.get_session
        original_build_settings_summary_response = (
            settings_routes_module._build_settings_summary_response
        )
        captured_kwargs: dict[str, object] = {}
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
            settings_routes_module.get_session = lambda session_id, user_id: (
                {"id": session_id, "user_id": user_id}
                if session_id == "settings-session-owned" and user_id == "user-1"
                else None
            )
            settings_routes_module._build_settings_summary_response = (
                lambda **kwargs: captured_kwargs.update(kwargs) or kwargs["settings"]
            )

            settings_routes_module.get_settings_summary(
                session_id=" settings-session-owned ",
                current_user={"id": "user-1"},
            )
        finally:
            settings_routes_module.get_stored_settings = original_get_stored_settings
            settings_routes_module.get_session = original_get_session
            settings_routes_module._build_settings_summary_response = (
                original_build_settings_summary_response
            )

        self.assertEqual(
            captured_kwargs["current_session_id"],
            "settings-session-owned",
        )

    def test_get_settings_summary_omits_unowned_session_id_from_queue_diagnostics(
        self,
    ) -> None:
        original_get_stored_settings = settings_routes_module.get_stored_settings
        original_get_session = settings_routes_module.get_session
        original_build_settings_summary_response = (
            settings_routes_module._build_settings_summary_response
        )
        captured_kwargs: dict[str, object] = {}
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
            settings_routes_module.get_session = lambda _session_id, _user_id: None
            settings_routes_module._build_settings_summary_response = (
                lambda **kwargs: captured_kwargs.update(kwargs) or kwargs["settings"]
            )

            settings_routes_module.get_settings_summary(
                session_id="settings-session-other",
                current_user={"id": "user-1"},
            )
        finally:
            settings_routes_module.get_stored_settings = original_get_stored_settings
            settings_routes_module.get_session = original_get_session
            settings_routes_module._build_settings_summary_response = (
                original_build_settings_summary_response
            )

        self.assertIsNone(captured_kwargs["current_session_id"])

    def test_build_settings_summary_response_marks_default_task_queue_fairness_limits_disabled(
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
                tool_registry_provider_source="default",
            ),
            runtime_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
                tool_registry_provider_sources_json=None,
                task_queue_max_concurrent=32,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.25,
            ),
            database_locator="postgresql://demo",
        )

        self.assertEqual(
            summary.task_queue_diagnostics,
            {
                "max_concurrent": 32,
                "active_count": 0,
                "waiting_count": 0,
                "available_slots": 32,
                "has_waiting_tasks": False,
                "saturated": False,
                "pressure_state": "idle",
                "max_concurrent_per_user": 0,
                "max_concurrent_per_session": 0,
                "poll_interval_sec": 0.25,
                "per_user_limit_enabled": False,
                "per_session_limit_enabled": False,
                "fairness_limits_enabled": False,
                "waiting_policy": "capacity_aware_oldest_eligible_fifo",
                "capacity_aware_fifo_enabled": True,
            },
        )

    def test_build_settings_summary_response_includes_productized_tool_details_for_real_provider_source_tools(
        self,
    ) -> None:
        summary = _build_settings_summary_response(
            settings=StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile="default",
                tool_registry_provider_source="analytics_suite",
            ),
            runtime_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
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
                                        "kind": "http_json",
                                        "url": "https://provider.example/search",
                                    },
                                    "result_preview_keys": [],
                                    "supports_result_preview": True,
                                    "default_timeout_ms": 21_000,
                                    "retryable_by_default": False,
                                },
                                "provider_math": {
                                    "template": "calc_eval",
                                    "label": "Provider Math",
                                    "kind": "provider_calc",
                                    "result_preview_keys": [],
                                    "supports_result_preview": True,
                                    "default_timeout_ms": 13_000,
                                },
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
            database_locator="postgresql://demo",
        )

        analytics_detail = next(
            detail
            for detail in summary.available_tool_registry_provider_source_details
            if detail.name == "analytics_suite"
        )
        self.assertEqual(
            [tool.name for tool in analytics_detail.tool_details],
            ["provider_math", "provider_search"],
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    tool.label,
                    tool.kind,
                    tool.semantic_kind,
                    tool.retryable_by_default,
                    tool.default_timeout_ms,
                    tool.requires_user_context,
                    tool.supports_result_preview,
                    getattr(tool, "execution_kind", None),
                    getattr(tool, "execution_summary", None),
                    tuple(tool.effective_result_preview_keys),
                )
                for tool in analytics_detail.tool_details
            ],
            [
                (
                    "provider_math",
                    "Provider Math",
                    "provider_calc",
                    "local_calculator",
                    True,
                    13_000,
                    True,
                    True,
                    None,
                    None,
                    ("expression", "result"),
                ),
                (
                    "provider_search",
                    "Provider Search",
                    "provider_retrieval",
                    "knowledge_retrieval",
                    False,
                    21_000,
                    True,
                    True,
                    "http_json",
                    {
                        "method": "GET",
                        "url_origin": "https://provider.example",
                        "url_path": "/search",
                    },
                    ("hit_count", "knowledge_base_id"),
                ),
            ],
        )

    def test_build_settings_summary_response_includes_per_tool_invalid_execution_diagnostics_for_real_provider_source_tools(
        self,
    ) -> None:
        summary = _build_settings_summary_response(
            settings=StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile="default",
                tool_registry_provider_source="analytics_suite",
            ),
            runtime_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
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
                                        "kind": "http_json",
                                        "url": "https://provider.example/search",
                                        "response_path": "   ",
                                    },
                                    "result_preview_keys": [],
                                    "supports_result_preview": True,
                                    "default_timeout_ms": 21_000,
                                    "retryable_by_default": False,
                                },
                                "provider_math": {
                                    "template": "calc_eval",
                                    "label": "Provider Math",
                                    "kind": "provider_calc",
                                    "result_preview_keys": [],
                                    "supports_result_preview": True,
                                    "default_timeout_ms": 13_000,
                                },
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
            database_locator="postgresql://demo",
        )

        analytics_detail = next(
            detail
            for detail in summary.available_tool_registry_provider_source_details
            if detail.name == "analytics_suite"
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    tuple(getattr(tool, "execution_diagnostics", ()) or ()),
                )
                for tool in analytics_detail.tool_details
            ],
            [
                ("provider_math", ()),
                (
                    "provider_search",
                    (
                        "http_json execution response_path must be a non-empty string when provided",
                    ),
                ),
            ],
        )

    def test_build_settings_summary_response_uses_runtime_semantic_override_for_real_provider_source_tools(
        self,
    ) -> None:
        summary = _build_settings_summary_response(
            settings=StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile="default",
                tool_registry_provider_source="analytics_suite",
            ),
            runtime_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
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
                                    "runtime_semantic_kind": "provider_search",
                                    "result_preview_keys": ["documents_total"],
                                    "supports_result_preview": True,
                                },
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
            database_locator="postgresql://demo",
        )

        analytics_detail = next(
            detail
            for detail in summary.available_tool_registry_provider_source_details
            if detail.name == "analytics_suite"
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    tool.kind,
                    tool.semantic_kind,
                    getattr(tool, "semantic_family", None),
                    tuple(tool.effective_result_preview_keys),
                )
                for tool in analytics_detail.tool_details
            ],
            [
                (
                    "provider_search",
                    "provider_retrieval",
                    "provider_search",
                    "knowledge_retrieval",
                    ("documents_total",),
                )
            ],
        )

    def test_build_settings_summary_response_includes_result_output_keys_for_real_provider_source_tools(
        self,
    ) -> None:
        summary = _build_settings_summary_response(
            settings=StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile="default",
                tool_registry_provider_source="analytics_suite",
            ),
            runtime_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
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
                                    "result_preview_keys": ["documents_total"],
                                    "result_output_keys": ["documents_total"],
                                    "runtime_semantic_kind": "provider_search",
                                    "supports_result_preview": True,
                                },
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
            database_locator="postgresql://demo",
        )

        analytics_detail = next(
            detail
            for detail in summary.available_tool_registry_provider_source_details
            if detail.name == "analytics_suite"
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    getattr(tool, "semantic_family", None),
                    tuple(tool.effective_result_preview_keys),
                    tuple(tool.effective_result_output_keys),
                )
                for tool in analytics_detail.tool_details
            ],
            [
                (
                    "provider_search",
                    "knowledge_retrieval",
                    ("documents_total",),
                    ("documents_total",),
                )
            ],
        )

    def test_build_settings_summary_response_falls_back_result_output_keys_to_preview_keys_for_runtime_override_real_tools(
        self,
    ) -> None:
        summary = _build_settings_summary_response(
            settings=StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile="default",
                tool_registry_provider_source="analytics_suite",
            ),
            runtime_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
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
                                    "result_preview_keys": ["documents_total"],
                                    "runtime_semantic_kind": "provider_search",
                                    "supports_result_preview": True,
                                },
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
            database_locator="postgresql://demo",
        )

        analytics_detail = next(
            detail
            for detail in summary.available_tool_registry_provider_source_details
            if detail.name == "analytics_suite"
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    getattr(tool, "semantic_family", None),
                    tuple(tool.effective_result_preview_keys),
                    tuple(tool.effective_result_output_keys),
                )
                for tool in analytics_detail.tool_details
            ],
            [
                (
                    "provider_search",
                    "knowledge_retrieval",
                    ("documents_total",),
                    ("documents_total",),
                )
            ],
        )

    def test_build_settings_summary_response_infers_preview_and_output_keys_from_semantic_family_for_runtime_override_real_tools(
        self,
    ) -> None:
        summary = _build_settings_summary_response(
            settings=StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile="default",
                tool_registry_provider_source="analytics_suite",
            ),
            runtime_settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
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
                                    "runtime_semantic_kind": "provider_search",
                                    "supports_result_preview": True,
                                },
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
            database_locator="postgresql://demo",
        )

        analytics_detail = next(
            detail
            for detail in summary.available_tool_registry_provider_source_details
            if detail.name == "analytics_suite"
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    getattr(tool, "semantic_family", None),
                    tuple(tool.effective_result_preview_keys),
                    tuple(tool.effective_result_output_keys),
                )
                for tool in analytics_detail.tool_details
            ],
            [
                (
                    "provider_search",
                    "knowledge_retrieval",
                    ("hit_count", "knowledge_base_id"),
                    ("hit_count", "knowledge_base_id"),
                )
            ],
        )

    def test_get_stored_settings_merges_runtime_registry_source_specs_for_runtime(
        self,
    ) -> None:
        row = {
            "mode": "mock",
            "provider": "mock",
            "model": "mock-gpt",
            "base_url": None,
            "api_key_enc": None,
            "tool_registry_profile": "planning_only",
            "tool_registry_provider_source": "planning_suite",
        }

        class FakeConnection:
            def execute(self, *_args, **_kwargs):
                return self

            def fetchone(self):
                return row

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, *_args):
                return False

        original_get_settings = settings_service_module.get_settings
        original_get_db_connection = settings_service_module.get_db_connection
        try:
            settings_service_module.get_settings = lambda: SimpleNamespace(
                mode="mock",
                provider="mock",
                model_name="mock-gpt",
                base_url=None,
                api_key=None,
                tool_registry_profile="default",
                tool_registry_provider_source="default",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "profile": "planning_only",
                            "overrides": {
                                "task_plan": {
                                    "label": "Task Planner Suite",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
                tool_registry_loaders_json=None,
                tool_registry_loader_factories_json=None,
                tool_registry_providers_json=None,
                tool_registry_provider_factories_json=None,
            )
            settings_service_module.get_db_connection = lambda: FakeContextManager()

            settings = settings_service_module.get_stored_settings("user-1")
        finally:
            settings_service_module.get_settings = original_get_settings
            settings_service_module.get_db_connection = original_get_db_connection

        self.assertEqual(settings.tool_registry_profile, "planning_only")
        self.assertEqual(settings.tool_registry_provider_source, "planning_suite")
        self.assertIsNotNone(settings.tool_registry_provider_sources_json)
        provider = get_configured_tool_registry_provider(settings=settings)
        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("task_plan",),
        )
        self.assertEqual(
            provider.load_tool_registry()["task_plan"].label,
            "Task Planner Suite",
        )

    def test_get_stored_settings_promotes_runtime_defaults_to_remote_when_provider_ready(
        self,
    ) -> None:
        class FakeConnection:
            def execute(self, *_args, **_kwargs):
                return self

            def fetchone(self):
                return None

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, *_args):
                return False

        original_get_settings = settings_service_module.get_settings
        original_get_db_connection = settings_service_module.get_db_connection
        try:
            settings_service_module.get_settings = lambda: SimpleNamespace(
                mode="mock",
                provider="openai",
                model_name="gpt-4.1-mini",
                base_url="https://api.openai.com/v1",
                api_key="sk-demo",
                tool_registry_profile="default",
                tool_registry_provider_source="planning_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "profile": "planning_only",
                            "overrides": {
                                "task_plan": {
                                    "label": "Task Planner Suite",
                                },
                            },
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
                tool_registry_loaders_json=None,
                tool_registry_loader_factories_json=None,
                tool_registry_providers_json=None,
                tool_registry_provider_factories_json=None,
            )
            settings_service_module.get_db_connection = lambda: FakeContextManager()

            settings = settings_service_module.get_stored_settings("user-1")
        finally:
            settings_service_module.get_settings = original_get_settings
            settings_service_module.get_db_connection = original_get_db_connection

        self.assertEqual(settings.mode, "remote")
        self.assertEqual(settings.provider, "openai")
        self.assertEqual(settings.model, "gpt-4.1-mini")
        self.assertEqual(settings.base_url, "https://api.openai.com/v1")
        self.assertEqual(settings.api_key, "sk-demo")
        self.assertEqual(settings.tool_registry_provider_source, "planning_suite")

    def test_get_stored_settings_keeps_canonical_mock_defaults_when_runtime_provider_is_incomplete(
        self,
    ) -> None:
        class FakeConnection:
            def execute(self, *_args, **_kwargs):
                return self

            def fetchone(self):
                return None

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, *_args):
                return False

        original_get_settings = settings_service_module.get_settings
        original_get_db_connection = settings_service_module.get_db_connection
        try:
            settings_service_module.get_settings = lambda: SimpleNamespace(
                mode="mock",
                provider="openai",
                model_name="gpt-4.1-mini",
                base_url="https://api.openai.com/v1",
                api_key=None,
                tool_registry_profile="default",
                tool_registry_provider_source="default",
                tool_registry_provider_sources_json=None,
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
                tool_registry_loaders_json=None,
                tool_registry_loader_factories_json=None,
                tool_registry_providers_json=None,
                tool_registry_provider_factories_json=None,
            )
            settings_service_module.get_db_connection = lambda: FakeContextManager()

            settings = settings_service_module.get_stored_settings("user-1")
        finally:
            settings_service_module.get_settings = original_get_settings
            settings_service_module.get_db_connection = original_get_db_connection

        self.assertEqual(settings.mode, "mock")
        self.assertEqual(settings.provider, "mock")
        self.assertEqual(settings.model, "mock-gpt")
        self.assertIsNone(settings.base_url)
        self.assertIsNone(settings.api_key)

    def test_get_stored_settings_keeps_runtime_remote_connection_defaults_for_existing_remote_row_with_missing_fields(
        self,
    ) -> None:
        row = {
            "mode": "remote",
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "base_url": None,
            "api_key_enc": None,
            "tool_registry_profile": "default",
            "tool_registry_provider_source": "default",
        }

        class FakeConnection:
            def execute(self, *_args, **_kwargs):
                return self

            def fetchone(self):
                return row

        class FakeContextManager:
            def __enter__(self):
                return FakeConnection()

            def __exit__(self, *_args):
                return False

        original_get_settings = settings_service_module.get_settings
        original_get_db_connection = settings_service_module.get_db_connection
        try:
            settings_service_module.get_settings = lambda: SimpleNamespace(
                mode="mock",
                provider="openai",
                model_name="gpt-4.1-mini",
                base_url="https://api.openai.com/v1",
                api_key="sk-runtime",
                tool_registry_profile="default",
                tool_registry_provider_source="default",
                tool_registry_provider_sources_json=None,
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
                tool_registry_loaders_json=None,
                tool_registry_loader_factories_json=None,
                tool_registry_providers_json=None,
                tool_registry_provider_factories_json=None,
            )
            settings_service_module.get_db_connection = lambda: FakeContextManager()

            settings = settings_service_module.get_stored_settings("user-1")
        finally:
            settings_service_module.get_settings = original_get_settings
            settings_service_module.get_db_connection = original_get_db_connection

        self.assertEqual(settings.mode, "remote")
        self.assertEqual(settings.provider, "openai")
        self.assertEqual(settings.model, "gpt-4.1-mini")
        self.assertEqual(settings.base_url, "https://api.openai.com/v1")
        self.assertEqual(settings.api_key, "sk-runtime")

    def test_backend_e2e_scripts_bootstrap_backend_root_before_imports(self) -> None:
        repo_root = ROOT.parent
        scripts = (
            repo_root / "backend" / "scripts" / "e2e_main_path.py",
            repo_root / "backend" / "scripts" / "e2e_export_consistency.py",
        )

        for script_path in scripts:
            with self.subTest(script=script_path.name):
                result = subprocess.run(
                    [sys.executable, str(script_path), "--help"],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    msg=(
                        f"{script_path.name} should import cleanly when executed from repo root.\n"
                        f"stdout:\n{result.stdout}\n"
                        f"stderr:\n{result.stderr}"
                    ),
                )

    def test_backend_e2e_scripts_avoid_pep604_isinstance_for_system_python(self) -> None:
        repo_root = ROOT.parent
        scripts = (
            repo_root / "backend" / "scripts" / "e2e_main_path.py",
        )

        for script_path in scripts:
            tree = ast.parse(script_path.read_text(encoding="utf-8"))
            bad_lines = [
                node.lineno
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "isinstance"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.BinOp)
                and isinstance(node.args[1].op, ast.BitOr)
            ]
            with self.subTest(script=script_path.name):
                self.assertEqual(
                    bad_lines,
                    [],
                    msg=(
                        f"{script_path.name} must run under the system python3 used by "
                        f"scripts/ci_run_backend_e2e.sh; avoid PEP 604 unions inside "
                        f"isinstance(...): {bad_lines}"
                    ),
                )

    def test_apply_tool_registry_preview_to_validate_response_uses_selected_source_override_label_for_calculator(
        self,
    ) -> None:
        response = _apply_tool_registry_preview_to_validate_response(
            result=SettingsValidateResponse(
                ok=True,
                mode="mock",
                provider="mock",
                model="mock-gpt",
                message="ok",
            ),
            effective_settings=SimpleNamespace(
                tool_registry_profile="calculator_only",
                tool_registry_provider_source="calculator_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "calculator_suite": {
                            "provider": "default",
                            "profile": "calculator_only",
                            "overrides": {
                                "calc_eval": {
                                    "label": "Calculator Suite",
                                },
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
        )

        self.assertEqual(response.tool_registry_profile, "calculator_only")
        self.assertEqual(response.tool_registry_provider_source, "calculator_suite")
        self.assertEqual(response.enabled_tool_names, ["calc_eval"])
        self.assertEqual(response.enabled_tool_labels, ["Calculator Suite"])

    def test_build_tool_plan_artifacts_uses_selected_source_override_label_for_calculator(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_provider_source="calculator_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "calculator_suite": {
                            "provider": "default",
                            "profile": "calculator_only",
                            "overrides": {
                                "calc_eval": {
                                    "label": "Calculator Suite",
                                },
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            )
        )

        artifacts = build_tool_plan_artifacts(
            "Please calculate [calc:1+2]",
            registry_provider=registry_provider,
        )

        self.assertEqual(artifacts.allowed_tool_names, ("calc_eval",))
        self.assertEqual(artifacts.allowed_tool_labels, ("Calculator Suite",))

    def test_apply_tool_registry_preview_to_validate_response_uses_effective_settings(
        self,
    ) -> None:
        response = _apply_tool_registry_preview_to_validate_response(
            result=SettingsValidateResponse(
                ok=True,
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                message="ok",
            ),
            effective_settings=SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_provider_source="suite_a",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_a": {
                            "profile": "planning_only",
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
        )

        self.assertEqual(response.tool_registry_profile, "planning_only")
        self.assertEqual(response.tool_registry_provider_source, "suite_a")
        self.assertEqual(response.enabled_tool_names, ["task_plan"])
        self.assertEqual(response.enabled_tool_labels, ["Task Planner"])
        self.assertEqual(
            [
                (detail.name, tuple(detail.enabled_tool_labels))
                for detail in response.available_tool_registry_profile_details
            ],
            [
                ("default", ("Task Planner", "Knowledge Retrieval", "Calculator")),
                ("planning_only", ("Task Planner",)),
                ("retrieval_only", ("Knowledge Retrieval",)),
                ("calculator_only", ("Calculator",)),
            ],
        )
        retrieval_profile_detail = next(
            detail
            for detail in response.available_tool_registry_profile_details
            if detail.name == "retrieval_only"
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    tool.label,
                    tool.kind,
                    tool.semantic_kind,
                    tuple(tool.effective_result_preview_keys),
                )
                for tool in retrieval_profile_detail.tool_details
            ],
            [
                (
                    "task_retrieve",
                    "Knowledge Retrieval",
                    "knowledge_retrieval",
                    "knowledge_retrieval",
                    ("hit_count", "knowledge_base_id"),
                )
            ],
        )
        self.assertEqual(
            [
                (
                    detail.name,
                    detail.base_profile,
                    tuple(detail.enabled_tool_labels),
                )
                for detail in response.available_tool_registry_provider_source_details
            ],
            [
                ("default", "default", ("Task Planner",)),
                ("suite_a", "planning_only", ("Task Planner",)),
            ],
        )
        suite_a_detail = next(
            detail
            for detail in response.available_tool_registry_provider_source_details
            if detail.name == "suite_a"
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    tool.label,
                    tool.kind,
                    tool.semantic_kind,
                    tuple(tool.effective_result_preview_keys),
                )
                for tool in suite_a_detail.tool_details
            ],
            [
                (
                    "task_plan",
                    "Task Planner",
                    "task_planner",
                    "task_planner",
                    ("plan", "steps"),
                )
            ],
        )

    def test_apply_tool_registry_preview_to_validate_response_includes_productized_tool_details_for_real_provider_source_tools(
        self,
    ) -> None:
        response = _apply_tool_registry_preview_to_validate_response(
            result=SettingsValidateResponse(
                ok=True,
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                message="ok",
            ),
            effective_settings=SimpleNamespace(
                tool_registry_profile="default",
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
                                        "kind": "http_json",
                                        "url": "https://provider.example/search",
                                    },
                                    "result_preview_keys": [],
                                    "supports_result_preview": True,
                                    "default_timeout_ms": 21_000,
                                    "retryable_by_default": False,
                                },
                                "provider_math": {
                                    "template": "calc_eval",
                                    "label": "Provider Math",
                                    "kind": "provider_calc",
                                    "result_preview_keys": [],
                                    "supports_result_preview": True,
                                    "default_timeout_ms": 13_000,
                                },
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
        )

        analytics_detail = next(
            detail
            for detail in response.available_tool_registry_provider_source_details
            if detail.name == "analytics_suite"
        )
        self.assertEqual(
            [tool.name for tool in analytics_detail.tool_details],
            ["provider_math", "provider_search"],
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    tool.semantic_kind,
                    getattr(tool, "execution_kind", None),
                    getattr(tool, "execution_summary", None),
                    tuple(tool.effective_result_preview_keys),
                )
                for tool in analytics_detail.tool_details
            ],
            [
                ("provider_math", "local_calculator", None, None, ("expression", "result")),
                (
                    "provider_search",
                    "knowledge_retrieval",
                    "http_json",
                    {
                        "method": "GET",
                        "url_origin": "https://provider.example",
                        "url_path": "/search",
                    },
                    ("hit_count", "knowledge_base_id"),
                ),
            ],
        )

    def test_apply_tool_registry_preview_to_validate_response_includes_result_output_keys_for_real_provider_source_tools(
        self,
    ) -> None:
        response = _apply_tool_registry_preview_to_validate_response(
            result=SettingsValidateResponse(
                ok=True,
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                message="ok",
            ),
            effective_settings=SimpleNamespace(
                tool_registry_profile="default",
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
                                    "result_preview_keys": ["documents_total"],
                                    "result_output_keys": ["documents_total"],
                                    "runtime_semantic_kind": "provider_search",
                                    "supports_result_preview": True,
                                },
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
        )

        analytics_detail = next(
            detail
            for detail in response.available_tool_registry_provider_source_details
            if detail.name == "analytics_suite"
        )
        self.assertEqual(
            [
                (
                    tool.name,
                    getattr(tool, "semantic_family", None),
                    tuple(tool.effective_result_preview_keys),
                    tuple(tool.effective_result_output_keys),
                )
                for tool in analytics_detail.tool_details
            ],
            [
                (
                    "provider_search",
                    "knowledge_retrieval",
                    ("documents_total",),
                    ("documents_total",),
                )
            ],
        )
