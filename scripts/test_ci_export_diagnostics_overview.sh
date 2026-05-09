#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OVERVIEW_SCRIPT="${ROOT_DIR}/scripts/ci_export_diagnostics_overview.sh"
TMP_DIR=""

assert_contains() {
  local file="$1"
  local expected="$2"
  if ! grep -Fq -- "$expected" "$file"; then
    echo "assertion failed: expected line not found" >&2
    echo "file=${file}" >&2
    echo "expected=${expected}" >&2
    exit 1
  fi
}

main() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR:-}"' EXIT

  cat > "${TMP_DIR}/frontend-diag.json" <<'JSON'
{"warnings": {"total": 2, "p0": 1, "p1": 1}}
JSON

  cat > "${TMP_DIR}/frontend-guard.json" <<'JSON'
{"scope":"frontend","strict_level":"p0","gate_result":"FAIL","gate_reason":"strict-level p0 requires p0=0","warning_total":2,"warning_p0":1,"warning_p1":1}
JSON

  cat > "${TMP_DIR}/backend-diag.json" <<'JSON'
{"status":"ok","warning_total":1,"warning_p0":0,"warning_p1":1}
JSON

  cat > "${TMP_DIR}/backend-guard.json" <<'JSON'
{"scope":"backend","strict_level":"any","gate_result":"PASS","gate_reason":"within threshold","warning_total":0,"warning_p0":0,"warning_p1":0}
JSON

  local out_md="${TMP_DIR}/overview.md"
  local out_json="${TMP_DIR}/overview.json"

  bash "${OVERVIEW_SCRIPT}" \
    --frontend-diagnostics-json "${TMP_DIR}/frontend-diag.json" \
    --frontend-guard-json "${TMP_DIR}/frontend-guard.json" \
    --backend-diagnostics-json "${TMP_DIR}/backend-diag.json" \
    --backend-guard-json "${TMP_DIR}/backend-guard.json" \
    --markdown-out "${out_md}" \
    --json-out "${out_json}" \
    --label "unit-test"

  assert_contains "${out_md}" "## export diagnostics overview (unit-test)"
  assert_contains "${out_md}" "- totals: warning_total=3, p0=1, p1=2, guard_failures=1"
  assert_contains "${out_md}" "- strict_level=p0, gate_result=FAIL"

  assert_contains "${out_json}" '"label": "unit-test"'
  assert_contains "${out_json}" '"warning_total": 3'
  assert_contains "${out_json}" '"guard_failures": 1'

  echo "ci_export_diagnostics_overview tests passed"
}

main "$@"
