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
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

import yaml

from adw.models import (
    PROHIBITED_ACT_MARKERS,
    Capability,
    GateSeverity,
    StepKind,
    Unit,
    describes_publishing,
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


def check_mission_is_self_contained(unit: Unit) -> list[Violation]:
    """The mission is the only field that reaches a runtime.

    At execution time the mission becomes the system prompt; the rest of the
    spec -- artefact list, config keys, acceptance criteria -- is not in front
    of the model. So a contract stated only in the YAML is a contract the model
    never sees. Driven through an external model, a unit whose mission did not
    name its artefacts invented its own set and produced no audit trail at all,
    which breaks everything downstream keyed on the declared keys.
    """
    violations: list[Violation] = []
    rule = "mission carries the whole contract"
    mission = unit.mission

    missing = [a.key for a in unit.artifacts if a.key not in mission]
    if missing:
        violations.append(
            Violation(
                unit.id,
                rule,
                Severity.ERROR,
                f"mission does not name {len(missing)} declared artefact key(s): {missing[:4]}",
            )
        )

    unnamed = [a.name for a in unit.artifacts if a.name not in mission]
    if unnamed:
        violations.append(
            Violation(
                unit.id,
                rule,
                Severity.ERROR,
                f"mission does not name {len(unnamed)} artefact(s) by name: {unnamed[:3]}",
            )
        )

    # The anti-fabrication rule is what stops a unit reciting a jurisdiction
    # value it recognises from training instead of reading the pack.
    lowered = mission.lower()
    if "from your own knowledge" not in lowered:
        violations.append(
            Violation(unit.id, rule, Severity.ERROR, "mission omits the anti-fabrication rule")
        )
    if "a gate, not a gap" not in lowered:
        violations.append(
            Violation(
                unit.id,
                rule,
                Severity.ERROR,
                "mission does not say a missing setting is a gate rather than a gap to fill",
            )
        )
    return violations


def check_hard_interlock(unit: Unit) -> list[Violation]:
    """A no-override rule must be a step, not a sentence.

    The workbook writes "None - interlock" where nobody may wave the case
    through. Composition turns that into an absolute gate; this verifies the
    plan actually enforces it, independently of how it was composed.
    """
    absolute = [
        g
        for g in unit.human_gates
        if g.severity is GateSeverity.ABSOLUTE and "interlock" in g.decision.lower()
    ]
    if not absolute:
        return []

    violations: list[Violation] = []
    rule = "hard interlock: no override exists"
    interlocks = [s for s in unit.plan if s.interlock]
    if not interlocks:
        violations.append(
            Violation(unit.id, rule, Severity.ERROR, "absolute interlock gate with no interlock step")
        )
    elif unit.plan[0] is not interlocks[0]:
        violations.append(
            Violation(unit.id, rule, Severity.ERROR, "interlock step does not run first")
        )
    if not any(g.id in ("GR-HARD-INTERLOCK", "GR-SAFETY-INTERLOCK") for g in unit.guardrails):
        violations.append(
            Violation(unit.id, rule, Severity.ERROR, "no interlock guardrail attached")
        )
    return violations


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

def check_owned_channels(unit: Unit) -> list[Violation]:
    violations: list[Violation] = []
    rule = "growth and social publish only from the customer's connected accounts"

    # Detection is shared with the engine layer via describes_publishing, so the
    # side that attaches the grant and the side that demands it cannot drift.
    publishes = Capability.PUBLISH in unit.capabilities or any(
        describes_publishing(s.description) for s in unit.plan
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

def _load_deglobalised_terms() -> dict[str, str]:
    """The agent names the workbook retired, mapped to their replacements.

    Read from the Localization sheet rather than hard-coded, so the check stays
    in step with the workbook: globalise another agent there and this check
    starts guarding the old name on the next build.

    Only the retired *names* are guarded, never the domain vocabulary inside
    them.  "Attestation Chain Tracker" was a UAE-anchored agent name and is
    banned; "attestation" is what the process is called in half the world's
    jurisdictions and is perfectly fine.
    """
    path = Path(__file__).resolve().parent.parent / "catalogue" / "localization.yaml"
    if not path.exists():  # the audit must still run without the catalogue
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    terms: dict[str, str] = {}
    for entry in data.get("globalized_agents", ()):
        former = str(entry.get("formerly", "")).strip()
        # Drop a trailing parenthetical qualifier: the banned thing is the name.
        former = re.sub(r"\s*\(.*\)$", "", former).strip()
        if former:
            terms[former.lower()] = entry["system_agent"]
    return terms


#: Names the workbook explicitly globalised.  A spec that still contains one has
#: hard-coded a market, which is exactly what the Localization sheet removed.
_DEGLOBALISED_TERMS = _load_deglobalised_terms()

#: Market-specific values that belong in a country pack, not in a spec body.
#: Several are short enough to hide inside ordinary words -- "sepa" in
#: "separately", "fps" in "RFPs", "line app" in "deadline approaching", "mot" in
#: "motor" -- so they are matched on word boundaries. Substring matching here
#: produced nothing but false positives.
_MARKET_LITERALS = (
    "whatsapp", "kakaotalk", "wechat", "zalo", "imessage", "line app",
    "yelp", "trustpilot", "tabelog", "dianping",
    "upi", "pix", "m-pesa", "mada", "sepa", "ideal", "fps",
    "mot", "tüv", "tuv", "shaken", "smog check", "ejari",
    "hipaa", "cqc", "gmc", "ahpra", "fca", "sec", "esma",
    "ramadan", "diwali", "golden week",
)

_MARKET_LITERAL_PATTERNS = tuple(
    (literal, re.compile(rf"\b{re.escape(literal)}\b", re.IGNORECASE))
    for literal in _MARKET_LITERALS
)

# Contexts where naming a market is legitimate: the catalogue itself enumerates
# instances when it is describing what a config key resolves to. "MOT / TUV /
# shaken / smog per market" is the config-not-code rule being followed, not
# broken.
_CONFIG_CONTEXT = (
    "country pack",
    "config",
    "per market",
    "per regulator",
    "per jurisdiction",
    "localis",
    "localiz",
    "active pack",
)


@lru_cache(maxsize=1)
def _pack_keys() -> tuple[frozenset[str], tuple[str, ...]]:
    """Every key each country pack answers, and the pack codes.

    Returns the keys present in *every* pack, plus the pack codes, so the two
    halves of the resolution rule can be checked separately: a key required by a
    unit has to be answerable wherever that unit runs, not just somewhere.
    """
    packs_dir = Path(__file__).resolve().parent.parent / "packs" / "countries"
    if not packs_dir.exists():
        return frozenset(), ()
    per_pack: list[set[str]] = []
    codes: list[str] = []
    for path in sorted(packs_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        keys = set(data) | set(data.get("settings") or {})
        keys.discard("settings")
        per_pack.append(keys)
        codes.append(path.stem.upper())
    if not per_pack:
        return frozenset(), ()
    return frozenset(set.intersection(*per_pack)), tuple(codes)


def check_config_resolves(unit: Unit) -> list[Violation]:
    """A declared config key must actually resolve to something.

    Declaring a key is a promise that a value exists to be read. Where it does
    not, the unit reaches runtime, finds nothing, and fills the hole from the
    model's own knowledge -- which is exactly the hard-coding the config-not-code
    rule exists to prevent, only now it is non-deterministic. Declaring the key
    without populating it is worse than not declaring it, because the spec reads
    as though the value is handled.
    """
    violations: list[Violation] = []
    rule = "declared config resolves"
    universal, codes = _pack_keys()
    if not codes:  # no packs on disk; nothing to check against
        return violations

    for key in unit.config_keys:
        if key.resolved_by != "country_pack":
            continue
        if key.key in universal:
            continue
        severity = Severity.ERROR if key.required else Severity.WARNING
        violations.append(
            Violation(
                unit.id,
                rule,
                severity,
                f"config key {key.key!r} is declared"
                + (" and required" if key.required else "")
                + " but no country pack defines it",
            )
        )
    return violations


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

    for literal, pattern in _MARKET_LITERAL_PATTERNS:
        matches = list(pattern.finditer(lowered))
        if not matches:
            continue
        # Naming a market literal is fine when the sentence is about resolving it
        # from configuration; it is a breach when it is stated as fact.
        window_ok = any(
            hint in lowered[max(0, m.start() - 160) : m.end() + 160]
            for m in matches
            for hint in _CONFIG_CONTEXT
        )
        if not window_ok:
            violations.append(
                Violation(
                    unit.id,
                    rule,
                    Severity.WARNING,
                    f"market literal {literal!r} stated outside a config context",
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
    check_mission_is_self_contained,
    check_probabilistic_authority,
    check_safety_protocol,
    check_hard_interlock,
    check_owned_channels,
    check_config_not_code,
    check_config_resolves,
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
    "check_config_resolves",
    "check_hard_interlock",
    "check_mission_is_self_contained",
    "check_owned_channels",
    "check_probabilistic_authority",
    "check_safety_protocol",
    "check_structure",
    "errors",
    "warnings",
]
