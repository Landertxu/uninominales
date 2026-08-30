.PHONY: check test vulture install-dev

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v --ignore=tests/test_golden_images.py

vulture:
	vulture src run.py manage.py verify_codes.py scripts/

check: vulture test
