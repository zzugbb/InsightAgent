#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_assert_operator_summary_contract.sh"
TMP_DIR=""

assert_contains() {
  local file="$1"
  local expected="$2"
  if ! grep -Fq -- "$expected" "$file"; then
    echo "assertion failed: expected line not found" >&2
    echo "file=${file}" >&2
    echo "expected=${expected}" >&2
    cat "$file" >&2 || true
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

  cat > "${TMP_DIR}/release-gate.json" <<'JSON'
{
  "summary_kind": "release_gate",
  "operator_summary": {
    "status": "ready",
    "headline": "release gate checks passed",
    "primary_action": "continue_release_review",
    "highest_severity": "ok",
    "focus_phases": ["backend", "frontend"],
    "blocking_step_labels": []
  }
}
JSON
  cat > "${TMP_DIR}/release-gate.md" <<'MD'
### release gate
- operator_status: ready
- operator_primary_action: continue_release_review
MD

  bash "${SCRIPT}" \
    --summary-json "${TMP_DIR}/release-gate.json" \
    --summary-kind release_gate \
    --markdown "${TMP_DIR}/release-gate.md" \
    > "${TMP_DIR}/release-gate.out"
  assert_contains "${TMP_DIR}/release-gate.out" "operator_summary_contract=PASS"
  assert_contains "${TMP_DIR}/release-gate.out" "operator_summary_count=1"
  assert_contains "${TMP_DIR}/release-gate.out" "markdown_operator_summary=yes"

  cat > "${TMP_DIR}/trend.json" <<'JSON'
{
  "summary_kind": "release_gate_trend",
  "current": {
    "operator_summary": {
      "status": "ready",
      "headline": "release gate checks passed",
      "primary_action": "continue_release_review",
      "highest_severity": "ok",
      "focus_phases": ["backend", "frontend"],
      "blocking_step_labels": []
    }
  },
  "previous": {
    "operator_summary": {
      "status": "action_required",
      "headline": "release gate failures need attention",
      "primary_action": "inspect_failed_steps",
      "highest_severity": "critical",
      "focus_phases": ["frontend"],
      "blocking_step_labels": ["frontend lint"]
    }
  }
}
JSON
  cat > "${TMP_DIR}/trend.md" <<'MD'
### release gate trend
- current_operator_status: ready
- current_operator_primary_action: continue_release_review
- previous_operator_status: action_required
- previous_operator_primary_action: inspect_failed_steps
MD

  bash "${SCRIPT}" \
    --summary-json "${TMP_DIR}/trend.json" \
    --summary-kind release_gate_trend \
    --markdown "${TMP_DIR}/trend.md" \
    > "${TMP_DIR}/trend.out"
  assert_contains "${TMP_DIR}/trend.out" "operator_summary_contract=PASS"
  assert_contains "${TMP_DIR}/trend.out" "operator_summary_count=2"

  cat > "${TMP_DIR}/missing-action.json" <<'JSON'
{
  "summary_kind": "release_gate",
  "operator_summary": {
    "status": "ready",
    "headline": "release gate checks passed",
    "highest_severity": "ok"
  }
}
JSON
  expect_fail bash "${SCRIPT}" --summary-json "${TMP_DIR}/missing-action.json" --summary-kind release_gate

  cat > "${TMP_DIR}/sensitive-value.json" <<'JSON'
{
  "summary_kind": "release_gate",
  "operator_summary": {
    "status": "review",
    "headline": "inspect /tmp/private-release-log",
    "primary_action": "inspect_failed_steps",
    "highest_severity": "warning"
  }
}
JSON
  expect_fail bash "${SCRIPT}" --summary-json "${TMP_DIR}/sensitive-value.json" --summary-kind release_gate

  cat > "${TMP_DIR}/missing-markdown.md" <<'MD'
### release gate
- result: PASS
MD
  expect_fail bash "${SCRIPT}" \
    --summary-json "${TMP_DIR}/release-gate.json" \
    --summary-kind release_gate \
    --markdown "${TMP_DIR}/missing-markdown.md"

  echo "ci_operator_summary_contract tests passed"
}

main "$@"
