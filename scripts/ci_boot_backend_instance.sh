#!/usr/bin/env bash

set -euo pipefail

host="127.0.0.1"
port=""
health_path="/health"
log_file=""
pid_file=""
attempts="60"
interval_sec="1"
failure_message=""
app_dir="backend"
app_target="app.main:app"
dry_run="0"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_boot_backend_instance.sh --port <port> --log-file <path> [options]

Options:
  --host <host>                  Default: 127.0.0.1
  --health-path <path>           Default: /health
  --pid-file <path>              Optional
  --attempts <n>                 Default: 60
  --interval-sec <seconds>       Default: 1
  --failure-message <text>       Optional; default uses host/port
  --app-dir <path>               Default: backend
  --app-target <module:app>      Default: app.main:app
  --dry-run                      Print commands only
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --host) host="${2:-}"; shift 2 ;;
    --port) port="${2:-}"; shift 2 ;;
    --health-path) health_path="${2:-}"; shift 2 ;;
    --log-file) log_file="${2:-}"; shift 2 ;;
    --pid-file) pid_file="${2:-}"; shift 2 ;;
    --attempts) attempts="${2:-}"; shift 2 ;;
    --interval-sec) interval_sec="${2:-}"; shift 2 ;;
    --failure-message) failure_message="${2:-}"; shift 2 ;;
    --app-dir) app_dir="${2:-}"; shift 2 ;;
    --app-target) app_target="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${port}" ] || [ -z "${log_file}" ]; then
  echo "--port and --log-file are required" >&2
  usage >&2
  exit 2
fi

if [ -z "${failure_message}" ]; then
  failure_message="backend ${host}:${port} failed to become healthy"
fi

health_url="http://${host}:${port}${health_path}"
health_output="/tmp/health-${port}.json"

start_cmd=(bash scripts/ci_start_bg_process.sh --log-file "${log_file}")
if [ -n "${pid_file}" ]; then
  start_cmd+=(--pid-file "${pid_file}")
fi
start_cmd+=(-- uvicorn "${app_target}" --app-dir "${app_dir}" --host "${host}" --port "${port}")

wait_cmd=(
  bash scripts/ci_wait_http_status.sh
  --url "${health_url}"
  --output-file "${health_output}"
  --attempts "${attempts}"
  --interval-sec "${interval_sec}"
  --failure-message "${failure_message}"
  --failure-log-file "${log_file}"
)

if [ "${dry_run}" = "1" ]; then
  echo "[dry-run] ${start_cmd[*]}"
  echo "[dry-run] ${wait_cmd[*]}"
  exit 0
fi

"${start_cmd[@]}"
"${wait_cmd[@]}"

echo "health_output=${health_output}"
