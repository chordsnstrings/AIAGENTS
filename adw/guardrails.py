"""Enforcement of the catalogue's standing rules.

The workbook states three standing rules and one legend entry that together
decide what a unit is allowed to do:

1. Config, not code -- vertical and country differences resolve to config.
2. Customer-owned channels -- growth and social publish only from the
   customer's connected accounts.
3. Probabilistic components flag, collect and draft -- never clear, diagnose,
   advise or approve.
4. A diamond marks a safety-critical protocol: recognition and routing only.

Prose in a spec is not enforcement.  This module reads a composed
:class:`~adw.models.Unit` and reports every way it breaches those rules, so the
rules are checked in CI rather than trusted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

from adw.models import (
    PROHIBITED_ACT_MARKERS,
    Capability,
    GateSeverity,
    StepKind,
    Unit,
)


class Severity(str, Enum):
    ERROR = "error"  # the unit must not ship
    WARNING = "warning"  # a human should look at this


@dataclass(frozen=True)
class Violation:
    unit_id: str
    rule: str
    severity: Severity
    detail: str

    def __str__(self) -> str:
        return f"[{self.severity.value:<7}] {self.unit_id:<9} {self.rule}: {self.detail}"


# --------------------------------------------------------------------------- #
# rule 4 -- safety-critical protocols recognise and route, nothing more
# --------------------------------------------------------------------------- #

#: Language that would mean the unit resolved the condition itself.  A diamond
#: unit may not contain it: the workbook's legend allows recognition and routing
#: only, and escalation IS the product.
_RESOLUTION_MARKERS = (
    "resolve the incident",
    "close the incident",
    "declare the site safe",
    "confirm it is safe",
    "clear the hazard",
    "make safe",
    "stand down",
    "reassure the customer that",
    "confirm no risk",
)


def check_safety_protocol(unit: Unit) -> list[Violation]:
    if not unit.is_safety_critical:
        return []
    violations: list[Violation] = []
    rule = "safety-critical: recognition and routing only"

    interlocks = [s for s in unit.plan if s.interlock]
    if not interlocks:
        violations.append(
            Violation(unit.id, rule, Severity.ERROR, "no interlock step in the plan")
        )
    elif unit.plan[0] is not interlocks[0]:
        violations.append(
            Violation(
                unit.id,
                rule,
                Severity.ERROR,
                f"interlock is step {unit.plan.index(interlocks[0]) + 1}, must be first",
            )
        )

    if not unit.plan or unit.plan[-1].kind is not StepKind.STOP:
        violations.append(
            Violation(
                unit.id,
                rule,
                Severity.ERROR,
                "plan must terminate in a stop step at the human gate",
            )
        )

    if not any(g.severity is GateSeverity.ABSOLUTE for g in unit.human_gates):
        violations.append(
            Violation(unit.id, rule, Severity.ERROR, "no absolute human gate declared")
        )

    body = f"{unit.mission}\n" + "\n".join(s.description for s in unit.plan)
    lowered = body.lower()
    for marker in _RESOLUTION_MARKERS:
        if marker in lowered:
            violations.append(
                Violation(
                    unit.id,
                    rule,
                    Severity.ERROR,
                    f"resolution language present: {marker!r}",
                )
            )
    return violations


# --------------------------------------------------------------------------- #
# rule 3 -- flag, collect, draft; never clear, diagnose, advise, approve
# --------------------------------------------------------------------------- #


def check_probabilistic_authority(unit: Unit) -> list[Violation]:
    violations: list[Violation] = []
    rule = "probabilistic components never clear, diagnose, advise or approve"

    gated = bool(unit.blocking_gates)
    for index, plan_step in enumerate(unit.plan):
        if plan_step.kind not in (StepKind.DECIDE, StepKind.ACT):
            continue
        lowered = plan_step.description.lower()
        for act, markers in PROHIBITED_ACT_MARKERS.items():
            for marker in markers:
                if marker not in lowered:
                    continue
                # A prohibited act is only acceptable when the step is explicitly
                # executing a human's decision, which requires a blocking gate.
                excused = gated and (
                    "once approved" in lowered
                    or "after the gate" in lowered
                    or "on the owner's instruction" in lowered
                    or "human-approved" in lowered
                )
                if not excused:
                    violations.append(
                        Violation(
                            unit.id,
                            rule,
                            Severity.ERROR,
                            f"step {index + 1} ({plan_step.id}) appears to {act}: {marker!r}",
                        )
                    )

    if not unit.human_gates:
        violations.append(
            Violation(unit.id, rule, Severity.ERROR, "no human gate declared")
        )
    return violations


# --------------------------------------------------------------------------- #
# rule 2 -- customer-owned channels
# --------------------------------------------------------------------------- #

#: Kept in step with ``engines.base.PUBLISHING_STEP_MARKERS``: the engine attaches
#: the connected-accounts grant on these markers, and this check demands it.
_PUBLISHING_STEP_MARKERS = ("publish", "post to", "send from", "share to", "upload to")


def check_owned_channels(unit: Unit) -> list[Violation]:
    violations: list[Violation] = []
    rule = "growth and social publish only from the customer's connected accounts"

    publishes = Capability.PUBLISH in unit.capabilities or any(
        marker in s.description.lower()
        for s in unit.plan
        for marker in _PUBLISHING_STEP_MARKERS
    )
    if not publishes:
        return violations

    declared = {c.key for c in unit.config_keys}
    if "connected_accounts" not in declared:
        violations.append(
            Violation(
                unit.id,
                rule,
                Severity.ERROR,
                "publishes but does not declare a connected_accounts config key",
            )
        )
    if not any(g.id == "SR-OWNED-CHANNELS" for g in unit.guardrails):
        violations.append(
            Violation(unit.id, rule, Severity.ERROR, "missing SR-OWNED-CHANNELS guardrail")
        )
    return violations


# --------------------------------------------------------------------------- #
# rule 1 -- config, not code
# --------------------------------------------------------------------------- #

#: Names the workbook explicitly globalised.  A spec that still contains one has
#: hard-coded a market, which is exactly what the localisation sheet removed.
_DEGLOBALISED_TERMS = {
    "dha": "Health-Marketing Guardrail (was DHA Comms Guardrail)",
    "rera": "Listing & Tenancy Compliance Checker (was RERA Compliance Checker)",
    "icp": "Consular/Portal Slot Watcher (was Embassy/ICP Slot Watcher)",
    "uae ct": "Jurisdiction Tax Calendar (was UAE CT/VAT Deadline Calendar)",
    "attestation chain": "Apostille & Legalization Chain",
}

#: Market-specific values that belong in a country pack, not in a spec body.
_MARKET_LITERALS = (
    "whatsapp", "kakaotalk", "wechat", "zalo", "imessage", "line app",
    "yelp", "trustpilot", "tabelog", "dianping",
    "upi", "pix", "m-pesa", "mada", "sepa", "ideal", "fps",
    "mot ", "tüv", "tuv ", "shaken", "smog check", "ejari",
    "hipaa", "cqc", "gmc", "ahpra", "fca", "sec ", "esma",
    "ramadan", "diwali", "golden week",
)

# Fields where naming a market is legitimate: the catalogue itself uses these
# names when describing what a config key resolves.
_CONFIG_CONTEXT = ("country pack", "config", "per market", "localis", "localiz")


def check_config_not_code(unit: Unit) -> list[Violation]:
    violations: list[Violation] = []
    rule = "config, not code"

    body = "\n".join(
        [unit.mission, *(s.description for s in unit.plan), *(a.description for a in unit.artifacts)]
    )
    lowered = body.lower()

    for term, replacement in _DEGLOBALISED_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            violations.append(
                Violation(
                    unit.id,
                    rule,
                    Severity.ERROR,
                    f"de-globalised term {term!r} present; use {replacement}",
                )
            )

    for literal in _MARKET_LITERALS:
        if literal not in lowered:
            continue
        # Naming a market literal is fine when the sentence is about resolving it
        # from configuration; it is a breach when it is stated as fact.
        window_ok = False
        for match in re.finditer(re.escape(literal), lowered):
            window = lowered[max(0, match.start() - 160) : match.end() + 160]
            if any(hint in window for hint in _CONFIG_CONTEXT):
                window_ok = True
        if not window_ok:
            violations.append(
                Violation(
                    unit.id,
                    rule,
                    Severity.WARNING,
                    f"market literal {literal.strip()!r} stated outside a config context",
                )
            )
    return violations


# --------------------------------------------------------------------------- #
# structural completeness
# --------------------------------------------------------------------------- #


def check_structure(unit: Unit) -> list[Violation]:
    violations: list[Violation] = []
    rule = "spec completeness"

    def error(detail: str) -> None:
        violations.append(Violation(unit.id, rule, Severity.ERROR, detail))

    if not unit.mission.strip():
        error("empty mission")
    if not unit.function.strip():
        error("empty function")
    if not unit.expected_output.strip():
        error("empty expected output")
    if not unit.acceptance:
        error("no acceptance criteria")
    if not unit.artifacts:
        error("no artefacts")
    if not unit.plan:
        error("empty plan")
    if not unit.guardrails:
        error("no guardrails")
    if not unit.config_keys:
        error("no config keys")

    if unit.plan and unit.plan[-1].kind not in (StepKind.RECORD, StepKind.STOP):
        error(f"plan ends in {unit.plan[-1].kind.value}, expected record or stop")

    if not any(s.kind is StepKind.RECORD for s in unit.plan):
        error("plan has no record step; artefacts would not be persisted")

    produced = {key for s in unit.plan for key in s.produces}
    declared = {a.key for a in unit.artifacts}
    orphaned = produced - declared
    if orphaned:
        error(f"plan produces undeclared artefacts: {sorted(orphaned)}")

    if unit.type.is_agent and not (unit.worker and unit.system_agent):
        error("agent without a worker title or system agent name")
    if unit.type.is_playbook and not unit.trigger:
        error("playbook without a trigger")

    step_ids = [s.id for s in unit.plan]
    if len(step_ids) != len(set(step_ids)):
        error("duplicate step ids")

    return violations


# --------------------------------------------------------------------------- #
# entry points
# --------------------------------------------------------------------------- #

CHECKS = (
    check_structure,
    check_probabilistic_authority,
    check_safety_protocol,
    check_owned_channels,
    check_config_not_code,
)


def audit_unit(unit: Unit) -> list[Violation]:
    """Run every standing-rule check against one unit."""
    violations: list[Violation] = []
    for check in CHECKS:
        violations.extend(check(unit))
    return violations


def audit(units: Iterable[Unit]) -> list[Violation]:
    """Run every standing-rule check against a collection of units."""
    violations: list[Violation] = []
    for unit in units:
        violations.extend(audit_unit(unit))
    return violations


def errors(violations: Sequence[Violation]) -> list[Violation]:
    return [v for v in violations if v.severity is Severity.ERROR]


def warnings(violations: Sequence[Violation]) -> list[Violation]:
    return [v for v in violations if v.severity is Severity.WARNING]


__all__ = [
    "CHECKS",
    "Severity",
    "Violation",
    "audit",
    "audit_unit",
    "check_config_not_code",
    "check_owned_channels",
    "check_probabilistic_authority",
    "check_safety_protocol",
    "check_structure",
    "errors",
    "warnings",
]
