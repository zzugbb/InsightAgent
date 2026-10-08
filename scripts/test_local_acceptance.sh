#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "${ROOT}/scripts/local_acceptance.sh" --dry-run --skip-health 2>&1 | tee /tmp/local-acceptance-dry.log
grep -q "dry_run: 1" /tmp/insightagent-local-acceptance-report.md
test -f /tmp/insightagent-local-acceptance-report.md
echo "local_acceptance dry-run test passed"
