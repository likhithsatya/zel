#!/usr/bin/env bash
set -euo pipefail

rm -f /etc/sudoers.d/packer
apt-mark unhold openssh-server openssh-client >/dev/null 2>&1 || true
usermod --password '!' packer || true
usermod --lock packer || true
gpasswd --delete packer sudo >/dev/null 2>&1 || true
rm -rf /home/packer/.ssh /home/packer/.bash_history
cloud-init clean --logs --seed
rm -f /etc/ssh/ssh_host_* /var/log/installer/autoinstall-user-data
truncate -s 0 /etc/machine-id
sync
systemctl poweroff