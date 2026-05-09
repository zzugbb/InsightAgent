#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="${ROOT_DIR}/scripts/ci_collect_backend_failure_diagnostics.sh"
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

  local output_file="${TMP_DIR}/diag.txt"
  local export_log="${TMP_DIR}/export.log"
  echo "line-1" > "${export_log}"
  echo "line-2" >> "${export_log}"

  expect_fail bash "${SCRIPT_PATH}"

  expect_pass bash "${SCRIPT_PATH}" \
    --output-file "${output_file}" \
    --primary-health-url "http://127.0.0.1:65530/health" \
    --secondary-health-url "http://127.0.0.1:65531/health" \
    --export-log-file "${export_log}" \
    --export-log-tail-lines 1 \
    --process-pattern "definitely-no-match-process" > "${TMP_DIR}/stdout.txt"

  assert_contains "output_file=${output_file}" "${TMP_DIR}/stdout.txt"
  assert_contains "===== date =====" "${output_file}"
  assert_contains "===== ps -ef (definitely-no-match-process) =====" "${output_file}"
  assert_contains "===== health primary =====" "${output_file}"
  assert_contains "===== health secondary =====" "${output_file}"
  assert_contains "===== export consistency tail =====" "${output_file}"
  assert_contains "line-2" "${output_file}"

  echo "ci_collect_backend_failure_diagnostics tests passed"
}

run_tests
