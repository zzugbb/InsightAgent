#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="${ROOT_DIR}/scripts/ci_finalize_e2e_for_workflow.sh"
TMP_DIR=""

expect_pass() {
  if ! "$@"; then
    echo "expected pass but failed: $*" >&2
    exit 1
  fi
}

expect_fail() {
  if "$@" >/dev/null 2>&1; then
    echo "expected fail but passed: $*" >&2
    exit 1
  fi
}

assert_contains() {
  local expected="$1"
  local file="$2"
  if ! grep -Fq -- "${expected}" "${file}"; then
    echo "expected '${expected}' in ${file}" >&2
    cat "${file}" >&2 || true
    exit 1
  fi
}

run_tests() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR}"' EXIT

  expect_fail bash "${SCRIPT_PATH}"
  expect_fail env -u GITHUB_EVENT_NAME -u GITHUB_REF \
    bash "${SCRIPT_PATH}" --scope backend --summary-file "${TMP_DIR}/missing-event.md"

  expect_pass env \
    GITHUB_EVENT_NAME=workflow_dispatch \
    GITHUB_REF=refs/heads/test \
    BACKEND_EXPORT_DIAG_STRICT_LEVEL_DEFAULT=p0 \
    BACKEND_EXPORT_DIAG_STRICT_LEVEL_MAIN_PUSH=any \
    bash "${SCRIPT_PATH}" \
      --scope backend \
      --summary-file "${TMP_DIR}/backend-summary.md" \
      --dry-run > "${TMP_DIR}/backend.out"

  assert_contains "[dry-run] bash scripts/ci_export_diag_flow.sh --scope backend" "${TMP_DIR}/backend.out"
  assert_contains "--default-level p0 --main-push-level any" "${TMP_DIR}/backend.out"
  assert_contains "[dry-run] artifact_name=backend-e2e-artifacts" "${TMP_DIR}/backend.out"

  expect_pass env \
    GITHUB_EVENT_NAME=pull_request \
    GITHUB_REF=refs/pull/12/merge \
    FRONTEND_EXPORT_DIAG_STRICT_LEVEL_DEFAULT=p0 \
    FRONTEND_EXPORT_DIAG_STRICT_LEVEL_MAIN_PUSH=any \
    FRONTEND_ARTIFACT_STAGE_MIN_INCLUDED_COUNT=2 \
    GITHUB_RUN_ID=123456 \
    GITHUB_RUN_ATTEMPT=7 \
    bash "${SCRIPT_PATH}" \
      --scope frontend \
      --summary-file "${TMP_DIR}/frontend-min-count-summary.md" \
      --dry-run > "${TMP_DIR}/frontend-min-count.out"

  assert_contains "[dry-run] min_included_count=2" "${TMP_DIR}/frontend-min-count.out"

  expect_pass env \
    GITHUB_EVENT_NAME=pull_request \
    GITHUB_REF=refs/pull/12/merge \
    FRONTEND_EXPORT_DIAG_STRICT_LEVEL_DEFAULT=p0 \
    FRONTEND_EXPORT_DIAG_STRICT_LEVEL_MAIN_PUSH=any \
    GITHUB_RUN_ID=123456 \
    GITHUB_RUN_ATTEMPT=7 \
    bash "${SCRIPT_PATH}" \
      --scope frontend \
      --summary-file "${TMP_DIR}/frontend-summary.md" \
      --dry-run > "${TMP_DIR}/frontend.out"

  assert_contains "[dry-run] bash scripts/ci_export_diag_flow.sh --scope frontend" "${TMP_DIR}/frontend.out"
  assert_contains "--default-level p0 --main-push-level any" "${TMP_DIR}/frontend.out"
  assert_contains "[dry-run] artifact_name=playwright-report-123456-7" "${TMP_DIR}/frontend.out"

  expect_pass env \
    GITHUB_EVENT_NAME=push \
    GITHUB_REF=refs/heads/main \
    FRONTEND_EXPORT_DIAG_STRICT_LEVEL_DEFAULT=p0 \
    FRONTEND_EXPORT_DIAG_STRICT_LEVEL_MAIN_PUSH=any \
    bash "${SCRIPT_PATH}" \
      --scope frontend \
      --summary-file "${TMP_DIR}/frontend-summary-override.md" \
      --default-level any \
      --main-push-level none \
      --artifact-name "frontend-artifact-manual" \
      --dispatch-override none \
      --dry-run > "${TMP_DIR}/frontend-override.out"

  assert_contains "--default-level any --main-push-level none --dispatch-override none" "${TMP_DIR}/frontend-override.out"
  assert_contains "[dry-run] artifact_name=frontend-artifact-manual" "${TMP_DIR}/frontend-override.out"

  echo "ci_finalize_e2e_for_workflow tests passed"
}

run_tests
