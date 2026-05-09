#!/usr/bin/env bash

set -euo pipefail

phase=""
api_base_url=""
frontend_base_url=""
frontend_dir="frontend"
dry_run="0"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_run_frontend_e2e.sh --phase <smoke|full|rerun-last-failed> --api-base-url <url> --frontend-base-url <url> [options]

Options:
  --frontend-dir <path>   Default: frontend
  --dry-run               Print commands without executing
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --phase) phase="${2:-}"; shift 2 ;;
    --api-base-url) api_base_url="${2:-}"; shift 2 ;;
    --frontend-base-url) frontend_base_url="${2:-}"; shift 2 ;;
    --frontend-dir) frontend_dir="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${phase}" ] || [ -z "${api_base_url}" ] || [ -z "${frontend_base_url}" ]; then
  echo "--phase, --api-base-url and --frontend-base-url are required" >&2
  usage >&2
  exit 2
fi

if [ "${phase}" != "smoke" ] && [ "${phase}" != "full" ] && [ "${phase}" != "rerun-last-failed" ]; then
  echo "invalid --phase: ${phase} (expected smoke|full|rerun-last-failed)" >&2
  exit 2
fi

if [ ! -d "${frontend_dir}" ] && [ "${dry_run}" != "1" ]; then
  echo "frontend dir not found: ${frontend_dir}" >&2
  exit 2
fi

if [ "${phase}" = "smoke" ]; then
  cmd="cd ${frontend_dir} && PLAYWRIGHT_API_BASE_URL=${api_base_url} PLAYWRIGHT_BASE_URL=${frontend_base_url} npm run test:e2e:smoke:matrix"
elif [ "${phase}" = "full" ]; then
  cmd="cd ${frontend_dir} && PLAYWRIGHT_API_BASE_URL=${api_base_url} PLAYWRIGHT_BASE_URL=${frontend_base_url} npm run test:e2e"
else
  cmd="cd ${frontend_dir} && PLAYWRIGHT_API_BASE_URL=${api_base_url} PLAYWRIGHT_BASE_URL=${frontend_base_url} npm run test:e2e -- --last-failed --output=test-results/last-failed"
fi

if [ "${dry_run}" = "1" ]; then
  echo "[dry-run] ${cmd}"
else
  eval "${cmd}"
fi
