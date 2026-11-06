#!/usr/bin/env python3
"""Generate a POC-faithful UEFI HTTP/iPXE deployment bundle."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil

import yaml

from generate_manifest import sha256, write_manifest
from validate_config import ROOT, validate


TEMPLATE_MARKERS = {
    "__PXE_BASE_URL__": "PXE_BASE_URL",
    "__INSTALL_NIC_MAC__": "INSTALL_NIC_MAC",
    "__INSTALL_DISK_SERIAL__": "INSTALL_DISK_SERIAL",
    "__INSTALL_HOSTNAME__": "INSTALL_HOSTNAME",
    "__INSTALL_USERNAME__": "INSTALL_USERNAME",
    "__SSH_AUTHORIZED_KEY__": "INSTALL_SSH_PUBLIC_KEY",
}


def render_user_data(template: str, values: dict[str, str], packages: list[str]) -> str:
    replacements = {
        "__INSTALL_NIC_MAC__": values["INSTALL_NIC_MAC"],
        "__INSTALL_DISK_SERIAL__": values["INSTALL_DISK_SERIAL"],
        "__INSTALL_HOSTNAME__": values["INSTALL_HOSTNAME"],
        "__INSTALL_USERNAME__": values["INSTALL_USERNAME"],
        "__SSH_AUTHORIZED_KEY__": values["INSTALL_SSH_PUBLIC_KEY"],
        "__PACKAGES__": ", ".join(json.dumps(name) for name in packages),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, json.dumps(value))
    yaml.safe_load(template.removeprefix("#cloud-config\n"))
    return template


def deployment_values(template_mode: bool) -> dict[str, str]:
    if template_mode:
        return {key: marker for marker, key in TEMPLATE_MARKERS.items()}
    values = {key: os.environ.get(key, "").strip() for key in TEMPLATE_MARKERS.values()}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise ValueError("Missing required deployment environment values: " + ", ".join(missing))
    if not re.fullmatch(r"https?://[^\s/@]+(?::\d+)?(?:/[^\s]*)?", values["PXE_BASE_URL"]):
        raise ValueError("PXE_BASE_URL must be an HTTP(S) URL without embedded credentials")
    if not re.fullmatch(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", values["INSTALL_NIC_MAC"]):
        raise ValueError("INSTALL_NIC_MAC must be a six-octet MAC address")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,62}", values["INSTALL_HOSTNAME"]):
        raise ValueError("INSTALL_HOSTNAME is invalid")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", values["INSTALL_USERNAME"]):
        raise ValueError("INSTALL_USERNAME is invalid")
    if not re.match(r"^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp[0-9]+)\s+\S+", values["INSTALL_SSH_PUBLIC_KEY"]):
        raise ValueError("INSTALL_SSH_PUBLIC_KEY must be an SSH public key, not a private key")
    return values


def generate(
    output: Path,
    template_mode: bool,
    artifact_version: str | None = None,
    media_dir: Path | None = None,
) -> None:
    validate()
    values = deployment_values(template_mode)
    versions = yaml.safe_load((ROOT / "config/versions.yml").read_text(encoding="utf-8"))
    artifact_version = artifact_version or versions["artifact_version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", artifact_version):
        raise ValueError("artifact version must use MAJOR.MINOR.PATCH")
    packages = yaml.safe_load((ROOT / "config/packages.yml").read_text(encoding="utf-8"))["base_packages"]
    release_dir = f"ubuntu-{versions['ubuntu']['version']}"
    base_url = values["PXE_BASE_URL"].rstrip("/")

    output.mkdir(parents=True, exist_ok=True)
    (output / "seed").mkdir(exist_ok=True)
    (output / "scripts").mkdir(exist_ok=True)
    user_template = (ROOT / "autoinstall/user-data").read_text(encoding="utf-8")
    (output / "seed/user-data").write_text(render_user_data(user_template, values, packages), encoding="utf-8")

    metadata = (ROOT / "autoinstall/meta-data").read_text(encoding="utf-8")
    metadata = metadata.replace("__INSTALL_HOSTNAME__", json.dumps(values["INSTALL_HOSTNAME"]))
    (output / "seed/meta-data").write_text(metadata, encoding="utf-8")

    ipxe = "\n".join([
        "#!ipxe",
        f"kernel {base_url}/{release_dir}/vmlinuz BOOTIF=01-${{netX/mac:hexhyp}} ip=dhcp fb=false url={base_url}/{release_dir}/{release_dir}-live-server-amd64.iso autoinstall ds=nocloud-net\\;s=${{tenant-cloudinit-url}} console=tty0 console=ttyS1,115200 initrd=initrd.magicinitrd",
        f"initrd {base_url}/{release_dir}/initrd",
        "boot",
        "",
    ])
    (output / "boot.ipxe").write_text(ipxe, encoding="utf-8")

    for name in ("install-packages.sh", "validate-os.sh", "validate-gpu.sh"):
        shutil.copy2(ROOT / "scripts" / name, output / "scripts" / name)
    (output / "config").mkdir(exist_ok=True)
    (output / "config/packages.txt").write_text("".join(f"{name}\n" for name in packages), encoding="utf-8")
    shutil.copy2(ROOT / "config/versions.yml", output / "config/versions.yml")
    shutil.copy2(ROOT / "config/hardware.yml", output / "config/hardware.yml")
    for name in (
        "common.sh",
        "setup-nvidia-repo.sh",
        "install-nvidia-driver.sh",
        "install-fabric-manager.sh",
        "install-cuda.sh",
    ):
        (output / "drivers").mkdir(exist_ok=True)
        shutil.copy2(ROOT / "drivers" / name, output / "drivers" / name)

    media_note = "Ubuntu kernel/initrd/ISO assets are external and must be staged at the URLs in boot.ipxe.\n"
    if media_dir is not None:
        media_files = {
            "vmlinuz": media_dir / "vmlinuz",
            "initrd": media_dir / "initrd",
            f"{release_dir}-live-server-amd64.iso": media_dir / f"{release_dir}-live-server-amd64.iso",
        }
        for source in media_files.values():
            if not source.is_file():
                raise ValueError(f"missing Ubuntu media asset: {source}")
        iso_path = media_files[f"{release_dir}-live-server-amd64.iso"]
        digest = sha256(iso_path)
        if digest != versions["ubuntu"]["iso_sha256"]:
            raise ValueError(f"Ubuntu ISO checksum mismatch: expected {versions['ubuntu']['iso_sha256']}, found {digest}")
        target_dir = output / release_dir
        target_dir.mkdir(exist_ok=True)
        for name, source in media_files.items():
            shutil.copy2(source, target_dir / name)
        media_note = f"Verified Ubuntu {versions['ubuntu']['version']} kernel/initrd/ISO are included in {release_dir}/.\n"

    (output / "README.txt").write_text(
        "NICo HGX B300 PXE configuration bundle.\n"
        + media_note
        + "INSTALLATION IS NOT READY: render with the approved HTTP URL, PXE MAC, target disk serial, hostname, username, and SSH public key.\n"
        + "Do not register this template seed for an unattended install.\n"
        + "GPU installers are authorization-gated and have not been hardware validated.\n"
        + "Register boot.ipxe and seed/user-data through the approved NICo OS workflow.\n",
        encoding="utf-8",
    )
    write_manifest(output, artifact_version)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", action="store_true", help="keep site-specific values as explicit placeholders")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/nvidia-b300-pxe-template")
    parser.add_argument("--artifact-version", help="override the config version, normally from a release tag")
    parser.add_argument("--media-dir", type=Path, help="include verified vmlinuz, initrd, and Ubuntu ISO from this directory")
    args = parser.parse_args()
    try:
        generate(args.output.resolve(), args.template, args.artifact_version, args.media_dir.resolve() if args.media_dir else None)
    except (OSError, ValueError, KeyError, yaml.YAMLError) as error:
        parser.error(str(error))
    print(f"Bundle generated: {args.output.resolve()}")