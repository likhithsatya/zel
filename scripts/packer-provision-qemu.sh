#!/usr/bin/env bash
set -euo pipefail

staged=/tmp/nvidia-b300-pxe
if [[ ! -d "$staged/config" && -d "$staged/payload/config" ]]; then
  staged="$staged/payload"
fi
payload=/opt/nvidia-b300-qemu/payload
install -d -m 0755 "$payload"
cp -a "$staged"/. "$payload"/
chmod 0755 "$payload"/drivers/*.sh "$payload"/scripts/*.sh

mapfile -t base_packages < <(python3 - "$payload/config/packages.yml" <<'PY'
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as source:
  packages = yaml.safe_load(source)["base_packages"]
print("\n".join(package for package in packages if package != "openssh-server"))
PY
)
export DEBIAN_FRONTEND=noninteractive
apt-mark hold openssh-server openssh-client
apt-get update
apt-get install -y --no-install-recommends --no-upgrade "${base_packages[@]}"

bash "$payload/scripts/validate-os.sh"

install -d -m 0755 /var/lib/nvidia-b300-qemu
cat >/etc/systemd/system/nvidia-b300-firstboot.service <<'EOF'
[Unit]
Description=Install pinned NVIDIA stack on first boot
Wants=network-online.target
After=network-online.target
ConditionPathExists=!/var/lib/nvidia-b300-qemu/gpu-stack-installed

[Service]
Type=oneshot
ExecStart=/opt/nvidia-b300-qemu/payload/scripts/packer-firstboot-nvidia.sh
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
EOF
systemctl enable nvidia-b300-firstboot.service
printf 'Packer base image provisioned; NVIDIA stack is scheduled for first boot.\n'