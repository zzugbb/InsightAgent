#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_resolve_diag_strict_level.sh"

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
  if "$@"; then
    echo "expected fail but passed: $*" >&2
    exit 1
  fi
}

main() {
  out=$(bash "$SCRIPT" --event-name pull_request --ref refs/pull/1/merge --default-level p0 --main-push-level any)
  assert_contains "$out" "strict_level=p0"
  assert_contains "$out" "policy_source=default"

  out=$(bash "$SCRIPT" --event-name push --ref refs/heads/main --default-level p0 --main-push-level any)
  assert_contains "$out" "strict_level=any"
  assert_contains "$out" "policy_source=main_push"

  out=$(bash "$SCRIPT" --event-name push --ref refs/heads/main --default-level p0 --main-push-level any --dispatch-override none)
  assert_contains "$out" "strict_level=none"
  assert_contains "$out" "policy_source=workflow_dispatch_input"

  out=$(bash "$SCRIPT" --event-name workflow_dispatch --ref refs/heads/main --default-level p0 --main-push-level any --dispatch-override auto)
  assert_contains "$out" "strict_level=p0"

  expect_fail bash "$SCRIPT" --event-name push --ref refs/heads/main --default-level bad --main-push-level any
  expect_fail bash "$SCRIPT" --event-name push --ref refs/heads/main --default-level p0 --main-push-level bad
  expect_fail bash "$SCRIPT" --event-name push --ref refs/heads/main --default-level p0 --main-push-level any --dispatch-override bad

  echo "ci_resolve_diag_strict_level tests passed"
}

main "$@"
