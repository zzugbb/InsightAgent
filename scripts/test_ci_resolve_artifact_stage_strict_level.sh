#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_resolve_artifact_stage_strict_level.sh"

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
  out=$(bash "$SCRIPT" --event-name pull_request --ref refs/pull/1/merge --default-level warn --main-push-level fail-on-empty)
  assert_contains "$out" "strict_level=warn"
  assert_contains "$out" "policy_source=default"

  out=$(bash "$SCRIPT" --event-name pull_request --ref refs/pull/1/merge --default-level warn --main-push-level fail-on-empty --pr-level fail-on-empty)
  assert_contains "$out" "strict_level=fail-on-empty"
  assert_contains "$out" "policy_source=pull_request"

  out=$(bash "$SCRIPT" --event-name pull_request --ref refs/pull/1/merge --default-level warn --main-push-level fail-on-empty --pr-level fail-on-empty --pr-ref-regex '^refs/pull/2/merge$')
  assert_contains "$out" "strict_level=warn"
  assert_contains "$out" "policy_source=default"

  out=$(bash "$SCRIPT" --event-name push --ref refs/heads/main --default-level warn --main-push-level fail-on-empty)
  assert_contains "$out" "strict_level=fail-on-empty"
  assert_contains "$out" "policy_source=main_push"

  out=$(bash "$SCRIPT" --event-name push --ref refs/heads/main --default-level warn --main-push-level fail-on-empty --dispatch-override none)
  assert_contains "$out" "strict_level=none"
  assert_contains "$out" "policy_source=workflow_dispatch_input"

  out=$(bash "$SCRIPT" --event-name workflow_dispatch --ref refs/heads/main --default-level warn --main-push-level fail-on-empty --dispatch-override auto)
  assert_contains "$out" "strict_level=warn"

  expect_fail bash "$SCRIPT" --event-name push --ref refs/heads/main --default-level bad --main-push-level fail-on-empty
  expect_fail bash "$SCRIPT" --event-name push --ref refs/heads/main --default-level warn --main-push-level bad
  expect_fail bash "$SCRIPT" --event-name push --ref refs/heads/main --default-level warn --main-push-level fail-on-empty --dispatch-override bad

  echo "ci_resolve_artifact_stage_strict_level tests passed"
}

main "$@"
