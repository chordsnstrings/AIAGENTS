.PHONY: help install catalogue packs agents build check test audit clean

help:
	@echo "make install    - install runtime and dev dependencies"
	@echo "make build      - regenerate catalogue, country packs and all 815 specs"
	@echo "make catalogue  - normalise the workbook into catalogue/"
	@echo "make packs      - regenerate the country packs"
	@echo "make agents     - regenerate the 815 unit specs"
	@echo "make check      - fail if anything generated is stale"
	@echo "make audit      - run the standing-rule audit over every spec"
	@echo "make test       - run the test suite"

install:
	pip install -e ".[dev]"

catalogue:
	python3 tools/build_catalogue.py

packs:
	python3 tools/build_country_packs.py

agents:
	python3 tools/generate_agents.py

build: catalogue packs agents

check:
	python3 tools/build_catalogue.py --check
	python3 tools/generate_agents.py --check

audit:
	python3 -m adw audit

test:
	python3 -m pytest

clean:
	rm -rf .pytest_cache **/__pycache__
