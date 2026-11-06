#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'Usage: %s CUSTOM.iso\n' "$0" >&2
  exit 2
fi
iso=$(realpath "$1")
code=${OVMF_CODE:-/usr/share/OVMF/OVMF_CODE_4M.fd}
vars=${OVMF_VARS:-/usr/share/OVMF/OVMF_VARS_4M.fd}
duration=${BOOT_SMOKE_TIMEOUT:-45}
command -v qemu-system-x86_64 >/dev/null 2>&1 || { printf 'qemu-system-x86_64 is required.\n' >&2; exit 2; }
command -v timeout >/dev/null 2>&1 || { printf 'timeout is required.\n' >&2; exit 2; }
command -v grep >/dev/null 2>&1 || { printf 'grep is required.\n' >&2; exit 2; }
[[ -r "$iso" ]] || { printf 'ISO is not readable: %s\n' "$iso" >&2; exit 2; }
[[ -r "$code" && -r "$vars" ]] || { printf 'OVMF UEFI firmware files are required.\n' >&2; exit 2; }

temporary_dir=$(mktemp -d)
trap 'rm -rf "$temporary_dir"' EXIT
cp -- "$vars" "$temporary_dir/OVMF_VARS.fd"
status=0
timeout --signal=TERM --kill-after=5 "$duration" \
  qemu-system-x86_64 \
    -machine q35 -accel tcg -m 4096 -smp 2 \
    -drive "if=pflash,format=raw,unit=0,readonly=on,file=$code" \
    -drive "if=pflash,format=raw,unit=1,file=$temporary_dir/OVMF_VARS.fd" \
    -cdrom "$iso" -boot order=d \
    -netdev user,id=net0 -device e1000,netdev=net0 \
    -display none -serial null -serial "file:$temporary_dir/serial.log" \
    -monitor none -no-reboot 2>"$temporary_dir/qemu.log" || status=$?

if [[ $status -ne 124 && $status -ne 0 ]]; then
  cat "$temporary_dir/qemu.log" >&2
  printf 'QEMU failed with exit status %s.\n' "$status" >&2
  exit "$status"
fi
grep -F 'Linux version' "$temporary_dir/serial.log" >/dev/null || {
  cat "$temporary_dir/qemu.log" >&2
  printf 'Custom ISO did not boot its Linux kernel under UEFI.\n' >&2
  exit 1
}
grep -F 'autoinstall ds=nocloud;s=/cdrom/autoinstall/' "$temporary_dir/serial.log" >/dev/null || {
  printf 'Expected local Autoinstall NoCloud arguments were not observed.\n' >&2
  exit 1
}
if grep -Fq "can't find command 'grub_platform'" "$temporary_dir/serial.log"; then
  printf 'Custom GRUB configuration emitted a boot error.\n' >&2
  exit 1
fi
printf 'PASS: UEFI ISO booted Ubuntu and passed local Autoinstall arguments. No disk was attached.\n'