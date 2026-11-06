#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
"$script_dir/setup-nvidia-repo.sh"
"$script_dir/install-nvidia-driver.sh"
"$script_dir/install-fabric-manager.sh"
"$script_dir/install-cuda.sh"
printf 'NVIDIA candidate stack installed. Hardware functionality still requires B300 validation.\n'