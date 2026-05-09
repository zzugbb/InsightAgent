#!/usr/bin/env bash

set -euo pipefail

log_file=""
pid_file=""
workdir=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_start_bg_process.sh [options] -- <command> [args...]

Options:
  --log-file <path>   Required. Redirect stdout/stderr to this file.
  --pid-file <path>   Optional. Write spawned process pid.
  --workdir <path>    Optional. Run command in this directory.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --log-file) log_file="${2:-}"; shift 2 ;;
    --pid-file) pid_file="${2:-}"; shift 2 ;;
    --workdir) workdir="${2:-}"; shift 2 ;;
    --) shift; break ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${log_file}" ]; then
  echo "--log-file is required" >&2
  usage >&2
  exit 2
fi
if [ "$#" -eq 0 ]; then
  echo "missing command after --" >&2
  usage >&2
  exit 2
fi
if [ -n "${workdir}" ] && [ ! -d "${workdir}" ]; then
  echo "workdir not found: ${workdir}" >&2
  exit 2
fi

mkdir -p "$(dirname "${log_file}")"
if [ -n "${pid_file}" ]; then
  mkdir -p "$(dirname "${pid_file}")"
fi

if [ -n "${workdir}" ]; then
  cd "${workdir}"
fi

nohup "$@" >"${log_file}" 2>&1 &
pid=$!

if [ -n "${pid_file}" ]; then
  printf '%s\n' "${pid}" > "${pid_file}"
fi

echo "started_pid=${pid}"
echo "log_file=${log_file}"
if [ -n "${pid_file}" ]; then
  echo "pid_file=${pid_file}"
fi
