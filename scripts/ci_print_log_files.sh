#!/usr/bin/env bash

set -euo pipefail

title="log files"
files=()

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_print_log_files.sh [options] --file <path> [--file <path> ...]

Options:
  --title <text>   Optional header title. Default: "log files"
  --file <path>    Log file path to print. Repeatable.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --title) title="${2:-}"; shift 2 ;;
    --file) files+=("${2:-}"); shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "${#files[@]}" -eq 0 ]; then
  echo "at least one --file is required" >&2
  usage >&2
  exit 2
fi

echo "===== ${title} ====="
for file in "${files[@]}"; do
  echo "===== ${file} ====="
  if [ -f "${file}" ]; then
    cat "${file}" || true
  else
    echo "(missing)"
  fi
done
