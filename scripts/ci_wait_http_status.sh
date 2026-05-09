#!/usr/bin/env bash

set -euo pipefail

url=""
output_file=""
expected_code="200"
attempts="60"
interval_sec="1"
failure_message="service failed to become healthy"
failure_log_file=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_wait_http_status.sh --url <url> --output-file <path> [options]

Options:
  --expected-code <http_code>       Default: 200
  --attempts <n>                    Default: 60
  --interval-sec <seconds>          Default: 1
  --failure-message <text>          Default: "service failed to become healthy"
  --failure-log-file <path>         Optional log file to print on failure
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --url) url="${2:-}"; shift 2 ;;
    --output-file) output_file="${2:-}"; shift 2 ;;
    --expected-code) expected_code="${2:-}"; shift 2 ;;
    --attempts) attempts="${2:-}"; shift 2 ;;
    --interval-sec) interval_sec="${2:-}"; shift 2 ;;
    --failure-message) failure_message="${2:-}"; shift 2 ;;
    --failure-log-file) failure_log_file="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${url}" ] || [ -z "${output_file}" ]; then
  echo "--url and --output-file are required" >&2
  usage >&2
  exit 2
fi

mkdir -p "$(dirname "${output_file}")"

i=1
while [ "${i}" -le "${attempts}" ]; do
  code="$(curl -s -o "${output_file}" -w "%{http_code}" "${url}" || true)"
  if [ "${code}" = "${expected_code}" ]; then
    cat "${output_file}"
    exit 0
  fi
  sleep "${interval_sec}"
  i=$((i + 1))
done

echo "${failure_message}" >&2
if [ -n "${failure_log_file}" ] && [ -f "${failure_log_file}" ]; then
  cat "${failure_log_file}" >&2 || true
fi
exit 1
