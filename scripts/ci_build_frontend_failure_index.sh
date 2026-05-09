#!/usr/bin/env bash

set -euo pipefail

results_dir="frontend/test-results"
output_file="/tmp/frontend-e2e-failure-index.md"
run_id=""
run_attempt=""
generated_at_utc=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_build_frontend_failure_index.sh [options]

Options:
  --results-dir <path>      Default: frontend/test-results
  --output-file <path>      Default: /tmp/frontend-e2e-failure-index.md
  --run-id <value>          Optional run id for index metadata
  --run-attempt <value>     Optional run attempt for index metadata
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --results-dir) results_dir="${2:-}"; shift 2 ;;
    --output-file) output_file="${2:-}"; shift 2 ;;
    --run-id) run_id="${2:-}"; shift 2 ;;
    --run-attempt) run_attempt="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

generated_at_utc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
mkdir -p "$(dirname "${output_file}")"

{
  echo "# frontend-e2e failure index"
  echo
  echo "- generated_at_utc: ${generated_at_utc}"
  if [ -n "${run_id}" ]; then
    echo "- run_id: ${run_id}"
  fi
  if [ -n "${run_attempt}" ]; then
    echo "- run_attempt: ${run_attempt}"
  fi
  echo
  if [ -d "${results_dir}" ]; then
    echo "## error-context.md"
    find "${results_dir}" -name "error-context.md" | sort | sed 's#^#- #'
    echo
    echo "## trace.zip"
    find "${results_dir}" -name "trace.zip" | sort | sed 's#^#- #'
  else
    echo "No ${results_dir} directory found."
  fi
} > "${output_file}"

echo "output_file=${output_file}"
