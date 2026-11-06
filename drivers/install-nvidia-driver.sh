#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_gpu_authorized
require_root

actual_release=$( . /etc/os-release && printf '%s' "$VERSION_ID" )
if [[ "$actual_release" != "24.04" || "$(dpkg --print-architecture)" != "amd64" ]]; then
  printf 'The pinned NVIDIA driver has only been checked here for Ubuntu 24.04 amd64.\n' >&2
  exit 2
fi

driver_package=$(gpu_config_value gpu_stack driver package)
driver_version=$(gpu_config_value gpu_stack driver apt_version)
pin_package=$(gpu_config_value gpu_stack driver pinning_package)
pin_version=$(gpu_config_value gpu_stack driver pinning_apt_version)
export DEBIAN_FRONTEND=noninteractive
apt-get update
require_repository_version "$driver_package" "$driver_version"
require_repository_version "$pin_package" "$pin_version"
apt-get install -y --no-install-recommends linux-headers-generic "$pin_package=$pin_version" "$driver_package=$driver_version"
printf 'Driver packages installed. No reboot was initiated; arrange one only in an approved maintenance window.\n'