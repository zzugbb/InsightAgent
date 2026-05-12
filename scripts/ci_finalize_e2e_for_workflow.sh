#!/usr/bin/env bash

set -euo pipefail

scope=""
event_name="${GITHUB_EVENT_NAME:-}"
ref_name="${GITHUB_REF:-}"
default_level=""
main_push_level=""
dispatch_override="auto"
summary_file=""
github_output_file=""
artifact_name=""
min_included_count=""
run_id="${GITHUB_RUN_ID:-}"
run_attempt="${GITHUB_RUN_ATTEMPT:-}"

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

quiet="0"
dry_run="0"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_finalize_e2e_for_workflow.sh \
    --scope <backend|frontend> \
    --summary-file <path> \
    [--github-output-file <path>] \
    [--dispatch-override <auto|none|p0|any>] \
    [--event-name <name>] \
    [--ref <ref>] \
    [--default-level <none|p0|any>] \
    [--main-push-level <none|p0|any>] \
    [--artifact-name <name>] \
    [--min-included-count <n>] \
    [--run-id <id>] \
    [--run-attempt <n>] \
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
    [--quiet] \
    [--dry-run]

Behavior:
  - Resolve per-scope defaults for strict levels and artifact name
  - Delegate to scripts/ci_finalize_e2e_scope.sh
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope) scope="${2:-}"; shift 2 ;;
    --event-name) event_name="${2:-}"; shift 2 ;;
    --ref) ref_name="${2:-}"; shift 2 ;;
    --default-level) default_level="${2:-}"; shift 2 ;;
    --main-push-level) main_push_level="${2:-}"; shift 2 ;;
    --dispatch-override) dispatch_override="${2:-}"; shift 2 ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    --github-output-file) github_output_file="${2:-}"; shift 2 ;;
    --artifact-name) artifact_name="${2:-}"; shift 2 ;;
    --min-included-count) min_included_count="${2:-}"; shift 2 ;;
    --run-id) run_id="${2:-}"; shift 2 ;;
    --run-attempt) run_attempt="${2:-}"; shift 2 ;;
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

if [ -z "${scope}" ] || [ -z "${summary_file}" ]; then
  echo "missing required arguments: --scope, --summary-file" >&2
  usage >&2
  exit 2
fi

if [ -z "${event_name}" ] || [ -z "${ref_name}" ]; then
  echo "missing event context: provide --event-name/--ref or set GITHUB_EVENT_NAME/GITHUB_REF" >&2
  exit 2
fi

case "${scope}" in
  backend)
    : "${default_level:=${BACKEND_EXPORT_DIAG_STRICT_LEVEL_DEFAULT:-p0}}"
    : "${main_push_level:=${BACKEND_EXPORT_DIAG_STRICT_LEVEL_MAIN_PUSH:-any}}"
    : "${min_included_count:=${BACKEND_ARTIFACT_STAGE_MIN_INCLUDED_COUNT:-}}"
    : "${artifact_name:=backend-e2e-artifacts}"
    ;;
  frontend)
    : "${default_level:=${FRONTEND_EXPORT_DIAG_STRICT_LEVEL_DEFAULT:-p0}}"
    : "${main_push_level:=${FRONTEND_EXPORT_DIAG_STRICT_LEVEL_MAIN_PUSH:-any}}"
    : "${min_included_count:=${FRONTEND_ARTIFACT_STAGE_MIN_INCLUDED_COUNT:-}}"
    if [ -z "${artifact_name}" ]; then
      if [ -n "${run_id}" ] && [ -n "${run_attempt}" ]; then
        artifact_name="playwright-report-${run_id}-${run_attempt}"
      else
        artifact_name="playwright-report"
      fi
    fi
    ;;
  *)
    echo "invalid --scope: ${scope} (expected backend|frontend)" >&2
    exit 2
    ;;
esac

cmd=(
  bash scripts/ci_finalize_e2e_scope.sh
  --scope "${scope}"
  --event-name "${event_name}"
  --ref "${ref_name}"
  --default-level "${default_level}"
  --main-push-level "${main_push_level}"
  --dispatch-override "${dispatch_override}"
  --summary-file "${summary_file}"
  --artifact-name "${artifact_name}"
)
if [ -n "${min_included_count}" ]; then
  cmd+=(--min-included-count "${min_included_count}")
fi

if [ -n "${github_output_file}" ]; then
  cmd+=(--github-output-file "${github_output_file}")
fi
if [ -n "${min_included_count}" ]; then
  cmd+=(--min-included-count "${min_included_count}")
fi
if [ -n "${source_path}" ]; then
  cmd+=(--source-path "${source_path}")
fi
if [ -n "${diagnostics_markdown_out}" ]; then
  cmd+=(--diagnostics-markdown-out "${diagnostics_markdown_out}")
fi
if [ -n "${diagnostics_json_out}" ]; then
  cmd+=(--diagnostics-json-out "${diagnostics_json_out}")
fi
if [ -n "${guard_markdown_out}" ]; then
  cmd+=(--guard-markdown-out "${guard_markdown_out}")
fi
if [ -n "${guard_json_out}" ]; then
  cmd+=(--guard-json-out "${guard_json_out}")
fi
if [ -n "${overview_markdown_out}" ]; then
  cmd+=(--overview-markdown-out "${overview_markdown_out}")
fi
if [ -n "${overview_json_out}" ]; then
  cmd+=(--overview-json-out "${overview_json_out}")
fi
if [ -n "${label}" ]; then
  cmd+=(--label "${label}")
fi
if [ -n "${overview_label}" ]; then
  cmd+=(--overview-label "${overview_label}")
fi
if [ -n "${artifacts_list_file}" ]; then
  cmd+=(--artifacts-list-file "${artifacts_list_file}")
fi
if [ -n "${artifacts_stage_dir}" ]; then
  cmd+=(--artifacts-stage-dir "${artifacts_stage_dir}")
fi
if [ "${quiet}" = "1" ]; then
  cmd+=(--quiet)
fi
if [ "${dry_run}" = "1" ]; then
  cmd+=(--dry-run)
fi

"${cmd[@]}"
