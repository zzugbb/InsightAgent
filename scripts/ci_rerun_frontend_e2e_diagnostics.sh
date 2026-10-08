#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
api_base_url=""
frontend_base_url=""
frontend_dir="${repo_root}/frontend"
summary_file="${GITHUB_STEP_SUMMARY:-}"
markdown_out="/tmp/frontend-e2e-rerun-diagnostics.md"
json_out="/tmp/frontend-e2e-rerun-diagnostics.json"
log_out="/tmp/frontend-e2e-rerun-diagnostics.log"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_rerun_frontend_e2e_diagnostics.sh \
    --api-base-url <url> \
    --frontend-base-url <url> \
    [--frontend-dir <path>] \
    [--summary-file <path>] \
    [--markdown-out <path>] \
    [--json-out <path>] \
    [--log-out <path>]

Behavior:
  - Rerun only Playwright tests that failed in the previous run (same test-results dir).
  - Always exits 0 so the workflow job outcome stays driven by the primary e2e steps.
  - Writes an explicit diagnostic summary (including rerun exit code and skipped reason).
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --api-base-url) api_base_url="${2:-}"; shift 2 ;;
    --frontend-base-url) frontend_base_url="${2:-}"; shift 2 ;;
    --frontend-dir) frontend_dir="${2:-}"; shift 2 ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    --markdown-out) markdown_out="${2:-}"; shift 2 ;;
    --json-out) json_out="${2:-}"; shift 2 ;;
    --log-out) log_out="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${api_base_url}" ] || [ -z "${frontend_base_url}" ]; then
  echo "--api-base-url and --frontend-base-url are required" >&2
  usage >&2
  exit 2
fi

if [ "${frontend_dir#/}" = "${frontend_dir}" ]; then
  frontend_dir="${repo_root}/${frontend_dir}"
fi

last_run_json="${frontend_dir}/test-results/.last-run.json"
rerun_mode="skipped"
rerun_exit_code="0"
rerun_detail="no prior chromium full run metadata"

if [ -f "${last_run_json}" ]; then
  failed_count="$(
    python3 - "${last_run_json}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    print(0)
    raise SystemExit(0)
failed = data.get("status") == "failed" or bool(data.get("failedTests"))
if isinstance(data.get("failedTests"), list):
    print(len(data["failedTests"]))
elif failed:
    print(1)
else:
    print(0)
PY
  )"
  if [ "${failed_count}" = "0" ]; then
    rerun_mode="skipped"
    rerun_detail="last run recorded zero failed tests; not invoking --last-failed"
  else
    rerun_mode="last-failed"
    rerun_detail="invoking playwright --last-failed in ${frontend_dir}/test-results"
    set +e
    bash "${repo_root}/scripts/ci_run_frontend_e2e.sh" \
      --phase rerun-last-failed \
      --api-base-url "${api_base_url}" \
      --frontend-base-url "${frontend_base_url}" \
      --frontend-dir "${frontend_dir}" \
      > >(tee "${log_out}") 2>&1
    rerun_exit_code="$?"
    set -e
  fi
else
  rerun_mode="skipped"
  rerun_detail="missing ${last_run_json}; cannot scope --last-failed"
fi

gate_result="PASS"
if [ "${rerun_mode}" = "last-failed" ] && [ "${rerun_exit_code}" != "0" ]; then
  gate_result="FAIL"
fi

timestamp_utc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

{
  echo "### frontend-e2e diagnostic rerun (chromium)"
  echo "- timestamp_utc: ${timestamp_utc}"
  echo "- mode: ${rerun_mode}"
  echo "- detail: ${rerun_detail}"
  echo "- playwright_exit_code: ${rerun_exit_code}"
  echo "- diagnostic_gate_result: ${gate_result}"
  echo "- note: this step never changes the job conclusion; primary e2e steps remain authoritative"
} > "${markdown_out}"

python3 - "${json_out}" "${rerun_mode}" "${rerun_exit_code}" "${gate_result}" "${rerun_detail}" "${timestamp_utc}" <<'PY'
import json
import sys

out, mode, exit_code, gate, detail, ts = sys.argv[1:7]
payload = {
    "scope": "frontend-e2e",
    "kind": "diagnostic_rerun",
    "timestamp_utc": ts,
    "mode": mode,
    "playwright_exit_code": int(exit_code),
    "diagnostic_gate_result": gate,
    "detail": detail,
    "job_outcome_authoritative": "primary_e2e_steps",
}
with open(out, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY

if [ -n "${summary_file}" ]; then
  {
    echo
    cat "${markdown_out}"
  } >> "${summary_file}"
fi

echo "diagnostic_rerun_mode=${rerun_mode}"
echo "diagnostic_rerun_exit_code=${rerun_exit_code}"
echo "diagnostic_rerun_gate_result=${gate_result}"
echo "diagnostic_rerun_markdown=${markdown_out}"
echo "diagnostic_rerun_json=${json_out}"

exit 0
