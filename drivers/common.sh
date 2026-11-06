#!/usr/bin/env bash
set -euo pipefail

DRIVERS_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$DRIVERS_DIR/.." && pwd)
VERSIONS_FILE="$REPO_ROOT/config/versions.yml"

gpu_config_value() {
  python3 - "$VERSIONS_FILE" "$@" <<'PY'
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as source:
    value = yaml.safe_load(source)
for key in sys.argv[2:]:
    value = value[key]
print(str(value).lower() if isinstance(value, bool) else value)
PY
}

require_gpu_authorized() {
  if [[ "$(gpu_config_value gpu_stack enabled)" != "true" || "$(gpu_config_value gpu_stack installation_authorized)" != "true" ]]; then
    printf 'GPU installation is disabled. Qualify the exact platform and explicitly authorize it in config/versions.yml first.\n' >&2
    return 2
  fi
}

require_root() {
  if [[ $EUID -ne 0 ]]; then
    printf 'Run this installer as root.\n' >&2
    return 2
  fi
}

require_repository_version() {
  local package=$1
  local version=$2
  if ! apt-cache madison "$package" | awk -F'|' -v expected="$version" '{gsub(/[[:space:]]/, "", $2); if ($2 == expected) found=1} END {exit !found}'; then
    printf 'Pinned package unavailable: %s=%s. Configure the approved NVIDIA Ubuntu repository first.\n' "$package" "$version" >&2
    return 2
  fi
}

require_installed_version() {
  local package=$1
  local expected=$2
  local actual
  actual=$(dpkg-query -W -f='${Version}' "$package" 2>/dev/null || true)
  if [[ "$actual" != "$expected" ]]; then
    printf 'Required package version not installed: %s=%s (found %s).\n' "$package" "$expected" "${actual:-absent}" >&2
    return 2
  fi
}