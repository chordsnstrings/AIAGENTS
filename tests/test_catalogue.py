"""The normalised catalogue must match the workbook it came from.

These are the counts the workbook itself declares on its README sheet.  If the
workbook changes, these numbers change with it -- deliberately, in a diff.
"""

from __future__ import annotations

from collections import Counter

import pytest

EXPECTED_TOTALS = {
    "units": 815,
    "core_worker": 68,
    "specialist": 355,
    "playbook_universal": 92,
    "playbook_vertical": 300,
    "departments": 10,
    "verticals": 60,
    "archetypes": 10,
    "mechanism_families": 14,
    "edge_case_domains": 9,
}


def test_totals_match_the_workbook(catalogue):
    assert dict(catalogue.totals) == EXPECTED_TOTALS


def test_unit_ids_are_unique(catalogue):
    ids = [u["id"] for u in catalogue.records]
    duplicates = [i for i, n in Counter(ids).items() if n > 1]
    assert not duplicates


def test_unit_paths_are_unique(catalogue):
    paths = [u["path"] for u in catalogue.records]
    duplicates = [p for p, n in Counter(paths).items() if n > 1]
    assert not duplicates


def test_every_unit_binds_to_a_known_mechanism_family(catalogue):
    known = set(catalogue.mechanism_families)
    unknown = {u["mechanism_family"] for u in catalogue.records} - known
    assert not unknown


def test_every_unit_has_a_function_and_an_expected_output(catalogue):
    for unit in catalogue.records:
        assert unit["function"].strip(), unit["id"]
        assert unit["expected_output"].strip(), unit["id"]
        assert unit["acceptance_criteria"], unit["id"]


def test_agents_are_named_and_playbooks_are_triggered(catalogue):
    for unit in catalogue.records:
        if unit["type"] in ("core_worker", "specialist"):
            assert unit["worker"], unit["id"]
            assert unit["system_agent"], unit["id"]
        else:
            assert unit["trigger"], unit["id"]


def test_every_vertical_has_specialists_and_five_playbooks(catalogue):
    for vertical in catalogue.verticals.values():
        assert vertical.specialist_ids, vertical.id
        assert len(vertical.playbook_ids) == 5, vertical.id


def test_vertical_archetypes_are_real(catalogue):
    known = set(catalogue.archetypes)
    for vertical in catalogue.verticals.values():
        assert set(vertical.archetypes) <= known, vertical.id


def test_department_headcounts_sum_to_the_core(catalogue):
    total = sum(d.headcount for d in catalogue.departments.values())
    assert total == EXPECTED_TOTALS["core_worker"]


def test_edge_case_domains_cover_every_universal_playbook(catalogue):
    total = sum(d.playbook_count for d in catalogue.domains.values())
    assert total == EXPECTED_TOTALS["playbook_universal"]


def test_the_four_new_mechanism_families_are_marked_new(catalogue):
    # MF11-MF14 are the additions in catalogue v2; MF13 rides the existing
    # ModelArk stack but is still new to the catalogue.
    new = {m.id for m in catalogue.mechanism_families.values() if m.is_new}
    assert new == {"MF11", "MF12", "MF13", "MF14"}


@pytest.mark.parametrize("rule_fragment", ["Config, not code", "Customer-owned channels", "flag"])
def test_standing_rules_are_carried_through(catalogue, rule_fragment):
    joined = " ".join(catalogue.standing_rules)
    assert rule_fragment.lower() in joined.lower()
