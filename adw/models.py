"""Typed model of the ADW catalogue.

Every automation unit in the workbook -- agent or playbook -- becomes a
:class:`Unit`.  A unit is inert data: it names a worker, the artefacts that
worker must produce, the mechanism family that carries it, and the decisions
that stay with a human.  Behaviour lives in the fourteen engines; a unit only
configures one.

The dataclasses here are the contract between three layers that are otherwise
independent:

* ``tools/build_catalogue.py`` writes the normalised catalogue.
* ``tools/generate_agents.py`` writes one YAML spec per unit.
* ``adw.registry`` loads those specs back and hands them to an engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

# --------------------------------------------------------------------------- #
# enumerations
# --------------------------------------------------------------------------- #


class UnitType(str, Enum):
    """The four kinds of automation unit the workbook distinguishes."""

    CORE_WORKER = "core_worker"
    SPECIALIST = "specialist"
    PLAYBOOK_UNIVERSAL = "playbook_universal"
    PLAYBOOK_VERTICAL = "playbook_vertical"

    @property
    def is_playbook(self) -> bool:
        return self in (UnitType.PLAYBOOK_UNIVERSAL, UnitType.PLAYBOOK_VERTICAL)

    @property
    def is_agent(self) -> bool:
        return not self.is_playbook


class StepKind(str, Enum):
    """What a plan step does.

    The distinction matters to the guardrail layer: ``DECIDE`` and ``ACT`` steps
    are the only ones that can breach the standing rule on probabilistic
    components, and ``GATE`` steps are the only ones that may resolve a human
    gate.
    """

    OBSERVE = "observe"  # watch a signal, read a queue, receive an event
    GATHER = "gather"  # collect structured detail, documents, photos
    ASSESS = "assess"  # score, grade, match, compare against a rule
    DECIDE = "decide"  # branch on the assessment
    DRAFT = "draft"  # compose something a human will approve
    ACT = "act"  # write to a system of record, send, book, publish
    NOTIFY = "notify"  # tell a person or a channel
    RECORD = "record"  # persist the artefact and the audit trail
    GATE = "gate"  # stop and hand the decision to a human
    STOP = "stop"  # terminal: the unit's work is finished


class Capability(str, Enum):
    """Coarse capability tags used for tool grants and risk review."""

    CONVERSE = "converse"
    SCORE = "score"
    SCHEDULE = "schedule"
    DISPATCH = "dispatch"
    COLLECT_DOCUMENTS = "collect_documents"
    ASSESS_MEDIA = "assess_media"
    WATCH_SIGNAL = "watch_signal"
    RECONCILE = "reconcile"
    SEQUENCE = "sequence"
    CLOCK = "clock"
    QUEUE_TRIAGE = "queue_triage"
    CASE_STATE = "case_state"
    TELEPHONY = "telephony"
    PUBLISH = "publish"
    GENERATE_CREATIVE = "generate_creative"
    RUN_PROTOCOL = "run_protocol"


class GateSeverity(str, Enum):
    """How hard a human gate blocks."""

    ADVISORY = "advisory"  # agent proceeds, human is informed
    BLOCKING = "blocking"  # agent stops until a human decides
    ABSOLUTE = "absolute"  # protocol runs to a fixed stop; no discretion exists


class Escalation(str, Enum):
    """Where a blocked unit goes."""

    OWNER = "owner"
    APPROVAL_QUEUE = "approval_queue"  # B3 Executive Assistant
    HUMAN_HANDOFF = "human_handoff"  # A12 Handover Clerk
    EMERGENCY_SERVICES = "emergency_services"
    REGULATOR_CONTACT = "regulator_contact"
    NAMED_ROLE = "named_role"


# --------------------------------------------------------------------------- #
# standing rules
# --------------------------------------------------------------------------- #

#: Verbs a probabilistic component may perform on its own authority.
PERMITTED_ACTS: frozenset[str] = frozenset({"flag", "collect", "draft"})

#: Verbs a probabilistic component may never perform on its own authority.
#: Straight from the workbook's standing rules: "Flag, collect, draft - never
#: clear, diagnose, advise, approve."
PROHIBITED_ACTS: frozenset[str] = frozenset({"clear", "diagnose", "advise", "approve"})

#: Substrings that mark a step as performing a prohibited act.  Matched against
#: the step description by :mod:`adw.guardrails`.
PROHIBITED_ACT_MARKERS: Mapping[str, tuple[str, ...]] = {
    "clear": ("clear the", "mark as safe", "declare safe", "sign off", "pass as compliant"),
    "diagnose": ("diagnose", "clinical opinion", "root-cause verdict", "medical assessment"),
    "advise": ("advise the customer", "legal advice", "financial advice", "medical advice"),
    "approve": ("approve the", "grant approval", "authorise payment", "authorize payment"),
}

#: Nouns that turn "published" into an adjective about the business's own
#: reference data.  "Quote only from the published price book" is the pricing
#: rule being obeyed, not an act of publishing to a channel, and conflating the
#: two would attach a connected-accounts grant to units that never publish --
#: which would make the customer-owned-channels rule mean nothing.
_PUBLISHED_AS_ADJECTIVE = (
    "price", "prices", "pricing", "terms", "policy", "policies", "criteria",
    "rate", "rates", "tariff", "tariffs", "hours", "fee", "fees", "schedule",
)

#: Matches a step that puts something out into the world on the customer's
#: behalf.  Shared by ``engines.base`` (which attaches the grant) and
#: ``adw.guardrails`` (which demands it), so the two cannot drift apart.
PUBLISHING_STEP_PATTERN = re.compile(
    # The noun may sit a couple of words after "published" -- "the published
    # cancellation fees" is still reference data, not an act of publishing.
    r"\bpublish(?:es|ed|ing)?\b(?!(?:\s+[\w-]+){0,2}\s+(?:"
    + "|".join(_PUBLISHED_AS_ADJECTIVE)
    + r")\b)"
    r"|\bpost(?:s|ed|ing)?\s+(?:it\s+)?to\b"
    r"|\bsend(?:s|ing)?\s+from\b"
    r"|\bshare(?:s|d|ing)?\s+to\b"
    r"|\bupload(?:s|ed|ing)?\s+to\b"
    r"|\bgoes?\s+live\s+on\b",
    re.IGNORECASE,
)


def describes_publishing(text: str) -> bool:
    """True when a step description publishes or sends on the customer's behalf."""
    return bool(PUBLISHING_STEP_PATTERN.search(text or ""))


# --------------------------------------------------------------------------- #
# reference tables
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MechanismFamily:
    """One of the fourteen engines.  Every unit binds to exactly one."""

    id: str
    number: int
    family: str
    what_it_does: str
    status: str
    slug: str
    module: str

    @property
    def is_new(self) -> bool:
        return self.status.upper().startswith("NEW")


@dataclass(frozen=True)
class Archetype:
    """A funnel shape.  Determines which agents anchor a roster."""

    id: str
    letter: str
    name: str
    recognise_by: str
    primary_lever: str
    anchor_agents: tuple[str, ...]
    slug: str


@dataclass(frozen=True)
class Vertical:
    """One of the sixty industry clusters."""

    id: str
    number: int
    name: str
    slug: str
    segment: str
    examples: tuple[str, ...]
    archetypes: tuple[str, ...]
    specialist_ids: tuple[str, ...]
    playbook_ids: tuple[str, ...]

    @property
    def is_enterprise(self) -> bool:
        return "Enterprise" in self.segment


@dataclass(frozen=True)
class Department:
    """One of the ten universal-core departments."""

    id: str
    name: str
    slug: str
    prefix: str
    unit_ids: tuple[str, ...]
    headcount: int


@dataclass(frozen=True)
class EdgeCaseDomain:
    """One of the nine universal edge-case domains."""

    id: str
    name: str
    slug: str
    prefix: str
    unit_ids: tuple[str, ...]
    playbook_count: int


# --------------------------------------------------------------------------- #
# unit parts
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Artifact:
    """A named thing the unit must produce.  Artefacts are the acceptance test."""

    key: str
    name: str
    description: str
    format: str = "record"
    retained: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "format": self.format,
            "retained": self.retained,
        }


@dataclass(frozen=True)
class AcceptanceCriterion:
    """One clause of the workbook's Expected output, made independently checkable."""

    id: str
    criterion: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "criterion": self.criterion, "evidence": self.evidence}


@dataclass(frozen=True)
class Step:
    """One step of an engine's plan for a unit."""

    id: str
    name: str
    kind: StepKind
    description: str
    produces: tuple[str, ...] = ()
    interlock: bool = False  # cannot be skipped, reordered or run late

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "kind": self.kind.value,
            "description": self.description,
        }
        if self.produces:
            data["produces"] = list(self.produces)
        if self.interlock:
            data["interlock"] = True
        return data


@dataclass(frozen=True)
class Guardrail:
    """A rule the unit must not breach, with the check that enforces it."""

    id: str
    rule: str
    check: str
    source: str = "standing_rule"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "rule": self.rule, "check": self.check, "source": self.source}


@dataclass(frozen=True)
class HumanGate:
    """A decision the workbook reserves for a person."""

    decision: str
    severity: GateSeverity
    escalate_to: Escalation
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = {
            "decision": self.decision,
            "severity": self.severity.value,
            "escalate_to": self.escalate_to.value,
        }
        if self.note:
            data["note"] = self.note
        return data


@dataclass(frozen=True)
class ConfigKey:
    """A country- or vertical-resolved setting.  Config, not code."""

    key: str
    description: str
    required: bool = False
    default: Any = None
    resolved_by: str = "country_pack"  # country_pack | vertical | owner

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "key": self.key,
            "description": self.description,
            "resolved_by": self.resolved_by,
        }
        if self.required:
            data["required"] = True
        if self.default is not None:
            data["default"] = self.default
        return data


@dataclass(frozen=True)
class Scope:
    """Where a unit applies."""

    department_id: str | None = None
    department_name: str | None = None
    vertical_id: str | None = None
    vertical_name: str | None = None
    segment: str | None = None
    domain_id: str | None = None
    domain_name: str | None = None
    archetypes: tuple[str, ...] = ()

    @property
    def is_universal(self) -> bool:
        return self.vertical_id is None


@dataclass(frozen=True)
class Flags:
    revenue_critical: bool = False
    safety_critical: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "revenue_critical": self.revenue_critical,
            "safety_critical": self.safety_critical,
        }


# --------------------------------------------------------------------------- #
# the unit
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Unit:
    """A fully-specified automation unit: one row of the master sheet, expanded.

    ``worker``/``system_agent`` are set for agents; ``trigger`` is set for
    playbooks.  Both carry an engine binding, a plan, artefacts, acceptance
    criteria, guardrails and human gates.
    """

    id: str
    type: UnitType
    scope: Scope
    mechanism_family: str
    function: str
    expected_output: str
    acceptance: tuple[AcceptanceCriterion, ...]
    flags: Flags

    worker: str | None = None
    system_agent: str | None = None
    trigger: str | None = None

    mission: str = ""
    inputs: tuple[str, ...] = ()
    artifacts: tuple[Artifact, ...] = ()
    plan: tuple[Step, ...] = ()
    guardrails: tuple[Guardrail, ...] = ()
    human_gates: tuple[HumanGate, ...] = ()
    config_keys: tuple[ConfigKey, ...] = ()
    tools: tuple[str, ...] = ()
    capabilities: tuple[Capability, ...] = ()
    kpis: tuple[str, ...] = ()
    channels: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    engine_profile: str = "default"
    engine_config: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)
    path: str = ""
    version: int = 1

    # -- identity ----------------------------------------------------------
    @property
    def display_name(self) -> str:
        if self.type.is_playbook:
            return f"{self.id} {self.trigger}"
        if self.worker and self.system_agent and self.worker != self.system_agent:
            return f"{self.worker} ({self.system_agent})"
        return self.worker or self.system_agent or self.id

    @property
    def name(self) -> str:
        return self.trigger if self.type.is_playbook else (self.worker or self.id)

    @property
    def is_playbook(self) -> bool:
        return self.type.is_playbook

    # -- posture -----------------------------------------------------------
    @property
    def is_safety_critical(self) -> bool:
        return self.flags.safety_critical

    @property
    def is_revenue_critical(self) -> bool:
        return self.flags.revenue_critical

    @property
    def is_recognition_only(self) -> bool:
        """Safety-critical protocols recognise and route; they never resolve.

        The workbook's legend is explicit: a diamond marks a "safety-critical
        protocol: recognition and routing only".
        """
        return self.flags.safety_critical

    @property
    def blocking_gates(self) -> tuple[HumanGate, ...]:
        return tuple(
            g for g in self.human_gates if g.severity is not GateSeverity.ADVISORY
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the on-disk YAML shape."""
        data: dict[str, Any] = {
            "id": self.id,
            "version": self.version,
            "kind": "playbook" if self.is_playbook else "agent",
            "type": self.type.value,
            "display_name": self.display_name,
        }
        if self.worker:
            data["worker"] = self.worker
        if self.system_agent:
            data["system_agent"] = self.system_agent
        if self.trigger:
            data["trigger"] = self.trigger
        data["scope"] = {
            k: v
            for k, v in {
                "department": (
                    {"id": self.scope.department_id, "name": self.scope.department_name}
                    if self.scope.department_id
                    else None
                ),
                "vertical": (
                    {
                        "id": self.scope.vertical_id,
                        "name": self.scope.vertical_name,
                        "segment": self.scope.segment,
                    }
                    if self.scope.vertical_id
                    else None
                ),
                "domain": (
                    {"id": self.scope.domain_id, "name": self.scope.domain_name}
                    if self.scope.domain_id
                    else None
                ),
                "archetypes": list(self.scope.archetypes) or None,
            }.items()
            if v is not None
        }
        data["engine"] = {
            "mechanism_family": self.mechanism_family,
            "profile": self.engine_profile,
            "config": dict(self.engine_config),
        }
        data["flags"] = self.flags.to_dict()
        data["function"] = self.function
        data["mission"] = self.mission
        data["expected_output"] = self.expected_output
        data["acceptance"] = [a.to_dict() for a in self.acceptance]
        data["inputs"] = list(self.inputs)
        data["artifacts"] = [a.to_dict() for a in self.artifacts]
        data["plan"] = [s.to_dict() for s in self.plan]
        data["guardrails"] = [g.to_dict() for g in self.guardrails]
        data["human_gates"] = [g.to_dict() for g in self.human_gates]
        data["capabilities"] = [c.value for c in self.capabilities]
        data["tools"] = list(self.tools)
        data["channels"] = list(self.channels)
        data["config_keys"] = [c.to_dict() for c in self.config_keys]
        data["kpis"] = list(self.kpis)
        if self.depends_on:
            data["depends_on"] = list(self.depends_on)
        data["provenance"] = dict(self.provenance)
        return data


# --------------------------------------------------------------------------- #
# runtime context
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class BusinessProfile:
    """The customer a roster is being assembled for."""

    name: str
    vertical_id: str
    country: str = "US"
    segment: str | None = None
    archetypes: tuple[str, ...] = ()
    channels: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    enabled_units: tuple[str, ...] = ()
    disabled_units: tuple[str, ...] = ()


@dataclass(frozen=True)
class CountryPack:
    """Resolved localisation configuration for one market."""

    code: str
    name: str
    languages: tuple[str, ...]
    messaging_channels: tuple[str, ...]
    review_surfaces: tuple[str, ...]
    attach_to_platforms: tuple[str, ...]
    payment_rails: tuple[str, ...]
    tax_calendar: tuple[str, ...]
    statutory_date_sets: tuple[str, ...]
    regulator_guardrails: tuple[str, ...]
    seasonal_calendar: tuple[str, ...]
    settings: Mapping[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, getattr(self, key, default))


@dataclass
class RunContext:
    """Everything an engine needs beyond the unit itself."""

    business: BusinessProfile
    country_pack: CountryPack
    now: str | None = None
    overrides: Mapping[str, Any] = field(default_factory=dict)

    def config(self, key: str, default: Any = None) -> Any:
        if key in self.overrides:
            return self.overrides[key]
        return self.country_pack.get(key, default)


__all__ = [
    "AcceptanceCriterion",
    "Archetype",
    "Artifact",
    "BusinessProfile",
    "Capability",
    "ConfigKey",
    "CountryPack",
    "Department",
    "EdgeCaseDomain",
    "Escalation",
    "Flags",
    "GateSeverity",
    "Guardrail",
    "HumanGate",
    "MechanismFamily",
    "PERMITTED_ACTS",
    "PROHIBITED_ACTS",
    "PROHIBITED_ACT_MARKERS",
    "PUBLISHING_STEP_PATTERN",
    "describes_publishing",
    "RunContext",
    "Scope",
    "Step",
    "StepKind",
    "Unit",
    "UnitType",
    "Vertical",
]
