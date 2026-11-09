packer {
  required_version = ">= 1.10.0"
  required_plugins {
    qemu = {
      source  = "github.com/hashicorp/qemu"
      version = ">= 1.1.0"
    }
  }
}

variable "base_image_url" {
  type = string
}

variable "base_image_checksum" {
  type = string
}

variable "payload_directory" {
  type = string
}

variable "output_directory" {
  type = string
}

variable "build_password_hash" {
  type      = string
  sensitive = true
}

variable "build_password" {
  type      = string
  sensitive = true
}

variable "build_user" {
  type    = string
  default = "packer"
}

variable "image_name" {
  type    = string
  default = "nvidia-b300-ubuntu-24.04.3-r620.qcow2"
}

variable "cpus" {
  type    = number
  default = 2
}

variable "memory_mb" {
  type    = number
  default = 4096
}

variable "disk_size" {
  type    = string
  default = "64G"
}

variable "accelerator" {
  type    = string
  default = "tcg"
}

variable "efi_firmware_code" {
  type    = string
  default = "/usr/share/OVMF/OVMF_CODE_4M.fd"
}

variable "efi_firmware_vars" {
  type    = string
  default = "/usr/share/OVMF/OVMF_VARS_4M.fd"
}

source "qemu" "b300" {
  iso_url          = var.base_image_url
  iso_checksum     = var.base_image_checksum
  disk_image       = true
  output_directory = var.output_directory
  vm_name          = var.image_name
  format           = "qcow2"
  disk_size        = var.disk_size
  disk_compression = true
  disk_interface   = "virtio"
  net_device       = "virtio-net"
  cpus             = var.cpus
  memory           = var.memory_mb
  accelerator      = var.accelerator
  headless         = true

  efi_boot          = true
  efi_firmware_code = var.efi_firmware_code
  efi_firmware_vars = var.efi_firmware_vars

  cd_label = "cidata"
  cd_content = {
    "user-data" = templatefile("${path.root}/cloud-init-user-data.tftpl", {
      build_user          = var.build_user
      build_password_hash = var.build_password_hash
    })
    "meta-data" = "instance-id: nvidia-b300-packer-build\nlocal-hostname: b300-qemu-image\n"
  }

  communicator           = "ssh"
  ssh_username           = var.build_user
  ssh_password           = var.build_password
  ssh_timeout            = "90m"
  ssh_handshake_attempts = 120
  shutdown_command       = "sudo -n /opt/nvidia-b300-qemu/payload/scripts/packer-cleanup-qemu.sh"
}

build {
  name    = "nvidia-b300-qemu"
  sources = ["source.qemu.b300"]

  provisioner "file" {
    source      = var.payload_directory
    destination = "/tmp/nvidia-b300-pxe/"
  }

  provisioner "shell" {
    inline = [
      "sudo -n mkdir -p /opt/nvidia-b300-qemu/payload",
      "sudo -n cp -a /tmp/nvidia-b300-pxe/. /opt/nvidia-b300-qemu/payload/",
      "sudo -n chmod 0755 /opt/nvidia-b300-qemu/payload/drivers/*.sh /opt/nvidia-b300-qemu/payload/scripts/*.sh",
      "sudo -n bash /opt/nvidia-b300-qemu/payload/scripts/packer-provision-qemu.sh",
    ]
  }

  post-processor "checksum" {
    checksum_types = ["sha256"]
    output         = "${var.output_directory}/${var.image_name}.{{ .ChecksumType }}"
  }
}