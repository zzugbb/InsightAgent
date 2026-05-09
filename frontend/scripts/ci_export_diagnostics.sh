#!/usr/bin/env bash

set -euo pipefail

results_dir="${1:-frontend/test-results}"
json_out="${2:-}"

echo "# frontend-e2e export diagnostics"
echo
echo "- generated_at_utc: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo

warning_count=0
p0_warning_count=0
p1_warning_count=0
warning_messages=""

main_context_count=0
main_ui_hint_count=0
main_header_hint_count=0
main_api_hint_count=0

shared_context_count=0
shared_semantic_ok_count=0
shared_expected_label="0 (no shared-kb error-context files)"

edge_context_count=0
edge_ui_hint_count=0
edge_header_hint_count=0
edge_api_hint_count=0
edge_404_semantic_hints=0

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

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

write_json_summary() {
  local out_path="$1"
  mkdir -p "$(dirname "${out_path}")"
  cat > "${out_path}" <<JSON
{
  "results_dir": "$(json_escape "${results_dir}")",
  "main": {
    "context_files_detected": ${main_context_count},
    "ui_download_layer_hints": ${main_ui_hint_count},
    "response_header_layer_hints": ${main_header_hint_count},
    "export_api_path_hints": ${main_api_hint_count}
  },
  "shared": {
    "context_files_detected": ${shared_context_count},
    "shared_permission_semantic_ok": ${shared_semantic_ok_count},
    "expected_label": "$(json_escape "${shared_expected_label}")"
  },
  "edge": {
    "context_files_detected": ${edge_context_count},
    "ui_download_layer_hints": ${edge_ui_hint_count},
    "response_header_layer_hints": ${edge_header_hint_count},
    "export_api_path_hints": ${edge_api_hint_count},
    "export_404_semantic_hints": ${edge_404_semantic_hints}
  },
  "warnings": {
    "total": ${warning_count},
    "p0": ${p0_warning_count},
    "p1": ${p1_warning_count}
  }
}
JSON
}

print_matched_files() {
  local label="$1"
  shift
  local files=("$@")
  echo "### matched error-context files"
  if [ ${#files[@]} -eq 0 ]; then
    echo "No ${label} error-context files found."
    return
  fi
  for file in "${files[@]}"; do
    echo "- ${file}"
  done
}

print_key_lines() {
  local regex="$1"
  shift
  local files=("$@")
  echo "### key lines"
  for file in "${files[@]}"; do
    grep -Ein "${regex}" "$file" || true
  done | head -n 120
}

sum_regex_hits() {
  local regex="$1"
  shift
  local files=("$@")
  local total=0
  local hits=0
  for file in "${files[@]}"; do
    hits=$(grep -Eci "${regex}" "$file" || true)
    total=$((total + hits))
  done
  echo "${total}"
}

UI_HINT_REGEX='waitForEvent\("download"\)|suggestedFilename|task-detail-export|sidebar-session-export|download event'
HEADER_HINT_REGEX='content-type|content-disposition|application/json|text/markdown|attachment;'
API_EXPORT_REGEX='/api/(tasks|sessions)/[^ ]*/export/(json|markdown)'
EDGE_SEMANTIC_REGEX='404|not found|task not found|session not found|cross-user|ownership|isolat'
SHARED_SEMANTIC_REGEX='shared-|kb-governance-action-clear|kb-governance-action-delete|non-admin|toBeDisabled'

MAIN_CONTEXT_PATH_REGEX='workbench-main-path'
EDGE_CONTEXT_PATH_REGEX='workbench-edge-cases'
SHARED_CONTEXT_PATH_REGEX='workbench-main-path.*(shared-kb-actions-disabled|shared.*kb.*disabled)'

MAIN_KEY_LINES_REGEX="download|suggestedfilename|content-type|content-disposition|application/json|text/markdown|${API_EXPORT_REGEX}"
EDGE_KEY_LINES_REGEX="${MAIN_KEY_LINES_REGEX}|${EDGE_SEMANTIC_REGEX}"
SHARED_KEY_LINES_REGEX='shared-|kb-governance-action-(clear|delete)|toBeDisabled|role|/api/auth/me|/api/rag/knowledge-bases'

if [ ! -d "${results_dir}" ]; then
  echo "No ${results_dir} directory found."
  if [ -n "${json_out}" ]; then
    write_json_summary "${json_out}"
  fi
  exit 0
fi

all_error_contexts=()
while IFS= read -r line; do
  all_error_contexts+=("$line")
done < <(find "${results_dir}" -name "error-context.md" | sort || true)

main_contexts=()
if [ ${#all_error_contexts[@]} -gt 0 ]; then
  while IFS= read -r line; do
    main_contexts+=("$line")
  done < <(printf '%s\n' "${all_error_contexts[@]}" | grep -E "${MAIN_CONTEXT_PATH_REGEX}" | grep -Ev "${SHARED_CONTEXT_PATH_REGEX}" || true)
fi
echo "## workbench-main-path"
if [ ${#main_contexts[@]} -eq 0 ]; then
  echo "No workbench-main-path error-context files found."
else
  print_matched_files "workbench-main-path" "${main_contexts[@]}"
  echo

  main_context_count=${#main_contexts[@]}
  main_ui_hint_count=$(sum_regex_hits "${UI_HINT_REGEX}" "${main_contexts[@]}")
  main_header_hint_count=$(sum_regex_hits "${HEADER_HINT_REGEX}" "${main_contexts[@]}")
  main_api_hint_count=$(sum_regex_hits "${API_EXPORT_REGEX}" "${main_contexts[@]}")

  echo "### assertion hint counters"
  echo "- context_files_detected: ${main_context_count}"
  echo "- ui_download_layer_hints: ${main_ui_hint_count}"
  echo "- response_header_layer_hints: ${main_header_hint_count}"
  echo "- export_api_path_hints: ${main_api_hint_count}"

  if [ "${main_context_count}" -gt 0 ] && [ "${main_api_hint_count}" -lt 1 ]; then
    add_warning "P0" "workbench-main-path" "export_api_path_hints expected >=1 when error-context exists, got ${main_api_hint_count}"
  fi
  if [ "${main_context_count}" -gt 0 ] && [ "${main_ui_hint_count}" -lt 1 ] && [ "${main_header_hint_count}" -lt 1 ]; then
    add_warning "P0" "workbench-main-path" "both ui_download_layer_hints and response_header_layer_hints are 0 with existing error-context"
  fi
  if [ "${main_ui_hint_count}" -lt 1 ]; then
    add_warning "P1" "workbench-main-path" "ui_download_layer_hints expected >=1, got ${main_ui_hint_count}"
  fi
  if [ "${main_header_hint_count}" -lt 1 ]; then
    add_warning "P1" "workbench-main-path" "response_header_layer_hints expected >=1, got ${main_header_hint_count}"
  fi
  if [ "${main_api_hint_count}" -lt 1 ]; then
    add_warning "P1" "workbench-main-path" "export_api_path_hints expected >=1, got ${main_api_hint_count}"
  fi
  echo

  print_key_lines "${MAIN_KEY_LINES_REGEX}" "${main_contexts[@]}"
fi
echo

shared_contexts=()
if [ ${#all_error_contexts[@]} -gt 0 ]; then
  while IFS= read -r line; do
    shared_contexts+=("$line")
  done < <(printf '%s\n' "${all_error_contexts[@]}" | grep -E "${SHARED_CONTEXT_PATH_REGEX}" || true)
fi
echo "## workbench-main-path-shared-kb"
if [ ${#shared_contexts[@]} -eq 0 ]; then
  echo "No workbench-main-path shared-kb error-context files found."
  echo
  echo "### assertion hint counters"
  echo "- context_files_detected: ${shared_context_count}"
  echo "- shared_permission_semantic_ok: ${shared_semantic_ok_count} (expected: ${shared_expected_label})"
else
  print_matched_files "workbench-main-path-shared-kb" "${shared_contexts[@]}"
  echo

  shared_context_count=${#shared_contexts[@]}
  shared_expected_label=">=1 (when shared-kb error-context files exist)"
  shared_semantic_ok_count=$(sum_regex_hits "${SHARED_SEMANTIC_REGEX}" "${shared_contexts[@]}")

  echo "### assertion hint counters"
  echo "- context_files_detected: ${shared_context_count}"
  echo "- shared_permission_semantic_ok: ${shared_semantic_ok_count} (expected: ${shared_expected_label})"

  if [ "${shared_context_count}" -gt 0 ] && [ "${shared_semantic_ok_count}" -lt 1 ]; then
    add_warning "P0" "workbench-main-path-shared-kb" "shared_permission_semantic_ok expected >=1 when error-context exists, got ${shared_semantic_ok_count}"
  fi
  if [ "${shared_semantic_ok_count}" -lt 1 ]; then
    add_warning "P1" "workbench-main-path-shared-kb" "shared_permission_semantic_ok expected >=1, got ${shared_semantic_ok_count}"
  fi
  echo

  print_key_lines "${SHARED_KEY_LINES_REGEX}" "${shared_contexts[@]}"
fi
echo

edge_contexts=()
if [ ${#all_error_contexts[@]} -gt 0 ]; then
  while IFS= read -r line; do
    edge_contexts+=("$line")
  done < <(printf '%s\n' "${all_error_contexts[@]}" | grep -E "${EDGE_CONTEXT_PATH_REGEX}" || true)
fi
echo "## workbench-edge-cases"
if [ ${#edge_contexts[@]} -eq 0 ]; then
  echo "No workbench-edge-cases error-context files found."
else
  print_matched_files "workbench-edge-cases" "${edge_contexts[@]}"
  echo

  edge_context_count=${#edge_contexts[@]}
  edge_ui_hint_count=$(sum_regex_hits "${UI_HINT_REGEX}" "${edge_contexts[@]}")
  edge_header_hint_count=$(sum_regex_hits "${HEADER_HINT_REGEX}" "${edge_contexts[@]}")
  edge_api_hint_count=$(sum_regex_hits "${API_EXPORT_REGEX}" "${edge_contexts[@]}")
  edge_404_semantic_hints=$(sum_regex_hits "${EDGE_SEMANTIC_REGEX}" "${edge_contexts[@]}")

  echo "### assertion hint counters"
  echo "- context_files_detected: ${edge_context_count}"
  echo "- ui_download_layer_hints: ${edge_ui_hint_count}"
  echo "- response_header_layer_hints: ${edge_header_hint_count}"
  echo "- export_api_path_hints: ${edge_api_hint_count}"
  echo "- export_404_semantic_hints: ${edge_404_semantic_hints}"

  if [ "${edge_context_count}" -gt 0 ] && [ "${edge_api_hint_count}" -lt 1 ]; then
    add_warning "P0" "workbench-edge-cases" "export_api_path_hints expected >=1 when error-context exists, got ${edge_api_hint_count}"
  fi
  if [ "${edge_context_count}" -gt 0 ] && [ "${edge_404_semantic_hints}" -lt 1 ]; then
    add_warning "P0" "workbench-edge-cases" "export_404_semantic_hints expected >=1 when error-context exists, got ${edge_404_semantic_hints}"
  fi
  if [ "${edge_context_count}" -gt 0 ] && [ "${edge_ui_hint_count}" -lt 1 ] && [ "${edge_header_hint_count}" -lt 1 ]; then
    add_warning "P0" "workbench-edge-cases" "both ui_download_layer_hints and response_header_layer_hints are 0 with existing error-context"
  fi
  if [ "${edge_ui_hint_count}" -lt 1 ]; then
    add_warning "P1" "workbench-edge-cases" "ui_download_layer_hints expected >=1, got ${edge_ui_hint_count}"
  fi
  if [ "${edge_header_hint_count}" -lt 1 ]; then
    add_warning "P1" "workbench-edge-cases" "response_header_layer_hints expected >=1, got ${edge_header_hint_count}"
  fi
  if [ "${edge_api_hint_count}" -lt 1 ]; then
    add_warning "P1" "workbench-edge-cases" "export_api_path_hints expected >=1, got ${edge_api_hint_count}"
  fi
  if [ "${edge_404_semantic_hints}" -lt 1 ]; then
    add_warning "P1" "workbench-edge-cases" "export_404_semantic_hints expected >=1, got ${edge_404_semantic_hints}"
  fi
  echo

  print_key_lines "${EDGE_KEY_LINES_REGEX}" "${edge_contexts[@]}"
fi

echo
if [ "${warning_count}" -gt 0 ]; then
  echo "## threshold alerts"
  echo "- total_alerts: ${warning_count}"
  echo "- severity: P0=${p0_warning_count}, P1=${p1_warning_count}"
  echo "- shared_scope: workbench-main-path-shared-kb contexts=${shared_context_count}, shared_permission_semantic_ok=${shared_semantic_ok_count} (expected: ${shared_expected_label})"
  printf '%b\n' "${warning_messages}"
else
  echo "## threshold alerts"
  echo "- total_alerts: 0 (all counters within expected range)"
  echo "- severity: P0=0, P1=0"
  echo "- shared_scope: workbench-main-path-shared-kb contexts=${shared_context_count}, shared_permission_semantic_ok=${shared_semantic_ok_count} (expected: ${shared_expected_label})"
fi

if [ -n "${json_out}" ]; then
  write_json_summary "${json_out}"
fi
