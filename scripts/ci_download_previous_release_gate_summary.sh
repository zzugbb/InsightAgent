#!/usr/bin/env bash

set -euo pipefail

workflow="release-gate.yml"
branch=""
current_run_id=""
artifact_name="release-gate-summary"
output_file="/tmp/previous-release-gate-summary.json"
summary_file=""
json_summary_file=""
download_dir=""
gh_bin="${GH_BIN:-gh}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_download_previous_release_gate_summary.sh \
    [--workflow <workflow-file>] \
    --branch <branch> \
    --current-run-id <id> \
    [--artifact-name <artifact-name>] \
    [--output-file <path>] \
    [--summary-file <path>] \
    [--json-summary-file <path>] \
    [--download-dir <path>] \
    [--gh-bin <path-or-command>]

Download the latest previous successful release gate summary artifact for the
same branch. Missing GitHub CLI, missing context, or missing artifacts are
reported as low-sensitivity diagnostics and exit successfully so the current
release gate can still publish a baseline trend summary.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --workflow) workflow="${2:-}"; shift 2 ;;
    --branch) branch="${2:-}"; shift 2 ;;
    --current-run-id) current_run_id="${2:-}"; shift 2 ;;
    --artifact-name) artifact_name="${2:-}"; shift 2 ;;
    --output-file) output_file="${2:-}"; shift 2 ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    --json-summary-file) json_summary_file="${2:-}"; shift 2 ;;
    --download-dir) download_dir="${2:-}"; shift 2 ;;
    --gh-bin) gh_bin="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

python_bin="${CI_JSON_TOOL_PYTHON:-}"
if [ -z "${python_bin}" ]; then
  if [ -x "backend/.venv/bin/python" ]; then
    python_bin="backend/.venv/bin/python"
  else
    python_bin="python3"
  fi
fi

write_summary() {
  local previous_available="$1"
  local reason="$2"
  local previous_run_id="${3:-}"

  "${python_bin}" - \
    "${summary_file}" \
    "${json_summary_file}" \
    "${workflow}" \
    "${branch}" \
    "${current_run_id}" \
    "${artifact_name}" \
    "${output_file}" \
    "${previous_available}" \
    "${reason}" \
    "${previous_run_id}" <<'PY'
import json
import sys
from pathlib import Path

(
    summary_path,
    json_path,
    workflow,
    branch,
    current_run_id,
    artifact_name,
    output_file,
    previous_available_raw,
    reason,
    previous_run_id_raw,
) = sys.argv[1:11]

previous_available = previous_available_raw == "true"
previous_run_id = int(previous_run_id_raw) if previous_run_id_raw else None
output_exists = Path(output_file).is_file()

if previous_available:
    operator_summary = {
        "status": "ready",
        "headline": "previous release gate summary available",
        "primary_action": "compare_release_gate_trend",
        "highest_severity": "ok",
        "previous_available": True,
        "reason": reason,
        "focus_areas": ["trend"],
        "blocking_reasons": [],
    }
elif reason in {"missing_branch", "missing_current_run_id", "missing_workflow", "missing_artifact_name"}:
    operator_summary = {
        "status": "review",
        "headline": "release gate context missing for previous summary lookup",
        "primary_action": "provide_release_gate_context",
        "highest_severity": "info",
        "previous_available": False,
        "reason": reason,
        "focus_areas": ["release_context"],
        "blocking_reasons": [reason],
    }
elif reason == "no_previous_success":
    operator_summary = {
        "status": "review",
        "headline": "no previous release gate summary is available",
        "primary_action": "accept_baseline_without_previous_summary",
        "highest_severity": "info",
        "previous_available": False,
        "reason": reason,
        "focus_areas": ["trend_baseline"],
        "blocking_reasons": [],
    }
else:
    operator_summary = {
        "status": "review",
        "headline": "previous summary download needs review",
        "primary_action": "review_previous_summary_baseline",
        "highest_severity": "warning",
        "previous_available": False,
        "reason": reason,
        "focus_areas": ["github_artifact"],
        "blocking_reasons": [reason],
    }

payload = {
    "summary_schema_version": 1,
    "summary_kind": "release_gate_previous_summary_download",
    "operator_summary": operator_summary,
    "previous_available": previous_available,
    "reason": reason,
    "workflow": workflow,
    "branch": branch,
    "current_run_id": int(current_run_id) if current_run_id.isdigit() else current_run_id,
    "previous_run_id": previous_run_id,
    "artifact_name": artifact_name,
    "output_file": output_file,
    "output_file_exists": output_exists,
}

lines = [
    "### release gate previous summary download",
    "- summary_schema_version: 1",
    "- summary_kind: release_gate_previous_summary_download",
    f"- previous_available: {'yes' if previous_available else 'no'}",
    f"- reason: {reason}",
    f"- operator_status: {operator_summary['status']}",
    f"- operator_primary_action: {operator_summary['primary_action']}",
    f"- operator_focus_areas: {','.join(operator_summary['focus_areas']) or 'none'}",
    f"- workflow: {workflow or 'unknown'}",
    f"- branch: {branch or 'unknown'}",
    f"- current_run_id: {current_run_id or 'unknown'}",
    f"- previous_run_id: {previous_run_id if previous_run_id is not None else 'none'}",
    f"- artifact_name: {artifact_name}",
    f"- output_file_exists: {'yes' if output_exists else 'no'}",
    "",
]

if summary_path:
    path = Path(summary_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"release_gate_previous_summary_download={summary_path}")
else:
    print("\n".join(lines))

if json_path:
    path = Path(json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"release_gate_previous_summary_download_json={json_path}")
PY
}

resolve_gh_bin() {
  if command -v "${gh_bin}" >/dev/null 2>&1; then
    command -v "${gh_bin}"
    return 0
  fi
  if [ -x "${gh_bin}" ]; then
    printf '%s\n' "${gh_bin}"
    return 0
  fi
  return 1
}

select_previous_run_id() {
  local runs_json="$1"
  "${python_bin}" - "${runs_json}" "${current_run_id}" <<'PY'
import json
import sys

runs_path, current_run_id = sys.argv[1:3]
try:
    with open(runs_path, "r", encoding="utf-8") as handle:
        runs = json.load(handle)
except Exception as exc:
    raise SystemExit(f"invalid run list JSON: {exc}")

if not isinstance(runs, list):
    raise SystemExit("run list JSON must be an array")

current = str(current_run_id)
for run in runs:
    if not isinstance(run, dict):
        continue
    run_id = run.get("databaseId") or run.get("id")
    if run_id is None or str(run_id) == current:
        continue
    if run.get("status") not in (None, "completed"):
        continue
    if run.get("conclusion") not in (None, "success"):
        continue
    print(run_id)
    break
PY
}

if [ -z "${branch}" ]; then
  write_summary "false" "missing_branch"
  exit 0
fi

if [ -z "${current_run_id}" ]; then
  write_summary "false" "missing_current_run_id"
  exit 0
fi

if [ -z "${workflow}" ]; then
  write_summary "false" "missing_workflow"
  exit 0
fi

if [ -z "${artifact_name}" ]; then
  write_summary "false" "missing_artifact_name"
  exit 0
fi

resolved_gh_bin="$(resolve_gh_bin || true)"
if [ -z "${resolved_gh_bin}" ]; then
  write_summary "false" "gh_unavailable"
  exit 0
fi

tmp_root=""
if [ -z "${download_dir}" ]; then
  tmp_root="$(mktemp -d)"
  download_dir="${tmp_root}/artifact"
  trap 'rm -rf "${tmp_root:-}"' EXIT
fi
mkdir -p "${download_dir}"
mkdir -p "$(dirname "${output_file}")"

runs_json="${download_dir}/release-gate-runs.json"
if ! "${resolved_gh_bin}" run list \
  --workflow "${workflow}" \
  --branch "${branch}" \
  --status success \
  --json databaseId,status,conclusion \
  --limit 20 > "${runs_json}"; then
  write_summary "false" "run_list_failed"
  exit 0
fi

previous_run_id="$(select_previous_run_id "${runs_json}" | head -n 1 || true)"
if [ -z "${previous_run_id}" ]; then
  write_summary "false" "no_previous_success"
  exit 0
fi

artifact_dir="${download_dir}/${artifact_name}-${previous_run_id}"
mkdir -p "${artifact_dir}"
if ! "${resolved_gh_bin}" run download "${previous_run_id}" \
  --name "${artifact_name}" \
  --dir "${artifact_dir}"; then
  write_summary "false" "download_failed" "${previous_run_id}"
  exit 0
fi

downloaded_summary="$(find "${artifact_dir}" -type f -name 'release-gate-summary.json' -print -quit)"
if [ -z "${downloaded_summary}" ]; then
  write_summary "false" "artifact_missing" "${previous_run_id}"
  exit 0
fi

cp "${downloaded_summary}" "${output_file}"
write_summary "true" "downloaded" "${previous_run_id}"
