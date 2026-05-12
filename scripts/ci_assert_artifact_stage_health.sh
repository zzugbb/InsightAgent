#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_assert_artifact_stage_health.sh \
    --scope <backend|frontend> \
    --included-count <n> \
    --missing-count <n> \
    [--min-included-count <n>] \
    [--stage-dir <path>] \
    [--manifest <path>] \
    [--strict-level <none|warn|fail-on-empty|fail-on-missing>] \
    [--label <name>] \
    [--summary-file <path>] \
    [--json-summary-file <path>] \
    [--quiet]

Behavior:
  - none: always pass
  - warn: always pass, but emit warning status when counts look suspicious
  - fail-on-empty: fail when included_count < min_included_count
  - fail-on-missing: fail when missing_count > 0
USAGE
}

scope=""
included_count=""
missing_count=""
min_included_count="1"
stage_dir=""
manifest=""
strict_level="warn"
label=""
summary_file=""
json_summary_file=""
quiet="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope) scope="${2:-}"; shift 2 ;;
    --included-count) included_count="${2:-}"; shift 2 ;;
    --missing-count) missing_count="${2:-}"; shift 2 ;;
    --min-included-count) min_included_count="${2:-}"; shift 2 ;;
    --stage-dir) stage_dir="${2:-}"; shift 2 ;;
    --manifest) manifest="${2:-}"; shift 2 ;;
    --strict-level) strict_level="${2:-}"; shift 2 ;;
    --label) label="${2:-}"; shift 2 ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    --json-summary-file) json_summary_file="${2:-}"; shift 2 ;;
    --quiet) quiet="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${scope}" ] || [ -z "${included_count}" ] || [ -z "${missing_count}" ]; then
  echo "missing required arguments: --scope/--included-count/--missing-count" >&2
  usage >&2
  exit 2
fi

if [ "${scope}" != "backend" ] && [ "${scope}" != "frontend" ]; then
  echo "[artifact-guard] invalid scope: ${scope}" >&2
  exit 2
fi

if [ -z "${label}" ]; then
  label="${scope}"
fi

if [ "${strict_level}" != "none" ] && [ "${strict_level}" != "warn" ] && [ "${strict_level}" != "fail-on-empty" ] && [ "${strict_level}" != "fail-on-missing" ]; then
  echo "[artifact-guard][${label}] invalid strict-level: ${strict_level}" >&2
  exit 2
fi

is_non_negative_int() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

if ! is_non_negative_int "${included_count}" || ! is_non_negative_int "${missing_count}"; then
  echo "[artifact-guard][${label}] included/missing counts must be non-negative integers" >&2
  exit 2
fi
if ! is_non_negative_int "${min_included_count}"; then
  echo "[artifact-guard][${label}] min-included-count must be a non-negative integer" >&2
  exit 2
fi

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

status="ok"
if [ "${included_count}" -lt "${min_included_count}" ] || [ "${missing_count}" -gt 0 ]; then
  status="warning"
fi

gate_result="PASS"
gate_reason="within threshold"
exit_code=0

case "${strict_level}" in
  none)
    gate_result="PASS"
    gate_reason="strict-level none"
    ;;
  warn)
    gate_result="PASS"
    if [ "${status}" = "warning" ]; then
      gate_reason="strict-level warn allows warnings"
    else
      gate_reason="strict-level warn and no warning signals"
    fi
    ;;
  fail-on-empty)
    if [ "${included_count}" -lt "${min_included_count}" ]; then
      gate_result="FAIL"
      gate_reason="strict-level fail-on-empty requires included_count>=${min_included_count}"
      exit_code=1
    fi
    ;;
  fail-on-missing)
    if [ "${missing_count}" -gt 0 ]; then
      gate_result="FAIL"
      gate_reason="strict-level fail-on-missing requires missing_count=0"
      exit_code=1
    fi
    ;;
esac

if [ "${quiet}" != "1" ]; then
  echo "[artifact-guard][${label}] strict_level=${strict_level} status=${status} included=${included_count} missing=${missing_count} gate=${gate_result}"
fi

if [ -n "${summary_file}" ]; then
  mkdir -p "$(dirname "${summary_file}")"
  {
    echo "### artifact stage guard: ${label}"
    echo "- scope: ${scope}"
    echo "- strict_level: ${strict_level}"
    echo "- status: ${status}"
    echo "- included_count: ${included_count}"
    echo "- missing_count: ${missing_count}"
    echo "- min_included_count: ${min_included_count}"
    echo "- stage_dir: ${stage_dir:-unknown}"
    echo "- manifest: ${manifest:-unknown}"
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
  "included_count": ${included_count},
  "missing_count": ${missing_count},
  "min_included_count": ${min_included_count},
  "stage_dir": "$(json_escape "${stage_dir}")",
  "manifest": "$(json_escape "${manifest}")",
  "gate_result": "$(json_escape "${gate_result}")",
  "gate_reason": "$(json_escape "${gate_reason}")"
}
JSON
fi

if [ "${exit_code}" -ne 0 ]; then
  echo "[artifact-guard][${label}] FAIL: ${gate_reason}" >&2
fi

exit "${exit_code}"
