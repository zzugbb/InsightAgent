#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_rerun_frontend_e2e_diagnostics.sh"
TMP_DIR=""

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
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR:-}"' EXIT

  frontend_dir="${TMP_DIR}/frontend"
  mkdir -p "${frontend_dir}/test-results"
  markdown_out="${TMP_DIR}/rerun.md"
  json_out="${TMP_DIR}/rerun.json"
  summary_file="${TMP_DIR}/step-summary.md"

  bash "${SCRIPT}" \
    --api-base-url http://127.0.0.1:8000 \
    --frontend-base-url http://127.0.0.1:3001 \
    --frontend-dir "${frontend_dir}" \
    --markdown-out "${markdown_out}" \
    --json-out "${json_out}" \
    --summary-file "${summary_file}"

  assert_contains "mode: skipped" "${markdown_out}"
  assert_contains '"mode": "skipped"' "${json_out}"
  assert_contains "diagnostic_gate_result: PASS" "${markdown_out}"
  assert_contains "### frontend-e2e diagnostic rerun (chromium)" "${summary_file}"

  printf '%s\n' '{"status":"failed","failedTests":["e2e/example.spec.ts"]}' > "${frontend_dir}/test-results/.last-run.json"

  bash "${SCRIPT}" \
    --api-base-url http://127.0.0.1:8000 \
    --frontend-base-url http://127.0.0.1:3001 \
    --frontend-dir "${frontend_dir}" \
    --markdown-out "${markdown_out}" \
    --json-out "${json_out}" \
    --log-out "${TMP_DIR}/rerun.log" \
    --summary-file "${summary_file}"

  assert_contains "mode: last-failed" "${markdown_out}"
  assert_contains "playwright_exit_code: 254" "${markdown_out}"
  assert_contains "diagnostic_gate_result: FAIL" "${markdown_out}"
  assert_contains '"diagnostic_gate_result": "FAIL"' "${json_out}"

  echo "ci_rerun_frontend_e2e_diagnostics tests passed"
}

main "$@"
