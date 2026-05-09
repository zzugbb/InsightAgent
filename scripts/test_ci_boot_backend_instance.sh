#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="${ROOT_DIR}/scripts/ci_boot_backend_instance.sh"
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
  expect_fail bash "${SCRIPT_PATH}" --port 8000

  expect_pass bash "${SCRIPT_PATH}" \
    --port 8000 \
    --log-file "${TMP_DIR}/backend.log" \
    --pid-file "${TMP_DIR}/backend.pid" \
    --failure-message "custom-fail-message" \
    --dry-run > "${TMP_DIR}/dry-run.out"

  assert_contains "ci_start_bg_process.sh --log-file ${TMP_DIR}/backend.log --pid-file ${TMP_DIR}/backend.pid" "${TMP_DIR}/dry-run.out"
  assert_contains "ci_wait_http_status.sh --url http://127.0.0.1:8000/health --output-file /tmp/health-8000.json" "${TMP_DIR}/dry-run.out"
  assert_contains "--failure-message custom-fail-message" "${TMP_DIR}/dry-run.out"

  expect_pass bash "${SCRIPT_PATH}" \
    --host 127.0.0.1 \
    --port 8010 \
    --health-path /health \
    --log-file "${TMP_DIR}/backend2.log" \
    --attempts 5 \
    --interval-sec 2 \
    --dry-run > "${TMP_DIR}/dry-run-2.out"
  assert_contains "--attempts 5 --interval-sec 2" "${TMP_DIR}/dry-run-2.out"
  assert_contains "backend 127.0.0.1:8010 failed to become healthy" "${TMP_DIR}/dry-run-2.out"

  echo "ci_boot_backend_instance tests passed"
}

run_tests
