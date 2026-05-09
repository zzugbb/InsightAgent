#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
START_SCRIPT="${ROOT_DIR}/scripts/ci_start_bg_process.sh"
WAIT_SCRIPT="${ROOT_DIR}/scripts/ci_wait_http_status.sh"
TMP_DIR=""
PROCESS_PID=""

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

cleanup() {
  if [ -n "${PROCESS_PID}" ] && kill -0 "${PROCESS_PID}" 2>/dev/null; then
    kill "${PROCESS_PID}" >/dev/null 2>&1 || true
    wait "${PROCESS_PID}" 2>/dev/null || true
  fi
  if [ -n "${TMP_DIR}" ] && [ -d "${TMP_DIR}" ]; then
    rm -rf "${TMP_DIR}"
  fi
}

run_tests() {
  TMP_DIR="$(mktemp -d)"
  trap cleanup EXIT

  expect_fail bash "${START_SCRIPT}" --log-file "${TMP_DIR}/x.log"
  expect_fail bash "${START_SCRIPT}" --log-file "${TMP_DIR}/x.log" --workdir "${TMP_DIR}/missing" -- echo hi
  expect_fail bash "${WAIT_SCRIPT}" --url "http://127.0.0.1:1/health"

  bash "${START_SCRIPT}" \
    --log-file "${TMP_DIR}/sleep.log" \
    --pid-file "${TMP_DIR}/sleep.pid" \
    -- sleep 30 >/dev/null

  PROCESS_PID="$(cat "${TMP_DIR}/sleep.pid")"
  if ! kill -0 "${PROCESS_PID}" 2>/dev/null; then
    echo "background process did not start: pid=${PROCESS_PID}" >&2
    exit 1
  fi

  expect_pass bash "${WAIT_SCRIPT}" \
    --url "file:///etc/hosts" \
    --output-file "${TMP_DIR}/hosts.txt" \
    --expected-code 000 \
    --attempts 1 \
    --interval-sec 0 >/dev/null

  expect_fail bash "${WAIT_SCRIPT}" \
    --url "file:///etc/hosts" \
    --output-file "${TMP_DIR}/health-fail.txt" \
    --expected-code 200 \
    --attempts 2 \
    --interval-sec 0

  echo "ci_service_bootstrap tests passed"
}

run_tests
