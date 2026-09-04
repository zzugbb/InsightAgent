#!/usr/bin/env bash

set -euo pipefail

frontend_diag_json=""
frontend_guard_json=""
backend_diag_json=""
backend_guard_json=""
markdown_out=""
json_out=""
label="ci-export-diagnostics"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_export_diagnostics_overview.sh [options]

Options:
  --frontend-diagnostics-json <path>
  --frontend-guard-json <path>
  --backend-diagnostics-json <path>
  --backend-guard-json <path>
  --markdown-out <path>
  --json-out <path>
  --label <name>

Notes:
  - Missing inputs are allowed; script will mark each section as unavailable.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --frontend-diagnostics-json) frontend_diag_json="${2:-}"; shift 2 ;;
    --frontend-guard-json) frontend_guard_json="${2:-}"; shift 2 ;;
    --backend-diagnostics-json) backend_diag_json="${2:-}"; shift 2 ;;
    --backend-guard-json) backend_guard_json="${2:-}"; shift 2 ;;
    --markdown-out) markdown_out="${2:-}"; shift 2 ;;
    --json-out) json_out="${2:-}"; shift 2 ;;
    --label) label="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "${markdown_out}" ] || [ -z "${json_out}" ]; then
  echo "--markdown-out and --json-out are required" >&2
  usage >&2
  exit 2
fi

mkdir -p "$(dirname "${markdown_out}")" "$(dirname "${json_out}")"

python3 - "$frontend_diag_json" "$frontend_guard_json" "$backend_diag_json" "$backend_guard_json" "$markdown_out" "$json_out" "$label" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

frontend_diag_path, frontend_guard_path, backend_diag_path, backend_guard_path, markdown_out, json_out, label = sys.argv[1:]


def load_json(path):
    if not path:
        return None, False
    if not os.path.isfile(path):
        return None, False
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), True
    except (OSError, json.JSONDecodeError, TypeError):
        return None, False


def summarize_frontend_diag(data):
    if not data:
        return {"available": False}
    warnings = data.get("warnings", {})
    return {
        "available": True,
        "warning_total": int(warnings.get("total", 0) or 0),
        "warning_p0": int(warnings.get("p0", 0) or 0),
        "warning_p1": int(warnings.get("p1", 0) or 0),
    }


def summarize_backend_diag(data):
    if not data:
        return {"available": False}
    return {
        "available": True,
        "status": str(data.get("status", "unknown")),
        "warning_total": int(data.get("warning_total", 0) or 0),
        "warning_p0": int(data.get("warning_p0", 0) or 0),
        "warning_p1": int(data.get("warning_p1", 0) or 0),
    }


def summarize_guard(data):
    if not data:
        return {"available": False}
    return {
        "available": True,
        "scope": str(data.get("scope", "unknown")),
        "strict_level": str(data.get("strict_level", "unknown")),
        "gate_result": str(data.get("gate_result", "unknown")),
        "gate_reason": str(data.get("gate_reason", "")),
        "warning_total": int(data.get("warning_total", 0) or 0),
        "warning_p0": int(data.get("warning_p0", 0) or 0),
        "warning_p1": int(data.get("warning_p1", 0) or 0),
    }


def unique(items):
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def build_operator_summary(
    frontend_diag_summary,
    frontend_guard_summary,
    backend_diag_summary,
    backend_guard_summary,
    warning_total,
    warning_p0,
    warning_p1,
    guard_failure_count,
):
    missing_scopes = []
    warning_scopes = []
    blocking_guard_scopes = []

    scoped_parts = [
        ("frontend", frontend_diag_summary, frontend_guard_summary),
        ("backend", backend_diag_summary, backend_guard_summary),
    ]
    for scope, diag_summary, guard_summary in scoped_parts:
        if not diag_summary.get("available") or not guard_summary.get("available"):
            missing_scopes.append(scope)
        scope_warning_total = int(diag_summary.get("warning_total", 0) or 0) + int(guard_summary.get("warning_total", 0) or 0)
        if scope_warning_total > 0:
            warning_scopes.append(scope)
        if guard_summary.get("available") and guard_summary.get("gate_result") == "FAIL":
            blocking_guard_scopes.append(scope)

    if blocking_guard_scopes:
        status = "action_required"
        headline = "export diagnostics guard failures need attention"
        primary_action = "inspect_failed_artifact_guards"
        highest_severity = "critical"
        focus_scopes = blocking_guard_scopes
    elif missing_scopes:
        status = "review"
        headline = "export diagnostics inputs need review"
        primary_action = "review_missing_diagnostics_inputs"
        highest_severity = "info"
        focus_scopes = missing_scopes
    elif warning_total > 0:
        status = "review"
        headline = "export diagnostics warnings need review"
        primary_action = "review_diagnostics_warnings"
        highest_severity = "warning"
        focus_scopes = warning_scopes
    else:
        status = "ready"
        headline = "export diagnostics ready"
        primary_action = "continue_release_review"
        highest_severity = "ok"
        focus_scopes = ["frontend", "backend"]

    return {
        "status": status,
        "headline": headline,
        "primary_action": primary_action,
        "highest_severity": highest_severity,
        "warning_total": warning_total,
        "warning_p0": warning_p0,
        "warning_p1": warning_p1,
        "guard_failures": guard_failure_count,
        "focus_scopes": unique(focus_scopes),
        "blocking_guard_scopes": unique(blocking_guard_scopes),
    }

frontend_diag, frontend_diag_ok = load_json(frontend_diag_path)
frontend_guard, frontend_guard_ok = load_json(frontend_guard_path)
backend_diag, backend_diag_ok = load_json(backend_diag_path)
backend_guard, backend_guard_ok = load_json(backend_guard_path)

frontend_diag_summary = summarize_frontend_diag(frontend_diag)
frontend_guard_summary = summarize_guard(frontend_guard)
backend_diag_summary = summarize_backend_diag(backend_diag)
backend_guard_summary = summarize_guard(backend_guard)

all_warning_total = 0
all_warning_p0 = 0
all_warning_p1 = 0
for part in [frontend_diag_summary, backend_diag_summary]:
    if part.get("available"):
        all_warning_total += int(part.get("warning_total", 0))
        all_warning_p0 += int(part.get("warning_p0", 0))
        all_warning_p1 += int(part.get("warning_p1", 0))

guard_failures = 0
for g in [frontend_guard_summary, backend_guard_summary]:
    if g.get("available") and g.get("gate_result") == "FAIL":
        guard_failures += 1

operator_summary = build_operator_summary(
    frontend_diag_summary,
    frontend_guard_summary,
    backend_diag_summary,
    backend_guard_summary,
    all_warning_total,
    all_warning_p0,
    all_warning_p1,
    guard_failures,
)

overview = {
    "label": label,
    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "operator_summary": operator_summary,
    "frontend": {
        "diagnostics": frontend_diag_summary,
        "guard": frontend_guard_summary,
    },
    "backend": {
        "diagnostics": backend_diag_summary,
        "guard": backend_guard_summary,
    },
    "totals": {
        "warning_total": all_warning_total,
        "warning_p0": all_warning_p0,
        "warning_p1": all_warning_p1,
        "guard_failures": guard_failures,
    },
}

with open(json_out, "w", encoding="utf-8") as f:
    json.dump(overview, f, ensure_ascii=False, indent=2)

lines = []
lines.append(f"## export diagnostics overview ({label})")
lines.append(f"- generated_at_utc: {overview['generated_at_utc']}")
lines.append(f"- totals: warning_total={all_warning_total}, p0={all_warning_p0}, p1={all_warning_p1}, guard_failures={guard_failures}")
lines.append(f"- operator_status: {operator_summary['status']}")
lines.append(f"- operator_primary_action: {operator_summary['primary_action']}")
lines.append(f"- operator_focus_scopes: {','.join(operator_summary['focus_scopes']) or 'none'}")

if frontend_diag_summary.get("available"):
    lines.append("### frontend diagnostics")
    lines.append(f"- warnings: total={frontend_diag_summary['warning_total']}, p0={frontend_diag_summary['warning_p0']}, p1={frontend_diag_summary['warning_p1']}")
else:
    lines.append("### frontend diagnostics")
    lines.append("- unavailable")

if frontend_guard_summary.get("available"):
    lines.append("### frontend guard")
    lines.append(f"- strict_level={frontend_guard_summary['strict_level']}, gate_result={frontend_guard_summary['gate_result']}, reason={frontend_guard_summary['gate_reason']}")
else:
    lines.append("### frontend guard")
    lines.append("- unavailable")

if backend_diag_summary.get("available"):
    lines.append("### backend diagnostics")
    lines.append(f"- status={backend_diag_summary['status']}, warnings: total={backend_diag_summary['warning_total']}, p0={backend_diag_summary['warning_p0']}, p1={backend_diag_summary['warning_p1']}")
else:
    lines.append("### backend diagnostics")
    lines.append("- unavailable")

if backend_guard_summary.get("available"):
    lines.append("### backend guard")
    lines.append(f"- strict_level={backend_guard_summary['strict_level']}, gate_result={backend_guard_summary['gate_result']}, reason={backend_guard_summary['gate_reason']}")
else:
    lines.append("### backend guard")
    lines.append("- unavailable")

with open(markdown_out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
PY

echo "overview markdown written to ${markdown_out}"
echo "overview json written to ${json_out}"
