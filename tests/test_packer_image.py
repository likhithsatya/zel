from pathlib import Path
import sys
import tempfile
import unittest
import hashlib
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_custom_iso import prepare_overlay
from build_packer_qemu import prepare_context


class PackerImageTests(unittest.TestCase):
    def test_packer_payload_opens_gate_only_for_separate_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            payload = prepare_context(Path(temporary))
            image_config = yaml.safe_load((payload / "config/versions.yml").read_text())
            repository_config = yaml.safe_load((ROOT / "config/versions.yml").read_text())
            self.assertTrue(image_config["gpu_stack"]["enabled"])
            self.assertTrue(image_config["gpu_stack"]["installation_authorized"])
            self.assertFalse(repository_config["gpu_stack"]["enabled"])
            self.assertTrue((payload / "config/packages.yml").is_file())
            self.assertTrue((payload / "scripts/packer-cleanup-qemu.sh").is_file())
            self.assertTrue((payload / "scripts/packer-firstboot-nvidia.sh").is_file())

    def test_qemu_template_uses_cloud_image_and_firstboot_gpu_setup(self):
        template = (ROOT / "packer/ubuntu-qemu-b300/b300.pkr.hcl").read_text()
        provisioner = (ROOT / "scripts/packer-provision-qemu.sh").read_text()
        self.assertIn("disk_image       = true", template)
        self.assertIn('cd_label = "cidata"', template)
        self.assertIn("nvidia-b300-firstboot.service", provisioner)
        self.assertNotIn("install-custom-image-stack.sh", provisioner)

    def test_release_assembler_accepts_digipowerx_iso_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            iso = root / "digipowerx-b300-ubuntu-24.04.3-r620.iso"
            contents = b"digipowerx test image\n"
            iso.write_bytes(contents)
            (root / f"{iso.name}.sha256").write_text(
                f"{hashlib.sha256(contents).hexdigest()}  {iso.name}\n", encoding="utf-8"
            )
            (root / f"{iso.name}.manifest.json").write_text("{}\n", encoding="utf-8")
            assets = root / "release-assets"
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
            self.assertEqual(restored.read_bytes(), contents)

    def test_digipowerx_motd_is_staged_for_iso_and_qcow_images(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qcow_payload = prepare_context(root / "qcow")
            iso_overlay = root / "iso"
            prepare_overlay(iso_overlay, "$6$test-only-hash")
            self.assertTrue((qcow_payload / "scripts/motd-digipowerx.sh").is_file())
            self.assertTrue((iso_overlay / "nvidia-b300/scripts/motd-digipowerx.sh").is_file())


if __name__ == "__main__":
    unittest.main()