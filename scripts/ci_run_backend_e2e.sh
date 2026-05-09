#!/usr/bin/env bash

set -euo pipefail

phase=""
base_url=""
log_dir="/tmp"
dry_run="0"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_run_backend_e2e.sh --phase <main|timeout> --base-url <url> [options]

Options:
  --log-dir <path>    Default: /tmp
  --dry-run           Print commands without executing
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --phase) phase="${2:-}"; shift 2 ;;
    --base-url) base_url="${2:-}"; shift 2 ;;
    --log-dir) log_dir="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${phase}" ] || [ -z "${base_url}" ]; then
  echo "--phase and --base-url are required" >&2
  usage >&2
  exit 2
fi

if [ "${phase}" != "main" ] && [ "${phase}" != "timeout" ]; then
  echo "invalid --phase: ${phase} (expected main|timeout)" >&2
  exit 2
fi

mkdir -p "${log_dir}"

run_cmd() {
  local cmd="$1"
  if [ "${dry_run}" = "1" ]; then
    echo "[dry-run] ${cmd}"
  else
    eval "${cmd}"
  fi
}

if [ "${phase}" = "main" ]; then
  run_cmd "python3 backend/scripts/e2e_baseline.py --base-url ${base_url} | tee ${log_dir}/e2e-baseline-8000.log"
  run_cmd "python3 backend/scripts/e2e_main_path.py --base-url ${base_url} | tee ${log_dir}/e2e-main-path-8000.log"
  run_cmd "python3 backend/scripts/e2e_export_consistency.py --base-url ${base_url} | tee ${log_dir}/e2e-export-consistency-8000.log"
  run_cmd "python3 backend/scripts/e2e_task_cancel_timeout.py --base-url ${base_url} --skip-timeout | tee ${log_dir}/e2e-cancel-8000.log"
else
  run_cmd "python3 backend/scripts/e2e_task_cancel_timeout.py --base-url ${base_url} --cancel-prompt-words 180000 --timeout-prompt-words 250000 | tee ${log_dir}/e2e-timeout-8010.log"
fi
