#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  printf 'Usage: %s RELEASE_ASSET_DIRECTORY [OUTPUT.iso]\n' "$0" >&2
  exit 2
fi
if [[ ! -d "$1" ]]; then
  printf 'Release asset directory not found: %s\n' "$1" >&2
  exit 2
fi
asset_dir=$(cd "$1" && pwd -P)
checksum_files=("$asset_dir"/*.iso.sha256)
if [[ ${#checksum_files[@]} -ne 1 || ! -f "${checksum_files[0]}" ]]; then
  printf 'Expected exactly one ISO SHA256 file in %s\n' "$asset_dir" >&2
  exit 2
fi
checksum_file=${checksum_files[0]}
iso_name=$(basename "$checksum_file" .sha256)
output=${2:-"$asset_dir/$iso_name"}
parts=()
for part in "$asset_dir/$iso_name".part[0-9][0-9]; do
  if [[ -f "$part" ]]; then
    parts+=("$part")
  fi
done
if [[ ${#parts[@]} -eq 0 || ! -r "$checksum_file" ]]; then
  printf 'Release ISO parts or checksum file are missing from %s\n' "$asset_dir" >&2
  exit 2
fi
if [[ -e "$output" ]]; then
  printf 'Refusing to overwrite existing file: %s\n' "$output" >&2
  exit 2
fi

case "$output" in
  /*) ;;
  *) output="$(pwd -P)/$output" ;;
esac
output_dir=$(dirname "$output")
mkdir -p "$output_dir"
temporary=$(mktemp "$output_dir/.custom-iso.XXXXXX")
trap 'rm -f "$temporary"' EXIT
cat "${parts[@]}" > "$temporary"
expected=$(awk 'NR == 1 {print $1; exit}' "$checksum_file")
if command -v shasum >/dev/null 2>&1; then
  actual=$(shasum -a 256 "$temporary" | awk '{print $1}')
elif command -v sha256sum >/dev/null 2>&1; then
  actual=$(sha256sum "$temporary" | awk '{print $1}')
else
  printf 'Neither shasum nor sha256sum is available.\n' >&2
  exit 2
fi
if [[ "$actual" != "$expected" ]]; then
  printf 'ISO checksum mismatch: expected %s, found %s.\n' "$expected" "$actual" >&2
  exit 1
fi
mv "$temporary" "$output"
trap - EXIT
printf 'Reassembled verified ISO: %s\n' "$output"