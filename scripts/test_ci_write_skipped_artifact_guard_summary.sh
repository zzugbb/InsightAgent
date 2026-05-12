#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_write_skipped_artifact_guard_summary.sh"
TMP_DIR=""

assert_contains() {
  local expected="$1"
  local file="$2"
  if ! grep -Fq -- "${expected}" "${file}"; then
    echo "expected '${expected}' in ${file}" >&2
    cat "${file}" >&2 || true
    exit 1
  fi
}

expect_fail() {
  if "$@" >/dev/null 2>&1; then
    echo "expected fail but passed: $*" >&2
    exit 1
  fi
}

main() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR:-}"' EXIT

  expect_fail bash "${SCRIPT}"

  bash "${SCRIPT}" \
    --scope backend \
    --summary-file "${TMP_DIR}/backend.md" \
    --reason "finalize_backend step did not succeed"
  assert_contains "### backend-e2e artifact stage guard" "${TMP_DIR}/backend.md"
  assert_contains "- skipped: true" "${TMP_DIR}/backend.md"
  assert_contains "- reason: finalize_backend step did not succeed" "${TMP_DIR}/backend.md"

  bash "${SCRIPT}" \
    --scope frontend \
    --summary-file "${TMP_DIR}/frontend.md" \
    --reason "finalize_frontend step did not succeed"
  assert_contains "### frontend-e2e artifact stage guard" "${TMP_DIR}/frontend.md"
  assert_contains "- skipped: true" "${TMP_DIR}/frontend.md"
  assert_contains "- reason: finalize_frontend step did not succeed" "${TMP_DIR}/frontend.md"

  echo "ci_write_skipped_artifact_guard_summary tests passed"
}

main "$@"
