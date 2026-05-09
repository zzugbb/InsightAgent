#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUARD_SCRIPT="${ROOT_DIR}/scripts/ci_diag_guard.sh"
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

main() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR:-}"' EXIT

  cat > "${TMP_DIR}/frontend-ok.json" <<'JSON'
{"warnings": {"total": 0, "p0": 0, "p1": 0}}
JSON

  cat > "${TMP_DIR}/frontend-warn.json" <<'JSON'
{"warnings": {"total": 2, "p0": 1, "p1": 1}}
JSON

  cat > "${TMP_DIR}/backend-ok.json" <<'JSON'
{"status": "ok", "warning_total": 0, "warning_p0": 0, "warning_p1": 0}
JSON

  cat > "${TMP_DIR}/backend-warn.json" <<'JSON'
{"status": "ok", "warning_total": 3, "warning_p0": 0, "warning_p1": 3}
JSON

  expect_pass "${GUARD_SCRIPT}" --json "${TMP_DIR}/frontend-ok.json" --scope frontend --strict-level none --label fe-ok-none --quiet
  expect_pass "${GUARD_SCRIPT}" --json "${TMP_DIR}/frontend-ok.json" --scope frontend --strict-level p0 --label fe-ok-p0 --quiet --summary-file "${TMP_DIR}/fe-ok-p0.md" --json-summary-file "${TMP_DIR}/fe-ok-p0.json"
  expect_pass "${GUARD_SCRIPT}" --json "${TMP_DIR}/frontend-ok.json" --scope frontend --strict-level any --label fe-ok-any --quiet
  grep -Fq -- "gate_result: PASS" "${TMP_DIR}/fe-ok-p0.md"
  grep -Fq -- '"gate_result": "PASS"' "${TMP_DIR}/fe-ok-p0.json"

  expect_fail "${GUARD_SCRIPT}" --json "${TMP_DIR}/frontend-warn.json" --scope frontend --strict-level p0 --label fe-warn-p0 --quiet
  expect_fail "${GUARD_SCRIPT}" --json "${TMP_DIR}/frontend-warn.json" --scope frontend --strict-level any --label fe-warn-any --quiet --summary-file "${TMP_DIR}/fe-warn-any.md" --json-summary-file "${TMP_DIR}/fe-warn-any.json"
  expect_pass "${GUARD_SCRIPT}" --json "${TMP_DIR}/frontend-warn.json" --scope frontend --strict-level none --label fe-warn-none --quiet
  grep -Fq -- "gate_result: FAIL" "${TMP_DIR}/fe-warn-any.md"
  grep -Fq -- '"gate_result": "FAIL"' "${TMP_DIR}/fe-warn-any.json"

  expect_pass "${GUARD_SCRIPT}" --json "${TMP_DIR}/backend-ok.json" --scope backend --strict-level any --label be-ok-any --quiet
  expect_fail "${GUARD_SCRIPT}" --json "${TMP_DIR}/backend-warn.json" --scope backend --strict-level any --label be-warn-any --quiet
  expect_pass "${GUARD_SCRIPT}" --json "${TMP_DIR}/backend-warn.json" --scope backend --strict-level p0 --label be-warn-p0 --quiet

  echo "ci_diag_guard tests passed"
}

main "$@"
