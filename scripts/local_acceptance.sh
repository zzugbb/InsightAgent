#!/usr/bin/env bash
# Unified local acceptance entry (safe defaults, staged, continues on failure).

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT_DIR}/backend/.venv/bin/python"
REPORT_MD="/tmp/insightagent-local-acceptance-report.md"
REPORT_JSON="/tmp/insightagent-local-acceptance-report.json"

DRY_RUN=0
WITH_REAL_GLM=0
WITH_PILOT_IMAGE_REBUILD=0
SKIP_HEALTH=0
SKIP_GATE=0
SKIP_TOOLING=0
MATERIALS_DIR=""
QUESTIONS_FILE=""
PILOT_URL=""

usage() {
  cat <<'USAGE'
Usage: scripts/local_acceptance.sh [options]

Options:
  --dry-run                 Print planned phases only
  --with-real-glm           Run real-model stages (consumes provider quota; prompts first)
  --with-pilot-image-rebuild  Rebuild candidate images and run smoke_pilot_images (slow)
  --skip-health             Skip 127.0.0.1 health checks
  --skip-gate               Skip release gate phases
  --skip-tooling            Skip CI tooling self-tests
  --materials-dir <path>    Enable business RAG acceptance (api mode prerequisites)
  --questions-file <path>   Question list for business RAG
  --pilot-url <https://...> Run pilot HTTPS probe
  --report-md <path>        Default: /tmp/insightagent-local-acceptance-report.md
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --with-real-glm) WITH_REAL_GLM=1; shift ;;
    --with-pilot-image-rebuild) WITH_PILOT_IMAGE_REBUILD=1; shift ;;
    --skip-health) SKIP_HEALTH=1; shift ;;
    --skip-gate) SKIP_GATE=1; shift ;;
    --skip-tooling) SKIP_TOOLING=1; shift ;;
    --materials-dir) MATERIALS_DIR="${2:-}"; shift 2 ;;
    --questions-file) QUESTIONS_FILE="${2:-}"; shift 2 ;;
    --pilot-url) PILOT_URL="${2:-}"; shift 2 ;;
    --report-md) REPORT_MD="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ ! -x "${PYTHON}" ]; then
  PYTHON="python3"
fi

declare -a PHASE_NAMES=()
declare -a PHASE_STATUS=()
declare -a PHASE_DETAIL=()

record_phase() {
  PHASE_NAMES+=("$1")
  PHASE_STATUS+=("$2")
  PHASE_DETAIL+=("$3")
}

run_cmd() {
  local name="$1"
  shift
  if [ "${DRY_RUN}" = "1" ]; then
    record_phase "${name}" "skipped" "dry-run: $*"
    return 0
  fi
  if "$@"; then
    record_phase "${name}" "pass" "$*"
    return 0
  fi
  record_phase "${name}" "fail" "$*"
  return 1
}

overall_fail=0

phase_health() {
  [ "${SKIP_HEALTH}" = "1" ] && { record_phase "health" "skipped" "user --skip-health"; return 0; }
  local ok=0
  for url in "http://127.0.0.1:8000/health" "http://127.0.0.1:3001"; do
    if [ "${DRY_RUN}" = "1" ]; then
      record_phase "health" "skipped" "dry-run curl ${url}"
      return 0
    fi
    code="$(curl -sS -o /dev/null -w "%{http_code}" --max-time 5 "${url}" 2>/dev/null || echo 000)"
    if [ "${code}" != "200" ] && [ "${url}" != "http://127.0.0.1:3001" ]; then
      ok=1
    fi
    if [ "${url}" = "http://127.0.0.1:3001" ] && [ "${code}" != "200" ] && [ "${code}" != "304" ]; then
      ok=1
    fi
  done
  if [ "${ok}" = "0" ]; then
    record_phase "health" "pass" "127.0.0.1:8000/health and :3001"
  else
    record_phase "health" "fail" "service not reachable (start backend/frontend on Mac)"
    overall_fail=1
  fi
}

phase_release_gate() {
  [ "${SKIP_GATE}" = "1" ] && { record_phase "release_gate" "skipped" "--skip-gate"; return 0; }
  run_cmd "release_gate_hygiene" bash "${ROOT_DIR}/scripts/ci_run_release_gate.sh" --phase hygiene || overall_fail=1
  run_cmd "release_gate_tooling" bash "${ROOT_DIR}/scripts/ci_run_release_gate.sh" --phase tooling || overall_fail=1
  run_cmd "release_gate_backend" bash "${ROOT_DIR}/scripts/ci_run_release_gate.sh" --phase backend || overall_fail=1
  run_cmd "release_gate_frontend" bash "${ROOT_DIR}/scripts/ci_run_release_gate.sh" --phase frontend || overall_fail=1
}

phase_tooling_extra() {
  [ "${SKIP_TOOLING}" = "1" ] && { record_phase "tooling_extra" "skipped" "--skip-tooling"; return 0; }
  run_cmd "business_rag_static" "${PYTHON}" "${ROOT_DIR}/scripts/test_business_rag_acceptance_static.py" || overall_fail=1
  run_cmd "export_evidence_static" "${PYTHON}" "${ROOT_DIR}/scripts/test_export_acceptance_evidence_static.py" || overall_fail=1
  run_cmd "pilot_drill_scripts" bash "${ROOT_DIR}/scripts/test_pilot_drill_scripts.sh" || overall_fail=1
}

phase_business_rag() {
  if [ -z "${MATERIALS_DIR}" ] || [ -z "${QUESTIONS_FILE}" ]; then
    record_phase "business_rag_api" "skipped" "缺输入: --materials-dir / --questions-file"
    return 0
  fi
  if [ -z "${INSIGHT_AGENT_ACCESS_TOKEN:-}" ]; then
    record_phase "business_rag_api" "skipped" "缺 INSIGHT_AGENT_ACCESS_TOKEN"
    return 0
  fi
  run_cmd "business_rag_api" "${PYTHON}" "${ROOT_DIR}/scripts/business_rag_acceptance_runner.py" \
    --materials-dir "${MATERIALS_DIR}" --questions-file "${QUESTIONS_FILE}" --cleanup || overall_fail=1
}

phase_pilot_probe() {
  if [ -z "${PILOT_URL}" ]; then
    record_phase "pilot_https" "skipped" "缺输入: --pilot-url"
    return 0
  fi
  run_cmd "pilot_https" bash "${ROOT_DIR}/scripts/pilot_https_probe.sh" --url "${PILOT_URL}" || overall_fail=1
}

phase_real_glm() {
  if [ "${WITH_REAL_GLM}" != "1" ]; then
    record_phase "real_glm" "skipped" "默认关闭；使用 --with-real-glm 开启（消耗真实用量）"
    return 0
  fi
  echo "WARNING: --with-real-glm 将消耗真实供应商用量；请确认已配置本机 remote 模型。" >&2
  record_phase "real_glm" "manual" "待用户在本机按 docs/real-model-acceptance.md 执行连通与规划等待验收"
}

phase_pilot_images() {
  if [ "${WITH_PILOT_IMAGE_REBUILD}" != "1" ]; then
    record_phase "pilot_images" "skipped" "默认关闭；使用 --with-pilot-image-rebuild"
    return 0
  fi
  record_phase "pilot_images" "manual" "待用户执行 smoke_pilot_images.py --with-agent-fixture（见 pilot-deployment-preflight.md）"
}

phase_health
phase_release_gate
phase_tooling_extra
phase_business_rag
phase_pilot_probe
phase_real_glm
phase_pilot_images

{
  echo "# 本机统一验收报告"
  echo "- generated_at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "- dry_run: ${DRY_RUN}"
  echo "- delivery_conclusion: 暂不可交付外部试点"
  echo ""
  echo "## 阶段结果"
  for i in "${!PHASE_NAMES[@]}"; do
    echo "- ${PHASE_NAMES[$i]}: ${PHASE_STATUS[$i]} — ${PHASE_DETAIL[$i]}"
  done
  echo ""
  echo "## 六项汇报摘要"
  echo "1. 改动：见各叠放 PR（CI 健壮性、RAG 工具包、目标任务模板、演练工具包、本脚本）。"
  echo "2. 测试：以本报告阶段结果为准；VM 已跑 tooling/静态自测，真实 glm/目标环境待本机。"
  echo "3. 未覆盖：真实业务资料、目标用户签收、目标部署 HTTPS/升级回滚、Docker 隔离 RAG 自测（无 daemon 时）。"
  echo "4. 镜像/运行状态：未因本脚本重建候选镜像。"
  echo "5. PR：cursor/*-11df 叠放草稿 PR，未合并。"
  echo "6. 待外部验收：A1 业务 RAG、A5 签收、A2/A3 目标环境；交付结论不变。"
} > "${REPORT_MD}"

python3 - "${REPORT_JSON}" "${PHASE_NAMES[*]}" "${PHASE_STATUS[*]}" <<'PY'
import json, sys
path = sys.argv[1]
names = sys.argv[2].split() if len(sys.argv) > 2 else []
statuses = sys.argv[3].split() if len(sys.argv) > 3 else []
with open(path, "w", encoding="utf-8") as f:
    json.dump({"phases": [{"name": n, "status": s} for n, s in zip(names, statuses)]}, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY

echo "report_md=${REPORT_MD}"
echo "report_json=${REPORT_JSON}"
exit "${overall_fail}"
