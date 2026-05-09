#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="${ROOT_DIR}/scripts/ci_run_frontend_e2e.sh"
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
  expect_fail bash "${SCRIPT_PATH}" --phase unknown --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001

  expect_pass bash "${SCRIPT_PATH}" --phase smoke --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001 --dry-run > "${TMP_DIR}/smoke.out"
  assert_contains "npm run test:e2e:smoke:matrix" "${TMP_DIR}/smoke.out"

  expect_pass bash "${SCRIPT_PATH}" --phase full --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001 --dry-run > "${TMP_DIR}/full.out"
  assert_contains "npm run test:e2e" "${TMP_DIR}/full.out"

  expect_pass bash "${SCRIPT_PATH}" --phase rerun-last-failed --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001 --dry-run > "${TMP_DIR}/rerun.out"
  assert_contains "--last-failed --output=test-results/last-failed" "${TMP_DIR}/rerun.out"

  echo "ci_run_frontend_e2e tests passed"
}

run_tests
