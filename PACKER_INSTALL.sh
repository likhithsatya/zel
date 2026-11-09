#!/bin/bash
# Packer Installation and Setup Script
# Supports: Linux (Ubuntu/Debian), macOS, and basic validation for all systems

set -e

PACKER_VERSION=">=1.10.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/packer-install.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[✓]${NC} $*" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[!]${NC} $*" | tee -a "$LOG_FILE"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            OS_VERSION=$VERSION_ID
        else
            error "Cannot detect Linux distribution"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        OS_VERSION=$(sw_vers -productVersion)
    else
        error "Unsupported OS: $OSTYPE"
    fi

    log "Detected OS: $OS ($OS_VERSION)"
}

# Install on Ubuntu/Debian
install_linux() {
    log "Installing Packer on $OS..."

    # Check if running as root or with sudo
    if [[ $EUID -ne 0 ]]; then
        error "Linux installation requires sudo. Please run: sudo bash $0"
    fi

    log "Adding HashiCorp GPG key..."
    wget -O - https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
    success "GPG key added"

    log "Adding HashiCorp repository..."
    CODENAME=$(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs)
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $CODENAME main" | tee /etc/apt/sources.list.d/hashicorp.list
    success "Repository added"

    log "Updating package lists..."
    apt-get update

    log "Installing Packer..."
    apt-get install -y packer
    success "Packer installed"

    # Install optional dependencies
    log "Installing optional dependencies..."
    apt-get install -y docker.io qemu-system-x86 qemu-utils xorriso python3-yaml 2>/dev/null || {
        warning "Some optional packages could not be installed, but Packer should work"
    }
}

# Install on macOS
install_macos() {
    log "Installing Packer on macOS..."

    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        error "Homebrew not found. Please install it first: https://brew.sh"
    fi

    log "Adding HashiCorp tap..."
    brew tap hashicorp/tap
    success "Tap added"

    log "Installing Packer..."
    brew install hashicorp/tap/packer
    success "Packer installed"

    # Install optional dependencies
    log "Installing optional dependencies..."
    brew install qemu xorriso python-yaml 2>/dev/null || {
        warning "Some optional packages could not be installed, but Packer should work"
    }
}

# Verify installation
verify_installation() {
    log "Verifying Packer installation..."

    if ! command -v packer &> /dev/null; then
        error "Packer installation failed or not in PATH"
    fi

    INSTALLED_VERSION=$(packer version | grep -oP 'Packer v\K[0-9.]+')
    success "Packer installed: v$INSTALLED_VERSION"

    # Check for Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        success "Docker found: $DOCKER_VERSION"
    else
        warning "Docker not found. Install for building Docker images: https://docs.docker.com/install"
    fi

    # Check for QEMU
    if command -v qemu-system-x86_64 &> /dev/null; then
        success "QEMU found for building VM images"
    else
        warning "QEMU not found. Install for building QEMU/KVM images"
    fi
}

# Initialize Packer
init_packer() {
    log "Initializing Packer..."

    if [ -f "$SCRIPT_DIR/packer/example.pkr.hcl" ] || [ -f "$SCRIPT_DIR/example.pkr.hcl" ]; then
        cd "$SCRIPT_DIR"
        packer init . 2>/dev/null || {
            warning "No Packer configuration found to initialize. You can create one later."
        }
    else
        log "No Packer templates found to initialize yet"
    fi
}

# Create example template
create_example() {
    log "Creating example Packer template..."

    EXAMPLE_FILE="$SCRIPT_DIR/example-simple.pkr.hcl"

    if [ -f "$EXAMPLE_FILE" ]; then
        log "Example already exists at $EXAMPLE_FILE"
        return
    fi

    cat > "$EXAMPLE_FILE" << 'EOF'
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
  name    = "example-image"
  sources = ["source.docker.example"]

  provisioner "shell" {
    inline = [
      "apt-get update",
      "apt-get install -y curl wget git",
      "echo 'Custom image built successfully!'",
      "apt-get clean"
    ]
  }

  post-processor "docker-tag" {
    repository = "my-custom/ubuntu"
    tags       = ["latest"]
  }
}
EOF

    success "Example template created at $EXAMPLE_FILE"
}

# Main installation flow
main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          Packer Installation and Setup Script             ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    log "Starting Packer installation..."
    log "Log file: $LOG_FILE"
    echo ""

    detect_os

    # Install based on OS
    case $OS in
        ubuntu|debian)
            install_linux
            ;;
        macos)
            install_macos
            ;;
        *)
            warning "Automatic installation not supported for $OS"
            echo "Please install Packer manually from: https://developer.hashicorp.com/packer/install"
            ;;
    esac

    echo ""
    verify_installation

    echo ""
    init_packer

    echo ""
    create_example

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         Installation Complete!${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"

    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Verify installation:"
    echo "   packer version"
    echo ""
    echo "2. Build the example image:"
    echo "   cd $SCRIPT_DIR"
    echo "   packer init ."
    echo "   packer build example-simple.pkr.hcl"
    echo ""
    echo "3. Read the guides:"
    echo "   cat $SCRIPT_DIR/PACKER_SETUP_GUIDE.md"
    echo "   cat $SCRIPT_DIR/PACKER_EXAMPLES.md"
    echo ""
    echo "4. Check documentation:"
    echo "   https://developer.hashicorp.com/packer/tutorials"
    echo "   https://github.com/lakshmojizelar/digipowerx-packer-images"
    echo ""

    log "Installation completed successfully!"
}

# Handle errors
trap 'error "Installation failed. Check $LOG_FILE for details."' ERR

# Run main function
main "$@"
