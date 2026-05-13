#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESOLVE_SCRIPT="${ROOT_DIR}/scripts/ci_resolve_artifact_stage_scope_config.sh"
LOAD_SCRIPT="${ROOT_DIR}/scripts/ci_load_artifact_stage_scope_config.sh"

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

  config_out="$(bash "${RESOLVE_SCRIPT}" --scope backend --repo-root /tmp/workspace)"
  expect_fail bash "${LOAD_SCRIPT}"
  expect_fail bash "${LOAD_SCRIPT}" --config-file "${tmp}/missing.txt"

  printf '%s\n' "${config_out}" > "${tmp}/config.txt"
  bash "${LOAD_SCRIPT}" --config-file "${tmp}/config.txt" --output-file "${tmp}/env.sh"

  env_out="$(
    bash -lc '
      set -euo pipefail
      source "'"${tmp}/env.sh"'"
      printf "changed=%s\n" "${ARTIFACT_CHANGED_FILES_PATH}"
      printf "path_regex=%s\n" "${ARTIFACT_PATH_REGEX}"
      printf "pr_ref_regex=%s\n" "${ARTIFACT_PR_REF_REGEX}"
      printf "guard_label=%s\n" "${ARTIFACT_GUARD_LABEL}"
      printf "summary_heading=%s\n" "${ARTIFACT_SUMMARY_HEADING}"
      printf "guard_markdown_out=%s\n" "${ARTIFACT_GUARD_MARKDOWN_OUT}"
      printf "guard_json_out=%s\n" "${ARTIFACT_GUARD_JSON_OUT}"
      printf "fallback_count=%s\n" "${#ARTIFACT_FALLBACK_PATHS[@]}"
      printf "fallback0=%s\n" "${ARTIFACT_FALLBACK_PATHS[0]}"
      printf "fallback2=%s\n" "${ARTIFACT_FALLBACK_PATHS[2]}"
    '
  )"

  assert_contains "${env_out}" "changed=/tmp/workspace/.github/backend-e2e-changed-files.txt"
  assert_contains "${env_out}" "path_regex=^(backend/|compose\\.full\\.yml$|\\.github/workflows/backend-e2e\\.yml$)"
  assert_contains "${env_out}" "pr_ref_regex=^(refs/pull/[0-9]+/merge)$"
  assert_contains "${env_out}" "guard_label=backend-e2e-artifact-stage"
  assert_contains "${env_out}" "summary_heading=### backend-e2e artifact strict policy"
  assert_contains "${env_out}" "guard_markdown_out=/tmp/backend-e2e-artifact-guard-summary.md"
  assert_contains "${env_out}" "guard_json_out=/tmp/backend-e2e-artifact-guard-summary.json"
  assert_contains "${env_out}" "fallback_count=3"
  assert_contains "${env_out}" "fallback0=backend/"
  assert_contains "${env_out}" "fallback2=.github/workflows/backend-e2e.yml"

  echo "ci_load_artifact_stage_scope_config tests passed"
}

main "$@"
