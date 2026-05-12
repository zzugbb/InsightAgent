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

  echo "ci_workflow_guards tests passed"
}

main "$@"
