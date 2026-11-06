#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
versions_file="$repo_root/config/versions.yml"
version=$(python3 - "$versions_file" <<'PY'
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as source:
    print(yaml.safe_load(source)["ubuntu"]["version"])
PY
)
expected_sha=$(python3 - "$versions_file" <<'PY'
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as source:
    print(yaml.safe_load(source)["ubuntu"]["iso_sha256"])
PY
)

iso_name="ubuntu-${version}-live-server-amd64.iso"
base_url="https://releases.ubuntu.com/${version}"
output_dir=${OUTPUT_DIR:-"$repo_root/artifacts/nvidia-b300-pxe-ubuntu-${version}"}
temporary_dir=$(mktemp -d)
trap 'rm -rf "$temporary_dir"' EXIT

command -v curl >/dev/null 2>&1 || { printf 'curl is required.\n' >&2; exit 2; }
command -v gpgv >/dev/null 2>&1 || { printf 'gpgv is required.\n' >&2; exit 2; }
command -v sha256sum >/dev/null 2>&1 || { printf 'sha256sum is required.\n' >&2; exit 2; }
command -v bsdtar >/dev/null 2>&1 || { printf 'bsdtar is required.\n' >&2; exit 2; }
command -v tar >/dev/null 2>&1 || { printf 'tar is required.\n' >&2; exit 2; }
command -v gzip >/dev/null 2>&1 || { printf 'gzip is required.\n' >&2; exit 2; }

keyring=${UBUNTU_ARCHIVE_KEYRING:-/usr/share/keyrings/ubuntu-archive-keyring.gpg}
if [[ ! -r "$keyring" ]]; then
  printf 'Ubuntu archive keyring not found: %s\n' "$keyring" >&2
  exit 2
fi

curl --fail --location --silent --show-error "$base_url/SHA256SUMS" --output "$temporary_dir/SHA256SUMS"
curl --fail --location --silent --show-error "$base_url/SHA256SUMS.gpg" --output "$temporary_dir/SHA256SUMS.gpg"
gpgv --keyring "$keyring" "$temporary_dir/SHA256SUMS.gpg" "$temporary_dir/SHA256SUMS"
signed_sha=$(awk -v name="$iso_name" '$2 == "*" name || $2 == name {print $1; exit}' "$temporary_dir/SHA256SUMS")
if [[ "$signed_sha" != "$expected_sha" ]]; then
  printf 'Signed Ubuntu checksum does not match config/versions.yml.\n' >&2
  exit 1
fi

iso_path=${UBUNTU_ISO:-"$temporary_dir/$iso_name"}
if [[ -z "${UBUNTU_ISO:-}" ]]; then
  curl --fail --location --retry 3 --progress-bar "$base_url/$iso_name" --output "$iso_path"
fi
printf '%s  %s\n' "$expected_sha" "$iso_path" | sha256sum --check

media_dir="$temporary_dir/media"
mkdir -p "$media_dir"
cp -- "$iso_path" "$media_dir/$iso_name"
bsdtar -xOf "$iso_path" casper/vmlinuz > "$media_dir/vmlinuz"
bsdtar -xOf "$iso_path" casper/initrd > "$media_dir/initrd"

python3 "$repo_root/scripts/prepare_pxe.py" \
  --template \
  --media-dir "$media_dir" \
  --output "$output_dir"
(cd "$output_dir" && sha256sum --check SHA256SUMS)

archive="$repo_root/artifacts/nvidia-b300-pxe-ubuntu-${version}.tar.gz"
mkdir -p "$(dirname -- "$archive")"
tar --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner -C "$(dirname -- "$output_dir")" -cf - "$(basename -- "$output_dir")" | gzip -n > "$archive"
sha256sum "$archive" > "$archive.sha256"
printf 'PXE deployment payload: %s\nArchive: %s\nChecksum: %s.sha256\n' "$output_dir" "$archive" "$archive"