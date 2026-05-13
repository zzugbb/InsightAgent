#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_resolve_artifact_stage_scope_config.sh"

assert_contains() {
  local haystack="$1"
  local needle="$2"
  if ! grep -Fq -- "$needle" <<<"$haystack"; then
    echo "assertion failed: expected [$needle]" >&2
    echo "$haystack" >&2
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
  out=$(bash "$SCRIPT" --scope backend --repo-root /tmp/workspace)
  assert_contains "$out" "changed_files_path=/tmp/workspace/.github/backend-e2e-changed-files.txt"
  assert_contains "$out" "path_regex=^(backend/|compose\\.full\\.yml$|\\.github/workflows/backend-e2e\\.yml$)"
  assert_contains "$out" "pr_ref_regex=^(refs/pull/[0-9]+/merge)$"
  assert_contains "$out" "guard_label=backend-e2e-artifact-stage"
  assert_contains "$out" "summary_heading=### backend-e2e artifact strict policy"
  assert_contains "$out" "guard_markdown_out=/tmp/backend-e2e-artifact-guard-summary.md"
  assert_contains "$out" "guard_json_out=/tmp/backend-e2e-artifact-guard-summary.json"
  assert_contains "$out" "fallback_path=backend/"
  assert_contains "$out" "fallback_path=compose.full.yml"
  assert_contains "$out" "fallback_path=.github/workflows/backend-e2e.yml"

  out=$(bash "$SCRIPT" --scope frontend)
  assert_contains "$out" "changed_files_path=.github/frontend-e2e-changed-files.txt"
  assert_contains "$out" "path_regex=^(frontend/|backend/|compose\\.full\\.yml$|\\.github/workflows/frontend-e2e\\.yml$)"
  assert_contains "$out" "pr_ref_regex=^(refs/pull/[0-9]+/merge)$"
  assert_contains "$out" "guard_label=frontend-e2e-artifact-stage"
  assert_contains "$out" "summary_heading=### frontend-e2e artifact strict policy"
  assert_contains "$out" "guard_markdown_out=/tmp/frontend-e2e-artifact-guard-summary.md"
  assert_contains "$out" "guard_json_out=/tmp/frontend-e2e-artifact-guard-summary.json"
  assert_contains "$out" "fallback_path=frontend/"
  assert_contains "$out" "fallback_path=backend/"
  assert_contains "$out" "fallback_path=compose.full.yml"
  assert_contains "$out" "fallback_path=.github/workflows/frontend-e2e.yml"

  expect_fail bash "$SCRIPT"
  expect_fail bash "$SCRIPT" --scope invalid

  echo "ci_resolve_artifact_stage_scope_config tests passed"
}

main "$@"
