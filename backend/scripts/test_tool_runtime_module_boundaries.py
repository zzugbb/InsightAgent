from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from app.services import tool_runtime
from app.services import tool_runtime_http_json
from app.services import tool_runtime_http_json_execution
from app.services import tool_runtime_registry
from app.services import tool_runtime_registry_runtime


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MAX_BACKEND_PYTHON_LINES = 3000
MAX_TOOL_RUNTIME_TEST_TOPIC_LINES = 2500
SIZE_BOUNDARY_ROOTS = (BACKEND_ROOT / "app", BACKEND_ROOT / "scripts")
TOOL_RUNTIME_SLICE_ROOT = BACKEND_ROOT / "scripts" / "tool_runtime_slice"
TOOL_RUNTIME_SLICE_SCRIPT = BACKEND_ROOT / "scripts" / "test_tool_runtime_slice.py"


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

    def test_tool_runtime_test_topics_keep_split_headroom(self) -> None:
        oversized: list[str] = []
        for path in sorted(TOOL_RUNTIME_SLICE_ROOT.glob("*.py")):
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count > MAX_TOOL_RUNTIME_TEST_TOPIC_LINES:
                oversized.append(
                    f"{path.relative_to(BACKEND_ROOT)} has {line_count} lines"
                )

        self.assertEqual([], oversized)

    def test_selective_slice_run_rejects_unmatched_pattern(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(TOOL_RUNTIME_SLICE_SCRIPT),
                "-k",
                "__definitely_no_tool_runtime_test_matches__",
            ],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(5, result.returncode)
        self.assertIn(
            "no tool runtime tests matched -k selection",
            result.stderr,
        )
        self.assertIn(
            "__definitely_no_tool_runtime_test_matches__",
            result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
