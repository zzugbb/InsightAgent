#!/usr/bin/env bash

set -euo pipefail

scope=""
dispatch_override="auto"
event_name=""
ref_name=""
default_level=""
main_push_level=""
summary_file=""

source_path=""
diagnostics_markdown_out=""
diagnostics_json_out=""
guard_markdown_out=""
guard_json_out=""
overview_markdown_out=""
overview_json_out=""
label=""
overview_label=""

artifacts_list_file=""
artifacts_stage_dir=""
artifact_name=""
min_included_count="1"
github_output_file=""
quiet="0"
dry_run="0"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_finalize_e2e_scope.sh \
    --scope <backend|frontend> \
    --event-name <name> \
    --ref <ref> \
    --default-level <none|p0|any> \
    --main-push-level <none|p0|any> \
    --summary-file <path> \
    [--dispatch-override <auto|none|p0|any>] \
    [--source-path <path>] \
    [--diagnostics-markdown-out <path>] \
    [--diagnostics-json-out <path>] \
    [--guard-markdown-out <path>] \
    [--guard-json-out <path>] \
    [--overview-markdown-out <path>] \
    [--overview-json-out <path>] \
    [--label <name>] \
    [--overview-label <name>] \
    [--artifacts-list-file <path>] \
    [--artifacts-stage-dir <path>] \
    [--artifact-name <name>] \
    [--min-included-count <n>] \
    [--github-output-file <path>] \
    [--quiet] \
    [--dry-run]

Behavior:
  - Run ci_export_diag_flow.sh for given scope
  - Stage artifacts via ci_stage_artifacts.sh
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope) scope="${2:-}"; shift 2 ;;
    --dispatch-override) dispatch_override="${2:-}"; shift 2 ;;
    --event-name) event_name="${2:-}"; shift 2 ;;
    --ref) ref_name="${2:-}"; shift 2 ;;
    --default-level) default_level="${2:-}"; shift 2 ;;
    --main-push-level) main_push_level="${2:-}"; shift 2 ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    --source-path) source_path="${2:-}"; shift 2 ;;
    --diagnostics-markdown-out) diagnostics_markdown_out="${2:-}"; shift 2 ;;
    --diagnostics-json-out) diagnostics_json_out="${2:-}"; shift 2 ;;
    --guard-markdown-out) guard_markdown_out="${2:-}"; shift 2 ;;
    --guard-json-out) guard_json_out="${2:-}"; shift 2 ;;
    --overview-markdown-out) overview_markdown_out="${2:-}"; shift 2 ;;
    --overview-json-out) overview_json_out="${2:-}"; shift 2 ;;
    --label) label="${2:-}"; shift 2 ;;
    --overview-label) overview_label="${2:-}"; shift 2 ;;
    --artifacts-list-file) artifacts_list_file="${2:-}"; shift 2 ;;
    --artifacts-stage-dir) artifacts_stage_dir="${2:-}"; shift 2 ;;
    --artifact-name) artifact_name="${2:-}"; shift 2 ;;
    --min-included-count) min_included_count="${2:-}"; shift 2 ;;
    --github-output-file) github_output_file="${2:-}"; shift 2 ;;
    --quiet) quiet="1"; shift ;;
    --dry-run) dry_run="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${scope}" ] || [ -z "${event_name}" ] || [ -z "${ref_name}" ] || [ -z "${default_level}" ] || [ -z "${main_push_level}" ] || [ -z "${summary_file}" ]; then
  echo "missing required arguments" >&2
  usage >&2
  exit 2
fi

case "${scope}" in
  backend)
    : "${source_path:=/tmp/e2e-export-consistency-8000.log}"
    : "${diagnostics_markdown_out:=/tmp/e2e-export-consistency-summary.txt}"
    : "${diagnostics_json_out:=/tmp/e2e-export-consistency-summary.json}"
    : "${guard_markdown_out:=/tmp/backend-e2e-export-guard-summary.md}"
    : "${guard_json_out:=/tmp/backend-e2e-export-guard-summary.json}"
    : "${overview_markdown_out:=/tmp/backend-e2e-export-overview.md}"
    : "${overview_json_out:=/tmp/backend-e2e-export-overview.json}"
    : "${label:=backend-e2e-export}"
    : "${overview_label:=backend-e2e}"
    : "${artifacts_list_file:=scripts/ci_artifacts_backend.txt}"
    : "${artifacts_stage_dir:=/tmp/backend-e2e-artifacts-stage}"
    : "${artifact_name:=backend-e2e-artifacts}"
    ;;
  frontend)
    : "${source_path:=frontend/test-results}"
    : "${diagnostics_markdown_out:=/tmp/frontend-e2e-export-summary.md}"
    : "${diagnostics_json_out:=/tmp/frontend-e2e-export-summary.json}"
    : "${guard_markdown_out:=/tmp/frontend-e2e-export-guard-summary.md}"
    : "${guard_json_out:=/tmp/frontend-e2e-export-guard-summary.json}"
    : "${overview_markdown_out:=/tmp/frontend-e2e-export-overview.md}"
    : "${overview_json_out:=/tmp/frontend-e2e-export-overview.json}"
    : "${label:=frontend-e2e-export}"
    : "${overview_label:=frontend-e2e}"
    : "${artifacts_list_file:=scripts/ci_artifacts_frontend.txt}"
    : "${artifacts_stage_dir:=/tmp/frontend-e2e-artifacts-stage}"
    : "${artifact_name:=playwright-report}"
    ;;
  *)
    echo "invalid --scope: ${scope} (expected backend|frontend)" >&2
    exit 2
    ;;
esac

flow_cmd=(
  bash scripts/ci_export_diag_flow.sh
  --scope "${scope}"
  --source-path "${source_path}"
  --diagnostics-markdown-out "${diagnostics_markdown_out}"
  --diagnostics-json-out "${diagnostics_json_out}"
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
  --label "${label}"
  --overview-label "${overview_label}"
)
if [ "${quiet}" = "1" ]; then
  flow_cmd+=(--quiet)
fi

stage_cmd=(
  bash scripts/ci_stage_artifacts.sh
  --list-file "${artifacts_list_file}"
  --output-dir "${artifacts_stage_dir}"
)

extract_kv_value() {
  local key="$1"
  local text="$2"
  printf '%s\n' "${text}" | awk -F= -v k="${key}" '$1==k {print substr($0, length(k)+2)}' | tail -n 1
}

if [ "${dry_run}" = "1" ]; then
  echo "[dry-run] ${flow_cmd[*]}"
  echo "[dry-run] ${stage_cmd[*]}"
  echo "[dry-run] artifact_name=${artifact_name}"
  echo "[dry-run] artifacts_stage_dir=${artifacts_stage_dir}"
  echo "[dry-run] min_included_count=${min_included_count}"
  exit 0
fi

"${flow_cmd[@]}"
stage_output="$("${stage_cmd[@]}")"
printf '%s\n' "${stage_output}"

staged_output_dir="$(extract_kv_value "staged_output_dir" "${stage_output}")"
included_count="$(extract_kv_value "included_count" "${stage_output}")"
missing_count="$(extract_kv_value "missing_count" "${stage_output}")"
stage_manifest="$(extract_kv_value "manifest" "${stage_output}")"

if [ -z "${staged_output_dir}" ]; then
  staged_output_dir="${artifacts_stage_dir}"
fi
if [ -z "${included_count}" ]; then
  included_count="0"
fi
if [ -z "${missing_count}" ]; then
  missing_count="0"
fi
if [ -z "${stage_manifest}" ]; then
  stage_manifest="${artifacts_stage_dir}/_manifest.txt"
fi

{
  echo
  echo "### ${overview_label} artifact stage"
  echo "- output_dir: ${staged_output_dir}"
  echo "- included_count: ${included_count}"
  echo "- missing_count: ${missing_count}"
  echo "- min_included_count: ${min_included_count}"
  echo "- manifest: ${stage_manifest}"
} >> "${summary_file}"

if [ -n "${github_output_file}" ]; then
  mkdir -p "$(dirname "${github_output_file}")"
  {
    echo "artifacts_stage_dir=${staged_output_dir}"
    echo "artifact_name=${artifact_name}"
    echo "scope=${scope}"
    echo "artifact_included_count=${included_count}"
    echo "artifact_missing_count=${missing_count}"
    echo "artifact_min_included_count=${min_included_count}"
    echo "artifact_manifest=${stage_manifest}"
  } >> "${github_output_file}"
fi

echo "artifact_name=${artifact_name}"
echo "artifacts_stage_dir=${staged_output_dir}"
echo "artifact_included_count=${included_count}"
echo "artifact_missing_count=${missing_count}"
echo "artifact_min_included_count=${min_included_count}"
echo "artifact_manifest=${stage_manifest}"
