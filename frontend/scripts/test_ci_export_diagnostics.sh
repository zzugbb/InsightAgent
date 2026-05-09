#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIAG_SCRIPT="${SCRIPT_DIR}/ci_export_diagnostics.sh"
TMP_ROOT=""

assert_contains() {
  local file="$1"
  local expected="$2"
  if ! grep -Fq -- "${expected}" "${file}"; then
    echo "assertion failed: expected line not found"
    echo "expected: ${expected}"
    echo "file: ${file}"
    exit 1
  fi
}

setup_fixture_success() {
  local root="$1"

  mkdir -p "${root}/workbench-main-path-export/hints"
  cat > "${root}/workbench-main-path-export/hints/error-context.md" <<'CTX'
waitForEvent("download")
content-type: application/json
GET /api/tasks/abc/export/json
CTX

  mkdir -p "${root}/workbench-main-path-shared-kb-actions-disabled/spec"
  cat > "${root}/workbench-main-path-shared-kb-actions-disabled/spec/error-context.md" <<'CTX'
shared-kb-actions-disabled
kb-governance-action-clear
toBeDisabled
CTX

  mkdir -p "${root}/workbench-edge-cases-export/spec"
  cat > "${root}/workbench-edge-cases-export/spec/error-context.md" <<'CTX'
suggestedFilename
action returned 404 not found
GET /api/sessions/abc/export/markdown
text/markdown
CTX
}

setup_fixture_failure() {
  local root="$1"

  mkdir -p "${root}/workbench-main-path-export/missing-api"
  cat > "${root}/workbench-main-path-export/missing-api/error-context.md" <<'CTX'
waitForEvent("download")
content-disposition: attachment;
CTX
}

main() {
  TMP_ROOT="$(mktemp -d)"
  trap 'rm -rf "${TMP_ROOT:-}"' EXIT

  # scenario 1: all hints present, expect zero alerts
  local ok_dir="${TMP_ROOT}/ok-results"
  mkdir -p "${ok_dir}"
  setup_fixture_success "${ok_dir}"

  local ok_out="${TMP_ROOT}/ok.out"
  bash "${DIAG_SCRIPT}" "${ok_dir}" > "${ok_out}"

  assert_contains "${ok_out}" "- total_alerts: 0 (all counters within expected range)"
  assert_contains "${ok_out}" "- context_files_detected: 1"
  assert_contains "${ok_out}" "- shared_scope: workbench-main-path-shared-kb contexts=1, shared_permission_semantic_ok=3 (expected: >=1 (when shared-kb error-context files exist))"

  # scenario 2: missing API hint in main-path, expect P0/P1 alerts
  local bad_dir="${TMP_ROOT}/bad-results"
  mkdir -p "${bad_dir}"
  setup_fixture_failure "${bad_dir}"

  local bad_out="${TMP_ROOT}/bad.out"
  bash "${DIAG_SCRIPT}" "${bad_dir}" > "${bad_out}"

  assert_contains "${bad_out}" "- total_alerts: 2"
  assert_contains "${bad_out}" "- [P0][workbench-main-path] export_api_path_hints expected >=1 when error-context exists, got 0"
  assert_contains "${bad_out}" "- [P1][workbench-main-path] export_api_path_hints expected >=1, got 0"

  echo "ci_export_diagnostics fixture tests passed"
}

main "$@"
