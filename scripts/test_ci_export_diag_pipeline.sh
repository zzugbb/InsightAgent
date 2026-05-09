#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIPELINE_SCRIPT="${ROOT_DIR}/scripts/ci_export_diag_pipeline.sh"
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
  if [ ! -f "$1" ]; then
    echo "expected file not found: $1" >&2
    exit 1
  fi
}

assert_contains() {
  local expected="$1"
  local file="$2"
  if ! grep -Fq -- "${expected}" "${file}"; then
    echo "expected '${expected}' in ${file}" >&2
    echo "---- file content ----" >&2
    cat "${file}" >&2 || true
    echo "----------------------" >&2
    exit 1
  fi
}

setup_tmp() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR}"' EXIT
}

run_tests() {
  setup_tmp

  cat > "${TMP_DIR}/frontend-ok.json" <<'JSON'
{
  "warnings": {
    "total": 1,
    "p0": 0,
    "p1": 1
  }
}
JSON

  cat > "${TMP_DIR}/frontend-warn.json" <<'JSON'
{
  "warnings": {
    "total": 2,
    "p0": 1,
    "p1": 1
  }
}
JSON

  cat > "${TMP_DIR}/backend-ok.json" <<'JSON'
{
  "status": "ok",
  "warning_total": 0,
  "warning_p0": 0,
  "warning_p1": 0
}
JSON

  cat > "${TMP_DIR}/backend-warn.json" <<'JSON'
{
  "status": "ok",
  "warning_total": 2,
  "warning_p0": 1,
  "warning_p1": 1
}
JSON

  expect_pass bash "${PIPELINE_SCRIPT}" \
    --scope frontend \
    --diagnostics-json "${TMP_DIR}/frontend-ok.json" \
    --guard-markdown-out "${TMP_DIR}/fe-ok-guard.md" \
    --guard-json-out "${TMP_DIR}/fe-ok-guard.json" \
    --overview-markdown-out "${TMP_DIR}/fe-ok-overview.md" \
    --overview-json-out "${TMP_DIR}/fe-ok-overview.json" \
    --event-name pull_request \
    --ref refs/pull/1/merge \
    --default-level p0 \
    --main-push-level any \
    --dispatch-override auto \
    --summary-file "${TMP_DIR}/fe-ok-summary.md" \
    --quiet > "${TMP_DIR}/fe-ok.out"

  assert_contains "strict_level=p0" "${TMP_DIR}/fe-ok.out"
  assert_contains "policy_source=default" "${TMP_DIR}/fe-ok.out"
  assert_contains "selected_strict_level: p0" "${TMP_DIR}/fe-ok-summary.md"
  assert_contains "gate_result: PASS" "${TMP_DIR}/fe-ok-guard.md"

  expect_fail bash "${PIPELINE_SCRIPT}" \
    --scope frontend \
    --diagnostics-json "${TMP_DIR}/frontend-warn.json" \
    --guard-markdown-out "${TMP_DIR}/fe-warn-guard.md" \
    --guard-json-out "${TMP_DIR}/fe-warn-guard.json" \
    --overview-markdown-out "${TMP_DIR}/fe-warn-overview.md" \
    --overview-json-out "${TMP_DIR}/fe-warn-overview.json" \
    --event-name push \
    --ref refs/heads/main \
    --default-level p0 \
    --main-push-level any \
    --dispatch-override auto \
    --summary-file "${TMP_DIR}/fe-warn-summary.md" \
    --quiet

  assert_file "${TMP_DIR}/fe-warn-overview.md"
  assert_file "${TMP_DIR}/fe-warn-overview.json"
  assert_contains "gate_result: FAIL" "${TMP_DIR}/fe-warn-guard.md"
  assert_contains "selected_strict_level: any" "${TMP_DIR}/fe-warn-summary.md"

  expect_pass bash "${PIPELINE_SCRIPT}" \
    --scope backend \
    --diagnostics-json "${TMP_DIR}/backend-warn.json" \
    --guard-markdown-out "${TMP_DIR}/be-warn-guard.md" \
    --guard-json-out "${TMP_DIR}/be-warn-guard.json" \
    --overview-markdown-out "${TMP_DIR}/be-warn-overview.md" \
    --overview-json-out "${TMP_DIR}/be-warn-overview.json" \
    --event-name workflow_dispatch \
    --ref refs/heads/feature/test \
    --default-level p0 \
    --main-push-level any \
    --dispatch-override none \
    --summary-file "${TMP_DIR}/be-warn-summary.md" \
    --quiet > "${TMP_DIR}/be-warn.out"

  assert_contains "strict_level=none" "${TMP_DIR}/be-warn.out"
  assert_contains "policy_source=workflow_dispatch_input" "${TMP_DIR}/be-warn.out"
  assert_contains "selected_strict_level: none" "${TMP_DIR}/be-warn-summary.md"
  assert_contains "gate_result: PASS" "${TMP_DIR}/be-warn-guard.md"

  echo "ci_export_diag_pipeline tests passed"
}

run_tests
