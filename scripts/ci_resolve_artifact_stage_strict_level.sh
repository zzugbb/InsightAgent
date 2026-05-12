#!/usr/bin/env bash

set -euo pipefail

event_name=""
ref_name=""
default_level=""
main_push_level=""
pr_level=""
pr_ref_regex=""
dispatch_override=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_resolve_artifact_stage_strict_level.sh \
    --event-name <name> \
    --ref <ref> \
    --default-level <none|warn|fail-on-empty|fail-on-missing> \
    --main-push-level <none|warn|fail-on-empty|fail-on-missing> \
    [--pr-level <none|warn|fail-on-empty|fail-on-missing>] \
    [--pr-ref-regex <regex>] \
    [--dispatch-override <auto|none|warn|fail-on-empty|fail-on-missing>]

Output:
  - strict_level=<value>
  - policy_source=<default|main_push|workflow_dispatch_input>
USAGE
}

is_valid_level() {
  case "$1" in
    none|warn|fail-on-empty|fail-on-missing) return 0 ;;
    *) return 1 ;;
  esac
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --event-name) event_name="${2:-}"; shift 2 ;;
    --ref) ref_name="${2:-}"; shift 2 ;;
    --default-level) default_level="${2:-}"; shift 2 ;;
    --main-push-level) main_push_level="${2:-}"; shift 2 ;;
    --pr-level) pr_level="${2:-}"; shift 2 ;;
    --pr-ref-regex) pr_ref_regex="${2:-}"; shift 2 ;;
    --dispatch-override) dispatch_override="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "${event_name}" ] || [ -z "${ref_name}" ] || [ -z "${default_level}" ] || [ -z "${main_push_level}" ]; then
  echo "missing required arguments" >&2
  usage >&2
  exit 2
fi

if ! is_valid_level "${default_level}"; then
  echo "invalid --default-level: ${default_level}" >&2
  exit 2
fi
if ! is_valid_level "${main_push_level}"; then
  echo "invalid --main-push-level: ${main_push_level}" >&2
  exit 2
fi
if [ -n "${pr_level}" ] && ! is_valid_level "${pr_level}"; then
  echo "invalid --pr-level: ${pr_level}" >&2
  exit 2
fi
if [ -n "${dispatch_override}" ] && [ "${dispatch_override}" != "auto" ] && ! is_valid_level "${dispatch_override}"; then
  echo "invalid --dispatch-override: ${dispatch_override}" >&2
  exit 2
fi

strict_level="${default_level}"
policy_source="default"

if [ "${event_name}" = "push" ] && [ "${ref_name}" = "refs/heads/main" ]; then
  strict_level="${main_push_level}"
  policy_source="main_push"
fi

if [ -n "${pr_level}" ] && [ "${event_name}" = "pull_request" ]; then
  if [ -z "${pr_ref_regex}" ] || printf '%s\n' "${ref_name}" | grep -Eq "${pr_ref_regex}"; then
    strict_level="${pr_level}"
    policy_source="pull_request"
  fi
fi

if [ -n "${dispatch_override}" ] && [ "${dispatch_override}" != "auto" ]; then
  strict_level="${dispatch_override}"
  policy_source="workflow_dispatch_input"
fi

echo "strict_level=${strict_level}"
echo "policy_source=${policy_source}"
