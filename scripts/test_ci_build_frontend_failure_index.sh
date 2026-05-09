#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="${ROOT_DIR}/scripts/ci_build_frontend_failure_index.sh"
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

  local results_dir="${TMP_DIR}/results"
  local output_file="${TMP_DIR}/index.md"
  mkdir -p "${results_dir}/suite-a" "${results_dir}/suite-b"
  echo "context-a" > "${results_dir}/suite-a/error-context.md"
  : > "${results_dir}/suite-b/trace.zip"

  expect_fail bash "${SCRIPT_PATH}" --unknown-arg x

  expect_pass bash "${SCRIPT_PATH}" \
    --results-dir "${results_dir}" \
    --output-file "${output_file}" \
    --run-id "123456" \
    --run-attempt "7" > "${TMP_DIR}/stdout.txt"

  assert_contains "output_file=${output_file}" "${TMP_DIR}/stdout.txt"
  assert_contains "# frontend-e2e failure index" "${output_file}"
  assert_contains "- run_id: 123456" "${output_file}"
  assert_contains "- run_attempt: 7" "${output_file}"
  assert_contains "## error-context.md" "${output_file}"
  assert_contains "${results_dir}/suite-a/error-context.md" "${output_file}"
  assert_contains "## trace.zip" "${output_file}"
  assert_contains "${results_dir}/suite-b/trace.zip" "${output_file}"

  expect_pass bash "${SCRIPT_PATH}" \
    --results-dir "${TMP_DIR}/missing-results" \
    --output-file "${TMP_DIR}/missing-index.md" > /dev/null
  assert_contains "No ${TMP_DIR}/missing-results directory found." "${TMP_DIR}/missing-index.md"

  echo "ci_build_frontend_failure_index tests passed"
}

run_tests
