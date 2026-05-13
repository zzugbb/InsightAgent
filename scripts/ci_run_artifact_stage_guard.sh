#!/usr/bin/env bash

set -euo pipefail

scope=""
repo_root="."
base_sha=""
head_sha="${GITHUB_SHA:-HEAD}"
dispatch_override="auto"
fallback_level=""
pr_level=""
included_count=""
missing_count=""
min_included_count="1"
stage_dir=""
manifest=""
summary_file=""
guard_markdown_out=""
guard_json_out=""
event_name="${GITHUB_EVENT_NAME:-}"
ref_name="${GITHUB_REF:-}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_run_artifact_stage_guard.sh \
    --scope <backend|frontend> \
    --repo-root <path> \
    --base-sha <sha> \
    --head-sha <sha> \
    --dispatch-override <auto|none|warn|fail-on-empty|fail-on-missing> \
    --fallback-level <none|warn|fail-on-empty|fail-on-missing> \
    --pr-level <none|warn|fail-on-empty|fail-on-missing> \
    --included-count <n> \
    --missing-count <n> \
    [--min-included-count <n>] \
    [--event-name <name>] \
    [--ref <ref>] \
    [--stage-dir <path>] \
    [--manifest <path>] \
    [--summary-file <path>] \
    [--guard-markdown-out <path>] \
    [--guard-json-out <path>]

Output:
  - changed_files_path=<path>
  - artifact_strict_level=<level>
  - artifact_policy_source=<source>
USAGE
}

extract_kv_value() {
  local key="$1"
  local file="$2"
  awk -F= -v k="${key}" '$1==k {print substr($0, length(k)+2)}' "${file}" | tail -n 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope) scope="${2:-}"; shift 2 ;;
    --repo-root) repo_root="${2:-}"; shift 2 ;;
    --base-sha) base_sha="${2:-}"; shift 2 ;;
    --head-sha) head_sha="${2:-}"; shift 2 ;;
    --dispatch-override) dispatch_override="${2:-}"; shift 2 ;;
    --fallback-level) fallback_level="${2:-}"; shift 2 ;;
    --pr-level) pr_level="${2:-}"; shift 2 ;;
    --included-count) included_count="${2:-}"; shift 2 ;;
    --missing-count) missing_count="${2:-}"; shift 2 ;;
    --min-included-count) min_included_count="${2:-}"; shift 2 ;;
    --event-name) event_name="${2:-}"; shift 2 ;;
    --ref) ref_name="${2:-}"; shift 2 ;;
    --stage-dir) stage_dir="${2:-}"; shift 2 ;;
    --manifest) manifest="${2:-}"; shift 2 ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    --guard-markdown-out) guard_markdown_out="${2:-}"; shift 2 ;;
    --guard-json-out) guard_json_out="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${scope}" ] || [ -z "${repo_root}" ] || [ -z "${fallback_level}" ] || [ -z "${pr_level}" ] || [ -z "${included_count}" ] || [ -z "${missing_count}" ]; then
  echo "missing required arguments" >&2
  usage >&2
  exit 2
fi

scope_config_file="$(mktemp)"
scope_env_file="$(mktemp)"
trap 'rm -f "${scope_config_file}" "${scope_env_file}"' EXIT

bash scripts/ci_resolve_artifact_stage_scope_config.sh \
  --scope "${scope}" \
  --repo-root "${repo_root}" > "${scope_config_file}"

bash scripts/ci_load_artifact_stage_scope_config.sh \
  --config-file "${scope_config_file}" \
  --output-file "${scope_env_file}"

# shellcheck disable=SC1090
source "${scope_env_file}"

collect_changed_files_cmd=(
  bash scripts/ci_collect_changed_files.sh
  --repo-root "${repo_root}"
  --event-name "${event_name}"
  --base-sha "${base_sha}"
  --head-sha "${head_sha}"
  --output-file "${ARTIFACT_CHANGED_FILES_PATH}"
)
for fallback_path in "${ARTIFACT_FALLBACK_PATHS[@]}"; do
  collect_changed_files_cmd+=(--fallback-path "${fallback_path}")
done
"${collect_changed_files_cmd[@]}" >/dev/null

artifact_level_out="$(
  bash scripts/ci_resolve_artifact_stage_path_level.sh \
    --scope "${scope}" \
    --changed-files "${ARTIFACT_CHANGED_FILES_PATH}" \
    --event-name "${event_name}" \
    --ref "${ref_name}" \
    --fallback-level "${fallback_level}" \
    --pr-level "${pr_level}" \
    --pr-ref-regex "${ARTIFACT_PR_REF_REGEX}" \
    --path-regex "${ARTIFACT_PATH_REGEX}" \
    --dispatch-override "${dispatch_override}"
)"

artifact_strict_level="$(printf '%s\n' "${artifact_level_out}" | awk -F= '$1=="strict_level"{print $2}')"
artifact_policy_source="$(printf '%s\n' "${artifact_level_out}" | awk -F= '$1=="policy_source"{print $2}')"
if [ -z "${artifact_strict_level}" ] || [ -z "${artifact_policy_source}" ]; then
  echo "failed to parse artifact strict-level resolver output" >&2
  echo "${artifact_level_out}" >&2
  exit 2
fi

if [ -z "${guard_markdown_out}" ]; then
  guard_markdown_out="${ARTIFACT_GUARD_MARKDOWN_OUT}"
fi
if [ -z "${guard_json_out}" ]; then
  guard_json_out="${ARTIFACT_GUARD_JSON_OUT}"
fi

bash scripts/ci_assert_artifact_stage_health.sh \
  --scope "${scope}" \
  --included-count "${included_count}" \
  --missing-count "${missing_count}" \
  --stage-dir "${stage_dir}" \
  --manifest "${manifest}" \
  --min-included-count "${min_included_count}" \
  --strict-level "${artifact_strict_level}" \
  --label "${ARTIFACT_GUARD_LABEL}" \
  --summary-file "${guard_markdown_out}" \
  --json-summary-file "${guard_json_out}" \
  --quiet

if [ -n "${summary_file}" ]; then
  {
    echo "${ARTIFACT_SUMMARY_HEADING}"
    echo "- policy: default=${fallback_level}, pr=${pr_level}"
    echo "- dispatch_override: ${dispatch_override}"
    echo "- policy_source: ${artifact_policy_source}"
    echo "- selected_strict_level: ${artifact_strict_level}"
  } >> "${summary_file}"
  if [ -n "${guard_markdown_out}" ] && [ -f "${guard_markdown_out}" ]; then
    cat "${guard_markdown_out}" >> "${summary_file}"
  fi
fi

echo "changed_files_path=${ARTIFACT_CHANGED_FILES_PATH}"
echo "artifact_strict_level=${artifact_strict_level}"
echo "artifact_policy_source=${artifact_policy_source}"
