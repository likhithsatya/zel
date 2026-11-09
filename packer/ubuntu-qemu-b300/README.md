# B300 QEMU Image Build

This is a separate Packer path that produces a preinstalled Ubuntu 24.04.3 `qcow2` image for VM/cloud testing. It does not replace the custom installer ISO and is not a bare-metal disk deployment method.

## Build

Prerequisites: Packer 1.10+, QEMU/QEMU image tools, OVMF, OpenSSL, Python with the repository requirements, internet access to Ubuntu/NVIDIA repositories, and enough free space for the source cloud image and image output. The pinned source is the date-stamped Ubuntu Noble cloud image in `config/versions.yml`; its SHA256SUMS manifest/signature and payload hash were verified before pinning.

From the repository root:

```bash
python -m pip install -r requirements.txt
packer version
make packer-qemu-validate
make packer-qemu
```

The build clones the signed, date-pinned Ubuntu 24.04 cloud image in `config/versions.yml` (or accepts `--source-image`), checks its SHA256, provisions base packages and the NVIDIA first-boot systemd unit, then removes the temporary build account and resets cloud-init state. The Packer build password is generated for the build and is not embedded in the resulting image. The NVIDIA stack is downloaded/installed on the image's first boot, not inside Packer's SSH provisioning session.

The default output is `artifacts/packer-qemu-b300/nvidia-b300-ubuntu-24.04.3-r620.qcow2` with SHA256 and JSON manifest files. V1 was built locally and copied to that path; its checksum and `qemu-img check` pass. The first-boot systemd install unit and GPU stack have not yet been successfully tested by booting this qcow2. Override local resources/output with:

```bash
python scripts/build_packer_qemu.py \
  --source-image /path/to/ubuntu-24.04-server-cloudimg-amd64.img \
  --output-dir /path/to/large-disk/packer-qemu-b300 \
  --cpus 2 --memory-mb 4096 --accelerator auto
```

## First Boot

The artifact is a generalized cloud-init image. The Packer build account is locked/removed before shutdown; the consumer must provide first-boot cloud-init user data (for example, a VM platform metadata service or a NoCloud seed) that creates the test user and SSH access. Do not reuse the Packer build credentials.

The qcow2 build and image integrity check have succeeded. The NVIDIA first-boot unit has not yet been boot-tested. This artifact can test the generalized OS image and (after first boot) package installation in a VM. It has no HGX B300 GPU/NVSwitch, so it cannot validate GPU detection, Fabric Manager operation on NVSwitch, or the exact Supermicro platform. The custom installer ISO remains the separate supervised physical-install artifact.

The NVIDIA package repositories must be reachable on first boot. A fully offline package repository is not part of this Packer/QEMU target yet. CUDA dependency versions are still resolved by repository version ranges, so the output is version-targeted, not a fully locked dependency snapshot. The current qcow2 was built and its structure/checksum verified, but the first-boot NVIDIA service has not yet been run in a VM.