#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_WORKFLOW="${ROOT_DIR}/.github/workflows/backend-e2e.yml"
FRONTEND_WORKFLOW="${ROOT_DIR}/.github/workflows/frontend-e2e.yml"

assert_contains() {
  local expected="$1"
  local file="$2"
  if ! grep -Fq -- "${expected}" "${file}"; then
    echo "expected '${expected}' in ${file}" >&2
    cat "${file}" >&2 || true
    exit 1
  fi
}

main() {
  assert_contains "if: always() && steps.finalize_backend.conclusion == 'success'" "${BACKEND_WORKFLOW}"
  assert_contains "if: always() && steps.finalize_frontend.conclusion == 'success'" "${FRONTEND_WORKFLOW}"
  assert_contains "path: \${{ steps.finalize_backend.outputs.artifacts_stage_dir }}" "${BACKEND_WORKFLOW}"
  assert_contains "path: \${{ steps.finalize_frontend.outputs.artifacts_stage_dir }}" "${FRONTEND_WORKFLOW}"
  assert_contains "fetch-depth: 0" "${BACKEND_WORKFLOW}"
  assert_contains "fetch-depth: 0" "${FRONTEND_WORKFLOW}"
  assert_contains "bash scripts/ci_resolve_artifact_stage_scope_config.sh \\" "${BACKEND_WORKFLOW}"
  assert_contains "bash scripts/ci_resolve_artifact_stage_scope_config.sh \\" "${FRONTEND_WORKFLOW}"
  assert_contains "bash scripts/ci_load_artifact_stage_scope_config.sh \\" "${BACKEND_WORKFLOW}"
  assert_contains "bash scripts/ci_load_artifact_stage_scope_config.sh \\" "${FRONTEND_WORKFLOW}"
  assert_contains 'source "${artifact_scope_env_file}"' "${BACKEND_WORKFLOW}"
  assert_contains 'source "${artifact_scope_env_file}"' "${FRONTEND_WORKFLOW}"
  assert_contains "ci_collect_changed_files.sh" "${BACKEND_WORKFLOW}"
  assert_contains "ci_collect_changed_files.sh" "${FRONTEND_WORKFLOW}"
  assert_contains "--scope backend \\" "${BACKEND_WORKFLOW}"
  assert_contains "--scope frontend \\" "${FRONTEND_WORKFLOW}"
  assert_contains '--pr-ref-regex "${ARTIFACT_PR_REF_REGEX}"' "${BACKEND_WORKFLOW}"
  assert_contains '--pr-ref-regex "${ARTIFACT_PR_REF_REGEX}"' "${FRONTEND_WORKFLOW}"
  assert_contains '--label "${ARTIFACT_GUARD_LABEL}"' "${BACKEND_WORKFLOW}"
  assert_contains '--label "${ARTIFACT_GUARD_LABEL}"' "${FRONTEND_WORKFLOW}"
  assert_contains 'echo "${ARTIFACT_SUMMARY_HEADING}"' "${BACKEND_WORKFLOW}"
  assert_contains 'echo "${ARTIFACT_SUMMARY_HEADING}"' "${FRONTEND_WORKFLOW}"

  echo "ci_workflow_guards tests passed"
}

main "$@"
