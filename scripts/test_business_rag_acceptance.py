#!/usr/bin/env python3
"""Wrapper to run business RAG acceptance self-test from repo tooling."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "business_rag_acceptance_runner.py"
PYTHON = ROOT / "backend" / ".venv" / "bin" / "python"


def main() -> int:
    python = PYTHON if PYTHON.is_file() else Path(sys.executable)
    static = ROOT / "scripts" / "test_business_rag_acceptance_static.py"
    static_result = subprocess.run([str(python), str(static)], cwd=str(ROOT))
    if static_result.returncode != 0:
        return static_result.returncode
    docker_check = subprocess.run(["docker", "info"], capture_output=True)
    if docker_check.returncode != 0:
        print("business_rag_acceptance: docker unavailable, skipped isolated self-test")
        return 0
    result = subprocess.run([str(python), str(RUNNER), "--self-test"], cwd=str(ROOT))
    if result.returncode == 0:
        print("business_rag_acceptance self-test passed")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
