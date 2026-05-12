#!/usr/bin/env bash

set -euo pipefail

scope=""
summary_file=""
reason=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_write_skipped_artifact_guard_summary.sh \
    --scope <backend|frontend> \
    --summary-file <path> \
    --reason <text>
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope) scope="${2:-}"; shift 2 ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    --reason) reason="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${scope}" ] || [ -z "${summary_file}" ] || [ -z "${reason}" ]; then
  echo "missing required arguments: --scope/--summary-file/--reason" >&2
  usage >&2
  exit 2
fi

case "${scope}" in
  backend) heading="### backend-e2e artifact stage guard" ;;
  frontend) heading="### frontend-e2e artifact stage guard" ;;
  *)
    echo "invalid --scope: ${scope} (expected backend|frontend)" >&2
    exit 2
    ;;
esac

mkdir -p "$(dirname "${summary_file}")"
{
  echo "${heading}"
  echo "- skipped: true"
  echo "- reason: ${reason}"
} >> "${summary_file}"
