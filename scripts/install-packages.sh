#!/usr/bin/env bash
set -euo pipefail

package_file=${1:-"$(dirname "${BASH_SOURCE[0]}")/../config/packages.txt"}
if [[ ! -r "$package_file" ]]; then
  printf 'Package list is not readable: %s\n' "$package_file" >&2
  exit 2
fi
mapfile -t packages < <(sed '/^[[:space:]]*$/d; /^[[:space:]]*#/d' "$package_file")
if [[ ${#packages[@]} -eq 0 ]]; then
  printf 'Package list is empty.\n' >&2
  exit 2
fi
for package in "${packages[@]}"; do
  if [[ ! "$package" =~ ^[a-z0-9][a-z0-9+.-]*$ ]]; then
    printf 'Invalid package name: %s\n' "$package" >&2
    exit 2
  fi
done
if [[ $EUID -ne 0 ]]; then
  printf 'Run this helper as root.\n' >&2
  exit 2
fi
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${packages[@]}"