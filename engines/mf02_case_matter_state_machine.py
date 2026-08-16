"""MF2 -- the case / matter state machine.

Some work is a conversation and finishes inside the hour.  This family is the
other kind: a thing that opens, acquires a reference, sits in a stage, runs
against a clock and is still open next week.  A matter, a claim, a dispute, a
non-conformance, a permit application, a returns authorisation, a complaint, a
consignment in transit -- the noun differs by vertical and the shape does not.
Each one is a case object with a stage model, an owner, a clock per stage, a
required-evidence list and a party waiting to be told where it has got to.

Two failure modes define the family and both are silence.  A case stops moving
and nobody notices until the customer chases, or a case moves and nobody tells
the customer.  So the engine's plan gathers, tests against terms that already
exist, transitions, and *then* notifies -- and every profile ends by sweeping
for what has gone still.

The third rule binds hard here.  These cases end in outcomes people care about:
a refund, a settlement, a concession, a determination.  The unit computes the
position the contract, the policy or the statute already produces,
cites where each clause came from and drafts the options; a person grants the
concession.  Config carries the rest: the stage names, the intervals, the
evidence a stage demands and the statutory clock all resolve from the vertical
overlay and the active country pack.
"""

from __future__ import annotations

from typing import Any, ClassVar, Mapping

from adw.models import (
    Artifact,
    Capability,
    ConfigKey,
    Guardrail,
    Step,
    StepKind,
)
from engines.base import Engine, Profile, artifact, register, step

# --------------------------------------------------------------------------- #
# family configuration
# --------------------------------------------------------------------------- #

#: Read by every unit of the family.  The stage model is the engine: change the
#: stages and the same code carries a snag list, a visa application or a
#: chargeback without knowing which it is holding.
_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="case_stage_model",
        description=(
            "Stages for this case type, their entry and exit conditions, the "
            "transitions allowed between them and which stages are terminal."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="stage_clocks",
        description=(
            "Target and breach interval for each stage, and the working calendar "
            "those intervals run against."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="statutory_clocks",
        description=(
            "Deadlines set by law or by contract that override the internal "
            "intervals, from the active country pack."
        ),
        required=True,
    ),
    ConfigKey(
        key="evidence_requirements",
        description=(
            "What must be on file before the case may enter each stage, and "
            "before it may close."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="update_cadence",
        description=(
            "How often the waiting party is told where the case stands, per "
            "stage and per channel, including the no-news update."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="authority_limits",
        description=(
            "The value, concession and goodwill limits below which the unit may "
            "execute the outcome the terms produce, and above which it gates."
        ),
        resolved_by="owner",
        required=True,
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

#: The eleven case shapes actually present in the catalogue, most specific
#: first.  Match tokens are read against worker, system agent, trigger, function
#: and expected output, so they are chosen to be distinctive nouns of the shape
#: rather than the verbs ("tracked", "logged", "resolved") the whole family
#: shares.
_PROFILES: tuple[Profile, ...] = (
    Profile(
        name="defect_ncr",
        summary=(
            "A defect, snag, fault or non-conformance held open against a "
            "corrective action until closure evidence lands."
        ),
        match=(
            "ncr",
            "non-conformance",
            "snag",
            "defect",
            "recall",
            "deviation",
            "fault",
            "uptime",
            "findings",
            "remediation plan",
            "affected lots",
            "affected units",
        ),
        steps=(
            step(
                "closure_watch",
                "Hold the non-conformance open until closure evidence lands",
                StepKind.ACT,
                (
                    "Keep the item in the open register with its corrective action, "
                    "its owner and its due date, and re-chase on the configured "
                    "interval. A non-conformance closes on filed evidence, never on "
                    "elapsed time or on an assurance that it has been dealt with."
                ),
                produces=("closure_register",),
            ),
        ),
        artifacts=(
            artifact(
                "closure_register",
                "Open-item register",
                (
                    "Every open defect with its severity grade, the party it is "
                    "attributed to, the corrective action, the owner, the due date "
                    "and the evidence still outstanding."
                ),
                "register",
            ),
        ),
        tools=("nonconformance_register", "photo_capture"),
        config_keys=(
            ConfigKey(
                key="defect_severity_grades",
                description=(
                    "Severity grades for this case type and the response interval "
                    "and notification each grade demands."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="corrective_action_policy",
                description=(
                    "What counts as closure evidence, who may attribute cost "
                    "between parties, and how long an item may stay open."
                ),
                resolved_by="owner",
            ),
        ),
        kpis=(
            "defects closed with evidence on file",
            "average age of the open register",
        ),
    ),
    Profile(
        name="complaint_recovery",
        summary=(
            "A complaint acknowledged in minutes, classified, and answered with "
            "the remedy the recovery matrix allows."
        ),
        match=("complaint", "guest recovery", "service-recovery"),
        steps=(
            step(
                "recovery_followup",
                "Close the loop and feed the register",
                StepKind.NOTIFY,
                (
                    "Come back after the remedy has landed, on the configured "
                    "interval, and record whether the complainant accepted it. File "
                    "the classification against the complaint register so a recurring "
                    "cause becomes visible as a pattern rather than as a third "
                    "unconnected complaint."
                ),
                produces=("complaint_register",),
            ),
        ),
        artifacts=(
            artifact(
                "complaint_register",
                "Complaint register entry",
                (
                    "The complaint classified against the configured taxonomy, with "
                    "the remedy offered, the cost of it, whether it was accepted and "
                    "the recurring cause it was filed under."
                ),
                "register",
            ),
        ),
        tools=("complaint_register", "recovery_offer_calculator"),
        config_keys=(
            ConfigKey(
                key="service_recovery_matrix",
                description=(
                    "Remedy allowed at each severity and value band, and the band "
                    "above which the offer becomes a gate."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="acknowledgement_target",
                description=(
                    "Minutes within which a complaint must be acknowledged, per "
                    "channel and in and out of hours."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "time to first acknowledgement",
            "complaints resolved before they reach a public review surface",
        ),
        channels=("voice",),
    ),
    Profile(
        name="incident_log",
        summary=(
            "An incident recorded while fresh, disclosed to each party only as "
            "policy allows, and tested against the pattern register."
        ),
        match=(
            "incident",
            "pattern",
            "flag",
            "liability triage",
            "attendance",
            "both families",
        ),
        steps=(
            step(
                "pattern_check",
                "Test the incident against the register",
                StepKind.ASSESS,
                (
                    "Run the new entry against the register for this party, site, "
                    "site team or animal and mark a repeat. Where the policy names a "
                    "threshold and the register has crossed it, raise it to the named "
                    "role instead of writing another routine entry."
                ),
                produces=("pattern_register",),
            ),
        ),
        artifacts=(
            artifact(
                "pattern_register",
                "Pattern register entry",
                (
                    "The incident filed against the subject it concerns, with prior "
                    "entries, the count against the configured threshold and the "
                    "handling instruction now attached to the record."
                ),
                "register",
            ),
        ),
        tools=("incident_register", "photo_capture"),
        config_keys=(
            ConfigKey(
                key="incident_notification_policy",
                description=(
                    "Who is told what after each incident type, including which "
                    "details must be withheld from which party."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="pattern_thresholds",
                description=(
                    "Repeat counts and windows at which an incident stops being "
                    "routine and goes to a named role."
                ),
                resolved_by="owner",
            ),
        ),
        kpis=(
            "incidents recorded with evidence on the day",
            "repeat patterns surfaced before the threshold breach",
        ),
        channels=("voice",),
    ),
    Profile(
        name="dispute_resolution",
        summary=(
            "A contested charge or position, answered with the dated record of "
            "what was actually agreed and the gap quantified."
        ),
        match=(
            "dispute",
            "chargeback",
            "withholds",
            "discrepancy",
            "quote history",
        ),
        steps=(
            step(
                "hold_and_chase",
                "Hold the amount and chase the missing evidence",
                StepKind.ACT,
                (
                    "Place the contested amount on hold in the ledger for as long as "
                    "the configured rules allow, chase whichever side still owes "
                    "evidence on the configured interval, and keep the response "
                    "deadline visible to the owner as it runs down."
                ),
                produces=("dispute_hold_record",),
            ),
        ),
        artifacts=(
            artifact(
                "dispute_hold_record",
                "Dispute hold and deadline record",
                (
                    "The contested amount, the hold placed against it, the response "
                    "deadline that applies and every piece of evidence requested, "
                    "received or still outstanding on each side."
                ),
            ),
        ),
        tools=("ledger_lookup", "quote_history"),
        config_keys=(
            ConfigKey(
                key="dispute_hold_rules",
                description=(
                    "How long a contested amount may be held, and the response "
                    "deadlines the scheme or the market imposes."
                ),
                required=True,
            ),
            ConfigKey(
                key="evidence_retention_window",
                description=(
                    "How far back quotes, approvals, signatures and delivery proof "
                    "remain retrievable for this market."
                ),
            ),
        ),
        kpis=(
            "disputes answered inside the response deadline",
            "disputes answered with the original agreement cited verbatim",
        ),
    ),
    Profile(
        name="deposit_cancellation",
        summary=(
            "A booking coming apart: contract tier applied, alternatives offered "
            "first, held capacity released, difference invoiced or credited."
        ),
        match=(
            "deposit",
            "no-show",
            "postponement",
            "cancelled",
            "attrition",
        ),
        steps=(
            step(
                "release_capacity",
                "Release the held capacity and record the recovery",
                StepKind.ACT,
                (
                    "Return the table, room block, seat, cohort place or trainer day "
                    "to the sales side the moment the terms allow, and record what "
                    "was recovered against what was forfeited so the commercial "
                    "outcome of the cancellation is a figure, not an impression."
                ),
                produces=("capacity_recovery_record",),
            ),
        ),
        artifacts=(
            artifact(
                "capacity_recovery_record",
                "Capacity and recovery record",
                (
                    "What was held, when it was released, what was resold against it "
                    "and the retained, forfeited or credited amount with the contract "
                    "tier each figure came from."
                ),
            ),
        ),
        tools=("booking_system", "ledger_lookup"),
        config_keys=(
            ConfigKey(
                key="cancellation_tiers",
                description=(
                    "Notice bands and the retention, transfer or credit each band "
                    "produces, per contract type."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="deposit_rules",
                description=(
                    "How deposits and holds are taken, applied, transferred and "
                    "released, and what may be charged against them."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "released capacity resold before the date",
            "cancellation outcomes matching the contracted tier",
        ),
    ),
    Profile(
        name="claim_adjudication",
        summary=(
            "A claim under a published rule: facts established, entitlement "
            "computed against a recorded rule version, outcome left to a person."
        ),
        match=(
            "claim",
            "compensation",
            "settlement",
            "valuation",
            "total-loss",
            "guarantee",
            "rights computed",
            "statutory position",
        ),
        steps=(
            step(
                "rule_version_recheck",
                "Re-test the claim when a governing figure changes",
                StepKind.ASSESS,
                (
                    "Re-run the computation whenever an input moves -- a revised "
                    "valuation, a late receipt, an amended rule version -- and keep "
                    "each run with the rule version and the inputs it used, so the "
                    "figure in front of the decision maker is reproducible."
                ),
                produces=("rule_version_record",),
            ),
        ),
        artifacts=(
            artifact(
                "rule_version_record",
                "Computation and rule-version record",
                (
                    "Each entitlement computation with the rule set and version "
                    "applied, the inputs it read, the figure produced and the clause "
                    "each element of the figure rests on."
                ),
            ),
        ),
        tools=("rule_engine", "ledger_lookup"),
        config_keys=(
            ConfigKey(
                key="claim_rule_set",
                description=(
                    "The compensation, statutory or policy rules that decide "
                    "entitlement in this market, with their version."
                ),
                required=True,
            ),
            ConfigKey(
                key="claim_evidence_schedule",
                description=(
                    "Evidence each claim type requires before it may be computed, "
                    "and how long the claimant has to supply it."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "claims computed with a recorded rule version",
            "claims decided inside the statutory window",
        ),
        channels=("postal_mail",),
    ),
    Profile(
        name="change_control",
        summary=(
            "A change against something already agreed: captured before work "
            "moves, priced against the original, accepted, re-baselined."
        ),
        match=(
            "variation",
            "amendment",
            "change log",
            "change tracker",
            "scope change",
            "rfi",
            "out-of-scope",
            "authorization matrix",
            "authorization captured",
            "rework",
            "make-good",
            "raw files",
            "cascade",
            "rippled",
        ),
        steps=(
            step(
                "rebaseline_scope",
                "Re-baseline the agreed scope",
                StepKind.ACT,
                (
                    "Attach the accepted change to the original document, restate the "
                    "running total and the revised dates, and mark the version it "
                    "supersedes so nobody works to the old one. An unbaselined change "
                    "is the argument this case exists to prevent."
                ),
                produces=("scope_baseline",),
            ),
        ),
        artifacts=(
            artifact(
                "scope_baseline",
                "Re-baselined scope",
                (
                    "The original document plus every accepted change, with the "
                    "running total, the revised dates, who asked for each change and "
                    "who accepted it."
                ),
            ),
        ),
        tools=("contract_store", "price_book_lookup"),
        config_keys=(
            ConfigKey(
                key="change_authority_matrix",
                description=(
                    "Who may request and who may accept a change at each value "
                    "band, and what must be in writing before work moves."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="variation_pricing_basis",
                description=(
                    "Rates, mark-ups and measurement basis used to price a change "
                    "against the original document."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "changes captured in writing before the work moved",
            "changes priced against the original document",
        ),
    ),
    Profile(
        name="refund_return",
        summary=(
            "Money or goods going back: entitlement verified against ledger and "
            "published terms, in-terms outcome executed, the rest gated."
        ),
        match=(
            "refund",
            "rma",
            "returns",
            "without receipt",
            "gift card",
            "restricted-fund",
        ),
        steps=(
            step(
                "execute_in_terms_outcome",
                "Execute the in-terms outcome and file the receipt",
                StepKind.ACT,
                (
                    "Put the money or the goods back through the rail the customer "
                    "originally used where the published terms cover it, confirm the "
                    "movement actually settled rather than that it was requested, and "
                    "file the receipt against the case. Anything the terms do not "
                    "cover leaves as a decision pack, not as a favour."
                ),
                produces=("settlement_receipt",),
            ),
        ),
        artifacts=(
            artifact(
                "settlement_receipt",
                "Settlement receipt",
                (
                    "Proof the refund, credit, replacement or reissue completed: "
                    "amount or item, rail used, reference, timestamp and the clause "
                    "of the published terms that allowed it."
                ),
            ),
        ),
        tools=("ledger_lookup", "payment_rail_client"),
        config_keys=(
            ConfigKey(
                key="refund_matrix",
                description=(
                    "What is refundable, creditable or replaceable, in what window "
                    "and on what rail, with the goodwill threshold that gates."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="return_window",
                description=(
                    "Return, exchange and reissue windows for this vertical, and "
                    "the condition the goods must be in."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "in-terms outcomes executed without a gate",
            "settlements confirmed as settled, not merely requested",
        ),
    ),
    Profile(
        name="application_casework",
        summary=(
            "An application, filing or obligation carried through its required "
            "steps and statutory clocks to a determination by someone else."
        ),
        match=(
            "application",
            "permit",
            "licen",
            "apostille",
            "legalization",
            "legalisation",
            "milestone",
            "statutory clock",
            "docket",
            "appeal",
            "election",
            "entitlement",
            "undertaking",
            "consent",
            "certificate",
            "exemption",
            "redaction",
            "materiality",
            "disclosure",
        ),
        steps=(
            step(
                "chase_next_requirement",
                "Chase the next outstanding requirement",
                StepKind.ACT,
                (
                    "Go after the next missing item from whoever holds it -- the "
                    "applicant, a third party or the authority -- on the interval the "
                    "statutory clock leaves room for, and log each chase. The case "
                    "waits on one named item at a time, and that item is always named."
                ),
                produces=("requirement_chase_log",),
            ),
        ),
        artifacts=(
            artifact(
                "requirement_chase_log",
                "Requirement and chase log",
                (
                    "The requirement checklist for this case type with each item's "
                    "holder, status and date, plus every chase sent and the reply it "
                    "did or did not produce."
                ),
                "log",
            ),
        ),
        tools=("checklist_runner", "statutory_calendar"),
        config_keys=(
            ConfigKey(
                key="requirement_checklist",
                description=(
                    "Documents, forms, fees and third-party steps this case type "
                    "requires, in the order the authority wants them."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="statutory_clock_calendar",
                description=(
                    "Statutory response windows, filing deadlines and working-day "
                    "rules for this market, from the active country pack."
                ),
                required=True,
            ),
        ),
        kpis=(
            "requirements filed before the statutory deadline",
            "applicants told their stage without being told an outcome",
        ),
        channels=("postal_mail",),
    ),
    Profile(
        name="status_visibility",
        summary=(
            "State somebody is waiting on, pushed on a cadence before the chase "
            "arrives -- and exceptions pushed the moment they appear."
        ),
        match=(
            "wismo",
            "where-is",
            "track-and-trace",
            "multi-carrier",
            "shipment status",
            "custody",
            "baggage",
            "lost property",
            "portal",
            "proactive",
            "status-only",
            "chasing results",
        ),
        steps=(
            step(
                "exception_sweep",
                "Sweep the tracked items and push exceptions immediately",
                StepKind.OBSERVE,
                (
                    "Poll every source system on the configured interval and push the "
                    "position before it is asked for. A stalled scan, a missed "
                    "milestone or a broken custody link goes out the moment it is "
                    "seen, not at the next scheduled update."
                ),
                produces=("exception_alert",),
            ),
        ),
        artifacts=(
            artifact(
                "exception_alert",
                "Tracking exception alert",
                (
                    "Each item whose movement stopped or whose milestone slipped, "
                    "with the source system that reported it, the last confirmed "
                    "position and who was told."
                ),
                "alert",
            ),
        ),
        tools=("carrier_tracking", "status_poller"),
        config_keys=(
            ConfigKey(
                key="status_source_systems",
                description=(
                    "Systems that hold the authoritative position for this case "
                    "type, and their polling intervals."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="disclosure_policy",
                description=(
                    "What a status update may say and what it must withhold until a "
                    "licensed or authorised person speaks."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "updates pushed before the customer asked",
            "inbound where-is-it contacts per open case",
        ),
        channels=("push_notification",),
    ),
    # Fallback.  Deliberately the canonical shape rather than a dumping ground:
    # a long-running matter carried stage by stage, with whatever is not moving
    # surfaced first.
    Profile(
        name="matter_progress",
        summary=(
            "A matter carried across weeks on stage clocks, with stalls ranked "
            "and surfaced before anyone chases."
        ),
        match=(),
        steps=(
            step(
                "stall_sweep",
                "Sweep the caseload for what is not moving",
                StepKind.ASSESS,
                (
                    "Run every open matter against its stage interval, rank what has "
                    "gone still by how long it has been still and what it waits on, "
                    "and send the stalled list on its own cadence whether or not any "
                    "matter moved this cycle."
                ),
                produces=("stalled_matter_list",),
            ),
        ),
        artifacts=(
            artifact(
                "stalled_matter_list",
                "Stalled matter list",
                (
                    "Open matters past their stage interval, ranked by days still, "
                    "each with the stage it is stuck in, the party it waits on and "
                    "the date it was last touched."
                ),
                "report",
            ),
        ),
        tools=("stall_report_builder",),
        config_keys=(
            ConfigKey(
                key="stall_thresholds",
                description=(
                    "Days in a stage at which a matter counts as stalled, per stage "
                    "and per case type."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="matter_review_cycle",
                description=(
                    "How often the caseload is swept and who receives the stalled "
                    "list."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "stalled matters surfaced before the client chased",
            "matters with a stage transition inside the review cycle",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class CaseMatterStateMachineEngine(Engine):
    """Carries every unit whose work is a case object rather than an exchange.

    The engine holds one skeleton -- pick up the event, assemble the evidence,
    test it against the terms, transition, draft, act, tell the waiting party --
    and eleven profiles that say what kind of case it is.  Nothing in the code
    knows whether the case is a snag, a chargeback or a visa file; the stage
    model, the clocks and the required evidence all arrive as configuration.
    """

    id: ClassVar[str] = "MF2"
    family: ClassVar[str] = "Case / matter state machine"
    what_it_does: ClassVar[str] = (
        "Long-running case objects with stages, clocks and updates - matters, "
        "claims, tickets, NCRs, permits, applications"
    )
    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.CASE_STATE,
        Capability.CLOCK,
        Capability.COLLECT_DOCUMENTS,
        Capability.SEQUENCE,
        Capability.WATCH_SIGNAL,
        Capability.QUEUE_TRIAGE,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "case_store",
        "stage_clock",
        "document_store",
        "policy_library",
        "message_sender",
        "task_queue",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "email",
        "messaging",
        "customer_portal",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "stage cycle time against the configured interval",
        "cases stalled beyond their stage clock",
        "update cadence met without a customer chase",
        "cases closed with the required evidence on file",
        "reopen rate after closure",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    state_object: ClassVar[str] = "case_file"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        return _PROFILES

    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Observe, gather, assess, decide, draft, act, notify.

        The order is the discipline.  Evidence is assembled before the position
        is computed, the position is computed before anything is drafted, and
        the waiting party is told last -- after the case has actually moved, so
        no update ever describes a transition that did not happen.
        """
        return (
            step(
                "open_case",
                "Find or open the case",
                StepKind.OBSERVE,
                (
                    "Take the inbound event and resolve it to exactly one case: match "
                    "it to an open reference, or open a new one and issue the "
                    "reference. Load the current stage, the clock already running and "
                    "everything the case has accumulated so far."
                ),
                produces=("case_file",),
            ),
            step(
                "assemble_evidence",
                "Assemble what this stage requires",
                StepKind.GATHER,
                (
                    "Pull the evidence the stage demands and nothing less: the "
                    "agreement or quote in force, prior correspondence, documents, "
                    "photographs, ledger lines, third-party records. Note what is "
                    "missing and who holds it rather than working around the gap."
                ),
                produces=("evidence_bundle",),
            ),
            step(
                "test_against_terms",
                "Test the case against the terms and the clocks",
                StepKind.ASSESS,
                (
                    "Compare what you have against the stage model, the published "
                    "terms and the clocks: what the agreement, policy or statute "
                    "already says about this situation, which stage conditions are "
                    "satisfied, what is outstanding and what is overdue. Cite the "
                    "source of every position; a position without a citation is an "
                    "opinion and does not go in the file."
                ),
                produces=("outstanding_items", "stage_clock_record"),
            ),
            step(
                "choose_transition",
                "Choose the next stage or the gate",
                StepKind.DECIDE,
                (
                    "Pick the transition the stage model allows for what you found. "
                    "If the outcome sits inside the configured authority limits, it is "
                    "a transition; if it needs a concession, an exception or a "
                    "judgement about who is right, it is a gate, and the gate is the "
                    "answer rather than a delay to the answer."
                ),
            ),
            step(
                "draft_output",
                "Draft the update and the decision pack",
                StepKind.DRAFT,
                (
                    "Write the update for the waiting party in their language: where "
                    "the case is, what happens next, by when and what is needed from "
                    "them. Where a person must decide, write the decision pack too -- "
                    "the position under the terms with its citations, the options "
                    "available, what each costs and the evidence behind each."
                ),
                produces=("case_update", "decision_pack"),
            ),
            step(
                "move_the_case",
                "Move the case and re-arm the clock",
                StepKind.ACT,
                (
                    "Write the transition to the case file with actor, timestamp and "
                    "reason, attach the evidence to the stage that needed it, set the "
                    "next due date and name the owner. Nothing leaves this step in a "
                    "stage the model does not define."
                ),
                produces=("case_file", "stage_clock_record"),
            ),
            step(
                "tell_the_waiting_party",
                "Tell everyone waiting on it",
                StepKind.NOTIFY,
                (
                    "Send the update on the configured cadence and channel, including "
                    "when there is no news, and route the decision pack to the named "
                    "contact when the case has stopped at a gate. A case that moved in "
                    "silence has not been worked."
                ),
                produces=("case_update",),
            ),
        )

    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "case_file",
                "Case file",
                (
                    "The case object itself: reference, parties, case type, current "
                    "stage, owner and every transition with its actor, timestamp and "
                    "reason."
                ),
            ),
            artifact(
                "evidence_bundle",
                "Evidence bundle",
                (
                    "Everything the case rests on, filed against the stage that "
                    "required it: agreements, quotes, correspondence, documents, "
                    "photographs, ledger lines and third-party records, each with its "
                    "source and date."
                ),
                "bundle",
            ),
            artifact(
                "stage_clock_record",
                "Stage clock record",
                (
                    "Opened, target and actual date for every stage, which intervals "
                    "were met and which breached, and the actor, reason and authority "
                    "behind any extension."
                ),
            ),
            artifact(
                "outstanding_items",
                "Outstanding items list",
                (
                    "What the case is still waiting on, from which party and since "
                    "when -- the list the stall sweep reads and the customer update "
                    "quotes from."
                ),
            ),
            artifact(
                "case_update",
                "Case update",
                (
                    "The message sent to the waiting party in the configured language "
                    "and channel: current stage, what happens next, by when, and what "
                    "is needed from them."
                ),
                "message",
            ),
            artifact(
                "decision_pack",
                "Decision pack",
                (
                    "The brief handed over when the case leaves the unit's authority: "
                    "the position the terms produce with citations, the options, the "
                    "cost and consequence of each, and the evidence behind them."
                ),
                "document",
            ),
        )

    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        vertical = record.get("vertical") or {}
        if vertical:
            where = (
                f"The stage names, intervals and required evidence for "
                f"{vertical['name'].lower()} come from the vertical overlay, not from "
                f"how the last case happened to run."
            )
        else:
            where = (
                "This case type runs across every vertical on the platform, so the "
                "stage names, intervals and required evidence are whatever the "
                "overlay in front of you supplies."
            )
        return (
            "HOW YOU WORK. You hold a case, not a conversation. Every event you "
            "touch belongs to one case object with a reference, a stage, an owner "
            "and a clock, so your first act is to find that case or open it, and "
            "nothing you say to anyone happens off the record. You move it one "
            "stage at a time along the stage model in configuration: gather what "
            "the stage requires, test it against terms that already exist -- the "
            "agreement, the quote, the policy, the statutory deadline -- and write "
            "down what you found before you write down what happens next. Inside "
            "the configured authority you make the transition and re-arm the clock; "
            "outside it you assemble the decision pack and stop, because computing "
            "the position the terms produce is your work and granting the "
            "concession is a person's. A case that stops moving is the failure this "
            "family exists to catch, so you surface a stalled stage before anyone "
            "chases you for it, and you treat silence towards the waiting party as "
            f"a defect even when the case is progressing. {self._profile_line(profile)} "
            f"{where}"
        )

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        return (
            Guardrail(
                id="GR-ONE-CASE-OBJECT",
                rule=(
                    "Every event lands on exactly one case object. Nothing is "
                    "handled off the record and no reply exists without a case."
                ),
                check=(
                    "Before any message is sent the case reference exists, is stored "
                    "against the thread and appears on the outbound message."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-STAGE-MODEL-ONLY",
                rule=(
                    "The case moves only along transitions the configured stage "
                    "model defines, and only into stages that model names."
                ),
                check=(
                    "Every transition is validated against case_stage_model before "
                    "it is written; an undefined transition raises a gate instead."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CLOCK-INTEGRITY",
                rule=(
                    "A clock starts when its stage opens and is never reset by "
                    "sending a message about the case."
                ),
                check=(
                    "stage_clock_record retains the original target date for every "
                    "stage; each extension carries an actor, a reason and the "
                    "authority that granted it."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-STALL-SURFACED",
                rule=(
                    "A case past its stage interval is surfaced before the waiting "
                    "party asks about it."
                ),
                check=(
                    "Every case beyond its stage_clocks interval appears in the "
                    "stall output with days overdue and the party it waits on, dated "
                    "before the next inbound chase."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-POSITION-NOT-VERDICT",
                rule=(
                    "The unit states the position existing terms already produce. "
                    "It never states the outcome: the concession, the settlement "
                    "and the closure decision belong to a person."
                ),
                check=(
                    "Every clause, rule or computed position in the draft carries a "
                    "citation to its source document and version, and the artefact "
                    "presents options rather than a determination."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-NO-SILENT-CLOSURE",
                rule=(
                    "A case closes only with its required evidence on file and the "
                    "waiting party told it has closed."
                ),
                check=(
                    "A transition into a terminal stage is refused unless "
                    "evidence_requirements are satisfied and a closing case_update "
                    "is logged as delivered."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-STATUS-NOT-CONTENT",
                rule=(
                    "Status is disclosed; the substance behind the status is not. "
                    "Results, third-party identities and anything a licensed person "
                    "must deliver stay out of the update."
                ),
                check=(
                    "Outbound updates name the stage, the owner and the next date "
                    "only; anything the disclosure policy reserves is withheld and "
                    "routed to the named role instead."
                ),
                source="mechanism_family",
            ),
        )

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "Existing case file for this reference, if one is already open",
            "Stage model, stage clocks and required evidence for this case type",
            "The agreement, quote, policy or statute the case is measured against",
            "Evidence already on file: documents, photographs, messages, ledger lines",
            "Open caseload and its stage clocks, for the stall sweep",
        )

    # -- internals ----------------------------------------------------------
    def _profile_line(self, profile: Profile) -> str:
        """One sentence naming what kind of case this profile is holding.

        Kept beside the profiles rather than inside them because it is prose
        about the mission, not configuration a customer can override.
        """
        return _PROFILE_MISSION_LINES.get(profile.name, _PROFILE_MISSION_LINES["matter_progress"])


#: Mission prose per profile.  Each one names the case type, its evidence and
#: the exact point at which the unit stops and a person takes over.
_PROFILE_MISSION_LINES: dict[str, str] = {
    "defect_ncr": (
        "This case is a non-conformance: capture the defect with its evidence at "
        "the moment it is found, grade it, attribute it to a party without "
        "arguing the attribution, hold it open against a corrective action and an "
        "owner, and let it close only when the closure evidence is filed."
    ),
    "complaint_recovery": (
        "This case is a complaint: acknowledge it within the configured minutes "
        "before you know the answer, classify it, draft the remedy the recovery "
        "matrix allows at your authority, and file the cause so the third "
        "occurrence is visible as a pattern rather than as a third complaint."
    ),
    "incident_log": (
        "This case is an incident: record what happened, who was involved and "
        "what evidence exists while it is fresh, tell each party only what the "
        "policy allows that party to hear, and run the entry against the register "
        "so a repeat is flagged rather than merely filed."
    ),
    "dispute_resolution": (
        "This case is a contested position: retrieve what was actually agreed -- "
        "verbatim, dated and sourced -- set it beside what is being asserted, "
        "quantify the gap, and put both sides of it in front of whoever owns the "
        "concession."
    ),
    "deposit_cancellation": (
        "This case is a booking coming apart: apply the contract tier or deposit "
        "rule exactly as written, offer the alternatives the terms oblige you to "
        "offer before anything is forfeited, release the held capacity back to "
        "the sales side, and invoice or credit the difference."
    ),
    "claim_adjudication": (
        "This case is a claim under a published rule: establish the facts the "
        "rule needs, compute the entitlement it produces with the rule version "
        "recorded, and present a reproducible computation for a person to act on "
        "rather than a settlement you have made."
    ),
    "change_control": (
        "This case is a change against something already agreed: capture it and "
        "who asked for it before any work moves, price the delta against the "
        "original document, get the acceptance in writing, and re-baseline the "
        "scope so the superseded version cannot be mistaken for the live one."
    ),
    "refund_return": (
        "This case is money or goods going back: verify the entitlement against "
        "the ledger and the published terms, put the in-terms outcome through the "
        "rail the customer originally used, and route anything outside the terms "
        "as a decision pack rather than as a favour."
    ),
    "application_casework": (
        "This case is an application or an obligation with a determination at the "
        "end of it: hold the requirement list, chase whichever party holds the "
        "next outstanding item, run the statutory clock and the internal clock as "
        "two distinct clocks, and tell the applicant where they stand at every "
        "stage without ever predicting the outcome."
    ),
    "status_visibility": (
        "This case is state somebody is waiting on: pull the current position "
        "from the systems that hold it, push it on the configured cadence before "
        "the chase arrives, and push exceptions the moment they appear -- and "
        "disclose where the case is, never what the result behind it says, "
        "because that content belongs to whoever is licensed to give it."
    ),
    "matter_progress": (
        "This case is a matter carried across weeks: keep every open matter on "
        "its stage clock, rank what is not moving by how long it has been still "
        "and what it waits on, and send the stalled list and the client update on "
        "their own cadences whether or not anything moved."
    ),
}


__all__ = ["CaseMatterStateMachineEngine"]
