#!/usr/bin/env bash
set -euo pipefail

if ! command -v lspci >/dev/null 2>&1 || ! lspci -nn | grep -Ei '(VGA compatible controller|3D controller).*\[10de:' >/dev/null; then
  printf 'NOT RUN: NVIDIA PCI hardware was not detected; this is not a GPU pass.\n' >&2
  exit 3
fi
printf 'PASS: NVIDIA PCI device detected on this host.\n'

if ! command -v nvidia-smi >/dev/null 2>&1; then
  printf 'FAIL: NVIDIA hardware is present but nvidia-smi is unavailable.\n' >&2
  exit 1
fi
nvidia-smi

if command -v nvcc >/dev/null 2>&1; then
  nvcc --version
else
  if [[ "${CUDA_REQUIRED:-true}" == "true" ]]; then
    printf 'FAIL: CUDA is required but nvcc is unavailable.\n' >&2
    exit 1
  fi
  printf 'NOT INSTALLED: CUDA compiler (nvcc).\n'
fi

if systemctl list-unit-files nvidia-fabricmanager.service --no-legend 2>/dev/null | grep -q nvidia-fabricmanager; then
  systemctl is-active --quiet nvidia-fabricmanager.service || {
    printf 'FAIL: Fabric Manager is installed but not active.\n' >&2
    exit 1
  }
  printf 'PASS: Fabric Manager is active.\n'
else
  if [[ "${FABRIC_MANAGER_REQUIRED:-true}" == "true" ]]; then
    printf 'FAIL: Fabric Manager is required but not installed.\n' >&2
    exit 1
  fi
  printf 'NOT INSTALLED: Fabric Manager; applicability must be confirmed for the validated platform stack.\n'
fi