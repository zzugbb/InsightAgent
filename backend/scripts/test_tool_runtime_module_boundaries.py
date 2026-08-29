from __future__ import annotations

from pathlib import Path
import unittest

from app.services import tool_runtime
from app.services import tool_runtime_http_json
from app.services import tool_runtime_http_json_execution
from app.services import tool_runtime_registry
from app.services import tool_runtime_registry_runtime


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MAX_BACKEND_PYTHON_LINES = 3000
SIZE_BOUNDARY_ROOTS = (BACKEND_ROOT / "app", BACKEND_ROOT / "scripts")


class ToolRuntimeModuleBoundaryTests(unittest.TestCase):
    def test_http_json_execution_implementation_lives_in_execution_module(self) -> None:
        self.assertIs(
            tool_runtime_http_json._build_http_json_tool_runner,
            tool_runtime_http_json_execution._build_http_json_tool_runner,
        )
        self.assertIs(
            tool_runtime_http_json.build_tool_registry_settings_execution_diagnostics,
            tool_runtime_http_json_execution.build_tool_registry_settings_execution_diagnostics,
        )

    def test_registry_runtime_implementation_lives_in_runtime_module(self) -> None:
        self.assertIs(
            tool_runtime_registry._impl_build_configured_tool_registry_provider_preflight_summary_model,
            tool_runtime_registry_runtime._impl_build_configured_tool_registry_provider_preflight_summary_model,
        )

    def test_facade_exports_remain_available(self) -> None:
        self.assertIs(
            tool_runtime._build_http_json_tool_runner,
            tool_runtime_http_json._build_http_json_tool_runner,
        )
        self.assertTrue(
            callable(tool_runtime.build_configured_tool_registry_provider_preflight_summary_model)
        )

    def test_backend_python_files_stay_below_size_boundary(self) -> None:
        oversized: list[str] = []
        for root in SIZE_BOUNDARY_ROOTS:
            for path in sorted(root.rglob("*.py")):
                if "__pycache__" in path.parts:
                    continue
                line_count = len(path.read_text(encoding="utf-8").splitlines())
                if line_count > MAX_BACKEND_PYTHON_LINES:
                    oversized.append(
                        f"{path.relative_to(BACKEND_ROOT)} has {line_count} lines"
                    )

        self.assertEqual([], oversized)


if __name__ == "__main__":
    unittest.main()
