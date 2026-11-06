#!/usr/bin/env python3
"""Build a bootable Ubuntu installer ISO that installs the pinned B300 software candidate."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = "/autoinstall"
PAYLOAD_PATH = "/nvidia-b300"
BOOT_ARGS = (
    "ip=dhcp BOOTIF=01-90-5a-08-c1-92-62 fb=false autoinstall "
    r"ds=nocloud\;s=/cdrom/autoinstall/ "
    "console=tty0 console=ttyS1,115200"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def random_password_hash() -> str:
    password = secrets.token_urlsafe(48)
    result = subprocess.run(
        ["openssl", "passwd", "-6", "-stdin"],
        input=password + "\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not result.startswith("$6$"):
        raise ValueError("OpenSSL did not return a SHA-512 password hash")
    return result


def prepare_overlay(overlay: Path, password_hash: str) -> None:
    versions_path = ROOT / "config/versions.yml"
    packages_path = ROOT / "config/packages.yml"
    versions = yaml.safe_load(versions_path.read_text(encoding="utf-8"))
    packages = yaml.safe_load(packages_path.read_text(encoding="utf-8"))["base_packages"]
    versions["gpu_stack"]["enabled"] = True
    versions["gpu_stack"]["installation_authorized"] = True

    seed = yaml.safe_load((ROOT / "autoinstall/custom-user-data").read_text(encoding="utf-8"))
    seed["autoinstall"]["identity"]["password"] = password_hash
    seed["autoinstall"]["packages"] = packages

    autoinstall_dir = overlay / "autoinstall"
    payload_dir = overlay / "nvidia-b300"
    autoinstall_dir.mkdir(parents=True)
    (autoinstall_dir / "user-data").write_text(
        "#cloud-config\n" + yaml.safe_dump(seed, sort_keys=False), encoding="utf-8"
    )
    (autoinstall_dir / "meta-data").write_text(
        "instance-id: nvidia-b300-ubuntu-24.04.3\nlocal-hostname: b300-01\n", encoding="utf-8"
    )

    (payload_dir / "config").mkdir(parents=True)
    (payload_dir / "drivers").mkdir()
    (payload_dir / "scripts").mkdir()
    (payload_dir / "config/versions.yml").write_text(
        yaml.safe_dump(versions, sort_keys=False), encoding="utf-8"
    )
    for name in (
        "common.sh",
        "setup-nvidia-repo.sh",
        "install-nvidia-driver.sh",
        "install-fabric-manager.sh",
        "install-cuda.sh",
        "install-custom-image-stack.sh",
    ):
        shutil.copy2(ROOT / "drivers" / name, payload_dir / "drivers" / name)
    for name in ("validate-os.sh", "validate-gpu.sh"):
        shutil.copy2(ROOT / "scripts" / name, payload_dir / "scripts" / name)


def patch_grub_config(source: str) -> str:
    lines = [line for line in source.splitlines() if line.strip() != "grub_platform"]
    linux_entries = 0
    for index, line in enumerate(lines):
        if re.match(r"^\s*linux\s+/casper/(?:hwe-)?vmlinuz\b", line):
            if not re.search(r"\s---\s*$", line):
                raise ValueError(f"unexpected Ubuntu GRUB kernel line: {line}")
            lines[index] = re.sub(r"\s+---\s*$", f" {BOOT_ARGS} ---", line)
            linux_entries += 1
    if linux_entries == 0:
        raise ValueError("no Ubuntu Server kernel entries found in source ISO GRUB config")
    for index, line in enumerate(lines):
        if line.startswith("set timeout="):
            lines[index] = "set timeout=10"
            break
    for index, line in enumerate(lines):
        if line.startswith('menuentry "Try or Install Ubuntu Server"'):
            lines[index] = line.replace(
                'menuentry "Try or Install Ubuntu Server"',
                'menuentry "Install Ubuntu 24.04.3 with NVIDIA data-center software"',
                1,
            )
            break
    return "\n".join(lines) + "\n"


def customize_grub(source_iso: Path, destination: Path) -> None:
    result = subprocess.run(
        ["bsdtar", "-xOf", str(source_iso), "boot/grub/grub.cfg"],
        check=True,
        capture_output=True,
        text=True,
    )
    destination.write_text(patch_grub_config(result.stdout), encoding="utf-8")


def build(source_iso: Path, output_iso: Path) -> None:
    if not source_iso.is_file():
        raise ValueError(f"Ubuntu source ISO not found: {source_iso}")
    expected_sha = yaml.safe_load((ROOT / "config/versions.yml").read_text(encoding="utf-8"))["ubuntu"]["iso_sha256"]
    source_sha = sha256(source_iso)
    if source_sha != expected_sha:
        raise ValueError(f"source ISO checksum mismatch: expected {expected_sha}, found {source_sha}")
    for tool in ("xorriso", "bsdtar", "openssl"):
        if shutil.which(tool) is None:
            raise ValueError(f"required image build tool not found: {tool}")

    output_iso.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nvidia-b300-iso-", dir=output_iso.parent) as temporary:
        stage = Path(temporary)
        overlay = stage / "overlay"
        overlay.mkdir()
        prepare_overlay(overlay, random_password_hash())
        grub_cfg = stage / "grub.cfg"
        customize_grub(source_iso, grub_cfg)
        temporary_iso = stage / output_iso.name
        command = [
            "xorriso",
            "-indev",
            str(source_iso.resolve()),
            "-outdev",
            str(temporary_iso),
            "-boot_image",
            "any",
            "replay",
            "-map",
            str(overlay / "autoinstall"),
            SEED_PATH,
            "-map",
            str(overlay / "nvidia-b300"),
            PAYLOAD_PATH,
            "-map",
            str(grub_cfg),
            "/boot/grub/grub.cfg",
            "-commit",
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("xorriso failed:\n" + result.stderr[-6000:])
        boot_report = subprocess.run(
            ["xorriso", "-indev", str(temporary_iso), "-report_el_torito", "plain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if "UEFI" not in boot_report.upper():
            raise ValueError("custom ISO does not report a UEFI El Torito boot image")
        check = subprocess.run(
            ["bsdtar", "-tf", str(temporary_iso)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        for required in (
            "autoinstall/user-data",
            "autoinstall/meta-data",
            "nvidia-b300/drivers/install-custom-image-stack.sh",
            "casper/vmlinuz",
            "casper/initrd",
        ):
            if required not in check:
                raise ValueError(f"custom ISO is missing {required}")
        os.replace(temporary_iso, output_iso)

    output_sha = sha256(output_iso)
    checksum_path = output_iso.with_suffix(output_iso.suffix + ".sha256")
    checksum_path.write_text(f"{output_sha}  {output_iso.name}\n", encoding="utf-8")
    versions = yaml.safe_load((ROOT / "config/versions.yml").read_text(encoding="utf-8"))
    manifest_path = output_iso.with_suffix(output_iso.suffix + ".manifest.json")
    manifest_path.write_text(
        json.dumps(
            {
                "image": output_iso.name,
                "ubuntu_version": versions["ubuntu"]["version"],
                "source_iso_sha256": source_sha,
                "image_sha256": output_sha,
                "gpu_stack": {
                    "driver": versions["gpu_stack"]["driver"]["version"],
                    "cuda": versions["gpu_stack"]["cuda"]["version"],
                    "fabric_manager": versions["gpu_stack"]["fabric_manager"]["version"],
                },
                "hardware_validation": "not_performed",
                "interactive_sections": ["identity", "storage", "ssh"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-iso", type=Path, required=True)
    parser.add_argument("--output-iso", type=Path, required=True)
    args = parser.parse_args()
    try:
        build(args.source_iso.resolve(), args.output_iso.resolve())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, yaml.YAMLError) as error:
        parser.error(str(error))
    print(f"Custom ISO built: {args.output_iso.resolve()}")