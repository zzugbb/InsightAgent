#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE_SCRIPT="${ROOT_DIR}/scripts/ci_stage_artifacts.sh"
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

assert_file() {
  if [ ! -e "$1" ]; then
    echo "expected path not found: $1" >&2
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

setup_tmp() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR}"' EXIT
}

run_tests() {
  setup_tmp

  local source_root="${TMP_DIR}/source"
  local out_dir="${TMP_DIR}/stage"
  local list_file="${TMP_DIR}/artifacts.txt"
  mkdir -p "${source_root}/dir-a"

  echo "hello" > "${source_root}/a.log"
  echo "world" > "${source_root}/dir-a/b.txt"

  cat > "${list_file}" <<LIST
# sample list
${source_root}/a.log
${source_root}/dir-a
${source_root}/missing.txt
LIST

  expect_fail bash "${STAGE_SCRIPT}" --list-file "${TMP_DIR}/missing-list.txt" --output-dir "${out_dir}"
  expect_fail bash "${STAGE_SCRIPT}" --list-file "${list_file}"

  expect_pass bash "${STAGE_SCRIPT}" --list-file "${list_file}" --output-dir "${out_dir}" > "${TMP_DIR}/stage.out"

  assert_file "${out_dir}/${source_root#/}/a.log"
  assert_file "${out_dir}/${source_root#/}/dir-a/b.txt"
  assert_file "${out_dir}/_manifest.txt"

  assert_contains "included_count=2" "${TMP_DIR}/stage.out"
  assert_contains "missing_count=1" "${TMP_DIR}/stage.out"
  assert_contains "- ${source_root}/missing.txt" "${out_dir}/_manifest.txt"

  echo "ci_stage_artifacts tests passed"
}

run_tests
