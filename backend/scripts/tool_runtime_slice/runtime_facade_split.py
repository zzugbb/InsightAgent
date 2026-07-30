from __future__ import annotations

from .context import *


class RuntimeFacadeSplitMixin:
    def test_tool_runtime_facade_exports_registry_split_module_functions(self) -> None:
        registry_module = __import__(
            "app.services.tool_runtime_registry",
            fromlist=[
                "build_tool_registry_from_file_artifacts",
                "get_configured_tool_registry_provider",
            ],
        )

        self.assertIs(
            tool_runtime_module.build_tool_registry_from_file_artifacts,
            registry_module.build_tool_registry_from_file_artifacts,
        )
        self.assertIs(
            tool_runtime_module.get_configured_tool_registry_provider,
            registry_module.get_configured_tool_registry_provider,
        )

    def test_tool_runtime_facade_exports_planning_split_module_functions(self) -> None:
        planning_module = __import__(
            "app.services.tool_runtime_planning",
            fromlist=["build_tool_plan", "build_tool_plan_artifacts"],
        )

        self.assertIs(tool_runtime_module.build_tool_plan, planning_module.build_tool_plan)
        self.assertIs(
            tool_runtime_module.build_tool_plan_artifacts,
            planning_module.build_tool_plan_artifacts,
        )

    def test_tool_runtime_facade_exports_execution_split_module_functions(self) -> None:
        execution_module = __import__(
            "app.services.tool_runtime_execution",
            fromlist=[
                "build_tool_result_summary",
                "execute_tool_plan_item_service_execution",
            ],
        )

        self.assertIs(
            tool_runtime_module.build_tool_result_summary,
            execution_module.build_tool_result_summary,
        )
        self.assertIs(
            tool_runtime_module.execute_tool_plan_item_service_execution,
            execution_module.execute_tool_plan_item_service_execution,
        )

    def test_tool_runtime_facade_exports_http_json_split_module_functions(self) -> None:
        http_json_module = __import__(
            "app.services.tool_runtime_http_json",
            fromlist=[
                "_normalize_tool_execution_kind",
                "build_tool_registry_settings_execution_diagnostics",
            ],
        )

        self.assertIs(
            tool_runtime_module._normalize_tool_execution_kind,
            http_json_module._normalize_tool_execution_kind,
        )
        self.assertIs(
            tool_runtime_module.build_tool_registry_settings_execution_diagnostics,
            http_json_module.build_tool_registry_settings_execution_diagnostics,
        )
