#!/usr/bin/env bash
set -euo pipefail

expected_release=${EXPECTED_UBUNTU_RELEASE:-24.04}
actual_release=$( . /etc/os-release && printf '%s' "$VERSION_ID" )
if [[ "$actual_release" != "$expected_release" ]]; then
  printf 'FAIL: expected Ubuntu %s, found %s\n' "$expected_release" "$actual_release" >&2
  exit 1
fi
kernel_release=$(uname -r)
if [[ -n "${EXPECTED_KERNEL_RELEASE:-}" && "$kernel_release" != "$EXPECTED_KERNEL_RELEASE" ]]; then
  printf 'FAIL: expected kernel %s, found %s\n' "$EXPECTED_KERNEL_RELEASE" "$kernel_release" >&2
  exit 1
fi
printf 'PASS: Ubuntu %s; kernel %s\n' "$actual_release" "$kernel_release"

if ! systemctl is-active --quiet ssh; then
  printf 'FAIL: SSH service is not active.\n' >&2
  exit 1
fi
printf 'PASS: SSH service is active.\n'

if [[ -d /var/log/installer ]]; then
  printf 'PASS: installer logs are present at /var/log/installer.\n'
else
  printf 'WARN: /var/log/installer was not found.\n'
fi

if [[ -n "${CONNECTIVITY_URL:-}" ]]; then
  curl --fail --silent --show-error --max-time 10 "$CONNECTIVITY_URL" >/dev/null
  printf 'PASS: connectivity check to %s\n' "$CONNECTIVITY_URL"
else
  printf 'SKIP: set CONNECTIVITY_URL to an operator-approved network endpoint.\n'
fi