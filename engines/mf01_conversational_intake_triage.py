"""MF1 -- Conversational intake & triage.

The largest and least uniform of the fourteen families: ninety-eight units whose
titles run from Receptionist to Pharmacovigilance Intake.  What they share is a
single mechanism.  Something arrives -- a chat, a call, a DM, a form, a comment,
a 999-adjacent out-of-hours page -- and the unit has to understand it, gather the
structured detail the next step needs, and route it.  Nothing more.  MF1 units
are the front of every roster, so they are also the units most tempted to
overreach: to reassure, to reason about a symptom, to say yes to a price.  The
engine's job is to make that temptation structurally impossible.

The family skeleton is therefore short and identical everywhere: receive,
capture, triage, route.  Everything after routing is the profile's business, and
the profiles are where ninety-eight differently-named workers resolve into
thirteen real shapes -- a first-notice clerk on a regulatory clock is not a
grounded answer desk, and neither is a screening engine that must give a reason
per rule.  Vertical difference is carried by the intake schema, the rule set and
the Q&A pack, all of which are configuration.

Two failure modes drive most of the guardrails here.  The first is the
confidently unsourced answer: a unit that knows the shape of the answer and
invents the substance.  The second is the quiet downgrade: an urgent request
graded on the caller's tone rather than the configured bands, because the caller
was polite.  Both are checked explicitly below.
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
# profile mission notes
# --------------------------------------------------------------------------- #

#: One sentence per profile, woven into the mission body.  Kept out of
#: :class:`Profile` because the dataclass is frozen and shared by all fourteen
#: engines; the discipline a profile demands is MF1's business, not the base's.
_PROFILE_NOTES: Mapping[str, str] = {
    "incident_first_notice": (
        "This is a first notice on a regulatory clock: capture the reportable "
        "minimum first, start the clock at first contact, and let the "
        "investigator judge what the event actually was"
    ),
    "urgent_severity_triage": (
        "Urgency here is a graded band, not an impression -- you may raise the "
        "band the rules assigned but you may never lower it, and the wait you "
        "publish is the honest one"
    ),
    "lead_qualification": (
        "You are scoring demand, not selling to it: the score, the reason behind "
        "each component and a dated next action all land on the pipeline record "
        "before the thread closes"
    ),
    "criteria_screen": (
        "You screen against published criteria and report the result rule by "
        "rule; an unknown is never rounded up to a pass, and approval, denial "
        "and every exception stay with the named human"
    ),
    "structured_case_intake": (
        "You are assembling a file for a licensed person who will take the "
        "matter: facts, documents and gaps in, opinion out"
    ),
    "quote_and_estimate": (
        "Every figure you put in writing resolves to a line in the published "
        "price book or to a quote the business already issued, and an estimate "
        "is presented as an estimate with its assumptions and validity"
    ),
    "booking_intake": (
        "The conversation is not finished until a real slot is held against live "
        "availability and confirmed back in the same thread"
    ),
    "service_request_desk": (
        "You work the documented steps for the request type in order and record "
        "what each returned; where the fix needs a credit, an exception or an "
        "engineer, you hand over with what you already tried"
    ),
    "match_and_recommend": (
        "You match against live stock, courses or evidence on the dimensions the "
        "catalogue is indexed on, and you say plainly when nothing fits rather "
        "than padding the shortlist"
    ),
    "grounded_answer_desk": (
        "You answer only from the named sources and you show which one; silence "
        "in the source is itself an answer, and interpretation belongs to a "
        "person"
    ),
    "thread_continuity": (
        "One contact, one thread: you resolve identity before you open anything, "
        "carry the context across the channel, language or second party, and "
        "never make someone repeat what you already hold -- which rail and which "
        "language you switch into is market configuration, never your preference"
    ),
    "human_handover": (
        "You hand over on the first trigger rather than trying one more turn, and "
        "the packet is assembled before the person is interrupted"
    ),
    "front_desk_concierge": (
        "You answer what the sources cover, capture the contact whatever the "
        "outcome, and route the rest -- no thread ends in silence and none is "
        "closed as no-action without a logged reason"
    ),
}


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class ConversationalIntakeTriageEngine(Engine):
    """Carries every MF1 unit: understand a request, gather detail, route it."""

    id: ClassVar[str] = "MF1"
    family: ClassVar[str] = "Conversational intake & triage"
    what_it_does: ClassVar[str] = "Understands a request, gathers structured detail, routes it"

    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.CONVERSE,
        Capability.QUEUE_TRIAGE,
        Capability.SCORE,
        Capability.CASE_STATE,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "conversation_channel",
        "intent_classifier",
        "contact_record",
        "qa_pack_lookup",
        "routing_queue",
        "escalation_queue",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "web_chat",
        "messaging",
        "email",
        "voice",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "first_response_seconds",
        "intake_completeness",
        "routing_accuracy",
        "escalation_rate",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = (
        ConfigKey(
            key="intake_fields",
            description=(
                "Fields the intake record must carry before a request of this type "
                "can be routed, by request type."
            ),
            resolved_by="vertical",
            required=True,
        ),
        ConfigKey(
            key="routing_map",
            description="Intent and urgency band to destination queue, role or rota.",
            resolved_by="owner",
            required=True,
        ),
        ConfigKey(
            key="urgency_bands",
            description=(
                "The urgency ladder and the response target each band carries, "
                "with the rules that assign it."
            ),
            resolved_by="vertical",
            required=True,
        ),
        ConfigKey(
            key="response_sla",
            description="First-response targets by channel, in hours and out of them.",
            resolved_by="owner",
            required=True,
        ),
        ConfigKey(
            key="qa_pack",
            description=(
                "The question-and-answer pack this unit may answer from: hours, "
                "scope, guarantees, cancellation and policy wording."
            ),
            resolved_by="owner",
            required=True,
        ),
    )
    state_object: ClassVar[str] = "conversation_thread"

    # -- profiles ----------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        """Thirteen shapes, ordered specific before general.

        Order carries real weight: "quotes out" appears in the high-value triage
        units, "pre-qualified" in a lead router, "eligibility checker" in a
        lead-magnet widget.  Where two shapes share a word, the profile whose
        mechanism actually runs the unit is listed first.
        """
        return (
            # Regulatory first notice outranks everything: the clock starts at
            # first contact and a mis-triage here is a reportable failure.
            Profile(
                name="incident_first_notice",
                summary=(
                    "Regulatory first notice -- incidents, near-misses, adverse "
                    "events, FNOL -- captured against a reporting clock."
                ),
                match=(
                    "incident",
                    "near-miss",
                    "near miss",
                    "adverse event",
                    "pharmacovigilance",
                    "first notice",
                    "first-notice",
                    "fnol",
                ),
                steps=(
                    step(
                        "reportable_minimum",
                        "Capture the reportable minimum",
                        StepKind.GATHER,
                        "Take who, what, when, where, harm and the product, policy, "
                        "batch or asset identifiers the report will need, before any "
                        "other question. Stamp the clock at first contact, not at the "
                        "moment the record was finished.",
                        produces=("incident_report",),
                    ),
                    step(
                        "reporting_criteria",
                        "Flag the reporting criteria that appear to be met",
                        StepKind.ASSESS,
                        "Compare what was captured against the reportable-event "
                        "criteria in the country pack and flag each one that appears "
                        "met, with the deadline it carries. You flag; whether the "
                        "event is reportable in substance is the investigator's call.",
                        produces=("reporting_clock",),
                    ),
                    step(
                        "safety_queue",
                        "Put the notice in the named queue with time remaining",
                        StepKind.NOTIFY,
                        "Deliver the notice to the safety, quality or claims queue "
                        "named for this event type with the deadline attached, and "
                        "confirm a person has it rather than assuming the queue was read.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "incident_report",
                        "First-notice record",
                        "The reportable minimum as captured, in the reporter's own "
                        "words alongside the structured fields.",
                    ),
                    artifact(
                        "reporting_clock",
                        "Reporting clock",
                        "Clock start, the criteria flagged and the deadline each one "
                        "carries under the active country pack.",
                    ),
                ),
                tools=("case_file_write", "regulatory_clock"),
                config_keys=(
                    ConfigKey(
                        key="reportable_event_criteria",
                        description="What counts as reportable in this market, by event type.",
                        required=True,
                    ),
                    ConfigKey(
                        key="reporting_deadlines",
                        description="Statutory clock for each reportable event type.",
                        required=True,
                    ),
                    ConfigKey(
                        key="incident_queue_map",
                        description="Which queue and named officer receives each event type.",
                        resolved_by="owner",
                        required=True,
                    ),
                ),
                kpis=(
                    "minutes_to_first_notice",
                    "reportable_field_completeness",
                    "deadline_breach_count",
                ),
            ),
            # Out-of-hours and surge demand: the band decides the promise, so the
            # band has to be assigned by rule before anything is offered.
            Profile(
                name="urgent_severity_triage",
                summary=(
                    "Urgent, out-of-hours and surge demand graded into severity "
                    "bands and offered a real dispatch window."
                ),
                match=(
                    "emergency",
                    "severity",
                    "surge",
                    "night",
                    "out-of-hours",
                    "out of hours",
                    "dispatch",
                    "fault triage",
                    "311",
                ),
                steps=(
                    step(
                        "grade_severity",
                        "Grade against the severity bands",
                        StepKind.ASSESS,
                        "Apply the configured severity bands and vulnerability criteria "
                        "-- dependency, lone occupancy, loss of heat, water or power, "
                        "risk to a third party -- to what was reported. The band comes "
                        "from the rules, never from how calm or how angry the caller sounded.",
                        produces=("severity_grade",),
                    ),
                    step(
                        "offer_window",
                        "Offer the window the band entitles them to",
                        StepKind.ACT,
                        "Read live capacity and the on-call rota and offer the response "
                        "window this band actually earns. Publish the honest wait; a "
                        "flattering one is a defect that surfaces on the doorstep.",
                        produces=("dispatch_offer",),
                    ),
                    step(
                        "page_on_call",
                        "Page the on-call contact for the band",
                        StepKind.NOTIFY,
                        "Page the contact the rota names for this band and this hour, and "
                        "keep escalating down the fallback list until a human acknowledges.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "severity_grade",
                        "Severity grade",
                        "Assigned band, the rule and vulnerability flags that assigned "
                        "it, and the response target it carries.",
                    ),
                    artifact(
                        "dispatch_offer",
                        "Dispatch window offer",
                        "The window offered, the capacity it was read from and the "
                        "caller's acceptance.",
                    ),
                ),
                tools=("on_call_rota", "capacity_board"),
                config_keys=(
                    ConfigKey(
                        key="severity_bands",
                        description="Severity ladder, assignment rules and response target per band.",
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="vulnerability_criteria",
                        description="What raises a band regardless of the presenting request.",
                        resolved_by="vertical",
                    ),
                    ConfigKey(
                        key="out_of_hours_rota",
                        description="Who is on call by band and hour, with the fallback chain.",
                        resolved_by="owner",
                        required=True,
                    ),
                ),
                kpis=("seconds_to_grade", "band_downgrade_rate", "out_of_hours_answer_rate"),
                channels=("voice", "messaging"),
            ),
            # Demand capture.  Listed before the quoting and screening profiles
            # because high-value triage units talk about quotes without building
            # one, and the lead-magnet widget talks about eligibility checkers.
            Profile(
                name="lead_qualification",
                summary=(
                    "Inbound demand captured, scored on the qualification model "
                    "and pushed to the pipeline with a dated next action."
                ),
                match=(
                    "lead qualifier",
                    "lead-magnet",
                    "scored lead",
                    "pipeline",
                    "sdr",
                    "high-value",
                    "brand-deal",
                    "negotiat",
                ),
                steps=(
                    step(
                        "score",
                        "Score the enquiry on the qualification model",
                        StepKind.ASSESS,
                        "Score need, urgency, budget band, fit and channel on the "
                        "configured model and record which signal moved each component. "
                        "A score without its reasons cannot be tuned later.",
                        produces=("lead_score",),
                    ),
                    step(
                        "pipeline_write",
                        "Push the record to the pipeline with a next action",
                        StepKind.ACT,
                        "Create or update the pipeline record with the score, the owner "
                        "and a dated next action. A lead with no next action is not a "
                        "lead; it is a note.",
                        produces=("pipeline_record",),
                    ),
                    step(
                        "owner_alert",
                        "Alert the owner on value and SLA",
                        StepKind.NOTIFY,
                        "Alert the named owner inside the configured window where the "
                        "score crosses the high-value threshold or the response SLA is "
                        "about to lapse.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "lead_score",
                        "Scored lead record",
                        "Need, urgency, budget band, fit and channel with the signal "
                        "behind each component.",
                    ),
                    artifact(
                        "pipeline_record",
                        "Pipeline record",
                        "The record as it landed in the pipeline, with stage, owner and "
                        "dated next action.",
                    ),
                ),
                tools=("crm_pipeline_write", "lead_scoring_model"),
                config_keys=(
                    ConfigKey(
                        key="qualification_model",
                        description="Scoring dimensions, weights and the thresholds that route.",
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="high_value_threshold",
                        description="The value above which a human is alerted immediately.",
                        resolved_by="owner",
                    ),
                    ConfigKey(
                        key="pipeline_stage_map",
                        description="Which pipeline stage each triage outcome writes to.",
                        resolved_by="owner",
                    ),
                ),
                kpis=("speed_to_lead_seconds", "qualified_lead_rate", "pipeline_acceptance_rate"),
            ),
            # Rule-based screening: eligibility, pre-qualification, candidate and
            # deal screens all run the same mechanism -- criteria in, reason out.
            Profile(
                name="criteria_screen",
                summary=(
                    "Rule-based screening against published criteria -- eligibility, "
                    "pre-qualification, candidate and deal screens -- with a reason per rule."
                ),
                match=(
                    "eligibility",
                    "eligible",
                    "pre-qual",
                    "prequal",
                    "pre-screen",
                    "screener",
                    "screening",
                    "screened",
                    "feasibility",
                    "criteria",
                    "placement test",
                    "placement result",
                    "assessment",
                ),
                steps=(
                    step(
                        "criteria_inputs",
                        "Collect exactly what the rule set needs",
                        StepKind.GATHER,
                        "Ask for the facts the published criteria actually test and "
                        "nothing else. Every extra question is a drop-off; every missing "
                        "one is a second contact.",
                    ),
                    step(
                        "apply_rules",
                        "Apply each criterion and record the result",
                        StepKind.ASSESS,
                        "Work the criteria in order and record pass, fail or unknown "
                        "against the rule id and its source. An unknown is never rounded "
                        "up to a pass, and a near miss is never rounded down to silence.",
                        produces=("criteria_trace",),
                    ),
                    step(
                        "draft_result",
                        "Draft the written result with its reasons",
                        StepKind.DRAFT,
                        "Draft the outcome, the reason for each criterion and what would "
                        "change it, in the wording the market requires -- including "
                        "adverse-action wording where the country pack demands it. This "
                        "is a screening result, not a decision.",
                        produces=("screening_result",),
                    ),
                    step(
                        "deliver_result",
                        "Deliver the result and file it",
                        StepKind.NOTIFY,
                        "Send the result to the contact, file it against the record, and "
                        "route anything the rules could not settle to the named human "
                        "who owns the exception.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "screening_result",
                        "Screening result",
                        "Pass, fail or referred, with the reason per criterion and the "
                        "wording required in this market.",
                    ),
                    artifact(
                        "criteria_trace",
                        "Criteria trace",
                        "Every criterion tested, its result, its rule id and the input "
                        "that decided it.",
                    ),
                ),
                tools=("rule_set_lookup",),
                config_keys=(
                    ConfigKey(
                        key="screening_rule_set",
                        description="The published criteria, versioned, that this screen applies.",
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="adverse_action_wording",
                        description="Required wording for a negative result in this market.",
                        required=True,
                    ),
                    ConfigKey(
                        key="unknown_criterion_policy",
                        description="What happens when a criterion cannot be evidenced.",
                        resolved_by="owner",
                    ),
                ),
                kpis=("screen_completion_rate", "criteria_coverage", "screen_overturn_rate"),
            ),
            # The file-building shape: everything the licensed person needs,
            # assembled before their first hour is spent.
            Profile(
                name="structured_case_intake",
                summary=(
                    "A structured file assembled for the licensed person who will "
                    "take the matter: facts and documents in, opinion out."
                ),
                match=(
                    "fact-find",
                    "needs-analysis",
                    "suitability",
                    "consult",
                    "client brief",
                    "moodboard",
                    "visual brief",
                    "patient intake",
                    "contract intake",
                    "trial intake",
                    "enquiry file",
                    "dept router",
                ),
                steps=(
                    step(
                        "case_facts",
                        "Work the intake schema for this matter type",
                        StepKind.GATHER,
                        "Collect parties, dates, jurisdiction, history, consents and the "
                        "documents the file needs -- and ask for each document at the "
                        "moment you ask about it, not in a chasing email next week.",
                        produces=("case_file",),
                    ),
                    step(
                        "completeness",
                        "Check the file against the schema",
                        StepKind.ASSESS,
                        "Compare the file to the schema and list what is missing by name, "
                        "so the professional opens a file they can act on rather than one "
                        "they have to chase.",
                    ),
                    step(
                        "case_brief",
                        "Draft the brief the professional reads first",
                        StepKind.DRAFT,
                        "Write what is being asked, the facts as given, the gaps, and any "
                        "conflict or red flag you noticed. Describe what you were told; "
                        "never characterise its merits.",
                        produces=("intake_brief",),
                    ),
                    step(
                        "assign_file",
                        "Place the file and book the time",
                        StepKind.NOTIFY,
                        "Place the file with the professional the routing map names and "
                        "book the consultation slot the policy allows, telling the contact "
                        "who will hold it and when.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "case_file",
                        "Structured case file",
                        "Every field the intake schema requires, with the documents "
                        "attached and each source named.",
                    ),
                    artifact(
                        "intake_brief",
                        "Intake brief",
                        "The one-page summary for the licensed person: ask, facts, gaps, "
                        "flags -- and no opinion.",
                    ),
                ),
                tools=("document_request", "case_file_write", "calendar_write"),
                config_keys=(
                    ConfigKey(
                        key="intake_schema",
                        description="Required fields and documents for this matter type.",
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="conflict_check_rules",
                        description="Checks run before a matter is opened, and who resolves a hit.",
                        resolved_by="owner",
                    ),
                    ConfigKey(
                        key="consent_wording",
                        description="Consent and disclosure wording required before intake.",
                        required=True,
                    ),
                ),
                kpis=("file_completeness_rate", "documents_collected_first_pass", "human_rework_rate"),
            ),
            # Priced output.  Sits after lead qualification so that "quotes out"
            # in a triage unit does not drag it into the quoting shape.
            Profile(
                name="quote_and_estimate",
                summary=(
                    "A priced answer built from a structured brief, every figure "
                    "traced to the published price book."
                ),
                match=(
                    "estimat",
                    "quote",
                    "quoting",
                    "quotation",
                    "valuation",
                    "appraiser",
                    "priced",
                    "pricing",
                    "price",
                    "rfq",
                ),
                steps=(
                    step(
                        "priced_brief",
                        "Collect the inputs the price book needs",
                        StepKind.GATHER,
                        "Take the measurable inputs -- quantities, dimensions, distance, "
                        "dates, headcount, spec, condition -- and mark every input you had "
                        "to assume rather than confirm.",
                    ),
                    step(
                        "price_lookup",
                        "Resolve every line against published pricing",
                        StepKind.ASSESS,
                        "Match each line to the published price book or to a quote the "
                        "business has already issued. Stop at the first line that will not "
                        "resolve; that line is a question for a person, not a guess.",
                        produces=("price_trace",),
                    ),
                    step(
                        "quote_draft",
                        "Draft the estimate with its bounds",
                        StepKind.DRAFT,
                        "Draft the figure with its assumptions, exclusions, validity period "
                        "and a range where the inputs are uncertain. An estimate presented "
                        "as a fixed price is a defect, however much the customer wanted one.",
                        produces=("quote_document",),
                    ),
                    step(
                        "issue_quote",
                        "Issue it or hold it at the gate",
                        StepKind.ACT,
                        "Send the estimate from the customer's own channel and log it "
                        "against the enquiry where every line resolved. Where any line was "
                        "assumed, discounted or outside the book, hold it at the approval "
                        "queue instead.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "quote_document",
                        "Written estimate",
                        "The figure as issued, with assumptions, exclusions and validity.",
                        fmt="document",
                    ),
                    artifact(
                        "price_trace",
                        "Price trace",
                        "Each line of the figure against the price-book row or prior quote "
                        "it came from, with the book version.",
                    ),
                ),
                tools=("price_book_lookup", "quote_builder"),
                config_keys=(
                    ConfigKey(
                        key="price_book_version",
                        description="The published price book in force, and the date it took effect.",
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="quote_validity_period",
                        description="How long an issued figure stands before it must be re-quoted.",
                        resolved_by="owner",
                    ),
                    ConfigKey(
                        key="tax_display_rules",
                        description="Whether figures show inclusive or exclusive of tax in this market.",
                        required=True,
                    ),
                ),
                kpis=("minutes_to_quote", "unpriced_line_rate", "quote_acceptance_rate"),
            ),
            # The intake conversation that has to end in a held slot.
            Profile(
                name="booking_intake",
                summary=(
                    "Intake that ends in a held slot: live availability checked, "
                    "booking taken, confirmation back in the thread."
                ),
                match=(
                    "booker",
                    "direct-booking",
                    "bookings taken",
                    "reservations",
                    "box-office",
                    "resale",
                    "seat",
                ),
                steps=(
                    step(
                        "availability",
                        "Check live availability",
                        StepKind.ASSESS,
                        "Read the real calendar or inventory, never a cached view, and offer "
                        "only the options the booking rules allow for this customer and "
                        "service.",
                    ),
                    step(
                        "hold_slot",
                        "Take the booking with its identifiers",
                        StepKind.ACT,
                        "Hold the slot with the identifiers the operation will need -- "
                        "vehicle, party size, room, seat, service, duration -- and take the "
                        "deposit the policy requires rather than one you decided on.",
                        produces=("booking_confirmation",),
                    ),
                    step(
                        "confirm_booking",
                        "Confirm in the same thread",
                        StepKind.NOTIFY,
                        "Confirm what was booked, what it costs, what happens next and how "
                        "to change it, in the thread the customer started.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "booking_confirmation",
                        "Booking confirmation",
                        "Slot, resource, identifiers, deposit state and confirmation id.",
                    ),
                ),
                tools=("calendar_write", "inventory_lookup"),
                config_keys=(
                    ConfigKey(
                        key="booking_rules",
                        description="Lead times, durations, resource matching and who may book what.",
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="deposit_policy",
                        description="When a deposit is required and how much.",
                        resolved_by="owner",
                    ),
                    ConfigKey(
                        key="cancellation_policy",
                        description="Cancellation and change terms quoted at the point of booking.",
                        resolved_by="owner",
                        required=True,
                    ),
                ),
                kpis=("booking_conversion_rate", "slot_accuracy", "no_show_rate"),
            ),
            # Account and service requests worked live.  Ahead of the matching
            # profile because an in-stay concierge makes "recommendations" too.
            Profile(
                name="service_request_desk",
                summary=(
                    "A live account or service request worked to completion in the "
                    "thread, or handed over with everything already tried."
                ),
                match=(
                    "issues resolved",
                    "support agent",
                    "helpline",
                    "walked to completion",
                    "in-stay",
                    "loyalty",
                    "proactively",
                    "provisions",
                    "accessibility",
                    "activation",
                    "navigator",
                    "seller",
                ),
                steps=(
                    step(
                        "account_context",
                        "Identify the account and read the history",
                        StepKind.GATHER,
                        "Resolve the account, verify the contact to the configured standard, "
                        "and read the recent history before asking them to repeat any of it.",
                    ),
                    step(
                        "resolve_steps",
                        "Work the documented steps in order",
                        StepKind.ACT,
                        "Run the runbook for this request type step by step and record what "
                        "each one returned. You execute the runbook; you do not invent a fix "
                        "outside it, and you do not keep trying once it is exhausted.",
                        produces=("resolution_log",),
                    ),
                    step(
                        "confirm_outcome",
                        "Confirm the outcome and the next step",
                        StepKind.NOTIFY,
                        "Say what was done, what happens next and by when. Where the "
                        "remedy is a credit, a refund, an exception or an engineer, name "
                        "the person who must approve it and route it to them.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "request_record",
                        "Service request record",
                        "The request as understood, the account it belongs to and its state.",
                    ),
                    artifact(
                        "resolution_log",
                        "Resolution log",
                        "Each runbook step attempted, what it returned, and where the "
                        "request stopped.",
                    ),
                ),
                tools=("account_lookup", "runbook_steps", "identity_verification"),
                config_keys=(
                    ConfigKey(
                        key="verification_standard",
                        description="How a contact is verified before account detail is discussed.",
                        required=True,
                    ),
                    ConfigKey(
                        key="runbook_library",
                        description="Documented steps per request type, versioned.",
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="goodwill_limits",
                        description="What may be credited or arranged without a person, if anything.",
                        resolved_by="owner",
                        required=True,
                    ),
                ),
                kpis=("first_contact_resolution_rate", "handle_time_minutes", "repeat_contact_rate"),
            ),
            # Requirement in, ranked options out.
            Profile(
                name="match_and_recommend",
                summary=(
                    "Requirements matched to live stock, courses, programmes or "
                    "proof, with the reason each option scored where it did."
                ),
                match=(
                    "matcher",
                    "matchmaker",
                    "matched",
                    "matches",
                    "matching",
                    "recommendation",
                    "guided selling",
                    "product advisor",
                    "plan advisor",
                    "learning-path",
                    "next-course",
                    "counselor",
                    "best-fit",
                ),
                steps=(
                    step(
                        "requirements",
                        "Capture the requirement in indexed dimensions",
                        StepKind.GATHER,
                        "Take the requirement on the dimensions the catalogue is actually "
                        "indexed on -- budget, level, spec, location, dates, goals -- so the "
                        "match runs on data rather than on adjectives.",
                    ),
                    step(
                        "rank_options",
                        "Rank the live catalogue against it",
                        StepKind.ASSESS,
                        "Score the live catalogue against the requirement and keep the "
                        "reason each option scored where it did, including the ones you "
                        "dropped and why.",
                        produces=("match_set",),
                    ),
                    step(
                        "shortlist",
                        "Draft the shortlist with its fit and misfit",
                        StepKind.DRAFT,
                        "Draft a short list of options, each with what fits and what does "
                        "not. Where nothing fits, say so and offer the alternative rather "
                        "than padding the list to look useful.",
                        produces=("recommendation_note",),
                    ),
                    step(
                        "send_shortlist",
                        "Send it and attach it to the record",
                        StepKind.NOTIFY,
                        "Send the shortlist in the contact's language and attach it to the "
                        "record so the next conversation starts from it.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "match_set",
                        "Match set",
                        "Every option considered with its score, the dimensions it was "
                        "scored on and the catalogue version.",
                    ),
                    artifact(
                        "recommendation_note",
                        "Shortlist",
                        "The options put forward, what fits, what does not, and what was "
                        "ruled out.",
                    ),
                ),
                tools=("catalogue_search", "availability_lookup"),
                config_keys=(
                    ConfigKey(
                        key="catalogue_source",
                        description="The live catalogue, stock or programme list this match runs against.",
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="match_dimensions",
                        description="Dimensions the match scores on, and their weights.",
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="shortlist_size",
                        description="How many options to put forward before choice becomes noise.",
                        resolved_by="owner",
                        default=3,
                    ),
                ),
                kpis=("match_acceptance_rate", "shortlist_conversion", "no_match_disclosure_rate"),
            ),
            # The biggest shape in the family: bounded question answering from a
            # named source, which is also where hallucination costs the most.
            Profile(
                name="grounded_answer_desk",
                summary=(
                    "Bounded question answering from named sources -- Q&A pack, "
                    "handbook, label, docs, archive, fee and fare schedules -- with "
                    "the source shown."
                ),
                match=(
                    "faq",
                    "q&a",
                    "policy",
                    "handbook",
                    "docs",
                    "grounded",
                    "label-bound",
                    "sop",
                    "archive",
                    "menu",
                    "allergen",
                    "stock and hours",
                    "availability answerer",
                    "explainer",
                    "explanation",
                    "explained",
                    "fee",
                    "bill",
                    "product base",
                    "service base",
                    "data-room",
                    "deflection",
                    "sourced",
                    "requirement answers",
                    "information service",
                    "rules",
                ),
                steps=(
                    step(
                        "retrieve",
                        "Retrieve from the named sources",
                        StepKind.ASSESS,
                        "Search the configured sources and keep the passage, the document "
                        "and its version beside the answer. Silence in the source is itself "
                        "an answer: report that the source does not cover it.",
                        produces=("source_citation",),
                    ),
                    step(
                        "draft_answer",
                        "Draft the answer inside its boundary",
                        StepKind.DRAFT,
                        "Write the answer in the contact's language, name the source, and "
                        "state the boundary where interpretation, advice or a judgement call "
                        "belongs to a person rather than to you.",
                        produces=("answered_question",),
                    ),
                    step(
                        "deliver_answer",
                        "Send it with its source and the way out",
                        StepKind.ACT,
                        "Send the answer with its source reference, and offer the handover "
                        "in the same message wherever the source stopped short of the "
                        "question that was actually asked.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "answered_question",
                        "Answered question",
                        "The question as asked, the answer given and the boundary stated.",
                    ),
                    artifact(
                        "source_citation",
                        "Source reference",
                        "Document, passage and version the answer was taken from.",
                    ),
                ),
                tools=("source_retrieval", "source_version_check"),
                config_keys=(
                    ConfigKey(
                        key="source_corpora",
                        description=(
                            "The documents this desk may answer from -- handbook, label, "
                            "docs, archive, schedule -- and their versions."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="answer_boundaries",
                        description="Question types that must be referred rather than answered.",
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="citation_style",
                        description="How a source is shown to the contact in this market.",
                    ),
                ),
                kpis=("grounded_answer_rate", "deflection_rate", "unsourced_answer_count"),
            ),
            # One contact, one thread -- across channels, languages and parties.
            Profile(
                name="thread_continuity",
                summary=(
                    "One contact, one thread: channel switches, languages and "
                    "second parties handled without losing context."
                ),
                match=(
                    "multilingual",
                    "language",
                    "mid-session",
                    "channel continuity",
                    "omnichannel",
                    "one thread per contact",
                    "dual-contact",
                    "separate parent",
                    "switchboard",
                    "messaging liaison",
                ),
                steps=(
                    step(
                        "resolve_identity",
                        "Reconcile the thread before opening one",
                        StepKind.ASSESS,
                        "Match the inbound message to an existing contact and thread across "
                        "every channel before creating anything. A duplicate thread is lost "
                        "context wearing a new id.",
                    ),
                    step(
                        "carry_context",
                        "Carry the context across the switch",
                        StepKind.ACT,
                        "Move the full history across the channel, language or second party "
                        "-- guardian, agent, colleague -- keeping each party's consent and "
                        "visibility as configured.",
                        produces=("unified_thread",),
                    ),
                    step(
                        "continue_thread",
                        "Tell them what you already hold",
                        StepKind.NOTIFY,
                        "Open on the new channel or in the new language by stating what you "
                        "already have, so nobody is asked to repeat themselves to prove the "
                        "handover worked.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "unified_thread",
                        "Unified thread",
                        "One conversation per contact with every channel, language and turn "
                        "in sequence.",
                        fmt="log",
                    ),
                    artifact(
                        "party_map",
                        "Party map",
                        "Who is on this thread, in what role, and what each of them may see.",
                    ),
                ),
                tools=("identity_resolution", "thread_merge", "translation"),
                config_keys=(
                    ConfigKey(
                        key="identity_match_rules",
                        description="How a contact is matched across channels and identifiers.",
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="party_roles",
                        description="Second-party roles this vertical recognises and what each may see.",
                        resolved_by="vertical",
                    ),
                    ConfigKey(
                        key="channel_switch_policy",
                        description="Which channel switches are offered, and when.",
                    ),
                ),
                kpis=("duplicate_thread_rate", "context_carry_rate", "language_match_rate"),
                channels=("web_chat", "messaging", "email", "voice", "social_dm"),
            ),
            # The escalation anchor: models.Escalation.HUMAN_HANDOFF points here.
            Profile(
                name="human_handover",
                summary=(
                    "The handover packet: everything the person taking over needs, "
                    "assembled before they are interrupted."
                ),
                match=("handoff", "handover"),
                steps=(
                    step(
                        "trigger_check",
                        "Check the handover triggers",
                        StepKind.ASSESS,
                        "Test the conversation against the configured triggers -- gate, "
                        "sentiment, value, repeat contact, explicit request -- and hand over "
                        "on the first one rather than trying one more turn.",
                    ),
                    step(
                        "packet",
                        "Assemble the packet",
                        StepKind.DRAFT,
                        "Build the packet: transcript, contact, intent summary, urgency flag, "
                        "what has already been tried, and the one decision the person is "
                        "being asked to make.",
                        produces=("handover_packet",),
                    ),
                    step(
                        "deliver_packet",
                        "Deliver it and close the loop both ways",
                        StepKind.NOTIFY,
                        "Deliver it to the recipient named for this hour of this day, confirm "
                        "a human has accepted it, and tell the contact who holds it now and "
                        "when they will hear back.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "handover_packet",
                        "Human handover packet",
                        "Transcript, contact, intent summary, urgency flag, what was tried "
                        "and the decision required.",
                    ),
                ),
                tools=("handover_queue", "presence_lookup"),
                config_keys=(
                    ConfigKey(
                        key="handover_triggers",
                        description="What forces a handover, in priority order.",
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="coverage_rota",
                        description="Who receives a handover by hour and day, with the fallback.",
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="handover_sla",
                        description="How long a packet may sit before it escalates again.",
                        resolved_by="owner",
                    ),
                ),
                kpis=("seconds_to_human", "handover_acceptance_rate", "context_completeness"),
            ),
            # Fallback: the general front desk.  Anything whose whole job is
            # "understand it, capture them, send it to the right place" lands here.
            Profile(
                name="front_desk_concierge",
                summary=(
                    "General intent recognition and routing: answer what is "
                    "answerable, capture the contact, route the rest."
                ),
                steps=(
                    step(
                        "draft_answer",
                        "Answer what the sources cover",
                        StepKind.DRAFT,
                        "Answer from the Q&A pack and the business profile where they cover "
                        "the question, and say what you cannot answer plainly rather than "
                        "filling the gap with something plausible.",
                    ),
                    step(
                        "capture_and_route",
                        "Capture the contact and send it on",
                        StepKind.ACT,
                        "Capture a name and a reachable channel on every thread whatever the "
                        "outcome, then send the request to the queue the routing map names "
                        "with the intent and urgency you assigned.",
                        produces=("routed_intent",),
                    ),
                    step(
                        "close_loop",
                        "Leave nothing in silence",
                        StepKind.NOTIFY,
                        "Tell the contact what happens next and by when. No thread ends "
                        "unanswered, and none is closed as no-action without a logged reason.",
                    ),
                ),
                artifacts=(
                    artifact(
                        "routed_intent",
                        "Routed intent",
                        "The intent recognised, the destination it was sent to and the rule "
                        "that sent it.",
                    ),
                ),
                tools=("source_retrieval", "routing_map_lookup"),
                config_keys=(
                    ConfigKey(
                        key="answerable_scope",
                        description="What this desk may answer itself before it must route.",
                        resolved_by="owner",
                        required=True,
                    ),
                ),
                kpis=("containment_rate", "contact_capture_rate", "misroute_rate"),
            ),
        )

    # -- plan --------------------------------------------------------------
    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Receive, capture, triage, route.

        Deliberately short.  Profile steps are appended after these, so the
        skeleton is the head of the operation -- the part that is identical
        whether the request becomes a quote, a screen or a first notice -- and
        the profile carries the tail.
        """
        return (
            step(
                "receive",
                "Receive and acknowledge",
                StepKind.OBSERVE,
                "Take the inbound event on the channel it arrived on, resolve the contact "
                "and thread, note the language and the timestamp, and acknowledge inside "
                "the configured first-response SLA even before you know the answer.",
                produces=("conversation_transcript",),
            ),
            step(
                "capture",
                "Capture the structured detail",
                StepKind.GATHER,
                "Work the intake schema conversationally -- one question at a time, in the "
                "contact's language, never a form pasted into a chat -- and stop asking the "
                "moment the record is complete enough to route. Never ask for what the "
                "record already holds.",
                produces=("intake_record", "contact_record"),
            ),
            step(
                "triage",
                "Classify intent, urgency and value",
                StepKind.ASSESS,
                "Classify the request against the configured intents and grade urgency "
                "against the bands, from the facts rather than the tone. Note by name any "
                "required field still missing.",
                produces=("triage_decision",),
            ),
            step(
                "route",
                "Choose the destination and record why",
                StepKind.DECIDE,
                "Pick the destination from the routing map for this intent and band, or the "
                "human gate where the request sits outside it, and record the rule that "
                "produced the choice so a reviewer can see why this went where it went.",
                produces=("triage_decision",),
            ),
        )

    # -- artefacts ---------------------------------------------------------
    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "conversation_transcript",
                "Conversation transcript",
                "Every turn of the conversation with channel, language, actor and "
                "timestamp, retained as one thread per contact.",
                fmt="log",
            ),
            artifact(
                "intake_record",
                "Structured intake record",
                "The fields the intake schema requires for this request type, each with "
                "the turn of the conversation it came from.",
            ),
            artifact(
                "contact_record",
                "Captured contact",
                "Name, reachable channel, language and consent state, captured on every "
                "thread whatever the outcome.",
            ),
            artifact(
                "triage_decision",
                "Triage decision",
                "Intent, urgency band, value band, destination and the rule that "
                "assigned each one.",
            ),
        )

    # -- inputs ------------------------------------------------------------
    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "Inbound message with its channel, language and timestamp",
            "Contact and thread history for this person across every channel",
            "Intake schema for this request type",
            "Routing map and urgency bands",
            "Q&A pack and the other named sources this unit may answer from",
        )

    # -- mission -----------------------------------------------------------
    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        """How an intake unit works, and what that discipline costs.

        Varies by profile and by vertical, because the discipline genuinely
        differs: a first-notice clerk and a menu answerer share a skeleton and
        almost nothing else.
        """
        lines = [
            "HOW YOU WORK. You run one thread per contact, on whichever rails the active "
            "country pack names, and you open by understanding what is actually being "
            "asked rather than pushing the request into the first category that fits. "
            "You gather the structured detail the next step needs one "
            "question at a time, in the contact's language, and you stop the moment the "
            "record is complete enough to route -- an interrogation loses the job as surely "
            "as a guess does.",
            "You grade urgency against the configured bands rather than the words that were "
            "used: a calm message can be an emergency and a furious one often is not. "
            "Routing is a decision you make from the routing map and record with its reason, "
            "so a reviewer can see why this request went where it went.",
            "Anything you say that could be checked comes from a source you can name -- the "
            "Q&A pack, the published price book, the rule set, the vertical overlay -- and "
            "what you cannot ground you hand to a person instead of improvising. "
            f"{_PROFILE_NOTES[profile.name].rstrip('.')}.",
        ]

        vertical = record.get("vertical") or {}
        if vertical:
            lines.append(
                f"You are working {vertical['name'].lower()} requests, so the terminology, "
                "the required fields, the intervals and the statutory dates come from the "
                "vertical overlay and the country pack, never from your own sense of the trade."
            )

        if record["type"].startswith("playbook"):
            lines.append(
                "You are a playbook: one trigger fires you, you run the sequence once, and "
                "you leave the standing conversation to the agent that owns it."
            )

        return "\n\n".join(lines)

    # -- guardrails --------------------------------------------------------
    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        """MF1's own failure modes, each with something a reviewer can check."""
        guardrails = [
            Guardrail(
                id="GR-MF1-GROUNDED-ANSWER",
                rule=(
                    "Every checkable statement comes from a named source. Where the "
                    "source is silent the unit says so and offers the handover."
                ),
                check=(
                    "Each answered claim in the reply carries a reference to the Q&A pack, "
                    "source corpus, price book or rule set with its version; a draft "
                    "containing an unreferenced claim cannot be sent."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF1-URGENCY-FLOOR",
                rule=(
                    "Urgency is assigned by rule. The unit may raise the band the rules "
                    "produced; it may never lower it."
                ),
                check=(
                    "triage_decision records the rule-assigned band alongside the final "
                    "band; any final band below the assigned one is rejected and routed to "
                    "the named human."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF1-COMPLETE-BEFORE-ROUTE",
                rule=(
                    "A routing decision needs the fields the intake schema marks required. "
                    "A missing field is a question or a gate, never an assumption."
                ),
                check=(
                    "No route step completes while a required intake field is empty; the "
                    "missing field is named in the record and in the handover if one follows."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF1-ONE-THREAD",
                rule=(
                    "One contact, one thread. Channel, language and party switches carry "
                    "the context with them."
                ),
                check=(
                    "The unit searches every channel for an existing contact before opening "
                    "a thread; a match produces a merge, not a second thread, and the "
                    "transcript shows the switch."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF1-NO-SILENT-DROP",
                rule=(
                    "Nothing arrives and disappears. Every thread ends in an answer, a "
                    "booked next action or a handover packet."
                ),
                check=(
                    "Threads closed without one of those three carry a logged reason and a "
                    "named closer; first_response_seconds is recorded on every thread and "
                    "an SLA breach raises an alert rather than a silence."
                ),
                source="mechanism_family",
            ),
        ]

        # Revenue-critical intake is judged on the clock as well as the content,
        # so give the speed promise a check of its own rather than leaving it as
        # a line of mission prose.
        if record["flags"]["revenue_critical"]:
            guardrails.append(
                Guardrail(
                    id="GR-MF1-FIRST-RESPONSE-CLOCK",
                    rule=(
                        "First response goes out inside the configured SLA even when the "
                        "answer is only that the request has been received and by whom."
                    ),
                    check=(
                        "Every thread carries a first-response timestamp measured from "
                        "arrival, not from the first working hour; breaches are counted "
                        "against the unit and surfaced on the owner's digest."
                    ),
                    source="mechanism_family",
                )
            )
        return tuple(guardrails)
