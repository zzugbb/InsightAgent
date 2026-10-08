#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo_root="${1:-${ROOT_DIR}}"

cd "${repo_root}"

# Line-start git conflict markers in tracked text files. ======= must be the
# whole line so longer underline rules are left alone.
pattern='^(<{7}( |$)|={7}[[:space:]]*$|>{7}( |$))'

set +e
matches="$(git grep -n -I -E "${pattern}" -- .)"
status=$?
set -e

if [ "${status}" -eq 1 ]; then
  exit 0
fi

if [ "${status}" -ne 0 ]; then
  echo "conflict marker scan failed (git grep exit ${status})" >&2
  exit "${status}"
fi

printf '%s\n' "${matches}" >&2
echo "tracked text files contain conflict markers" >&2
exit 1
