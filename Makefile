.PHONY: validate test bundle-template image custom-iso smoke-custom-iso report

validate:
	python scripts/validate_config.py
	bash -n scripts/*.sh drivers/*.sh

test:
	python -m unittest discover -s tests -v

bundle-template:
	python scripts/prepare_pxe.py --template --output artifacts/nvidia-b300-pxe-template

image:
	bash scripts/build-deployment-media.sh

custom-iso:
	bash scripts/build-custom-iso.sh

smoke-custom-iso:
	bash scripts/smoke-test-custom-iso.sh artifacts/nvidia-b300-ubuntu-24.04.3-r620.iso

report:
	python scripts/generate_project_report.py