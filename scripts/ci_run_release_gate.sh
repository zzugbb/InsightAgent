#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
phase="all"
dry_run="0"
summary_file=""
json_summary_file=""
overall_result="PASS"
repo_root="${ROOT_DIR}"
event_name="${GITHUB_EVENT_NAME:-}"
base_sha=""
head_sha="${GITHUB_SHA:-HEAD}"
ref_name="${GITHUB_REF:-}"
changed_files_path=""
changed_files_resolve_source=""
changed_files_count=""
resolved_phase_csv=""

FRONTEND_NODE_TESTS=(
  "lib/stores/chat-stream-store-utils.node.test.ts"
  "app/components/workbench/runtime-debug-modal-utils.node.test.ts"
  "app/components/workbench/audit-logs-modal-utils.node.test.ts"
  "app/components/workbench/model-settings-modal-utils.node.test.ts"
  "app/components/workbench/task-queue-diagnostics-contract.type.test.ts"
  "app/components/workbench/utils.node.test.ts"
  "app/components/workbench/knowledge-base-governance-modal-utils.node.test.ts"
  "app/source-file-size.node.test.ts"
  "app/tasks/task-detail-page-utils.node.test.ts"
)

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_run_release_gate.sh [--phase <auto|all|backend|frontend|tooling|hygiene>] [--dry-run]
    [--summary-file <path>] [--json-summary-file <path>]
    [--repo-root <path>] [--event-name <name>] [--base-sha <sha>]
    [--head-sha <sha>] [--ref <ref>]

Phases:
  backend   Run backend full slice and module boundary checks.
  frontend  Run frontend node tests, lint, and production build.
  tooling   Run CI/e2e tooling self-tests without starting services.
  hygiene   Run compileall, diff whitespace, and backup-plan diff checks.
  all       Run every phase above.
  auto      Use PR changed files to choose backend/frontend phases, then always
            run tooling and hygiene. CI/workflow/script changes run all phases.

This gate intentionally avoids local service startup and e2e execution. Use the
runbook e2e commands for backend/frontend service-backed validation.
USAGE
}

STEP_LABELS=()
STEP_WORKDIRS=()
STEP_COMMANDS=()
STEP_RESULTS=()
STEP_EXIT_CODES=()

shell_quote() {
  printf '%q' "$1"
}

format_command() {
  local rendered=""
  local arg
  for arg in "$@"; do
    if [ -n "${rendered}" ]; then
      rendered+=" "
    fi
    rendered+="$(shell_quote "${arg}")"
  done
  printf '%s\n' "${rendered}"
}

json_string() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  value="${value//$'\t'/\\t}"
  value="${value//$'\b'/\\b}"
  value="${value//$'\f'/\\f}"
  printf '"%s"\n' "${value}"
}

record_step() {
  STEP_LABELS+=("$1")
  STEP_WORKDIRS+=("$2")
  STEP_COMMANDS+=("$3")
  STEP_RESULTS+=("$4")
  STEP_EXIT_CODES+=("$5")
}

write_summaries() {
  local result="$1"
  local i
  local total_steps="${#STEP_LABELS[@]}"
  local pass_steps=0
  local fail_steps=0
  local dry_run_steps=0
  local failed_step_labels="none"
  local failed_json="["
  local failed_count=0

  for i in "${!STEP_LABELS[@]}"; do
    case "${STEP_RESULTS[$i]}" in
      PASS) pass_steps=$((pass_steps + 1)) ;;
      FAIL)
        fail_steps=$((fail_steps + 1))
        if [ "${failed_step_labels}" = "none" ]; then
          failed_step_labels="${STEP_LABELS[$i]}"
        else
          failed_step_labels+=",${STEP_LABELS[$i]}"
        fi
        if [ "${failed_count}" -gt 0 ]; then
          failed_json+=", "
        fi
        failed_json+="$(json_string "${STEP_LABELS[$i]}")"
        failed_count=$((failed_count + 1))
        ;;
      DRY-RUN) dry_run_steps=$((dry_run_steps + 1)) ;;
    esac
  done
  failed_json+="]"

  if [ -n "${summary_file}" ]; then
    mkdir -p "$(dirname "${summary_file}")"
    {
      echo "### release gate"
      echo "- summary_schema_version: 1"
      echo "- summary_kind: release_gate"
      echo "- service_required: no"
      echo "- phase: ${phase}"
      if [ -n "${resolved_phase_csv}" ]; then
        echo "- resolved_phases: ${resolved_phase_csv}"
      fi
      if [ -n "${changed_files_resolve_source}" ]; then
        echo "- changed_files_source: ${changed_files_resolve_source}"
        echo "- changed_files_count: ${changed_files_count}"
      fi
      echo "- result: ${result}"
      echo "- dry_run: ${dry_run}"
      echo "- total_steps: ${total_steps}"
      echo "- passed_steps: ${pass_steps}"
      echo "- failed_steps: ${fail_steps}"
      echo "- dry_run_steps: ${dry_run_steps}"
      echo "- failed_step_labels: ${failed_step_labels}"
      echo
      echo "| step | result | exit_code | workdir | command |"
      echo "| --- | --- | --- | --- | --- |"
      for i in "${!STEP_LABELS[@]}"; do
        echo "| ${STEP_LABELS[$i]} | ${STEP_RESULTS[$i]} | ${STEP_EXIT_CODES[$i]} | ${STEP_WORKDIRS[$i]} | \`${STEP_COMMANDS[$i]}\` |"
      done
    } > "${summary_file}"
    echo "release_gate_summary=${summary_file}"
  fi
  if [ -n "${json_summary_file}" ]; then
    mkdir -p "$(dirname "${json_summary_file}")"
    {
      printf '{\n'
      printf '  "summary_schema_version": 1,\n'
      printf '  "summary_kind": "release_gate",\n'
      printf '  "service_required": false,\n'
      printf '  "phase": %s,\n' "$(json_string "${phase}")"
      printf '  "resolved_phases": %s,\n' "$(json_string "${resolved_phase_csv}")"
      printf '  "changed_files_source": %s,\n' "$(json_string "${changed_files_resolve_source}")"
      printf '  "changed_files_count": %s,\n' "$(json_string "${changed_files_count}")"
      printf '  "result": %s,\n' "$(json_string "${result}")"
      printf '  "dry_run": %s,\n' "$(json_string "${dry_run}")"
      printf '  "step_summary": {"total": %s, "pass": %s, "fail": %s, "dry_run": %s},\n' \
        "${total_steps}" \
        "${pass_steps}" \
        "${fail_steps}" \
        "${dry_run_steps}"
      printf '  "failed_step_labels": %s,\n' "${failed_json}"
      printf '  "steps": [\n'
      for i in "${!STEP_LABELS[@]}"; do
        if [ "${i}" -gt 0 ]; then
          printf ',\n'
        fi
        printf '    {"label": %s, "result": %s, "exit_code": %s, "workdir": %s, "command": %s}' \
          "$(json_string "${STEP_LABELS[$i]}")" \
          "$(json_string "${STEP_RESULTS[$i]}")" \
          "${STEP_EXIT_CODES[$i]}" \
          "$(json_string "${STEP_WORKDIRS[$i]}")" \
          "$(json_string "${STEP_COMMANDS[$i]}")"
      done
      printf '\n  ]\n'
      printf '}\n'
    } > "${json_summary_file}"
    echo "release_gate_json_summary=${json_summary_file}"
  fi
}

run_step() {
  local label="$1"
  local workdir="$2"
  shift 2
  local display
  display="$(format_command "$@")"
  echo "[release-gate] ${label}"
  echo "[release-gate] workdir=${workdir}"
  if [ "${dry_run}" = "1" ]; then
    echo "[release-gate] would run: ${display}"
    record_step "${label}" "${workdir}" "${display}" "DRY-RUN" "0"
    return 0
  fi
  set +e
  (cd "${workdir}" && "$@")
  local exit_code=$?
  set -e
  if [ "${exit_code}" -eq 0 ]; then
    record_step "${label}" "${workdir}" "${display}" "PASS" "0"
    return 0
  fi
  overall_result="FAIL"
  record_step "${label}" "${workdir}" "${display}" "FAIL" "${exit_code}"
  write_summaries "${overall_result}"
  exit "${exit_code}"
}

run_backend() {
  run_step \
    "backend full slice" \
    "${ROOT_DIR}" \
    backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py
  run_step \
    "backend module boundaries" \
    "${ROOT_DIR}/backend" \
    env PYTHONPATH=. .venv/bin/python scripts/test_tool_runtime_module_boundaries.py
}

run_frontend() {
  run_step \
    "frontend node tests" \
    "${ROOT_DIR}/frontend" \
    node --test --experimental-strip-types "${FRONTEND_NODE_TESTS[@]}"
  run_step \
    "frontend lint" \
    "${ROOT_DIR}/frontend" \
    npm run lint
  run_step \
    "frontend build" \
    "${ROOT_DIR}/frontend" \
    npm run build
}

run_tooling() {
  run_step \
    "ci tooling self-tests" \
    "${ROOT_DIR}" \
    bash scripts/test_ci_e2e_tooling.sh all
}

run_hygiene() {
  run_step \
    "backend compileall" \
    "${ROOT_DIR}" \
    backend/.venv/bin/python -m compileall -q backend/app backend/scripts
  run_step \
    "diff whitespace" \
    "${ROOT_DIR}" \
    git diff --check
  run_step \
    "backup plan remains untouched" \
    "${ROOT_DIR}" \
    git diff -- data/insightagent.plan.back.md
}

join_resolved_phases() {
  local joined=""
  local item
  for item in "${RESOLVED_PHASES[@]}"; do
    if [ -n "${joined}" ]; then
      joined+=","
    fi
    joined+="${item}"
  done
  printf '%s\n' "${joined}"
}

resolve_auto_phases() {
  local collect_output
  changed_files_path="$(mktemp)"
  collect_output="$(
    bash "${ROOT_DIR}/scripts/ci_collect_changed_files.sh" \
      --repo-root "${repo_root}" \
      --event-name "${event_name}" \
      --base-sha "${base_sha}" \
      --head-sha "${head_sha}" \
      --output-file "${changed_files_path}" \
      --fallback-path backend/ \
      --fallback-path frontend/ \
      --fallback-path scripts/ \
      --fallback-path .github/workflows/release-gate.yml \
      --fallback-path .github/workflows/backend-e2e.yml \
      --fallback-path .github/workflows/frontend-e2e.yml \
      --fallback-path docs/development-runbook.md \
      --fallback-path compose.full.yml
  )"
  printf '%s\n' "${collect_output}"
  changed_files_resolve_source="$(printf '%s\n' "${collect_output}" | awk -F= '$1=="resolve_source"{print $2}')"
  changed_files_count="$(printf '%s\n' "${collect_output}" | awk -F= '$1=="changed_count"{print $2}')"
  echo "changed_files_path=${changed_files_path}"

  RESOLVED_PHASES=()
  if [ "${changed_files_resolve_source}" != "git_diff" ]; then
    RESOLVED_PHASES=(backend frontend tooling hygiene)
    resolved_phase_csv="$(join_resolved_phases)"
    echo "resolved_phases=${resolved_phase_csv}"
    return 0
  fi

  if grep -Eq '^(scripts/|\.github/workflows/|docs/development-runbook\.md$|compose\.full\.yml$)' "${changed_files_path}"; then
    RESOLVED_PHASES=(backend frontend tooling hygiene)
    resolved_phase_csv="$(join_resolved_phases)"
    echo "resolved_phases=${resolved_phase_csv}"
    return 0
  fi

  if grep -Eq '^backend/' "${changed_files_path}"; then
    RESOLVED_PHASES+=(backend)
  fi
  if grep -Eq '^frontend/' "${changed_files_path}"; then
    RESOLVED_PHASES+=(frontend)
  fi
  RESOLVED_PHASES+=(tooling hygiene)
  resolved_phase_csv="$(join_resolved_phases)"
  echo "resolved_phases=${resolved_phase_csv}"
}

run_phase_name() {
  case "$1" in
    backend) run_backend ;;
    frontend) run_frontend ;;
    tooling) run_tooling ;;
    hygiene) run_hygiene ;;
    *)
      echo "internal error: unknown resolved phase $1" >&2
      exit 2
      ;;
  esac
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --phase) phase="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    --json-summary-file) json_summary_file="${2:-}"; shift 2 ;;
    --repo-root) repo_root="${2:-}"; shift 2 ;;
    --event-name) event_name="${2:-}"; shift 2 ;;
    --base-sha) base_sha="${2:-}"; shift 2 ;;
    --head-sha) head_sha="${2:-}"; shift 2 ;;
    --ref) ref_name="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "${phase}" in
  auto|all|backend|frontend|tooling|hygiene) ;;
  *)
    echo "unknown phase: ${phase} (expected: auto|all|backend|frontend|tooling|hygiene)" >&2
    exit 2
    ;;
esac

echo "[release-gate] phase=${phase}"
echo "[release-gate] dry_run=${dry_run}"

case "${phase}" in
  auto)
    resolve_auto_phases
    for resolved_phase in "${RESOLVED_PHASES[@]}"; do
      run_phase_name "${resolved_phase}"
    done
    ;;
  all)
    resolved_phase_csv="backend,frontend,tooling,hygiene"
    run_backend
    run_frontend
    run_tooling
    run_hygiene
    ;;
  backend)
    resolved_phase_csv="backend"
    run_backend
    ;;
  frontend)
    resolved_phase_csv="frontend"
    run_frontend
    ;;
  tooling)
    resolved_phase_csv="tooling"
    run_tooling
    ;;
  hygiene)
    resolved_phase_csv="hygiene"
    run_hygiene
    ;;
esac

if [ "${dry_run}" = "1" ]; then
  overall_result="DRY-RUN"
fi

echo "[release-gate] completed phase=${phase}"
write_summaries "${overall_result}"
