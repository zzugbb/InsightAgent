#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT_DIR}/scripts/ci_download_previous_release_gate_summary.sh"
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

assert_file_exists() {
  local file="$1"
  if [ ! -f "${file}" ]; then
    echo "expected file to exist: ${file}" >&2
    find "${TMP_DIR}" -maxdepth 4 -type f -print >&2 || true
    exit 1
  fi
}

main() {
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR:-}"' EXIT

  mkdir -p "${TMP_DIR}/bin"
  cat > "${TMP_DIR}/bin/gh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

if [ "$1" = "run" ] && [ "$2" = "list" ]; then
  printf '[{"databaseId":200,"status":"completed","conclusion":"success"},{"databaseId":100,"status":"completed","conclusion":"success"}]\n'
  exit 0
fi

if [ "$1" = "run" ] && [ "$2" = "download" ]; then
  run_id="$3"
  download_dir=""
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dir)
        download_dir="${2:-}"
        shift 2
        ;;
      *)
        shift
        ;;
    esac
  done
  mkdir -p "${download_dir}"
  cat > "${download_dir}/release-gate-summary.json" <<JSON
{
  "summary_kind": "release_gate",
  "summary_schema_version": 1,
  "result": "PASS_PREVIOUS_${run_id}",
  "step_summary": {"total": 9, "pass": 9, "fail": 0, "dry_run": 0},
  "failed_step_labels": []
}
JSON
  exit 0
fi

echo "unexpected gh invocation: $*" >&2
exit 1
SH
  chmod +x "${TMP_DIR}/bin/gh"

  PATH="${TMP_DIR}/bin:${PATH}" bash "${SCRIPT}" \
    --workflow release-gate.yml \
    --branch main \
    --current-run-id 200 \
    --output-file "${TMP_DIR}/previous-release-gate-summary.json" \
    --summary-file "${TMP_DIR}/download.md" \
    --json-summary-file "${TMP_DIR}/download.json"
  assert_file_exists "${TMP_DIR}/previous-release-gate-summary.json"
  "$(json_tool_python)" -m json.tool "${TMP_DIR}/download.json" >/dev/null
  assert_contains '"result": "PASS_PREVIOUS_100"' "${TMP_DIR}/previous-release-gate-summary.json"
  assert_contains "- summary_kind: release_gate_previous_summary_download" "${TMP_DIR}/download.md"
  assert_contains "- previous_available: yes" "${TMP_DIR}/download.md"
  assert_contains "- previous_run_id: 100" "${TMP_DIR}/download.md"
  assert_contains '"summary_kind": "release_gate_previous_summary_download"' "${TMP_DIR}/download.json"
  assert_contains '"previous_available": true' "${TMP_DIR}/download.json"
  assert_contains '"previous_run_id": 100' "${TMP_DIR}/download.json"
  assert_contains '"reason": "downloaded"' "${TMP_DIR}/download.json"

  bash "${SCRIPT}" \
    --branch main \
    --current-run-id 200 \
    --gh-bin "${TMP_DIR}/missing-gh" \
    --output-file "${TMP_DIR}/missing.json" \
    --summary-file "${TMP_DIR}/missing.md" \
    --json-summary-file "${TMP_DIR}/missing-summary.json"
  "$(json_tool_python)" -m json.tool "${TMP_DIR}/missing-summary.json" >/dev/null
  assert_contains "- previous_available: no" "${TMP_DIR}/missing.md"
  assert_contains "- reason: gh_unavailable" "${TMP_DIR}/missing.md"
  assert_contains '"previous_available": false' "${TMP_DIR}/missing-summary.json"
  assert_contains '"reason": "gh_unavailable"' "${TMP_DIR}/missing-summary.json"

  bash "${SCRIPT}" \
    --current-run-id 200 \
    --gh-bin "${TMP_DIR}/bin/gh" \
    --output-file "${TMP_DIR}/missing-branch.json" \
    --summary-file "${TMP_DIR}/missing-branch.md" \
    --json-summary-file "${TMP_DIR}/missing-branch-summary.json"
  assert_contains "- reason: missing_branch" "${TMP_DIR}/missing-branch.md"
  assert_contains '"reason": "missing_branch"' "${TMP_DIR}/missing-branch-summary.json"

  echo "ci_download_previous_release_gate_summary tests passed"
}

main "$@"
