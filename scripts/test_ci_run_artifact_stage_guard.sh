#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_run_artifact_stage_guard.sh"
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

expect_pass() {
  if ! "$@"; then
    echo "expected pass but failed: $*" >&2
    exit 1
  fi
}

main() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR:-}"' EXIT

  mkdir -p "${TMP_DIR}/repo/.github"
  summary_file="${TMP_DIR}/summary.md"
  touch "${summary_file}"

  expect_pass env \
    GITHUB_EVENT_NAME=pull_request \
    GITHUB_REF=refs/pull/9/merge \
    GITHUB_SHA=abc123 \
    bash "${SCRIPT}" \
      --scope backend \
      --repo-root "${TMP_DIR}/repo" \
      --base-sha deadbeef \
      --head-sha abc123 \
      --dispatch-override auto \
      --fallback-level warn \
      --pr-level fail-on-empty \
      --included-count 2 \
      --missing-count 0 \
      --min-included-count 2 \
      --stage-dir "${TMP_DIR}/stage" \
      --manifest "${TMP_DIR}/manifest.txt" \
      --summary-file "${summary_file}" \
      --guard-markdown-out "${TMP_DIR}/guard.md" \
      --guard-json-out "${TMP_DIR}/guard.json" \
      > "${TMP_DIR}/stdout.txt"

  assert_contains "artifact_strict_level=fail-on-empty" "${TMP_DIR}/stdout.txt"
  assert_contains "artifact_policy_source=path_match" "${TMP_DIR}/stdout.txt"
  assert_contains "changed_files_path=${TMP_DIR}/repo/.github/backend-e2e-changed-files.txt" "${TMP_DIR}/stdout.txt"
  assert_contains "backend/" "${TMP_DIR}/repo/.github/backend-e2e-changed-files.txt"
  assert_contains "### backend-e2e artifact strict policy" "${summary_file}"
  assert_contains "- policy_source: path_match" "${summary_file}"
  assert_contains "gate_result: PASS" "${TMP_DIR}/guard.md"

  echo "ci_run_artifact_stage_guard tests passed"
}

main "$@"
