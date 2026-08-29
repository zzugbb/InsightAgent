#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
phase="all"
dry_run="0"

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
    return 0
  fi
  (cd "${workdir}" && "$@")
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

echo "[release-gate] completed phase=${phase}"
