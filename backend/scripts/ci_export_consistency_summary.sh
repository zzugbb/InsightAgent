#!/usr/bin/env bash

set -euo pipefail

log_file="${1:-/tmp/e2e-export-consistency-8000.log}"

echo "## Export Consistency Snapshot"

if [ ! -f "${log_file}" ]; then
  echo
  echo "- Export consistency log is missing."
  exit 0
fi

STEP_REGEX='^\[[0-9]+/[0-9]+\]'
OK_LINE_REGEX='^  - OK:'
PASS_BANNER_REGEX='^E2E export consistency passed:'
TASK_EXPORT_REGEX='task export json/markdown consistency \+ download'
SESSION_EXPORT_REGEX='session export json/markdown consistency \+ download'
SHARED_RAG_REGEX='shared-rag role semantics remain compatible with export flow'
CROSS_USER_REGEX='cross-user export isolation checks'
NOT_FOUND_REGEX='export not-found responses'
KEY_LINES_REGEX='^\[[0-9]+/[0-9]+\]|^  - OK:|^E2E export consistency passed:|^- '

step_count=$(grep -Ec "${STEP_REGEX}" "${log_file}" || true)
ok_count=$(grep -Ec "${OK_LINE_REGEX}" "${log_file}" || true)
step_total_expected=$(grep -Eo "${STEP_REGEX}" "${log_file}" | head -n 1 | sed -E 's#^\[[0-9]+/([0-9]+)\]#\1#' || true)
passed_count=$(grep -Ec "${PASS_BANNER_REGEX}" "${log_file}" || true)
task_export_ok=$(grep -Ec "${TASK_EXPORT_REGEX}" "${log_file}" || true)
session_export_ok=$(grep -Ec "${SESSION_EXPORT_REGEX}" "${log_file}" || true)
shared_rag_ok=$(grep -Ec "${SHARED_RAG_REGEX}" "${log_file}" || true)
cross_user_ok=$(grep -Ec "${CROSS_USER_REGEX}" "${log_file}" || true)
not_found_ok=$(grep -Ec "${NOT_FOUND_REGEX}" "${log_file}" || true)

warning_count=0
p0_warning_count=0
p1_warning_count=0
warning_messages=""

add_warning() {
  local severity="$1"
  local scope="$2"
  local detail="$3"
  warning_count=$((warning_count + 1))
  if [ "${severity}" = "P0" ]; then
    p0_warning_count=$((p0_warning_count + 1))
  else
    p1_warning_count=$((p1_warning_count + 1))
  fi
  warning_messages="${warning_messages}\n  - [${severity}][${scope}] ${detail}"
}

if ! [[ "${step_total_expected}" =~ ^[0-9]+$ ]] || [ "${step_total_expected}" -lt 1 ]; then
  add_warning "P0" "backend-export-consistency" "step_total_expected parse failed, got ${step_total_expected:-<empty>}"
  step_total_expected=0
fi
if [ "${step_total_expected}" -gt 0 ] && [ "${step_count}" -ne "${step_total_expected}" ]; then
  add_warning "P0" "backend-export-consistency" "steps_detected expected ${step_total_expected}, got ${step_count}"
fi
if [ "${step_total_expected}" -gt 0 ] && [ "${ok_count}" -ne "${step_total_expected}" ]; then
  add_warning "P0" "backend-export-consistency" "ok_lines_detected expected ${step_total_expected}, got ${ok_count}"
fi
if [ "${passed_count}" -ne 1 ]; then
  add_warning "P0" "backend-export-consistency" "pass_banner_detected expected 1, got ${passed_count}"
fi
if [ "${task_export_ok}" -lt 1 ]; then
  add_warning "P1" "backend-export-consistency" "task_export_consistency_ok expected >=1, got ${task_export_ok}"
fi
if [ "${session_export_ok}" -lt 1 ]; then
  add_warning "P1" "backend-export-consistency" "session_export_consistency_ok expected >=1, got ${session_export_ok}"
fi
if [ "${shared_rag_ok}" -lt 1 ]; then
  add_warning "P1" "backend-export-consistency" "shared_rag_semantics_ok expected >=1, got ${shared_rag_ok}"
fi
if [ "${cross_user_ok}" -lt 1 ]; then
  add_warning "P1" "backend-export-consistency" "cross_user_isolation_ok expected >=1, got ${cross_user_ok}"
fi
if [ "${not_found_ok}" -lt 1 ]; then
  add_warning "P1" "backend-export-consistency" "not_found_semantics_ok expected >=1, got ${not_found_ok}"
fi

echo
echo "- Script log: ${log_file}"
echo "- Assertion counters:"
echo "  - step_total_expected: ${step_total_expected} (parsed from first [x/N] line)"
echo "  - steps_detected: ${step_count} (expected: ${step_total_expected})"
echo "  - ok_lines_detected: ${ok_count} (expected: ${step_total_expected})"
echo "  - pass_banner_detected: ${passed_count} (expected: 1)"
echo "  - task_export_consistency_ok: ${task_export_ok} (expected: >=1)"
echo "  - session_export_consistency_ok: ${session_export_ok} (expected: >=1)"
echo "  - shared_rag_semantics_ok: ${shared_rag_ok} (expected: >=1)"
echo "  - cross_user_isolation_ok: ${cross_user_ok} (expected: >=1)"
echo "  - not_found_semantics_ok: ${not_found_ok} (expected: >=1)"
echo "## threshold alerts"
if [ "${warning_count}" -gt 0 ]; then
  echo "- total_alerts: ${warning_count}"
  echo "- severity: P0=${p0_warning_count}, P1=${p1_warning_count}"
  printf '%b\n' "${warning_messages}"
else
  echo "- total_alerts: 0 (all counters within expected range)"
  echo "- severity: P0=0, P1=0"
fi
echo "## key lines"
grep -E "${KEY_LINES_REGEX}" "${log_file}" || true
