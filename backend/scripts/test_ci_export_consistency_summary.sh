#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUMMARY_SCRIPT="${SCRIPT_DIR}/ci_export_consistency_summary.sh"
TMP_ROOT=""

assert_contains() {
  local file="$1"
  local expected="$2"
  if ! grep -Fq -- "${expected}" "${file}"; then
    echo "assertion failed: expected line not found"
    echo "expected: ${expected}"
    echo "file: ${file}"
    exit 1
  fi
}

write_success_log() {
  local file="$1"
  cat > "${file}" <<'LOG'
[1/7] 注册并保存 mock 设置
  - OK: auth + settings
[2/7] 创建任务并跑完整流
  - OK: task stream done
[3/7] shared-* 知识库跨角色语义与导出并存
  - OK: shared kb role semantics stay compatible with export checks
[4/7] 任务导出一致性
  - OK: task export json/markdown consistency + governance + download
[5/7] 会话导出一致性
  - OK: session export json/markdown consistency + task-level governance + download
[6/7] 负例：跨用户导出隔离
  - OK: cross-user export isolation checks
[7/7] 负例：跨资源不存在检查
  - OK: not-found checks
E2E export consistency passed:
- task export json/markdown schema, governance and summary consistency
- session export json/markdown stats consistency + task-level governance consistency
- download=true content-disposition headers
- shared-rag role semantics remain compatible with export flow
- cross-user export isolation checks
- export not-found responses
LOG
}

write_failure_log() {
  local file="$1"
  cat > "${file}" <<'LOG'
[1/7] login and create baseline data
  - OK: registered users and created baseline task/session
[2/7] task export json/markdown consistency + download
  - OK: task export payload and download headers are consistent
LOG
}

main() {
  TMP_ROOT="$(mktemp -d)"
  trap 'rm -rf "${TMP_ROOT:-}"' EXIT

  local ok_log="${TMP_ROOT}/ok.log"
  local ok_out="${TMP_ROOT}/ok.out"
  local ok_json="${TMP_ROOT}/ok.json"
  write_success_log "${ok_log}"
  bash "${SUMMARY_SCRIPT}" "${ok_log}" "${ok_json}" > "${ok_out}"

  assert_contains "${ok_out}" "- total_alerts: 0 (all counters within expected range)"
  assert_contains "${ok_out}" "- severity: P0=0, P1=0"
  assert_contains "${ok_json}" '"status": "ok"'
  assert_contains "${ok_json}" '"warning_total": 0'
  assert_contains "${ok_json}" '"step_total_expected": 7'

  local bad_log="${TMP_ROOT}/bad.log"
  local bad_out="${TMP_ROOT}/bad.out"
  local bad_json="${TMP_ROOT}/bad.json"
  write_failure_log "${bad_log}"
  bash "${SUMMARY_SCRIPT}" "${bad_log}" "${bad_json}" > "${bad_out}"

  assert_contains "${bad_out}" "- total_alerts:"
  assert_contains "${bad_out}" "[P0][backend-export-consistency]"
  assert_contains "${bad_json}" '"warning_total":'
  assert_contains "${bad_json}" '"warning_p0":'

  local missing_out="${TMP_ROOT}/missing.out"
  local missing_json="${TMP_ROOT}/missing.json"
  bash "${SUMMARY_SCRIPT}" "${TMP_ROOT}/missing.log" "${missing_json}" > "${missing_out}"
  assert_contains "${missing_out}" "- Export consistency log is missing."
  assert_contains "${missing_json}" '"status": "log_missing"'

  echo "ci_export_consistency_summary fixture tests passed"
}

main "$@"
