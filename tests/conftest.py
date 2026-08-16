"""Shared fixtures.

The catalogue and the 815 specs are loaded once per session: they are read-only
and re-reading 815 YAML files per test would dominate the run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from adw.registry import Catalogue, Registry, available_country_packs, load_country_pack  # noqa: E402
from engines.base import all_engines, load_engines  # noqa: E402


@pytest.fixture(scope="session")
def catalogue() -> Catalogue:
    return Catalogue.load()


@pytest.fixture(scope="session")
def registry() -> Registry:
    return Registry.load()


@pytest.fixture(scope="session")
def engines() -> dict:
    load_engines()
    return all_engines()


@pytest.fixture(scope="session")
def country_packs() -> dict:
    return {code: load_country_pack(code) for code in available_country_packs()}
