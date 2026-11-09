#!/usr/bin/env bash
set -u

os_name=$(. /etc/os-release && printf '%s' "${PRETTY_NAME:-Ubuntu}")
kernel=$(uname -r 2>/dev/null || printf 'unknown')
uptime=$(uptime -p 2>/dev/null | sed 's/^up //' || printf 'unknown')
cpu_count=$(nproc 2>/dev/null || printf 'unknown')
memory=$(awk '/MemTotal:/ {printf "%.1f GiB", $2 / 1048576}' /proc/meminfo 2>/dev/null)
disk=$(df -hP / 2>/dev/null | awk 'NR == 2 {printf "%s total, %s free", $2, $4}')
ip_address=$(hostname -I 2>/dev/null | awk '{print $1}')
gpu_status='Not detected (VM or driver unavailable)'

if command -v nvidia-smi >/dev/null 2>&1; then
  gpu_list=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || true)
  if [[ -n "$gpu_list" ]]; then
    gpu_count=$(printf '%s\n' "$gpu_list" | awk 'NF {count++} END {print count+0}')
    driver_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
    gpu_status="$gpu_count GPU(s), driver ${driver_version:-unknown}"
  fi
fi

printf '\n'
printf '+-----------------------------------------------------------+\n'
printf '|                    DIGIPOWERX COMPUTE NODE                |\n'
printf '|                HGX B300 Ubuntu Image V1                   |\n'
printf '+-----------------------------------------------------------+\n'
printf '\n'
printf '  OS:       %s\n' "$os_name"
printf '  Kernel:   %s\n' "$kernel"
printf '  Uptime:   %s\n' "${uptime:-unknown}"
printf '  CPUs:     %s\n' "$cpu_count"
printf '  Memory:   %s\n' "${memory:-unknown}"
printf '  Root disk:%s\n' " ${disk:-unknown}"
printf '  Address:  %s\n' "${ip_address:-unknown}"
printf '  NVIDIA:   %s\n' "$gpu_status"
printf '\n'