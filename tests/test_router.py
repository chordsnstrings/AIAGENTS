"""Roster resolution: which units a given business actually runs.

Every one of the sixty verticals must resolve to a usable roster in every
market, and the units the catalogue says are never disabled must survive an
owner trying to disable them.
"""

from __future__ import annotations

import pytest

from adw.models import BusinessProfile, UnitType
from adw.registry import load_country_pack
from adw.router import ALWAYS_ON, Wave, coverage, missing_config, resolve_roster


@pytest.fixture(scope="module")
def uk_pack():
    return load_country_pack("UK")


def _profile(vertical_id: str, **kwargs) -> BusinessProfile:
    return BusinessProfile(name="Test Business", vertical_id=vertical_id, **kwargs)


def test_every_vertical_resolves_to_a_roster(catalogue, registry, uk_pack):
    for vertical_id in catalogue.verticals:
        roster = resolve_roster(_profile(vertical_id), catalogue, registry, uk_pack)
        assert roster.entries
        assert roster.wave(Wave.NOW), vertical_id


def test_a_roster_is_core_plus_vertical_plus_universal_playbooks(catalogue, registry, uk_pack):
    vertical = catalogue.verticals["V7"]
    roster = resolve_roster(_profile("V7"), catalogue, registry, uk_pack)
    expected = (
        len(registry.core_workers)
        + len(vertical.specialist_ids)
        + len(vertical.playbook_ids)
        + len(registry.universal_playbooks)
    )
    assert len(roster.entries) == expected


def test_roster_contains_no_other_vertical(catalogue, registry, uk_pack):
    roster = resolve_roster(_profile("V7"), catalogue, registry, uk_pack)
    for entry in roster.entries:
        if entry.unit.scope.vertical_id:
            assert entry.unit.scope.vertical_id == "V7", entry.id


def test_unknown_vertical_is_rejected(catalogue, registry, uk_pack):
    with pytest.raises(KeyError):
        resolve_roster(_profile("V999"), catalogue, registry, uk_pack)


def test_always_on_units_cannot_be_disabled(catalogue, registry, uk_pack):
    profile = _profile("V1", disabled_units=ALWAYS_ON)
    roster = resolve_roster(profile, catalogue, registry, uk_pack)
    for entry in roster.entries:
        if entry.id in ALWAYS_ON:
            assert entry.wave is Wave.NOW, entry.id


def test_owner_can_disable_an_ordinary_unit(catalogue, registry, uk_pack):
    profile = _profile("V1", disabled_units=("B8",))
    roster = resolve_roster(profile, catalogue, registry, uk_pack)
    entry = next(e for e in roster.entries if e.id == "B8")
    assert entry.wave is Wave.SKIP


def test_owner_can_force_a_unit_on(catalogue, registry, uk_pack):
    profile = _profile("V1", enabled_units=("J2",))
    roster = resolve_roster(profile, catalogue, registry, uk_pack)
    entry = next(e for e in roster.entries if e.id == "J2")
    assert entry.wave is Wave.NOW


def test_archetype_anchors_land_in_wave_now(catalogue, registry, uk_pack):
    # ARC-A (emergency trades) anchors on A6, A3, D1, F2.
    roster = resolve_roster(_profile("V1"), catalogue, registry, uk_pack)
    now = {e.id for e in roster.wave(Wave.NOW)}
    assert {"A6", "A3", "D1", "F2"} <= now


def test_safety_critical_playbooks_are_always_wave_now(catalogue, registry, uk_pack):
    for vertical_id in catalogue.verticals:
        roster = resolve_roster(_profile(vertical_id), catalogue, registry, uk_pack)
        for entry in roster.entries:
            if entry.unit.is_safety_critical:
                assert entry.wave is Wave.NOW, f"{vertical_id}/{entry.id}"


def test_weak_fit_archetype_gets_a_thinner_roster(catalogue, registry, uk_pack):
    # V21 (retail product-led) is ARC-J, which the workbook itself deprioritises.
    weak = resolve_roster(_profile("V21"), catalogue, registry, uk_pack)
    strong = resolve_roster(_profile("V1"), catalogue, registry, uk_pack)
    weak_now = len(weak.wave(Wave.NOW))
    strong_now = len(strong.wave(Wave.NOW))
    assert weak_now < strong_now
    assert weak.wave(Wave.SKIP)


def test_missing_config_lists_owner_supplied_settings(catalogue, registry, uk_pack):
    roster = resolve_roster(_profile("V7"), catalogue, registry, uk_pack)
    outstanding = missing_config(roster)
    assert "escalation_contacts" in outstanding
    # Anything the country pack already answers must not be asked of the owner.
    assert "language_set" not in outstanding
    assert "messaging_channel" not in outstanding


def test_every_unit_is_reachable_through_some_roster(registry, catalogue):
    result = coverage(registry, catalogue)
    assert result["unreachable"] == []
    assert result["reachable"] == result["total"] == 815


def test_roster_explains_itself(catalogue, registry, uk_pack):
    roster = resolve_roster(_profile("V5"), catalogue, registry, uk_pack)
    text = roster.explain()
    assert "NOW" in text and "NEXT" in text
    for entry in roster.entries:
        assert entry.reason


@pytest.mark.parametrize("country", ["US", "UK", "DE", "IN", "AE", "JP", "BR"])
def test_rosters_resolve_in_every_market(country, catalogue, registry):
    pack = load_country_pack(country)
    roster = resolve_roster(_profile("V5"), catalogue, registry, pack)
    assert roster.country_pack.code == country
    assert roster.summary()["active"] > 0
