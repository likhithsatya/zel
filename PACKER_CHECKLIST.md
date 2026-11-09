# Packer Setup Checklist

**Step-by-step checklist to get Packer installed and build your first custom image.**

---

## Pre-Installation

- [ ] **Check OS**: Running Ubuntu/Debian, macOS, or other Linux?
- [ ] **Check disk space**: At least 15 GB free disk space
- [ ] **Check internet**: Have a stable internet connection
- [ ] **Root/sudo**: Ready to enter your password for Linux installations

---

## Installation

### Option 1: Automated Installation (Recommended for Linux/macOS)

- [ ] Read the PACKER_SETUP_GUIDE.md file
- [ ] Make the script executable: `chmod +x PACKER_INSTALL.sh`
- [ ] Run the installer: `./PACKER_INSTALL.sh`
- [ ] Follow the on-screen prompts
- [ ] Check the log: `cat packer-install.log`

### Option 2: Manual Installation

**Linux (Ubuntu/Debian)**
- [ ] Add GPG key: `wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg`
- [ ] Add repository: `echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list`
- [ ] Update packages: `sudo apt update`
- [ ] Install Packer: `sudo apt install packer`

**macOS**
- [ ] Install Homebrew (if not already): https://brew.sh
- [ ] Add tap: `brew tap hashicorp/tap`
- [ ] Install Packer: `brew install hashicorp/tap/packer`

**Other OS**
- [ ] Visit: https://developer.hashicorp.com/packer/install
- [ ] Download binary for your OS
- [ ] Add to PATH

---

## Verification

- [ ] Verify Packer installed: `packer version`
  - Should output: `Packer v1.x.x`
- [ ] Verify Docker (optional, for Docker images): `docker --version`
- [ ] Verify QEMU (optional, for VM images): `qemu-system-x86_64 --version`

---

## Learn the Basics

### Read Documentation

- [ ] Read [PACKER_README.md](PACKER_README.md) - Overview
- [ ] Read [PACKER_SETUP_GUIDE.md](PACKER_SETUP_GUIDE.md) - Complete guide
- [ ] Read [PACKER_QUICK_REFERENCE.md](PACKER_QUICK_REFERENCE.md) - Syntax reference
- [ ] Skim [PACKER_EXAMPLES.md](PACKER_EXAMPLES.md) - Template examples

### Understand Concepts

- [ ] Know what a "source" is (Docker, AWS, QEMU, etc.)
- [ ] Know what a "provisioner" is (shell, file, ansible, etc.)
- [ ] Know what a "post-processor" is (docker-tag, docker-push, etc.)
- [ ] Understand the HCL2 template structure

---

## Set Up Your First Project

### Create Project Directory

- [ ] Create directory: `mkdir ~/packer-project && cd ~/packer-project`
- [ ] Create subdirectories:
  ```bash
  mkdir -p packer scripts output
  ```

### Copy Example Template

- [ ] Copy from PACKER_EXAMPLES.md: "Simple Docker Image" template
- [ ] Save as: `packer/simple.pkr.hcl`
- [ ] Review the template, understand each section

### Prepare Build Environment

- [ ] Ensure Docker is running: `docker ps` (should not error)
- [ ] Ensure internet connection is stable
- [ ] Check disk space: `df -h` (verify 15+ GB available)

---

## Build Your First Image

### Step 1: Initialize Packer

- [ ] Run: `packer init .` (from project directory)
- [ ] Should download Docker plugin

### Step 2: Validate Template

- [ ] Run: `packer validate packer/simple.pkr.hcl`
- [ ] Should output: "The configuration is valid."
- [ ] If errors, fix them and rerun

### Step 3: Build Image

- [ ] Run: `packer build packer/simple.pkr.hcl`
- [ ] Watch the build progress
- [ ] Image should build in 2-5 minutes
- [ ] Output should show success and image name

### Step 4: Verify Image

- [ ] List Docker images: `docker images | grep my-custom`
- [ ] Should see your custom image
- [ ] Run container: `docker run --rm my-custom/ubuntu:latest echo "Hello!"`
- [ ] Should output: "Hello!"

---

## Try Advanced Examples

### Docker with Provisioners

- [ ] Copy "Docker Image with Multiple Provisioners" from PACKER_EXAMPLES.md
- [ ] Create dummy app directory: `mkdir -p app && echo 'print("test")' > app/app.py`
- [ ] Create setup script: `scripts/install.sh`
- [ ] Run: `packer build advanced-docker.pkr.hcl`
- [ ] Verify: `docker run my-custom/myapp:latest python3 /opt/myapp/app.py`

### AWS AMI (if you have AWS credentials)

- [ ] Configure AWS: `aws configure`
- [ ] Copy "AWS EC2 AMI" template from PACKER_EXAMPLES.md
- [ ] Review AWS variables (region, instance type)
- [ ] Run: `packer build aws-ami.pkr.hcl`
- [ ] Check AWS Console for new AMI

### QEMU Image (if QEMU installed)

- [ ] Verify QEMU: `qemu-system-x86_64 --version`
- [ ] Copy "QEMU/KVM Disk Image" template from PACKER_EXAMPLES.md
- [ ] Run: `packer build qemu-image.pkr.hcl`
- [ ] Verify output: `ls -lh output/qemu-ubuntu/`

---

## Customize a Build

### Using Variables

- [ ] Create a variables file: `vars.pkrvars.hcl`
- [ ] Add variables:
  ```hcl
  base_image = "ubuntu:22.04"
  packages = ["curl", "wget", "git", "docker.io"]
  app_version = "2.0"
  ```
- [ ] Build with variables: `packer build -var-file=vars.pkrvars.hcl template.pkr.hcl`

### Using CLI Overrides

- [ ] Build with custom values:
  ```bash
  packer build \
    -var 'base_image=ubuntu:20.04' \
    -var 'app_version=3.0' \
    template.pkr.hcl
  ```

### Adding Provisioners

- [ ] Add shell provisioner to install software
- [ ] Add file provisioner to copy config files
- [ ] Test after each modification: `packer validate`, then `packer build`

---

## Real-World: Build NVIDIA GPU ISO

### Prerequisites

- [ ] Clone repo: `git clone https://github.com/lakshmojizelar/digipowerx-packer-images.git`
- [ ] Change directory: `cd digipowerx-packer-images`
- [ ] Verify disk space: `df -h` (need 25+ GB)

### Initial Setup

- [ ] Run: `make deps` (installs system dependencies)
- [ ] Run: `make init` (downloads Packer plugins)
- [ ] Verify: `packer version` (should be >= 1.10.0)

### Configuration

- [ ] Generate password: `openssl passwd -6 'YourPassword'`
- [ ] Edit: `iso/nvidia-autoinstall/user-data`
- [ ] Paste password hash in `identity.password`
- [ ] Change `username` if desired
- [ ] Add SSH keys in `ssh.authorized-keys` if available

### Build

- [ ] Validate: `make validate`
- [ ] Build (first time takes 20-30 min): `make nvidia-iso`
- [ ] Check output: `ls -lh output/ubuntu-24.04.5-nvidia580.iso`
- [ ] Verify checksum: `sha256sum -c output/ubuntu-24.04.5-nvidia580.iso.sha256`

### Test (Optional)

- [ ] Test in VM (requires QEMU): `make nvidia-test`
- [ ] Should output: "PASS" at the end

### Deploy

- [ ] Write to USB: `sudo dd if=output/ubuntu-24.04.5-nvidia580.iso of=/dev/sdX bs=4M`
- [ ] Boot from USB on target server
- [ ] Answer "yes" to autoinstall
- [ ] System reboots when done

---

## Troubleshooting

### If: Packer command not found
- [ ] Check PATH: `echo $PATH`
- [ ] Reinstall: See Installation section
- [ ] Verify: `which packer`

### If: Docker image build fails
- [ ] Check Docker: `docker run hello-world`
- [ ] Start Docker: `sudo systemctl start docker`
- [ ] Check disk: `df -h` (need free space)

### If: Build is too slow
- [ ] First build is always slow (downloads packages)
- [ ] Subsequent builds are faster (cached)
- [ ] Check internet: `ping 8.8.8.8`
- [ ] Monitor disk: `watch -n 5 "du -sh output/"`

### If: AWS build fails
- [ ] Check credentials: `aws sts get-caller-identity`
- [ ] Check region: `aws ec2 describe-regions`
- [ ] Verify IAM permissions

### If: QEMU build fails
- [ ] Check QEMU: `qemu-system-x86_64 --version`
- [ ] Verify KVM: `kvm-ok`
- [ ] Enable KVM if needed: `sudo modprobe kvm_intel`

---

## Next Steps After Building

### 1. Test Your Image

- [ ] Run locally: `docker run -it my-image /bin/bash`
- [ ] Test functionality: Verify installed packages and services
- [ ] Check logs: Review any build output for errors

### 2. Document Your Build

- [ ] Create README: Explain what the image contains
- [ ] Document variables: List all customizable options
- [ ] Note dependencies: List required tools and disk space

### 3. Automate Builds

- [ ] Set up Git repository
- [ ] Create `.gitignore` for large artifacts
- [ ] Add CI/CD workflow (GitHub Actions, GitLab CI, etc.)
- [ ] Trigger builds on commit or schedule

### 4. Share Your Images

**Docker Hub**
- [ ] Create account: https://hub.docker.com
- [ ] Login locally: `docker login`
- [ ] Tag image: `docker tag my-image:latest username/my-image:latest`
- [ ] Push: `docker push username/my-image:latest`

**AWS**
- [ ] Make AMI public (if desired)
- [ ] Create AMI launch template
- [ ] Document in runbook

**Private Registry**
- [ ] Set up private Docker registry
- [ ] Configure authentication
- [ ] Push images to private registry

---

## Common Commands Reference

```bash
# Installation
packer version                    # Verify Packer installed
packer init .                     # Download plugins

# Template management
packer validate template.pkr.hcl  # Check syntax
packer inspect template.pkr.hcl   # Show template details
packer fmt template.pkr.hcl       # Format HCL2 code

# Building
packer build template.pkr.hcl     # Build with defaults
packer build -var 'key=value' ... # Build with variables
packer build -var-file=vars.pkrvars.hcl ...  # Build with variable file
packer build -debug ...           # Build with debugging paused

# Cleanup
rm -rf packer_cache               # Remove downloaded plugins
rm -rf output                      # Remove built artifacts
docker image rm my-image          # Remove Docker image
```

---

## Success Checklist

- [ ] Packer installed and verified
- [ ] First Docker image built successfully
- [ ] Second template built with customization
- [ ] Variables used to customize builds
- [ ] At least one advanced template tested
- [ ] Understand the full Packer workflow
- [ ] Ready to build custom images for production

---

## Resources to Bookmark

- [ ] [Packer Documentation](https://developer.hashicorp.com/packer)
- [ ] [Packer GitHub](https://github.com/hashicorp/packer)
- [ ] [DigiPowerX Packer Images](https://github.com/lakshmojizelar/digipowerx-packer-images)
- [ ] [Local Guides](./PACKER_QUICK_REFERENCE.md)

---

## Get Help

| Issue | Resources |
|-------|-----------|
| General questions | [Packer Tutorials](https://developer.hashicorp.com/packer/tutorials) |
| Syntax help | [PACKER_QUICK_REFERENCE.md](PACKER_QUICK_REFERENCE.md) |
| Template examples | [PACKER_EXAMPLES.md](PACKER_EXAMPLES.md) |
| Installation issues | [PACKER_SETUP_GUIDE.md](PACKER_SETUP_GUIDE.md#troubleshooting) |
| Specific tool | [HashiCorp Discuss](https://discuss.hashicorp.com/c/packer) |

---

**Estimated Completion Time:** 2-4 hours total
- Installation: 10-20 minutes
- Learning basics: 30-60 minutes
- First build: 5-10 minutes
- Advanced examples: 1-2 hours

**You're ready to build custom images! 🚀**

---

**Last Updated:** November 2024
