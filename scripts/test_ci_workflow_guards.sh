#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_WORKFLOW="${ROOT_DIR}/.github/workflows/backend-e2e.yml"
FRONTEND_WORKFLOW="${ROOT_DIR}/.github/workflows/frontend-e2e.yml"
RELEASE_GATE_WORKFLOW="${ROOT_DIR}/.github/workflows/release-gate.yml"
BACKEND_ARTIFACTS_LIST="${ROOT_DIR}/scripts/ci_artifacts_backend.txt"

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
  assert_contains "BACKEND_ARTIFACT_STAGE_STRICT_LEVEL_MAIN_PUSH: \"fail-on-missing\"" "${BACKEND_WORKFLOW}"
  assert_contains "FRONTEND_ARTIFACT_STAGE_STRICT_LEVEL_MAIN_PUSH: \"fail-on-missing\"" "${FRONTEND_WORKFLOW}"
  assert_contains "--scope backend \\" "${BACKEND_WORKFLOW}"
  assert_contains "--scope frontend \\" "${FRONTEND_WORKFLOW}"
  assert_contains '--main-push-level "${BACKEND_ARTIFACT_STAGE_STRICT_LEVEL_MAIN_PUSH}" \' "${BACKEND_WORKFLOW}"
  assert_contains '--main-push-level "${FRONTEND_ARTIFACT_STAGE_STRICT_LEVEL_MAIN_PUSH}" \' "${FRONTEND_WORKFLOW}"
  assert_contains "TASK_QUEUE_MAX_CONCURRENT: \"1\"" "${BACKEND_WORKFLOW}"
  assert_contains "TASK_QUEUE_POLL_INTERVAL_SEC: \"0.1\"" "${BACKEND_WORKFLOW}"
  assert_contains "Start backend on :8011 (queue concurrency=1)" "${BACKEND_WORKFLOW}"
  assert_contains "Run queue e2e on :8011" "${BACKEND_WORKFLOW}"
  assert_contains "bash scripts/ci_run_backend_e2e.sh \\" "${BACKEND_WORKFLOW}"
  assert_contains "--phase queue \\" "${BACKEND_WORKFLOW}"
  assert_contains "--base-url http://127.0.0.1:8011 \\" "${BACKEND_WORKFLOW}"
  assert_contains "/tmp/backend-8011.log" "${BACKEND_ARTIFACTS_LIST}"
  assert_contains "/tmp/health-8011.json" "${BACKEND_ARTIFACTS_LIST}"
  assert_contains "/tmp/e2e-queue-8011.log" "${BACKEND_ARTIFACTS_LIST}"
  assert_not_contains "/tmp/backend-e2e-diagnostics.txt" "${BACKEND_ARTIFACTS_LIST}"
  assert_contains "TASK_QUEUE_MAX_CONCURRENT: \"1\"" "${FRONTEND_WORKFLOW}"
  assert_contains "TASK_QUEUE_POLL_INTERVAL_SEC: \"0.1\"" "${FRONTEND_WORKFLOW}"
  assert_contains "Start backend on :8011 for frontend queue e2e" "${FRONTEND_WORKFLOW}"
  assert_contains "Run frontend queue e2e" "${FRONTEND_WORKFLOW}"
  assert_contains "bash scripts/ci_run_frontend_e2e.sh \\" "${FRONTEND_WORKFLOW}"
  assert_contains "--phase queue \\" "${FRONTEND_WORKFLOW}"
  assert_contains "--api-base-url http://127.0.0.1:8011 \\" "${FRONTEND_WORKFLOW}"
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
  assert_contains "run: cd frontend && npx playwright install-deps chromium firefox webkit" "${FRONTEND_WORKFLOW}"
  assert_contains "run: cd frontend && npx playwright install chromium firefox webkit" "${FRONTEND_WORKFLOW}"
  assert_not_contains "run: cd frontend && npx playwright install --with-deps chromium firefox webkit" "${FRONTEND_WORKFLOW}"
  assert_contains "name: release-gate" "${RELEASE_GATE_WORKFLOW}"
  assert_contains "release_gate_phase:" "${RELEASE_GATE_WORKFLOW}"
  assert_contains "default: auto" "${RELEASE_GATE_WORKFLOW}"
  assert_contains "RELEASE_GATE_PHASE: \${{ github.event.inputs.release_gate_phase || 'auto' }}" "${RELEASE_GATE_WORKFLOW}"
  assert_contains "python-version: \"3.14\"" "${RELEASE_GATE_WORKFLOW}"
  assert_contains "node-version: \"24\"" "${RELEASE_GATE_WORKFLOW}"
  assert_contains "npm --prefix frontend ci" "${RELEASE_GATE_WORKFLOW}"
  assert_contains 'bash scripts/ci_run_release_gate.sh --phase "${RELEASE_GATE_PHASE}" \' "${RELEASE_GATE_WORKFLOW}"
  assert_contains '--repo-root "${{ github.workspace }}" \' "${RELEASE_GATE_WORKFLOW}"
  assert_contains '--event-name "${GITHUB_EVENT_NAME}" \' "${RELEASE_GATE_WORKFLOW}"
  assert_contains "--base-sha \"\${{ github.event.pull_request.base.sha || '' }}\" \\" "${RELEASE_GATE_WORKFLOW}"
  assert_contains '--head-sha "${{ github.sha }}" \' "${RELEASE_GATE_WORKFLOW}"
  assert_contains '--ref "${GITHUB_REF}" \' "${RELEASE_GATE_WORKFLOW}"
  assert_contains '--summary-file "$GITHUB_STEP_SUMMARY" \' "${RELEASE_GATE_WORKFLOW}"
  assert_contains "--json-summary-file /tmp/release-gate-summary.json" "${RELEASE_GATE_WORKFLOW}"
  assert_contains "name: release-gate-summary" "${RELEASE_GATE_WORKFLOW}"
  assert_contains "path: /tmp/release-gate-summary.json" "${RELEASE_GATE_WORKFLOW}"
  assert_not_contains "ci_run_backend_e2e.sh" "${RELEASE_GATE_WORKFLOW}"
  assert_not_contains "ci_run_frontend_e2e.sh" "${RELEASE_GATE_WORKFLOW}"

  echo "ci_workflow_guards tests passed"
}

main "$@"
