# HashiCorp Packer - Custom Image Building Guide

A comprehensive guide to installing and using HashiCorp Packer for building custom machine images (Docker, AWS AMI, VM disk images, ISO installers).

## 📋 Contents

This repository includes complete documentation and tools for setting up Packer:

### Guides

1. **[PACKER_SETUP_GUIDE.md](PACKER_SETUP_GUIDE.md)** - Complete setup guide
   - Installation instructions (Linux, macOS, Windows)
   - Packer basics and core concepts
   - Real-world example: NVIDIA GPU Ubuntu ISO
   - Troubleshooting common issues

2. **[PACKER_EXAMPLES.md](PACKER_EXAMPLES.md)** - Copy-paste ready templates
   - Simple Docker image
   - Docker with multiple provisioners
   - AWS EC2 AMI
   - QEMU/KVM disk image
   - Ubuntu ISO with custom packages
   - Production-ready image with validation

3. **[PACKER_QUICK_REFERENCE.md](PACKER_QUICK_REFERENCE.md)** - One-page cheat sheet
   - Essential commands
   - HCL2 syntax reference
   - Common sources and provisioners
   - Debugging tips
   - Variable usage

### Scripts

4. **[PACKER_INSTALL.sh](PACKER_INSTALL.sh)** - Automated installation
   - Detects your OS (Linux/macOS)
   - Installs Packer and dependencies
   - Verifies installation
   - Creates example template

---

## 🚀 Quick Start

### 1. Install Packer

**Option A: Automated (Linux/macOS)**
```bash
chmod +x PACKER_INSTALL.sh
./PACKER_INSTALL.sh
```

**Option B: Manual (Linux)**
```bash
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install packer
```

**Option C: macOS**
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/packer
```

### 2. Verify Installation
```bash
packer version
# Output: Packer v1.x.x
```

### 3. Build Your First Image
```bash
# Create a simple template
cat > simple.pkr.hcl << 'EOF'
packer {
  required_plugins {
    docker = {
      source  = "github.com/hashicorp/docker"
      version = "~> 1.0"
    }
  }
}

source "docker" "ubuntu" {
  image   = "ubuntu:24.04"
  pull    = true
  discard = true
}

build {
  name    = "my-first-image"
  sources = ["source.docker.ubuntu"]

  provisioner "shell" {
    inline = [
      "apt-get update",
      "apt-get install -y curl wget",
      "echo 'Success!'"
    ]
  }

  post-processor "docker-tag" {
    repository = "my-custom-image"
    tags       = ["latest"]
  }
}
EOF

# Initialize and build
packer init .
packer validate simple.pkr.hcl
packer build simple.pkr.hcl
```

---

## 📚 Learning Path

1. **Beginner**: Start with [PACKER_SETUP_GUIDE.md](PACKER_SETUP_GUIDE.md#understanding-packer-basics)
   - Learn core concepts
   - Follow the quick start example
   - Try building a Docker image

2. **Intermediate**: Review [PACKER_EXAMPLES.md](PACKER_EXAMPLES.md)
   - Study different templates
   - Adapt examples to your needs
   - Build for AWS or QEMU

3. **Advanced**: Use [PACKER_QUICK_REFERENCE.md](PACKER_QUICK_REFERENCE.md)
   - Deep dive into HCL2 syntax
   - Write production templates
   - Integrate with CI/CD

4. **Real-World**: Reference the [DigiPowerX Project](#inspiration)
   - Study industrial-grade Packer usage
   - Build NVIDIA GPU ISOs
   - Create offline installation media

---

## 📖 Key Concepts

### Packer Workflow

```
Template (.pkr.hcl)
    ↓
Variables
    ↓
Source (Docker, AWS, QEMU, etc.)
    ↓
Provisioners (install software, configure)
    ↓
Post-Processors (tag, push, compress)
    ↓
Artifact (built image)
```

### Main Components

| Component | Purpose | Examples |
|-----------|---------|----------|
| **Source** | Where to build | Docker, AWS EC2, QEMU, Azure |
| **Provisioners** | What to install | shell, file, ansible, puppet |
| **Post-Processors** | Final processing | docker-tag, docker-push, checksum |
| **Variables** | Configuration | strings, numbers, lists, maps |
| **Locals** | Computed values | timestamps, paths, derived values |

---

## 🔧 Common Tasks

### Build a Docker Image
```bash
packer build docker-template.pkr.hcl
docker images  # See your new image
docker run --rm my-image:latest /bin/bash -c "echo 'Hello!'"
```

### Build an AWS AMI
```bash
# Configure AWS credentials first
aws configure
packer build aws-template.pkr.hcl
# Check AWS Console → EC2 → AMIs
```

### Build a QEMU Image
```bash
packer build qemu-template.pkr.hcl
ls -lh output/image.qcow2
# Can be used with KVM, VirtualBox, etc.
```

### Customize a Build
```bash
packer build \
  -var 'version=2.0' \
  -var 'region=us-west-2' \
  -var-file="prod.pkrvars.hcl" \
  template.pkr.hcl
```

### Debug a Build
```bash
packer build -debug template.pkr.hcl
# Pauses after each step, allows inspection
```

---

## 🎯 Real-World Example: NVIDIA GPU ISO

The [DigiPowerX Packer Images](https://github.com/lakshmojizelar/digipowerx-packer-images) project shows how to build a professional-grade Ubuntu ISO with NVIDIA drivers bundled for offline installation.

### What It Builds

| Artifact | Command | Use Case |
|----------|---------|----------|
| NVIDIA GPU Installer ISO | `make nvidia-iso` | Offline installation on GPU servers |
| Plain Autoinstall ISO | `make iso` | Vanilla Ubuntu with autoinstall |
| QEMU Image | `make image` | Test in local VMs |
| Docker Image | `make docker` | Container-based builds |

### Key Features

- ✅ Bundles NVIDIA drivers, CUDA, Container Toolkit for offline install
- ✅ Supports GPU monitoring (DCGM) and persistence daemon
- ✅ Works with Secure Boot (prebuilt kernel modules)
- ✅ Fully automated installation via cloud-init
- ✅ ~8 GB final ISO, installable without internet

### Quick Setup

```bash
git clone https://github.com/lakshmojizelar/digipowerx-packer-images.git
cd digipowerx-packer-images

# One-time setup
make deps    # Install system dependencies
make init    # Download Packer plugins

# Set login credentials (IMPORTANT!)
openssl passwd -6 'YourPassword'
# Copy hash to iso/nvidia-autoinstall/user-data

# Build the ISO
make validate
make nvidia-iso

# Result: output/ubuntu-24.04.5-nvidia580.iso
```

---

## 🛠️ Requirements

### System

| Requirement | Minimum | Recommended |
|-----------|---------|------------|
| OS | Linux 20.04+, macOS 10.12+, Windows 10+ | Ubuntu 22.04+ LTS |
| Disk Space | 15 GB | 25-50 GB |
| RAM | 2 GB | 4+ GB |
| CPU | 2 cores | 4+ cores |
| Internet | Required (build only) | 100+ Mbps |

### Tools

| Tool | Purpose | Install |
|------|---------|---------|
| Packer | Core | `apt install packer` or `brew install hashicorp/tap/packer` |
| Docker | Docker image builds | `apt install docker.io` or `brew install docker` |
| QEMU | VM image builds | `apt install qemu-system-x86` |
| Ansible | Provisioning | `apt install ansible` or `pip install ansible` |
| xorriso | ISO manipulation | `apt install xorriso` |

### Optional (for specific features)

```bash
# Ubuntu/Debian
sudo apt-get install -y \
  docker.io \
  qemu-system-x86 qemu-utils \
  xorriso \
  python3-yaml \
  ansible

# macOS
brew install docker qemu xorriso python-yaml
```

---

## 📝 Project Structure

```
/workspaces/zel/
├── PACKER_README.md              ← You are here
├── PACKER_SETUP_GUIDE.md         ← Complete setup guide
├── PACKER_EXAMPLES.md            ← Copy-paste templates
├── PACKER_QUICK_REFERENCE.md     ← One-page cheat sheet
├── PACKER_INSTALL.sh             ← Automated installation
│
├── packer/                        ← Your Packer templates
│   ├── docker/                    ← Docker image templates
│   ├── aws/                       ← AWS AMI templates
│   └── qemu/                      ← QEMU/KVM templates
│
├── scripts/                       ← Provisioning scripts
│   ├── install-docker.sh
│   ├── setup-app.sh
│   └── validate.sh
│
└── output/                        ← Built artifacts
    ├── docker-images/
    ├── aws-amis/
    ├── qemu-images/
    └── isos/
```

---

## 🐛 Troubleshooting

### Issue: "Plugin not found"
```bash
# Solution: Initialize Packer first
packer init .
```

### Issue: "Docker daemon not running"
```bash
# Solution: Start Docker
sudo systemctl start docker
# OR
docker run hello-world
```

### Issue: "Permission denied"
```bash
# Solution: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Issue: Build too slow
```bash
# First build is slow (downloads packages)
# Use -var to customize and skip unnecessary packages
# Check disk space: df -h
# Monitor build: watch -n 5 "du -sh output/"
```

### Issue: Out of disk space
```bash
# Clean up Packer cache and artifacts
rm -rf packer_cache output/
# Free up space, then try again
```

---

## 📚 Additional Resources

### Official Documentation
- [Packer Install](https://developer.hashicorp.com/packer/install)
- [Packer Tutorials](https://developer.hashicorp.com/packer/tutorials)
- [Packer AWS Guide](https://developer.hashicorp.com/packer/tutorials/aws)
- [Packer Docker Guide](https://developer.hashicorp.com/packer/tutorials/docker)
- [HCL2 Language](https://developer.hashicorp.com/packer/guides/hcl)

### Example Projects
- [DigiPowerX Packer Images](https://github.com/lakshmojizelar/digipowerx-packer-images)
  - Professional NVIDIA GPU ISO creation
  - Offline installation media
  - Complete build pipeline

### Community
- [Packer GitHub Issues](https://github.com/hashicorp/packer/issues)
- [Packer Discussions](https://discuss.hashicorp.com/c/packer)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/packer)

---

## 🤝 Contributing

Found an issue or want to improve this guide?

1. Check existing documentation
2. Create detailed examples
3. Share your templates
4. Document what worked for you

---

## 📄 License

This documentation is provided as-is for educational purposes. Refer to HashiCorp Packer's license for terms.

---

## ✨ Next Steps

1. **Read** [PACKER_SETUP_GUIDE.md](PACKER_SETUP_GUIDE.md) for detailed installation
2. **Run** `./PACKER_INSTALL.sh` to set up your system
3. **Follow** [PACKER_EXAMPLES.md](PACKER_EXAMPLES.md) to build your first image
4. **Reference** [PACKER_QUICK_REFERENCE.md](PACKER_QUICK_REFERENCE.md) as you work
5. **Build** custom images for your use cases!

---

**Last Updated:** November 2024\
**Packer Version:** 1.10.0+\
**Maintained for:** Ubuntu 22.04+, macOS 10.12+, Generic Linux
