#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FLOW_SCRIPT="${ROOT_DIR}/scripts/ci_export_diag_flow.sh"
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

  mkdir -p "${TMP_DIR}/frontend-results"
  cat > "${TMP_DIR}/backend-ok.log" <<'LOG'
[1/2] task export json/markdown consistency + download
  - OK: task export consistency
[2/2] session export json/markdown consistency + download
  - OK: session export consistency
E2E export consistency passed: /tmp/foo
shared-rag role semantics remain compatible with export flow
cross-user export isolation checks
export not-found responses
LOG

  expect_fail bash "${FLOW_SCRIPT}" --scope frontend --source-path "${TMP_DIR}/frontend-results"

  expect_pass bash "${FLOW_SCRIPT}" \
    --scope frontend \
    --source-path "${TMP_DIR}/frontend-results" \
    --diagnostics-markdown-out "${TMP_DIR}/frontend-diag.md" \
    --diagnostics-json-out "${TMP_DIR}/frontend-diag.json" \
    --guard-markdown-out "${TMP_DIR}/frontend-guard.md" \
    --guard-json-out "${TMP_DIR}/frontend-guard.json" \
    --overview-markdown-out "${TMP_DIR}/frontend-overview.md" \
    --overview-json-out "${TMP_DIR}/frontend-overview.json" \
    --event-name pull_request \
    --ref refs/pull/1/merge \
    --default-level p0 \
    --main-push-level any \
    --dispatch-override auto \
    --summary-file "${TMP_DIR}/frontend-summary.md" \
    --quiet > "${TMP_DIR}/frontend-flow.out"

  assert_file "${TMP_DIR}/frontend-diag.md"
  assert_file "${TMP_DIR}/frontend-diag.json"
  assert_file "${TMP_DIR}/frontend-guard.md"
  assert_file "${TMP_DIR}/frontend-overview.md"
  assert_contains "strict_level=p0" "${TMP_DIR}/frontend-flow.out"
  assert_contains "### frontend-e2e export diagnostics" "${TMP_DIR}/frontend-summary.md"
  assert_contains "### frontend-e2e export diagnostics guard" "${TMP_DIR}/frontend-summary.md"

  expect_pass bash "${FLOW_SCRIPT}" \
    --scope backend \
    --source-path "${TMP_DIR}/backend-ok.log" \
    --diagnostics-markdown-out "${TMP_DIR}/backend-diag.md" \
    --diagnostics-json-out "${TMP_DIR}/backend-diag.json" \
    --guard-markdown-out "${TMP_DIR}/backend-guard.md" \
    --guard-json-out "${TMP_DIR}/backend-guard.json" \
    --overview-markdown-out "${TMP_DIR}/backend-overview.md" \
    --overview-json-out "${TMP_DIR}/backend-overview.json" \
    --event-name workflow_dispatch \
    --ref refs/heads/feat/x \
    --default-level p0 \
    --main-push-level any \
    --dispatch-override none \
    --summary-file "${TMP_DIR}/backend-summary.md" \
    --quiet > "${TMP_DIR}/backend-flow.out"

  assert_contains "strict_level=none" "${TMP_DIR}/backend-flow.out"
  assert_contains "policy_source=workflow_dispatch_input" "${TMP_DIR}/backend-flow.out"
  assert_contains "### backend-e2e export consistency" "${TMP_DIR}/backend-summary.md"
  assert_contains "### backend-e2e export diagnostics overview" "${TMP_DIR}/backend-summary.md"

  echo "ci_export_diag_flow tests passed"
}

run_tests
