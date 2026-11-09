from pathlib import Path
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

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


if __name__ == "__main__":
    unittest.main()