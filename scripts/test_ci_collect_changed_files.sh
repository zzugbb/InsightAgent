#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="${ROOT_DIR}/scripts/ci_collect_changed_files.sh"
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

assert_contains() {
  local expected="$1"
  local file="$2"
  if ! grep -Fq -- "${expected}" "${file}"; then
    echo "expected '${expected}' in ${file}" >&2
    cat "${file}" >&2 || true
    exit 1
  fi
}

assert_line_count() {
  local expected="$1"
  local file="$2"
  local actual
  actual="$(wc -l < "${file}" | tr -d ' ')"
  if [ "${actual}" != "${expected}" ]; then
    echo "expected ${expected} lines in ${file}, got ${actual}" >&2
    cat "${file}" >&2 || true
    exit 1
  fi
}

setup_git_repo() {
  local repo_dir="$1"
  mkdir -p "${repo_dir}"
  git init "${repo_dir}" >/dev/null
  git -C "${repo_dir}" config user.name "CI Test"
  git -C "${repo_dir}" config user.email "ci@example.com"
}

main() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR:-}"' EXIT

  expect_fail bash "${SCRIPT_PATH}"

  setup_git_repo "${TMP_DIR}/repo"
  cat > "${TMP_DIR}/repo/backend.txt" <<'TXT'
base
TXT
  git -C "${TMP_DIR}/repo" add backend.txt
  git -C "${TMP_DIR}/repo" commit -m "base" >/dev/null
  base_sha="$(git -C "${TMP_DIR}/repo" rev-parse HEAD)"

  cat > "${TMP_DIR}/repo/backend.txt" <<'TXT'
head
TXT
  mkdir -p "${TMP_DIR}/repo/frontend"
  cat > "${TMP_DIR}/repo/frontend/app.tsx" <<'TXT'
hello
TXT
  git -C "${TMP_DIR}/repo" add backend.txt frontend/app.tsx
  git -C "${TMP_DIR}/repo" commit -m "head" >/dev/null
  head_sha="$(git -C "${TMP_DIR}/repo" rev-parse HEAD)"

  expect_pass bash "${SCRIPT_PATH}" \
    --repo-root "${TMP_DIR}/repo" \
    --event-name pull_request \
    --base-sha "${base_sha}" \
    --head-sha "${head_sha}" \
    --output-file "${TMP_DIR}/pr-diff.txt" \
    --fallback-path backend/ \
    --fallback-path .github/workflows/backend-e2e.yml \
    > "${TMP_DIR}/pr-diff.out"

  assert_contains "resolve_source=git_diff" "${TMP_DIR}/pr-diff.out"
  assert_contains "changed_count=2" "${TMP_DIR}/pr-diff.out"
  assert_contains "backend.txt" "${TMP_DIR}/pr-diff.txt"
  assert_contains "frontend/app.tsx" "${TMP_DIR}/pr-diff.txt"

  expect_pass bash "${SCRIPT_PATH}" \
    --repo-root "${TMP_DIR}/repo" \
    --event-name pull_request \
    --base-sha deadbeef \
    --head-sha "${head_sha}" \
    --output-file "${TMP_DIR}/pr-fallback.txt" \
    --fallback-path backend/ \
    --fallback-path .github/workflows/backend-e2e.yml \
    > "${TMP_DIR}/pr-fallback.out"

  assert_contains "resolve_source=pull_request_fallback" "${TMP_DIR}/pr-fallback.out"
  assert_contains "backend/" "${TMP_DIR}/pr-fallback.txt"
  assert_contains ".github/workflows/backend-e2e.yml" "${TMP_DIR}/pr-fallback.txt"
  assert_line_count 2 "${TMP_DIR}/pr-fallback.txt"

  expect_pass bash "${SCRIPT_PATH}" \
    --repo-root "${TMP_DIR}/repo" \
    --event-name push \
    --output-file "${TMP_DIR}/push-fallback.txt" \
    --fallback-path frontend/ \
    --fallback-path backend/ \
    > "${TMP_DIR}/push-fallback.out"

  assert_contains "resolve_source=non_pull_request_fallback" "${TMP_DIR}/push-fallback.out"
  assert_contains "frontend/" "${TMP_DIR}/push-fallback.txt"
  assert_contains "backend/" "${TMP_DIR}/push-fallback.txt"
  assert_line_count 2 "${TMP_DIR}/push-fallback.txt"

  echo "ci_collect_changed_files tests passed"
}

main "$@"
