#!/usr/bin/env bash

set -euo pipefail

output_file=""
primary_health_url="http://127.0.0.1:8000/health"
secondary_health_url="http://127.0.0.1:8010/health"
export_log_file="/tmp/e2e-export-consistency-8000.log"
export_log_tail_lines="80"
process_pattern="python|uvicorn"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_collect_backend_failure_diagnostics.sh --output-file <path> [options]

Options:
  --primary-health-url <url>      Default: http://127.0.0.1:8000/health
  --secondary-health-url <url>    Default: http://127.0.0.1:8010/health
  --export-log-file <path>        Default: /tmp/e2e-export-consistency-8000.log
  --export-log-tail-lines <n>     Default: 80
  --process-pattern <regex>       Default: python|uvicorn
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-file) output_file="${2:-}"; shift 2 ;;
    --primary-health-url) primary_health_url="${2:-}"; shift 2 ;;
    --secondary-health-url) secondary_health_url="${2:-}"; shift 2 ;;
    --export-log-file) export_log_file="${2:-}"; shift 2 ;;
    --export-log-tail-lines) export_log_tail_lines="${2:-}"; shift 2 ;;
    --process-pattern) process_pattern="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${output_file}" ]; then
  echo "--output-file is required" >&2
  usage >&2
  exit 2
fi

mkdir -p "$(dirname "${output_file}")"

{
  echo "===== date ====="
  date -u
  echo ""
  echo "===== ps -ef (${process_pattern}) ====="
  ps -ef 2>&1 | grep -E "${process_pattern}" || true
  echo ""
  echo "===== health primary ====="
  curl -s -i -m 5 "${primary_health_url}" 2>&1 || true
  echo ""
  echo "===== health secondary ====="
  curl -s -i -m 5 "${secondary_health_url}" 2>&1 || true
  echo ""
  echo "===== export consistency tail ====="
  tail -n "${export_log_tail_lines}" "${export_log_file}" || true
} > "${output_file}"

echo "output_file=${output_file}"
