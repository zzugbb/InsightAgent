#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_run_release_gate.sh"
TMP_DIR=""

json_tool_python() {
  if [ -n "${CI_JSON_TOOL_PYTHON:-}" ]; then
    printf '%s\n' "${CI_JSON_TOOL_PYTHON}"
  elif [ -x "${ROOT_DIR}/backend/.venv/bin/python" ]; then
    printf '%s\n' "${ROOT_DIR}/backend/.venv/bin/python"
  else
    printf '%s\n' "python3"
  fi
}

assert_contains() {
  local expected="$1"
  local file="$2"
  if ! grep -Fq -- "${expected}" "${file}"; then
    echo "expected '${expected}' in ${file}" >&2
    cat "${file}" >&2 || true
    exit 1
  fi
}

assert_not_contains() {
  local unexpected="$1"
  local file="$2"
  if grep -Fq -- "${unexpected}" "${file}"; then
    echo "did not expect '${unexpected}' in ${file}" >&2
    cat "${file}" >&2 || true
    exit 1
  fi
}

expect_fail() {
  if "$@" >/dev/null 2>&1; then
    echo "expected fail but passed: $*" >&2
    exit 1
  fi
}

setup_git_repo() {
  local repo_dir="$1"
  mkdir -p "${repo_dir}"
  git init "${repo_dir}" >/dev/null
  git -C "${repo_dir}" config user.name "CI Test"
  git -C "${repo_dir}" config user.email "ci@example.com"
}

main() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR:-}"' EXIT

  bash "${SCRIPT}" --dry-run --phase all > "${TMP_DIR}/all.txt"
  assert_contains "phase=all" "${TMP_DIR}/all.txt"
  assert_contains "backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py" "${TMP_DIR}/all.txt"
  assert_contains "PYTHONPATH=. .venv/bin/python scripts/test_tool_runtime_module_boundaries.py" "${TMP_DIR}/all.txt"
  assert_contains "node --test --experimental-strip-types" "${TMP_DIR}/all.txt"
  assert_contains "app/components/workbench/task-queue-diagnostics-contract.type.test.ts" "${TMP_DIR}/all.txt"
  assert_contains "app/source-file-size.node.test.ts" "${TMP_DIR}/all.txt"
  assert_contains "npm run lint" "${TMP_DIR}/all.txt"
  assert_contains "npm run build" "${TMP_DIR}/all.txt"
  assert_contains "bash scripts/test_ci_e2e_tooling.sh all" "${TMP_DIR}/all.txt"
  assert_contains "backend/.venv/bin/python -m compileall -q backend/app backend/scripts" "${TMP_DIR}/all.txt"
  assert_contains "git diff --check" "${TMP_DIR}/all.txt"
  assert_contains "git diff -- data/insightagent.plan.back.md" "${TMP_DIR}/all.txt"
  assert_not_contains "ci_run_backend_e2e.sh" "${TMP_DIR}/all.txt"
  assert_not_contains "ci_run_frontend_e2e.sh" "${TMP_DIR}/all.txt"

  bash "${SCRIPT}" \
    --dry-run \
    --phase frontend \
    --summary-file "${TMP_DIR}/summary.md" \
    --json-summary-file "${TMP_DIR}/summary.json" \
    > "${TMP_DIR}/summary-stdout.txt"
  assert_contains "release_gate_summary=${TMP_DIR}/summary.md" "${TMP_DIR}/summary-stdout.txt"
  assert_contains "release_gate_json_summary=${TMP_DIR}/summary.json" "${TMP_DIR}/summary-stdout.txt"
  assert_contains "### release gate" "${TMP_DIR}/summary.md"
  assert_contains "- summary_schema_version: 1" "${TMP_DIR}/summary.md"
  assert_contains "- phase: frontend" "${TMP_DIR}/summary.md"
  assert_contains "- result: DRY-RUN" "${TMP_DIR}/summary.md"
  assert_contains "- total_steps: 3" "${TMP_DIR}/summary.md"
  assert_contains "- dry_run_steps: 3" "${TMP_DIR}/summary.md"
  assert_contains "- failed_steps: 0" "${TMP_DIR}/summary.md"
  assert_contains "- failed_step_labels: none" "${TMP_DIR}/summary.md"
  assert_contains "| frontend node tests | DRY-RUN |" "${TMP_DIR}/summary.md"
  assert_contains '"summary_schema_version": 1' "${TMP_DIR}/summary.json"
  assert_contains '"phase": "frontend"' "${TMP_DIR}/summary.json"
  assert_contains '"result": "DRY-RUN"' "${TMP_DIR}/summary.json"
  assert_contains '"step_summary": {"total": 3, "pass": 0, "fail": 0, "dry_run": 3}' "${TMP_DIR}/summary.json"
  assert_contains '"failed_step_labels": []' "${TMP_DIR}/summary.json"
  assert_contains '"label": "frontend build"' "${TMP_DIR}/summary.json"

  env RELEASE_GATE_PYTHON=/no/such/python bash "${SCRIPT}" \
    --dry-run \
    --phase frontend \
    --json-summary-file "${TMP_DIR}/invalid-python-summary.json" \
    > "${TMP_DIR}/invalid-python-summary-stdout.txt"
  "$(json_tool_python)" -m json.tool "${TMP_DIR}/invalid-python-summary.json" >/dev/null
  assert_contains '"phase": "frontend"' "${TMP_DIR}/invalid-python-summary.json"
  assert_contains '"label": "frontend build"' "${TMP_DIR}/invalid-python-summary.json"

  bash "${SCRIPT}" --dry-run --phase frontend > "${TMP_DIR}/frontend.txt"
  assert_contains "phase=frontend" "${TMP_DIR}/frontend.txt"
  assert_contains "node --test --experimental-strip-types" "${TMP_DIR}/frontend.txt"
  assert_contains "npm run build" "${TMP_DIR}/frontend.txt"
  assert_not_contains "test_tool_runtime_slice.py" "${TMP_DIR}/frontend.txt"

  setup_git_repo "${TMP_DIR}/repo"
  mkdir -p "${TMP_DIR}/repo/frontend" "${TMP_DIR}/repo/backend"
  printf 'base\n' > "${TMP_DIR}/repo/frontend/app.tsx"
  printf 'base\n' > "${TMP_DIR}/repo/backend/app.py"
  git -C "${TMP_DIR}/repo" add frontend/app.tsx backend/app.py
  git -C "${TMP_DIR}/repo" commit -m "base" >/dev/null
  base_sha="$(git -C "${TMP_DIR}/repo" rev-parse HEAD)"
  printf 'head\n' > "${TMP_DIR}/repo/frontend/app.tsx"
  git -C "${TMP_DIR}/repo" add frontend/app.tsx
  git -C "${TMP_DIR}/repo" commit -m "frontend" >/dev/null
  frontend_sha="$(git -C "${TMP_DIR}/repo" rev-parse HEAD)"

  bash "${SCRIPT}" \
    --dry-run \
    --phase auto \
    --repo-root "${TMP_DIR}/repo" \
    --event-name pull_request \
    --base-sha "${base_sha}" \
    --head-sha "${frontend_sha}" \
    --ref refs/pull/42/merge \
    --summary-file "${TMP_DIR}/auto-frontend.md" \
    > "${TMP_DIR}/auto-frontend.txt"
  assert_contains "phase=auto" "${TMP_DIR}/auto-frontend.txt"
  assert_contains "resolved_phases=frontend,tooling,hygiene" "${TMP_DIR}/auto-frontend.txt"
  assert_contains "resolve_source=git_diff" "${TMP_DIR}/auto-frontend.txt"
  assert_contains "frontend node tests" "${TMP_DIR}/auto-frontend.txt"
  assert_contains "ci tooling self-tests" "${TMP_DIR}/auto-frontend.txt"
  assert_contains "backup plan remains untouched" "${TMP_DIR}/auto-frontend.txt"
  assert_not_contains "backend full slice" "${TMP_DIR}/auto-frontend.txt"
  assert_contains "- resolved_phases: frontend,tooling,hygiene" "${TMP_DIR}/auto-frontend.md"

  printf 'head\n' > "${TMP_DIR}/repo/backend/app.py"
  git -C "${TMP_DIR}/repo" add backend/app.py
  git -C "${TMP_DIR}/repo" commit -m "backend" >/dev/null
  backend_sha="$(git -C "${TMP_DIR}/repo" rev-parse HEAD)"

  bash "${SCRIPT}" \
    --dry-run \
    --phase auto \
    --repo-root "${TMP_DIR}/repo" \
    --event-name pull_request \
    --base-sha "${frontend_sha}" \
    --head-sha "${backend_sha}" \
    --ref refs/pull/44/merge \
    > "${TMP_DIR}/auto-backend.txt"
  assert_contains "resolved_phases=backend,tooling,hygiene" "${TMP_DIR}/auto-backend.txt"
  assert_contains "backend full slice" "${TMP_DIR}/auto-backend.txt"
  assert_not_contains "frontend node tests" "${TMP_DIR}/auto-backend.txt"

  printf 'workflow\n' > "${TMP_DIR}/repo/.github-workflow-placeholder"
  mkdir -p "${TMP_DIR}/repo/.github/workflows"
  printf 'name: release\n' > "${TMP_DIR}/repo/.github/workflows/release-gate.yml"
  git -C "${TMP_DIR}/repo" add .github/workflows/release-gate.yml
  git -C "${TMP_DIR}/repo" commit -m "workflow" >/dev/null
  workflow_sha="$(git -C "${TMP_DIR}/repo" rev-parse HEAD)"

  bash "${SCRIPT}" \
    --dry-run \
    --phase auto \
    --repo-root "${TMP_DIR}/repo" \
    --event-name pull_request \
    --base-sha "${backend_sha}" \
    --head-sha "${workflow_sha}" \
    --ref refs/pull/43/merge \
    > "${TMP_DIR}/auto-workflow.txt"
  assert_contains "resolved_phases=backend,frontend,tooling,hygiene" "${TMP_DIR}/auto-workflow.txt"
  assert_contains "backend full slice" "${TMP_DIR}/auto-workflow.txt"
  assert_contains "frontend node tests" "${TMP_DIR}/auto-workflow.txt"

  expect_fail bash "${SCRIPT}" --phase unknown --dry-run

  echo "ci_release_gate tests passed"
}

main "$@"
