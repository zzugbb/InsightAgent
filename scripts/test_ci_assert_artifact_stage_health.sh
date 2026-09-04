#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUARD_SCRIPT="${ROOT_DIR}/scripts/ci_assert_artifact_stage_health.sh"
TMP_DIR=""

expect_pass() {
  if ! "$@" >/dev/null; then
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

main() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR:-}"' EXIT

  expect_fail "${GUARD_SCRIPT}"
  expect_fail "${GUARD_SCRIPT}" --scope backend --included-count x --missing-count 0

  expect_pass "${GUARD_SCRIPT}" \
    --scope backend \
    --included-count 2 \
    --missing-count 0 \
    --strict-level none \
    --label be-none \
    --summary-file "${TMP_DIR}/be-none.md" \
    --json-summary-file "${TMP_DIR}/be-none.json" \
    --quiet
  assert_contains "gate_result: PASS" "${TMP_DIR}/be-none.md"
  assert_contains "operator_status: ready" "${TMP_DIR}/be-none.md"
  assert_contains "operator_primary_action: continue_release_review" "${TMP_DIR}/be-none.md"
  assert_contains "\"gate_result\": \"PASS\"" "${TMP_DIR}/be-none.json"
  assert_contains "\"operator_summary\"" "${TMP_DIR}/be-none.json"
  assert_contains "\"primary_action\": \"continue_release_review\"" "${TMP_DIR}/be-none.json"

  expect_pass "${GUARD_SCRIPT}" \
    --scope frontend \
    --included-count 0 \
    --missing-count 3 \
    --strict-level warn \
    --label fe-warn \
    --summary-file "${TMP_DIR}/fe-warn.md" \
    --json-summary-file "${TMP_DIR}/fe-warn.json" \
    --quiet
  assert_contains "status: warning" "${TMP_DIR}/fe-warn.md"
  assert_contains "gate_reason: strict-level warn allows warnings" "${TMP_DIR}/fe-warn.md"
  assert_contains "operator_status: review" "${TMP_DIR}/fe-warn.md"
  assert_contains "operator_primary_action: review_artifact_stage_warnings" "${TMP_DIR}/fe-warn.md"
  assert_contains "\"highest_severity\": \"warning\"" "${TMP_DIR}/fe-warn.json"
  assert_contains "\"focus_scopes\": [\"frontend\"]" "${TMP_DIR}/fe-warn.json"

  expect_fail "${GUARD_SCRIPT}" \
    --scope backend \
    --included-count 0 \
    --missing-count 0 \
    --strict-level fail-on-empty \
    --label be-empty \
    --summary-file "${TMP_DIR}/be-empty.md" \
    --json-summary-file "${TMP_DIR}/be-empty.json" \
    --quiet
  assert_contains "gate_result: FAIL" "${TMP_DIR}/be-empty.md"
  assert_contains "gate_reason: strict-level fail-on-empty requires included_count>=1" "${TMP_DIR}/be-empty.md"
  assert_contains "operator_status: action_required" "${TMP_DIR}/be-empty.md"
  assert_contains "operator_primary_action: stage_required_artifacts" "${TMP_DIR}/be-empty.md"
  assert_contains "\"blocking_reasons\": [\"included_count_below_min\"]" "${TMP_DIR}/be-empty.json"

  expect_pass "${GUARD_SCRIPT}" \
    --scope backend \
    --included-count 1 \
    --missing-count 0 \
    --strict-level fail-on-empty \
    --label be-empty-one \
    --quiet

  expect_fail "${GUARD_SCRIPT}" \
    --scope backend \
    --included-count 1 \
    --missing-count 0 \
    --min-included-count 2 \
    --strict-level fail-on-empty \
    --label be-empty-min-two \
    --summary-file "${TMP_DIR}/be-empty-min-two.md" \
    --json-summary-file "${TMP_DIR}/be-empty-min-two.json" \
    --quiet
  assert_contains "min_included_count: 2" "${TMP_DIR}/be-empty-min-two.md"
  assert_contains "gate_reason: strict-level fail-on-empty requires included_count>=2" "${TMP_DIR}/be-empty-min-two.md"
  assert_contains "operator_primary_action: stage_required_artifacts" "${TMP_DIR}/be-empty-min-two.md"

  expect_fail "${GUARD_SCRIPT}" \
    --scope frontend \
    --included-count 2 \
    --missing-count 1 \
    --strict-level fail-on-missing \
    --label fe-missing \
    --summary-file "${TMP_DIR}/fe-missing.md" \
    --json-summary-file "${TMP_DIR}/fe-missing.json" \
    --quiet
  assert_contains "gate_reason: strict-level fail-on-missing requires missing_count=0" "${TMP_DIR}/fe-missing.md"
  assert_contains "operator_status: action_required" "${TMP_DIR}/fe-missing.md"
  assert_contains "operator_primary_action: restore_missing_artifacts" "${TMP_DIR}/fe-missing.md"
  assert_contains "\"blocking_reasons\": [\"missing_artifacts\"]" "${TMP_DIR}/fe-missing.json"

  expect_pass "${GUARD_SCRIPT}" \
    --scope frontend \
    --included-count 3 \
    --missing-count 0 \
    --strict-level fail-on-missing \
    --label fe-clean \
    --quiet

  echo "ci_assert_artifact_stage_health tests passed"
}

main "$@"
