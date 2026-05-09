#!/usr/bin/env bash

set -euo pipefail

scope=""
diagnostics_json=""
guard_markdown_out=""
guard_json_out=""
overview_markdown_out=""
overview_json_out=""
label=""
overview_label=""
event_name=""
ref_name=""
default_level=""
main_push_level=""
dispatch_override="auto"
summary_file=""
quiet="0"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_export_diag_pipeline.sh \
    --scope <frontend|backend> \
    --diagnostics-json <path> \
    --guard-markdown-out <path> \
    --guard-json-out <path> \
    --overview-markdown-out <path> \
    --overview-json-out <path> \
    --event-name <name> \
    --ref <ref> \
    --default-level <none|p0|any> \
    --main-push-level <none|p0|any> \
    [--dispatch-override <auto|none|p0|any>] \
    [--label <name>] \
    [--overview-label <name>] \
    [--summary-file <path>] \
    [--quiet]

Behavior:
  - Resolve strict level via ci_resolve_diag_strict_level.sh
  - Run ci_diag_guard.sh and always build overview output
  - Exit with guard result (0 pass / non-zero fail)
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope) scope="${2:-}"; shift 2 ;;
    --diagnostics-json) diagnostics_json="${2:-}"; shift 2 ;;
    --guard-markdown-out) guard_markdown_out="${2:-}"; shift 2 ;;
    --guard-json-out) guard_json_out="${2:-}"; shift 2 ;;
    --overview-markdown-out) overview_markdown_out="${2:-}"; shift 2 ;;
    --overview-json-out) overview_json_out="${2:-}"; shift 2 ;;
    --event-name) event_name="${2:-}"; shift 2 ;;
    --ref) ref_name="${2:-}"; shift 2 ;;
    --default-level) default_level="${2:-}"; shift 2 ;;
    --main-push-level) main_push_level="${2:-}"; shift 2 ;;
    --dispatch-override) dispatch_override="${2:-}"; shift 2 ;;
    --label) label="${2:-}"; shift 2 ;;
    --overview-label) overview_label="${2:-}"; shift 2 ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    --quiet) quiet="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "${scope}" ] || [ -z "${diagnostics_json}" ] || [ -z "${guard_markdown_out}" ] || [ -z "${guard_json_out}" ] || [ -z "${overview_markdown_out}" ] || [ -z "${overview_json_out}" ] || [ -z "${event_name}" ] || [ -z "${ref_name}" ] || [ -z "${default_level}" ] || [ -z "${main_push_level}" ]; then
  echo "missing required arguments" >&2
  usage >&2
  exit 2
fi

case "${scope}" in
  frontend|backend) ;;
  *)
    echo "invalid --scope: ${scope} (expected frontend|backend)" >&2
    exit 2
    ;;
esac

if [ -z "${label}" ]; then
  label="${scope}-export"
fi
if [ -z "${overview_label}" ]; then
  overview_label="${scope}-e2e"
fi

if [ ! -f "${diagnostics_json}" ]; then
  echo "diagnostics json not found: ${diagnostics_json}" >&2
  exit 2
fi

mkdir -p "$(dirname "${guard_markdown_out}")" "$(dirname "${guard_json_out}")" "$(dirname "${overview_markdown_out}")" "$(dirname "${overview_json_out}")"

resolved="$(bash scripts/ci_resolve_diag_strict_level.sh \
  --event-name "${event_name}" \
  --ref "${ref_name}" \
  --default-level "${default_level}" \
  --main-push-level "${main_push_level}" \
  --dispatch-override "${dispatch_override}")"

strict_level="$(printf '%s\n' "${resolved}" | sed -n 's/^strict_level=//p')"
policy_source="$(printf '%s\n' "${resolved}" | sed -n 's/^policy_source=//p')"

if [ -z "${strict_level}" ] || [ -z "${policy_source}" ]; then
  echo "failed to parse strict-level resolver output" >&2
  exit 2
fi

set +e
if [ "${quiet}" = "1" ]; then
  bash scripts/ci_diag_guard.sh \
    --json "${diagnostics_json}" \
    --scope "${scope}" \
    --strict-level "${strict_level}" \
    --label "${label}" \
    --quiet \
    --summary-file "${guard_markdown_out}" \
    --json-summary-file "${guard_json_out}"
else
  bash scripts/ci_diag_guard.sh \
    --json "${diagnostics_json}" \
    --scope "${scope}" \
    --strict-level "${strict_level}" \
    --label "${label}" \
    --summary-file "${guard_markdown_out}" \
    --json-summary-file "${guard_json_out}"
fi
guard_exit_code=$?
set -e

case "${scope}" in
  frontend)
    bash scripts/ci_export_diagnostics_overview.sh \
      --frontend-diagnostics-json "${diagnostics_json}" \
      --frontend-guard-json "${guard_json_out}" \
      --markdown-out "${overview_markdown_out}" \
      --json-out "${overview_json_out}" \
      --label "${overview_label}"
    ;;
  backend)
    bash scripts/ci_export_diagnostics_overview.sh \
      --backend-diagnostics-json "${diagnostics_json}" \
      --backend-guard-json "${guard_json_out}" \
      --markdown-out "${overview_markdown_out}" \
      --json-out "${overview_json_out}" \
      --label "${overview_label}"
    ;;
esac

if [ -n "${summary_file}" ]; then
  mkdir -p "$(dirname "${summary_file}")"
  {
    echo "### ${scope}-e2e export diagnostics guard"
    echo "- policy: default=${default_level}, main_push=${main_push_level}"
    echo "- dispatch_override: ${dispatch_override}"
    echo "- policy_source: ${policy_source}"
    echo "- selected_strict_level: ${strict_level}"
    cat "${guard_markdown_out}"
    echo
    echo "### ${scope}-e2e export diagnostics overview"
    cat "${overview_markdown_out}"
  } >> "${summary_file}"
fi

echo "strict_level=${strict_level}"
echo "policy_source=${policy_source}"

echo "guard_markdown_out=${guard_markdown_out}"
echo "guard_json_out=${guard_json_out}"
echo "overview_markdown_out=${overview_markdown_out}"
echo "overview_json_out=${overview_json_out}"

exit "${guard_exit_code}"
