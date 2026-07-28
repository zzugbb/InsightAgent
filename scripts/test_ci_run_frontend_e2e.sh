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

  expect_pass bash -c "cd '${TMP_DIR}' && bash '${SCRIPT_PATH}' --phase full --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001 --dry-run" > "${TMP_DIR}/full-from-other-cwd.out"
  assert_contains "cd ${ROOT_DIR}/frontend" "${TMP_DIR}/full-from-other-cwd.out"

  space_frontend_dir="${TMP_DIR}/frontend with spaces"
  quoted_space_frontend_dir="$(printf "%q" "${space_frontend_dir}")"
  expect_pass bash "${SCRIPT_PATH}" --phase full --frontend-dir "${space_frontend_dir}" --api-base-url "http://127.0.0.1:8000/api?token=a b&mode=test" --frontend-base-url "http://127.0.0.1:3001/app path" --dry-run > "${TMP_DIR}/quoted.out"
  assert_contains "cd ${quoted_space_frontend_dir}" "${TMP_DIR}/quoted.out"
  assert_contains "PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000/api\\?token=a\\ b\\&mode=test" "${TMP_DIR}/quoted.out"
  assert_contains "PLAYWRIGHT_BASE_URL=http://127.0.0.1:3001/app\\ path" "${TMP_DIR}/quoted.out"

  expect_pass bash "${SCRIPT_PATH}" --phase rerun-last-failed --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001 --dry-run > "${TMP_DIR}/rerun.out"
  assert_contains "--last-failed --output=test-results/last-failed" "${TMP_DIR}/rerun.out"

  echo "ci_run_frontend_e2e tests passed"
}

run_tests
