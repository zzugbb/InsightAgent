#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
phase=""
base_url=""
log_dir="/tmp"
dry_run="0"
backend_e2e_python="${BACKEND_E2E_PYTHON:-}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_run_backend_e2e.sh --phase <main|timeout|queue> --base-url <url> [options]

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

if [ "${phase}" != "main" ] && [ "${phase}" != "timeout" ] && [ "${phase}" != "queue" ]; then
  echo "invalid --phase: ${phase} (expected main|timeout|queue)" >&2
  exit 2
fi

mkdir -p "${log_dir}"
if [ "${log_dir#/}" = "${log_dir}" ]; then
  log_dir="$(cd "${log_dir}" && pwd)"
fi

if [ -z "${backend_e2e_python}" ]; then
  if [ -x "${repo_root}/backend/.venv/bin/python" ]; then
    backend_e2e_python="backend/.venv/bin/python"
  else
    backend_e2e_python="python3"
  fi
fi

base_url_without_scheme="${base_url#*://}"
base_url_authority="${base_url_without_scheme%%/*}"
if [[ "${base_url_authority}" == *:* ]]; then
  log_suffix="${base_url_authority##*:}"
else
  log_suffix="${base_url_authority//[^A-Za-z0-9_.-]/_}"
fi
if [ -z "${log_suffix}" ]; then
  log_suffix="backend"
fi

run_cmd() {
  local cmd="$1"
  if [ "${dry_run}" = "1" ]; then
    echo "[dry-run] ${cmd}"
  else
    eval "${cmd}"
  fi
}

shell_quote() {
  printf "%q" "$1"
}

quoted_backend_e2e_python="$(shell_quote "${backend_e2e_python}")"
quoted_base_url="$(shell_quote "${base_url}")"
quoted_log_dir="$(shell_quote "${log_dir}")"

cd "${repo_root}"

if [ "${phase}" = "main" ]; then
  run_cmd "${quoted_backend_e2e_python} backend/scripts/e2e_baseline.py --base-url ${quoted_base_url} | tee ${quoted_log_dir}/e2e-baseline-${log_suffix}.log"
  run_cmd "${quoted_backend_e2e_python} backend/scripts/e2e_main_path.py --base-url ${quoted_base_url} | tee ${quoted_log_dir}/e2e-main-path-${log_suffix}.log"
  run_cmd "${quoted_backend_e2e_python} backend/scripts/e2e_export_consistency.py --base-url ${quoted_base_url} | tee ${quoted_log_dir}/e2e-export-consistency-${log_suffix}.log"
  run_cmd "${quoted_backend_e2e_python} backend/scripts/e2e_task_cancel_timeout.py --base-url ${quoted_base_url} --skip-timeout | tee ${quoted_log_dir}/e2e-cancel-${log_suffix}.log"
elif [ "${phase}" = "timeout" ]; then
  run_cmd "${quoted_backend_e2e_python} backend/scripts/e2e_task_cancel_timeout.py --base-url ${quoted_base_url} --cancel-prompt-words 180000 --timeout-prompt-words 250000 | tee ${quoted_log_dir}/e2e-timeout-${log_suffix}.log"
else
  run_cmd "${quoted_backend_e2e_python} backend/scripts/e2e_queue_concurrency.py --base-url ${quoted_base_url} | tee ${quoted_log_dir}/e2e-queue-${log_suffix}.log"
fi
