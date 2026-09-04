#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_release_readiness_matrix.sh"
WORKFLOW="${ROOT_DIR}/.github/workflows/release-gate.yml"
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

  bash "${SCRIPT}" --format markdown --output "${TMP_DIR}/readiness.md"
  assert_contains "### release readiness matrix" "${TMP_DIR}/readiness.md"
  assert_contains "| gate_id | required_for_release | service_required | command | notes |" "${TMP_DIR}/readiness.md"
  assert_contains "| release-gate | yes | no |" "${TMP_DIR}/readiness.md"
  assert_contains "bash scripts/ci_run_release_gate.sh --phase auto" "${TMP_DIR}/readiness.md"
  assert_contains "| backend-e2e-main | yes | yes |" "${TMP_DIR}/readiness.md"
  assert_contains "bash scripts/ci_run_backend_e2e.sh --phase main" "${TMP_DIR}/readiness.md"
  assert_contains "| backend-e2e-timeout | yes | yes |" "${TMP_DIR}/readiness.md"
  assert_contains "| backend-e2e-queue | yes | yes |" "${TMP_DIR}/readiness.md"
  assert_contains "| frontend-e2e-smoke | yes | yes |" "${TMP_DIR}/readiness.md"
  assert_contains "| frontend-e2e-full | yes | yes |" "${TMP_DIR}/readiness.md"
  assert_contains "| frontend-e2e-queue | yes | yes |" "${TMP_DIR}/readiness.md"
  assert_contains "| artifact-stage-guard | yes | no |" "${TMP_DIR}/readiness.md"
  assert_contains "| release-visibility-summary | yes | no |" "${TMP_DIR}/readiness.md"
  assert_contains "decision_summary" "${TMP_DIR}/readiness.md"
  assert_contains "operator_summary" "${TMP_DIR}/readiness.md"
  assert_contains "| release-gate-previous-summary | yes | no |" "${TMP_DIR}/readiness.md"
  assert_contains "bash scripts/ci_download_previous_release_gate_summary.sh --workflow release-gate.yml" "${TMP_DIR}/readiness.md"
  assert_contains "download diagnostics and operator_summary" "${TMP_DIR}/readiness.md"
  assert_contains "| release-gate-trend-summary | yes | no |" "${TMP_DIR}/readiness.md"
  assert_contains "bash scripts/ci_release_gate_trend_summary.sh --current-json <path> --previous-json <path>" "${TMP_DIR}/readiness.md"
  assert_contains "| rollback-decision-log | yes | no |" "${TMP_DIR}/readiness.md"
  assert_contains "| artifact-retention-policy | yes | no |" "${TMP_DIR}/readiness.md"

  bash "${SCRIPT}" --format json --output "${TMP_DIR}/readiness.json"
  "$(json_tool_python)" -m json.tool "${TMP_DIR}/readiness.json" >/dev/null
  assert_contains '"gate_id": "release-gate"' "${TMP_DIR}/readiness.json"
  assert_contains '"required_for_release": true' "${TMP_DIR}/readiness.json"
  assert_contains '"service_required": false' "${TMP_DIR}/readiness.json"
  assert_contains '"gate_id": "backend-e2e-main"' "${TMP_DIR}/readiness.json"
  assert_contains '"gate_id": "backend-e2e-queue"' "${TMP_DIR}/readiness.json"
  assert_contains '"service_required": true' "${TMP_DIR}/readiness.json"
  assert_contains '"gate_id": "frontend-e2e-queue"' "${TMP_DIR}/readiness.json"
  assert_contains '"gate_id": "artifact-stage-guard"' "${TMP_DIR}/readiness.json"
  assert_contains '"gate_id": "release-visibility-summary"' "${TMP_DIR}/readiness.json"
  assert_contains 'decision_summary, and operator_summary for release approval' "${TMP_DIR}/readiness.json"
  assert_contains '"gate_id": "release-gate-previous-summary"' "${TMP_DIR}/readiness.json"
  assert_contains 'download diagnostics and operator_summary' "${TMP_DIR}/readiness.json"
  assert_contains '"gate_id": "release-gate-trend-summary"' "${TMP_DIR}/readiness.json"
  assert_contains '"gate_id": "rollback-decision-log"' "${TMP_DIR}/readiness.json"
  assert_contains '"gate_id": "artifact-retention-policy"' "${TMP_DIR}/readiness.json"

  bash "${SCRIPT}" --format markdown > "${TMP_DIR}/stdout.md"
  assert_contains "release readiness matrix" "${TMP_DIR}/stdout.md"

  expect_fail bash "${SCRIPT}" --format yaml

  assert_contains "Write release readiness matrix" "${WORKFLOW}"
  assert_contains "bash scripts/ci_release_readiness_matrix.sh --format markdown --output /tmp/release-readiness.md" "${WORKFLOW}"
  assert_contains "bash scripts/ci_release_readiness_matrix.sh --format json --output /tmp/release-readiness.json" "${WORKFLOW}"
  assert_contains "name: release-readiness-matrix" "${WORKFLOW}"
  assert_contains "/tmp/release-readiness.md" "${WORKFLOW}"
  assert_contains "/tmp/release-readiness.json" "${WORKFLOW}"

  echo "ci_release_readiness tests passed"
}

main "$@"
