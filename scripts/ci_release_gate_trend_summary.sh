#!/usr/bin/env bash

set -euo pipefail

current_json=""
previous_json=""
summary_file=""
json_summary_file=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_release_gate_trend_summary.sh \
    --current-json <path> \
    [--previous-json <path>] \
    [--summary-file <path>] \
    [--json-summary-file <path>]

Build a trend-friendly release gate summary from the current release gate JSON
summary and an optional previous summary. This script only reads summary files;
it does not start services or run release gates.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --current-json) current_json="${2:-}"; shift 2 ;;
    --previous-json) previous_json="${2:-}"; shift 2 ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    --json-summary-file) json_summary_file="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${current_json}" ]; then
  echo "missing required argument: --current-json" >&2
  usage >&2
  exit 2
fi

if [ ! -f "${current_json}" ]; then
  echo "current summary not found: ${current_json}" >&2
  exit 1
fi

if [ -n "${previous_json}" ] && [ ! -f "${previous_json}" ]; then
  echo "previous summary not found: ${previous_json}" >&2
  exit 1
fi

python_bin="${CI_JSON_TOOL_PYTHON:-}"
if [ -z "${python_bin}" ]; then
  if [ -x "backend/.venv/bin/python" ]; then
    python_bin="backend/.venv/bin/python"
  else
    python_bin="python3"
  fi
fi

"${python_bin}" - "${current_json}" "${previous_json}" "${summary_file}" "${json_summary_file}" <<'PY'
import json
import sys
from pathlib import Path


def load_json(path: str) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"summary must be a JSON object: {path}")
    return data


def step_summary(data: dict) -> dict:
    raw = data.get("step_summary") if isinstance(data.get("step_summary"), dict) else {}
    return {
        "total": int(raw.get("total") or 0),
        "pass": int(raw.get("pass") or 0),
        "fail": int(raw.get("fail") or 0),
        "dry_run": int(raw.get("dry_run") or 0),
    }


def failed_labels(data: dict) -> list[str]:
    raw = data.get("failed_step_labels")
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if str(item)]


def decision_summary(data: dict) -> dict:
    raw = data.get("decision_summary") if isinstance(data.get("decision_summary"), dict) else {}
    follow_up_raw = raw.get("required_follow_up")
    follow_up = follow_up_raw if isinstance(follow_up_raw, list) else []
    return {
        "release_decision": str(raw.get("release_decision") or ""),
        "rollback_decision": str(raw.get("rollback_decision") or ""),
        "reason": str(raw.get("reason") or ""),
        "required_follow_up": [str(item) for item in follow_up if str(item)],
    }


def operator_summary(data: dict) -> dict:
    raw = data.get("operator_summary") if isinstance(data.get("operator_summary"), dict) else {}
    focus_phases_raw = raw.get("focus_phases")
    blocking_labels_raw = raw.get("blocking_step_labels")
    focus_phases = focus_phases_raw if isinstance(focus_phases_raw, list) else []
    blocking_labels = blocking_labels_raw if isinstance(blocking_labels_raw, list) else []
    return {
        "status": str(raw.get("status") or ""),
        "headline": str(raw.get("headline") or ""),
        "primary_action": str(raw.get("primary_action") or ""),
        "highest_severity": str(raw.get("highest_severity") or ""),
        "total_steps": int(raw.get("total_steps") or 0),
        "failed_steps": int(raw.get("failed_steps") or 0),
        "focus_phases": [str(item) for item in focus_phases if str(item)],
        "blocking_step_labels": [str(item) for item in blocking_labels if str(item)],
    }


def compact_release_gate(data: dict) -> dict:
    return {
        "summary_kind": str(data.get("summary_kind") or ""),
        "summary_schema_version": int(data.get("summary_schema_version") or 0),
        "service_required": bool(data.get("service_required", False)),
        "phase": str(data.get("phase") or ""),
        "result": str(data.get("result") or "UNKNOWN"),
        "resolved_phases": str(data.get("resolved_phases") or ""),
        "step_summary": step_summary(data),
        "failed_step_labels": failed_labels(data),
        "decision_summary": decision_summary(data),
        "operator_summary": operator_summary(data),
    }


def delta(current: dict, previous: dict) -> dict:
    return {
        key: current["step_summary"][key] - previous["step_summary"][key]
        for key in ("total", "pass", "fail", "dry_run")
    }


def trend_result(current: dict, previous: dict | None, deltas: dict) -> str:
    if previous is None:
        return "baseline"
    if deltas["fail"] < 0:
        return "improved"
    if deltas["fail"] > 0:
        return "regressed"
    if current["result"] != previous["result"]:
        return "changed"
    return "unchanged"


def markdown_list(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


current_path, previous_path, summary_path, json_path = sys.argv[1:5]
current = compact_release_gate(load_json(current_path))
previous = compact_release_gate(load_json(previous_path)) if previous_path else None
deltas = delta(current, previous) if previous is not None else {"total": 0, "pass": 0, "fail": 0, "dry_run": 0}
current_failed = set(current["failed_step_labels"])
previous_failed = set(previous["failed_step_labels"]) if previous is not None else set()
added_failed = sorted(current_failed - previous_failed)
removed_failed = sorted(previous_failed - current_failed)
result = trend_result(current, previous, deltas)

payload = {
    "summary_schema_version": 1,
    "summary_kind": "release_gate_trend",
    "source_summary_kind": current["summary_kind"],
    "previous_available": previous is not None,
    "trend_result": result,
    "current": current,
    "previous": previous,
    "step_deltas": deltas,
    "added_failed_step_labels": added_failed,
    "removed_failed_step_labels": removed_failed,
}

lines = [
    "### release gate trend",
    "- summary_schema_version: 1",
    "- summary_kind: release_gate_trend",
    f"- source_summary_kind: {current['summary_kind'] or 'unknown'}",
    f"- previous_available: {'yes' if previous is not None else 'no'}",
    f"- trend_result: {result}",
    f"- current_result: {current['result']}",
]
if previous is not None:
    lines.append(f"- previous_result: {previous['result']}")
lines.extend([
    f"- current_total_steps: {current['step_summary']['total']}",
    f"- current_failed_steps: {current['step_summary']['fail']}",
])
if previous is not None:
    lines.append(f"- previous_failed_steps: {previous['step_summary']['fail']}")
lines.extend([
    f"- current_operator_status: {current['operator_summary']['status'] or 'unknown'}",
    f"- current_operator_primary_action: {current['operator_summary']['primary_action'] or 'unknown'}",
    f"- current_operator_focus_phases: {markdown_list(current['operator_summary']['focus_phases'])}",
])
if previous is not None:
    lines.extend([
        f"- previous_operator_status: {previous['operator_summary']['status'] or 'unknown'}",
        f"- previous_operator_primary_action: {previous['operator_summary']['primary_action'] or 'unknown'}",
    ])
lines.extend([
    f"- failed_steps_delta: {deltas['fail']:+d}",
    f"- current_failed_step_labels: {markdown_list(current['failed_step_labels'])}",
    f"- added_failed_step_labels: {markdown_list(added_failed)}",
    f"- removed_failed_step_labels: {markdown_list(removed_failed)}",
])
lines.append("")

if summary_path:
    path = Path(summary_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"release_gate_trend_summary={summary_path}")
else:
    print("\n".join(lines))

if json_path:
    path = Path(json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"release_gate_trend_json_summary={json_path}")
PY
