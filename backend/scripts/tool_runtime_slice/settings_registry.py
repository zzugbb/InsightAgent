from __future__ import annotations

from .context import *


class SettingsRegistryMixin:
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

    def test_apply_tool_registry_preview_to_validate_response_includes_file_backed_real_calc_tool_details(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "validate-calc-registry.json"
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
                                    "url": "https://provider.example/${tool_registry_profile}/calc",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "expression": "$expression",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "expression": "$.expression",
                                        "result": "$.value",
                                        "request_id": "$.request_id",
                                    },
                                },
                                "result_preview_keys": ["expression", "result"],
                                "result_output_keys": [
                                    "expression",
                                    "result",
                                    "request_id",
                                ],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
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
                ),
            )

        calculator_detail = next(
            detail
            for detail in response.available_tool_registry_provider_source_details
            if detail.name == "calculator_suite"
        )
        provider_math = next(
            tool for tool in calculator_detail.tool_details if tool.name == "provider_math"
        )
        self.assertEqual(calculator_detail.base_profile, "calculator_only")
        self.assertEqual(provider_math.execution_kind, "http_json")
        self.assertEqual(provider_math.semantic_kind, "local_calculator")
        self.assertEqual(
            provider_math.execution_summary,
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/calculator_only/calc",
                "header_count": 2,
                "query_param_count": 2,
                "json_body_field_count": 3,
                "response_path": "$.data",
                "result_field_names": ["expression", "result", "request_id"],
            },
        )
        self.assertEqual(
            tuple(provider_math.effective_result_preview_keys),
            ("expression", "result"),
        )
        self.assertEqual(
            tuple(provider_math.effective_result_output_keys),
            ("expression", "result", "request_id"),
        )

    def test_apply_tool_registry_preview_to_validate_response_falls_back_result_output_keys_to_preview_keys_for_runtime_override_real_tools(
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

    def test_apply_tool_registry_preview_to_validate_response_infers_preview_and_output_keys_from_semantic_family_for_runtime_override_real_tools(
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
                    ("hit_count", "knowledge_base_id"),
                    ("hit_count", "knowledge_base_id"),
                )
            ],
        )

    def test_apply_tool_registry_preview_to_validate_response_reuses_shared_tool_registry_options_bundle(
        self,
    ) -> None:
        original_build_tool_registry_options_bundle = getattr(
            settings_routes_module,
            "_build_tool_registry_options_bundle",
            None,
        )
        try:
            def fake_build_tool_registry_options_bundle(*, effective_settings):
                return {
                    "available_tool_registry_profiles": ["default", "planning_only"],
                    "available_tool_registry_profile_details": [
                        settings_routes_module.ToolRegistryProfileOptionResponse(
                            name="default",
                            enabled_tool_names=["task_plan"],
                            enabled_tool_labels=["Task Planner"],
                        )
                    ],
                    "available_tool_registry_provider_sources": ["default", "suite_a"],
                    "available_tool_registry_provider_source_details": [
                        settings_routes_module.ToolRegistryProviderSourceOptionResponse(
                            name="default",
                            base_profile="default",
                            enabled_tool_names=["task_plan"],
                            enabled_tool_labels=["Task Planner"],
                        )
                    ],
                }

            settings_routes_module._build_tool_registry_options_bundle = (
                fake_build_tool_registry_options_bundle
            )
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
                ),
            )
        finally:
            if original_build_tool_registry_options_bundle is None:
                delattr(settings_routes_module, "_build_tool_registry_options_bundle")
            else:
                settings_routes_module._build_tool_registry_options_bundle = (
                    original_build_tool_registry_options_bundle
                )

        self.assertEqual(
            [detail.name for detail in response.available_tool_registry_profile_details],
            ["default"],
        )
        self.assertEqual(
            [
                detail.name
                for detail in response.available_tool_registry_provider_source_details
            ],
            ["default"],
        )

    def test_apply_tool_registry_preview_to_validate_response_validates_raw_option_detail_dicts(
        self,
    ) -> None:
        original_build_tool_registry_options_bundle = getattr(
            settings_routes_module,
            "_build_tool_registry_options_bundle",
            None,
        )
        try:
            def fake_build_tool_registry_options_bundle(*, effective_settings):
                return {
                    "available_tool_registry_profiles": ["default"],
                    "available_tool_registry_profile_details": [
                        {
                            "name": "default",
                            "enabled_tool_names": ["task_plan"],
                            "enabled_tool_labels": ["Task Planner"],
                        }
                    ],
                    "available_tool_registry_provider_sources": ["default"],
                    "available_tool_registry_provider_source_details": [
                        {
                            "name": "default",
                            "base_profile": "default",
                            "enabled_tool_names": ["task_plan"],
                            "enabled_tool_labels": ["Task Planner"],
                        }
                    ],
                }

            settings_routes_module._build_tool_registry_options_bundle = (
                fake_build_tool_registry_options_bundle
            )
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
                    tool_registry_provider_source="default",
                ),
            )
        finally:
            if original_build_tool_registry_options_bundle is None:
                delattr(settings_routes_module, "_build_tool_registry_options_bundle")
            else:
                settings_routes_module._build_tool_registry_options_bundle = (
                    original_build_tool_registry_options_bundle
                )

        self.assertEqual(
            response.available_tool_registry_profile_details[0].name,
            "default",
        )
        self.assertEqual(
            response.available_tool_registry_provider_source_details[0].base_profile,
            "default",
        )

    def test_apply_tool_registry_preview_to_validate_response_keeps_provider_source_diagnostics_summary(
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
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": "missing-registry.json",
                        }
                    }
                )
            ),
        )

        file_source = next(
            detail
            for detail in response.available_tool_registry_provider_source_details
            if detail.name == "file_source"
        )
        self.assertTrue(file_source.diagnostics_summary.has_diagnostics)
        self.assertEqual(file_source.diagnostics_summary.missing_total, 1)
        self.assertEqual(file_source.diagnostics_summary.total, 1)
        self.assertEqual(
            file_source.diagnostics_summary.entries[0].target,
            "registry_files",
        )
        self.assertTrue(
            file_source.diagnostics_summary.entries[0].values[0].endswith(
                "/missing-registry.json"
            )
        )

    def test_apply_tool_registry_preview_to_validate_response_includes_invalid_tool_execution_diagnostics(
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
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "analytics_suite": {
                            "provider": "default",
                        }
                    }
                ),
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "execution": {
                                "kind": "unsupported_transport",
                            }
                        }
                    }
                ),
            ),
        )

        analytics_suite = next(
            detail
            for detail in response.available_tool_registry_provider_source_details
            if detail.name == "analytics_suite"
        )
        self.assertTrue(analytics_suite.diagnostics_summary.has_diagnostics)
        self.assertEqual(analytics_suite.diagnostics_summary.missing_total, 0)
        self.assertEqual(analytics_suite.diagnostics_summary.skipped_total, 0)
        self.assertEqual(analytics_suite.diagnostics_summary.total, 1)
        self.assertEqual(
            [
                (
                    entry.kind,
                    entry.target,
                    entry.count,
                    tuple(entry.values),
                )
                for entry in analytics_suite.diagnostics_summary.entries
            ],
            [
                (
                    "invalid",
                    "tool_executions",
                    1,
                    (
                        "calc_eval: unsupported tool execution kind unsupported_transport",
                    ),
                )
            ],
        )

    def test_apply_tool_registry_preview_to_validate_response_includes_per_tool_invalid_execution_diagnostics(
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

    def test_settings_update_request_preserves_raw_registry_selection_fields(
        self,
    ) -> None:
        original_normalize_governance_filter = (
            chat_persistence_module._normalize_governance_filter
        )
        try:
            chat_persistence_module._normalize_governance_filter = (
                lambda _value: (_ for _ in ()).throw(
                    AssertionError(
                        "settings request model should no longer normalize registry selection fields via the governance filter helper"
                    )
                )
            )
            payload = settings_routes_module.SettingsUpdateRequest(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url=" https://example.invalid/v1 ",
                api_key=" secret ",
                tool_registry_profile=" Planning_Only ",
                tool_registry_provider_source=" Planning_Suite ",
            )
        finally:
            chat_persistence_module._normalize_governance_filter = (
                original_normalize_governance_filter
            )

        self.assertEqual(payload.tool_registry_profile, " Planning_Only ")
        self.assertEqual(payload.tool_registry_provider_source, " Planning_Suite ")

    def test_resolve_effective_tool_registry_selection_trusts_shared_registry_name_helpers(
        self,
    ) -> None:
        payload = settings_routes_module.SettingsUpdateRequest(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://example.invalid/v1",
            api_key="secret",
            tool_registry_profile=" Planning_Only ",
            tool_registry_provider_source=" Planning_Suite ",
        )
        existing = StoredSettings(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://example.invalid/v1",
            api_key="secret",
            tool_registry_profile=None,
            tool_registry_provider_source=None,
        )
        original_get_settings = settings_routes_module.get_settings
        original_get_tool_registry_profile_name_from_settings = (
            settings_routes_module.get_tool_registry_profile_name_from_settings
        )
        original_get_tool_registry_provider_source_name_from_settings = (
            settings_routes_module.get_tool_registry_provider_source_name_from_settings
        )
        captured_profiles: list[object] = []
        captured_sources: list[object] = []
        try:
            settings_routes_module.get_settings = lambda: SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
            )

            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured_profiles.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "profile::normalized"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            def fake_get_tool_registry_provider_source_name_from_settings(
                *,
                settings=None,
            ):
                captured_sources.append(
                    getattr(settings, "tool_registry_provider_source", None)
                )
                if (
                    getattr(settings, "tool_registry_provider_source", None)
                    == " Planning_Suite "
                ):
                    return "source::normalized"
                return original_get_tool_registry_provider_source_name_from_settings(
                    settings=settings
                )

            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            settings_routes_module.get_tool_registry_provider_source_name_from_settings = (
                fake_get_tool_registry_provider_source_name_from_settings
            )
            resolved = settings_routes_module._resolve_effective_tool_registry_selection(  # type: ignore[attr-defined]
                payload=payload,
                existing=existing,
            )
        finally:
            settings_routes_module.get_settings = original_get_settings
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )
            settings_routes_module.get_tool_registry_provider_source_name_from_settings = (
                original_get_tool_registry_provider_source_name_from_settings
            )

        self.assertIn(" Planning_Only ", captured_profiles)
        self.assertIn(" Planning_Suite ", captured_sources)
        self.assertEqual(resolved, ("profile::normalized", "source::normalized"))

    def test_resolve_effective_tool_registry_selection_treats_blank_payload_as_missing(
        self,
    ) -> None:
        payload = settings_routes_module.SettingsUpdateRequest(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://example.invalid/v1",
            api_key="secret",
            tool_registry_profile="   ",
            tool_registry_provider_source="   ",
        )
        existing = StoredSettings(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://example.invalid/v1",
            api_key="secret",
            tool_registry_profile="existing_profile",
            tool_registry_provider_source="existing_source",
        )
        original_get_settings = settings_routes_module.get_settings
        original_get_tool_registry_profile_name_from_settings = (
            settings_routes_module.get_tool_registry_profile_name_from_settings
        )
        original_get_tool_registry_provider_source_name_from_settings = (
            settings_routes_module.get_tool_registry_provider_source_name_from_settings
        )
        captured_profiles: list[object] = []
        captured_sources: list[object] = []
        try:
            settings_routes_module.get_settings = lambda: SimpleNamespace(
                tool_registry_profile="runtime_profile",
                tool_registry_provider_source="runtime_source",
            )

            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured_profiles.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == "existing_profile":
                    return "existing_profile"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            def fake_get_tool_registry_provider_source_name_from_settings(
                *,
                settings=None,
            ):
                captured_sources.append(
                    getattr(settings, "tool_registry_provider_source", None)
                )
                if (
                    getattr(settings, "tool_registry_provider_source", None)
                    == "existing_source"
                ):
                    return "existing_source"
                return original_get_tool_registry_provider_source_name_from_settings(
                    settings=settings
                )

            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            settings_routes_module.get_tool_registry_provider_source_name_from_settings = (
                fake_get_tool_registry_provider_source_name_from_settings
            )
            resolved = settings_routes_module._resolve_effective_tool_registry_selection(  # type: ignore[attr-defined]
                payload=payload,
                existing=existing,
            )
        finally:
            settings_routes_module.get_settings = original_get_settings
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )
            settings_routes_module.get_tool_registry_provider_source_name_from_settings = (
                original_get_tool_registry_provider_source_name_from_settings
            )

        self.assertNotIn("   ", captured_profiles)
        self.assertNotIn("   ", captured_sources)
        self.assertIn("existing_profile", captured_profiles)
        self.assertIn("existing_source", captured_sources)
        self.assertEqual(resolved, ("existing_profile", "existing_source"))

    def test_update_settings_reuses_shared_registry_helpers_for_default_fallbacks(
        self,
    ) -> None:
        payload = settings_routes_module.SettingsUpdateRequest(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://example.invalid/v1",
            api_key="secret",
        )
        original_get_stored_settings = settings_routes_module.get_stored_settings
        original_get_settings = settings_routes_module.get_settings
        original_get_tool_registry_profile_name_from_settings = (
            settings_routes_module.get_tool_registry_profile_name_from_settings
        )
        original_get_tool_registry_provider_source_name_from_settings = (
            settings_routes_module.get_tool_registry_provider_source_name_from_settings
        )
        original_build_tool_registry_options_bundle = getattr(
            settings_routes_module,
            "_build_tool_registry_options_bundle",
            None,
        )
        original_save_settings = settings_routes_module.save_settings
        original_build_settings_summary_response = (
            settings_routes_module._build_settings_summary_response
        )
        original_safe_record_audit_event = settings_routes_module.safe_record_audit_event
        captured_profiles: list[object] = []
        captured_sources: list[object] = []
        saved_settings: list[StoredSettings] = []
        try:
            settings_routes_module.get_stored_settings = lambda _user_id: StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile=None,
                tool_registry_provider_source=None,
            )
            settings_routes_module.get_settings = lambda: SimpleNamespace(
                tool_registry_profile=" Planning_Only ",
                tool_registry_provider_source=" Planning_Suite ",
            )

            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured_profiles.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "profile::normalized"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            def fake_get_tool_registry_provider_source_name_from_settings(
                *,
                settings=None,
            ):
                captured_sources.append(
                    getattr(settings, "tool_registry_provider_source", None)
                )
                if (
                    getattr(settings, "tool_registry_provider_source", None)
                    == " Planning_Suite "
                ):
                    return "source::normalized"
                return original_get_tool_registry_provider_source_name_from_settings(
                    settings=settings
                )

            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            settings_routes_module.get_tool_registry_provider_source_name_from_settings = (
                fake_get_tool_registry_provider_source_name_from_settings
            )
            settings_routes_module._build_tool_registry_options_bundle = (
                lambda *, effective_settings: {
                    "available_tool_registry_profiles": [
                        "default",
                        "profile::normalized",
                    ],
                    "available_tool_registry_profile_details": [],
                    "available_tool_registry_provider_sources": [
                        "default",
                        "source::normalized",
                    ],
                    "available_tool_registry_provider_source_details": [],
                }
            )
            settings_routes_module.save_settings = lambda _user_id, settings: (
                saved_settings.append(settings) or settings
            )
            settings_routes_module._build_settings_summary_response = (
                lambda *, settings, runtime_settings=None, database_locator=None, **_kwargs: settings
            )
            settings_routes_module.safe_record_audit_event = lambda **_kwargs: None

            result = settings_routes_module.update_settings(
                payload,
                current_user={"id": "user-1"},
            )
        finally:
            settings_routes_module.get_stored_settings = original_get_stored_settings
            settings_routes_module.get_settings = original_get_settings
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )
            settings_routes_module.get_tool_registry_provider_source_name_from_settings = (
                original_get_tool_registry_provider_source_name_from_settings
            )
            if original_build_tool_registry_options_bundle is None:
                delattr(settings_routes_module, "_build_tool_registry_options_bundle")
            else:
                settings_routes_module._build_tool_registry_options_bundle = (
                    original_build_tool_registry_options_bundle
                )
            settings_routes_module.save_settings = original_save_settings
            settings_routes_module._build_settings_summary_response = (
                original_build_settings_summary_response
            )
            settings_routes_module.safe_record_audit_event = (
                original_safe_record_audit_event
            )

        self.assertIn(" Planning_Only ", captured_profiles)
        self.assertIn(" Planning_Suite ", captured_sources)
        self.assertEqual(len(saved_settings), 1)
        self.assertEqual(saved_settings[0].tool_registry_profile, "profile::normalized")
        self.assertEqual(
            saved_settings[0].tool_registry_provider_source,
            "source::normalized",
        )
        self.assertEqual(result.tool_registry_profile, "profile::normalized")
        self.assertEqual(result.tool_registry_provider_source, "source::normalized")

    def test_update_settings_reuses_shared_tool_registry_options_bundle_for_validation(
        self,
    ) -> None:
        payload = settings_routes_module.SettingsUpdateRequest(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://example.invalid/v1",
            api_key="secret",
        )
        original_get_stored_settings = settings_routes_module.get_stored_settings
        original_get_settings = settings_routes_module.get_settings
        original_build_tool_registry_options_bundle = getattr(
            settings_routes_module,
            "_build_tool_registry_options_bundle",
            None,
        )
        original_save_settings = settings_routes_module.save_settings
        original_build_settings_summary_response = (
            settings_routes_module._build_settings_summary_response
        )
        original_safe_record_audit_event = settings_routes_module.safe_record_audit_event
        saved_settings: list[StoredSettings] = []
        try:
            settings_routes_module.get_stored_settings = lambda _user_id: StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile=None,
                tool_registry_provider_source=None,
            )
            settings_routes_module.get_settings = lambda: SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_provider_source="suite_a",
            )

            def fake_build_tool_registry_options_bundle(*, effective_settings):
                return {
                    "available_tool_registry_profiles": ["default", "planning_only"],
                    "available_tool_registry_profile_details": [],
                    "available_tool_registry_provider_sources": ["default", "suite_a"],
                    "available_tool_registry_provider_source_details": [],
                }

            settings_routes_module._build_tool_registry_options_bundle = (
                fake_build_tool_registry_options_bundle
            )
            settings_routes_module.save_settings = lambda _user_id, settings: (
                saved_settings.append(settings) or settings
            )
            settings_routes_module._build_settings_summary_response = (
                lambda *, settings, runtime_settings=None, database_locator=None, **_kwargs: settings
            )
            settings_routes_module.safe_record_audit_event = lambda **_kwargs: None

            result = settings_routes_module.update_settings(
                payload,
                current_user={"id": "user-1"},
            )
        finally:
            settings_routes_module.get_stored_settings = original_get_stored_settings
            settings_routes_module.get_settings = original_get_settings
            if original_build_tool_registry_options_bundle is None:
                delattr(settings_routes_module, "_build_tool_registry_options_bundle")
            else:
                settings_routes_module._build_tool_registry_options_bundle = (
                    original_build_tool_registry_options_bundle
                )
            settings_routes_module.save_settings = original_save_settings
            settings_routes_module._build_settings_summary_response = (
                original_build_settings_summary_response
            )
            settings_routes_module.safe_record_audit_event = (
                original_safe_record_audit_event
            )

        self.assertEqual(len(saved_settings), 1)
        self.assertEqual(saved_settings[0].tool_registry_profile, "planning_only")
        self.assertEqual(saved_settings[0].tool_registry_provider_source, "suite_a")
        self.assertEqual(result.tool_registry_profile, "planning_only")
        self.assertEqual(result.tool_registry_provider_source, "suite_a")

    def test_update_settings_reuses_shared_tool_registry_selection_validator(
        self,
    ) -> None:
        payload = settings_routes_module.SettingsUpdateRequest(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://example.invalid/v1",
            api_key="secret",
        )
        original_get_stored_settings = settings_routes_module.get_stored_settings
        original_get_settings = settings_routes_module.get_settings
        original_validate_tool_registry_selection = getattr(
            settings_routes_module,
            "_validate_tool_registry_selection",
            None,
        )
        original_build_tool_registry_options_bundle = getattr(
            settings_routes_module,
            "_build_tool_registry_options_bundle",
            None,
        )
        original_save_settings = settings_routes_module.save_settings
        original_build_settings_summary_response = (
            settings_routes_module._build_settings_summary_response
        )
        original_safe_record_audit_event = settings_routes_module.safe_record_audit_event
        captured_validation_calls: list[tuple[str, str, object]] = []
        saved_settings: list[StoredSettings] = []
        try:
            settings_routes_module.get_stored_settings = lambda _user_id: StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://example.invalid/v1",
                api_key="secret",
                tool_registry_profile=None,
                tool_registry_provider_source=None,
            )
            runtime_settings = SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_provider_source="suite_a",
            )
            settings_routes_module.get_settings = lambda: runtime_settings

            def fake_validate_tool_registry_selection(
                *,
                effective_settings,
                tool_registry_profile,
                tool_registry_provider_source,
            ):
                captured_validation_calls.append(
                    (
                        tool_registry_profile,
                        tool_registry_provider_source,
                        effective_settings,
                    )
                )

            settings_routes_module._validate_tool_registry_selection = (  # type: ignore[attr-defined]
                fake_validate_tool_registry_selection
            )
            settings_routes_module._build_tool_registry_options_bundle = (
                lambda *, effective_settings: (_ for _ in ()).throw(
                    AssertionError(
                        "update_settings should reuse _validate_tool_registry_selection(...) instead of reading option bundle fields directly"
                    )
                )
            )
            settings_routes_module.save_settings = lambda _user_id, settings: (
                saved_settings.append(settings) or settings
            )
            settings_routes_module._build_settings_summary_response = (
                lambda *, settings, runtime_settings=None, database_locator=None, **_kwargs: settings
            )
            settings_routes_module.safe_record_audit_event = lambda **_kwargs: None

            result = settings_routes_module.update_settings(
                payload,
                current_user={"id": "user-1"},
            )
        finally:
            settings_routes_module.get_stored_settings = original_get_stored_settings
            settings_routes_module.get_settings = original_get_settings
            if original_validate_tool_registry_selection is None:
                if hasattr(settings_routes_module, "_validate_tool_registry_selection"):
                    delattr(settings_routes_module, "_validate_tool_registry_selection")
            else:
                settings_routes_module._validate_tool_registry_selection = (  # type: ignore[attr-defined]
                    original_validate_tool_registry_selection
                )
            if original_build_tool_registry_options_bundle is None:
                delattr(settings_routes_module, "_build_tool_registry_options_bundle")
            else:
                settings_routes_module._build_tool_registry_options_bundle = (
                    original_build_tool_registry_options_bundle
                )
            settings_routes_module.save_settings = original_save_settings
            settings_routes_module._build_settings_summary_response = (
                original_build_settings_summary_response
            )
            settings_routes_module.safe_record_audit_event = (
                original_safe_record_audit_event
            )

        self.assertEqual(
            captured_validation_calls,
            [("planning_only", "suite_a", runtime_settings)],
        )
        self.assertEqual(len(saved_settings), 1)
        self.assertEqual(result.tool_registry_profile, "planning_only")
        self.assertEqual(result.tool_registry_provider_source, "suite_a")

    def test_update_settings_reuses_existing_remote_base_url_when_payload_omits_it(
        self,
    ) -> None:
        payload = settings_routes_module.SettingsUpdateRequest(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            api_key="secret",
        )
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
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://runtime.example/v1",
                api_key="secret",
                tool_registry_profile="default",
                tool_registry_provider_source="default",
            )
            settings_routes_module.get_settings = lambda: SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
            )
            settings_routes_module.save_settings = lambda _user_id, settings: (
                saved_settings.append(settings) or settings
            )
            settings_routes_module._build_settings_summary_response = (
                lambda *, settings, runtime_settings=None, database_locator=None, **_kwargs: settings
            )
            settings_routes_module.safe_record_audit_event = lambda **_kwargs: None

            result = settings_routes_module.update_settings(
                payload,
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
        self.assertEqual(saved_settings[0].base_url, "https://runtime.example/v1")
        self.assertEqual(result.base_url, "https://runtime.example/v1")

    def test_validate_settings_reuses_shared_tool_registry_selection_validator(
        self,
    ) -> None:
        payload = settings_routes_module.SettingsUpdateRequest(
            mode="mock",
            provider="mock",
            model="mock-gpt",
            tool_registry_profile="missing_profile",
            tool_registry_provider_source="default",
        )
        original_get_stored_settings = settings_routes_module.get_stored_settings
        original_get_settings = settings_routes_module.get_settings
        original_validate_tool_registry_selection = (
            settings_routes_module._validate_tool_registry_selection
        )
        original_safe_record_audit_event = settings_routes_module.safe_record_audit_event
        captured_validation_calls: list[tuple[str, str, object]] = []
        try:
            settings_routes_module.get_stored_settings = lambda _user_id: StoredSettings(
                mode="mock",
                provider="mock",
                model="mock-gpt",
                base_url=None,
                api_key=None,
                tool_registry_profile=None,
                tool_registry_provider_source=None,
            )
            runtime_settings = SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
            )
            settings_routes_module.get_settings = lambda: runtime_settings

            def fake_validate_tool_registry_selection(
                *,
                effective_settings,
                tool_registry_profile,
                tool_registry_provider_source,
            ):
                captured_validation_calls.append(
                    (
                        tool_registry_profile,
                        tool_registry_provider_source,
                        effective_settings,
                    )
                )
                raise settings_routes_module.HTTPException(
                    status_code=422,
                    detail="tool_registry_profile is invalid",
                )

            settings_routes_module._validate_tool_registry_selection = (
                fake_validate_tool_registry_selection
            )
            settings_routes_module.safe_record_audit_event = lambda **_kwargs: None

            response = settings_routes_module.validate_settings(
                payload,
                current_user={"id": "user-validate-registry"},
            )
        finally:
            settings_routes_module.get_stored_settings = original_get_stored_settings
            settings_routes_module.get_settings = original_get_settings
            settings_routes_module._validate_tool_registry_selection = (
                original_validate_tool_registry_selection
            )
            settings_routes_module.safe_record_audit_event = (
                original_safe_record_audit_event
            )

        self.assertEqual(
            captured_validation_calls,
            [("missing_profile", "default", runtime_settings)],
        )
        self.assertFalse(response.ok)
        self.assertEqual(response.error_code, "tool_registry_selection_invalid")
        self.assertEqual(response.error, "tool_registry_profile is invalid")

    def test_validate_settings_reuses_existing_remote_base_url_when_payload_omits_it(
        self,
    ) -> None:
        payload = settings_routes_module.SettingsUpdateRequest(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            api_key="secret",
        )
        original_get_stored_settings = settings_routes_module.get_stored_settings
        original_get_settings = settings_routes_module.get_settings
        original_urlopen = settings_routes_module.urlopen
        original_safe_record_audit_event = settings_routes_module.safe_record_audit_event
        try:
            settings_routes_module.get_stored_settings = lambda _user_id: StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url="https://runtime.example/v1",
                api_key="secret",
                tool_registry_profile="default",
                tool_registry_provider_source="default",
            )
            settings_routes_module.get_settings = lambda: SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
            )

            class FakeResponse:
                status = 200

                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return False

            settings_routes_module.urlopen = lambda request, timeout=0: FakeResponse()
            settings_routes_module.safe_record_audit_event = lambda **_kwargs: None

            response = settings_routes_module.validate_settings(
                payload,
                current_user={"id": "user-validate-base-url"},
            )
        finally:
            settings_routes_module.get_stored_settings = original_get_stored_settings
            settings_routes_module.get_settings = original_get_settings
            settings_routes_module.urlopen = original_urlopen
            settings_routes_module.safe_record_audit_event = (
                original_safe_record_audit_event
            )

        self.assertTrue(response.ok)
        self.assertEqual(response.message, "remote preflight succeeded.")
        self.assertEqual(response.mode, "remote")
        self.assertEqual(response.provider, "openai")
        self.assertEqual(response.model, "gpt-4.1-mini")

    def test_validate_settings_redacts_remote_preflight_network_error_diagnostics(
        self,
    ) -> None:
        payload = settings_routes_module.SettingsUpdateRequest(
            mode="remote",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://runtime.example/v1",
            api_key="secret",
        )
        original_get_stored_settings = settings_routes_module.get_stored_settings
        original_get_settings = settings_routes_module.get_settings
        original_urlopen = settings_routes_module.urlopen
        original_safe_record_audit_event = settings_routes_module.safe_record_audit_event
        original_validate_tool_registry_selection = (
            settings_routes_module._validate_tool_registry_selection
        )
        original_apply_tool_registry_preview = (
            settings_routes_module._apply_tool_registry_preview_to_validate_response
        )
        try:
            settings_routes_module.get_stored_settings = lambda _user_id: StoredSettings(
                mode="remote",
                provider="openai",
                model="gpt-4.1-mini",
                base_url=None,
                api_key=None,
                tool_registry_profile="default",
                tool_registry_provider_source="default",
            )
            settings_routes_module.get_settings = lambda: SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="default",
            )
            settings_routes_module._validate_tool_registry_selection = (  # type: ignore[assignment]
                lambda **_kwargs: None
            )
            settings_routes_module._apply_tool_registry_preview_to_validate_response = (  # type: ignore[assignment]
                lambda *, result, effective_settings: result
            )

            def fake_urlopen(request, timeout=0):
                method = getattr(request, "get_method", lambda: "")()
                if method == "HEAD":
                    raise settings_routes_module.URLError(
                        "callback https://provider.example/cb?"
                        "access_token=secret-token#client_secret=hidden"
                    )
                raise RuntimeError(
                    "GET failed response_path=$.data.access_token Bearer secret-token"
                )

            settings_routes_module.urlopen = fake_urlopen
            settings_routes_module.safe_record_audit_event = lambda **_kwargs: None

            response = settings_routes_module.validate_settings(
                payload,
                current_user={"id": "user-validate-network-redaction"},
            )
        finally:
            settings_routes_module.get_stored_settings = original_get_stored_settings
            settings_routes_module.get_settings = original_get_settings
            settings_routes_module.urlopen = original_urlopen
            settings_routes_module.safe_record_audit_event = (
                original_safe_record_audit_event
            )
            settings_routes_module._validate_tool_registry_selection = (
                original_validate_tool_registry_selection
            )
            settings_routes_module._apply_tool_registry_preview_to_validate_response = (
                original_apply_tool_registry_preview
            )

        self.assertFalse(response.ok)
        self.assertEqual(response.error_code, "remote_preflight_network_error")
        self.assertIsNotNone(response.error)
        assert response.error is not None
        self.assertIn("[redacted]", response.error)
        self.assertIn("callback", response.error)
        self.assertNotIn("access_token", response.error)
        self.assertNotIn("client_secret", response.error)
        self.assertNotIn("secret-token", response.error)
        self.assertNotIn("Bearer", response.error)

    def test_tool_registry_profile_option_details_reuse_preview_labels(
        self,
    ) -> None:
        original_get_available_tool_registry_profile_names = (
            settings_routes_module.get_available_tool_registry_profile_names
        )
        original_build_tool_registry_preview_fields = (
            settings_routes_module._build_tool_registry_preview_fields
        )
        try:
            settings_routes_module.get_available_tool_registry_profile_names = (
                lambda: ("default",)
            )

            def fake_build_tool_registry_preview_fields(*, effective_settings):
                return {
                    "tool_registry_profile": getattr(
                        effective_settings,
                        "tool_registry_profile",
                        "default",
                    ),
                    "tool_registry_provider_source": "default",
                    "enabled_tool_names": ["calc_eval", "task_plan"],
                    "enabled_tool_labels": ["Custom Calculator", "Task Planner"],
                }

            settings_routes_module._build_tool_registry_preview_fields = (
                fake_build_tool_registry_preview_fields
            )
            option_bundle = settings_routes_module._build_tool_registry_options_bundle(
                effective_settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="default",
                )
            )
        finally:
            settings_routes_module.get_available_tool_registry_profile_names = (
                original_get_available_tool_registry_profile_names
            )
            settings_routes_module._build_tool_registry_preview_fields = (
                original_build_tool_registry_preview_fields
            )

        details = option_bundle["available_tool_registry_profile_details"]
        self.assertEqual(details[0]["enabled_tool_names"], ["task_plan", "calc_eval"])
        self.assertEqual(
            details[0]["enabled_tool_labels"],
            ["Task Planner", "Custom Calculator"],
        )

    def test_tool_registry_options_bundle_returns_raw_profile_detail_dicts(
        self,
    ) -> None:
        original_profile_option_response = (
            settings_routes_module.ToolRegistryProfileOptionResponse
        )
        try:
            def fail_profile_option_response(*args, **kwargs):
                raise AssertionError(
                    "option bundle should not construct profile response models"
                )

            settings_routes_module.ToolRegistryProfileOptionResponse = (
                fail_profile_option_response
            )
            option_bundle = settings_routes_module._build_tool_registry_options_bundle(
                effective_settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="default",
                )
            )
        finally:
            settings_routes_module.ToolRegistryProfileOptionResponse = (
                original_profile_option_response
            )

        details = option_bundle["available_tool_registry_profile_details"]
        self.assertIsInstance(details[0], dict)
        self.assertEqual(details[0]["name"], "default")
        self.assertIn("enabled_tool_names", details[0])
        self.assertIn("enabled_tool_labels", details[0])
        self.assertIn("tool_details", details[0])

    def test_tool_registry_options_bundle_returns_raw_provider_source_detail_dicts(
        self,
    ) -> None:
        original_provider_source_option_response = (
            settings_routes_module.ToolRegistryProviderSourceOptionResponse
        )
        try:
            def fail_provider_source_option_response(*args, **kwargs):
                raise AssertionError(
                    "option bundle should not construct provider source response models"
                )

            settings_routes_module.ToolRegistryProviderSourceOptionResponse = (
                fail_provider_source_option_response
            )
            option_bundle = settings_routes_module._build_tool_registry_options_bundle(
                effective_settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="default",
                )
            )
        finally:
            settings_routes_module.ToolRegistryProviderSourceOptionResponse = (
                original_provider_source_option_response
            )

        details = option_bundle["available_tool_registry_provider_source_details"]
        self.assertIsInstance(details[0], dict)
        self.assertEqual(details[0]["name"], "default")
        self.assertEqual(details[0]["base_profile"], "default")
        self.assertIn("enabled_tool_names", details[0])
        self.assertIn("enabled_tool_labels", details[0])
        self.assertIn("tool_details", details[0])
        self.assertIn("diagnostics_summary", details[0])

    def test_tool_registry_options_bundle_includes_provider_source_diagnostics_summary(
        self,
    ) -> None:
        option_bundle = settings_routes_module._build_tool_registry_options_bundle(
            effective_settings=SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": "missing-registry.json",
                        }
                    }
                )
            )
        )

        file_source = next(
            detail
            for detail in option_bundle["available_tool_registry_provider_source_details"]
            if detail["name"] == "file_source"
        )
        diagnostics_summary = file_source["diagnostics_summary"]
        self.assertTrue(bool(diagnostics_summary["has_diagnostics"]))
        self.assertEqual(diagnostics_summary["missing_total"], 1)
        self.assertEqual(diagnostics_summary["skipped_total"], 0)
        self.assertEqual(diagnostics_summary["total"], 1)
        self.assertEqual(
            diagnostics_summary["entries"][0]["target"],
            "registry_files",
        )
        self.assertTrue(
            str(diagnostics_summary["entries"][0]["values"][0]).endswith(
                "/missing-registry.json"
            )
        )

    def test_tool_registry_options_bundle_includes_global_invalid_tool_execution_diagnostics(
        self,
    ) -> None:
        option_bundle = settings_routes_module._build_tool_registry_options_bundle(
            effective_settings=SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "analytics_suite": {
                            "provider": "default",
                        }
                    }
                ),
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "execution": {
                                "kind": "unsupported_transport",
                            }
                        }
                    }
                ),
            )
        )

        analytics_suite = next(
            detail
            for detail in option_bundle["available_tool_registry_provider_source_details"]
            if detail["name"] == "analytics_suite"
        )
        diagnostics_summary = analytics_suite["diagnostics_summary"]
        self.assertTrue(bool(diagnostics_summary["has_diagnostics"]))
        self.assertEqual(diagnostics_summary["missing_total"], 0)
        self.assertEqual(diagnostics_summary["skipped_total"], 0)
        self.assertEqual(diagnostics_summary["total"], 1)
        self.assertEqual(
            diagnostics_summary["entries"],
            (
                {
                    "kind": "invalid",
                    "target": "tool_executions",
                    "count": 1,
                    "values": (
                        "calc_eval: unsupported tool execution kind unsupported_transport",
                    ),
                },
            ),
        )

    def test_provider_source_option_details_reuse_shared_profile_name_helper(
        self,
    ) -> None:
        original_get_tool_registry_profile_name_from_settings = (
            settings_routes_module.get_tool_registry_profile_name_from_settings
        )
        captured: list[object] = []
        try:
            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "profile::normalized"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            option_bundle = settings_routes_module._build_tool_registry_options_bundle(
                effective_settings=SimpleNamespace(
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "suite_a": {
                                "provider": "default",
                                "profile": " Planning_Only ",
                            }
                        }
                    )
                )
            )
        finally:
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )

        details = option_bundle["available_tool_registry_provider_source_details"]
        suite_a = next(detail for detail in details if detail["name"] == "suite_a")
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(suite_a["base_profile"], "profile::normalized")

    def test_tool_registry_options_bundle_humanizes_unlabeled_provider_source_tool_labels(
        self,
    ) -> None:
        original_get_available_tool_registry_profile_names = (
            settings_routes_module.get_available_tool_registry_profile_names
        )
        original_build_tool_registry_preview_fields = (
            settings_routes_module._build_tool_registry_preview_fields
        )
        original_build_tool_registry_provider_sources_from_settings_artifacts = (
            settings_routes_module.build_tool_registry_provider_sources_from_settings_artifacts
        )
        original_get_tool_registry_provider_source_specs_from_settings = (
            settings_routes_module.get_tool_registry_provider_source_specs_from_settings
        )
        try:
            settings_routes_module.get_available_tool_registry_profile_names = (
                lambda: ("default",)
            )
            settings_routes_module._build_tool_registry_preview_fields = (
                lambda *, effective_settings: {
                    "tool_registry_profile": "default",
                    "tool_registry_provider_source": "default",
                    "enabled_tool_names": ["task_plan"],
                    "enabled_tool_labels": ["Task Planner"],
                }
            )
            settings_routes_module.build_tool_registry_provider_sources_from_settings_artifacts = (
                lambda settings=None: {
                    "sources": {
                        "analytics_suite": StaticToolRegistryProvider(
                            registry={
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
                            }
                        )
                    },
                    "source_diagnostics": {
                        "analytics_suite": {},
                    },
                }
            )
            settings_routes_module.get_tool_registry_provider_source_specs_from_settings = (
                lambda settings=None: {
                    "analytics_suite": {
                        "profile": "default",
                    }
                }
            )

            option_bundle = settings_routes_module._build_tool_registry_options_bundle(
                effective_settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="analytics_suite",
                )
            )
        finally:
            settings_routes_module.get_available_tool_registry_profile_names = (
                original_get_available_tool_registry_profile_names
            )
            settings_routes_module._build_tool_registry_preview_fields = (
                original_build_tool_registry_preview_fields
            )
            settings_routes_module.build_tool_registry_provider_sources_from_settings_artifacts = (
                original_build_tool_registry_provider_sources_from_settings_artifacts
            )
            settings_routes_module.get_tool_registry_provider_source_specs_from_settings = (
                original_get_tool_registry_provider_source_specs_from_settings
            )

        analytics_suite = next(
            detail
            for detail in option_bundle["available_tool_registry_provider_source_details"]
            if detail["name"] == "analytics_suite"
        )
        self.assertEqual(
            analytics_suite["enabled_tool_labels"],
            ["Provider Math", "Provider Search"],
        )

    def test_provider_source_option_details_reuse_shared_provider_source_name_helper_for_spec_lookup(
        self,
    ) -> None:
        original_get_tool_registry_provider_source_name_from_settings = (
            tool_runtime_module.get_tool_registry_provider_source_name_from_settings
        )
        original_get_tool_registry_profile_name_from_settings = (
            settings_routes_module.get_tool_registry_profile_name_from_settings
        )
        captured_sources: list[object] = []
        captured_profiles: list[object] = []
        try:
            def fake_get_tool_registry_provider_source_name_from_settings(
                *,
                settings=None,
            ):
                captured_sources.append(
                    getattr(settings, "tool_registry_provider_source", None)
                )
                if (
                    getattr(settings, "tool_registry_provider_source", None)
                    == " Suite_A "
                ):
                    return "suite_a"
                return original_get_tool_registry_provider_source_name_from_settings(
                    settings=settings
                )

            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured_profiles.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "profile::normalized"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                fake_get_tool_registry_provider_source_name_from_settings
            )
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            option_bundle = settings_routes_module._build_tool_registry_options_bundle(
                effective_settings=SimpleNamespace(
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            " Suite_A ": {
                                "provider": "default",
                                "profile": " Planning_Only ",
                            }
                        }
                    )
                )
            )
        finally:
            tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                original_get_tool_registry_provider_source_name_from_settings
            )
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )

        details = option_bundle["available_tool_registry_provider_source_details"]
        suite_a = next(detail for detail in details if detail["name"] == "suite_a")
        self.assertIn(" Suite_A ", captured_sources)
        self.assertIn(" Planning_Only ", captured_profiles)
        self.assertEqual(suite_a["base_profile"], "profile::normalized")

    def test_provider_source_option_details_reuse_shared_source_specs_helper(
        self,
    ) -> None:
        original_get_tool_registry_provider_source_specs_from_settings = getattr(
            settings_routes_module,
            "get_tool_registry_provider_source_specs_from_settings",
            None,
        )
        original_get_tool_registry_profile_name_from_settings = (
            settings_routes_module.get_tool_registry_profile_name_from_settings
        )
        captured_profiles: list[object] = []
        try:
            def fake_get_tool_registry_provider_source_specs_from_settings(
                *,
                settings=None,
            ):
                return {
                    "suite_a": {
                        "provider": "default",
                        "profile": " Planning_Only ",
                    }
                }

            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured_profiles.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "profile::normalized"
                return "default"

            settings_routes_module.get_tool_registry_provider_source_specs_from_settings = (
                fake_get_tool_registry_provider_source_specs_from_settings
            )
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            option_bundle = settings_routes_module._build_tool_registry_options_bundle(
                effective_settings=SimpleNamespace(
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "suite_a": {
                                "provider": "default",
                                "profile": "default",
                            }
                        }
                    )
                )
            )
        finally:
            if original_get_tool_registry_provider_source_specs_from_settings is None:
                delattr(
                    settings_routes_module,
                    "get_tool_registry_provider_source_specs_from_settings",
                )
            else:
                settings_routes_module.get_tool_registry_provider_source_specs_from_settings = (
                    original_get_tool_registry_provider_source_specs_from_settings
                )
            settings_routes_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )

        details = option_bundle["available_tool_registry_provider_source_details"]
        suite_a = next(detail for detail in details if detail["name"] == "suite_a")
        self.assertIn(" Planning_Only ", captured_profiles)
        self.assertEqual(suite_a["base_profile"], "profile::normalized")

    def test_provider_source_option_details_do_not_recompute_available_source_names(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(
                settings_routes_module,
                "get_available_tool_registry_provider_source_names",
            )
        )
        option_bundle = settings_routes_module._build_tool_registry_options_bundle(
            effective_settings=SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "suite_a": {
                            "provider": "default",
                            "profile": "planning_only",
                        }
                    }
                )
            )
        )

        details = option_bundle["available_tool_registry_provider_source_details"]
        self.assertEqual([detail["name"] for detail in details], ["default", "suite_a"])

    def test_settings_route_module_does_not_expose_dead_tool_registry_option_detail_wrappers(
        self,
    ) -> None:
        self.assertFalse(
            hasattr(settings_routes_module, "_build_tool_registry_profile_option_details")
        )
        self.assertFalse(
            hasattr(
                settings_routes_module,
                "_build_tool_registry_provider_source_option_details",
            )
        )
        self.assertFalse(
            hasattr(settings_routes_module, "_build_tool_registry_profile_options")
        )
        self.assertFalse(
            hasattr(
                settings_routes_module,
                "_build_tool_registry_provider_source_options",
            )
        )

    def test_build_settings_summary_response_reuses_shared_tool_registry_options_bundle(
        self,
    ) -> None:
        original_build_tool_registry_options_bundle = getattr(
            settings_routes_module,
            "_build_tool_registry_options_bundle",
            None,
        )
        original_build_tool_registry_preview_fields = (
            settings_routes_module._build_tool_registry_preview_fields
        )
        try:
            def fake_build_tool_registry_options_bundle(*, effective_settings):
                return {
                    "available_tool_registry_profiles": ["default", "planning_only"],
                    "available_tool_registry_profile_details": [
                        settings_routes_module.ToolRegistryProfileOptionResponse(
                            name="default",
                            enabled_tool_names=["task_plan"],
                            enabled_tool_labels=["Task Planner"],
                        )
                    ],
                    "available_tool_registry_provider_sources": ["default", "suite_a"],
                    "available_tool_registry_provider_source_details": [
                        settings_routes_module.ToolRegistryProviderSourceOptionResponse(
                            name="default",
                            base_profile="default",
                            enabled_tool_names=["task_plan"],
                            enabled_tool_labels=["Task Planner"],
                        )
                    ],
                }

            settings_routes_module._build_tool_registry_options_bundle = (
                fake_build_tool_registry_options_bundle
            )
            settings_routes_module._build_tool_registry_preview_fields = (
                lambda *, effective_settings: {
                    "tool_registry_profile": "planning_only",
                    "tool_registry_provider_source": "suite_a",
                    "enabled_tool_names": ["task_plan"],
                    "enabled_tool_labels": ["Task Planner"],
                }
            )
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
                    tool_registry_profile="planning_only",
                    tool_registry_provider_source="suite_a",
                ),
                database_locator="postgresql://demo",
            )
        finally:
            if original_build_tool_registry_options_bundle is None:
                delattr(settings_routes_module, "_build_tool_registry_options_bundle")
            else:
                settings_routes_module._build_tool_registry_options_bundle = (
                    original_build_tool_registry_options_bundle
                )
            settings_routes_module._build_tool_registry_preview_fields = (
                original_build_tool_registry_preview_fields
            )

        self.assertEqual(
            summary.available_tool_registry_profiles,
            ["default", "planning_only"],
        )
        self.assertEqual(
            summary.available_tool_registry_provider_sources,
            ["default", "suite_a"],
        )
        self.assertEqual(
            [detail.name for detail in summary.available_tool_registry_profile_details],
            ["default"],
        )
        self.assertEqual(
            [
                detail.name
                for detail in summary.available_tool_registry_provider_source_details
            ],
            ["default"],
        )
