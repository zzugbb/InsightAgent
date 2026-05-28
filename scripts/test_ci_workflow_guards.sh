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

assert_not_contains() {
  local unexpected="$1"
  local file="$2"
  if grep -Fq -- "${unexpected}" "${file}"; then
    echo "did not expect '${unexpected}' in ${file}" >&2
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
  assert_contains "bash scripts/ci_run_artifact_stage_guard.sh \\" "${BACKEND_WORKFLOW}"
  assert_contains "bash scripts/ci_run_artifact_stage_guard.sh \\" "${FRONTEND_WORKFLOW}"
  assert_contains "--scope backend \\" "${BACKEND_WORKFLOW}"
  assert_contains "--scope frontend \\" "${FRONTEND_WORKFLOW}"
  assert_contains '--dispatch-override "${artifact_dispatch_override:-auto}"' "${BACKEND_WORKFLOW}"
  assert_contains '--dispatch-override "${artifact_dispatch_override:-auto}"' "${FRONTEND_WORKFLOW}"
  assert_not_contains "--guard-markdown-out" "${BACKEND_WORKFLOW}"
  assert_not_contains "--guard-json-out" "${BACKEND_WORKFLOW}"
  assert_not_contains "--guard-markdown-out" "${FRONTEND_WORKFLOW}"
  assert_not_contains "--guard-json-out" "${FRONTEND_WORKFLOW}"
  assert_contains 'bash scripts/ci_write_skipped_artifact_guard_summary.sh \' "${BACKEND_WORKFLOW}"
  assert_contains 'bash scripts/ci_write_skipped_artifact_guard_summary.sh \' "${FRONTEND_WORKFLOW}"
  assert_contains '--reason "finalize_backend step did not succeed"' "${BACKEND_WORKFLOW}"
  assert_contains '--reason "finalize_frontend step did not succeed"' "${FRONTEND_WORKFLOW}"
  assert_contains "uses: actions/cache@v4" "${FRONTEND_WORKFLOW}"
  assert_contains "path: ~/.cache/ms-playwright" "${FRONTEND_WORKFLOW}"
  assert_contains "key: playwright-\${{ runner.os }}-" "${FRONTEND_WORKFLOW}"
  assert_contains "run: cd frontend && npx playwright install chromium firefox webkit" "${FRONTEND_WORKFLOW}"
  assert_not_contains "run: cd frontend && npx playwright install --with-deps chromium firefox webkit" "${FRONTEND_WORKFLOW}"

  echo "ci_workflow_guards tests passed"
}

main "$@"
