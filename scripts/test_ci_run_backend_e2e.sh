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
  expected_backend_e2e_python="${BACKEND_E2E_PYTHON:-}"
  if [ -z "${expected_backend_e2e_python}" ]; then
    if [ -x "${ROOT_DIR}/backend/.venv/bin/python" ]; then
      expected_backend_e2e_python="backend/.venv/bin/python"
    else
      expected_backend_e2e_python="python3"
    fi
  fi

  expect_fail bash "${SCRIPT_PATH}"
  expect_fail bash "${SCRIPT_PATH}" --phase unknown --base-url http://127.0.0.1:8000

  expect_pass bash "${SCRIPT_PATH}" --phase main --base-url http://127.0.0.1:8000 --log-dir "${TMP_DIR}" --dry-run > "${TMP_DIR}/main.out"
  assert_contains "${expected_backend_e2e_python} backend/scripts/e2e_baseline.py --base-url http://127.0.0.1:8000" "${TMP_DIR}/main.out"
  assert_contains "${expected_backend_e2e_python} backend/scripts/e2e_main_path.py --base-url http://127.0.0.1:8000" "${TMP_DIR}/main.out"
  assert_contains "${expected_backend_e2e_python} backend/scripts/e2e_export_consistency.py --base-url http://127.0.0.1:8000" "${TMP_DIR}/main.out"
  assert_contains "${expected_backend_e2e_python} backend/scripts/e2e_task_cancel_timeout.py --base-url http://127.0.0.1:8000 --skip-timeout" "${TMP_DIR}/main.out"

  expect_pass bash "${SCRIPT_PATH}" --phase timeout --base-url http://127.0.0.1:8010 --log-dir "${TMP_DIR}" --dry-run > "${TMP_DIR}/timeout.out"
  assert_contains "--cancel-prompt-words 180000 --timeout-prompt-words 250000" "${TMP_DIR}/timeout.out"

  expect_pass bash "${SCRIPT_PATH}" --phase main --base-url http://127.0.0.1:9000 --log-dir "${TMP_DIR}" --dry-run > "${TMP_DIR}/main-9000.out"
  assert_contains "tee ${TMP_DIR}/e2e-main-path-9000.log" "${TMP_DIR}/main-9000.out"

  expect_pass bash -c "cd '${TMP_DIR}' && bash '${SCRIPT_PATH}' --phase main --base-url http://127.0.0.1:8000 --log-dir '${TMP_DIR}' --dry-run" > "${TMP_DIR}/main-from-other-cwd.out"
  assert_contains "${expected_backend_e2e_python} backend/scripts/e2e_main_path.py --base-url http://127.0.0.1:8000" "${TMP_DIR}/main-from-other-cwd.out"

  expect_pass bash -c "cd '${TMP_DIR}' && bash '${SCRIPT_PATH}' --phase main --base-url http://127.0.0.1:8000 --log-dir relative-e2e-logs --dry-run" > "${TMP_DIR}/main-relative-log-dir.out"
  assert_contains "tee ${TMP_DIR}/relative-e2e-logs/e2e-main-path-8000.log" "${TMP_DIR}/main-relative-log-dir.out"

  space_log_dir="${TMP_DIR}/e2e logs"
  quoted_space_log_dir="$(printf "%q" "${space_log_dir}")"
  expect_pass bash "${SCRIPT_PATH}" --phase main --base-url "http://127.0.0.1:9001/api?token=a b&mode=test" --log-dir "${space_log_dir}" --dry-run > "${TMP_DIR}/quoted.out"
  assert_contains "--base-url http://127.0.0.1:9001/api\\?token=a\\ b\\&mode=test" "${TMP_DIR}/quoted.out"
  assert_contains "tee ${quoted_space_log_dir}/e2e-main-path-9001.log" "${TMP_DIR}/quoted.out"

  expect_pass env BACKEND_E2E_PYTHON=python3 bash "${SCRIPT_PATH}" --phase main --base-url http://127.0.0.1:8000 --log-dir "${TMP_DIR}" --dry-run > "${TMP_DIR}/python-override.out"
  assert_contains "python3 backend/scripts/e2e_baseline.py --base-url http://127.0.0.1:8000" "${TMP_DIR}/python-override.out"

  echo "ci_run_backend_e2e tests passed"
}

run_tests
