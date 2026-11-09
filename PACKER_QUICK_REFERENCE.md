# Packer Quick Reference Card

**One-page cheat sheet for HashiCorp Packer**

---

## Installation

### Linux (Ubuntu/Debian)
```bash
sudo bash /path/to/PACKER_INSTALL.sh
# OR manual:
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install packer
```

### macOS
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/packer
```

### Verify
```bash
packer version
```

---

## Essential Commands

| Command | Purpose |
|---------|---------|
| `packer init` | Download required plugins |
| `packer validate template.pkr.hcl` | Check syntax and configuration |
| `packer inspect template.pkr.hcl` | Show template details |
| `packer build template.pkr.hcl` | Build the image |
| `packer build -debug template.pkr.hcl` | Build with debug output |
| `packer console` | Interactive HCL2 console |
| `packer fmt template.pkr.hcl` | Format HCL2 code |

---

## HCL2 Template Structure

```hcl
# 1. Declare required Packer and plugins
packer {
  required_version = ">= 1.10.0"
  required_plugins {
    docker = {
      source  = "github.com/hashicorp/docker"
      version = "~> 1.0"
    }
  }
}

# 2. Define variables
variable "image_name" {
  type        = string
  default     = "my-image"
  description = "Name of the image"
  sensitive   = false
}

# 3. Define locals (computed values)
locals {
  full_name = "${var.image_name}-${timestamp()}"
}

# 4. Define sources (where to build)
source "docker" "my_source" {
  image   = "ubuntu:24.04"
  pull    = true
  discard = true
}

# 5. Define build (how to build)
build {
  name    = "example-build"
  sources = ["source.docker.my_source"]

  # Provisioners (shell, file, ansible, etc.)
  provisioner "shell" {
    inline = ["echo 'Hello'"]
  }

  # Post-processors (tag, push, compress, etc.)
  post-processor "docker-tag" {
    repository = "my-image"
    tags       = ["latest"]
  }
}
```

---

## Common Sources (Builders)

### Docker
```hcl
source "docker" "example" {
  image   = "ubuntu:24.04"
  pull    = true
  discard = true  # Don't keep intermediate containers
}
```

### AWS EC2
```hcl
source "amazon-ebs" "example" {
  ami_name      = "my-ami"
  instance_type = "t3.micro"
  region        = "us-east-1"
  source_ami    = "ami-0c55b159cbfafe1f0"
}
```

### QEMU/KVM
```hcl
source "qemu" "example" {
  iso_url      = "https://example.com/image.iso"
  iso_checksum = "file:https://example.com/SHA256SUMS"
  output_directory = "output/"
  vm_name      = "image.qcow2"
  accelerator  = "kvm"
  memory       = "2048"
  cpus         = "2"
}
```

### Azure
```hcl
source "azure-arm" "example" {
  client_id       = var.client_id
  client_secret   = var.client_secret
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
  image_publisher = "Canonical"
  image_offer     = "UbuntuServer"
  image_sku       = "20.04-LTS"
}
```

---

## Provisioners (How to configure)

### Shell
```hcl
provisioner "shell" {
  # Inline commands
  inline = [
    "apt-get update",
    "apt-get install -y curl"
  ]

  # OR from script file
  script = "setup.sh"

  # Environment variables
  environment_vars = ["HOME=/root", "PATH=/usr/local/bin:$PATH"]

  # Only on certain OS
  only = ["source.docker.ubuntu"]
}
```

### Shell-Local
```hcl
provisioner "shell-local" {
  inline_shebang = "/bin/bash -e"
  inline = [
    "echo 'Running on build host'",
    "date > build-time.txt"
  ]
}
```

### File
```hcl
provisioner "file" {
  # Copy files to image
  source      = "local/path/"
  destination = "/tmp/files"

  # OR copy content
  content = "Hello, World!"
  destination = "/tmp/hello.txt"
}
```

### Ansible
```hcl
provisioner "ansible" {
  playbook_file = "playbook.yaml"
  user          = "ubuntu"
  extra_arguments = ["--extra-vars", "env=prod"]
}
```

### Chef
```hcl
provisioner "chef-client" {
  server_url             = "https://chef.example.com"
  node_name              = "web-instance"
  chef_license           = "accept"
  policy_group           = "web"
  policy_name            = "web-base"
}
```

---

## Post-Processors (Finalize output)

### Docker Tag
```hcl
post-processor "docker-tag" {
  repository = "docker.io/myuser/myimage"
  tags       = ["latest", "v1.0"]
}
```

### Docker Push
```hcl
post-processor "docker-push" {
  ecr_login       = true
  aws_region      = "us-east-1"
  docker_username = var.docker_username
  docker_password = var.docker_password
}
```

### Checksum
```hcl
post-processor "checksum" {
  checksum_types = ["sha256", "sha512"]
  output         = "checksums.txt"
}
```

### Compress
```hcl
post-processor "compress" {
  output = "artifacts/image.tar.gz"
}
```

### Manifest
```hcl
post-processor "manifest" {
  output     = "manifest.json"
  strip_path = true
}
```

---

## Variables

### Declaration
```hcl
variable "region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region"
  sensitive   = false
  validation {
    condition     = contains(["us-east-1", "us-west-2"], var.region)
    error_message = "Invalid region"
  }
}
```

### Variable Files
```bash
# Use variables from file
packer build -var-file="vars.pkrvars.hcl" template.pkr.hcl
```

### Variable Content
```hcl
# vars.pkrvars.hcl
region  = "eu-west-1"
env     = "production"
tags    = ["prod", "web"]
```

### CLI Override
```bash
packer build \
  -var 'region=us-west-2' \
  -var 'env=staging' \
  template.pkr.hcl
```

---

## Locals (Computed Values)

```hcl
locals {
  timestamp = regex_replace(timestamp(), "[- TZ:]", "")
  image_id  = "my-image-${local.timestamp}"
  tags = {
    BuildDate = timestamp()
    Builder   = "Packer"
  }
}
```

---

## Functions

### String Functions
```hcl
# Formatting
templatefile("${path.root}/script.sh", { var = "value" })
format("my-%s-image", var.name)

# Regex
regex("^(.+?)-(.+?)$", "ubuntu-24.04")
regex_replace(timestamp(), "[- TZ:]", "")

# Path
file("${path.root}/file.txt")
abspath("./relative/path")
```

### Type Conversions
```hcl
join(",", ["a", "b", "c"])
split(",", "a,b,c")
flatten([["a"], ["b", "c"]])
```

### Conditionals
```hcl
var.enable_docker ? "docker.io" : "localhost:5000"
try(var.optional_value, "default")
```

---

## Environment Variables

```hcl
# In provisioners
provisioner "shell" {
  environment_vars = [
    "DEBUG=true",
    "VERSION=${var.version}",
    "BUILD_TIME=${timestamp()}"
  ]
  inline = ["echo $VERSION"]
}

# From OS
locals {
  home = env("HOME")
}
```

---

## Debugging

### Enable Debug Mode
```bash
packer build -debug template.pkr.hcl
# Pauses after each step, shows available commands
```

### Add Debug Output
```hcl
provisioner "shell" {
  inline = [
    "set -x",  # Enable bash debug
    "echo DEBUG: $HOME",
    "env | sort"
  ]
}
```

### Inspect Intermediate Images
```bash
packer build -on-error=ask template.pkr.hcl
# Pauses on error, lets you inspect container/VM
```

---

## Build with Variables

### Simple
```bash
packer build template.pkr.hcl
```

### With Variables
```bash
packer build \
  -var 'version=2.0' \
  -var 'region=eu-west-1' \
  template.pkr.hcl
```

### From File
```bash
packer build -var-file="prod.pkrvars.hcl" template.pkr.hcl
```

### Multiple Files
```bash
packer build \
  -var-file="defaults.pkrvars.hcl" \
  -var-file="prod.pkrvars.hcl" \
  template.pkr.hcl
```

### Debug Build
```bash
packer build -debug template.pkr.hcl
```

---

## Common Patterns

### Set Hostname
```hcl
provisioner "shell" {
  inline = [
    "echo 'my-host' | sudo tee /etc/hostname",
    "sudo hostname -F /etc/hostname"
  ]
}
```

### Install Docker
```hcl
provisioner "shell" {
  script = "${path.root}/install-docker.sh"
}
```

### Copy Configuration
```hcl
provisioner "file" {
  source      = "config/"
  destination = "/etc/myapp"
}

provisioner "shell" {
  inline = ["sudo chown -R root:root /etc/myapp"]
}
```

### Run Tests
```hcl
provisioner "shell" {
  inline = [
    "test -f /usr/bin/docker || exit 1",
    "docker --version",
    "echo 'Validation passed!'"
  ]
}
```

### Cleanup
```hcl
provisioner "shell" {
  inline = [
    "apt-get clean",
    "apt-get autoclean",
    "rm -rf /var/lib/apt/lists/*",
    "rm -rf /tmp/*"
  ]
}
```

---

## File Locations

| Item | Location |
|------|----------|
| Main template | `template.pkr.hcl` |
| Variables file | `variables.pkr.hcl` or `vars.pkrvars.hcl` |
| Local variables | `locals.pkr.hcl` |
| Build scripts | `scripts/` |
| Config files | `config/` or `files/` |
| Output | `output/` (default) |
| Cache | `packer_cache/` |

---

## Useful Resources

- **Official Docs**: https://developer.hashicorp.com/packer
- **Tutorials**: https://developer.hashicorp.com/packer/tutorials
- **AWS**: https://developer.hashicorp.com/packer/tutorials/aws
- **Docker**: https://developer.hashicorp.com/packer/tutorials/docker
- **GitHub Repo**: https://github.com/lakshmojizelar/digipowerx-packer-images

---

**Last Updated:** November 2024
**Packer Version:** 1.10.0+
