#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="${ROOT_DIR}/scripts/ci_run_backend_e2e.sh"
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
  expect_fail bash "${SCRIPT_PATH}" --phase unknown --base-url http://127.0.0.1:8000

  expect_pass bash "${SCRIPT_PATH}" --phase main --base-url http://127.0.0.1:8000 --log-dir "${TMP_DIR}" --dry-run > "${TMP_DIR}/main.out"
  assert_contains "e2e_baseline.py --base-url http://127.0.0.1:8000" "${TMP_DIR}/main.out"
  assert_contains "e2e_main_path.py --base-url http://127.0.0.1:8000" "${TMP_DIR}/main.out"
  assert_contains "e2e_export_consistency.py --base-url http://127.0.0.1:8000" "${TMP_DIR}/main.out"
  assert_contains "e2e_task_cancel_timeout.py --base-url http://127.0.0.1:8000 --skip-timeout" "${TMP_DIR}/main.out"

  expect_pass bash "${SCRIPT_PATH}" --phase timeout --base-url http://127.0.0.1:8010 --log-dir "${TMP_DIR}" --dry-run > "${TMP_DIR}/timeout.out"
  assert_contains "--cancel-prompt-words 180000 --timeout-prompt-words 250000" "${TMP_DIR}/timeout.out"

  echo "ci_run_backend_e2e tests passed"
}

run_tests
