# Project and Conversation History

Updated: 2026-11-06

This document records the decisions and work completed in the conversation. It is a project summary, not a verbatim transcript. No passwords, private keys, API tokens, BMC credentials, or NICo certificates are recorded here.

## Objective and Scope

The requested project is Ubuntu Server 24.04.3 provisioning for the documented Supermicro HGX B300 in NIC mode. The user clarified that BMC boot/media handling will be performed by their team and that the immediate deliverable is a custom Ubuntu installer image with NVIDIA software and a build pipeline.

Two distinct artifacts exist:

- A NICo/iPXE PXE deployment bundle, following the original POC architecture.
- A custom, bootable Ubuntu installer ISO that can be booted using the user's chosen method. It prompts for installation identity, storage, and SSH configuration and installs a documentation-supported NVIDIA stack during Autoinstall.

The ISO is an installer, not a preinstalled raw or qcow2 disk snapshot. A named Hydra-like preinstalled image remains separate future scope.

## Reference Facts

The checked-in references are [B300 NICo Bring-up](../B300%20NICo%20Bring-up.pdf) and [the NICo provisioning POC report](../POC%20Report-%20NICo%20Site%20Controller%20End-to-End%20Bare-Metal%20Provisioning%20of%20HGX%20B300.docx).

The documented POC used:

- Supermicro platform reference: PIO-422GS-NB3RT, serial S989423X6713063.
- Onboard Intel X710 PXE MAC: `90:5A:08:C1:92:62`.
- Host/BMC addresses: `10.10.30.81` and `10.10.30.77` on VLAN 30 (`10.10.30.0/24`, gateway `.254`).
- Existing borderleaf DHCP relay to NICo DHCP at `.250` and `.251`; no second DHCP server or new VLAN.
- NICo seed handoff: `${tenant-cloudinit-url}`.
- Control plane: `10.11.1.0/24`.
- Temporary media host: `10.11.1.99:8090`; it was not reboot-safe and is not a permanent hosting choice.
- Installed POC OS: Ubuntu 24.04.3, kernel `6.8.0-147-generic`, hostname `b300-01`, user `digi`, key-only SSH.

The POC did not document the install disk serial or SSH public key. The 3.44 TB root filesystem observation is not a disk identity. The old wipe approval applied to the POC run only. The POC used the admin CLI on `tf1`; production NICo route (CLI vs REST) was not settled, and the report recommends REST for production. The POC excluded GPU software and did not validate the NVIDIA stack.

## Work Completed

### Provisioning Project

- Added Ubuntu Autoinstall and NoCloud seed templates, base packages, hardware/version/deployment configuration, Codespaces setup, Make targets, shell helpers, tests, and GitHub Actions validation/package workflows.
- Implemented POC-faithful UEFI HTTP/iPXE bundle generation with SHA256 manifest and site-value validation.
- Downloaded Ubuntu Server 24.04.3, verified Ubuntu's signed checksum manifest with the Ubuntu archive keyring, and verified the ISO SHA256.
- Built a full PXE payload containing the ISO, kernel, initrd, iPXE file, seed template, helper scripts, and checksum files.

### Custom Installer ISO

- Added `scripts/build_custom_iso.py` and `scripts/build-custom-iso.sh` to remaster the official Ubuntu ISO while replaying its BIOS/UEFI boot metadata.
- Added an embedded local NoCloud seed. The installer uses interactive identity, storage, and SSH sections; the POC PXE MAC is configured for DHCP. No SSH key or reusable password is baked into the image; a per-build random password hash is generated for the interactive account configuration.
- Added an Autoinstall late-command that installs the NVIDIA software from Ubuntu/NVIDIA package repositories. The ISO installation needs network access to those repositories.
- The checked-in `config/versions.yml` leaves ordinary GPU installation gates closed. The custom ISO contains a separate image-local config copy with the gates open so this ISO installs the requested candidate stack.
- Added a self-hosted GitHub Actions custom ISO workflow labelled `image-builder`, plus a QEMU/OVMF smoke-test script.
- Added release chunking and reassembly because GitHub limits individual release assets to under 2 GiB. The release includes two numbered ISO parts, the SHA256 sidecar, manifest, and reassembly helper.
- Added `scripts/generate_project_report.py` and a `make report` target, producing an editable v1 report and a two-page architecture PDF; the PDF diagram distinguishes the custom ISO flow from the reference NICo PXE flow.
- Added a project history of operational blockers and NICo status to [README.md](../README.md).

## NVIDIA Candidate Stack

The ISO currently targets:

| Component | Package/version |
| --- | --- |
| NVIDIA open driver | `nvidia-open=620.70.06-1ubuntu1` |
| Driver pin | `nvidia-driver-pinning-620.70.06=620.70.06-1ubuntu1` |
| CUDA Toolkit | `cuda-toolkit-13-5=13.5.0-1` |
| Fabric Manager package | `nvidia-fabricmanager=620-1`, transitional to `nvidia-fabricmanager-direct=2.0.0.rel106-1` |
| FM driver interface library | `libnvidia-fmdrv1=620.70.06-1ubuntu1` |

NVIDIA's R620 release notes date driver `620.70.06` to 2026-11-04, support Ubuntu 24.04 point releases including 24.04.3, and mention HGX B300 in virtualization passthrough and server-platform architecture tables. These references do not qualify the exact Supermicro PIO-422GS-NB3RT configuration. CUDA 13.5 maps to R620. NVIDIA's Fabric Manager guide explicitly describes HGX B300 NVSwitch topology and states that starting with driver release 620 Fabric Manager is independently versioned. The standalone FM package version `2.0.0.rel106` is therefore not by itself a driver mismatch; the image pins its driver interface library to the exact R620 package version.

A previous R595 candidate was also researched: driver/FM `595.112.07` and CUDA 13.2 (current repository package `cuda-toolkit-13-2=13.2.2-1`). R595 release notes dated 2026-10-22 also list HGX B300 and Ubuntu 24.04. This is an older branch alternative, not a Supermicro-qualified stack, and it is not the version in the current ISO.

## Artifacts

- Custom installer ISO: [`artifacts/nvidia-b300-ubuntu-24.04.3-r620.iso`](../artifacts/nvidia-b300-ubuntu-24.04.3-r620.iso).
- ISO checksum file: [`artifacts/nvidia-b300-ubuntu-24.04.3-r620.iso.sha256`](../artifacts/nvidia-b300-ubuntu-24.04.3-r620.iso.sha256).
- ISO manifest: [`artifacts/nvidia-b300-ubuntu-24.04.3-r620.iso.manifest.json`](../artifacts/nvidia-b300-ubuntu-24.04.3-r620.iso.manifest.json).
- NICo PXE bundle: [`artifacts/nvidia-b300-pxe-ubuntu-24.04.3.tar.gz`](../artifacts/nvidia-b300-pxe-ubuntu-24.04.3.tar.gz).
- Public GitHub Release: [b300-ubuntu-24.04.3-r620-20261106](https://github.com/likhithsatya/zel/releases/tag/b300-ubuntu-24.04.3-r620-20261106), containing the two ISO parts and reassembly/checksum files.
- Editable build report: [`docs/B300-CUSTOM-OS-V1-REPORT.md`](B300-CUSTOM-OS-V1-REPORT.md).
- Architecture PDF: [`docs/B300-CUSTOM-OS-V1-REPORT.pdf`](B300-CUSTOM-OS-V1-REPORT.pdf).

The current ISO SHA256 is `be8d2af941a072a5428c0ab8ed0c49f3eb248672542f56b4127d2ae557db52f9`. The `artifacts/` directory is git-ignored to keep multi-gigabyte binaries out of Git history; the ISO is published in the GitHub Release above.

## Validation Performed

- `make validate test`: passed 8 unit tests, configuration validation, and shell syntax checks after report generation was added.
- `make report`: generated the editable Markdown and two-page PDF successfully; both pages were visually inspected.
- `git diff --check`: passed.
- Ubuntu checksum manifest signature and ISO checksum: verified.
- Custom ISO checksum: verified using its sidecar.
- ISO split/reassembly round-trip test: passed with checksum preservation.
- `make smoke-custom-iso`: passed. QEMU with OVMF reached the Ubuntu 24.04.3 kernel and the local Autoinstall arguments. No virtual disk was attached.
- Editor diagnostics: no errors reported at the last diagnostics run.

The QEMU test is only a UEFI boot smoke test. It did not complete an Ubuntu installation, test NVIDIA package downloads, test a running GPU, or validate B300 behavior.

## Not Done / Open Risks

- No BMC operation, NICo registration, disk wipe, physical installation, or server reboot was performed.
- No full VM installation/package-download test was performed. The B300 VLAN's access to Ubuntu/NVIDIA repositories is unverified; interrupted package downloads can leave an incomplete install.
- The exact Supermicro OEM driver qualification and Secure Boot/MOK enrollment procedure remain unverified.
- The custom ISO bypasses NICo during boot. The POC machine already has NICo state/instance records; coordinate with the NICo owner and reconcile those records after any reinstall.
- Fresh written disk-wipe approval and an install window are still required. Supervised console interaction is needed to select the intended disk.
- The current image installs the R620 candidate; do not describe it as GPU-validated or production-qualified. GPU checks must run on the physical B300 after installation.
- No external message to Chakra, Vinod, or the team was sent. Draft messages were provided in chat only.
- No named Hydra-like preinstalled disk image was built; the current artifact is an installer ISO.

## Suggested Next Actions

1. Ask Chakra/Supermicro to confirm the driver branch, Secure Boot/MOK steps, and exact platform support for PIO-422GS-NB3RT. Decide whether to retain R620 or build the R595 alternative.
2. Verify outbound repository access from VLAN 30 or provide an approved mirror/proxy.
3. Coordinate with Vinod/NICo before bypassing its existing records and obtain fresh written wipe approval and a time window.
4. Verify the ISO SHA256 after transfer, then perform a supervised install with console access and careful disk selection.
5. After first boot, validate Ubuntu/SSH and installer logs; only then run GPU checks on the physical B300. Do not count VM smoke tests as GPU validation.

## Repository State

The source and documentation are committed and pushed to `main`. The ISO is published as the GitHub Release listed above. The original ISO and PXE archive remain ignored by Git so multi-gigabyte binaries do not enter Git history.