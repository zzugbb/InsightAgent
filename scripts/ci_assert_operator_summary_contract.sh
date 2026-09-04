#!/usr/bin/env bash

set -euo pipefail

summary_json=""
summary_kind=""
markdown_file=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_assert_operator_summary_contract.sh \
    --summary-json <path> \
    --summary-kind <kind> \
    [--markdown <path>]

Validate low-sensitivity operator_summary fields in release/operator-facing
summaries. This script only reads local summary files and does not start
services.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --summary-json) summary_json="${2:-}"; shift 2 ;;
    --summary-kind) summary_kind="${2:-}"; shift 2 ;;
    --markdown) markdown_file="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${summary_json}" ] || [ -z "${summary_kind}" ]; then
  echo "--summary-json and --summary-kind are required" >&2
  usage >&2
  exit 2
fi

if [ ! -f "${summary_json}" ]; then
  echo "summary json not found: ${summary_json}" >&2
  exit 1
fi

if [ -n "${markdown_file}" ] && [ ! -f "${markdown_file}" ]; then
  echo "markdown summary not found: ${markdown_file}" >&2
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

"${python_bin}" - "${summary_json}" "${summary_kind}" "${markdown_file}" <<'PY'
import json
import re
import sys
from pathlib import Path
from typing import Any


summary_path, expected_kind, markdown_path = sys.argv[1:4]

VALID_STATUSES = {"ready", "review", "action_required"}
VALID_SEVERITIES = {"ok", "info", "warning", "critical"}
REQUIRED_STRING_FIELDS = ("status", "headline", "primary_action", "highest_severity")
SENSITIVE_TOKEN_RE = re.compile(
    r"(secret|token|api[_-]?key|password|private[_-]?key|connection[_-]?string)",
    re.IGNORECASE,
)
SENSITIVE_PATH_RE = re.compile(r"(^|\s)(/[^\s]+|[A-Za-z]:\\[^\s]+)")


def fail(message: str) -> None:
    raise SystemExit(f"operator summary contract failed: {message}")


def load_json(path: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid summary json: {exc}")
    if not isinstance(data, dict):
        fail("summary json must be an object")
    return data


def iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(iter_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(iter_strings(item))
        return strings
    return []


def validate_string_value(context: str, value: str) -> None:
    if SENSITIVE_TOKEN_RE.search(value):
        fail(f"{context} contains sensitive token-like text")
    if SENSITIVE_PATH_RE.search(value):
        fail(f"{context} contains path-like text")
    if "\n" in value or "\r" in value:
        fail(f"{context} contains multiline text")


def validate_operator_summary(context: str, summary: Any) -> None:
    if not isinstance(summary, dict):
        fail(f"{context} must be an object")
    for field in REQUIRED_STRING_FIELDS:
        value = summary.get(field)
        if not isinstance(value, str) or not value.strip():
            fail(f"{context}.{field} must be a non-empty string")
    if summary["status"] not in VALID_STATUSES:
        fail(f"{context}.status has unsupported value: {summary['status']}")
    if summary["highest_severity"] not in VALID_SEVERITIES:
        fail(f"{context}.highest_severity has unsupported value: {summary['highest_severity']}")
    for key, value in summary.items():
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, (str, int, float, bool)):
                    fail(f"{context}.{key} list contains non-scalar value")
        elif not isinstance(value, (str, int, float, bool, type(None))):
            fail(f"{context}.{key} must be scalar or a scalar list")
    for text in iter_strings(summary):
        validate_string_value(context, text)


def collect_operator_summaries(data: dict[str, Any]) -> list[tuple[str, Any]]:
    if expected_kind == "release_gate_trend":
        current = data.get("current") if isinstance(data.get("current"), dict) else {}
        previous = data.get("previous") if isinstance(data.get("previous"), dict) else None
        summaries = [("current.operator_summary", current.get("operator_summary"))]
        if previous is not None:
            summaries.append(("previous.operator_summary", previous.get("operator_summary")))
        return summaries
    return [("operator_summary", data.get("operator_summary"))]


data = load_json(summary_path)
actual_kind = str(data.get("summary_kind") or "")
if actual_kind and actual_kind != expected_kind:
    fail(f"summary_kind mismatch: expected {expected_kind}, got {actual_kind}")

summaries = collect_operator_summaries(data)
if not summaries:
    fail("no operator_summary found")
for context, summary in summaries:
    validate_operator_summary(context, summary)

markdown_status = "not_checked"
if markdown_path:
    markdown = Path(markdown_path).read_text(encoding="utf-8")
    has_status = "- operator_status:" in markdown or "- current_operator_status:" in markdown
    has_action = "- operator_primary_action:" in markdown or "- current_operator_primary_action:" in markdown
    if not has_status or not has_action:
        fail("markdown summary must expose operator status and primary action")
    markdown_status = "yes"

print("operator_summary_contract=PASS")
print(f"summary_kind={expected_kind}")
print(f"operator_summary_count={len(summaries)}")
print(f"markdown_operator_summary={markdown_status}")
PY
