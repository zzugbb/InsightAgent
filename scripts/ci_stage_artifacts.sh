#!/usr/bin/env bash

set -euo pipefail

list_file=""
output_dir=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_stage_artifacts.sh --list-file <path> --output-dir <path>

Behavior:
  - Read artifact paths from list file (one path per line)
  - Ignore blank lines and lines starting with '#'
  - Copy existing files/directories into output dir while preserving path shape
  - Write summary manifest to <output-dir>/_manifest.txt
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --list-file) list_file="${2:-}"; shift 2 ;;
    --output-dir) output_dir="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${list_file}" ] || [ -z "${output_dir}" ]; then
  echo "--list-file and --output-dir are required" >&2
  usage >&2
  exit 2
fi
if [ ! -f "${list_file}" ]; then
  echo "list file not found: ${list_file}" >&2
  exit 2
fi

rm -rf "${output_dir}"
mkdir -p "${output_dir}"

included_count=0
missing_count=0
included_items=""
missing_items=""

stage_one() {
  local src="$1"
  local rel="${src}"
  local dest=""

  if [[ "${src}" = /* ]]; then
    rel="${src#/}"
  fi
  dest="${output_dir}/${rel}"
  mkdir -p "$(dirname "${dest}")"
  cp -R "${src}" "${dest}"
}

while IFS= read -r line || [ -n "${line}" ]; do
  # Trim leading/trailing whitespace.
  path="$(printf '%s' "${line}" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  if [ -z "${path}" ]; then
    continue
  fi
  if [[ "${path}" = \#* ]]; then
    continue
  fi

  if [ -e "${path}" ]; then
    stage_one "${path}"
    included_count=$((included_count + 1))
    included_items="${included_items}\n- ${path}"
  else
    missing_count=$((missing_count + 1))
    missing_items="${missing_items}\n- ${path}"
  fi
done < "${list_file}"

manifest="${output_dir}/_manifest.txt"
{
  echo "# staged artifacts"
  echo "- list_file: ${list_file}"
  echo "- output_dir: ${output_dir}"
  echo "- included_count: ${included_count}"
  echo "- missing_count: ${missing_count}"
  echo
  echo "## included"
  if [ "${included_count}" -gt 0 ]; then
    printf '%b\n' "${included_items}"
  else
    echo "(none)"
  fi
  echo
  echo "## missing"
  if [ "${missing_count}" -gt 0 ]; then
    printf '%b\n' "${missing_items}"
  else
    echo "(none)"
  fi
} > "${manifest}"

echo "staged_output_dir=${output_dir}"
echo "included_count=${included_count}"
echo "missing_count=${missing_count}"
echo "manifest=${manifest}"
