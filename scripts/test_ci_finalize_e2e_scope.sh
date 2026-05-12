#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="${ROOT_DIR}/scripts/ci_finalize_e2e_scope.sh"
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

assert_file() {
  if [ ! -e "$1" ]; then
    echo "expected path not found: $1" >&2
    exit 1
  fi
}

run_tests() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR}"' EXIT

  mkdir -p "${TMP_DIR}/frontend-results"
  cat > "${TMP_DIR}/backend.log" <<'LOG'
[1/2] task export json/markdown consistency + download
  - OK: task export consistency
[2/2] session export json/markdown consistency + download
  - OK: session export consistency
E2E export consistency passed: /tmp/foo
shared-rag role semantics remain compatible with export flow
cross-user export isolation checks
export not-found responses
LOG

  echo "sample-artifact" > "${TMP_DIR}/artifact.txt"
  cat > "${TMP_DIR}/artifacts.list" <<LIST
${TMP_DIR}/artifact.txt
${TMP_DIR}/missing.txt
LIST

  expect_fail bash "${SCRIPT_PATH}"
  expect_fail bash "${SCRIPT_PATH}" --scope backend --event-name push --ref refs/heads/main --default-level p0 --main-push-level any

  expect_pass bash "${SCRIPT_PATH}" \
    --scope backend \
    --event-name workflow_dispatch \
    --ref refs/heads/test \
    --default-level p0 \
    --main-push-level any \
    --dispatch-override none \
    --summary-file "${TMP_DIR}/backend-summary.md" \
    --source-path "${TMP_DIR}/backend.log" \
    --diagnostics-markdown-out "${TMP_DIR}/backend-diag.md" \
    --diagnostics-json-out "${TMP_DIR}/backend-diag.json" \
    --guard-markdown-out "${TMP_DIR}/backend-guard.md" \
    --guard-json-out "${TMP_DIR}/backend-guard.json" \
    --overview-markdown-out "${TMP_DIR}/backend-overview.md" \
    --overview-json-out "${TMP_DIR}/backend-overview.json" \
    --artifacts-list-file "${TMP_DIR}/artifacts.list" \
    --artifacts-stage-dir "${TMP_DIR}/backend-stage" \
    --artifact-name "backend-custom-artifact" \
    --github-output-file "${TMP_DIR}/backend.ghout" \
    --quiet > "${TMP_DIR}/backend.out"

  assert_file "${TMP_DIR}/backend-stage/_manifest.txt"
  assert_contains "artifact_name=backend-custom-artifact" "${TMP_DIR}/backend.out"
  assert_contains "artifacts_stage_dir=${TMP_DIR}/backend-stage" "${TMP_DIR}/backend.out"
  assert_contains "artifact_included_count=1" "${TMP_DIR}/backend.out"
  assert_contains "artifact_missing_count=1" "${TMP_DIR}/backend.out"
  assert_contains "artifact_min_included_count=1" "${TMP_DIR}/backend.out"
  assert_contains "artifact_manifest=${TMP_DIR}/backend-stage/_manifest.txt" "${TMP_DIR}/backend.out"
  assert_contains "min_included_count: 1" "${TMP_DIR}/backend-summary.md"
  assert_contains "artifact_name=backend-custom-artifact" "${TMP_DIR}/backend.ghout"
  assert_contains "artifacts_stage_dir=${TMP_DIR}/backend-stage" "${TMP_DIR}/backend.ghout"
  assert_contains "scope=backend" "${TMP_DIR}/backend.ghout"
  assert_contains "artifact_included_count=1" "${TMP_DIR}/backend.ghout"
  assert_contains "artifact_missing_count=1" "${TMP_DIR}/backend.ghout"
  assert_contains "artifact_min_included_count=1" "${TMP_DIR}/backend.ghout"
  assert_contains "artifact_manifest=${TMP_DIR}/backend-stage/_manifest.txt" "${TMP_DIR}/backend.ghout"
  assert_contains "### backend-e2e export consistency" "${TMP_DIR}/backend-summary.md"
  assert_contains "### backend-e2e export diagnostics guard" "${TMP_DIR}/backend-summary.md"
  assert_contains "### backend-e2e artifact stage" "${TMP_DIR}/backend-summary.md"
  assert_contains "- included_count: 1" "${TMP_DIR}/backend-summary.md"
  assert_contains "- missing_count: 1" "${TMP_DIR}/backend-summary.md"

  expect_pass bash "${SCRIPT_PATH}" \
    --scope frontend \
    --event-name pull_request \
    --ref refs/pull/123/merge \
    --default-level p0 \
    --main-push-level any \
    --dispatch-override none \
    --summary-file "${TMP_DIR}/frontend-summary.md" \
    --source-path "${TMP_DIR}/frontend-results" \
    --diagnostics-markdown-out "${TMP_DIR}/frontend-diag.md" \
    --diagnostics-json-out "${TMP_DIR}/frontend-diag.json" \
    --guard-markdown-out "${TMP_DIR}/frontend-guard.md" \
    --guard-json-out "${TMP_DIR}/frontend-guard.json" \
    --overview-markdown-out "${TMP_DIR}/frontend-overview.md" \
    --overview-json-out "${TMP_DIR}/frontend-overview.json" \
    --artifacts-list-file "${TMP_DIR}/artifacts.list" \
    --artifacts-stage-dir "${TMP_DIR}/frontend-stage" \
    --artifact-name "frontend-custom-artifact" \
    --github-output-file "${TMP_DIR}/frontend.ghout" \
    --quiet > "${TMP_DIR}/frontend.out"

  assert_file "${TMP_DIR}/frontend-stage/_manifest.txt"
  assert_contains "artifact_name=frontend-custom-artifact" "${TMP_DIR}/frontend.out"
  assert_contains "artifacts_stage_dir=${TMP_DIR}/frontend-stage" "${TMP_DIR}/frontend.out"
  assert_contains "artifact_included_count=1" "${TMP_DIR}/frontend.out"
  assert_contains "artifact_missing_count=1" "${TMP_DIR}/frontend.out"
  assert_contains "artifact_min_included_count=1" "${TMP_DIR}/frontend.out"
  assert_contains "artifact_manifest=${TMP_DIR}/frontend-stage/_manifest.txt" "${TMP_DIR}/frontend.out"
  assert_contains "min_included_count: 1" "${TMP_DIR}/frontend-summary.md"
  assert_contains "artifact_name=frontend-custom-artifact" "${TMP_DIR}/frontend.ghout"
  assert_contains "artifacts_stage_dir=${TMP_DIR}/frontend-stage" "${TMP_DIR}/frontend.ghout"
  assert_contains "scope=frontend" "${TMP_DIR}/frontend.ghout"
  assert_contains "artifact_included_count=1" "${TMP_DIR}/frontend.ghout"
  assert_contains "artifact_missing_count=1" "${TMP_DIR}/frontend.ghout"
  assert_contains "artifact_min_included_count=1" "${TMP_DIR}/frontend.ghout"
  assert_contains "artifact_manifest=${TMP_DIR}/frontend-stage/_manifest.txt" "${TMP_DIR}/frontend.ghout"
  assert_contains "### frontend-e2e export diagnostics" "${TMP_DIR}/frontend-summary.md"
  assert_contains "### frontend-e2e export diagnostics guard" "${TMP_DIR}/frontend-summary.md"
  assert_contains "### frontend-e2e artifact stage" "${TMP_DIR}/frontend-summary.md"
  assert_contains "- included_count: 1" "${TMP_DIR}/frontend-summary.md"
  assert_contains "- missing_count: 1" "${TMP_DIR}/frontend-summary.md"

  expect_pass bash "${SCRIPT_PATH}" \
    --scope frontend \
    --event-name push \
    --ref refs/heads/main \
    --default-level p0 \
    --main-push-level any \
    --summary-file "${TMP_DIR}/dry-summary.md" \
    --dry-run > "${TMP_DIR}/dry.out"
  assert_contains "[dry-run] bash scripts/ci_export_diag_flow.sh --scope frontend" "${TMP_DIR}/dry.out"
  assert_contains "[dry-run] bash scripts/ci_stage_artifacts.sh --list-file scripts/ci_artifacts_frontend.txt" "${TMP_DIR}/dry.out"
  assert_contains "[dry-run] artifact_name=playwright-report" "${TMP_DIR}/dry.out"
  assert_contains "[dry-run] artifacts_stage_dir=/tmp/frontend-e2e-artifacts-stage" "${TMP_DIR}/dry.out"
  assert_contains "[dry-run] min_included_count=1" "${TMP_DIR}/dry.out"

  echo "ci_finalize_e2e_scope tests passed"
}

run_tests
