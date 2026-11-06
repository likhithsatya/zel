#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_gpu_authorized
require_root

driver_package=$(gpu_config_value gpu_stack driver package)
driver_version=$(gpu_config_value gpu_stack driver apt_version)
fm_package=$(gpu_config_value gpu_stack fabric_manager package)
fm_version=$(gpu_config_value gpu_stack fabric_manager apt_version)
fm_direct_package=$(gpu_config_value gpu_stack fabric_manager direct_package)
fm_direct_version=$(gpu_config_value gpu_stack fabric_manager direct_version)
fm_driver_library=$(gpu_config_value gpu_stack fabric_manager driver_library_package)
fm_driver_library_version=$(gpu_config_value gpu_stack fabric_manager driver_library_version)
require_installed_version "$driver_package" "$driver_version"
export DEBIAN_FRONTEND=noninteractive
apt-get update
require_repository_version "$fm_package" "$fm_version"
require_repository_version "$fm_direct_package" "$fm_direct_version"
require_repository_version "$fm_driver_library" "$fm_driver_library_version"
apt-get install -y --no-install-recommends "$fm_driver_library=$fm_driver_library_version" "$fm_package=$fm_version"
apt-mark hold "$fm_package" "$fm_direct_package" "$fm_driver_library"