#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "${ROOT}/scripts/pilot_https_probe.sh" --url https://example.com --summary-file /tmp/pilot-https-probe-test.md >/dev/null || true
grep -q "pilot HTTPS probe" /tmp/pilot-https-probe-test.md

# Capture first, then match: under pipefail, `cmd | grep -q` lets grep exit on the first
# hit while cmd is still writing, so cmd dies with SIGPIPE (141); reproducible on macOS.
drill_output="$(bash "${ROOT}/scripts/pilot_backup_restore_drill.sh" --project dry --snapshot-dir /tmp/snap --dry-run)"
for expected in "-p dry up -d postgres chroma" "backup --project dry " "restore --project dry-restored " \
  "-p dry down -v" "-p dry-restored down -v"; do
  if [[ "${drill_output}" != *"[dry-run]"*"${expected}"* ]]; then
    echo "pilot drill dry-run output missing: ${expected}" >&2
    exit 1
  fi
done

echo "pilot_drill_scripts tests passed"
