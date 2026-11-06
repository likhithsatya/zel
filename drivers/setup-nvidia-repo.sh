#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_gpu_authorized
require_root

actual_release=$( . /etc/os-release && printf '%s' "$VERSION_ID" )
if [[ "$actual_release" != "24.04" || "$(dpkg --print-architecture)" != "amd64" ]]; then
  printf 'The pinned CUDA repository is only configured here for Ubuntu 24.04 amd64.\n' >&2
  exit 2
fi

repository=$(gpu_config_value gpu_stack repository url)
keyring_version=$(gpu_config_value gpu_stack repository keyring_version)
expected_sha=$(gpu_config_value gpu_stack repository keyring_sha256)
package="cuda-keyring_${keyring_version}_all.deb"
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
curl --fail --location --silent --show-error "$repository/$package" --output "$tmpdir/$package"
printf '%s  %s\n' "$expected_sha" "$tmpdir/$package" | sha256sum --check --status || {
  printf 'CUDA repository keyring checksum mismatch.\n' >&2
  exit 1
}
dpkg -i "$tmpdir/$package"
apt-get update