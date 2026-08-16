.PHONY: help install catalogue packs agents docs build check verify test audit clean

help:
	@echo "make install    - install runtime and dev dependencies"
	@echo "make build      - regenerate catalogue, packs, all 815 specs and the docs"
	@echo "make verify     - end-to-end proof that all 815 units are built and valid"
	@echo "make catalogue  - normalise the workbook into catalogue/"
	@echo "make packs      - regenerate the country packs"
	@echo "make agents     - regenerate the 815 unit specs"
	@echo "make docs       - regenerate the browsable catalogue index"
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

docs:
	python3 tools/build_docs.py

build: catalogue packs agents docs

verify:
	python3 tools/verify_build.py

check:
	python3 tools/build_catalogue.py --check
	python3 tools/generate_agents.py --check

audit:
	python3 -m adw audit

test:
	python3 -m pytest

clean:
	rm -rf .pytest_cache **/__pycache__
