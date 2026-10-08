#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "${ROOT}/scripts/pilot_https_probe.sh" --url https://example.com --summary-file /tmp/pilot-https-probe-test.md >/dev/null || true
grep -q "pilot HTTPS probe" /tmp/pilot-https-probe-test.md
bash "${ROOT}/scripts/pilot_backup_restore_drill.sh" --project dry --snapshot-dir /tmp/snap --dry-run | grep -q dry-run
echo "pilot_drill_scripts tests passed"
