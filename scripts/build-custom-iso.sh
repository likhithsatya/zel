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
temporary_dir=$(mktemp -d)
trap 'rm -rf "$temporary_dir"' EXIT
keyring=${UBUNTU_ARCHIVE_KEYRING:-/usr/share/keyrings/ubuntu-archive-keyring.gpg}
if [[ ! -r "$keyring" ]]; then
  printf 'Ubuntu archive keyring not found: %s\n' "$keyring" >&2
  exit 2
fi

command -v curl >/dev/null 2>&1 || { printf 'curl is required.\n' >&2; exit 2; }
command -v gpgv >/dev/null 2>&1 || { printf 'gpgv is required.\n' >&2; exit 2; }
command -v sha256sum >/dev/null 2>&1 || { printf 'sha256sum is required.\n' >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { printf 'python3 is required.\n' >&2; exit 2; }

curl --fail --location --silent --show-error "$base_url/SHA256SUMS" --output "$temporary_dir/SHA256SUMS"
curl --fail --location --silent --show-error "$base_url/SHA256SUMS.gpg" --output "$temporary_dir/SHA256SUMS.gpg"
gpgv --keyring "$keyring" "$temporary_dir/SHA256SUMS.gpg" "$temporary_dir/SHA256SUMS"
signed_sha=$(awk -v name="$iso_name" '$2 == "*" name || $2 == name {print $1; exit}' "$temporary_dir/SHA256SUMS")
if [[ "$signed_sha" != "$expected_sha" ]]; then
  printf 'Signed Ubuntu checksum does not match config/versions.yml.\n' >&2
  exit 1
fi

if [[ -n "${UBUNTU_ISO:-}" ]]; then
  source_iso=$(realpath "$UBUNTU_ISO")
else
  source_iso="$repo_root/artifacts/ubuntu-source/$iso_name"
  mkdir -p "$(dirname -- "$source_iso")"
  if [[ ! -f "$source_iso" ]]; then
    curl --fail --location --retry 3 --progress-bar "$base_url/$iso_name" --output "$source_iso"
  fi
fi
printf '%s  %s\n' "$expected_sha" "$source_iso" | sha256sum --check

output_iso=${OUTPUT_ISO:-"$repo_root/artifacts/nvidia-b300-ubuntu-${version}-r620.iso"}
python3 "$repo_root/scripts/build_custom_iso.py" --source-iso "$source_iso" --output-iso "$output_iso"