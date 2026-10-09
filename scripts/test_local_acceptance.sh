#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/local-acceptance-test.XXXXXX")"
trap 'rm -rf "${WORK}"' EXIT

fail() {
  echo "local_acceptance test failed: $*" >&2
  exit 1
}

# Default report paths keep working.
bash "${ROOT}/scripts/local_acceptance.sh" --dry-run --skip-health > /tmp/local-acceptance-dry.log 2>&1
test -f /tmp/insightagent-local-acceptance-report.md
grep -q "dry_run: 1" /tmp/insightagent-local-acceptance-report.md

# Summary is built from runtime git state, not text baked into the script.
md="${WORK}/report.md"
json="${WORK}/report.json"
bash "${ROOT}/scripts/local_acceptance.sh" --dry-run --skip-health --report-md "${md}" --report-json "${json}" \
  > "${WORK}/run.log" 2>&1
expected_branch="$(git -C "${ROOT}" symbolic-ref --short -q HEAD || echo detached)"
expected_commit="$(git -C "${ROOT}" rev-parse --short HEAD)"
grep -qxF -- "- branch: ${expected_branch}" "${md}" || fail "branch line missing"
grep -qxF -- "- commit: ${expected_commit}" "${md}" || fail "commit line missing"
grep -qF -- "5. 提交与工作区：${expected_branch}@${expected_commit}" "${md}" || fail "item 5 not runtime"
grep -qF -- "2. 测试：pass 0 / fail 0 / skipped " "${md}" || fail "item 2 counts missing"
grep -qF -- "delivery_conclusion: 暂不可交付外部试点" "${md}" || fail "delivery conclusion missing"
if grep -qE -- '11df|叠放|草稿 PR' "${md}" "${ROOT}/scripts/local_acceptance.sh"; then
  fail "stale hard-coded PR text present"
fi
python3 - "${json}" "${expected_branch}" "${expected_commit}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["dry_run"] is True
assert data["delivery_conclusion"] == "暂不可交付外部试点"
assert data["git"]["branch"] == sys.argv[2], data["git"]
assert data["git"]["commit"] == sys.argv[3], data["git"]
assert data["git"]["backup_plan"] in {"unchanged", "modified"}
assert data["phases"] and all(p["status"] == "skipped" for p in data["phases"])
PY

# Outside a git checkout the report degrades to "unknown" instead of failing.
mkdir -p "${WORK}/nogit/scripts"
cp "${ROOT}/scripts/local_acceptance.sh" "${WORK}/nogit/scripts/"
GIT_CEILING_DIRECTORIES="${WORK}" bash "${WORK}/nogit/scripts/local_acceptance.sh" --dry-run --skip-health \
  --report-md "${WORK}/nogit.md" --report-json "${WORK}/nogit.json" > "${WORK}/nogit.log" 2>&1
grep -qxF -- "- branch: unknown" "${WORK}/nogit.md" || fail "non-git fallback missing"
grep -qxF -- "- backup_plan: unknown" "${WORK}/nogit.md" || fail "non-git backup plan fallback missing"

echo "local_acceptance dry-run test passed"
