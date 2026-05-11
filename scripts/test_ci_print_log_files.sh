#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="${ROOT_DIR}/scripts/ci_print_log_files.sh"
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

  echo "aaa" > "${TMP_DIR}/a.log"

  expect_fail bash "${SCRIPT_PATH}"
  expect_fail bash "${SCRIPT_PATH}" --unknown x

  expect_pass bash "${SCRIPT_PATH}" \
    --title "demo logs" \
    --file "${TMP_DIR}/a.log" \
    --file "${TMP_DIR}/missing.log" > "${TMP_DIR}/out.txt"

  assert_contains "===== demo logs =====" "${TMP_DIR}/out.txt"
  assert_contains "===== ${TMP_DIR}/a.log =====" "${TMP_DIR}/out.txt"
  assert_contains "aaa" "${TMP_DIR}/out.txt"
  assert_contains "===== ${TMP_DIR}/missing.log =====" "${TMP_DIR}/out.txt"
  assert_contains "(missing)" "${TMP_DIR}/out.txt"

  echo "ci_print_log_files tests passed"
}

run_tests
