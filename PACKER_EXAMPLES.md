# Packer Custom Image Examples

This document contains practical, copy-paste-ready Packer templates for building custom images.

---

## Table of Contents

1. [Simple Docker Image](#simple-docker-image)
2. [Docker Image with Multiple Provisioners](#docker-image-with-multiple-provisioners)
3. [AWS EC2 AMI](#aws-ec2-ami)
4. [QEMU/KVM Disk Image](#qemukvm-disk-image)
5. [Ubuntu ISO with Custom Packages](#ubuntu-iso-with-custom-packages)
6. [Production-Ready Image with Validation](#production-ready-image-with-validation)

---

## Simple Docker Image

**File:** `simple-docker.pkr.hcl`

```hcl
packer {
  required_plugins {
    docker = {
      source  = "github.com/hashicorp/docker"
      version = "~> 1.0"
    }
  }
}

# Define the Docker base image
source "docker" "ubuntu" {
  image   = "ubuntu:24.04"
  pull    = true
  discard = true  # Don't keep intermediate containers
}

build {
  name    = "simple-ubuntu"
  sources = ["source.docker.ubuntu"]

  # Install basic tools
  provisioner "shell" {
    inline = [
      "apt-get update",
      "apt-get install -y curl wget git htop",
      "apt-get clean"
    ]
  }

  # Tag the final Docker image
  post-processor "docker-tag" {
    repository = "my-custom/ubuntu"
    tags       = ["latest", "24.04"]
  }
}
```

**Build it:**
```bash
packer init .
packer validate simple-docker.pkr.hcl
packer build simple-docker.pkr.hcl
docker images | grep my-custom/ubuntu
docker run my-custom/ubuntu:latest curl --version
```

---

## Docker Image with Multiple Provisioners

**File:** `advanced-docker.pkr.hcl`

```hcl
packer {
  required_plugins {
    docker = {
      source  = "github.com/hashicorp/docker"
      version = "~> 1.0"
    }
  }
}

variable "app_name" {
  type    = string
  default = "myapp"
}

variable "docker_registry" {
  type    = string
  default = "docker.io"
}

locals {
  image_name = "${var.docker_registry}/likhithsatya/${var.app_name}"
}

source "docker" "app" {
  image   = "ubuntu:24.04"
  pull    = true
  discard = true
}

build {
  name    = var.app_name
  sources = ["source.docker.app"]

  # Stage 1: Update and install system packages
  provisioner "shell" {
    inline = [
      "apt-get update",
      "apt-get upgrade -y",
      "apt-get install -y curl wget git build-essential python3 python3-pip",
      "apt-get clean",
      "rm -rf /var/lib/apt/lists/*"
    ]
  }

  # Stage 2: Copy application files
  provisioner "file" {
    source      = "app/"
    destination = "/opt/${var.app_name}"
  }

  # Stage 3: Run installation script
  provisioner "shell" {
    script = "scripts/install.sh"
    environment_vars = [
      "APP_HOME=/opt/${var.app_name}",
      "APP_NAME=${var.app_name}"
    ]
  }

  # Stage 4: Health check - ensure app is working
  provisioner "shell" {
    inline = [
      "echo 'Testing application...'",
      "test -f /opt/${var.app_name}/app.py || exit 1",
      "python3 /opt/${var.app_name}/app.py --version || true"
    ]
  }

  # Stage 5: Create metadata
  provisioner "file" {
    content     = "Built on: $(date -u +'%Y-%m-%dT%H:%M:%SZ')\nApp: ${var.app_name}\n"
    destination = "/etc/image-metadata.txt"
  }

  # Post-processor: Tag and push
  post-processor "docker-tag" {
    repository = local.image_name
    tags       = ["latest", "v1.0", "build-${uuidv4()}"]
  }
}
```

**Build it:**
```bash
packer init .
packer build advanced-docker.pkr.hcl
packer build -var 'app_name=myservice' advanced-docker.pkr.hcl
```

---

## AWS EC2 AMI

**File:** `aws-ami.pkr.hcl`

```hcl
packer {
  required_plugins {
    amazon = {
      source  = "github.com/hashicorp/amazon"
      version = "~> 1.0"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "ami_name" {
  type    = string
  default = "my-custom-ubuntu-24"
}

source "amazon-ebs" "ubuntu" {
  ami_name        = var.ami_name
  instance_type   = var.instance_type
  region          = var.aws_region

  # Ubuntu 24.04 LTS AMI (x86_64)
  source_ami_filter {
    filters = {
      name                = "ubuntu/images/hvm-ssd2/ubuntu-noble-24.04-amd64-server-*"
      virtualization-type = "hvm"
      root-device-type    = "ebs"
    }
    most_recent = true
    owners      = ["099720109477"]  # Canonical's AWS account
  }

  # Security group (optional, allows SSH)
  security_group_filter {
    filters = {
      group-name = "default"
    }
  }

  # Tag the AMI
  tags = {
    Name        = var.ami_name
    BuildDate   = timestamp()
    BuildBy     = "Packer"
    OS          = "Ubuntu 24.04 LTS"
  }

  # Snapshot tags
  snapshot_tags = {
    Name = "${var.ami_name}-snapshot"
  }
}

build {
  name    = "aws-ubuntu-custom"
  sources = ["source.amazon-ebs.ubuntu"]

  # Wait for cloud-init to finish
  provisioner "shell" {
    inline = ["cloud-init status --wait"]
  }

  # Update system
  provisioner "shell" {
    inline = [
      "sudo apt-get update",
      "sudo apt-get upgrade -y",
      "sudo apt-get install -y docker.io curl wget git jq",
      "sudo systemctl enable docker"
    ]
  }

  # Configure Docker
  provisioner "shell" {
    script = "setup-docker.sh"
  }

  # Cleanup
  provisioner "shell" {
    inline = [
      "sudo apt-get clean",
      "sudo rm -rf /tmp/*"
    ]
  }
}
```

**Build it:**
```bash
packer init .
# Ensure AWS credentials are configured
aws configure
packer build aws-ami.pkr.hcl
packer build -var 'aws_region=us-west-2' aws-ami.pkr.hcl
```

---

## QEMU/KVM Disk Image

**File:** `qemu-image.pkr.hcl`

```hcl
packer {
  required_plugins {
    qemu = {
      source  = "github.com/hashicorp/qemu"
      version = "~> 1.0"
    }
  }
}

variable "disk_size" {
  type    = string
  default = "5000"  # MB
}

variable "memory" {
  type    = string
  default = "2048"  # MB
}

variable "cpus" {
  type    = string
  default = "2"
}

source "qemu" "ubuntu" {
  iso_url           = "https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img"
  iso_checksum      = "file:https://cloud-images.ubuntu.com/releases/24.04/release/SHA256SUMS"
  iso_storage_path  = "packer_cache"

  output_directory  = "output/qemu-ubuntu"
  vm_name           = "ubuntu-24.04.qcow2"
  disk_size         = var.disk_size
  format            = "qcow2"

  accelerator       = "kvm"
  cpu_model         = "host"
  memory            = var.memory
  cpus              = var.cpus

  # Network
  net_device        = "virtio-net"
  disk_interface    = "virtio"

  # Firmware
  firmware          = "/usr/share/ovmf/OVMF.fd"
  machine_type      = "q35"

  # SSH
  ssh_username      = "ubuntu"
  ssh_password      = "ubuntu"
  ssh_timeout       = "5m"
  shutdown_command  = "echo 'ubuntu' | sudo -S shutdown -P now"

  boot_wait         = "10s"
}

build {
  name    = "qemu-ubuntu"
  sources = ["source.qemu.ubuntu"]

  provisioner "shell" {
    inline = [
      "sudo apt-get update",
      "sudo apt-get upgrade -y",
      "sudo apt-get install -y curl wget git",
      "sudo apt-get clean"
    ]
  }
}
```

**Build it:**
```bash
sudo systemctl start libvirtd
packer init .
packer build qemu-image.pkr.hcl
ls -lh output/qemu-ubuntu/
```

---

## Ubuntu ISO with Custom Packages

**File:** `ubuntu-iso.pkr.hcl`

```hcl
packer {
  required_version = ">= 1.10.0"
  required_plugins {
    docker = {
      source  = "github.com/hashicorp/docker"
      version = ">= 1.0"
    }
  }
}

variable "ubuntu_version" {
  type    = string
  default = "24.04.5"
}

variable "iso_name" {
  type    = string
  default = "custom-ubuntu"
}

variable "custom_packages" {
  type    = list(string)
  default = ["curl", "wget", "git", "htop", "vim"]
}

locals {
  iso_url       = "https://releases.ubuntu.com/${var.ubuntu_version}/ubuntu-${var.ubuntu_version}-live-server-amd64.iso"
  output_name   = "${var.iso_name}-${var.ubuntu_version}.iso"
  repo_dir      = "${abspath(path.root)}/custom-packages"
  cache_dir     = "${abspath(path.root)}/cache"
}

source "docker" "ubuntu" {
  image   = "ubuntu:24.04"
  pull    = true
  discard = true
  volumes = {
    (local.repo_dir) = "/opt/packages"
  }
}

build {
  name    = "ubuntu-iso"
  sources = ["source.docker.ubuntu"]

  # Fetch ISO
  provisioner "shell-local" {
    inline = [
      "mkdir -p ${local.cache_dir} ${local.repo_dir}",
      "cd ${local.cache_dir}",
      "curl -L ${local.iso_url} -o ubuntu-${var.ubuntu_version}-live-server-amd64.iso || test -f ubuntu-${var.ubuntu_version}-live-server-amd64.iso",
      "echo 'ISO cached'"
    ]
    inline_shebang = "/bin/bash -e"
  }

  # Build local package repository
  provisioner "shell" {
    script = "scripts/build-package-repo.sh"
    environment_vars = [
      "PACKAGES=${join(" ", var.custom_packages)}",
      "REPO_OUT=/opt/packages"
    ]
  }

  # Repack ISO with custom packages
  provisioner "shell-local" {
    inline = [
      "cd ${local.cache_dir}",
      "mkdir -p iso-mount iso-work",
      "sudo mount -o loop ubuntu-${var.ubuntu_version}-live-server-amd64.iso iso-mount",
      "cp -rT iso-mount iso-work",
      "cp -r ${local.repo_dir}/* iso-work/packages/",
      "cd iso-work",
      "xorriso -as mkisofs -iso-level 3 -o ../../../${local.output_name} -full-iso9660-filenames -volid Ubuntu .",
      "cd ..",
      "sudo umount iso-mount || true"
    ]
    inline_shebang = "/bin/bash -e"
  }

  # Verify
  provisioner "shell-local" {
    inline = [
      "ls -lh ${abspath(path.root)}/${local.output_name}",
      "echo 'ISO built successfully!'"
    ]
  }
}
```

---

## Production-Ready Image with Validation

**File:** `production.pkr.hcl`

```hcl
packer {
  required_plugins {
    docker = {
      source  = "github.com/hashicorp/docker"
      version = "~> 1.0"
    }
  }
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "registry" {
  type    = string
  default = "docker.io"
}

variable "app_version" {
  type    = string
  default = "1.0.0"
}

source "docker" "app" {
  image   = "ubuntu:24.04"
  pull    = true
  discard = true
}

build {
  name    = "production-app"
  sources = ["source.docker.app"]

  # Stage 1: System setup
  provisioner "shell" {
    inline = [
      "set -e",
      "apt-get update",
      "apt-get install -y --no-install-recommends curl wget ca-certificates",
      "apt-get clean",
      "rm -rf /var/lib/apt/lists/*"
    ]
  }

  # Stage 2: Application
  provisioner "file" {
    source      = "app/"
    destination = "/opt/app"
  }

  provisioner "shell" {
    inline = [
      "cd /opt/app",
      "chmod +x entrypoint.sh",
      "test -f app.py || test -f Dockerfile || exit 1"
    ]
  }

  # Stage 3: Validation - Pre-build tests
  provisioner "shell" {
    inline = [
      "echo 'Running validation tests...'",
      "test -d /opt/app || exit 1",
      "test -f /opt/app/entrypoint.sh || exit 1",
      "curl --version || true",
      "echo 'Validation passed!'"
    ]
  }

  # Stage 4: Metadata and labeling
  provisioner "file" {
    content = templatefile("${path.root}/metadata.json.tpl", {
      version = var.app_version
      date    = formatdate("YYYY-MM-DD hh:mm:ss Z", timestamp())
    })
    destination = "/opt/app/metadata.json"
  }

  # Stage 5: Security hardening
  provisioner "shell" {
    inline = [
      "adduser --system --no-create-home appuser || true",
      "chown -R appuser:nogroup /opt/app"
    ]
  }

  # Post-processor: Tag with metadata
  post-processor "docker-tag" {
    repository = "${var.registry}/likhithsatya/app"
    tags = [
      var.image_tag,
      "v${var.app_version}",
      "build-${regex_replace(timestamp(), "[- TZ:]", "")}"
    ]
  }
}
```

**Build commands:**
```bash
packer init .
packer validate production.pkr.hcl
packer build production.pkr.hcl
packer build -var 'image_tag=v1.2.3' -var 'app_version=1.2.3' production.pkr.hcl
```

---

## Using Variables in Builds

**File:** `variables.pkr.hcl`

```hcl
variable "base_image" {
  type        = string
  default     = "ubuntu:24.04"
  description = "Base Docker image"
}

variable "packages" {
  type        = list(string)
  default     = ["curl", "wget", "git"]
  description = "Packages to install"
}

variable "environment_vars" {
  type        = map(string)
  default     = {}
  description = "Environment variables to set"
}

variable "build_tag" {
  type        = string
  default     = "latest"
  description = "Tag for the built image"
}

locals {
  packages_str = join(" ", var.packages)
}
```

**Build with variables:**
```bash
packer build \
  -var 'base_image=ubuntu:22.04' \
  -var 'packages=["curl","docker.io","nodejs"]' \
  -var 'build_tag=production' \
  template.pkr.hcl
```

---

## Common Provisioning Scripts

### setup-docker.sh
```bash
#!/bin/bash
set -e

# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io

# Add current user to docker group
sudo usermod -aG docker ubuntu

# Enable Docker daemon
sudo systemctl enable docker
sudo systemctl start docker

# Verify
docker --version
```

### install-app.sh
```bash
#!/bin/bash
set -e

APP_HOME=${APP_HOME:-/opt/app}
echo "Installing application to $APP_HOME"

cd $APP_HOME

# Install Python dependencies
if [ -f requirements.txt ]; then
  sudo pip3 install -r requirements.txt
fi

# Run setup
if [ -f setup.py ]; then
  sudo python3 setup.py install
fi

echo "Application installed successfully"
```

---

## Tips and Best Practices

### 1. **Use Variables for Flexibility**
```hcl
variable "package_list" {
  type = list(string)
}

provisioner "shell" {
  inline = ["apt-get install -y ${join(" ", var.package_list)}"]
}
```

### 2. **Cache Large Downloads**
```hcl
provisioner "shell-local" {
  inline = [
    "mkdir -p cache",
    "cd cache",
    "[ -f large-file.tar.gz ] || curl -O https://example.com/large-file.tar.gz"
  ]
}
```

### 3. **Run Tests During Build**
```hcl
provisioner "shell" {
  inline = [
    "python3 -m pytest tests/ || exit 1",
    "echo 'All tests passed!'"
  ]
}
```

### 4. **Clean Up to Reduce Image Size**
```hcl
provisioner "shell" {
  inline = [
    "apt-get clean",
    "apt-get autoclean",
    "rm -rf /var/lib/apt/lists/*",
    "rm -rf /tmp/*",
    "rm -rf /var/tmp/*"
  ]
}
```

### 5. **Use Environment Variables Securely**
```hcl
variable "api_key" {
  type      = string
  sensitive = true
}

provisioner "shell" {
  environment_vars = ["API_KEY=${var.api_key}"]
  inline           = ["echo $API_KEY > ~/.config/app.key"]
}
```

---

**Last Updated:** November 2024
