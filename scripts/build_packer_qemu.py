#!/usr/bin/env python3
"""Build a separate Packer/QEMU preinstalled qcow2 image for VM/cloud testing."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "packer/ubuntu-qemu-b300"
IMAGE_NAME = "nvidia-b300-ubuntu-24.04.3-r620.qcow2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def password_hash(password: str) -> str:
    return subprocess.run(
        ["openssl", "passwd", "-6", "-stdin"],
        input=password + "\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def prepare_context(context: Path) -> Path:
    config = yaml.safe_load((ROOT / "config/versions.yml").read_text(encoding="utf-8"))
    payload = context / "payload"
    (payload / "config").mkdir(parents=True)
    (payload / "drivers").mkdir()
    (payload / "scripts").mkdir()
    shutil.copy2(ROOT / "config/packages.yml", payload / "config/packages.yml")
    config["gpu_stack"]["enabled"] = True
    config["gpu_stack"]["installation_authorized"] = True
    (payload / "config/versions.yml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )
    for name in (
        "common.sh",
        "setup-nvidia-repo.sh",
        "install-nvidia-driver.sh",
        "install-fabric-manager.sh",
        "install-cuda.sh",
        "install-custom-image-stack.sh",
    ):
        shutil.copy2(ROOT / "drivers" / name, payload / "drivers" / name)
    for name in (
        "validate-os.sh",
        "motd-digipowerx.sh",
        "packer-provision-qemu.sh",
        "packer-cleanup-qemu.sh",
        "packer-firstboot-nvidia.sh",
    ):
        shutil.copy2(ROOT / "scripts" / name, payload / "scripts" / name)
    return payload


def run(command: list[str], cwd: Path, environment: dict[str, str]) -> None:
    print("+ " + " ".join(command[:3]))
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def build(
    source_image: Path | None,
    output_dir: Path,
    cpus: int,
    memory_mb: int,
    accelerator: str,
    validate_only: bool = False,
) -> Path | None:
    packer = shutil.which(os.environ.get("PACKER_BIN", "packer"))
    if not packer:
        raise ValueError("Packer is required; install it using HashiCorp's official installation instructions")
    for tool in ("qemu-system-x86_64", "qemu-img", "openssl"):
        if shutil.which(tool) is None:
            raise ValueError(f"required build tool not found: {tool}")

    versions = yaml.safe_load((ROOT / "config/versions.yml").read_text(encoding="utf-8"))
    ubuntu_version = versions["ubuntu"]["version"]
    cloud_base = versions["ubuntu"]["packer_qemu_base"]
    expected_source_sha = cloud_base["sha256"]
    source_url = cloud_base["url"]
    if source_image is not None:
        if not source_image.is_file():
            raise ValueError(f"Ubuntu cloud image not found: {source_image}")
        actual_source_sha = sha256(source_image)
        if actual_source_sha != expected_source_sha:
            raise ValueError(f"cloud image checksum mismatch: expected {expected_source_sha}, found {actual_source_sha}")
        source_url = source_image.resolve().as_uri()

    code = Path(os.environ.get("OVMF_CODE", "/usr/share/OVMF/OVMF_CODE_4M.fd"))
    variables = Path(os.environ.get("OVMF_VARS", "/usr/share/OVMF/OVMF_VARS_4M.fd"))
    if not code.is_file() or not variables.is_file():
        raise ValueError("OVMF UEFI files are required; set OVMF_CODE and OVMF_VARS to their local paths")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_image = output_dir / IMAGE_NAME
    if not validate_only and output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty output directory: {output_dir}")

    accelerator = accelerator or ("kvm" if os.access("/dev/kvm", os.R_OK | os.W_OK) else "tcg")
    build_password = secrets.token_urlsafe(32)
    build_password_digest = password_hash(build_password)
    with tempfile.TemporaryDirectory(prefix="b300-packer-build-") as temp_name:
        context = Path(temp_name)
        packer_output = context / "output"
        payload = prepare_context(context)
        variables_copy = context / "OVMF_VARS.fd"
        shutil.copy2(variables, variables_copy)
        environment = os.environ.copy()
        environment.update({
            "PKR_VAR_base_image_url": source_url,
            "PKR_VAR_base_image_checksum": f"sha256:{expected_source_sha}",
            "PKR_VAR_payload_directory": str(payload),
            "PKR_VAR_output_directory": str(packer_output),
            "PKR_VAR_build_password": build_password,
            "PKR_VAR_build_password_hash": build_password_digest,
            "PKR_VAR_cpus": str(cpus),
            "PKR_VAR_memory_mb": str(memory_mb),
            "PKR_VAR_accelerator": accelerator,
            "PKR_VAR_efi_firmware_code": str(code),
            "PKR_VAR_efi_firmware_vars": str(variables_copy),
        })
        run([packer, "init", "."], TEMPLATE_DIR, environment)
        run([packer, "fmt", "-check", "."], TEMPLATE_DIR, environment)
        run([packer, "validate", "."], TEMPLATE_DIR, environment)
        if validate_only:
            return None
        run([packer, "build", "."], TEMPLATE_DIR, environment)
        built_image = packer_output / IMAGE_NAME
        if not built_image.is_file():
            candidates = sorted(packer_output.glob("*.qcow2"))
            if len(candidates) != 1:
                raise ValueError(f"expected one qcow2 image in {packer_output}, found {len(candidates)}")
            built_image = candidates[0]
        subprocess.run(["qemu-img", "check", "-f", "qcow2", str(built_image)], check=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_image = output_dir / built_image.name
        if output_image.exists():
            raise ValueError(f"refusing to overwrite existing image: {output_image}")
        shutil.move(str(built_image), str(output_image))

    image_sha = sha256(output_image)
    (output_dir / f"{output_image.name}.sha256").write_text(
        f"{image_sha}  {output_image.name}\n", encoding="utf-8"
    )
    (output_dir / f"{output_image.name}.manifest.json").write_text(
        json.dumps({
            "image": output_image.name,
            "format": "qcow2",
            "ubuntu_version": ubuntu_version,
            "source_cloud_image_sha256": expected_source_sha,
            "image_sha256": image_sha,
            "gpu_stack": {
                "driver": versions["gpu_stack"]["driver"]["version"],
                "cuda": versions["gpu_stack"]["cuda"]["version"],
                "fabric_manager": versions["gpu_stack"]["fabric_manager"]["version"],
            },
            "hardware_validation": "not_performed",
            "first_boot_user_data_required": True,
            "first_boot_stack_installation": "not_tested",
            "packer_build_password_embedded": False,
            "packer_build_account": "password-cleared-and-locked; sudo-membership-removed",
            "gpu_stack_installation_mode": "first_boot_systemd_unit",
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_image


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-image", type=Path, help="verified local Ubuntu cloud disk; defaults to the pinned official URL")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/packer-qemu-b300")
    parser.add_argument("--cpus", type=int, default=2)
    parser.add_argument("--memory-mb", type=int, default=4096)
    parser.add_argument("--accelerator", choices=("auto", "kvm", "tcg"), default="auto")
    parser.add_argument("--validate-only", action="store_true", help="initialize and validate Packer template without building the qcow2")
    args = parser.parse_args()
    try:
        image = build(
            args.source_image.resolve() if args.source_image else None,
            args.output_dir.resolve(),
            args.cpus,
            args.memory_mb,
            "" if args.accelerator == "auto" else args.accelerator,
            args.validate_only,
        )
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, yaml.YAMLError) as error:
        parser.error(str(error))
    if image is None:
        print("Packer template and temporary seed validated; no image was built.")
    else:
        print(f"Preinstalled QEMU image built: {image}")