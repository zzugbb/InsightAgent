#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
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

setup_fixture_non_export_edge_case() {
  local root="$1"

  mkdir -p "${root}/workbench-edge-cases-queue-018a4-sition-and-can-be-cancelled-chromium"
  cat > "${root}/workbench-edge-cases-queue-018a4-sition-and-can-be-cancelled-chromium/error-context.md" <<'CTX'
Timeout waiting for queued phase
response headers:
content-type: application/json; charset=utf-8
CTX
}

main() {
  TMP_ROOT="$(mktemp -d)"
  root_results_marker_dir="${ROOT_DIR}/frontend/test-results/codex-export-diagnostics-cwd-test"
  trap 'rm -rf "${TMP_ROOT:-}" "${root_results_marker_dir}"' EXIT

  # scenario 1: all hints present, expect zero alerts
  local ok_dir="${TMP_ROOT}/ok-results"
  mkdir -p "${ok_dir}"
  setup_fixture_success "${ok_dir}"

  local ok_out="${TMP_ROOT}/ok.out"
  local ok_json="${TMP_ROOT}/ok.json"
  bash "${DIAG_SCRIPT}" "${ok_dir}" "${ok_json}" > "${ok_out}"

  assert_contains "${ok_out}" "- total_alerts: 0 (all counters within expected range)"
  assert_contains "${ok_out}" "- context_files_detected: 1"
  assert_contains "${ok_out}" "- shared_scope: workbench-main-path-shared-kb contexts=1, shared_permission_semantic_ok=3 (expected: >=1 (when shared-kb error-context files exist))"
  assert_contains "${ok_json}" "\"total\": 0"
  assert_contains "${ok_json}" "\"shared_permission_semantic_ok\": 3"

  # scenario 1b: non-export edge-case failures should not trip export diagnostics
  local queue_dir="${TMP_ROOT}/queue-results"
  mkdir -p "${queue_dir}"
  setup_fixture_non_export_edge_case "${queue_dir}"

  local queue_out="${TMP_ROOT}/queue.out"
  local queue_json="${TMP_ROOT}/queue.json"
  bash "${DIAG_SCRIPT}" "${queue_dir}" "${queue_json}" > "${queue_out}"

  assert_contains "${queue_out}" "No workbench-edge-cases export error-context files found."
  assert_contains "${queue_out}" "- total_alerts: 0 (all counters within expected range)"
  assert_contains "${queue_json}" "\"context_files_detected\": 0"

  # scenario 2: missing API hint in main-path, expect P0/P1 alerts
  local bad_dir="${TMP_ROOT}/bad-results"
  mkdir -p "${bad_dir}"
  setup_fixture_failure "${bad_dir}"

  local bad_out="${TMP_ROOT}/bad.out"
  local bad_json="${TMP_ROOT}/bad.json"
  bash "${DIAG_SCRIPT}" "${bad_dir}" "${bad_json}" > "${bad_out}"

  assert_contains "${bad_out}" "- total_alerts: 2"
  assert_contains "${bad_out}" "- [P0][workbench-main-path] export_api_path_hints expected >=1 when error-context exists, got 0"
  assert_contains "${bad_out}" "- [P1][workbench-main-path] export_api_path_hints expected >=1, got 0"
  assert_contains "${bad_json}" "\"total\": 2"
  assert_contains "${bad_json}" "\"p0\": 1"
  assert_contains "${bad_json}" "\"p1\": 1"

  mkdir -p "${root_results_marker_dir}/workbench-main-path-export"
  cat > "${root_results_marker_dir}/workbench-main-path-export/error-context.md" <<'CTX'
waitForEvent("download")
content-type: application/json
GET /api/tasks/default/export/json
CTX

  local default_out="${TMP_ROOT}/default.out"
  bash -c "cd '${TMP_ROOT}' && bash '${DIAG_SCRIPT}'" > "${default_out}"
  assert_contains "${default_out}" "- context_files_detected: 1"

  echo "ci_export_diagnostics fixture tests passed"
}

main "$@"
