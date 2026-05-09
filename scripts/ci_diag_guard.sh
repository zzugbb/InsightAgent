#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_diag_guard.sh --json <path> --scope <frontend|backend> [--strict-level <none|p0|any>] [--label <name>] [--summary-file <path>] [--json-summary-file <path>]

Behavior:
  - strict-level=none: always pass
  - strict-level=p0: fail when P0 warnings > 0
  - strict-level=any: fail when total warnings > 0
USAGE
}

json_path=""
scope=""
strict_level="none"
label=""
summary_file=""
json_summary_file=""
quiet="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --json)
      json_path="${2:-}"
      shift 2
      ;;
    --scope)
      scope="${2:-}"
      shift 2
      ;;
    --strict-level)
      strict_level="${2:-}"
      shift 2
      ;;
    --label)
      label="${2:-}"
      shift 2
      ;;
    --summary-file)
      summary_file="${2:-}"
      shift 2
      ;;
    --json-summary-file)
      json_summary_file="${2:-}"
      shift 2
      ;;
    --quiet)
      quiet="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${json_path}" ] || [ -z "${scope}" ]; then
  echo "missing required arguments --json/--scope" >&2
  usage >&2
  exit 2
fi
if [ -z "${label}" ]; then
  label="${scope}"
fi

if [ ! -f "${json_path}" ]; then
  echo "[diag-guard][${label}] json file not found: ${json_path}" >&2
  exit 2
fi

if [ "${scope}" != "frontend" ] && [ "${scope}" != "backend" ]; then
  echo "[diag-guard][${label}] invalid scope: ${scope}" >&2
  exit 2
fi
if [ "${strict_level}" != "none" ] && [ "${strict_level}" != "p0" ] && [ "${strict_level}" != "any" ]; then
  echo "[diag-guard][${label}] invalid strict-level: ${strict_level}" >&2
  exit 2
fi

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

parsed=()
while IFS= read -r line; do
  parsed+=("$line")
done < <(python3 - "${json_path}" "${scope}" <<'PY'
import json, sys
path = sys.argv[1]
scope = sys.argv[2]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

if scope == "frontend":
    warnings = data.get("warnings", {})
    total = int(warnings.get("total", 0) or 0)
    p0 = int(warnings.get("p0", 0) or 0)
    p1 = int(warnings.get("p1", 0) or 0)
    status = "ok"
else:
    total = int(data.get("warning_total", 0) or 0)
    p0 = int(data.get("warning_p0", 0) or 0)
    p1 = int(data.get("warning_p1", 0) or 0)
    status = str(data.get("status", "ok"))

print(total)
print(p0)
print(p1)
print(status)
PY
)

warning_total="${parsed[0]:-0}"
warning_p0="${parsed[1]:-0}"
warning_p1="${parsed[2]:-0}"
status="${parsed[3]:-unknown}"

if [ "${quiet}" != "1" ]; then
  echo "[diag-guard][${label}] strict_level=${strict_level} status=${status} warnings(total=${warning_total}, p0=${warning_p0}, p1=${warning_p1})"
fi

gate_result="PASS"
gate_reason="within threshold"
exit_code=0

case "${strict_level}" in
  none)
    gate_result="PASS"
    gate_reason="strict-level none"
    ;;
  p0)
    if [ "${warning_p0}" -gt 0 ]; then
      gate_result="FAIL"
      gate_reason="strict-level p0 requires p0=0"
      exit_code=1
    fi
    ;;
  any)
    if [ "${warning_total}" -gt 0 ]; then
      gate_result="FAIL"
      gate_reason="strict-level any requires total=0"
      exit_code=1
    fi
    ;;
esac

if [ -n "${summary_file}" ]; then
  mkdir -p "$(dirname "${summary_file}")"
  {
    echo "### diag guard: ${label}"
    echo "- scope: ${scope}"
    echo "- strict_level: ${strict_level}"
    echo "- status: ${status}"
    echo "- warnings: total=${warning_total}, p0=${warning_p0}, p1=${warning_p1}"
    echo "- gate_result: ${gate_result}"
    echo "- gate_reason: ${gate_reason}"
  } > "${summary_file}"
fi

if [ -n "${json_summary_file}" ]; then
  mkdir -p "$(dirname "${json_summary_file}")"
  cat > "${json_summary_file}" <<JSON
{
  "label": "$(json_escape "${label}")",
  "scope": "$(json_escape "${scope}")",
  "strict_level": "$(json_escape "${strict_level}")",
  "status": "$(json_escape "${status}")",
  "warning_total": ${warning_total},
  "warning_p0": ${warning_p0},
  "warning_p1": ${warning_p1},
  "gate_result": "$(json_escape "${gate_result}")",
  "gate_reason": "$(json_escape "${gate_reason}")"
}
JSON
fi

if [ "${exit_code}" -ne 0 ]; then
  echo "[diag-guard][${label}] FAIL: ${gate_reason}" >&2
fi

exit "${exit_code}"
