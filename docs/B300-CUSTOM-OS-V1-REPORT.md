# HGX B300 Custom Ubuntu Installer — Version 1 build, architecture, and test report

**Prepared:** 2026-11-06
**Status:** Prepared for supervised test; physical B300/GPU validation pending.

```mermaid
flowchart LR
  A[Official Ubuntu 24.04.3 ISO] --> B[Verify signature and SHA256] --> C[Remaster GRUB + local seed + NVIDIA tools] --> D[Custom UEFI/BIOS ISO] --> E[Interactive Autoinstall] --> F[Ubuntu + NVIDIA candidate stack]
  N[NICo controller] --> R[Existing VLAN 30 DHCP relay] --> I[UEFI HTTP / iPXE] --> S[Ubuntu assets + tenant-cloudinit-url seed] --> P[POC Autoinstall path]
```

The custom ISO path is distinct from the original NICo/iPXE POC path. The ISO does not register with NICo; BMC handling is operator-owned.

## Executive summary

V1 is a bootable Ubuntu Server 24.04.3 installer ISO for a supervised B300 test. It installs the NVIDIA R620 driver candidate, CUDA 13.5, and Fabric Manager during Autoinstall. The image is prepared and UEFI-boot-smoke-tested in QEMU; it has not been installed on the physical B300 and its GPU stack is not hardware-validated.

## Architecture

The report shows two distinct paths. The original POC path is NICo with UEFI HTTP/iPXE and a NICo-hosted NoCloud seed. The V1 custom ISO is booted using the operator's chosen media method and does not register with or call NICo. BMC handling is operator-owned and was not performed by this project.

## What was built

- Ubuntu 24.04.3 source ISO verified against Ubuntu's signed SHA256 manifest.
- Custom ISO remaster preserving BIOS and UEFI boot metadata, with local NoCloud seed and Autoinstall arguments.
- Interactive identity, disk/storage, and SSH setup; no disk serial or SSH key is baked into the image.
- Late-command installs the pinned candidate NVIDIA stack from Ubuntu/NVIDIA repositories; network access is required during installation.
- Build scripts, self-hosted GitHub Actions workflow, QEMU/OVMF smoke test, checksum/manifest, and GitHub release packaging split under the per-asset size limit.

## V1 software candidate

| Component | Pinned package(s) | Status |
| --- | --- | --- |
| NVIDIA driver | nvidia-open 620.70.06-1ubuntu1; pin package 620.70.06-1ubuntu1 | Candidate; not B300-tested |
| CUDA Toolkit | cuda-toolkit-13-5 13.5.0-1 | Candidate; repository dependencies are version-ranged |
| Fabric Manager | nvidia-fabricmanager 620-1 -> direct 2.0.0.rel106-1 | Standalone FM versioning for R620 |
| FM driver library | libnvidia-fmdrv1 620.70.06-1ubuntu1 | Pinned to matching driver package |

NVIDIA's R620 release notes mention HGX B300 and Ubuntu 24.04, and the Fabric Manager guide documents HGX B300 NVSwitch topology and independent FM versioning starting at driver release 620. These references do not constitute qualification of the exact Supermicro PIO-422GS-NB3RT. NVIDIA's R595 branch is an alternative candidate, not the stack in this V1 ISO.

## Test evidence

- 7 local unit tests pass, including Autoinstall/GRUB behavior, release split/reassembly, manifest integrity, and default installer gates.
- Ubuntu source signature and ISO checksum verified; custom ISO checksum verified.
- QEMU with OVMF boots the ISO to Ubuntu 24.04.3 kernel and confirms local Autoinstall arguments. No virtual disk was attached.
- No complete VM installation, NVIDIA package download/install, physical B300 install, or GPU/NVSwitch validation has been performed.

## Release

ISO: nvidia-b300-ubuntu-24.04.3-r620.iso. SHA256: be8d2af941a072a5428c0ab8ed0c49f3eb248672542f56b4127d2ae557db52f9. GitHub Release: https://github.com/likhithsatya/zel/releases/tag/b300-ubuntu-24.04.3-r620-20261106. The ISO is split into two downloadable parts because GitHub limits individual release assets to under 2 GiB. Download every release asset into one directory and run bash assemble-release-iso.sh . to reconstruct and verify the ISO.

## Before physical testing

1. Confirm fresh written disk-wipe approval and an install window; the previous POC approval does not cover this run.
2. Select and verify the intended disk at the interactive installer storage screen; supervise the console.
3. Check Secure Boot/MOK requirements and confirm VLAN 30 can reach Ubuntu and NVIDIA package repositories or an approved mirror.
4. Coordinate the NICo record update because this ISO boot path bypasses NICo; no BMC/NICo action was performed by this project.
5. After installation, validate OS/SSH, then driver, all eight GPU PCI devices, nvidia-smi, CUDA, and Fabric Manager on the physical B300. Keep results separate from the QEMU smoke-test result.

## Scope boundary

This is an installer ISO, not a preinstalled raw/qcow2 image or a named Hydra-like custom image. The PXE/NICo workflow remains available separately. No BMC operation, NICo registration, disk wipe, physical installation, or GPU qualification was performed.
