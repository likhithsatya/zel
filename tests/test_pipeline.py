import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]


class BundleTests(unittest.TestCase):
    def test_template_bundle_matches_documented_boot_flow(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bundle"
            subprocess.run(
                [sys.executable, str(ROOT / "scripts/prepare_pxe.py"), "--template", "--output", str(output)],
                check=True,
                cwd=ROOT,
            )
            ipxe = (output / "boot.ipxe").read_text(encoding="utf-8")
            self.assertIn("ip=dhcp fb=false", ipxe)
            self.assertIn("autoinstall ds=nocloud-net\\;s=${tenant-cloudinit-url}", ipxe)
            self.assertIn("console=tty0 console=ttyS1,115200", ipxe)
            self.assertIn("__PXE_BASE_URL__", ipxe)
            self.assertNotIn("10.11.1.99", ipxe)

            user_data = yaml.safe_load((output / "seed/user-data").read_text(encoding="utf-8").removeprefix("#cloud-config\n"))
            install = user_data["autoinstall"]
            self.assertEqual(install["storage"]["layout"]["name"], "direct")
            self.assertTrue(install["network"]["ethernets"]["pxe"]["dhcp4"])
            self.assertEqual(install["identity"]["password"], "!")
            self.assertFalse(install["ssh"]["allow-pw"])
            self.assertEqual(install["ssh"]["authorized-keys"], ["__SSH_AUTHORIZED_KEY__"])
            self.assertTrue((output / "scripts/validate-gpu.sh").is_file())
            self.assertEqual(yaml.safe_load((output / "seed/meta-data").read_text())["instance-id"], "__INSTALL_HOSTNAME__")

    def test_release_version_override_is_manifested(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bundle"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/prepare_pxe.py"),
                    "--template",
                    "--artifact-version",
                    "1.2.3",
                    "--output",
                    str(output),
                ],
                check=True,
                cwd=ROOT,
            )
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["artifact_version"], "1.2.3")

    def test_gpu_installers_fail_closed_by_default(self):
        for name in (
            "setup-nvidia-repo.sh",
            "install-nvidia-driver.sh",
            "install-fabric-manager.sh",
            "install-cuda.sh",
            "install-custom-image-stack.sh",
        ):
            result = subprocess.run(
                ["bash", str(ROOT / "drivers" / name)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("GPU installation is disabled", result.stderr)

    def test_custom_iso_prompts_and_keeps_gpu_install_in_image_scope(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_custom_iso import prepare_overlay

        with tempfile.TemporaryDirectory() as temporary:
            overlay = Path(temporary)
            prepare_overlay(overlay, "$6$test-only-random-hash")
            seed = yaml.safe_load((overlay / "autoinstall/user-data").read_text())["autoinstall"]
            self.assertEqual(seed["interactive-sections"], ["identity", "storage", "ssh"])
            self.assertEqual(seed["identity"]["password"], "$6$test-only-random-hash")
            self.assertEqual(seed["ssh"]["allow-pw"], False)
            image_config = yaml.safe_load((overlay / "nvidia-b300/config/versions.yml").read_text())
            repo_config = yaml.safe_load((ROOT / "config/versions.yml").read_text())
            self.assertTrue(image_config["gpu_stack"]["enabled"])
            self.assertTrue(image_config["gpu_stack"]["installation_authorized"])
            self.assertFalse(repo_config["gpu_stack"]["enabled"])
            self.assertTrue((overlay / "nvidia-b300/drivers/install-custom-image-stack.sh").is_file())

    def test_custom_iso_grub_uses_local_seed_and_preserves_kernel_separator(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_custom_iso import patch_grub_config

        source = (
            'set timeout=30\n'
            'menuentry "Try or Install Ubuntu Server" {\n'
            '        linux /casper/vmlinuz  ---\n'
            '        initrd /casper/initrd\n'
            '}\n'
            'menuentry "Ubuntu Server with the HWE kernel" {\n'
            '        linux /casper/hwe-vmlinuz  ---\n'
            '        initrd /casper/hwe-initrd\n'
            '}\n'
        )
        grub = patch_grub_config(source)
        self.assertIn('menuentry "Install Ubuntu 24.04.3 with NVIDIA data-center software"', grub)
        self.assertEqual(grub.count(r"ds=nocloud\;s=/cdrom/autoinstall/"), 2)
        self.assertEqual(grub.count(" ---"), 2)
        self.assertNotRegex(grub, r"(?m)^\s*grub_platform\s*$")

    def test_release_iso_split_and_reassembly_preserves_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            iso = root / "nvidia-b300-ubuntu-24.04.3-r620.iso"
            payload = bytes(range(256)) * 32
            iso.write_bytes(payload)
            (root / f"{iso.name}.sha256").write_text(
                f"{hashlib.sha256(payload).hexdigest()}  {iso.name}\n", encoding="utf-8"
            )
            (root / f"{iso.name}.manifest.json").write_text("{}\n", encoding="utf-8")
            assets = root / "assets"
            subprocess.run(
                ["bash", str(ROOT / "scripts/split-release-iso.sh"), str(iso), str(assets)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            restored = root / "restored.iso"
            subprocess.run(
                ["bash", str(assets / "assemble-release-iso.sh"), str(assets), str(restored)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(restored.read_bytes(), payload)

    def test_manifest_and_checksum_file_cover_generated_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bundle"
            subprocess.run(
                [sys.executable, str(ROOT / "scripts/prepare_pxe.py"), "--template", "--output", str(output)],
                check=True,
                cwd=ROOT,
            )
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["ubuntu_version"], "24.04.3")
            self.assertFalse(manifest["gpu_stack_enabled"])
            self.assertEqual(manifest["artifact_version"], "0.1.0")
            self.assertEqual(manifest["gpu_stack"]["driver"]["version"], "620.70.06")
            self.assertEqual(manifest["gpu_stack"]["cuda"]["version"], "13.5")
            self.assertEqual(manifest["gpu_stack"]["fabric_manager"]["version"], "2.0.0.rel106")
            self.assertEqual(manifest["gpu_stack"]["hardware_validation"], "not_performed")
            for name, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
            subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=output, check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()