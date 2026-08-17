"""The engine contract.

The catalogue's first standing rule is *config, not code*: fourteen engines carry
all 815 units, and vertical and country differences resolve to configuration.
This module is where that rule is made structural.

An :class:`Engine` knows how one mechanism family behaves.  It does not know
about any individual agent.  Given a catalogue record it *composes* a
:class:`~adw.models.Unit`: it picks a profile, writes the mission, lays out the
plan, names the artefacts, attaches the guardrails and declares which
configuration keys the unit reads.  Adding an agent to the catalogue therefore
means adding a row to the workbook, never a new class.

Subclasses implement five hooks:

``profiles``      the presets this family offers, in match order
``base_plan``     the step skeleton every unit of this family runs
``base_artifacts``the artefacts every unit of this family produces
``mission_body``  family-specific mission prose
``family_guardrails`` rules that apply to every unit of this family

Everything else -- acceptance criteria, standing-rule guardrails, human gates,
safety interlocks, provenance -- is assembled by :meth:`Engine.compose`, so it is
identical across all fourteen families and cannot drift.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Iterable, Mapping, Sequence

from adw.models import (
    AcceptanceCriterion,
    Artifact,
    Capability,
    ConfigKey,
    Escalation,
    Flags,
    GateSeverity,
    Guardrail,
    HumanGate,
    Scope,
    Step,
    StepKind,
    Unit,
    UnitType,
    describes_publishing,
)

# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Profile:
    """A preset within a mechanism family.

    Profiles are how one engine covers dozens of differently-named workers.  The
    Front Desk's Receptionist, Eligibility Officer and Night Dispatcher are all
    MF1 units; they differ by profile, and a profile is pure configuration.
    """

    name: str
    summary: str
    #: Lowercase substrings matched against the unit's name, system agent name
    #: and function.  First profile with a hit wins, so order matters.
    match: tuple[str, ...] = ()
    steps: tuple[Step, ...] = ()
    artifacts: tuple[Artifact, ...] = ()
    tools: tuple[str, ...] = ()
    config_keys: tuple[ConfigKey, ...] = ()
    kpis: tuple[str, ...] = ()
    channels: tuple[str, ...] = ()

    def matches(self, haystack: str) -> bool:
        return any(token in haystack for token in self.match)


# --------------------------------------------------------------------------- #
# standing-rule guardrails, applied to every unit of every family
# --------------------------------------------------------------------------- #

STANDING_GUARDRAILS: tuple[Guardrail, ...] = (
    Guardrail(
        id="SR-PROBABILISTIC",
        rule=(
            "Probabilistic components flag, collect and draft. They never clear, "
            "diagnose, advise or approve."
        ),
        check=(
            "No plan step of kind decide or act may perform a prohibited act "
            "without a preceding blocking human gate."
        ),
    ),
    Guardrail(
        id="SR-OWNED-CHANNELS",
        rule=(
            "Growth and social output publishes only from the customer's own "
            "connected accounts."
        ),
        check=(
            "Every publish or send step names a channel held in the customer's "
            "OAuth grant; no platform account owned by ADW is ever the sender."
        ),
    ),
    Guardrail(
        id="SR-CONFIG-NOT-CODE",
        rule=(
            "Vertical and country differences resolve to configuration; the unit "
            "carries no market-specific logic."
        ),
        check=(
            "Every market-dependent value the unit reads is declared in "
            "config_keys and resolved from the active country pack."
        ),
    ),
    Guardrail(
        id="SR-AUDIT",
        rule="Every artefact the unit produces is retained with its audit trail.",
        check=(
            "The plan ends in a record step and each declared artefact is written "
            "with actor, timestamp and source."
        ),
    ),
)

#: Attached to units whose expected output names a number, a price or a quote.
PRICING_GUARDRAIL = Guardrail(
    id="GR-PUBLISHED-PRICES-ONLY",
    rule="Money figures come from published pricing. The unit never invents a number.",
    check=(
        "Every figure in the artefact resolves to a row in the published price "
        "book or to a quote already issued by the business."
    ),
    source="catalogue",
)

#: Attached to every safety-critical (diamond) unit.
SAFETY_GUARDRAIL = Guardrail(
    id="GR-SAFETY-INTERLOCK",
    rule=(
        "Safety-critical protocol: recognition and routing only. The unit "
        "recognises the condition, executes the fixed steps and stops at the "
        "human gate. It never resolves the underlying situation."
    ),
    check=(
        "Interlock steps run first and cannot be skipped, reordered or deferred; "
        "the plan terminates in a gate or stop step, never in a resolution."
    ),
    source="catalogue",
)

#: Attached to units the workbook marks "None - interlock": a rule with no
#: override, on a unit that is not otherwise a safety protocol.
HARD_INTERLOCK_GUARDRAIL = Guardrail(
    id="GR-HARD-INTERLOCK",
    rule=(
        "The interlock holds absolutely. No override exists - not for the "
        "customer, not for staff, not for the owner, and not for this unit."
    ),
    check=(
        "The interlock step runs first and its block stays applied until the "
        "underlying condition is satisfied on the evidence the rule requires; "
        "no path through the plan lifts it on anyone's say-so."
    ),
    source="catalogue",
)

#: Attached to units that touch regulated advice surfaces.
REGULATED_GUARDRAIL = Guardrail(
    id="GR-REGULATED-SURFACE",
    rule=(
        "Regulated subject matter: the unit collects and routes, and never gives "
        "advice that a licensed person must give."
    ),
    check=(
        "Outbound copy is checked against the regulator guardrails in the active "
        "country pack before it leaves the queue."
    ),
    source="country_pack",
)

#: Config keys every unit reads, whatever its family.
UNIVERSAL_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="language_set",
        description="Languages the unit must answer in, from the active country pack.",
        required=True,
    ),
    ConfigKey(
        key="messaging_channel",
        description="Primary messaging rail for this market (WhatsApp, SMS/RCS, LINE, ...).",
        required=True,
    ),
    ConfigKey(
        key="business_hours",
        description="Opening hours and out-of-hours policy for the business.",
        resolved_by="owner",
    ),
    ConfigKey(
        key="escalation_contacts",
        description="Who receives a gate, by role, with an out-of-hours fallback.",
        resolved_by="owner",
        required=True,
    ),
)

# Terms that mark a unit as sitting on a regulated advice surface.
_REGULATED_MARKERS = (
    "clinical",
    "medical",
    "patient",
    "dental",
    "prescri",
    "legal",
    "matter",
    "advice",
    "regulat",
    "compliance",
    "licence",
    "license",
    "statutory",
    "kyc",
    "aml",
    "safeguard",
    "payor",
    "insurance",
    "financial",
    "tax",
    "audit",
    "visa",
    "immigration",
)

# Terms that mark a unit as handling money figures.
_PRICING_MARKERS = (
    "price",
    "pricing",
    "quote",
    "estimate",
    "invoice",
    "payment",
    "deposit",
    "refund",
    "fee",
    "cost",
    "tariff",
    "rate",
    "commission",
    "revenue",
    "cash",
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


class Engine(ABC):
    """Base class for the fourteen mechanism-family engines."""

    #: Mechanism family id, e.g. ``"MF1"``.
    id: ClassVar[str]
    #: Human name from the workbook, e.g. ``"Conversational intake & triage"``.
    family: ClassVar[str]
    #: One-line statement of what the family does.
    what_it_does: ClassVar[str]
    #: Capabilities every unit of this family holds.
    capabilities: ClassVar[tuple[Capability, ...]] = ()
    #: Tools every unit of this family is granted.
    default_tools: ClassVar[tuple[str, ...]] = ()
    #: Channels the family works over by default.
    default_channels: ClassVar[tuple[str, ...]] = ()
    #: KPIs reported for every unit of this family.
    default_kpis: ClassVar[tuple[str, ...]] = ()
    #: Config keys every unit of this family reads.
    config_keys: ClassVar[tuple[ConfigKey, ...]] = ()
    #: State object the family maintains, if any.
    state_object: ClassVar[str] = ""

    # -- hooks -------------------------------------------------------------
    @property
    @abstractmethod
    def profiles(self) -> tuple[Profile, ...]:
        """Presets offered by this family, in match order.

        The last profile must have an empty ``match`` tuple: it is the fallback.
        """

    @abstractmethod
    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """The step skeleton every unit of this family runs."""

    @abstractmethod
    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        """Artefacts every unit of this family produces."""

    @abstractmethod
    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        """Family-specific mission prose, woven into the composed mission."""

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        """Rules that apply to every unit of this family.  Optional."""
        return ()

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        """Inputs every unit of this family consumes.  Optional."""
        return ()

    # -- profile selection --------------------------------------------------
    def select_profile(self, record: Mapping[str, Any]) -> Profile:
        haystack = " ".join(
            str(part or "").lower()
            for part in (
                record.get("worker"),
                record.get("system_agent"),
                record.get("trigger"),
                record.get("function"),
                record.get("expected_output"),
            )
        )
        for profile in self.profiles:
            if profile.match and profile.matches(haystack):
                return profile
        fallback = self.profiles[-1]
        if fallback.match:
            raise AssertionError(
                f"{self.id}: last profile {fallback.name!r} must be the unconditional fallback"
            )
        return fallback

    # -- composition --------------------------------------------------------
    def compose(self, record: Mapping[str, Any]) -> Unit:
        """Turn one catalogue record into a fully-specified unit."""
        profile = self.select_profile(record)
        unit_type = UnitType(record["type"])
        flags = Flags(**record["flags"])

        scope = self._scope(record)
        artifacts = self._artifacts(record, profile)
        plan = self._plan(record, profile, flags)
        gates = self._human_gates(record, flags)
        guardrails = self._guardrails(record, flags)
        acceptance = self._acceptance(record)
        config_keys = self._config_keys(record, profile, plan)

        return Unit(
            id=record["id"],
            type=unit_type,
            scope=scope,
            mechanism_family=self.id,
            function=record["function"],
            expected_output=record["expected_output"],
            acceptance=acceptance,
            flags=flags,
            worker=record.get("worker"),
            system_agent=record.get("system_agent"),
            trigger=record.get("trigger"),
            mission=self._mission(record, profile, flags, gates, artifacts, config_keys),
            inputs=self._inputs(record, profile),
            artifacts=artifacts,
            plan=plan,
            guardrails=guardrails,
            human_gates=gates,
            config_keys=config_keys,
            tools=tuple(dict.fromkeys(self.default_tools + profile.tools)),
            capabilities=self.capabilities,
            kpis=tuple(dict.fromkeys(self.default_kpis + profile.kpis)),
            channels=tuple(dict.fromkeys(self.default_channels + profile.channels)),
            engine_profile=profile.name,
            engine_config=self._engine_config(record, profile),
            provenance={
                "workbook": "ADW_MASTER_AGENT_CATALOGUE.xlsx",
                "catalogue_version": "2",
                "unit_type": record["type"],
                "mechanism_family": self.id,
                "engine": type(self).__name__,
                "generated_by": "tools/generate_agents.py",
            },
            path=record["path"],
        )

    # -- composition parts --------------------------------------------------
    def _scope(self, record: Mapping[str, Any]) -> Scope:
        department = record.get("department") or {}
        vertical = record.get("vertical") or {}
        domain = record.get("domain") or {}
        return Scope(
            department_id=department.get("id"),
            department_name=department.get("name"),
            vertical_id=vertical.get("id"),
            vertical_name=vertical.get("name"),
            segment=vertical.get("segment"),
            domain_id=domain.get("id"),
            domain_name=domain.get("name"),
            archetypes=tuple(record.get("archetypes") or ()),
        )

    def _artifacts(
        self, record: Mapping[str, Any], profile: Profile
    ) -> tuple[Artifact, ...]:
        artifacts = list(self.base_artifacts(record)) + list(profile.artifacts)
        artifacts.extend(derive_artifacts(record))

        if record["flags"]["safety_critical"] or requires_hard_interlock(record):
            # The interlock step produces this, so it has to be a declared
            # artefact: on an interlocked unit the record of what the protocol
            # did, and when, is the deliverable.
            artifacts.append(
                Artifact(
                    key="interlock_log",
                    name="Safety interlock log",
                    description=(
                        "What the protocol recognised, which fixed steps ran, in what "
                        "order and at what time, and the point at which the unit "
                        "stopped and handed over."
                    ),
                    format="log",
                )
            )

        artifacts.append(
            Artifact(
                key="audit_trail",
                name="Audit trail",
                description=(
                    "Every action, gate and message with actor, timestamp and source, "
                    "retained for the life of the record."
                ),
                format="log",
            )
        )
        seen: dict[str, Artifact] = {}
        for artifact in artifacts:
            seen.setdefault(artifact.key, artifact)
        return tuple(seen.values())

    def _plan(
        self, record: Mapping[str, Any], profile: Profile, flags: Flags
    ) -> tuple[Step, ...]:
        steps = list(self.base_plan(record)) + list(profile.steps)

        if flags.safety_critical:
            # A diamond unit recognises and routes.  The interlock runs before
            # anything else and the plan can only terminate at a gate.
            steps = [
                Step(
                    id="interlock",
                    name="Run the safety interlock",
                    kind=StepKind.ACT,
                    description=(
                        "Recognise the condition and execute the fixed protocol steps "
                        "before any commercial step. The interlock cannot be skipped, "
                        "reordered or deferred, and no other step may run ahead of it."
                    ),
                    produces=("interlock_log",),
                    interlock=True,
                ),
                *steps,
            ]
        elif requires_hard_interlock(record):
            # Not a diamond: the unit does go on to finish its work.  But the
            # rule holds first and holds absolutely -- the workbook's own words
            # are "hard stop", "no override in the agent", "enforced until
            # renewed" -- so it is a step, not a sentence in the mission.
            steps = [
                Step(
                    id="interlock",
                    name="Enforce the hard interlock",
                    kind=StepKind.ACT,
                    description=(
                        "Apply the block, hold or restriction the rule demands before "
                        "anything else runs, and keep it applied until the underlying "
                        "condition is genuinely satisfied. There is no override: not "
                        "by the customer, not by staff, not by the owner, and not by "
                        "this unit. Record what was blocked and why."
                    ),
                    produces=("interlock_log",),
                    interlock=True,
                ),
                *steps,
            ]

        steps.append(
            Step(
                id="record",
                name="Record the artefacts",
                kind=StepKind.RECORD,
                description=(
                    "Write every declared artefact to the system of record with its "
                    "audit trail, then report the acceptance result."
                ),
                produces=("audit_trail",),
            )
        )

        if flags.safety_critical:
            steps.append(
                Step(
                    id="stop",
                    name="Stop at the human gate",
                    kind=StepKind.STOP,
                    description=(
                        "Hand the situation to the named human contact and stop. "
                        "The unit does not resolve, clear or close the underlying "
                        "condition under any circumstances."
                    ),
                )
            )

        # Renumber so ids are stable and ordered regardless of source.
        return tuple(
            Step(
                id=f"{record['id'].lower()}-s{index:02d}-{step.id}",
                name=step.name,
                kind=step.kind,
                description=step.description,
                produces=step.produces,
                interlock=step.interlock,
            )
            for index, step in enumerate(steps, start=1)
        )

    def _human_gates(
        self, record: Mapping[str, Any], flags: Flags
    ) -> tuple[HumanGate, ...]:
        gates: list[HumanGate] = []
        for raw in record.get("human_gates") or ():
            gates.append(build_human_gate(raw, flags))

        if flags.safety_critical and not any(
            g.severity is GateSeverity.ABSOLUTE for g in gates
        ):
            gates.append(
                HumanGate(
                    decision="Resolution of the safety condition itself",
                    severity=GateSeverity.ABSOLUTE,
                    escalate_to=Escalation.EMERGENCY_SERVICES,
                    note=(
                        "Recognition and routing only. Escalation is the product; "
                        "the unit stops here."
                    ),
                )
            )

        if not gates:
            gates.append(
                HumanGate(
                    decision="Anything outside the configured policy bounds",
                    severity=GateSeverity.BLOCKING,
                    escalate_to=Escalation.APPROVAL_QUEUE,
                    note=(
                        "The workbook reserves no named decision for this unit; the "
                        "policy boundary is still a gate."
                    ),
                )
            )
        return tuple(gates)

    def _guardrails(
        self, record: Mapping[str, Any], flags: Flags
    ) -> tuple[Guardrail, ...]:
        guardrails = list(STANDING_GUARDRAILS) + list(self.family_guardrails(record))
        haystack = _haystack(record)
        if flags.safety_critical:
            guardrails.append(SAFETY_GUARDRAIL)
        elif requires_hard_interlock(record):
            guardrails.append(HARD_INTERLOCK_GUARDRAIL)
        if any(marker in haystack for marker in _PRICING_MARKERS):
            guardrails.append(PRICING_GUARDRAIL)
        if any(marker in haystack for marker in _REGULATED_MARKERS):
            guardrails.append(REGULATED_GUARDRAIL)
        seen: dict[str, Guardrail] = {}
        for guardrail in guardrails:
            seen.setdefault(guardrail.id, guardrail)
        return tuple(seen.values())

    def _acceptance(self, record: Mapping[str, Any]) -> tuple[AcceptanceCriterion, ...]:
        criteria = []
        for index, clause in enumerate(record["acceptance_criteria"], start=1):
            criteria.append(
                AcceptanceCriterion(
                    id=f"{record['id']}-AC{index}",
                    criterion=clause,
                    evidence=evidence_for(clause),
                )
            )
        # Every unit is additionally accountable for its audit trail.
        criteria.append(
            AcceptanceCriterion(
                id=f"{record['id']}-AC{len(criteria) + 1}",
                criterion="Every action and gate is recorded with actor, timestamp and source",
                evidence="audit_trail entries covering the full run",
            )
        )
        return tuple(criteria)

    def _config_keys(
        self,
        record: Mapping[str, Any],
        profile: Profile,
        plan: Sequence[Step] = (),
    ) -> tuple[ConfigKey, ...]:
        keys = list(UNIVERSAL_CONFIG_KEYS) + list(self.config_keys) + list(profile.config_keys)

        # A unit that sends or publishes anything must name the grant it sends
        # under, or the customer-owned-channels rule is unenforceable.
        publishes = Capability.PUBLISH in self.capabilities or any(
            describes_publishing(step_.description) for step_ in plan
        )
        if publishes:
            keys.append(
                ConfigKey(
                    key="connected_accounts",
                    description=(
                        "OAuth grants for the customer's own accounts. Every publish "
                        "and every send leaves from one of these; the platform never "
                        "posts from an account it owns."
                    ),
                    resolved_by="owner",
                    required=True,
                )
            )

        if record.get("vertical"):
            keys.append(
                ConfigKey(
                    key="vertical_overlay",
                    description=(
                        f"Vertical overlay for {record['vertical']['name']}: intervals, "
                        "terminology, required fields and statutory dates."
                    ),
                    resolved_by="vertical",
                    required=True,
                )
            )
        haystack = _haystack(record)
        if any(marker in haystack for marker in _REGULATED_MARKERS):
            keys.append(
                ConfigKey(
                    key="regulator_guardrails",
                    description=(
                        "Advertising, claims and advice rules for this market's "
                        "regulator, from the active country pack."
                    ),
                    required=True,
                )
            )
        if any(marker in haystack for marker in _PRICING_MARKERS):
            keys.append(
                ConfigKey(
                    key="payment_rails",
                    description="Payment rails available in this market.",
                )
            )
            keys.append(
                ConfigKey(
                    key="published_price_book",
                    description="The only source of money figures this unit may quote.",
                    resolved_by="owner",
                    required=True,
                )
            )
        seen: dict[str, ConfigKey] = {}
        for key in keys:
            seen.setdefault(key.key, key)
        return tuple(seen.values())

    def _inputs(self, record: Mapping[str, Any], profile: Profile) -> tuple[str, ...]:
        inputs = list(self.family_inputs(record))
        if record.get("trigger"):
            inputs.insert(0, f"Trigger event: {record['trigger']}")
        if record.get("vertical"):
            inputs.append(f"Vertical overlay for {record['vertical']['name']}")
        inputs.append("Active country pack")
        inputs.append("Business profile: hours, services, policies, published prices")
        return tuple(dict.fromkeys(inputs))

    def _engine_config(
        self, record: Mapping[str, Any], profile: Profile
    ) -> dict[str, Any]:
        return {
            "profile": profile.name,
            "profile_summary": profile.summary,
            "state_object": self.state_object or None,
            "recognition_only": bool(record["flags"]["safety_critical"]),
            "revenue_critical": bool(record["flags"]["revenue_critical"]),
        }

    def _mission(
        self,
        record: Mapping[str, Any],
        profile: Profile,
        flags: Flags,
        gates: Sequence[HumanGate],
        artifacts: Sequence[Artifact] = (),
        config_keys: Sequence[ConfigKey] = (),
    ) -> str:
        """Compose the unit's operating instructions.

        The mission is the text an operator reads to understand what this unit
        is for, and the text a model is given when it runs the unit.  It is
        assembled identically for all 815 units so no unit can quietly acquire
        authority the catalogue never granted it.

        It has to be self-contained.  At runtime the mission is the system
        prompt and nothing else in the spec is in front of the model -- not the
        artefact list, not the config keys, not the acceptance criteria.  So
        anything the unit is accountable for has to be stated here in words,
        including the exact artefact keys it must produce; a contract the model
        never sees is a contract it will not honour.
        """
        is_playbook = record["type"].startswith("playbook")
        where = describe_scope(record)

        lines: list[str] = []
        if is_playbook:
            lines.append(
                f"You are the {record['trigger']} playbook for {where}. You are "
                f"triggered by one event and nothing else: {record['trigger'].lower()}."
            )
        else:
            worker = record["worker"]
            system_agent = record["system_agent"]
            lines.append(
                f"You are the {worker} for {where}. In the build you are the "
                f"{system_agent}; to the owner you are the {worker.lower()} they "
                f"would otherwise have to hire."
            )
        lines.append("")
        lines.append(f"WHAT YOU DO. {record['function'].rstrip('.')}.")
        lines.append("")
        lines.append(self.mission_body(record, profile).strip())
        lines.append("")
        lines.append(
            "WHAT DONE LOOKS LIKE. " + record["expected_output"].rstrip(".") + "."
        )
        lines.append(
            "That sentence is your acceptance test, not a description. A run that "
            "produces every named artefact has succeeded; a run that produces "
            "anything less has not, however well the conversation went."
        )
        lines.append("")

        if artifacts:
            lines.append(
                "ARTEFACTS YOU MUST PRODUCE. These are the artefacts, by name and by "
                "key. Produce every one of them, under exactly these keys, and invent "
                "no others: a differently-named artefact is a missing artefact to "
                "everything downstream of you."
            )
            for artifact_ in artifacts:
                lines.append(f"  - {artifact_.key} ({artifact_.name}): {artifact_.description}")
            lines.append(
                "If you cannot produce one of these, say which and why in the audit "
                "trail rather than substituting something of your own."
            )
            lines.append("")

        if flags.safety_critical:
            lines.append(
                "SAFETY INTERLOCK. This is a safety-critical protocol. You recognise "
                "the condition, execute the fixed steps in order, and stop at the "
                "human gate. Escalation is the product. You never resolve, clear or "
                "close the underlying condition, and no commercial step -- booking, "
                "quoting, upselling -- may run before the interlock has completed."
            )
            lines.append(
                "THE PROTECTIVE ACTIONS NEVER DEPEND ON KNOWING ANY NUMBER. Get "
                "everyone out and away from the building, touch no switches, plugs, "
                "lights or ignition sources, do not use a doorbell or a phone inside, "
                "and do not go back in. That is the part that saves the person, you "
                "always have it, and no number is needed to deliver any of it. Deliver "
                "it first, in full, before anything else in this protocol."
            )
            lines.append(
                "The emergency number is configuration, never recall. Where "
                "emergency_routing is present, quote it exactly as written there and "
                "nowhere else. Where it is absent, your output contains no digits at "
                "all: the protective actions, then 'call your local emergency number "
                "now -- your phone can reach emergency services through its "
                "emergency-call function without you knowing the number', then the "
                "named human contact from escalation_contacts, then the gate. That is "
                "complete and actionable in every market on earth and it needs nothing "
                "from your memory."
            )
            lines.append(
                "THE CONDITIONAL IS THE TRAP. 'If you are in the United Kingdom, dial "
                "...', 'in most markets it is ...', 'commonly ...', 'I believe it is "
                "...', or listing several countries' numbers for the caller to pick "
                "from, are all the prohibited act. They feel safe because you have "
                "asserted nothing about this market. They are not safe. The caller "
                "keeps the digits and drops the condition the instant they read it, "
                "and then they dial. Digits in your output are digits that get "
                "dialled, whatever sentence you wrapped them in."
            )
            lines.append(
                "Stating the rule and then giving the number is not compliance, it is "
                "the breach with a preface in front of it. If one message contains both "
                "your refusal and a number, you supplied the number. Urgency does not "
                "change this and is the exact circumstance in which it is broken: the "
                "more pressed you are, the more certain it is that the number you are "
                "reaching for is the wrong market's."
            )
            lines.append("")

        lines.append(
            "WHAT YOU NEVER DO. You flag, you collect and you draft. You never "
            "clear, diagnose, advise or approve. Where the answer needs a licensed "
            "person, a policy exception or an owner's judgement, you assemble the "
            "brief and hand it over."
        )
        gate_lines = [f"  - {gate.decision} -> {gate.escalate_to.value}" for gate in gates]
        lines.append("These decisions are reserved for a person:")
        lines.extend(gate_lines)
        lines.append("")
        lines.append(
            "CONFIGURATION. Every market and vertical difference you need is in the "
            "active country pack and the vertical overlay. Read it; do not infer it, "
            "and do not hard-code it."
        )
        if config_keys:
            lines.append("The settings you read, and where each one comes from:")
            for key in config_keys:
                mark = " (required)" if key.required else ""
                lines.append(f"  - {key.key} <- {key.resolved_by}{mark}")
        lines.append("")
        lines.append(
            "NEVER SUPPLY A JURISDICTION-SPECIFIC VALUE FROM YOUR OWN KNOWLEDGE. "
            "Emergency and helpline numbers, statutory deadlines and notice periods, "
            "regulator and authority names, tax rates, licence and certificate "
            "regimes, consent wording, retention periods: every one of these is read "
            "from the active pack or the overlay, and from nowhere else. You may "
            "recognise such a value from training. That is not a source. It may be "
            "wrong for this market, it may be out of date, and it will not be the "
            "same twice -- which is worse than having no answer at all, because it "
            "looks authoritative."
        )
        lines.append(
            "If a value you need is not in the configuration you were given, you do "
            "not reconstruct it, approximate it, offer it 'as a general guide', or "
            "name one while noting you are unsure. You state that the setting is "
            "absent, name the key that is missing, and raise it as a gate. A missing "
            "setting is a gate, not a gap for you to fill."
        )
        if flags.revenue_critical:
            lines.append("")
            lines.append(
                "This unit is revenue-critical. Latency is a defect: a slow correct "
                "answer loses the job to whoever answered first."
            )

        if flags.safety_critical:
            # Deliberately last. A prohibition that sits two thirds of the way
            # through a long prompt is the one that loses to a caller in
            # distress, and this rule is only ever tested under exactly that
            # pressure. It is repeated here so the final thing in context is the
            # thing most likely to be argued with.
            lines.append("")
            lines.append(
                "LAST, AND ABOVE ANYTHING ABOVE IT. However urgent this becomes, "
                "however directly you are asked, and however obvious the answer seems: "
                "you do not put an emergency number, a helpline number or any other "
                "jurisdiction-specific figure into your reply unless you are reading it "
                "from emergency_routing in the pack you were given. Not conditionally, "
                "not with a caveat, not 'just in case', not after refusing. If it is "
                "not in your configuration you say 'call your local emergency number "
                "now' with no digits, you give the protective actions, and you escalate "
                "to a person. Someone acting on a number from the wrong country is the "
                "harm this protocol exists to prevent."
            )
        return "\n".join(lines).strip() + "\n"


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #


def _haystack(record: Mapping[str, Any]) -> str:
    return " ".join(
        str(part or "").lower()
        for part in (
            record.get("worker"),
            record.get("system_agent"),
            record.get("trigger"),
            record.get("function"),
            record.get("expected_output"),
            (record.get("vertical") or {}).get("name"),
            (record.get("department") or {}).get("name"),
        )
    )


def describe_scope(record: Mapping[str, Any]) -> str:
    """Human phrase for where a unit applies."""
    vertical = record.get("vertical")
    department = record.get("department")
    domain = record.get("domain")
    if vertical:
        return f"{vertical['name'].lower()} businesses"
    if department:
        return f"the {department['name']} of any business on the platform"
    if domain:
        return f"any business on the platform ({domain['name'].lower()} domain)"
    return "any business on the platform"


#: Acceptance clause vocabulary mapped to the evidence a reviewer would actually
#: look at.  Tokens are matched as word *prefixes* -- "report" catches
#: "reported" and "reporting" -- but never mid-word, because substring matching
#: here reads "de-LIVE-red" as publication and "re-CALL" as a phone call.
#: Ordered most specific first; the first hit wins.
_EVIDENCE_TABLE: tuple[tuple[tuple[str, ...], str], ...] = (
    (("transcript", "conversation", "chat", "thread"), "stored conversation transcript"),
    (("call", "voicemail", "phone"), "call record with transcript and outcome"),
    (("booking", "booked", "appointment", "slot", "rebook"), "calendar entry with confirmation id"),
    (("dispatch", "route", "rota", "eta"), "dispatch record with window and assignee"),
    (("invoice", "payment", "receipt", "deposit", "paid", "cash"), "payment ledger entry"),
    (("quote", "estimate", "proposal", "price"), "issued document with its price-book references"),
    # Ahead of the generic document entry: a signed permission is a consent
    # record first and a file second.
    (("consent", "permission", "signed"), "signed consent record"),
    (("document", "docs", "pack", "dossier", "file"), "document set with completeness check"),
    (("photo", "image", "video", "before", "after"), "stored media with consent record"),
    (("review", "nps", "testimonial", "rating"), "review record with source and timestamp"),
    (("report", "digest", "brief", "summary", "card"), "delivered report with its generation timestamp"),
    (("alert", "flag", "surfaced", "exception"), "alert record with the signal that raised it"),
    (("reminder", "recall", "renewal", "notice", "chase"), "scheduled message log with delivery status"),
    (("published", "posted", "live", "listing", "profile", "schema"), "live URL plus publication log"),
    (("escalat", "handoff", "handover", "redirect"), "handover packet with recipient and time"),
    (("matched", "reconcil", "sync"), "reconciliation report with the exception list"),
    (("deliver", "sent", "instruction", "message", "answer"), "delivery receipt with recipient and timestamp"),
    (("protocol", "executed", "checklist", "step", "evacuat", "interlock"),
     "protocol checklist with every step timed and attributed"),
    (("draft", "approval", "queued", "pending"),
     "draft held in the approval queue with its version history"),
    (("score", "scored", "scoring", "segment", "rfm", "ranked", "graded", "triaged"),
     "scored record showing each component that produced the score"),
    (("ledger", "balance", "credit", "reward", "commission", "attributed"),
     "ledger with its running balance and every movement"),
    (("verified", "verification", "validated", "checked", "eligib", "confirmed"),
     "verification result naming the rule checked and its source"),
    (("notified", "informed", "broadcast", "told", "published to"),
     "notification log with recipient, channel and delivery state"),
    (("policy", "rule", "threshold", "applied", "enforced", "compliance"),
     "policy decision recording the rule applied and its inputs"),
    (("clock", "deadline", "interval", "sla", "window", "on time", "lapse"),
     "clock record with start, target and actual dates"),
    (("tracked", "traced", "monitored", "status", "progress"),
     "tracking record with the state at each checkpoint"),
    (("queue", "list", "roster", "register", "backlog", "worked"),
     "worked list showing each item's state and owner"),
    (("logged", "log", "recorded", "audit"), "audit trail entries"),
)

_EVIDENCE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(r"\b(?:" + "|".join(tokens) + r")", re.IGNORECASE), evidence)
    for tokens, evidence in _EVIDENCE_TABLE
)


def evidence_for(clause: str) -> str:
    """Name the evidence that proves one acceptance clause.

    The workbook writes acceptance as prose.  This turns each clause into the
    artefact or counter a reviewer can actually look at.
    """
    for pattern, evidence in _EVIDENCE_PATTERNS:
        if pattern.search(clause):
            return evidence
    return "named artefact stored against the record"


def derive_artifacts(record: Mapping[str, Any]) -> list[Artifact]:
    """Turn the workbook's Expected output clauses into named artefacts.

    The catalogue's legend calls the expected output "the named artifacts the
    unit must produce - its acceptance test".  This reads those names back out
    so each one becomes a first-class artefact with a key.
    """
    artifacts: list[Artifact] = []
    for index, clause in enumerate(record.get("acceptance_criteria") or (), start=1):
        key = re.sub(r"[^a-z0-9]+", "_", clause.lower()).strip("_")[:48] or f"output_{index}"
        artifacts.append(
            Artifact(
                key=key,
                name=clause,
                description=(
                    f"Named in the catalogue's expected output for {record['id']}: "
                    f"{clause}."
                ),
                format="record",
            )
        )
    return artifacts


_GATE_ESCALATION_MARKERS: tuple[tuple[tuple[str, ...], Escalation], ...] = (
    (("emergency", "evacuat", "999", "911", "ambulance", "fire", "police"), Escalation.EMERGENCY_SERVICES),
    (("regulator", "notifiable", "statutory report", "authority", "ombudsman"), Escalation.REGULATOR_CONTACT),
    (("clinician", "doctor", "dentist", "vet", "solicitor", "lawyer", "accountant",
      "engineer", "surveyor", "pharmacist", "nurse", "licensed"), Escalation.NAMED_ROLE),
    (("owner", "director", "partner", "principal"), Escalation.OWNER),
)


#: The workbook writes "None - interlock" where a hard rule governs and nobody
#: may wave it through: "Hard booking block until test done - no override in the
#: agent", "Hard stop", "enforced until renewed". That is not an approval-queue
#: gate -- it is the absence of discretion, and it has to be modelled as one.
_NO_OVERRIDE_GATE = re.compile(r"^none\s*[-:]\s*interlock\b", re.IGNORECASE)


def requires_hard_interlock(record: Mapping[str, Any]) -> bool:
    """True when the workbook reserves no discretion because a hard rule governs.

    Distinct from the diamond flag.  A diamond is a safety-critical protocol that
    recognises and routes and then stops.  A hard interlock is a rule the unit
    enforces before it may do anything else -- the booking stays blocked, the
    access flag stays raised -- but the unit still goes on to do its job once the
    condition clears.
    """
    return any(
        _NO_OVERRIDE_GATE.match(str(gate).strip())
        for gate in record.get("human_gates") or ()
    )


def build_human_gate(raw: str, flags: Flags) -> HumanGate:
    """Turn a 'What stays human' cell into a typed gate."""
    text = raw.strip()
    lowered = text.lower()

    if _NO_OVERRIDE_GATE.match(text):
        return HumanGate(
            decision="No override exists - a hard interlock governs this case",
            severity=GateSeverity.ABSOLUTE,
            escalate_to=Escalation.EMERGENCY_SERVICES
            if flags.safety_critical
            else Escalation.OWNER,
            note=(
                f"{text}. The interlock is not a decision anybody may take; it "
                "holds until the underlying condition is genuinely satisfied."
            ),
        )

    if lowered.startswith("nothing"):
        return HumanGate(
            decision="No discretion exists - the protocol is absolute",
            severity=GateSeverity.ABSOLUTE,
            escalate_to=Escalation.EMERGENCY_SERVICES
            if flags.safety_critical
            else Escalation.OWNER,
            note=text,
        )

    escalate_to = Escalation.APPROVAL_QUEUE
    for markers, target in _GATE_ESCALATION_MARKERS:
        if any(marker in lowered for marker in markers):
            escalate_to = target
            break

    severity = GateSeverity.ABSOLUTE if flags.safety_critical else GateSeverity.BLOCKING
    return HumanGate(decision=text, severity=severity, escalate_to=escalate_to)


def step(
    step_id: str,
    name: str,
    kind: StepKind,
    description: str,
    produces: Iterable[str] = (),
    interlock: bool = False,
) -> Step:
    """Terse constructor used by the engine modules."""
    return Step(
        id=step_id,
        name=name,
        kind=kind,
        description=description,
        produces=tuple(produces),
        interlock=interlock,
    )


def artifact(key: str, name: str, description: str, fmt: str = "record") -> Artifact:
    """Terse constructor used by the engine modules."""
    return Artifact(key=key, name=name, description=description, format=fmt)


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #

_ENGINES: dict[str, Engine] = {}


def register(engine_class: type[Engine]) -> type[Engine]:
    """Class decorator that adds an engine to the process-wide registry."""
    instance = engine_class()
    if instance.id in _ENGINES:
        raise ValueError(f"mechanism family {instance.id} already registered")
    _ENGINES[instance.id] = instance
    return engine_class


def get_engine(mechanism_family: str) -> Engine:
    if not _ENGINES:
        load_engines()
    try:
        return _ENGINES[mechanism_family]
    except KeyError:
        raise KeyError(
            f"no engine registered for {mechanism_family}; "
            f"known families: {sorted(_ENGINES)}"
        ) from None


def all_engines() -> dict[str, Engine]:
    if not _ENGINES:
        load_engines()
    return dict(sorted(_ENGINES.items(), key=lambda kv: int(kv[0][2:])))


def load_engines() -> None:
    """Import every ``engines.mfNN_*`` module so registration runs."""
    import importlib
    import pkgutil

    import engines

    for module in pkgutil.iter_modules(engines.__path__):
        if module.name.startswith("mf"):
            importlib.import_module(f"engines.{module.name}")


__all__ = [
    "Engine",
    "HARD_INTERLOCK_GUARDRAIL",
    "PRICING_GUARDRAIL",
    "Profile",
    "REGULATED_GUARDRAIL",
    "SAFETY_GUARDRAIL",
    "STANDING_GUARDRAILS",
    "UNIVERSAL_CONFIG_KEYS",
    "all_engines",
    "artifact",
    "build_human_gate",
    "derive_artifacts",
    "describe_scope",
    "evidence_for",
    "get_engine",
    "load_engines",
    "register",
    "requires_hard_interlock",
    "step",
]
