#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  printf 'Usage: %s BUNDLE_DIRECTORY\n' "$0" >&2
  exit 2
fi
exec python3 "$(dirname "${BASH_SOURCE[0]}")/generate_manifest.py" "$1"