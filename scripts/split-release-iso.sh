#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  printf 'Usage: %s CUSTOM.iso RELEASE_ASSET_DIRECTORY\n' "$0" >&2
  exit 2
fi
iso=$(realpath "$1")
output_dir=$(realpath -m "$2")
iso_name=$(basename -- "$iso")
checksum_file="${iso}.sha256"
manifest_file="${iso}.manifest.json"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ! -r "$iso" || ! -r "$checksum_file" || ! -r "$manifest_file" ]]; then
  printf 'ISO, checksum, and manifest files are all required.\n' >&2
  exit 2
fi
(cd "$(dirname -- "$iso")" && sha256sum --check "$(basename -- "$checksum_file")")
mkdir -p "$output_dir"
split --bytes=1800M --numeric-suffixes=1 --suffix-length=2 "$iso" "$output_dir/$iso_name.part"
cp -- "$checksum_file" "$manifest_file" "$output_dir/"
cp -- "$script_dir/assemble-release-iso.sh" "$output_dir/"

printf 'This release contains split ISO parts because GitHub limits each release asset to under 2 GiB.\n\n' > "$output_dir/REASSEMBLE.txt"
printf 'After downloading all files into one directory, run:\n\n' >> "$output_dir/REASSEMBLE.txt"
printf '  bash assemble-release-iso.sh .\n\n' >> "$output_dir/REASSEMBLE.txt"
printf 'The script joins the numbered parts and verifies the ISO SHA256.\n' >> "$output_dir/REASSEMBLE.txt"
if find "$output_dir" -maxdepth 1 -type f -name "$iso_name.part*" -printf '%s\n' | awk '$1 >= 2147483648 {exit 1}'; then
  printf 'Release assets prepared in %s\n' "$output_dir"
else
  printf 'A release part exceeds GitHub\047s 2 GiB asset limit.\n' >&2
  exit 1
fi