#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCOPE="${1:-all}"

run_common() {
  bash "${ROOT_DIR}/scripts/test_ci_collect_backend_failure_diagnostics.sh"
  bash "${ROOT_DIR}/scripts/test_ci_build_frontend_failure_index.sh"
  bash "${ROOT_DIR}/scripts/test_ci_service_bootstrap.sh"
  bash "${ROOT_DIR}/scripts/test_ci_stage_artifacts.sh"
  bash "${ROOT_DIR}/scripts/test_ci_resolve_diag_strict_level.sh"
  bash "${ROOT_DIR}/scripts/test_ci_diag_guard.sh"
  bash "${ROOT_DIR}/scripts/test_ci_export_diagnostics_overview.sh"
  bash "${ROOT_DIR}/scripts/test_ci_export_diag_pipeline.sh"
  bash "${ROOT_DIR}/scripts/test_ci_export_diag_flow.sh"
}

run_backend() {
  bash "${ROOT_DIR}/backend/scripts/test_ci_export_consistency_summary.sh"
}

run_frontend() {
  bash "${ROOT_DIR}/frontend/scripts/test_ci_export_diagnostics.sh"
}

case "${SCOPE}" in
  common)
    run_common
    ;;
  backend)
    run_common
    run_backend
    ;;
  frontend)
    run_common
    run_frontend
    ;;
  all)
    run_common
    run_backend
    run_frontend
    ;;
  *)
    echo "unknown scope: ${SCOPE} (expected: common|backend|frontend|all)" >&2
    exit 2
    ;;
esac

echo "ci_e2e_tooling tests passed (scope=${SCOPE})"
