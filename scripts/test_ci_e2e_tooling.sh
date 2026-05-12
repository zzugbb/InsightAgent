#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCOPE="${1:-all}"

run_common() {
  bash "${ROOT_DIR}/scripts/test_ci_assert_artifact_stage_health.sh"
  bash "${ROOT_DIR}/scripts/test_ci_collect_changed_files.sh"
  bash "${ROOT_DIR}/scripts/test_ci_resolve_artifact_stage_strict_level.sh"
  bash "${ROOT_DIR}/scripts/test_ci_resolve_artifact_stage_path_level.sh"
  bash "${ROOT_DIR}/scripts/test_ci_print_log_files.sh"
  bash "${ROOT_DIR}/scripts/test_ci_finalize_e2e_for_workflow.sh"
  bash "${ROOT_DIR}/scripts/test_ci_finalize_e2e_scope.sh"
  bash "${ROOT_DIR}/scripts/test_ci_workflow_guards.sh"
  bash "${ROOT_DIR}/scripts/test_ci_boot_backend_instance.sh"
  bash "${ROOT_DIR}/scripts/test_ci_run_backend_e2e.sh"
  bash "${ROOT_DIR}/scripts/test_ci_run_frontend_e2e.sh"
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
