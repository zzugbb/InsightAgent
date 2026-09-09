from __future__ import annotations

import sys
import warnings
from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI


BACKEND_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_FASTAPI_VERSION = "0.118.3"


class RuntimeDependencyContractMixin:
    def test_runtime_dependency_fastapi_pin_matches_installed_version(self) -> None:
        requirement_lines = {
            line.strip()
            for line in (BACKEND_ROOT / "requirements.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        self.assertIn(
            f"fastapi=={EXPECTED_FASTAPI_VERSION}",
            requirement_lines,
        )
        self.assertEqual(EXPECTED_FASTAPI_VERSION, version("fastapi"))

    def test_runtime_dependency_fastapi_route_registration_is_warning_free_on_python_314(
        self,
    ) -> None:
        if sys.version_info < (3, 14):
            self.skipTest("Python 3.14 coroutine deprecation is not active")

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", DeprecationWarning)
            app = FastAPI()

            @app.get("/runtime-dependency-probe")
            async def runtime_dependency_probe() -> dict[str, str]:
                return {"status": "ok"}

        coroutine_warnings = [
            warning
            for warning in captured
            if issubclass(warning.category, DeprecationWarning)
            and "asyncio.iscoroutinefunction" in str(warning.message)
        ]
        self.assertEqual([], coroutine_warnings)
