#!/usr/bin/env bash

set -euo pipefail

format="markdown"
output_file=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_release_readiness_matrix.sh [--format <markdown|json>] [--output <path>]

The matrix is a static release-readiness checklist. It documents which gates are
required before release and whether each gate needs service-backed execution.
It does not start backend/frontend services or run e2e tests.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --format) format="${2:-}"; shift 2 ;;
    --output) output_file="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "${format}" in
  markdown|json) ;;
  *)
    echo "unknown format: ${format} (expected: markdown|json)" >&2
    exit 2
    ;;
esac

render_markdown() {
  cat <<'MARKDOWN'
### release readiness matrix

| gate_id | required_for_release | service_required | command | notes |
| --- | --- | --- | --- | --- |
| release-gate | yes | no | `bash scripts/ci_run_release_gate.sh --phase auto` | Static backend/frontend/tooling/hygiene gate. Does not replace service-backed e2e. |
| backend-e2e-main | yes | yes | `bash scripts/ci_run_backend_e2e.sh --phase main --base-url http://127.0.0.1:8000 --log-dir /tmp` | Validates backend baseline, main path, export consistency, and cancel path against a running backend. |
| backend-e2e-timeout | yes | yes | `bash scripts/ci_run_backend_e2e.sh --phase timeout --base-url http://127.0.0.1:8010 --log-dir /tmp` | Validates long-running timeout behavior on an isolated backend port. |
| backend-e2e-queue | yes | yes | `bash scripts/ci_run_backend_e2e.sh --phase queue --base-url http://127.0.0.1:8011 --log-dir /tmp` | Validates low-concurrency queue ordering against an isolated backend port. |
| frontend-e2e-smoke | yes | yes | `bash scripts/ci_run_frontend_e2e.sh --phase smoke --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001` | Fast Chromium smoke matrix against running backend and frontend services. |
| frontend-e2e-full | yes | yes | `bash scripts/ci_run_frontend_e2e.sh --phase full --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001` | Full Playwright suite for release candidates and UI contract changes. |
| frontend-e2e-queue | yes | yes | `bash scripts/ci_run_frontend_e2e.sh --phase queue --api-base-url http://127.0.0.1:8011 --frontend-base-url http://127.0.0.1:3001` | Validates low-concurrency queue recovery through the browser UI. |
| artifact-stage-guard | yes | no | `bash scripts/ci_run_artifact_stage_guard.sh --scope <backend|frontend> --stage-dir <dir> --artifact-name <artifact>` | Runs after e2e finalization to ensure diagnostics artifacts are staged before upload. |
| release-visibility-summary | yes | no | `bash scripts/ci_run_release_gate.sh --phase all --summary-file <path> --json-summary-file <path>` | Captures resolved phases and step results for release approval and post-release comparison. |
| rollback-decision-log | yes | no | `cat $GITHUB_STEP_SUMMARY` | Confirms the release summary keeps enough gate, e2e, and artifact guard context to decide rollback. |
| artifact-retention-policy | yes | no | `grep -R "retention-days: 14" .github/workflows` | Ensures uploaded release, backend e2e, and frontend e2e artifacts have an explicit two-week retention window. |
MARKDOWN
}

render_json() {
  cat <<'JSON'
{
  "schema_version": 1,
  "description": "Static release-readiness matrix. Service-backed gates require separately started backend/frontend services.",
  "gates": [
    {
      "gate_id": "release-gate",
      "required_for_release": true,
      "service_required": false,
      "command": "bash scripts/ci_run_release_gate.sh --phase auto",
      "notes": "Static backend/frontend/tooling/hygiene gate. Does not replace service-backed e2e."
    },
    {
      "gate_id": "backend-e2e-main",
      "required_for_release": true,
      "service_required": true,
      "command": "bash scripts/ci_run_backend_e2e.sh --phase main --base-url http://127.0.0.1:8000 --log-dir /tmp",
      "notes": "Validates backend baseline, main path, export consistency, and cancel path against a running backend."
    },
    {
      "gate_id": "backend-e2e-timeout",
      "required_for_release": true,
      "service_required": true,
      "command": "bash scripts/ci_run_backend_e2e.sh --phase timeout --base-url http://127.0.0.1:8010 --log-dir /tmp",
      "notes": "Validates long-running timeout behavior on an isolated backend port."
    },
    {
      "gate_id": "backend-e2e-queue",
      "required_for_release": true,
      "service_required": true,
      "command": "bash scripts/ci_run_backend_e2e.sh --phase queue --base-url http://127.0.0.1:8011 --log-dir /tmp",
      "notes": "Validates low-concurrency queue ordering against an isolated backend port."
    },
    {
      "gate_id": "frontend-e2e-smoke",
      "required_for_release": true,
      "service_required": true,
      "command": "bash scripts/ci_run_frontend_e2e.sh --phase smoke --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001",
      "notes": "Fast Chromium smoke matrix against running backend and frontend services."
    },
    {
      "gate_id": "frontend-e2e-full",
      "required_for_release": true,
      "service_required": true,
      "command": "bash scripts/ci_run_frontend_e2e.sh --phase full --api-base-url http://127.0.0.1:8000 --frontend-base-url http://127.0.0.1:3001",
      "notes": "Full Playwright suite for release candidates and UI contract changes."
    },
    {
      "gate_id": "frontend-e2e-queue",
      "required_for_release": true,
      "service_required": true,
      "command": "bash scripts/ci_run_frontend_e2e.sh --phase queue --api-base-url http://127.0.0.1:8011 --frontend-base-url http://127.0.0.1:3001",
      "notes": "Validates low-concurrency queue recovery through the browser UI."
    },
    {
      "gate_id": "artifact-stage-guard",
      "required_for_release": true,
      "service_required": false,
      "command": "bash scripts/ci_run_artifact_stage_guard.sh --scope <backend|frontend> --stage-dir <dir> --artifact-name <artifact>",
      "notes": "Runs after e2e finalization to ensure diagnostics artifacts are staged before upload."
    },
    {
      "gate_id": "release-visibility-summary",
      "required_for_release": true,
      "service_required": false,
      "command": "bash scripts/ci_run_release_gate.sh --phase all --summary-file <path> --json-summary-file <path>",
      "notes": "Captures resolved phases and step results for release approval and post-release comparison."
    },
    {
      "gate_id": "rollback-decision-log",
      "required_for_release": true,
      "service_required": false,
      "command": "cat $GITHUB_STEP_SUMMARY",
      "notes": "Confirms the release summary keeps enough gate, e2e, and artifact guard context to decide rollback."
    },
    {
      "gate_id": "artifact-retention-policy",
      "required_for_release": true,
      "service_required": false,
      "command": "grep -R \"retention-days: 14\" .github/workflows",
      "notes": "Ensures uploaded release, backend e2e, and frontend e2e artifacts have an explicit two-week retention window."
    }
  ]
}
JSON
}

write_output() {
  if [ -n "${output_file}" ]; then
    mkdir -p "$(dirname "${output_file}")"
    "$@" > "${output_file}"
    echo "release_readiness_matrix=${output_file}"
  else
    "$@"
  fi
}

if [ "${format}" = "markdown" ]; then
  write_output render_markdown
else
  write_output render_json
fi
