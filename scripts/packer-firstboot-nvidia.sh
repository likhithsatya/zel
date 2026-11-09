#!/usr/bin/env bash
set -euo pipefail

payload=/opt/nvidia-b300-qemu/payload
state_dir=/var/lib/nvidia-b300-qemu
install -d -m 0755 "$state_dir"
exec > >(tee -a /var/log/nvidia-b300-firstboot-install.log) 2>&1

if [[ -f "$state_dir/gpu-stack-installed" ]]; then
  printf 'Pinned NVIDIA stack already installed; skipping.\n'
  exit 0
fi

"$payload/drivers/install-custom-image-stack.sh"
touch "$state_dir/gpu-stack-installed"
systemctl disable nvidia-b300-firstboot.service
printf 'First-boot NVIDIA candidate install completed. GPU validation remains hardware-specific.\n'