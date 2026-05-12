#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_resolve_artifact_stage_path_level.sh"

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
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT

  cat > "${tmp}/changed.txt" <<'TXT'
backend/app/main.py
frontend/app/page.tsx
TXT

  out=$(bash "$SCRIPT" --scope backend --changed-files "${tmp}/changed.txt" --event-name pull_request --ref refs/pull/1/merge --pr-level fail-on-empty --pr-ref-regex '^refs/pull/[0-9]+/merge$' --path-regex '^(backend/|compose\.full\.yml$|\.github/workflows/backend-e2e\.yml$)')
  assert_contains "$out" "strict_level=fail-on-empty"
  assert_contains "$out" "policy_source=path_match"
  assert_contains "$out" "path_match=yes"

  out=$(bash "$SCRIPT" --scope backend --changed-files "${tmp}/changed.txt" --event-name pull_request --ref refs/pull/1/merge --pr-level fail-on-empty --pr-ref-regex '^refs/pull/[0-9]+/merge$' --path-regex '^docs/')
  assert_contains "$out" "strict_level=warn"
  assert_contains "$out" "policy_source=path_miss"
  assert_contains "$out" "path_match=no"

  out=$(bash "$SCRIPT" --scope backend --changed-files "${tmp}/changed.txt" --event-name push --ref refs/heads/main --fallback-level warn --path-regex '^(backend/|compose\.full\.yml$|\.github/workflows/backend-e2e\.yml$)')
  assert_contains "$out" "strict_level=warn"
  assert_contains "$out" "policy_source=default"

  out=$(bash "$SCRIPT" --scope backend --changed-files "${tmp}/changed.txt" --event-name workflow_dispatch --ref refs/heads/main --fallback-level warn --path-regex '^(backend/|compose\.full\.yml$|\.github/workflows/backend-e2e\.yml$)' --dispatch-override fail-on-empty)
  assert_contains "$out" "strict_level=fail-on-empty"
  assert_contains "$out" "policy_source=workflow_dispatch_input"

  expect_fail bash "$SCRIPT" --scope backend --changed-files "${tmp}/changed.txt" --fallback-level bad

  echo "ci_resolve_artifact_stage_path_level tests passed"
}

main "$@"
