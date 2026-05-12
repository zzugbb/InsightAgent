#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_resolve_artifact_stage_path_level.sh \
    --scope <backend|frontend> \
    --changed-files <path> \
    [--dispatch-override <auto|none|warn|fail-on-empty|fail-on-missing>] \
    [--pr-level <none|warn|fail-on-empty|fail-on-missing>] \
    [--pr-ref-regex <regex>] \
    [--path-regex <regex>] \
    [--fallback-level <none|warn|fail-on-empty|fail-on-missing>]

Output:
  - strict_level=<value>
  - policy_source=<default|pull_request|path_match|path_miss>
  - path_match=<yes|no>
USAGE
}

scope=""
changed_files=""
dispatch_override="auto"
pr_level=""
pr_ref_regex=""
path_regex=""
fallback_level="warn"
event_name="${GITHUB_EVENT_NAME:-}"
ref_name="${GITHUB_REF:-}"

is_valid_level() {
  case "$1" in
    none|warn|fail-on-empty|fail-on-missing) return 0 ;;
    *) return 1 ;;
  esac
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope) scope="${2:-}"; shift 2 ;;
    --changed-files) changed_files="${2:-}"; shift 2 ;;
    --dispatch-override) dispatch_override="${2:-}"; shift 2 ;;
    --pr-level) pr_level="${2:-}"; shift 2 ;;
    --pr-ref-regex) pr_ref_regex="${2:-}"; shift 2 ;;
    --path-regex) path_regex="${2:-}"; shift 2 ;;
    --fallback-level) fallback_level="${2:-}"; shift 2 ;;
    --event-name) event_name="${2:-}"; shift 2 ;;
    --ref) ref_name="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "${scope}" ] || [ -z "${changed_files}" ]; then
  echo "missing required arguments: --scope/--changed-files" >&2
  usage >&2
  exit 2
fi

if [ -n "${pr_level}" ] && ! is_valid_level "${pr_level}"; then
  echo "invalid --pr-level: ${pr_level}" >&2
  exit 2
fi
if ! is_valid_level "${fallback_level}"; then
  echo "invalid --fallback-level: ${fallback_level}" >&2
  exit 2
fi
if [ -n "${dispatch_override}" ] && [ "${dispatch_override}" != "auto" ] && ! is_valid_level "${dispatch_override}"; then
  echo "invalid --dispatch-override: ${dispatch_override}" >&2
  exit 2
fi

path_match="no"
if [ -n "${path_regex}" ] && grep -Eq "${path_regex}" "${changed_files}"; then
  path_match="yes"
fi

strict_level="${fallback_level}"
policy_source="default"

if [ "${event_name}" = "pull_request" ] && [ -n "${pr_level}" ]; then
  if [ -z "${pr_ref_regex}" ] || printf '%s\n' "${ref_name}" | grep -Eq "${pr_ref_regex}"; then
    if [ "${path_match}" = "yes" ]; then
      strict_level="${pr_level}"
      policy_source="path_match"
    else
      policy_source="path_miss"
    fi
  fi
fi

if [ -n "${dispatch_override}" ] && [ "${dispatch_override}" != "auto" ]; then
  strict_level="${dispatch_override}"
  policy_source="workflow_dispatch_input"
fi

echo "strict_level=${strict_level}"
echo "policy_source=${policy_source}"
echo "path_match=${path_match}"
