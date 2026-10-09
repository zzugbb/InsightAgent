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
  --report-json <path>      Default: /tmp/insightagent-local-acceptance-report.json
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
    --report-json) REPORT_JSON="${2:-}"; shift 2 ;;
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

# Runtime facts for the six-item summary; read-only, never history baked into the script.
git_ro() {
  git -C "${ROOT_DIR}" "$@" 2>/dev/null
}

GIT_BRANCH="unknown"
GIT_COMMIT="unknown"
GIT_UPSTREAM="none"
GIT_AHEAD="unknown"
GIT_BEHIND="unknown"
GIT_TRACKED_CHANGES="unknown"
GIT_UNTRACKED="unknown"
GIT_BASE_REF="none"
GIT_COMMITS_OVER_BASE="unknown"
BACKUP_PLAN_STATE="unknown"
if git_ro rev-parse --is-inside-work-tree >/dev/null; then
  GIT_BRANCH="$(git_ro symbolic-ref --short -q HEAD || echo "detached")"
  GIT_COMMIT="$(git_ro rev-parse --short HEAD || echo "unknown")"
  if upstream="$(git_ro rev-parse --abbrev-ref --symbolic-full-name '@{u}')"; then
    GIT_UPSTREAM="${upstream}"
    if counts="$(git_ro rev-list --left-right --count '@{u}...HEAD')"; then
      GIT_BEHIND="$(printf '%s' "${counts}" | awk '{print $1}')"
      GIT_AHEAD="$(printf '%s' "${counts}" | awk '{print $2}')"
    fi
  fi
  if git_ro rev-parse --verify -q origin/main >/dev/null; then
    GIT_BASE_REF="origin/main"
    GIT_COMMITS_OVER_BASE="$(git_ro rev-list --count origin/main..HEAD || echo "unknown")"
  fi
  if porcelain="$(git_ro status --porcelain=v1 --untracked-files=normal)"; then
    GIT_TRACKED_CHANGES="$(printf '%s\n' "${porcelain}" | awk 'NF && substr($0, 1, 2) != "??"' | wc -l | tr -d ' ')"
    GIT_UNTRACKED="$(printf '%s\n' "${porcelain}" | awk 'substr($0, 1, 2) == "??"' | wc -l | tr -d ' ')"
  fi
  if git_ro diff --quiet HEAD -- data/insightagent.plan.back.md; then
    BACKUP_PLAN_STATE="unchanged"
  else
    BACKUP_PLAN_STATE="modified"
  fi
fi

PILOT_IMAGES="docker unavailable"
if command -v docker >/dev/null 2>&1; then
  if images="$(docker image ls --format '{{.Repository}}:{{.Tag}}' 2>/dev/null)"; then
    PILOT_IMAGES="$(printf '%s\n' "${images}" | awk '/^insightagent-(backend|frontend):pilot-/' | sort | paste -sd ',' - | sed 's/,/, /g')"
    [ -n "${PILOT_IMAGES}" ] || PILOT_IMAGES="none"
  fi
fi

count_status() {
  local wanted="$1" total=0 status
  for status in "${PHASE_STATUS[@]}"; do
    [ "${status}" = "${wanted}" ] && total=$((total + 1))
  done
  echo "${total}"
}

phases_with_status() {
  local wanted="$1" out="" i
  for i in "${!PHASE_NAMES[@]}"; do
    if [ "${PHASE_STATUS[$i]}" = "${wanted}" ]; then
      out="${out:+${out}, }${PHASE_NAMES[$i]}"
    fi
  done
  echo "${out:-无}"
}

PASS_COUNT="$(count_status pass)"
FAIL_COUNT="$(count_status fail)"
SKIPPED_COUNT="$(count_status skipped)"
MANUAL_COUNT="$(count_status manual)"
GENERATED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

{
  echo "# 本机统一验收报告"
  echo "- generated_at: ${GENERATED_AT}"
  echo "- dry_run: ${DRY_RUN}"
  echo "- delivery_conclusion: 暂不可交付外部试点"
  echo ""
  echo "## 仓库状态（运行时读取）"
  echo "- branch: ${GIT_BRANCH}"
  echo "- commit: ${GIT_COMMIT}"
  echo "- upstream: ${GIT_UPSTREAM} (ahead ${GIT_AHEAD}, behind ${GIT_BEHIND})"
  echo "- commits_over_base: ${GIT_COMMITS_OVER_BASE} (base ${GIT_BASE_REF})"
  echo "- worktree: tracked_changes ${GIT_TRACKED_CHANGES}, untracked ${GIT_UNTRACKED}"
  echo "- backup_plan: ${BACKUP_PLAN_STATE}"
  echo "- pilot_images: ${PILOT_IMAGES}"
  echo ""
  echo "## 阶段结果"
  for i in "${!PHASE_NAMES[@]}"; do
    echo "- ${PHASE_NAMES[$i]}: ${PHASE_STATUS[$i]} — ${PHASE_DETAIL[$i]}"
  done
  echo ""
  echo "## 六项汇报摘要"
  echo "1. 改动：本脚本只读取并运行检查，不修改代码；当前 ${GIT_BRANCH}@${GIT_COMMIT}，相对 ${GIT_BASE_REF} 多 ${GIT_COMMITS_OVER_BASE} 个提交，具体改动以对应提交/PR 为准。"
  echo "2. 测试：pass ${PASS_COUNT} / fail ${FAIL_COUNT} / skipped ${SKIPPED_COUNT} / manual ${MANUAL_COUNT}；失败阶段：$(phases_with_status fail)。"
  echo "3. 未覆盖：本次跳过 $(phases_with_status skipped)；需人工 $(phases_with_status manual)；真实业务资料、目标用户签收、目标部署 HTTPS/升级回滚始终需外部证据。"
  echo "4. 镜像/运行状态：本脚本不构建、不删除镜像；本机候选镜像 ${PILOT_IMAGES}。"
  echo "5. 提交与工作区：${GIT_BRANCH}@${GIT_COMMIT}，upstream ${GIT_UPSTREAM}（ahead ${GIT_AHEAD} / behind ${GIT_BEHIND}）；已跟踪改动 ${GIT_TRACKED_CHANGES}、未跟踪 ${GIT_UNTRACKED}；备份计划 ${BACKUP_PLAN_STATE}。"
  echo "6. 待外部验收：A1 业务 RAG、A5 签收、A2/A3 目标环境；交付结论：暂不可交付外部试点。"
} > "${REPORT_MD}"

python3 - "${REPORT_JSON}" "${PHASE_NAMES[*]}" "${PHASE_STATUS[*]}" \
  "${GENERATED_AT}" "${DRY_RUN}" "${GIT_BRANCH}" "${GIT_COMMIT}" "${GIT_UPSTREAM}" "${GIT_AHEAD}" \
  "${GIT_BEHIND}" "${GIT_BASE_REF}" "${GIT_COMMITS_OVER_BASE}" "${GIT_TRACKED_CHANGES}" \
  "${GIT_UNTRACKED}" "${BACKUP_PLAN_STATE}" "${PILOT_IMAGES}" <<'PY'
import json, sys
(path, names, statuses, generated_at, dry_run, branch, commit, upstream, ahead, behind,
 base_ref, over_base, tracked, untracked, backup_plan, pilot_images) = sys.argv[1:17]
with open(path, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": generated_at,
        "dry_run": dry_run == "1",
        "delivery_conclusion": "暂不可交付外部试点",
        "git": {"branch": branch, "commit": commit, "upstream": upstream, "ahead": ahead,
                "behind": behind, "base_ref": base_ref, "commits_over_base": over_base,
                "tracked_changes": tracked, "untracked": untracked, "backup_plan": backup_plan},
        "pilot_images": pilot_images,
        "phases": [{"name": n, "status": s} for n, s in zip(names.split(), statuses.split())],
    }, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY

echo "report_md=${REPORT_MD}"
echo "report_json=${REPORT_JSON}"
exit "${overall_fail}"
