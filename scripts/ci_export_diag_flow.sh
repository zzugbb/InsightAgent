#!/usr/bin/env bash

set -euo pipefail

scope=""
source_path=""
diagnostics_markdown_out=""
diagnostics_json_out=""
guard_markdown_out=""
guard_json_out=""
overview_markdown_out=""
overview_json_out=""
event_name=""
ref_name=""
default_level=""
main_push_level=""
dispatch_override="auto"
summary_file=""
label=""
overview_label=""
quiet="0"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_export_diag_flow.sh \
    --scope <frontend|backend> \
    --source-path <path> \
    --diagnostics-markdown-out <path> \
    --diagnostics-json-out <path> \
    --guard-markdown-out <path> \
    --guard-json-out <path> \
    --overview-markdown-out <path> \
    --overview-json-out <path> \
    --event-name <name> \
    --ref <ref> \
    --default-level <none|p0|any> \
    --main-push-level <none|p0|any> \
    [--dispatch-override <auto|none|p0|any>] \
    [--summary-file <path>] \
    [--label <name>] \
    [--overview-label <name>] \
    [--quiet]

Behavior:
  - Build scope diagnostics summary (markdown + json)
  - Append diagnostics markdown to summary file if provided
  - Run ci_export_diag_pipeline.sh for guard + overview + gating
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope) scope="${2:-}"; shift 2 ;;
    --source-path) source_path="${2:-}"; shift 2 ;;
    --diagnostics-markdown-out) diagnostics_markdown_out="${2:-}"; shift 2 ;;
    --diagnostics-json-out) diagnostics_json_out="${2:-}"; shift 2 ;;
    --guard-markdown-out) guard_markdown_out="${2:-}"; shift 2 ;;
    --guard-json-out) guard_json_out="${2:-}"; shift 2 ;;
    --overview-markdown-out) overview_markdown_out="${2:-}"; shift 2 ;;
    --overview-json-out) overview_json_out="${2:-}"; shift 2 ;;
    --event-name) event_name="${2:-}"; shift 2 ;;
    --ref) ref_name="${2:-}"; shift 2 ;;
    --default-level) default_level="${2:-}"; shift 2 ;;
    --main-push-level) main_push_level="${2:-}"; shift 2 ;;
    --dispatch-override) dispatch_override="${2:-}"; shift 2 ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    --label) label="${2:-}"; shift 2 ;;
    --overview-label) overview_label="${2:-}"; shift 2 ;;
    --quiet) quiet="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${scope}" ] || [ -z "${source_path}" ] || [ -z "${diagnostics_markdown_out}" ] || [ -z "${diagnostics_json_out}" ] || [ -z "${guard_markdown_out}" ] || [ -z "${guard_json_out}" ] || [ -z "${overview_markdown_out}" ] || [ -z "${overview_json_out}" ] || [ -z "${event_name}" ] || [ -z "${ref_name}" ] || [ -z "${default_level}" ] || [ -z "${main_push_level}" ]; then
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

mkdir -p "$(dirname "${diagnostics_markdown_out}")" "$(dirname "${diagnostics_json_out}")"

case "${scope}" in
  frontend)
    bash frontend/scripts/ci_export_diagnostics.sh "${source_path}" "${diagnostics_json_out}" | tee "${diagnostics_markdown_out}"
    diagnostics_section_title="frontend-e2e export diagnostics"
    ;;
  backend)
    bash backend/scripts/ci_export_consistency_summary.sh "${source_path}" "${diagnostics_json_out}" | tee "${diagnostics_markdown_out}"
    diagnostics_section_title="backend-e2e export consistency"
    ;;
esac

if [ -n "${summary_file}" ]; then
  mkdir -p "$(dirname "${summary_file}")"
  {
    echo "### ${diagnostics_section_title}"
    cat "${diagnostics_markdown_out}"
  } >> "${summary_file}"
fi

pipeline_args=(
  --scope "${scope}"
  --diagnostics-json "${diagnostics_json_out}"
  --guard-markdown-out "${guard_markdown_out}"
  --guard-json-out "${guard_json_out}"
  --overview-markdown-out "${overview_markdown_out}"
  --overview-json-out "${overview_json_out}"
  --event-name "${event_name}"
  --ref "${ref_name}"
  --default-level "${default_level}"
  --main-push-level "${main_push_level}"
  --dispatch-override "${dispatch_override}"
  --summary-file "${summary_file}"
)

if [ -n "${label}" ]; then
  pipeline_args+=(--label "${label}")
fi
if [ -n "${overview_label}" ]; then
  pipeline_args+=(--overview-label "${overview_label}")
fi
if [ "${quiet}" = "1" ]; then
  pipeline_args+=(--quiet)
fi

bash scripts/ci_export_diag_pipeline.sh "${pipeline_args[@]}"
