"""Every unit in the catalogue must exist on disk as a complete spec.

The requirement is 815 units built individually -- no sampling, no placeholders,
no stubs.  These tests are what "no placeholders" means concretely: the file
count is exact, every catalogue row has a file, and every file carries real
content in every field a unit needs to run.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from adw.models import UnitType
from adw.registry import AGENTS_DIR, REPO_ROOT

EXPECTED_TOTAL = 815

#: Text that would mean a spec was left unfinished.
PLACEHOLDER_MARKERS = ("TODO", "TBD", "FIXME", "XXX", "PLACEHOLDER", "lorem ipsum", "<insert")


def test_exactly_815_spec_files_on_disk():
    files = list(AGENTS_DIR.rglob("*.yaml"))
    assert len(files) == EXPECTED_TOTAL


def test_registry_loads_all_815(registry):
    assert len(registry) == EXPECTED_TOTAL


def test_every_catalogue_unit_has_a_spec(catalogue, registry):
    catalogue_ids = {u["id"] for u in catalogue.records}
    spec_ids = {u.id for u in registry}
    assert catalogue_ids == spec_ids


def test_every_spec_is_at_its_catalogue_path(catalogue, registry):
    for record in catalogue.records:
        unit = registry.get(record["id"])
        assert unit.path == record["path"], record["id"]
        assert (REPO_ROOT / record["path"]).exists(), record["id"]


def test_type_counts(registry):
    counts = Counter(u.type for u in registry)
    assert counts[UnitType.CORE_WORKER] == 68
    assert counts[UnitType.SPECIALIST] == 355
    assert counts[UnitType.PLAYBOOK_UNIVERSAL] == 92
    assert counts[UnitType.PLAYBOOK_VERTICAL] == 300


def test_no_spec_contains_a_placeholder():
    offenders = []
    for path in AGENTS_DIR.rglob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        for marker in PLACEHOLDER_MARKERS:
            if marker.lower() in text.lower():
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {marker}")
    assert not offenders


def test_every_spec_is_fully_populated(registry):
    """No unit may ship with an empty required field."""
    incomplete = []
    for unit in registry:
        checks = {
            "mission": bool(unit.mission.strip()),
            "function": bool(unit.function.strip()),
            "expected_output": bool(unit.expected_output.strip()),
            "acceptance": bool(unit.acceptance),
            "artifacts": bool(unit.artifacts),
            "plan": bool(unit.plan),
            "guardrails": bool(unit.guardrails),
            "human_gates": bool(unit.human_gates),
            "config_keys": bool(unit.config_keys),
            "capabilities": bool(unit.capabilities),
            "tools": bool(unit.tools),
            "kpis": bool(unit.kpis),
            "inputs": bool(unit.inputs),
        }
        missing = [name for name, ok in checks.items() if not ok]
        if missing:
            incomplete.append(f"{unit.id}: {missing}")
    assert not incomplete


def test_missions_are_substantive(registry):
    """A mission is operating instructions, not a one-liner."""
    thin = [
        u.id
        for u in registry
        if len(u.mission.split()) < 120 or u.mission.count("\n") < 8
    ]
    assert not thin


def test_missions_are_unit_specific(registry):
    """No two units may share a mission verbatim.

    Identical missions would mean the engine templated over the units rather
    than composing from them.
    """
    seen: dict[str, str] = {}
    collisions = []
    for unit in registry:
        existing = seen.get(unit.mission)
        if existing:
            collisions.append(f"{unit.id} == {existing}")
        seen[unit.mission] = unit.id
    assert not collisions


def test_every_mission_names_the_unit_and_its_output(registry):
    wrong = []
    for unit in registry:
        mission = unit.mission
        name = unit.trigger if unit.is_playbook else unit.worker
        if name and name.lower() not in mission.lower():
            wrong.append(f"{unit.id}: mission does not name {name!r}")
        if unit.expected_output.rstrip(".").lower() not in mission.lower():
            wrong.append(f"{unit.id}: mission does not carry the expected output")
    assert not wrong


def test_acceptance_criteria_come_from_the_expected_output(catalogue, registry):
    for record in catalogue.records:
        unit = registry.get(record["id"])
        # Each workbook clause becomes a criterion; the engine adds the audit one.
        assert len(unit.acceptance) == len(record["acceptance_criteria"]) + 1, record["id"]
        for index, clause in enumerate(record["acceptance_criteria"]):
            assert unit.acceptance[index].criterion == clause, record["id"]
            assert unit.acceptance[index].evidence, record["id"]


def test_every_artifact_key_is_unique_within_a_unit(registry):
    offenders = []
    for unit in registry:
        keys = [a.key for a in unit.artifacts]
        if len(keys) != len(set(keys)):
            offenders.append(unit.id)
    assert not offenders


def test_plan_step_ids_are_prefixed_and_ordered(registry):
    for unit in registry:
        prefix = unit.id.lower()
        for index, step in enumerate(unit.plan, start=1):
            assert step.id.startswith(f"{prefix}-s{index:02d}-"), f"{unit.id}: {step.id}"


def test_specs_round_trip_through_the_generator(catalogue):
    """Regenerating must reproduce the committed files byte for byte."""
    import subprocess

    result = subprocess.run(
        ["python3", "tools/generate_agents.py", "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_catalogue_is_regenerable_from_the_workbook():
    import subprocess

    result = subprocess.run(
        ["python3", "tools/build_catalogue.py", "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
