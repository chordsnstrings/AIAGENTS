"""The shared vocabulary the engine layer and the audit layer both depend on.

``describes_publishing`` decides two things at once: whether an engine attaches a
``connected_accounts`` grant, and whether the audit demands one.  If it says yes
too readily the customer-owned-channels rule becomes noise attached to units that
never publish; if it says no too readily a unit publishes without a declared
grant.  Both directions are pinned here.
"""

from __future__ import annotations

import pytest

from adw.models import (
    PERMITTED_ACTS,
    PROHIBITED_ACTS,
    Flags,
    GateSeverity,
    HumanGate,
    Escalation,
    Scope,
    Step,
    StepKind,
    Unit,
    UnitType,
    describes_publishing,
)

# "published X" as reference data the business owns, not an act of publishing.
NOT_PUBLISHING = [
    "Compare what you have against the published terms and the clocks",
    "Quote only from the published price book",
    "Answer from the published criteria, rule by rule",
    "Honour the published cancellation fees",
    "Apply the published late-cancellation policy",
    "Cost indication from published pricing only",
    "Check the published rates before quoting",
    "Draft the reply and queue it for approval",
    "Record the outcome against the case file",
]

PUBLISHING = [
    "Publish the approved post to the profile",
    "Publishes weekly posts on the agreed schedule",
    "Published Q&A pages live on the site",
    "Post it to the connected account",
    "Send from the owner's own mailbox",
    "Upload to the directory listing",
    "Share to the local community group",
    "The campaign goes live on the owner's channel",
]


@pytest.mark.parametrize("text", NOT_PUBLISHING)
def test_reference_data_is_not_publishing(text):
    assert not describes_publishing(text)


@pytest.mark.parametrize("text", PUBLISHING)
def test_outbound_acts_are_publishing(text):
    assert describes_publishing(text)


def test_empty_text_is_not_publishing():
    assert not describes_publishing("")
    assert not describes_publishing(None)  # type: ignore[arg-type]


def test_permitted_and_prohibited_acts_are_disjoint():
    assert PERMITTED_ACTS.isdisjoint(PROHIBITED_ACTS)
    assert PERMITTED_ACTS == {"flag", "collect", "draft"}
    assert PROHIBITED_ACTS == {"clear", "diagnose", "advise", "approve"}


def _unit(**overrides) -> Unit:
    defaults = dict(
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
    )
    defaults.update(overrides)
    return Unit(**defaults)


def test_display_name_pairs_worker_and_system_agent():
    assert _unit().display_name == "Tester (Test Agent)"


def test_playbook_display_name_uses_the_trigger():
    unit = _unit(
        type=UnitType.PLAYBOOK_UNIVERSAL, worker=None, system_agent=None, trigger="Refund requested"
    )
    assert unit.display_name == "T1 Refund requested"
    assert unit.is_playbook


def test_safety_critical_units_are_recognition_only():
    assert _unit(flags=Flags(safety_critical=True)).is_recognition_only
    assert not _unit().is_recognition_only


def test_blocking_gates_exclude_advisory_ones():
    unit = _unit(
        human_gates=(
            HumanGate("a", GateSeverity.ADVISORY, Escalation.OWNER),
            HumanGate("b", GateSeverity.BLOCKING, Escalation.OWNER),
            HumanGate("c", GateSeverity.ABSOLUTE, Escalation.EMERGENCY_SERVICES),
        )
    )
    assert [g.decision for g in unit.blocking_gates] == ["b", "c"]


def test_unit_serialises_to_the_on_disk_shape():
    unit = _unit(
        plan=(Step(id="s1", name="n", kind=StepKind.RECORD, description="d", produces=("k",)),)
    )
    data = unit.to_dict()
    assert data["id"] == "T1"
    assert data["kind"] == "agent"
    assert data["engine"]["mechanism_family"] == "MF1"
    assert data["plan"][0]["kind"] == "record"
    assert data["plan"][0]["produces"] == ["k"]
