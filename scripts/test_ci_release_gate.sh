#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_run_release_gate.sh"
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

assert_not_contains() {
  local unexpected="$1"
  local file="$2"
  if grep -Fq -- "${unexpected}" "${file}"; then
    echo "did not expect '${unexpected}' in ${file}" >&2
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

  bash "${SCRIPT}" --dry-run --phase all > "${TMP_DIR}/all.txt"
  assert_contains "phase=all" "${TMP_DIR}/all.txt"
  assert_contains "backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py" "${TMP_DIR}/all.txt"
  assert_contains "PYTHONPATH=. .venv/bin/python scripts/test_tool_runtime_module_boundaries.py" "${TMP_DIR}/all.txt"
  assert_contains "node --test --experimental-strip-types" "${TMP_DIR}/all.txt"
  assert_contains "app/source-file-size.node.test.ts" "${TMP_DIR}/all.txt"
  assert_contains "npm run lint" "${TMP_DIR}/all.txt"
  assert_contains "npm run build" "${TMP_DIR}/all.txt"
  assert_contains "bash scripts/test_ci_e2e_tooling.sh all" "${TMP_DIR}/all.txt"
  assert_contains "backend/.venv/bin/python -m compileall -q backend/app backend/scripts" "${TMP_DIR}/all.txt"
  assert_contains "git diff --check" "${TMP_DIR}/all.txt"
  assert_contains "git diff -- data/insightagent.plan.back.md" "${TMP_DIR}/all.txt"
  assert_not_contains "ci_run_backend_e2e.sh" "${TMP_DIR}/all.txt"
  assert_not_contains "ci_run_frontend_e2e.sh" "${TMP_DIR}/all.txt"

  bash "${SCRIPT}" \
    --dry-run \
    --phase frontend \
    --summary-file "${TMP_DIR}/summary.md" \
    --json-summary-file "${TMP_DIR}/summary.json" \
    > "${TMP_DIR}/summary-stdout.txt"
  assert_contains "release_gate_summary=${TMP_DIR}/summary.md" "${TMP_DIR}/summary-stdout.txt"
  assert_contains "release_gate_json_summary=${TMP_DIR}/summary.json" "${TMP_DIR}/summary-stdout.txt"
  assert_contains "### release gate" "${TMP_DIR}/summary.md"
  assert_contains "- phase: frontend" "${TMP_DIR}/summary.md"
  assert_contains "- result: DRY-RUN" "${TMP_DIR}/summary.md"
  assert_contains "| frontend node tests | DRY-RUN |" "${TMP_DIR}/summary.md"
  assert_contains '"phase": "frontend"' "${TMP_DIR}/summary.json"
  assert_contains '"result": "DRY-RUN"' "${TMP_DIR}/summary.json"
  assert_contains '"label": "frontend build"' "${TMP_DIR}/summary.json"

  bash "${SCRIPT}" --dry-run --phase frontend > "${TMP_DIR}/frontend.txt"
  assert_contains "phase=frontend" "${TMP_DIR}/frontend.txt"
  assert_contains "node --test --experimental-strip-types" "${TMP_DIR}/frontend.txt"
  assert_contains "npm run build" "${TMP_DIR}/frontend.txt"
  assert_not_contains "test_tool_runtime_slice.py" "${TMP_DIR}/frontend.txt"

  expect_fail bash "${SCRIPT}" --phase unknown --dry-run

  echo "ci_release_gate tests passed"
}

main "$@"
