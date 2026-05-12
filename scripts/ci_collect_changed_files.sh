#!/usr/bin/env bash

set -euo pipefail

repo_root="."
event_name="${GITHUB_EVENT_NAME:-}"
base_sha=""
head_sha="${GITHUB_SHA:-HEAD}"
output_file=""
fallback_paths=()

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_collect_changed_files.sh \
    --output-file <path> \
    [--repo-root <path>] \
    [--event-name <name>] \
    [--base-sha <sha>] \
    [--head-sha <sha>] \
    [--fallback-path <path>]...

Behavior:
  - For pull_request: try `git diff --name-only <base> <head>`
  - If the PR diff cannot be resolved, write fallback paths instead
  - For non-pull_request events, always write fallback paths

Output:
  - resolve_source=<git_diff|pull_request_fallback|non_pull_request_fallback>
  - changed_count=<n>
  - output_file=<path>
USAGE
}

write_fallback_paths() {
  local target_file="$1"
  : > "${target_file}"
  if [ "${#fallback_paths[@]}" -gt 0 ]; then
    printf '%s\n' "${fallback_paths[@]}" > "${target_file}"
  fi
}

count_lines() {
  local target_file="$1"
  if [ ! -s "${target_file}" ]; then
    echo "0"
    return
  fi
  wc -l < "${target_file}" | tr -d ' '
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo-root) repo_root="${2:-}"; shift 2 ;;
    --event-name) event_name="${2:-}"; shift 2 ;;
    --base-sha) base_sha="${2:-}"; shift 2 ;;
    --head-sha) head_sha="${2:-}"; shift 2 ;;
    --output-file) output_file="${2:-}"; shift 2 ;;
    --fallback-path) fallback_paths+=("${2:-}"); shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${output_file}" ]; then
  echo "missing required argument: --output-file" >&2
  usage >&2
  exit 2
fi

mkdir -p "$(dirname "${output_file}")"

resolve_source="non_pull_request_fallback"
if [ "${event_name}" = "pull_request" ] && [ -n "${base_sha}" ] && [ -n "${head_sha}" ]; then
  if git -C "${repo_root}" rev-parse --verify "${base_sha}^{commit}" >/dev/null 2>&1 \
    && git -C "${repo_root}" rev-parse --verify "${head_sha}^{commit}" >/dev/null 2>&1 \
    && git -C "${repo_root}" diff --name-only "${base_sha}" "${head_sha}" > "${output_file}"; then
    resolve_source="git_diff"
  else
    write_fallback_paths "${output_file}"
    resolve_source="pull_request_fallback"
  fi
else
  write_fallback_paths "${output_file}"
fi

changed_count="$(count_lines "${output_file}")"
echo "resolve_source=${resolve_source}"
echo "changed_count=${changed_count}"
echo "output_file=${output_file}"
