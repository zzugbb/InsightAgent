#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_GATE_PYTHON="${RELEASE_GATE_PYTHON:-${ROOT_DIR}/backend/.venv/bin/python}"
phase="all"
dry_run="0"
summary_file=""
json_summary_file=""
overall_result="PASS"

FRONTEND_NODE_TESTS=(
  "lib/stores/chat-stream-store-utils.node.test.ts"
  "app/components/workbench/runtime-debug-modal-utils.node.test.ts"
  "app/components/workbench/audit-logs-modal-utils.node.test.ts"
  "app/components/workbench/model-settings-modal-utils.node.test.ts"
  "app/components/workbench/utils.node.test.ts"
  "app/components/workbench/knowledge-base-governance-modal-utils.node.test.ts"
  "app/source-file-size.node.test.ts"
  "app/tasks/task-detail-page-utils.node.test.ts"
)

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_run_release_gate.sh [--phase <all|backend|frontend|tooling|hygiene>] [--dry-run]
    [--summary-file <path>] [--json-summary-file <path>]

Phases:
  backend   Run backend full slice and module boundary checks.
  frontend  Run frontend node tests, lint, and production build.
  tooling   Run CI/e2e tooling self-tests without starting services.
  hygiene   Run compileall, diff whitespace, and backup-plan diff checks.
  all       Run every phase above.

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
  "${RELEASE_GATE_PYTHON}" -c 'import json, sys; print(json.dumps(sys.argv[1]))' "$1"
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
  if [ -n "${summary_file}" ]; then
    mkdir -p "$(dirname "${summary_file}")"
    {
      echo "### release gate"
      echo "- phase: ${phase}"
      echo "- result: ${result}"
      echo "- dry_run: ${dry_run}"
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
      printf '  "phase": %s,\n' "$(json_string "${phase}")"
      printf '  "result": %s,\n' "$(json_string "${result}")"
      printf '  "dry_run": %s,\n' "$(json_string "${dry_run}")"
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

while [ "$#" -gt 0 ]; do
  case "$1" in
    --phase) phase="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
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

case "${phase}" in
  all|backend|frontend|tooling|hygiene) ;;
  *)
    echo "unknown phase: ${phase} (expected: all|backend|frontend|tooling|hygiene)" >&2
    exit 2
    ;;
esac

echo "[release-gate] phase=${phase}"
echo "[release-gate] dry_run=${dry_run}"

case "${phase}" in
  all)
    run_backend
    run_frontend
    run_tooling
    run_hygiene
    ;;
  backend)
    run_backend
    ;;
  frontend)
    run_frontend
    ;;
  tooling)
    run_tooling
    ;;
  hygiene)
    run_hygiene
    ;;
esac

if [ "${dry_run}" = "1" ]; then
  overall_result="DRY-RUN"
fi

echo "[release-gate] completed phase=${phase}"
write_summaries "${overall_result}"
