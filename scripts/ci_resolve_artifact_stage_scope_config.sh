#!/usr/bin/env bash

set -euo pipefail

scope=""
repo_root=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_resolve_artifact_stage_scope_config.sh \
    --scope <backend|frontend> \
    [--repo-root <path>]

Output:
  - changed_files_path=<path>
  - path_regex=<regex>
  - pr_ref_regex=<regex>
  - guard_label=<label>
  - summary_heading=<markdown heading>
  - guard_markdown_out=<path>
  - guard_json_out=<path>
  - fallback_path=<path>   # repeated for each fallback path
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope) scope="${2:-}"; shift 2 ;;
    --repo-root) repo_root="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${scope}" ]; then
  echo "missing required argument: --scope" >&2
  usage >&2
  exit 2
fi

prefix=""
if [ -n "${repo_root}" ]; then
  prefix="${repo_root%/}/"
fi

case "${scope}" in
  backend)
    changed_files_path="${prefix}.github/backend-e2e-changed-files.txt"
    path_regex='^(backend/|compose\.full\.yml$|\.github/workflows/backend-e2e\.yml$)'
    pr_ref_regex='^(refs/pull/[0-9]+/merge)$'
    guard_label='backend-e2e-artifact-stage'
    summary_heading='### backend-e2e artifact strict policy'
    guard_markdown_out='/tmp/backend-e2e-artifact-guard-summary.md'
    guard_json_out='/tmp/backend-e2e-artifact-guard-summary.json'
    fallback_paths=(
      "backend/"
      "compose.full.yml"
      ".github/workflows/backend-e2e.yml"
    )
    ;;
  frontend)
    changed_files_path="${prefix}.github/frontend-e2e-changed-files.txt"
    path_regex='^(frontend/|backend/|compose\.full\.yml$|\.github/workflows/frontend-e2e\.yml$)'
    pr_ref_regex='^(refs/pull/[0-9]+/merge)$'
    guard_label='frontend-e2e-artifact-stage'
    summary_heading='### frontend-e2e artifact strict policy'
    guard_markdown_out='/tmp/frontend-e2e-artifact-guard-summary.md'
    guard_json_out='/tmp/frontend-e2e-artifact-guard-summary.json'
    fallback_paths=(
      "frontend/"
      "backend/"
      "compose.full.yml"
      ".github/workflows/frontend-e2e.yml"
    )
    ;;
  *)
    echo "invalid --scope: ${scope} (expected backend|frontend)" >&2
    exit 2
    ;;
esac

echo "changed_files_path=${changed_files_path}"
echo "path_regex=${path_regex}"
echo "pr_ref_regex=${pr_ref_regex}"
echo "guard_label=${guard_label}"
echo "summary_heading=${summary_heading}"
echo "guard_markdown_out=${guard_markdown_out}"
echo "guard_json_out=${guard_json_out}"
for fallback_path in "${fallback_paths[@]}"; do
  echo "fallback_path=${fallback_path}"
done
