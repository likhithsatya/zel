# NICo HGX B300 PXE Provisioning

Reproducible Ubuntu Server 24.04.3 provisioning for the documented HGX B300 NIC-mode workflow. The repository provides both a NICo/iPXE deployment bundle and a bootable custom installer ISO that installs the pinned NVIDIA candidate stack. It does not operate NICo, BMCs, DHCP, VLANs, or physical servers.

## Reference findings

The checked-in [B300 NICo Bring-up](B300%20NICo%20Bring-up.pdf) and [NICo provisioning POC report](POC%20Report-%20NICo%20Site%20Controller%20End-to-End%20Bare-Metal%20Provisioning%20of%20HGX%20B300.docx) report a successful Ubuntu 24.04.3 install on a Supermicro HGX B300 in zero-DPU/NIC mode. The host's onboard Intel X710 PXE port booted through UEFI HTTP, iPXE fetched the Ubuntu kernel, initrd, and live-server ISO over HTTP, and Subiquity ran unattended Autoinstall. NICo supplied the NoCloud seed using `${tenant-cloudinit-url}`.

The POC used VLAN 30 (`10.10.30.0/24`, gateway `.254`) for the B300, BMC, and jump host. The B300 PXE MAC was `90:5A:08:C1:92:62`; its POC BMC/host addresses were `.77`/`.81`. The existing borderleaf relay forwarded DHCP to NICo's `.250`/`.251` servers; no additional relay or DHCP server was needed. NICo's control plane used `10.11.1.0/24`; its test image server was `10.11.1.99:8090`, a temporary server that is not suitable as a permanent deployment URL. These are **reference test values only** and are not defaults in this project. The installed host was Ubuntu 24.04.3, kernel `6.8.0-147-generic`, hostname `b300-01`, with key-only SSH. The report's iPXE arguments include `BOOTIF`, `ip=dhcp`, `fb=false`, `url=`, `autoinstall`, `ds=nocloud-net;s=${tenant-cloudinit-url}`, and serial console settings.

The guide/report also document Supermicro-specific Redfish behavior and NICo image patches. NICo's standard boot-order endpoint was rejected; the successful setup used the vendor `FixedBootOrder` path. NICo image tags could be reverted by Helm upgrades, the OS server was transient, and some NICo changes were not tracked upstream. Those are operational prerequisites for the site owner, not automation performed here. The POC explicitly excluded GPU drivers and Fabric Manager; this project has a documentation-supported candidate only, not an OEM-qualified or hardware-tested stack.

## Repository contents

- `autoinstall/`: Autoinstall and NoCloud seed templates.
- `config/`: platform notes, diagnostic packages, deployment defaults, and version/validation status.
- `drivers/`: separately gated NVIDIA repository, driver, Fabric Manager, and CUDA installers.
- `scripts/`: config validation, bundle generation, OS/GPU checks, package helper, and checksums.
- `.github/workflows/`: configuration validation, PXE bundle packaging, and self-hosted custom ISO builds.
- `tests/`: bundle, custom ISO, release reassembly, and report-generation tests.

The PXE archive contains the official Ubuntu kernel, initrd, live-server ISO, iPXE entry, seed template, helper scripts, and checksums. Separately, `make custom-iso` builds `artifacts/nvidia-b300-ubuntu-24.04.3-r620.iso`, a bootable UEFI installer ISO with an interactive identity/disk/SSH setup, DigiPowerX login banner, and an Autoinstall late-command that installs the pinned NVIDIA driver, Fabric Manager, and CUDA. It is an installer ISO, not a preinstalled raw/qcow2 disk image. The NVIDIA/Ubuntu package repositories must be reachable during installation.

The DigiPowerX installer ISO is available in the [custom installer prerelease](https://github.com/likhithsatya/zel/releases/tag/digipowerx-b300-custom-ubuntu-24.04.3-r620-20261109). Download both numbered parts and the checksum, then follow the included `REASSEMBLE.txt` instructions. The published ISO SHA256 is `3f3ebbaaea3a4133d38f1635d13e0cb74e9c954a97ae25e0bbabec86ac3947ae`.

For a separate Packer/QEMU VM/cloud artifact, `make packer-qemu-validate` validates the builder and `make packer-qemu` creates `artifacts/packer-qemu-b300/nvidia-b300-ubuntu-24.04.3-r620.qcow2`. The current local 64-GiB qcow2 includes the DigiPowerX login banner, passes `qemu-img check`, and has its SHA256 in the sidecar. It is a generalized VM image, not a bare-metal installer, and requires cloud-init user data on first boot to create the consumer account/SSH access. The NVIDIA candidate stack is installed by an enabled systemd first-boot service, not during the Packer build; that service has not yet been exercised in a VM. The temporary Packer build account is password-cleared/locked and removed from sudo before finalization. The build needs network access to Ubuntu/NVIDIA repositories on first boot.

The qcow2, SHA256, and manifest are published in the [Packer first-boot candidate prerelease](https://github.com/likhithsatya/zel/releases/tag/b300-qemu-qcow2-firstboot-candidate-20261109). It is separate from the DigiPowerX installer ISO; first-boot package installation and GPU behavior are unvalidated.

The GitHub repository is public as of 2026-11-09. Its POC documents include internal IP addresses and the B300 MAC; confirm that public exposure is approved. Keep the self-hosted `image-builder` runner isolated and restrict its workflows to trusted maintainers.

## Local use

Use Python 3.12+ and Bash. In Codespaces, install the pinned Python dependency:

```bash
python -m pip install -r requirements.txt
make validate
make test
make bundle-template
make custom-iso
make smoke-custom-iso
make report
make packer-qemu-validate
```

`make custom-iso` verifies Ubuntu's signed media manifest and ISO checksum, then remasters the source ISO while preserving its BIOS/UEFI boot catalog. `make smoke-custom-iso` boots the result under QEMU/OVMF with no disk attached and checks the kernel and local Autoinstall arguments. `scripts/split-release-iso.sh` prepares sub-2-GiB release parts plus checksum, manifest, and reassembly script because GitHub limits individual release assets to less than 2 GiB. The GitHub image workflow requires a self-hosted runner labelled `image-builder`, with `xorriso`, `bsdtar`, `gpgv`, `openssl`, QEMU, OVMF, the Ubuntu archive keyring, and enough free space for the source, remastered ISO, and release parts. Configuration validation remains on a separate hosted runner.

`make report` regenerates the editable [v1 build report](docs/B300-CUSTOM-OS-V1-REPORT.md) and [architecture PDF](docs/B300-CUSTOM-OS-V1-REPORT.pdf) using the pinned ReportLab dependency.

`make bundle-template` creates a **non-deployable template artifact** under `artifacts/`; endpoint, NIC, disk, host, user, and SSH-key values remain placeholders. To render a site-specific bundle, provide values out of band:

```bash
export PXE_BASE_URL='http://<approved-image-server>:<port>'
export INSTALL_NIC_MAC='<B300-PXE-NIC-MAC>'
export INSTALL_DISK_SERIAL='<explicit-install-target-serial>'
export INSTALL_HOSTNAME='<host-name>'
export INSTALL_USERNAME='digi'
export INSTALL_SSH_PUBLIC_KEY='<authorized-public-key>'
./scripts/prepare-pxe.sh --output artifacts/site-bundle
```

To build the complete PXE payload, including the official Ubuntu 24.04.3 ISO, kernel, and initrd, run `make image`. It verifies Ubuntu's signed `SHA256SUMS` with the local Ubuntu archive keyring, checks the ISO against the pinned digest, and writes `artifacts/nvidia-b300-pxe-ubuntu-24.04.3.tar.gz` plus a SHA256 file. This is a NICo/iPXE HTTP deployment payload, **not a standalone USB ISO**. It contains a template seed and is not target-ready until its required disk serial, SSH public key, and approved HTTP base URL are supplied. Render a site-specific copy while reusing the verified media:

```bash
python scripts/prepare_pxe.py \
	--media-dir artifacts/nvidia-b300-pxe-ubuntu-24.04.3/ubuntu-24.04.3 \
	--output artifacts/site-bundle
```

The machine-specific `INSTALL_DISK_SERIAL`, `INSTALL_SSH_PUBLIC_KEY`, `PXE_BASE_URL`, and other values must be present in the environment for this final render. The PXE MAC and disk are never guessed. The generated `SHA256SUMS` covers the Ubuntu ISO, boot files, seed, and scripts.

Do not commit site values, credentials, or private keys. The PXE MAC and disk serial are mandatory to avoid choosing an arbitrary NIC or installation disk. The Autoinstall password is locked and SSH password authentication is disabled; provide a public key through the deployment environment. Treat the rendered seed and artifact as site-specific operational data.

The generated `boot.ipxe` references these files at `PXE_BASE_URL/ubuntu-24.04.3/`: `vmlinuz`, `initrd`, and `ubuntu-24.04.3-live-server-amd64.iso`. Stage the matching Ubuntu 24.04.3 live-server assets on an approved HTTP service before provisioning. Verify the ISO release and checksum against Ubuntu's official image publication; this pipeline does not download or silently substitute a newer point release.

## NICo integration

1. The POC host was `10.10.30.81` and was reported reachable after Run 1; confirm its current state before any new operation. The previous “wipe approved” entry applied to the POC run only. Obtain fresh written workload-owner approval and a maintenance window before disk wipe, allocation, or reboot.
2. The POC relay to NICo DHCP (`.250`/`.251`) and `${tenant-cloudinit-url}` seed handoff are already documented as working. Do not add a DHCP server or change VLAN, bridge, relay, or switch settings.
3. The POC served media at `10.11.1.99:8090` using a transient server on `nico-01`; it is not a permanent hosting choice. Select and approve durable HTTP hosting reachable from VLAN 30, then stage the archive contents at the paths used in `boot.ipxe`.
4. The POC command shape was `nico-admin-cli operating-system create --name ubuntu-24.04.3-autoinstall --org <org> --ipxe-script "$(cat boot.ipxe)" --user-data "$(cat seed/user-data)"`. The report used the admin CLI on `tf1`; it does not establish that as the production route, and the production REST path should be confirmed with the NICo owner. Do not reuse the POC's `--cloud-unsafe-op` shortcut by default. This repository does not call NICo APIs or store credentials.
5. The POC's public key is reportedly in the user-data on `tf1`, but it is not in these documents or this repository. Confirm with Vinod whether to use that key or a team key. The POC's 3.44 TB root filesystem is not a disk identity; obtain and verify the target disk serial from the running host, NICo inventory, or BMC.
6. Confirm the target is the POC machine (serial `S989423X6713063`, PXE MAC `90:5A:08:C1:92:62`) before rendering. Review the final seed, target disk serial, URL, and checksums before registration. The template is not ready to install until those inputs are resolved.

No shared DHCP, VLAN, bridge, BMC, firmware, boot-order, or NICo configuration is changed by the scripts in this repository.

## Remaining Readiness Blockers

The confirmed POC MAC (`90:5A:08:C1:92:62`), host address (`10.10.30.81`), relay to `.250`/`.251`, and NICo seed handoff are reusable for this same B300. They do not make the current template safe to register or install.

| Blocker | Likely owner | How to resolve |
| --- | --- | --- |
| Target disk serial | B300 operator, likely Vinod | Read from the running host, NICo inventory, or BMC; verify the intended disk, especially if multiple disks are present. |
| Persistent HTTP URL | Infrastructure owner | Select durable hosting reachable from VLAN 30. `10.11.1.99:8090` was temporary and must not be assumed. |
| SSH public key | Vinod or team lead | Choose the existing `digi` key or a team key. The POC key may be on `tf1`, but is not in this repository. Only the public key is needed. |
| Fresh wipe/install approval | Machine owner | Obtain written approval and a dated maintenance window. The POC's earlier wipe approval does not authorize another run. |
| Production NICo route | Vinod/NICo owner | Decide between the POC admin CLI and the recommended production REST API. The POC CLI/certificate availability does not settle the production route. |

Resolve the disk serial and persistent URL first; the SSH key can be selected in parallel. Wipe approval must be in hand before any real allocation or install. Until then, the archive is prepared but not install-ready.

## Validation boundaries

GitHub Actions and local tests can validate YAML/config values, shell syntax, bundle contents, and artifact checksums. They do **not** validate UEFI HTTP boot, NICo integration, or GPU behavior. `scripts/validate-gpu.sh` must be run on the actual B300 after the approved GPU software stack is installed; a VM without NVIDIA hardware is not a GPU pass.

The custom ISO installs Ubuntu plus the documentation-supported NVIDIA candidate during setup. It is not hardware or OEM validated, and successful ISO/VM boot does not prove GPU functionality. A separately named preinstalled image patterned on Hydra remains future scope; it needs an agreed image name and distinct image recipe/pipeline. The current `.iso` is an installer, not a preinstalled disk snapshot.

## NVIDIA Compatibility Candidate

The following is a documentation-supported candidate for the HGX B300 NVSwitch platform, not a claim that the Supermicro PIO-422GS-NB3RT has been tested with it:

| Component | Pinned NVIDIA package | Version | Evidence |
| --- | --- | --- | --- |
| Data Center driver | `nvidia-open=620.70.06-1ubuntu1`; `nvidia-driver-pinning-620.70.06=620.70.06-1ubuntu1` | R620, `620.70.06` | NVIDIA's [R620 release notes](https://docs.nvidia.com/datacenter/tesla/tesla-release-notes-620-70-06/index.html) date the release 4 Nov 2026, support Ubuntu 24.04.z through .5, and mention HGX B300 in both the virtualization passthrough table and server-platform architecture list. These entries do not qualify the exact Supermicro chassis. The [driver installation guide](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/kernel-modules.html) directs Ubuntu users to `nvidia-open` and provides driver pinning packages. |
| CUDA Toolkit | `cuda-toolkit-13-5=13.5.0-1` | CUDA 13.5 | NVIDIA's [CUDA 13.5 release notes](https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html) map 13.5 to R620 and state that new features/newly enabled platforms require R620 or later. |
| Fabric Manager | `nvidia-fabricmanager=620-1` -> `nvidia-fabricmanager-direct=2.0.0.rel106-1`; `libnvidia-fmdrv1=620.70.06-1ubuntu1` | Standalone FM `2.0.0.rel106`; driver interface library matches R620 `620.70.06` | NVIDIA's [Fabric Manager guide](https://docs.nvidia.com/datacenter/tesla/fabric-manager-user-guide/index.html) explicitly covers HGX B300 8-GPU NVSwitch systems. It states FM packages match the driver before release 620 and are independently versioned starting with 620. The installer pins the driver-interface library to the matching driver package version. |

The package versions above were checked in NVIDIA's Ubuntu 24.04 repository on 2026-11-06. The repository keyring is pinned to `cuda-keyring=1.1-1` and its SHA256 is recorded in `config/versions.yml`; installation follows NVIDIA's [CUDA Linux guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html). CUDA 13.5 maps to R620 in NVIDIA's CUDA release notes. The package manifest and references are in [config/versions.yml](config/versions.yml).

This matrix is **not hardware validated**. The POC did not install GPU software, and the available references do not provide a Supermicro OEM qualification statement for the exact PIO-422GS-NB3RT SKU. In the checked-in `config/versions.yml`, `gpu_stack.enabled` and `gpu_stack.installation_authorized` remain `false`; normal PXE bundles cannot install it. `make custom-iso` creates an explicit image-local copy with those two flags enabled so the requested custom ISO installs the candidate stack. This is authorization to build that installer, not evidence of OEM qualification or physical GPU functionality.

CUDA's metapackage is pinned, but its repository dependencies use version ranges; fully reproducible CUDA subpackage resolution still requires a dated repository snapshot or a generated package lock. The kernel reference `6.8.0-147-generic` is the POC observation, not a hard kernel pin; installation requires headers for the running kernel.

## Custom ISO Installation

The custom ISO has identity, storage, and SSH as interactive Autoinstall sections. The installer uses the POC X710 MAC (`90:5A:08:C1:92:62`) with DHCP, defaults the account labels to `b300-01`/`digi`, and lets the operator choose the actual local password, installation disk, and SSH configuration. The build embeds only a per-build random password hash; no SSH key or reusable credential is baked in. If no key is entered, SSH password login remains disabled, so use the local console to add an authorized key after installation.

The late-command installs the R620 driver, Fabric Manager, and CUDA from NVIDIA's Ubuntu 24.04 repository. The target must have working DHCP and network access to both Ubuntu and NVIDIA package repositories during installation. Confirm the system's Secure Boot state and an approved DKMS/MOK enrollment procedure before use; that flow is not validated here. The NICo tracker says BIOS setup credentials are held by NICo Vault and lock-down settings were applied. Obtain access through the authorized Vault custodian and confirm the selected ISO boot method is permitted; do not bypass lock-down or make unapproved firmware changes. The ISO does not need NICo registration or the temporary `.99:8090` host; boot/media attachment is handled by the operator's chosen method.

If booting from BMC virtual media, verify that the media session survives the install reboot and any link interruption. The tracker reports brief BMC network drops; the possibility that they interrupt virtual media is a risk to check, not a confirmed failure.

1. Verify the ISO with `sha256sum -c artifacts/nvidia-b300-ubuntu-24.04.3-r620.iso.sha256` after transfer.
2. Likhith and Sai Rishith are the proposed supervised test operators; confirm the approach and schedule with Chakra and the machine owner. Obtain fresh written disk-wipe approval and an install window.
3. Before boot, confirm the NICo Vault credential custodian, BIOS setup password access, and that existing lock-down/boot settings permit the approved ISO boot path. Do not bypass lock-down or make unapproved firmware changes.
4. If using BMC virtual media, confirm it remains connected over reboot; the reported link-drop risk is an inference that must be checked. Agree on a rollback plan covering console/recovery access, an approved reimage or NICo reprovision route, and how to reconcile the host to NICo `Ready` if installation fails. This rollback has not been tested.
5. At the installer, set the account/password, select and verify the intended target disk, and configure the SSH public key. Keep network connected through the NVIDIA package installation and reboot.
6. Review installer logs for driver, Fabric Manager, and CUDA package failures. After first boot, run `scripts/validate-os.sh` and `scripts/validate-gpu.sh` on the actual B300. A successful ISO build or VM boot is not GPU validation.

## Hardware validation procedure

After site and workload-owner authorization, use an isolated test environment first:

1. Confirm the exact B300 SKU, firmware, PXE NIC, target disk serial, NICo image/chart versions, existing relay/DNS, HTTP asset URLs, and maintenance-window approval.
2. Verify the Ubuntu 24.04.3 ISO checksum and that the kernel/initrd/ISO and NICo seed URL are reachable from the host VLAN. Confirm that no new DHCP service or network change is involved.
3. From the generated bundle directory, run `sha256sum -c SHA256SUMS`. Review the iPXE script and Autoinstall seed; verify hostname, SSH public key, NIC MAC, and disk serial. Confirm the target disk may be erased.
4. Register the OS definition using the approved NICo procedure. Allocate only the explicitly approved test node; do not run the POC's `--cloud-unsafe-op` or destructive operations by default.
5. Observe the documented sequence: NICo discovery/validation, UEFI HTTP, iPXE, installer asset and seed fetch, Autoinstall, reboot, then key-only SSH. Save NICo events and installer logs.
6. On the installed host run `sudo scripts/validate-os.sh` and check `journalctl -b`, `/var/log/installer`, SSH, DHCP/network reachability, and artifact checksums.
7. For an explicitly authorized test, obtain Supermicro qualification for the exact SKU and review the candidate matrix. Configure the repository with `sudo drivers/setup-nvidia-repo.sh`, then set both GPU gate fields to `true` and run `sudo drivers/install-nvidia-driver.sh`, `sudo drivers/install-fabric-manager.sh`, and `sudo drivers/install-cuda.sh`. Reboot only after workload-owner approval. Run `sudo scripts/validate-gpu.sh` on the physical B300 and record PCI detection, driver version, `nvidia-smi`, CUDA compiler status, and Fabric Manager status. Do not mark GPU validation passed from CI or a VM.

## Known limitations

- NICo control-plane registration and seed hosting remain operator-managed; there is no documented approved API integration in this repository.
- The bundle references externally hosted Ubuntu assets and is not a complete disk image.
- No production network values, credentials, or NICo patches are supplied. NVIDIA package versions are a documentation-supported candidate but remain gated pending Supermicro SKU qualification and hardware testing.
- B300-specific NICo hardware validation, image durability, upgrade/recovery behavior, and multi-node operation remain untested here.
- The POC's NIC mode is in scope. BlueField-3/DOCA/DPU provisioning is explicitly out of scope.