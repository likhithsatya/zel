#!/usr/bin/env python3
"""Write a deterministic JSON manifest and SHA256SUMS for a deployment bundle."""

import argparse
import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(bundle: Path, artifact_version: str | None = None) -> None:
    with (ROOT / "config/versions.yml").open(encoding="utf-8") as source:
        versions = yaml.safe_load(source)
    files = sorted(
        path for path in bundle.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "SHA256SUMS"}
    )
    manifest = {
        "artifact_version": artifact_version or versions["artifact_version"],
        "ubuntu_version": versions["ubuntu"]["version"],
        "gpu_stack_enabled": versions["gpu_stack"]["enabled"],
        "gpu_stack": {
            "validation_status": versions["gpu_stack"]["validation_status"],
            "hardware_validation": versions["gpu_stack"]["hardware_validation"],
            "driver": {
                "version": versions["gpu_stack"]["driver"]["version"],
                "apt_version": versions["gpu_stack"]["driver"]["apt_version"],
            },
            "cuda": {
                "version": versions["gpu_stack"]["cuda"]["version"],
                "apt_version": versions["gpu_stack"]["cuda"]["apt_version"],
            },
            "fabric_manager": {
                "version": versions["gpu_stack"]["fabric_manager"]["version"],
                "apt_version": versions["gpu_stack"]["fabric_manager"]["apt_version"],
            },
        },
        "files": {path.relative_to(bundle).as_posix(): sha256(path) for path in files},
    }
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    checksum_files = sorted(path for path in bundle.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (bundle / "SHA256SUMS").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(bundle).as_posix()}\n" for path in checksum_files),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--artifact-version")
    args = parser.parse_args()
    write_manifest(args.bundle.resolve(), args.artifact_version)