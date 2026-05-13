#!/usr/bin/env bash

set -euo pipefail

config_file=""
output_file=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_load_artifact_stage_scope_config.sh \
    --config-file <path> \
    --output-file <path>

Behavior:
  - Read key/value lines from ci_resolve_artifact_stage_scope_config.sh output
  - Write a shell snippet that exports parsed variables
USAGE
}

shell_quote() {
  printf "%q" "$1"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --config-file) config_file="${2:-}"; shift 2 ;;
    --output-file) output_file="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${config_file}" ] || [ -z "${output_file}" ]; then
  echo "missing required arguments: --config-file/--output-file" >&2
  usage >&2
  exit 2
fi

if [ ! -f "${config_file}" ]; then
  echo "config file not found: ${config_file}" >&2
  exit 2
fi

extract_single_value() {
  local key="$1"
  awk -F= -v k="${key}" '$1==k {print substr($0, length(k)+2)}' "${config_file}" | tail -n 1
}

changed_files_path="$(extract_single_value "changed_files_path")"
path_regex="$(extract_single_value "path_regex")"
pr_ref_regex="$(extract_single_value "pr_ref_regex")"
guard_label="$(extract_single_value "guard_label")"
summary_heading="$(extract_single_value "summary_heading")"
guard_markdown_out="$(extract_single_value "guard_markdown_out")"
guard_json_out="$(extract_single_value "guard_json_out")"
fallback_paths=()
while IFS= read -r fallback_path; do
  fallback_paths+=("${fallback_path}")
done < <(awk -F= '$1=="fallback_path" {print substr($0, length($1)+2)}' "${config_file}")

if [ -z "${changed_files_path}" ] || [ -z "${path_regex}" ] || [ -z "${pr_ref_regex}" ] || [ -z "${guard_label}" ] || [ -z "${summary_heading}" ] || [ -z "${guard_markdown_out}" ] || [ -z "${guard_json_out}" ] || [ "${#fallback_paths[@]}" -eq 0 ]; then
  echo "failed to parse artifact stage scope config from ${config_file}" >&2
  exit 2
fi

mkdir -p "$(dirname "${output_file}")"
{
  echo "ARTIFACT_CHANGED_FILES_PATH=$(shell_quote "${changed_files_path}")"
  echo "ARTIFACT_PATH_REGEX=$(shell_quote "${path_regex}")"
  echo "ARTIFACT_PR_REF_REGEX=$(shell_quote "${pr_ref_regex}")"
  echo "ARTIFACT_GUARD_LABEL=$(shell_quote "${guard_label}")"
  echo "ARTIFACT_SUMMARY_HEADING=$(shell_quote "${summary_heading}")"
  echo "ARTIFACT_GUARD_MARKDOWN_OUT=$(shell_quote "${guard_markdown_out}")"
  echo "ARTIFACT_GUARD_JSON_OUT=$(shell_quote "${guard_json_out}")"
  printf 'ARTIFACT_FALLBACK_PATHS=('
  for fallback_path in "${fallback_paths[@]}"; do
    printf ' %s' "$(shell_quote "${fallback_path}")"
  done
  echo " )"
} > "${output_file}"
