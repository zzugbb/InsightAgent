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
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), True


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

overview = {
    "label": label,
    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
