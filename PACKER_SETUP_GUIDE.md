# Packer Setup Guide for Custom Images

This guide covers installing Packer on your system and building custom images with reference to HashiCorp's official tutorials and the digipowerx-packer-images repository.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Understanding Packer Basics](#understanding-packer-basics)
4. [Building Custom Images - Real World Example](#building-custom-images---real-world-example)
5. [Troubleshooting](#troubleshooting)
6. [Resources](#resources)

---

## Installation

### Prerequisites

**System Requirements:**
- Linux, macOS, or Windows
- About 15-25 GB free disk space (for building images)
- Internet access (only needed for builds)

### Linux Installation (Ubuntu/Debian)

```bash
# Add HashiCorp's GPG key
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg

# Add the HashiCorp repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

# Update and install
sudo apt update
sudo apt install packer
```

### Verify Installation

```bash
packer version
# Output: Packer v1.x.x
```

### macOS Installation

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/packer
```

### Windows Installation

Download the binary from:
https://www.hashicorp.com/products/packer/downloads

---

## Quick Start

### 1. Create Your First Packer Template

Create a file called `example.pkr.hcl`:

```hcl
packer {
  required_plugins {
    docker = {
      source  = "github.com/hashicorp/docker"
      version = "~> 1.0"
    }
  }
}

source "docker" "example" {
  image   = "ubuntu:24.04"
  pull    = true
  discard = true
}

build {
  name    = "my-custom-image"
  sources = ["source.docker.example"]

  provisioner "shell" {
    inline = [
      "echo 'Building custom image'",
      "apt-get update",
      "apt-get install -y curl wget",
      "echo 'Custom image ready!'"
    ]
  }
}
```

### 2. Initialize Packer

```bash
# Download required plugins
packer init .
```

### 3. Validate Your Template

```bash
packer validate example.pkr.hcl
# Output: The configuration is valid.
```

### 4. Build the Image

```bash
packer build example.pkr.hcl
```

---

## Understanding Packer Basics

### Core Concepts

1. **Source** - Where to build the image (Docker, AWS AMI, QEMU, etc.)
   ```hcl
   source "docker" "my_image" {
     image   = "ubuntu:24.04"
     pull    = true
     discard = true
   }
   ```

2. **Provisioners** - Scripts/tools to run during build (shell, file, ansible, etc.)
   ```hcl
   provisioner "shell" {
     inline = ["apt-get install -y git"]
   }

   provisioner "file" {
     source      = "local/path/to/file"
     destination = "/tmp/file"
   }
   ```

3. **Post-processors** - Actions after build completes (compress, upload, etc.)
   ```hcl
   post-processor "docker-tag" {
     repository = "myregistry/myimage"
     tags       = ["latest", "1.0"]
   }
   ```

4. **Build** - Orchestrates the sources and provisioners
   ```hcl
   build {
     sources = ["source.docker.my_image"]

     provisioner "shell" { ... }
     provisioner "file" { ... }
   }
   ```

### Common Packer Commands

```bash
packer init .              # Download plugins
packer validate file.pkr.hcl  # Validate syntax
packer build file.pkr.hcl     # Build the image
packer build -debug file.pkr.hcl  # Build with debug output
packer inspect file.pkr.hcl   # Show template details
```

---

## Building Custom Images - Real World Example

This example is based on the **digipowerx-packer-images** repository, which builds a custom Ubuntu 24.04 LTS ISO with NVIDIA drivers bundled for offline installation.

### What They Build

| Artifact | Purpose | Output |
|---|---|---|
| **NVIDIA GPU Installer ISO** | Ubuntu with NVIDIA drivers bundled for offline install | `ubuntu-24.04.5-nvidia580.iso` |
| Plain Autoinstall ISO | Vanilla Ubuntu with automated installation | `ubuntu-24.04.5-autoinstall.iso` |
| QEMU/KVM Disk Image | VM-ready disk image | `ubuntu-24.04.5-qemu/` |
| Docker Image | Container image | Docker local image |

### Key Architecture

The NVIDIA ISO build process (simplified):

```
make nvidia-iso
  ↓
1. Fetch & verify vanilla Ubuntu ISO (3 GB)
  ↓
2. Docker container: Collect all NVIDIA packages offline
   - NVIDIA driver (580 branch)
   - Kernel modules
   - CUDA toolkit
   - Container toolkit
   - DCGM (monitoring)
  ↓
3. Repack vanilla ISO with offline packages
  ↓
Output: 8.4 GB ISO ready for offline installation
```

### Setup Steps for Ubuntu 24.04

```bash
# 1. Clone the repository
git clone https://github.com/lakshmojizelar/digipowerx-packer-images.git
cd digipowerx-packer-images

# 2. Install dependencies
make deps  # Installs qemu, xorriso, ovmf, python3-yaml
make init  # Downloads Packer plugins

# 3. IMPORTANT: Set your login credentials
openssl passwd -6 'YourStrongPassword'
# Copy the hash to iso/nvidia-autoinstall/user-data

# 4. Validate the configuration
make validate

# 5. Build the NVIDIA ISO (takes 15-30 minutes on first run)
make nvidia-iso
# Result: output/ubuntu-24.04.5-nvidia580.iso

# 6. (Optional) Test the ISO in a VM
make nvidia-test
```

### Packer Template Breakdown (from digipowerx)

The `packer/nvidia-iso/nvidia-iso.pkr.hcl` file:

```hcl
# 1. Declare required Packer version and Docker plugin
packer {
  required_version = ">= 1.10.0"
  required_plugins {
    docker = {
      source  = "github.com/hashicorp/docker"
      version = ">= 1.0.8"
    }
  }
}

# 2. Variables for customization
variable "ubuntu_version" {
  type    = string
  default = "24.04.5"
}

variable "driver_branch" {
  type    = string
  default = "580"  # NVIDIA driver version
}

variable "with_docker" {
  type    = bool
  default = true
}

# 3. Define the Docker source
source "docker" "ubuntu" {
  image   = "ubuntu:24.04"
  pull    = true
  discard = true
}

# 4. Build pipeline: 3 stages
build {
  name    = "nvidia-iso"
  sources = ["source.docker.ubuntu"]

  # Stage 1: Verify kernel ABI compatibility
  provisioner "shell-local" {
    inline = [
      "ISO=$(./scripts/fetch-iso.sh ${var.ubuntu_version})",
      "ABI=$(./scripts/iso-kernel-abi.sh \"$ISO\")",
      "[ \"$ABI\" = '6.8.0-139-generic' ] || exit 1"
    ]
  }

  # Stage 2: Collect NVIDIA packages offline
  provisioner "shell" {
    script = "./scripts/nvidia/collect-packages.sh"
    environment_vars = [
      "DRIVER_BRANCH=${var.driver_branch}",
      "WITH_DOCKER=${var.with_docker ? "1" : "0"}"
    ]
  }

  # Stage 3: Repack and verify ISO
  provisioner "shell-local" {
    inline = [
      "./scripts/build-iso.sh ...",
      "xorriso -indev output/ubuntu.iso -report_el_torito plain"
    ]
  }
}
```

---

## Customization Examples

### Build with Different NVIDIA Driver

```bash
make nvidia-iso PACKER_ARGS="-var driver_branch=595"
```

### Include Additional Packages

```bash
make nvidia-iso PACKER_ARGS="-var 'extra_packages=[\"htop\",\"curl\"]'"
```

### Unattended Installation (⚠️ wipes disk without confirmation)

```bash
make nvidia-iso-unattended
```

---

## Troubleshooting

### Issue: "Plugin not found"

```bash
# Solution: Initialize Packer
packer init .
```

### Issue: "Docker not running"

```bash
# Check Docker status
sudo systemctl status docker

# Start Docker if stopped
sudo systemctl start docker

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Issue: Insufficient disk space

```bash
# Check available space
df -h

# Monitor during build
watch -n 5 "df -h; du -sh output/"
```

### Issue: Build fails with "kernel_abi mismatch"

The NVIDIA drivers in the ISO don't match the kernel version. The build output tells you the expected ABI:

```bash
make nvidia-iso PACKER_ARGS="-var kernel_abi=6.8.0-XXX-generic"
```

### Issue: Timeout or slow builds

- First builds are slow: ~30 minutes (downloads ISO + all packages)
- Subsequent builds: ~5-10 minutes (cached)
- Ensure good internet connection

---

## Resources

### Official HashiCorp Documentation

- **Install Packer**: https://developer.hashicorp.com/packer/install
- **Tutorials**: https://developer.hashicorp.com/packer/tutorials
- **AWS AMI**: https://developer.hashicorp.com/packer/tutorials/aws
- **Docker**: https://developer.hashicorp.com/packer/tutorials/docker
- **HCP Packer Registry**: https://developer.hashicorp.com/packer/tutorials/hcp-get-started
- **HCL2 Configuration**: https://developer.hashicorp.com/packer/guides/hcl

### Example Projects

- **DigiPowerX Packer Images** (NVIDIA GPU ISO)
  - Repository: https://github.com/lakshmojizelar/digipowerx-packer-images
  - Features: Offline NVIDIA driver installation, DCGM, Container Toolkit
  - Supports: Ubuntu 24.04 LTS

### Key Concepts

1. **Builders** (formerly "sources")
   - Docker
   - QEMU/KVM
   - AWS EC2
   - Azure
   - Google Cloud
   - Vagrant

2. **Provisioners**
   - `shell` - Run shell commands
   - `file` - Copy files
   - `ansible` - Run Ansible playbooks
   - `puppet` - Run Puppet
   - `chef` - Run Chef

3. **Post-Processors**
   - `docker-tag` - Tag Docker images
   - `docker-push` - Push to registry
   - `vagrant` - Create Vagrant box
   - `checksum` - Generate checksums
   - `compress` - Compress artifacts

---

## Next Steps

1. **Install Packer**: Follow the installation section
2. **Try the Quick Start**: Build your first Docker image
3. **Study Real Examples**: Review the digipowerx repository
4. **Build Custom Images**: Adapt templates for your needs
5. **Test Locally**: Use QEMU/Docker before cloud deployment
6. **Integrate with CI/CD**: Automate image builds in GitHub Actions or similar

---

## Quick Reference: Common Patterns

### Docker Image
```hcl
source "docker" "example" {
  image   = "ubuntu:24.04"
  pull    = true
  discard = true
}
```

### AWS AMI
```hcl
source "amazon-ebs" "example" {
  ami_name      = "my-custom-image"
  instance_type = "t3.micro"
  region        = "us-east-1"
  source_ami    = "ami-0c55b159cbfafe1f0"  # Ubuntu 24.04
}
```

### QEMU/KVM
```hcl
source "qemu" "example" {
  iso_url           = "https://cloud-images.ubuntu.com/24.04/current/focal-server-cloudimg-amd64.img"
  iso_checksum      = "..."
  output_directory  = "output/"
  vm_name           = "ubuntu-24.04.qcow2"
}
```

### Shell Provisioner
```hcl
provisioner "shell" {
  inline = [
    "apt-get update",
    "apt-get install -y docker.io",
    "systemctl enable docker"
  ]
}
```

### File Provisioner
```hcl
provisioner "file" {
  source      = "local/config.yaml"
  destination = "/etc/myapp/config.yaml"
}
```

---

**Last Updated:** November 2024
**References:** HashiCorp Packer Docs, DigiPowerX Project
