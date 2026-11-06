#!/usr/bin/env python3
"""Validate the safe, non-GPU baseline configuration."""

from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        value = yaml.safe_load(source)
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a YAML mapping")
    return value


def validate() -> None:
    versions = load_yaml(ROOT / "config/versions.yml")
    packages = load_yaml(ROOT / "config/packages.yml")
    hardware = load_yaml(ROOT / "config/hardware.yml")
    deployment = load_yaml(ROOT / "config/deployment.yml")

    if versions.get("ubuntu", {}).get("version") != "24.04.3":
        raise ValueError("Ubuntu version must remain pinned to the POC's 24.04.3")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(versions.get("artifact_version", ""))):
        raise ValueError("artifact_version must use MAJOR.MINOR.PATCH")
    gpu_stack = versions.get("gpu_stack", {})
    if not isinstance(gpu_stack.get("enabled"), bool):
        raise ValueError("gpu_stack.enabled must be an explicit boolean")
    if not isinstance(gpu_stack.get("installation_authorized"), bool):
        raise ValueError("gpu_stack.installation_authorized must be an explicit boolean")
    if gpu_stack.get("enabled") and not gpu_stack.get("installation_authorized"):
        raise ValueError("GPU software installation requires explicit operator authorization")
    candidates = {
        "driver": ("nvidia-open", "620.70.06", "620.70.06-1ubuntu1"),
        "cuda": ("cuda-toolkit-13-5", "13.5", "13.5.0-1"),
        "fabric_manager": ("nvidia-fabricmanager", "2.0.0.rel106", "620-1"),
    }
    for component, (package, version, apt_version) in candidates.items():
        entry = gpu_stack.get(component, {})
        if (entry.get("package"), entry.get("version"), entry.get("apt_version")) != (package, version, apt_version):
            raise ValueError(f"{component} candidate does not match the reviewed NVIDIA package matrix")
    driver = gpu_stack["driver"]
    if (driver.get("pinning_package"), driver.get("pinning_apt_version")) != (
        "nvidia-driver-pinning-620.70.06",
        "620.70.06-1ubuntu1",
    ):
        raise ValueError("NVIDIA driver pinning package must match the candidate release")
    fabric_manager = gpu_stack["fabric_manager"]
    if (fabric_manager.get("direct_package"), fabric_manager.get("direct_version")) != (
        "nvidia-fabricmanager-direct",
        "2.0.0.rel106-1",
    ):
        raise ValueError("Fabric Manager's direct package version must match the reviewed package")
    if (fabric_manager.get("driver_library_package"), fabric_manager.get("driver_library_version")) != (
        "libnvidia-fmdrv1",
        "620.70.06-1ubuntu1",
    ) or fabric_manager.get("driver_library_version") != driver.get("apt_version"):
        raise ValueError("Fabric Manager's driver interface library must match the pinned NVIDIA driver")
    if gpu_stack.get("fabric_manager", {}).get("required") is not True:
        raise ValueError("Fabric Manager must be required for the HGX B300 NVSwitch validation path")
    if gpu_stack.get("hardware_validation") != "not_performed" or gpu_stack.get("oem_qualification") != "pending":
        raise ValueError("Do not claim Supermicro hardware qualification or physical validation in configuration")
    if gpu_stack.get("repository", {}).get("keyring_sha256") != "d2a6b11c096396d868758b86dab1823b25e14d70333f1dfa74da5ddaf6a06dba":
        raise ValueError("CUDA repository keyring checksum differs from the reviewed NVIDIA package")

    names = packages.get("base_packages")
    if not isinstance(names, list) or not names:
        raise ValueError("base_packages must be a non-empty list")
    if len(names) != len(set(names)) or any(not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", str(name)) for name in names):
        raise ValueError("base_packages contains a duplicate or invalid package name")
    if hardware.get("installation", {}).get("network") != "dhcp":
        raise ValueError("network provisioning must follow the POC's DHCP-based flow")
    network = deployment.get("network", {})
    if network.get("prohibit_local_dhcp_server") is not True or network.get("pxe_base_url") is not None:
        raise ValueError("site network endpoints must remain operator-supplied; do not add a DHCP server")
    if network.get("seed_url") != "${tenant-cloudinit-url}":
        raise ValueError("the NICo seed URL must preserve the documented tenant-cloudinit-url handoff")
    if deployment.get("provisioning", {}).get("destructive_actions_automated") is not False:
        raise ValueError("physical provisioning actions must remain operator-controlled")

    for path in (ROOT / ".github/workflows").glob("*.yml"):
        with path.open(encoding="utf-8") as source:
            yaml.safe_load(source)

    user_data = (ROOT / "autoinstall/user-data").read_text(encoding="utf-8")
    autoinstall = yaml.safe_load(user_data.removeprefix("#cloud-config\n")).get("autoinstall", {})
    if autoinstall.get("version") != 1:
        raise ValueError("Autoinstall version must be 1")
    if autoinstall.get("identity", {}).get("password") != "!":
        raise ValueError("Autoinstall identity must remain password-locked")
    if autoinstall.get("ssh", {}).get("allow-pw") is not False:
        raise ValueError("SSH password authentication must remain disabled")
    if autoinstall.get("network", {}).get("ethernets", {}).get("pxe", {}).get("dhcp4") is not True:
        raise ValueError("The selected PXE interface must use DHCP")
    if autoinstall.get("storage", {}).get("layout", {}).get("name") != "direct":
        raise ValueError("Disk layout must preserve the POC's direct layout")
    if not autoinstall.get("storage", {}).get("layout", {}).get("match", {}).get("serial"):
        raise ValueError("Autoinstall must require an explicit target disk serial")
    if not autoinstall.get("network", {}).get("ethernets", {}).get("pxe", {}).get("match", {}).get("macaddress"):
        raise ValueError("Autoinstall must require an explicit PXE NIC MAC")
    with (ROOT / "autoinstall/meta-data").open(encoding="utf-8") as source:
        yaml.safe_load(source)


if __name__ == "__main__":
    validate()
    print("Configuration valid; NVIDIA candidate versions are pinned and installation gates are enforced.")