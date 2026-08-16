"""The standing rules are checked, not trusted.

The workbook states three standing rules and one legend entry about
safety-critical protocols.  A spec that breaches any of them must not ship, so
each rule gets a test that fails the build rather than a paragraph that asks
nicely.
"""

from __future__ import annotations

from adw.guardrails import (
    Severity,
    audit,
    audit_unit,
    check_probabilistic_authority,
    check_safety_protocol,
    errors,
)
from adw.models import (
    Escalation,
    Flags,
    GateSeverity,
    Scope,
    Step,
    StepKind,
    Unit,
    UnitType,
    HumanGate,
)


def test_the_whole_catalogue_passes_the_standing_rule_audit(registry):
    violations = errors(audit(registry))
    assert not violations, "\n".join(str(v) for v in violations[:25])


def test_every_unit_declares_at_least_one_human_gate(registry):
    ungated = [u.id for u in registry if not u.human_gates]
    assert not ungated


def test_every_unit_carries_the_four_standing_guardrails(registry):
    required = {"SR-PROBABILISTIC", "SR-OWNED-CHANNELS", "SR-CONFIG-NOT-CODE", "SR-AUDIT"}
    missing = [
        f"{u.id}: {sorted(required - {g.id for g in u.guardrails})}"
        for u in registry
        if not required <= {g.id for g in u.guardrails}
    ]
    assert not missing


def test_safety_critical_units_recognise_and_route_only(registry):
    diamonds = registry.safety_critical
    assert diamonds, "the catalogue marks 37 units safety-critical"
    for unit in diamonds:
        assert unit.plan[0].interlock, f"{unit.id}: interlock is not the first step"
        assert unit.plan[-1].kind is StepKind.STOP, f"{unit.id}: does not stop"
        assert any(
            g.severity is GateSeverity.ABSOLUTE for g in unit.human_gates
        ), f"{unit.id}: no absolute gate"
        assert unit.is_recognition_only, unit.id
        assert not audit_unit(unit) or not errors(audit_unit(unit)), unit.id


def test_safety_critical_count_matches_the_workbook(registry):
    assert len(registry.safety_critical) == 37


def test_hard_interlock_units_enforce_the_rule_as_a_step(registry):
    """"None - interlock" in the workbook means no override exists.

    Eight units say so without being safety-critical -- the patch test that
    blocks a booking, the failed right-to-work check, the allergy order, the
    election-period comms restriction. The rule must be the first step of the
    plan, not a sentence in the mission, and it must carry its own guardrail.
    """
    hard = [
        u
        for u in registry
        if not u.is_safety_critical
        and any(
            g.severity is GateSeverity.ABSOLUTE and "interlock" in g.decision.lower()
            for g in u.human_gates
        )
    ]
    assert len(hard) == 8, sorted(u.id for u in hard)
    for unit in hard:
        assert unit.plan[0].interlock, f"{unit.id}: interlock is not the first step"
        assert any(g.id == "GR-HARD-INTERLOCK" for g in unit.guardrails), unit.id
        assert any(a.key == "interlock_log" for a in unit.artifacts), unit.id
        # Unlike a diamond, a hard-interlock unit still finishes its work once
        # the condition clears, so it must not be forced into a terminal stop.
        assert unit.plan[-1].kind is StepKind.RECORD, unit.id


def test_every_interlock_step_declares_its_log(registry):
    for unit in registry:
        if any(s.interlock for s in unit.plan):
            assert any(a.key == "interlock_log" for a in unit.artifacts), unit.id


def test_revenue_critical_count_matches_the_workbook(registry):
    assert len(registry.revenue_critical) == 68


def test_publishing_units_name_their_connected_accounts_grant(registry):
    from adw.models import Capability

    offenders = []
    for unit in registry:
        if Capability.PUBLISH not in unit.capabilities:
            continue
        if "connected_accounts" not in {c.key for c in unit.config_keys}:
            offenders.append(unit.id)
    assert not offenders


def test_every_unit_persists_its_artefacts(registry):
    for unit in registry:
        assert any(s.kind is StepKind.RECORD for s in unit.plan), unit.id
        assert any(a.key == "audit_trail" for a in unit.artifacts), unit.id


def test_plans_only_produce_declared_artefacts(registry):
    offenders = []
    for unit in registry:
        declared = {a.key for a in unit.artifacts}
        produced = {key for s in unit.plan for key in s.produces}
        if produced - declared:
            offenders.append(f"{unit.id}: {sorted(produced - declared)}")
    assert not offenders


# --------------------------------------------------------------------------- #
# the checks themselves must be able to fail
# --------------------------------------------------------------------------- #


def _minimal_unit(**overrides) -> Unit:
    defaults = dict(
        id="TEST-1",
        type=UnitType.CORE_WORKER,
        scope=Scope(department_id="DEPT-01", department_name="Front Desk"),
        mechanism_family="MF1",
        function="test",
        expected_output="test",
        acceptance=(),
        flags=Flags(),
        worker="Tester",
        system_agent="Test Agent",
        human_gates=(
            HumanGate(
                decision="anything",
                severity=GateSeverity.BLOCKING,
                escalate_to=Escalation.OWNER,
            ),
        ),
    )
    defaults.update(overrides)
    return Unit(**defaults)


def test_probabilistic_check_catches_an_ungated_approval():
    unit = _minimal_unit(
        plan=(
            Step(
                id="s1",
                name="Approve it",
                kind=StepKind.ACT,
                description="Approve the refund and close the case.",
            ),
        )
    )
    violations = check_probabilistic_authority(unit)
    assert any("approve" in v.detail for v in violations)


def test_probabilistic_check_allows_executing_a_human_decision():
    unit = _minimal_unit(
        plan=(
            Step(
                id="s1",
                name="Apply the decision",
                kind=StepKind.ACT,
                description="Once approved by the owner, approve the refund in the ledger.",
            ),
        )
    )
    assert not check_probabilistic_authority(unit)


def test_probabilistic_check_requires_a_gate():
    unit = _minimal_unit(human_gates=())
    assert any("no human gate" in v.detail for v in check_probabilistic_authority(unit))


def test_safety_check_catches_a_protocol_that_resolves():
    unit = _minimal_unit(
        flags=Flags(safety_critical=True),
        human_gates=(
            HumanGate(
                decision="none",
                severity=GateSeverity.ABSOLUTE,
                escalate_to=Escalation.EMERGENCY_SERVICES,
            ),
        ),
        plan=(
            Step(
                id="s1",
                name="Interlock",
                kind=StepKind.ACT,
                description="Run the protocol.",
                interlock=True,
            ),
            Step(
                id="s2",
                name="Close",
                kind=StepKind.STOP,
                description="Clear the hazard and stand down.",
            ),
        ),
    )
    details = " ".join(v.detail for v in check_safety_protocol(unit))
    assert "resolution language" in details


def test_safety_check_requires_an_interlock_first():
    unit = _minimal_unit(
        flags=Flags(safety_critical=True),
        plan=(
            Step(id="s1", name="Chat", kind=StepKind.GATHER, description="Ask questions."),
            Step(id="s2", name="Stop", kind=StepKind.STOP, description="Hand over."),
        ),
    )
    details = " ".join(v.detail for v in check_safety_protocol(unit))
    assert "no interlock step" in details


def test_hard_interlock_check_catches_a_gate_without_a_step():
    from adw.guardrails import check_hard_interlock

    unit = _minimal_unit(
        human_gates=(
            HumanGate(
                decision="No override exists - a hard interlock governs this case",
                severity=GateSeverity.ABSOLUTE,
                escalate_to=Escalation.OWNER,
            ),
        ),
        plan=(Step(id="s1", name="Do it", kind=StepKind.ACT, description="Just do it."),),
    )
    details = " ".join(v.detail for v in check_hard_interlock(unit))
    assert "no interlock step" in details


def test_hard_interlock_check_ignores_ordinary_units():
    from adw.guardrails import check_hard_interlock

    assert not check_hard_interlock(_minimal_unit())


def test_audit_severities_are_partitioned():
    unit = _minimal_unit(human_gates=())
    violations = audit_unit(unit)
    assert all(v.severity in (Severity.ERROR, Severity.WARNING) for v in violations)
