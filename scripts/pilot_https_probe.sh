#!/usr/bin/env bash
# Read-only HTTPS / access boundary probe for a pilot URL (no credentials printed).

set -euo pipefail

url=""
summary_file=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/pilot_https_probe.sh --url <https://host> [--summary-file <path>]
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --url) url="${2:-}"; shift 2 ;;
    --summary-file) summary_file="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "${url}" ]; then
  usage >&2
  exit 2
fi

health_url="${url%/}/health"
lines=()
lines+=("### pilot HTTPS probe")
lines+=("- target: ${url}")
lines+=("- health_url: ${health_url}")

code="$(curl -sS -o /tmp/pilot-https-probe-body.txt -w "%{http_code}" --max-time 15 "${health_url}" || echo "000")"
lines+=("- health_http_code: ${code}")

if command -v openssl >/dev/null 2>&1; then
  host="$(printf '%s' "${url}" | sed -E 's#^https?://([^/:]+).*#\1#')"
  cert_info="$(echo | openssl s_client -servername "${host}" -connect "${host}:443" 2>/dev/null | openssl x509 -noout -dates -subject 2>/dev/null || true)"
  if [ -n "${cert_info}" ]; then
    while IFS= read -r line; do
      lines+=("- cert: ${line}")
    done <<< "${cert_info}"
  else
    lines+=("- cert: unavailable (non-TLS or handshake failed)")
  fi
fi

printf '%s\n' "${lines[@]}"
if [ -n "${summary_file}" ]; then
  printf '%s\n' "${lines[@]}" >> "${summary_file}"
fi

if [ "${code}" = "200" ]; then
  exit 0
fi
exit 1
