"""What survives into the runtime.

A behavioural review of all 815 units against an external model found three
things the static suite could not see, because every check passed while the
units still misbehaved:

* The mission is the system prompt. Nothing else in the spec is in front of the
  model -- not the artefact list, not the config keys. A unit whose mission did
  not name its artefacts invented its own set and produced no audit trail.
* 79 of 85 declared country-pack keys resolved to nothing, so 757 units read a
  setting that did not exist and filled the hole from training.
* Nothing forbade supplying a jurisdiction value from the model's own
  knowledge. A safety-critical gas-leak protocol said it did not have the
  emergency number loaded and then supplied one anyway, differently per run.

These tests pin all three shut.
"""

from __future__ import annotations

import pytest

from adw.guardrails import (
    Severity,
    check_config_resolves,
    check_mission_is_self_contained,
    errors,
)
from adw.registry import available_country_packs, load_country_pack

# Keys whose value would be dangerous to default: a wrong emergency number is
# worse than an absent one, because it gets dialled.
NO_DEFAULT_KEYS = ("emergency_routing",)


# --------------------------------------------------------------------------- #
# the mission carries the whole contract
# --------------------------------------------------------------------------- #


def test_every_mission_names_every_artefact_key(registry):
    offenders = []
    for unit in registry:
        missing = [a.key for a in unit.artifacts if a.key not in unit.mission]
        if missing:
            offenders.append(f"{unit.id}: {missing[:3]}")
    assert not offenders, offenders[:10]


def test_every_mission_names_every_artefact_by_name(registry):
    offenders = []
    for unit in registry:
        missing = [a.name for a in unit.artifacts if a.name not in unit.mission]
        if missing:
            offenders.append(f"{unit.id}: {missing[:3]}")
    assert not offenders, offenders[:10]


def test_every_mission_declares_its_config_keys(registry):
    """A key the model is never told about is a key it will not read."""
    offenders = [
        unit.id
        for unit in registry
        if any(k.key not in unit.mission for k in unit.config_keys)
    ]
    assert not offenders, offenders[:10]


def test_every_mission_forbids_answering_from_training(registry):
    for unit in registry:
        lowered = unit.mission.lower()
        assert "from your own knowledge" in lowered, unit.id
        assert "a gate, not a gap" in lowered, unit.id


def test_safety_critical_missions_forbid_recalling_an_emergency_number(registry):
    for unit in registry.safety_critical:
        lowered = unit.mission.lower()
        assert "emergency number is configuration, never recall" in lowered, unit.id
        assert "emergency_routing" in unit.mission, unit.id
        # The protective actions do not depend on a number and must still land.
        assert "protective actions" in lowered, unit.id


def test_safety_critical_missions_close_the_conditional_loophole(registry):
    """The observed leak was conditional, not assertive.

    A behavioural run had V1-E1 state "I will not supply one from memory" and
    then, one line later, "if you are in the United Kingdom, dial ...". The
    conditional feels safe because it asserts nothing about this market; it is
    not, because the caller keeps the digits and drops the condition.
    """
    for unit in registry.safety_critical:
        lowered = unit.mission.lower()
        assert "the conditional is the trap" in lowered, unit.id
        assert "is not compliance, it is the breach" in lowered, unit.id
        assert "digits in your output are digits that get dialled" in lowered, unit.id


def test_safety_critical_missions_supply_a_no_digit_alternative(registry):
    """Refusal alone leaves a vacuum, and the vacuum is what got filled.

    Telling a unit what not to say to someone in danger, without giving it
    something adequate to say instead, is why it reached for the number. The
    sanctioned answer must be complete, actionable and digit-free.
    """
    for unit in registry.safety_critical:
        lowered = unit.mission.lower()
        assert "protective actions never depend on knowing any number" in lowered, unit.id
        assert "call your local emergency number" in lowered, unit.id
        assert "with no digits" in lowered, unit.id


def test_the_refusal_rule_is_the_last_thing_in_a_safety_mission(registry):
    """Position is part of the fix.

    This rule is only ever tested under pressure, and the leak happened with the
    prohibition sitting 68% of the way through an 8,700-character prompt. It is
    restated last so the final thing in context is the thing most likely to be
    argued with.
    """
    for unit in registry.safety_critical:
        tail = unit.mission.lower()[-1200:]
        assert "last, and above anything above it" in tail, unit.id
        assert "however urgent this becomes" in tail, unit.id


def test_no_safety_mission_contains_a_dialable_emergency_number(registry):
    """The mission must not itself hand the model digits to echo back."""
    import re

    pattern = re.compile(r"\b(?:999|911|112|110|119|000|111|190|192|193|1669)\b")
    for unit in registry.safety_critical:
        # emergency_routing is read at runtime; the prompt template carries no
        # number of its own, so there is nothing to recite even by accident.
        assert not pattern.search(unit.mission), f"{unit.id}: {pattern.findall(unit.mission)}"


def test_mission_check_catches_an_unnamed_artefact():
    from adw.models import Artifact, Flags, Scope, Unit, UnitType

    unit = Unit(
        id="T1",
        type=UnitType.CORE_WORKER,
        scope=Scope(),
        mechanism_family="MF1",
        function="f",
        expected_output="e",
        acceptance=(),
        flags=Flags(),
        worker="Tester",
        system_agent="Test Agent",
        mission="A mission that mentions nothing at all.",
        artifacts=(Artifact(key="case_file", name="Case file", description="d"),),
    )
    details = " ".join(v.detail for v in check_mission_is_self_contained(unit))
    assert "case_file" in details
    assert "anti-fabrication" in details


# --------------------------------------------------------------------------- #
# declared config actually resolves
# --------------------------------------------------------------------------- #


def test_no_unit_declares_a_country_pack_key_that_resolves_to_nothing(registry):
    violations = [v for u in registry for v in check_config_resolves(u)]
    assert not violations, [str(v) for v in violations[:10]]


def test_every_required_country_pack_key_is_answered_by_every_pack(registry):
    required = {
        k.key
        for u in registry
        for k in u.config_keys
        if k.resolved_by == "country_pack" and k.required
    }
    assert required, "expected units to require country-pack settings"
    for code in available_country_packs():
        answered = set(load_country_pack(code).settings)
        assert required <= answered, f"{code} missing {sorted(required - answered)[:6]}"


def test_every_declared_country_pack_key_is_answered_somewhere(registry):
    declared = {
        k.key for u in registry for k in u.config_keys if k.resolved_by == "country_pack"
    }
    anywhere: set[str] = set()
    for code in available_country_packs():
        anywhere |= set(load_country_pack(code).settings)
    assert declared <= anywhere, sorted(declared - anywhere)[:10]


def test_config_resolution_check_fails_when_a_key_is_unpopulated(monkeypatch, registry):
    """The check must be able to fail, or it is not a check."""
    import adw.guardrails as guardrails

    guardrails._pack_keys.cache_clear()
    monkeypatch.setattr(guardrails, "_pack_keys", lambda: (frozenset({"language_set"}), ("US",)))
    unit = registry.get("D1")
    violations = check_config_resolves(unit)
    assert errors(violations), "stripping the packs must produce errors"
    assert any("working_calendar" in v.detail for v in violations)
    # monkeypatch restores the real (cached) function at teardown.


# --------------------------------------------------------------------------- #
# emergency routing is per-market and never defaulted
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("code", available_country_packs())
def test_every_pack_states_its_own_emergency_routing(code):
    routing = load_country_pack(code).get("emergency_routing")
    assert isinstance(routing, dict), code
    for field in ("general", "police", "fire", "ambulance", "poison", "gas_leak", "electricity"):
        assert routing.get(field), f"{code}: {field} empty"
    # The protective actions do not depend on any number being known.
    assert "get everyone out" in routing["script"].lower(), code
    assert "quote no number that is not written here" in routing["script"].lower(), code
    # The answer to "what do I say with no configuration" is itself
    # configuration, so a unit never has to improvise it under pressure.
    absent = routing["absent_script"]
    assert "call your local emergency number" in absent.lower(), code
    assert not __import__("re").search(r"\b\d{3,}\b", absent), f"{code}: absent_script has digits"


def test_emergency_numbers_are_not_shared_across_unrelated_markets():
    """A default emergency number is a wrong emergency number.

    If two packs agreed on every field it would mean one had been copied rather
    than researched, which is the failure this key exists to prevent.
    """
    seen: dict[tuple, str] = {}
    for code in available_country_packs():
        routing = load_country_pack(code).get("emergency_routing")
        signature = (routing["general"], routing["fire"], routing["ambulance"], routing["gas_leak"])
        assert signature not in seen, f"{code} duplicates {seen.get(signature)}"
        seen[signature] = code


@pytest.mark.parametrize(
    "code,expected",
    [
        ("UK", "999"),
        ("US", "911"),
        ("DE", "112"),
        ("AU", "000"),
        ("NZ", "111"),
        ("JP", "119"),
        ("BR", "192"),
    ],
)
def test_known_emergency_numbers_are_right(code, expected):
    """Spot-check the values a unit will read out loud."""
    routing = load_country_pack(code).get("emergency_routing")
    joined = " ".join(str(v) for v in routing.values())
    assert expected in joined, f"{code}: expected {expected} somewhere in {routing}"


def test_packs_flag_what_an_operator_must_confirm_locally():
    """Utility lines are distributor-specific in most markets.

    Where there is no national number the pack says so in words rather than
    leaving a hole, because a hole is what invites a fabricated answer.
    """
    for code in available_country_packs():
        routing = load_country_pack(code).get("emergency_routing")
        assert "confirm_locally" in routing, code
        for field in routing["confirm_locally"]:
            assert field in routing, f"{code}: flags {field} but does not define it"
        for field in ("gas_leak", "electricity"):
            value = routing[field].lower()
            if "no national" in value:
                assert "call" in value, f"{code}: {field} states no line but no fallback"
