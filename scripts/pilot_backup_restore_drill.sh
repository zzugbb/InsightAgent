#!/usr/bin/env bash
# Timeboxed backup/restore drill using local_stack_snapshot on a disposable compose project.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT_DIR}/backend/.venv/bin/python"
COMPOSE_FILE="${ROOT_DIR}/compose.full.yml"
project=""
snapshot_dir=""
dry_run="0"

usage() {
  cat <<'USAGE'
Usage:
  scripts/pilot_backup_restore_drill.sh --project <unique-name> --snapshot-dir <path> [--dry-run]

Creates ONLY the named compose project/volumes. Refuses to run without explicit --project.
Records elapsed seconds for backup and restore phases to stdout JSON (no secrets).
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project) project="${2:-}"; shift 2 ;;
    --snapshot-dir) snapshot_dir="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "${project}" ] || [ -z "${snapshot_dir}" ]; then
  usage >&2
  exit 2
fi

if [ ! -x "${PYTHON}" ]; then
  PYTHON="python3"
fi

if [ "${dry_run}" = "1" ]; then
  echo "[dry-run] docker compose -f ${COMPOSE_FILE} -p ${project} up -d postgres chroma"
  echo "[dry-run] docker compose -f ${COMPOSE_FILE} -p ${project} stop"
  echo "[dry-run] ${PYTHON} scripts/local_stack_snapshot.py backup --project ${project} --snapshot ${snapshot_dir}"
  echo "[dry-run] ${PYTHON} scripts/local_stack_snapshot.py restore --project ${project}-restored --snapshot ${snapshot_dir}"
  echo "[dry-run] docker compose -f ${COMPOSE_FILE} -p ${project} down -v"
  echo "[dry-run] docker compose -f ${COMPOSE_FILE} -p ${project}-restored down -v"
  exit 0
fi

start_total=$(date +%s)
docker compose -f "${COMPOSE_FILE}" -p "${project}" up -d postgres chroma
docker compose -f "${COMPOSE_FILE}" -p "${project}" stop

backup_start=$(date +%s)
"${PYTHON}" "${ROOT_DIR}/scripts/local_stack_snapshot.py" backup --project "${project}" --snapshot "${snapshot_dir}"
backup_end=$(date +%s)

restore_project="${project}-restored"
restore_start=$(date +%s)
"${PYTHON}" "${ROOT_DIR}/scripts/local_stack_snapshot.py" restore --project "${restore_project}" --snapshot "${snapshot_dir}"
restore_end=$(date +%s)

end_total=$(date +%s)

python3 - <<PY
import json
print(json.dumps({
  "project": "${project}",
  "restore_project": "${restore_project}",
  "snapshot_dir": "${snapshot_dir}",
  "backup_seconds": ${backup_end} - ${backup_start},
  "restore_seconds": ${restore_end} - ${restore_start},
  "total_seconds": ${end_total} - ${start_total},
  "note": "fixture timing only; target RPO/RTO requires real environment drill record",
}, ensure_ascii=False))
PY

docker compose -f "${COMPOSE_FILE}" -p "${project}" down -v
docker compose -f "${COMPOSE_FILE}" -p "${restore_project}" down -v
