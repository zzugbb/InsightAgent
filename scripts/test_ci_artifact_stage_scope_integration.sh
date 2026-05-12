#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCOPE_SCRIPT="${ROOT_DIR}/scripts/ci_resolve_artifact_stage_scope_config.sh"
PATH_LEVEL_SCRIPT="${ROOT_DIR}/scripts/ci_resolve_artifact_stage_path_level.sh"

assert_contains() {
  local haystack="$1"
  local needle="$2"
  if ! grep -Fq -- "$needle" <<<"$haystack"; then
    echo "assertion failed: expected [$needle]" >&2
    echo "$haystack" >&2
    exit 1
  fi
}

extract_value() {
  local text="$1"
  local key="$2"
  printf '%s\n' "${text}" | awk -F= -v k="${key}" '$1==k {print substr($0, length(k)+2)}' | tail -n 1
}

main() {
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT

  backend_cfg=$(bash "${SCOPE_SCRIPT}" --scope backend)
  backend_regex=$(extract_value "${backend_cfg}" "path_regex")
  cat > "${tmp}/backend-changed.txt" <<'TXT'
backend/app/main.py
TXT
  out=$(bash "${PATH_LEVEL_SCRIPT}" \
    --scope backend \
    --changed-files "${tmp}/backend-changed.txt" \
    --event-name pull_request \
    --ref refs/pull/3/merge \
    --pr-level fail-on-empty \
    --pr-ref-regex '^refs/pull/[0-9]+/merge$' \
    --path-regex "${backend_regex}" \
    --fallback-level warn)
  assert_contains "${out}" "strict_level=fail-on-empty"
  assert_contains "${out}" "policy_source=path_match"

  frontend_cfg=$(bash "${SCOPE_SCRIPT}" --scope frontend)
  frontend_regex=$(extract_value "${frontend_cfg}" "path_regex")
  cat > "${tmp}/frontend-changed.txt" <<'TXT'
docs/notes.md
TXT
  out=$(bash "${PATH_LEVEL_SCRIPT}" \
    --scope frontend \
    --changed-files "${tmp}/frontend-changed.txt" \
    --event-name pull_request \
    --ref refs/pull/5/merge \
    --pr-level fail-on-empty \
    --pr-ref-regex '^refs/pull/[0-9]+/merge$' \
    --path-regex "${frontend_regex}" \
    --fallback-level warn)
  assert_contains "${out}" "strict_level=warn"
  assert_contains "${out}" "policy_source=path_miss"

  echo "ci_artifact_stage_scope_integration tests passed"
}

main "$@"
