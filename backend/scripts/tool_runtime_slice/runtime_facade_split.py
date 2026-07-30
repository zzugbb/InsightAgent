from __future__ import annotations

from .context import *


class RuntimeFacadeSplitMixin:
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
