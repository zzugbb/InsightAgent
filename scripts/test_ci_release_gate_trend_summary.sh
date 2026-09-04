#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_release_gate_trend_summary.sh"
TMP_DIR=""

json_tool_python() {
  if [ -n "${CI_JSON_TOOL_PYTHON:-}" ]; then
    printf '%s\n' "${CI_JSON_TOOL_PYTHON}"
  elif [ -x "${ROOT_DIR}/backend/.venv/bin/python" ]; then
    printf '%s\n' "${ROOT_DIR}/backend/.venv/bin/python"
  else
    printf '%s\n' "python3"
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

expect_fail() {
  if "$@" >/dev/null 2>&1; then
    echo "expected fail but passed: $*" >&2
    exit 1
  fi
}

main() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR:-}"' EXIT

  cat > "${TMP_DIR}/current.json" <<'JSON'
{
  "summary_kind": "release_gate",
  "summary_schema_version": 1,
  "service_required": false,
  "phase": "all",
  "result": "PASS",
  "step_summary": {"total": 9, "pass": 9, "fail": 0, "dry_run": 0},
  "failed_step_labels": [],
  "decision_summary": {"release_decision": "approve", "rollback_decision": "not_required", "reason": "all_required_static_gates_passed", "required_follow_up": []},
  "operator_summary": {"status": "ready", "headline": "release gate checks passed", "primary_action": "continue_release_review", "highest_severity": "ok", "total_steps": 9, "failed_steps": 0, "focus_phases": ["backend", "frontend", "tooling", "hygiene"], "blocking_step_labels": []}
}
JSON

  cat > "${TMP_DIR}/previous.json" <<'JSON'
{
  "summary_kind": "release_gate",
  "summary_schema_version": 1,
  "service_required": false,
  "phase": "all",
  "result": "FAIL",
  "step_summary": {"total": 9, "pass": 8, "fail": 1, "dry_run": 0},
  "failed_step_labels": ["frontend lint"],
  "decision_summary": {"release_decision": "hold", "rollback_decision": "investigate_failed_gate", "reason": "failed_required_static_gate", "required_follow_up": ["inspect_failed_steps", "keep_previous_release"]},
  "operator_summary": {"status": "action_required", "headline": "release gate failures need attention", "primary_action": "inspect_failed_steps", "highest_severity": "critical", "total_steps": 9, "failed_steps": 1, "focus_phases": ["frontend"], "blocking_step_labels": ["frontend lint"]}
}
JSON

  bash "${SCRIPT}" \
    --current-json "${TMP_DIR}/current.json" \
    --summary-file "${TMP_DIR}/baseline.md" \
    --json-summary-file "${TMP_DIR}/baseline.json"
  "$(json_tool_python)" -m json.tool "${TMP_DIR}/baseline.json" >/dev/null
  assert_contains "### release gate trend" "${TMP_DIR}/baseline.md"
  assert_contains "- summary_kind: release_gate_trend" "${TMP_DIR}/baseline.md"
  assert_contains "- previous_available: no" "${TMP_DIR}/baseline.md"
  assert_contains "- trend_result: baseline" "${TMP_DIR}/baseline.md"
  assert_contains "- current_failed_steps: 0" "${TMP_DIR}/baseline.md"
  assert_contains "- current_operator_status: ready" "${TMP_DIR}/baseline.md"
  assert_contains "- current_operator_primary_action: continue_release_review" "${TMP_DIR}/baseline.md"
  assert_contains "- current_operator_focus_phases: backend, frontend, tooling, hygiene" "${TMP_DIR}/baseline.md"
  assert_contains '"summary_kind": "release_gate_trend"' "${TMP_DIR}/baseline.json"
  assert_contains '"previous_available": false' "${TMP_DIR}/baseline.json"
  assert_contains '"trend_result": "baseline"' "${TMP_DIR}/baseline.json"
  assert_contains '"release_decision": "approve"' "${TMP_DIR}/baseline.json"
  assert_contains '"rollback_decision": "not_required"' "${TMP_DIR}/baseline.json"
  assert_contains '"operator_summary": {' "${TMP_DIR}/baseline.json"
  assert_contains '"status": "ready"' "${TMP_DIR}/baseline.json"
  assert_contains '"primary_action": "continue_release_review"' "${TMP_DIR}/baseline.json"

  bash "${SCRIPT}" \
    --current-json "${TMP_DIR}/current.json" \
    --previous-json "${TMP_DIR}/previous.json" \
    --summary-file "${TMP_DIR}/trend.md" \
    --json-summary-file "${TMP_DIR}/trend.json"
  "$(json_tool_python)" -m json.tool "${TMP_DIR}/trend.json" >/dev/null
  assert_contains "- previous_available: yes" "${TMP_DIR}/trend.md"
  assert_contains "- trend_result: improved" "${TMP_DIR}/trend.md"
  assert_contains "- failed_steps_delta: -1" "${TMP_DIR}/trend.md"
  assert_contains "- current_operator_status: ready" "${TMP_DIR}/trend.md"
  assert_contains "- current_operator_primary_action: continue_release_review" "${TMP_DIR}/trend.md"
  assert_contains "- previous_operator_status: action_required" "${TMP_DIR}/trend.md"
  assert_contains "- previous_operator_primary_action: inspect_failed_steps" "${TMP_DIR}/trend.md"
  assert_contains "- removed_failed_step_labels: frontend lint" "${TMP_DIR}/trend.md"
  assert_contains '"previous_available": true' "${TMP_DIR}/trend.json"
  assert_contains '"trend_result": "improved"' "${TMP_DIR}/trend.json"
  assert_contains '"fail": -1' "${TMP_DIR}/trend.json"
  assert_contains '"removed_failed_step_labels": [' "${TMP_DIR}/trend.json"
  assert_contains '"frontend lint"' "${TMP_DIR}/trend.json"
  assert_contains '"release_decision": "hold"' "${TMP_DIR}/trend.json"
  assert_contains '"rollback_decision": "investigate_failed_gate"' "${TMP_DIR}/trend.json"
  assert_contains '"status": "action_required"' "${TMP_DIR}/trend.json"
  assert_contains '"blocking_step_labels": [' "${TMP_DIR}/trend.json"

  expect_fail bash "${SCRIPT}" --current-json "${TMP_DIR}/missing.json"

  echo "ci_release_gate_trend_summary tests passed"
}

main "$@"
