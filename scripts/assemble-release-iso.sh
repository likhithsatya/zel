#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  printf 'Usage: %s RELEASE_ASSET_DIRECTORY [OUTPUT.iso]\n' "$0" >&2
  exit 2
fi
asset_dir=$(realpath "$1")
iso_name=nvidia-b300-ubuntu-24.04.3-r620.iso
output=${2:-"$asset_dir/$iso_name"}
checksum_file="$asset_dir/$iso_name.sha256"
mapfile -t parts < <(find "$asset_dir" -maxdepth 1 -type f -name "$iso_name.part[0-9][0-9]" -print | sort)
if [[ ${#parts[@]} -eq 0 || ! -r "$checksum_file" ]]; then
  printf 'Release ISO parts or checksum file are missing from %s\n' "$asset_dir" >&2
  exit 2
fi
if [[ -e "$output" ]]; then
  printf 'Refusing to overwrite existing file: %s\n' "$output" >&2
  exit 2
fi

output=$(realpath -m "$output")
mkdir -p "$(dirname -- "$output")"
temporary=$(mktemp "$(dirname -- "$output")/.custom-iso.XXXXXX")
trap 'rm -f "$temporary"' EXIT
cat "${parts[@]}" > "$temporary"
expected=$(awk 'NR == 1 {print $1; exit}' "$checksum_file")
printf '%s  %s\n' "$expected" "$temporary" | sha256sum --check
mv -- "$temporary" "$output"
trap - EXIT
printf 'Reassembled verified ISO: %s\n' "$output"