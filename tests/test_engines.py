"""Fourteen engines must carry all 815 units.

That is the catalogue's first standing rule, and it is only true if every family
has an engine, every engine is reachable, and no engine leans on a generic
fallback to cover shapes it never modelled.
"""

from __future__ import annotations

from collections import Counter

import pytest

#: The share of a family's units its fallback profile may carry before the
#: family's real shapes should be considered unmodelled.
MAX_FALLBACK_SHARE = 0.34


def test_all_fourteen_engines_are_registered(engines):
    assert sorted(engines, key=lambda f: int(f[2:])) == [f"MF{n}" for n in range(1, 15)]


def test_engine_metadata_matches_the_catalogue(engines, catalogue):
    for family_id, engine in engines.items():
        family = catalogue.mechanism_families[family_id]
        assert engine.id == family.id
        assert engine.family == family.family
        assert engine.what_it_does == family.what_it_does


def test_engine_modules_are_where_the_catalogue_says(catalogue):
    import importlib

    for family in catalogue.mechanism_families.values():
        importlib.import_module(family.module)


def test_every_engine_declares_its_surface(engines):
    for family_id, engine in engines.items():
        assert engine.capabilities, family_id
        assert engine.default_tools, family_id
        assert engine.default_kpis, family_id
        assert engine.profiles, family_id


def test_every_engine_ends_with_an_unconditional_fallback(engines):
    for family_id, engine in engines.items():
        assert engine.profiles[-1].match == (), (
            f"{family_id}: last profile {engine.profiles[-1].name!r} must be the fallback"
        )
        for profile in engine.profiles[:-1]:
            assert profile.match, f"{family_id}: {profile.name} has no match tokens"


def test_profile_names_are_unique_within_an_engine(engines):
    for family_id, engine in engines.items():
        names = [p.name for p in engine.profiles]
        assert len(names) == len(set(names)), family_id


def test_profile_match_tokens_are_distinctive(engines):
    """A short token would swallow units that belong to another profile."""
    for family_id, engine in engines.items():
        for profile in engine.profiles:
            for token in profile.match:
                assert len(token) >= 3, f"{family_id}/{profile.name}: {token!r} too short"
                assert token == token.lower(), f"{family_id}/{profile.name}: {token!r} not lowercase"


def test_every_engine_carries_at_least_one_unit(registry, engines):
    for family_id in engines:
        assert registry.by_mechanism_family.get(family_id), family_id


def test_engines_do_not_over_rely_on_their_fallback(registry, engines):
    overloaded = []
    for family_id, engine in engines.items():
        units = registry.by_mechanism_family[family_id]
        fallback = engine.profiles[-1].name
        share = sum(1 for u in units if u.engine_profile == fallback) / len(units)
        if share > MAX_FALLBACK_SHARE:
            overloaded.append(f"{family_id}: {share:.0%} on fallback {fallback!r}")
    assert not overloaded


def test_every_declared_profile_is_used_by_some_unit(registry, engines):
    """A profile no unit reaches is either dead config or a broken match token."""
    unused = []
    for family_id, engine in engines.items():
        used = {u.engine_profile for u in registry.by_mechanism_family[family_id]}
        for profile in engine.profiles:
            if profile.name not in used:
                unused.append(f"{family_id}/{profile.name}")
    assert not unused


def test_composition_is_deterministic(catalogue, engines):
    """The same record must compose to the same unit every time."""
    from engines.base import get_engine

    for record in catalogue.records[:60]:
        engine = get_engine(record["mechanism_family"])
        assert engine.compose(record).to_dict() == engine.compose(record).to_dict()


def test_unit_counts_per_family_match_the_catalogue(registry, catalogue):
    expected = Counter(u["mechanism_family"] for u in catalogue.records)
    actual = {k: len(v) for k, v in registry.by_mechanism_family.items()}
    assert actual == dict(expected)


@pytest.mark.parametrize("family_id", [f"MF{n}" for n in range(1, 15)])
def test_family_units_all_compose_cleanly(family_id, catalogue, engines):
    from adw.guardrails import audit_unit, errors
    from engines.base import get_engine

    engine = get_engine(family_id)
    records = [r for r in catalogue.records if r["mechanism_family"] == family_id]
    for record in records:
        unit = engine.compose(record)
        assert unit.plan and unit.artifacts and unit.mission.strip(), record["id"]
        assert not errors(audit_unit(unit)), record["id"]
