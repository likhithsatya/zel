#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_gpu_authorized
require_root

driver_package=$(gpu_config_value gpu_stack driver package)
driver_version=$(gpu_config_value gpu_stack driver apt_version)
cuda_package=$(gpu_config_value gpu_stack cuda package)
cuda_version=$(gpu_config_value gpu_stack cuda apt_version)
require_installed_version "$driver_package" "$driver_version"
export DEBIAN_FRONTEND=noninteractive
apt-get update
require_repository_version "$cuda_package" "$cuda_version"
apt-get install -y --no-install-recommends "$cuda_package=$cuda_version"
apt-mark hold "$cuda_package"