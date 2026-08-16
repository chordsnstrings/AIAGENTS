"""MF14 -- protocol & incident playbooks.

Every other family in the catalogue runs on a cadence or a queue.  This one runs
on an event: a smell of gas mid-chat, a child still in the building at closing
time, a letter with a date on it, a batch that failed its test, a disclosure
somebody has waited months to make.  The event decides everything -- what runs,
in what order, how long there is and who has to be holding it when the unit
stops -- and the business rarely gets a second attempt, because the scene is
tidied, the memory fades, the log rotates and the window shuts.  So the product
of a unit here is never a resolution.  It is a recognised event, an evidenced
record, a clock that started at the right moment and a named human who has the
thing in their hands and knows it.

Three disciplines carry that and each of them fails in a way nobody notices at
the time.  The first is recognition: an event that was not recognised as one is
handled as an ordinary conversation, and every clock in the protocol is already
lost by the time somebody realises.  So recognition is a test against a written
list rather than a judgement, and the time of recognition is stamped, because
every deadline in this family is measured from it and not from the moment
somebody got round to the work.  The second is order.  Protocol steps are
written in their order for a reason -- evidence before the scene is altered,
containment before the account is used again, the interlock before anything
commercial -- so a step that cannot be run is recorded as blocked and never
quietly skipped.  The third is the handover.  A protocol whose steps all ran and
whose escalation nobody acknowledged has failed, so an escalation that is not
picked up re-escalates on the configured fallback rather than ageing on a queue.

The third standing rule is not a caveat on this family; it is the shape of it.
Escalation *is* the product.  You recognise, you execute the fixed steps, you
assemble the pack and you stop at the human gate -- and the decisions that sit
past that gate are the whole reason the gate exists: whether to notify a
regulator, whether to admit liability, what the statement says, whether the
waiver stands, whether the machine restarts, what the clinician does next.  The
unit prepares every one of those completely and takes none of them.  Which
protocol applies, what its steps are, what each clock is worth in this market,
who is on the chain tonight and what a record must contain to survive an insurer
or a court all arrive as configuration, which is how one engine carries an
evacuation script, a garnishment order and a batch recall without knowing which
of them it is holding.
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

#: Read by every unit of the family.  Between them these seven keys are the
#: whole protocol: which events are recognised, what each one is worth in time,
#: who has to be holding it, what a person alone may decide, what the record
#: must contain to survive later scrutiny, who must be told and what stops going
#: out while the thing is live.  Change them and the same code runs an
#: evacuation script, a bereavement closure and a dangerous-goods hold.
_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="protocol_register",
        description=(
            "Every event this business runs a protocol for: the recognition "
            "criteria that say the event has occurred, the fixed steps it "
            "carries in their order, and the point at which the protocol stops."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="statutory_clocks",
        description=(
            "The deadlines each class of event carries in this market: what "
            "each one is measured from, how long it runs, the warning points "
            "before it expires and the role that owns it."
        ),
        required=True,
    ),
    ConfigKey(
        key="escalation_chain",
        description=(
            "The named roles for each event class in the order they are worked, "
            "the route to each, the interval between attempts, the "
            "acknowledgement window, the out-of-hours position and the point at "
            "which the chain leaves the business."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="reserved_decisions",
        description=(
            "Which decisions inside each protocol belong to a person, who holds "
            "each one, and what may and may not proceed while one is "
            "outstanding."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="evidence_standard",
        description=(
            "What must be captured for each class of event, in what form, and "
            "how long it is retained, so the record still stands when an "
            "insurer, a regulator or a court reaches it in this market."
        ),
        required=True,
    ),
    ConfigKey(
        key="notification_matrix",
        description=(
            "Who must be told about each class of event, in what order and with "
            "what wording, and which of those notifications are mandatory in "
            "this market rather than discretionary."
        ),
        required=True,
    ),
    ConfigKey(
        key="suppression_rules",
        description=(
            "What stops going out to an affected record while a protocol is "
            "live -- marketing, reminders, review requests, automated chasers, "
            "renewals -- and what releases it again."
        ),
        resolved_by="owner",
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

#: The fourteen protocol shapes actually present in the catalogue, most specific
#: first.  Tokens are the nouns of the mechanism -- "lockout", "verbatim",
#: "quarantine", "keyholder cascade", "docket" -- rather than the verbs every
#: unit here shares ("logged", "captured", "routed", "protocol"), which would
#: match all 141 of them.  Order carries real weight in six places.  The
#: interlock tokens must claim the physical and clinical protocols before any
#: commercial profile sees them.  The disclosure tokens must claim safeguarding,
#: harassment and ethics captures before "incident" reaches them.  The breach
#: tokens must claim the ransomware unit before "insurer" pulls it into the
#: evidence profile.  The brief tokens must claim the parts trace whose product
#: is an executive brief before "trace" swallows it.  The comms tokens must claim
#: the media inquiry before "deadline" files it as a docketing job.  And the mode
#: tokens must claim the weather closure before "rebook" reads a mass rebooking
#: cascade as a piece of service recovery.
_PROFILES: tuple[Profile, ...] = (
    Profile(
        name="safety_interlock",
        summary=(
            "A fixed physical or clinical protocol that runs ahead of everything "
            "else, blocks every commercial step behind it and has no override "
            "inside the unit."
        ),
        match=(
            "evacuation",
            "emergency-line",
            "emergency routing",
            "hard-coded",
            "first-aid",
            "poison-line",
            "allerg",
            "lockout",
            "stop-work",
            "ground-fault",
            "remote isolation",
            "life-support",
            "priority register",
            "protection-register",
            "protection rules",
            "dangerous goods",
            "dangerous-goods",
            "hard stop",
            "no override",
            "age-gate",
        ),
        steps=(
            step(
                "run_the_recognition_list",
                "Test the presentation against the written list",
                StepKind.ASSESS,
                (
                    "Match what you have in front of you against the written "
                    "recognition list for this protocol, item by item, and record which "
                    "item matched. You are reading a list, not grading a severity: the "
                    "list exists precisely so that the question 'is this bad enough' is "
                    "never asked by a probabilistic component. Where the presentation "
                    "matches nothing on the list but sits near it, the protocol runs "
                    "anyway and the near-match is recorded for the human."
                ),
                produces=("recognition_checklist",),
            ),
            step(
                "hold_everything_behind_the_interlock",
                "Block every commercial step until the protocol has run",
                StepKind.ACT,
                (
                    "Put a hold on every commercial and convenience step behind this "
                    "protocol -- the booking, the quote, the upsell, the service action, "
                    "the reactivation -- and keep it there until the fixed steps have "
                    "completed and the named human is holding the case. The hold has no "
                    "override inside the unit and no exception for a good reason, a "
                    "regular customer or a busy day; a request to lift it is logged as a "
                    "request and routed, never actioned here. Record the hold with the "
                    "time it went on and everything it stopped."
                ),
                produces=("interlock_block_record",),
            ),
        ),
        artifacts=(
            artifact(
                "recognition_checklist",
                "Recognition checklist",
                (
                    "The written list for this protocol with the item that matched, the "
                    "items that did not, the near-matches noted for the human and the "
                    "time the match was made."
                ),
            ),
            artifact(
                "interlock_block_record",
                "Interlock block record",
                (
                    "What was held behind the interlock, when the hold went on, every "
                    "request to lift it with who asked, and the time and authority under "
                    "which it was finally lifted."
                ),
                "log",
            ),
        ),
        tools=("recognition_checklist", "emergency_directory", "action_block"),
        config_keys=(
            ConfigKey(
                key="recognition_criteria",
                description=(
                    "The written list of presentations that trigger this protocol in "
                    "this vertical, and the near-misses recorded rather than actioned."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="emergency_routing",
                description=(
                    "The emergency number, poison line, duty authority or on-call "
                    "engineer this market routes each condition to, with the script."
                ),
                required=True,
            ),
        ),
        kpis=(
            "presentations tested against the written list rather than judged",
            "commercial steps that ran before the protocol had completed",
            "interlocks lifted with a recorded authority",
        ),
        channels=("voice",),
    ),
    Profile(
        name="confidential_disclosure",
        summary=(
            "Somebody discloses something: it is captured in their own words, "
            "routed to one named person on a restricted channel, and the unit "
            "goes no further."
        ),
        match=(
            "safeguarding",
            "verbatim",
            "confidential capture",
            "harassment",
            "grievance",
            "ethics report",
            "title-ix",
            "designated",
            "fee earner",
            "routed to medical",
            "no agent conclusions",
            "goes no further",
            "never investigates",
        ),
        steps=(
            step(
                "capture_it_in_their_own_words",
                "Take it down verbatim and add nothing",
                StepKind.GATHER,
                (
                    "Record what was said in the words it was said in, with the time, the "
                    "channel and who was present. Do not paraphrase it, tidy it, summarise "
                    "it or ask the question that would take it further, because a leading "
                    "question here contaminates an investigation somebody else has to run "
                    "and can cost the disclosure its value entirely. Capture what is "
                    "needed to reach the person and no more, and write no impression, "
                    "assessment or conclusion of your own anywhere in the record."
                ),
                produces=("verbatim_capture",),
            ),
            step(
                "route_it_to_one_named_person",
                "Deliver it to the designated recipient alone",
                StepKind.NOTIFY,
                (
                    "Send it to the single designated recipient the configuration names "
                    "-- the safeguarding lead, the designated officer, the fee earner, "
                    "the medical staff -- on the restricted route, and to nobody else. It "
                    "does not enter the general case notes, the shared inbox, the team "
                    "channel or any digest. Then stop: no follow-up question, no second "
                    "conversation on the subject, no status chase to the discloser, and "
                    "no acknowledgement that implies anybody has assessed anything."
                ),
                produces=("restricted_routing_receipt",),
            ),
        ),
        artifacts=(
            artifact(
                "verbatim_capture",
                "Verbatim capture",
                (
                    "What was said, in the words it was said in, with time, channel and "
                    "those present, and no impression, assessment or conclusion added."
                ),
                "document",
            ),
            artifact(
                "restricted_routing_receipt",
                "Restricted routing receipt",
                (
                    "The one recipient it went to, the restricted route used, the time of "
                    "delivery, the acknowledgement received and the visibility "
                    "restrictions applied to the record."
                ),
            ),
        ),
        tools=("verbatim_recorder", "restricted_case_store", "named_lead_directory"),
        config_keys=(
            ConfigKey(
                key="designated_recipients",
                description=(
                    "The one named role that receives each class of disclosure, with "
                    "the deputy, the out-of-hours route and the acknowledgement window."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="disclosure_handling_rules",
                description=(
                    "What may be asked, what must be recorded and what must never be "
                    "shared for each class of disclosure in this market."
                ),
                required=True,
            ),
        ),
        kpis=(
            "disclosures reaching the designated person inside the window",
            "captures containing an assessment nobody asked the unit for",
            "disclosures visible to anyone outside the restricted route",
        ),
        channels=("named_role_inbox",),
    ),
    Profile(
        name="breach_containment",
        summary=(
            "A data or security event: the clock starts at discovery, the scope "
            "is compiled as fact with its unknowns named, containment runs from "
            "the runbook and every notification is drafted and held."
        ),
        match=(
            "data breach",
            "citizen data",
            "security incident",
            "ransomware",
            "phishing",
            "isolation runbook",
            "security-researcher",
            "containment",
            "indicator",
            "scope-of-data",
        ),
        steps=(
            step(
                "scope_what_was_exposed",
                "State the scope as fact, including what is not yet known",
                StepKind.ASSESS,
                (
                    "Compile which records were reachable, whose they are, which fields "
                    "they carry, over what window and by what route, and set out beside "
                    "it the part of the scope that is still unknown and what would settle "
                    "it. The notification decision that follows turns on this document, "
                    "so an optimistic scope is worse than an incomplete one: name the "
                    "unknowns as unknowns rather than reasoning them away, and revise the "
                    "assessment as the picture changes instead of overwriting it."
                ),
                produces=("exposure_scope_assessment",),
            ),
            step(
                "run_the_containment_runbook",
                "Preserve the state, then contain",
                StepKind.ACT,
                (
                    "Preserve the logs, sessions and system state the runbook requires "
                    "before anything is changed, because the containment action is "
                    "usually the thing that destroys the evidence of how the access "
                    "happened. Then work the runbook's steps in order -- revoke, isolate, "
                    "rotate, freeze, tighten the finance controls for the window -- each "
                    "with its time and actor. Containment is the whole of your authority "
                    "here: who is told, and whether anyone is told, is reserved."
                ),
                produces=("containment_log",),
            ),
        ),
        artifacts=(
            artifact(
                "exposure_scope_assessment",
                "Exposure scope assessment",
                (
                    "Records reachable, data subjects, field classes, window and route, "
                    "with the unknown part of the scope named as unknown and each "
                    "revision kept beside the last."
                ),
                "report",
            ),
            artifact(
                "containment_log",
                "Containment log",
                (
                    "The preserved state taken before any change, then every containment "
                    "step from the runbook with its time, actor and result."
                ),
                "log",
            ),
        ),
        tools=("log_preserver", "exposure_scoper", "containment_runbook"),
        config_keys=(
            ConfigKey(
                key="breach_notification_rules",
                description=(
                    "The notification thresholds, recipients and clocks this market "
                    "attaches to a data or security event, and who may decide."
                ),
                required=True,
            ),
            ConfigKey(
                key="containment_runbook",
                description=(
                    "The containment steps for each indicator class, in order, with "
                    "the state that must be preserved before each one runs."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "containment steps run inside the runbook's window",
            "scope assessments naming their unknowns explicitly",
            "notifications that left the business without the reserved decision",
        ),
        channels=("owner_dashboard",),
    ),
    Profile(
        name="incident_evidence",
        summary=(
            "A physical incident recorded to evidential standard while the "
            "scene, the people and the memories are still there, with the "
            "insurer's pack built from the record and no admission in it."
        ),
        match=(
            "insurer",
            "witness",
            "incident capture",
            "incident report",
            "incident record",
            "incident log",
            "shoplifting",
            "lost-time",
            "crowd incident",
            "serious incident",
            "family liaison",
            "evidence preserved",
            "preserved evidence",
            "de-escalation",
        ),
        steps=(
            step(
                "record_the_scene_and_the_people",
                "Capture the scene and the accounts before they go",
                StepKind.GATHER,
                (
                    "Photograph what is there with its time and place, take each witness's "
                    "account in their own words and one at a time, out of earshot of the "
                    "others, and write the sequence with times: who was present, what was "
                    "in use, what the "
                    "conditions were, what was said. All of this decays within hours -- "
                    "the scene is tidied, the shift changes, the accounts converge on "
                    "whatever was discussed in the meantime -- so capture comes before "
                    "anybody is comforted, anything is repaired and anyone is told."
                ),
                produces=("scene_record",),
            ),
            step(
                "assemble_the_claim_pack",
                "Build the insurer's pack out of the record",
                StepKind.DRAFT,
                (
                    "Fill the first-notification form and the aftercare schedule from what "
                    "the record actually holds, and from nothing else. State what was "
                    "observed, by whom and when, and leave cause, fault and apportionment "
                    "entirely blank: a sympathetic sentence in an incident pack is read "
                    "later as an admission, and it is read that way by people who were "
                    "not there. Submission of the pack, and every word said to the injured "
                    "party about who is responsible, is reserved."
                ),
                produces=("claim_notification_pack",),
            ),
        ),
        artifacts=(
            artifact(
                "scene_record",
                "Scene and witness record",
                (
                    "Timed and located media, each witness account taken one at a time in "
                    "their own words, the sequence of events with times, the conditions "
                    "and the people present."
                ),
                "bundle",
            ),
            artifact(
                "claim_notification_pack",
                "Claim notification pack",
                (
                    "The insurer's first-notification form built from the record, the "
                    "aftercare scheduled, and explicitly empty fields where cause, fault "
                    "and apportionment belong."
                ),
                "document",
            ),
        ),
        tools=("media_capture", "witness_recorder", "claim_form_builder"),
        config_keys=(
            ConfigKey(
                key="incident_evidence_requirements",
                description=(
                    "What an incident of this class must contain in this vertical: "
                    "media, witnesses, measurements, forms and retention."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="insurer_notification_rules",
                description=(
                    "The insurer's notification window, the form each class of loss "
                    "uses, and who may submit it."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "incidents captured with media and one-at-a-time witness accounts the same day",
            "claim packs accepted without a further evidence request",
            "records containing an admission, a cause or an apportionment",
        ),
    ),
    Profile(
        name="sensitive_mode",
        summary=(
            "A death, a bereavement or an incapacity: every automated channel "
            "goes silent for that record, and one short human message waits for "
            "a person to send."
        ),
        match=(
            "deceased",
            "condolence",
            "bereavement",
            "euthanasia",
            "estate",
            "incapacitated",
            "marketing suppressed",
            "sensitive mode",
            "sensitive-mode",
            "sensitivity mode",
            "reminders suppressed",
            "quiet-time",
            "sensitive closure",
        ),
        steps=(
            step(
                "silence_every_automated_channel",
                "Suppress the outbound queue for this record",
                StepKind.ACT,
                (
                    "Switch off every automated message this record could receive -- "
                    "reminders, recalls, renewals, marketing, review requests, chasers, "
                    "anniversaries -- across every queue and every surface at once, and "
                    "where the protocol says permanently, make it permanent rather than "
                    "paused. One booking reminder to a dead person's phone undoes years "
                    "of goodwill in a single message and cannot be taken back, so name "
                    "every queue you suppressed and the ones you could not reach."
                ),
                produces=("suppression_record",),
            ),
            step(
                "draft_the_one_message_a_person_sends",
                "Write the one short message and leave it held",
                StepKind.DRAFT,
                (
                    "Draft one short message in the business's own voice: the "
                    "acknowledgement, the practical next step and the document checklist "
                    "if one is needed, and nothing else -- no offer, no survey, no "
                    "signature block full of promotions. Keep the documentation the "
                    "protocol asks for to the minimum it names. The message waits for a "
                    "named person to read and send from the business's own account, "
                    "because this is the one message a machine must never send unread."
                ),
                produces=("condolence_draft",),
            ),
        ),
        artifacts=(
            artifact(
                "suppression_record",
                "Suppression record",
                (
                    "Every queue and surface suppressed for this record, whether the "
                    "suppression is permanent, the time it took effect and any queue that "
                    "could not be reached."
                ),
                "log",
            ),
            artifact(
                "condolence_draft",
                "Held sensitive message",
                (
                    "The one short message in the business's voice with the practical "
                    "next step and any document checklist, held for a named person to "
                    "read and send."
                ),
                "document",
            ),
        ),
        tools=("outbound_suppressor", "record_freeze", "message_drafter"),
        config_keys=(
            ConfigKey(
                key="sensitive_mode_rules",
                description=(
                    "What sensitive mode switches off in this vertical, what it "
                    "freezes, what stays permanently off and what may release it."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="estate_document_checklist",
                description=(
                    "The documents an estate, executor or authorised representative "
                    "must produce in this market before anything is released."
                ),
                required=True,
            ),
        ),
        kpis=(
            "automated messages that reached a suppressed record",
            "sensitive records closed with the checklist complete",
            "sensitive messages sent by a person rather than by the unit",
        ),
        channels=("email",),
    ),
    Profile(
        name="decision_brief",
        summary=(
            "The facts, the options and what each one costs assembled onto one "
            "page for the person whose authority or judgement the decision "
            "needs, with the recommendation left blank."
        ),
        match=(
            "options pack",
            "decision pack",
            "executive brief",
            "exposure assessment",
            "options computed",
            "remediation",
            "suitability",
            "routed to the adviser",
            "for compliance",
            "authorization matrix",
            "authorization captured",
            "approver",
            "for consultant",
            "to the consultant",
        ),
        steps=(
            step(
                "assemble_the_facts_and_the_options",
                "Set out every option with its cost and its deadline",
                StepKind.DRAFT,
                (
                    "Write what happened, what is at stake and what the record already "
                    "holds, then each course open to the business with what it costs, "
                    "what it gives up, what it forecloses and the date after which it is "
                    "no longer available. Price every figure from the published price "
                    "book or from a quote already issued. Leave the recommendation field "
                    "empty: the judgement being asked for is exactly the thing the reader "
                    "is qualified for and you are not, and a brief that argues for one "
                    "option has stopped being a brief."
                ),
                produces=("options_brief",),
            ),
            step(
                "put_it_in_front_of_the_authority_holder",
                "Route it to the role the matrix names, with the deadline on it",
                StepKind.NOTIFY,
                (
                    "Send it to the role the authority matrix names for this class and "
                    "this value -- the adviser, the fee earner, the consultant, the "
                    "compliance officer, the director -- with the deadline on the face of "
                    "it and the consequence of missing it stated. Where the window passes "
                    "without an answer, move to the fallback the matrix names rather than "
                    "waiting, and record both the wait and the move."
                ),
                produces=("authority_routing_record",),
            ),
        ),
        artifacts=(
            artifact(
                "options_brief",
                "Options brief",
                (
                    "One page: what happened, what is at stake, each option with its "
                    "cost, trade-off and expiry, the price-book reference behind every "
                    "figure and an empty recommendation field."
                ),
                "document",
            ),
            artifact(
                "authority_routing_record",
                "Authority routing record",
                (
                    "The role the brief went to under which matrix rule, the deadline "
                    "shown, the time sent, the answer received and every fallback used."
                ),
            ),
        ),
        tools=("authority_matrix", "options_modeller", "brief_composer"),
        config_keys=(
            ConfigKey(
                key="authority_matrix",
                description=(
                    "Which role decides which class of question at which value, with "
                    "the fallback when the window passes unanswered."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="option_sources",
                description=(
                    "Where each kind of option is computed from in this vertical: "
                    "contract terms, scheme rules, published remedies, intake calendars."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "briefs answered inside the deadline shown on them",
            "options priced from the published price book",
            "briefs carrying a recommendation nobody asked the unit for",
        ),
    ),
    Profile(
        name="trace_and_sweep",
        summary=(
            "Every affected unit and every affected person found from the "
            "records, held or contacted, with the list complete rather than "
            "representative."
        ),
        match=(
            "recall",
            "quarantine",
            "batch",
            "trace",
            "affected stock",
            "affected-unit",
            "affected results",
            "affected items",
            "provenance",
            "contamination",
            "excursion",
            "counterfeit",
            "disposition",
            "recollection",
            "cold-chain",
            "sweep",
        ),
        steps=(
            step(
                "trace_the_population_both_ways",
                "Trace backwards to the inputs and forwards to every destination",
                StepKind.ASSESS,
                (
                    "From the affected lot, batch, sample, shipment or run, trace "
                    "backwards to everything that went into it and forwards to every "
                    "place it went -- every unit, every order, every patient, every "
                    "customer, every onward consignment. Name the systems you searched "
                    "and the ones you could not, because the danger in this work is a "
                    "trace that looks complete: an unsearchable channel left unnamed "
                    "reads as an empty result and somebody downstream is missed."
                ),
                produces=("trace_matrix", "affected_party_list"),
            ),
            step(
                "hold_it_and_work_the_list",
                "Quarantine what is in reach and contact everyone who is not",
                StepKind.ACT,
                (
                    "Physically or systemically hold everything still within reach and "
                    "mark it so it cannot be picked, shipped, served or released by "
                    "somebody who has not heard, then contact every identified party on "
                    "the protocol's wording through the business's own channels and track "
                    "each contact to a response rather than to a send. Speed is the whole "
                    "point of the trace: what it is worth is decided in hours, and the "
                    "disposition of the held stock stays with the human who owns it."
                ),
                produces=("quarantine_record",),
            ),
        ),
        artifacts=(
            artifact(
                "trace_matrix",
                "Two-way trace matrix",
                (
                    "Every input into the affected lot and every destination out of it, "
                    "with the systems searched, the systems that could not be searched "
                    "and the gap that leaves."
                ),
                "report",
            ),
            artifact(
                "affected_party_list",
                "Affected-party list",
                (
                    "Every identified holder, purchaser, patient or consignee with what "
                    "they hold, how they were contacted, when, and whether they have "
                    "responded."
                ),
            ),
            artifact(
                "quarantine_record",
                "Quarantine record",
                (
                    "What was held, where, when, how it is marked against release, and "
                    "the disposition question left open for the named human."
                ),
                "log",
            ),
        ),
        tools=("batch_tracer", "record_search", "contact_sweeper"),
        config_keys=(
            ConfigKey(
                key="traceability_records",
                description=(
                    "The systems that hold lot, batch, serial and consignment history, "
                    "how far back each reaches and which channels cannot be traced."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="recall_protocol",
                description=(
                    "The trace depth, contact wording, response window and holding "
                    "rules for a recall or withdrawal in this vertical."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "affected units accounted for against units produced or sold",
            "affected parties contacted inside the protocol window",
            "traces completed in hours rather than days",
        ),
        channels=("messaging", "email"),
    ),
    Profile(
        name="custody_and_access",
        summary=(
            "Who held what, what it could reach and who has it now: the chain "
            "reconstructed, the identity tested before anything moves, and the "
            "gaps named."
        ),
        match=(
            "custody",
            "access revoked",
            "access audit",
            "re-code",
            "locksmith",
            "credential",
            "identity verification",
            "identity protocol",
            "key-safe",
            "secure-release",
            "verification challenge",
            "re-map",
            "remap",
            "re-issue",
            "offboarding",
        ),
        steps=(
            step(
                "reconstruct_what_it_could_reach",
                "List every door, system and record the credential touched",
                StepKind.ASSESS,
                (
                    "Work out everything the key, code, card, account or person could "
                    "reach and when -- doors, safes, systems, mailboxes, shared logins, "
                    "customer records, payment rails, third-party portals -- and mark "
                    "each as revoked, re-coded, still open or unknown. The shared login "
                    "nobody remembered and the third-party portal nobody owns are what "
                    "make this list worth building, so an unknown is recorded as unknown "
                    "rather than assumed closed."
                ),
                produces=("access_reconstruction",),
            ),
            step(
                "test_the_identity_before_the_handover",
                "Run the identity test, and refuse the handover if it fails",
                StepKind.ACT,
                (
                    "Before anything is released, re-issued or handed over, run the "
                    "identity test the protocol names -- the photograph, the password, "
                    "the document, the counter-signature, the named person on the record "
                    "-- and log which test was used, who ran it and what it returned. A "
                    "verbal assurance is not a test, however convincing the caller is, "
                    "and pressure is the ordinary condition of every attempt that "
                    "matters. Where the test fails, the handover does not happen and the "
                    "attempt is routed."
                ),
                produces=("custody_chain_record",),
            ),
        ),
        artifacts=(
            artifact(
                "access_reconstruction",
                "Access reconstruction",
                (
                    "Every door, system, account and record the credential or person "
                    "could reach, with dates, and each marked revoked, re-coded, open or "
                    "unknown."
                ),
                "report",
            ),
            artifact(
                "custody_chain_record",
                "Custody chain record",
                (
                    "Each handover with who held the item or the person before and "
                    "after, the identity test run, who ran it, the time, and any gap in "
                    "the chain named as a gap."
                ),
            ),
        ),
        tools=("access_directory", "identity_challenge", "custody_ledger"),
        config_keys=(
            ConfigKey(
                key="identity_verification_rules",
                description=(
                    "The test each kind of handover requires in this vertical, what "
                    "counts as a pass, and what may never be accepted as proof."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="access_inventory",
                description=(
                    "Everything a credential or role can reach in this business, "
                    "including shared logins and third-party portals, with its owner."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "handovers carrying a recorded identity test",
            "credentials revoked or re-coded inside the protocol window",
            "gaps left unnamed in a custody chain",
        ),
    ),
    Profile(
        name="contact_cascade",
        summary=(
            "A named list worked in order until somebody acknowledges, every "
            "attempt timed, and the threshold contact raised when the list runs "
            "out rather than the case going quiet."
        ),
        match=(
            "keyholder cascade",
            "contact cascade",
            "escalation chain",
            "escalation ladder",
            "notification chain",
            "notification cascade",
            "template cascade",
            "vendor cascade",
            "in listed order",
            "contacts in order",
            "called in order",
            "contacted in order",
            "acknowledgement tracking",
            "until acknowledged",
            "on-call",
            "paged",
            "check-in",
        ),
        steps=(
            step(
                "work_the_chain_in_order",
                "Work each name on its route, at the stated interval",
                StepKind.ACT,
                (
                    "Contact each name in the order the chain sets, on the route it sets, "
                    "and move to the next only when the stated interval has passed with "
                    "no acknowledgement -- not sooner because it feels urgent and not "
                    "later because the last attempt is still ringing. Log every attempt "
                    "with its time, route, duration and result, including the ones that "
                    "went nowhere. A delivery receipt is not an acknowledgement: the "
                    "chain advances on a person answering and on nothing else."
                ),
                produces=("cascade_log",),
            ),
            step(
                "raise_it_when_the_list_runs_out",
                "Escalate past the last name rather than stopping",
                StepKind.GATE,
                (
                    "When the chain is exhausted, raise the threshold contact the protocol "
                    "names -- the out-of-hours contact, the duty manager, the designated "
                    "authority -- at the point it names and not one attempt later, and "
                    "keep the case open until a person has acknowledged it in writing. An "
                    "exhausted chain with nobody on the end of it is the failure this "
                    "profile exists to prevent, and it is never treated as an outcome."
                ),
                produces=("acknowledgement_record",),
            ),
        ),
        artifacts=(
            artifact(
                "cascade_log",
                "Cascade log",
                (
                    "Every attempt in order with the name, route, time, duration and "
                    "result, and the interval waited before each move down the chain."
                ),
                "log",
            ),
            artifact(
                "acknowledgement_record",
                "Acknowledgement record",
                (
                    "Who finally acknowledged, when, by what means, what they were told, "
                    "and every threshold contact raised on the way there."
                ),
            ),
        ),
        tools=("contact_chain", "dialler", "acknowledgement_tracker"),
        config_keys=(
            ConfigKey(
                key="cascade_order",
                description=(
                    "The named contacts for this event class in order, their routes, "
                    "the threshold contact and the point the chain leaves the business."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="attempt_intervals",
                description=(
                    "How long to wait between attempts and before the threshold "
                    "contact for each event class in this vertical."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "chains ending in a recorded human acknowledgement",
            "attempts made at the configured interval",
            "chains that ran out with nobody reached",
        ),
        channels=("voice", "messaging"),
    ),
    Profile(
        name="holding_comms",
        summary=(
            "One approved line held across every channel while monitoring is "
            "intensified, the schedule is paused and every word waits on the "
            "person who owns the response."
        ),
        match=(
            "holding statement",
            "holding",
            "approved lines",
            "approved-lines",
            "response options",
            "one voice",
            "one-voice",
            "monitoring",
            "pile-on",
            "controversy",
            "rumour",
            "status page",
            "status comms",
            "media inquiry",
            "editor",
            "nothing sent",
            "posting paused",
            "public response",
            "comms mode",
            "correction notice",
            "retraction",
            "restricted mode",
            "publication rules",
            "syndication",
        ),
        steps=(
            step(
                "hold_one_line_across_every_channel",
                "Write one line and give it to everyone at once",
                StepKind.DRAFT,
                (
                    "Draft the holding line and the response options with their "
                    "consequences beside them, then brief every channel and every member "
                    "of staff with the same wording at the same moment, saying plainly "
                    "what may be said and what may not. Two versions of the same answer "
                    "is the story; one line that says little is survivable and often "
                    "correct. Nothing here goes out until the person who owns the "
                    "response has chosen the words."
                ),
                produces=("one_voice_brief", "response_options"),
            ),
            step(
                "pause_the_schedule_and_watch",
                "Pause what was queued and keep the timeline",
                StepKind.ACT,
                (
                    "Pause the scheduled content, the automated replies and the campaigns "
                    "for the window, because a cheerful promotion landing mid-incident is "
                    "the screenshot that outlives the incident. Raise the monitoring "
                    "cadence on the named surfaces and keep a timestamped timeline of who "
                    "said what and where, so the response is built on the record rather "
                    "than on the loudest thread. Restrictions the market imposes on this "
                    "window are enforced across every surface without exception."
                ),
                produces=("comms_timeline",),
            ),
        ),
        artifacts=(
            artifact(
                "one_voice_brief",
                "One-voice brief",
                (
                    "The single approved wording issued to staff and every channel, with "
                    "what may be said, what may not, and who the questions go to."
                ),
                "document",
            ),
            artifact(
                "response_options",
                "Response options",
                (
                    "Each available response with its consequence, its reach and its "
                    "expiry, held for the person who owns the decision."
                ),
                "document",
            ),
            artifact(
                "comms_timeline",
                "Comms timeline",
                (
                    "A timestamped record of what was said where, by whom, on which "
                    "surface, with the paused schedule and the monitoring cadence run."
                ),
                "log",
            ),
        ),
        tools=("channel_monitor", "scheduler_pause", "statement_drafter"),
        config_keys=(
            ConfigKey(
                key="approved_lines",
                description=(
                    "The pre-agreed wording for each class of event, who may add to "
                    "it, and the named spokesperson every question goes to."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="monitored_surfaces",
                description=(
                    "The channels, review surfaces and communities watched during a "
                    "comms window in this market, with the raised cadence for each."
                ),
                required=True,
            ),
        ),
        kpis=(
            "channels carrying the same approved line",
            "statements that left the business without the reserved decision",
            "scheduled content that went out during a paused window",
        ),
        channels=("social", "email", "messaging"),
    ),
    Profile(
        name="statutory_clock",
        summary=(
            "An instrument arrives with a date attached: it is classified, every "
            "deadline it carries is computed from its own trigger and docketed, "
            "and the window is protected."
        ),
        match=(
            "statutory",
            "docket",
            "deadline",
            "clock",
            "litigation hold",
            "regulatory inquiry",
            "appeal",
            "cure-period",
            "claim-window",
            "regulated complaint",
            "complaints procedure",
            "regulatory-format",
            "extension-of-time",
            "jurisdiction",
            "preservation",
        ),
        steps=(
            step(
                "extract_every_deadline_it_carries",
                "Classify it and compute the dates, including the unstated ones",
                StepKind.ASSESS,
                (
                    "Read what arrived -- the order, the notice, the letter, the request, "
                    "the complaint, the refusal -- classify it against the register, find "
                    "the date each period runs from, and compute every deadline it carries "
                    "under the rules of the jurisdiction that governs it, including the "
                    "ones the document never mentions. The unstated deadline is the one "
                    "that ends the claim: an acknowledgement due in days, a preservation "
                    "duty starting on receipt, a right that lapses if nothing is filed."
                ),
                produces=("instrument_classification",),
            ),
            step(
                "docket_it_and_protect_the_window",
                "Enter it, name its owner and warn early",
                StepKind.ACT,
                (
                    "Enter every deadline in the docket with the date it runs from, the "
                    "instrument that carries it, the named owner and the warning points "
                    "before it expires, and put in place whatever the instrument requires "
                    "held -- the preservation notice, the paused workflow, the frozen "
                    "record -- with the acknowledgements tracked. Warn at each configured "
                    "point rather than on the day: a window met with an hour left was "
                    "still nearly missed, and the substance belongs to a person who needs "
                    "the time you protected."
                ),
                produces=("deadline_docket",),
            ),
        ),
        artifacts=(
            artifact(
                "instrument_classification",
                "Instrument classification",
                (
                    "What arrived, its class, the date each period runs from, every "
                    "deadline computed under the governing rules and the ones the "
                    "document itself never stated."
                ),
                "report",
            ),
            artifact(
                "deadline_docket",
                "Deadline docket",
                (
                    "Each deadline with its trigger date, source instrument, named "
                    "owner, warning points, the holds put in place and the "
                    "acknowledgements received."
                ),
            ),
        ),
        tools=("instrument_classifier", "deadline_calculator", "docket"),
        config_keys=(
            ConfigKey(
                key="deadline_rules",
                description=(
                    "How each period is computed in the governing jurisdiction: what "
                    "it runs from, working or calendar days, and how it is served."
                ),
                required=True,
            ),
            ConfigKey(
                key="docket_owners",
                description=(
                    "Who owns each class of deadline, the warning points before it "
                    "expires and the escalation when a warning goes unanswered."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "deadlines computed from the instrument's own trigger date",
            "windows met with the response ready before the warning point",
            "deadlines discovered only after they had run",
        ),
    ),
    Profile(
        name="operating_mode_switch",
        summary=(
            "The business flips into a declared temporary mode -- away, offline, "
            "surge, lockdown, closed -- and every rule of that mode is enforced "
            "at every surface until it is switched back."
        ),
        match=(
            "away mode",
            "offline",
            "surge mode",
            "lockdown",
            "outage",
            "closure",
            "runbook",
            "fallback",
            "backup",
            "back-up",
            "load-shed",
            "double-books",
            "delegation rules",
            "digest-only",
            "catch-up sync",
            "mass rebooking",
        ),
        steps=(
            step(
                "switch_the_mode_on_everywhere",
                "Activate the mode's rules at every surface at once",
                StepKind.ACT,
                (
                    "Turn on the mode's whole rule set in one move -- what queues, what is "
                    "delegated, what is cached locally, what is triaged first, what is "
                    "restricted, which hours are shown -- and push it to every surface the "
                    "customer can see, not merely the one that raised the event. A site "
                    "that says open while the door is locked, or a booking page still "
                    "taking work the business cannot do, costs more than the disruption "
                    "did. Record who declared the mode and when it started."
                ),
                produces=("mode_activation_record",),
            ),
            step(
                "hold_the_mode_then_catch_up",
                "Keep the position honest, then reconcile on exit",
                StepKind.ACT,
                (
                    "Keep the rules enforced for as long as the trigger lasts and keep one "
                    "honest statement of the position in front of customers and staff: an "
                    "unwelcome accurate wait beats an optimistic one that slips twice. "
                    "Queue everything the mode defers rather than dropping it. On exit, "
                    "run the catch-up -- sync what was cached, work the queue in the order "
                    "it arrived, and reconcile every deferred item to a landing -- because "
                    "the losses in this shape of work happen after the event, not during "
                    "it."
                ),
                produces=("queued_backlog", "catch_up_log"),
            ),
        ),
        artifacts=(
            artifact(
                "mode_activation_record",
                "Mode activation record",
                (
                    "Which mode was declared, by whom, when, the rule set it applied and "
                    "every surface it was pushed to with the confirmation from each."
                ),
            ),
            artifact(
                "queued_backlog",
                "Deferred queue",
                (
                    "Everything the mode deferred, in arrival order, with what each item "
                    "needs and who was told it was waiting."
                ),
            ),
            artifact(
                "catch_up_log",
                "Catch-up log",
                (
                    "The exit reconciliation: what was cached and synced, what was worked "
                    "off the queue, what landed and anything that could not be recovered."
                ),
                "log",
            ),
        ),
        tools=("mode_switch", "surface_updater", "queue_store"),
        config_keys=(
            ConfigKey(
                key="operating_modes",
                description=(
                    "The temporary modes this vertical runs, the rule set each one "
                    "applies and the surfaces each must reach."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="mode_thresholds",
                description=(
                    "What triggers each mode, who may declare and end it, and the "
                    "emergency thresholds that break through it."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "surfaces carrying the mode's rules inside the switch window",
            "deferred items reconciled to a landing after the mode ended",
            "customer-facing surfaces left stating the wrong position",
        ),
        channels=("owner_dashboard", "messaging"),
    ),
    Profile(
        name="service_recovery",
        summary=(
            "The published rule applied exactly as written, the customer made "
            "whole inside it, the capacity recovered, and any departure from the "
            "rule drafted rather than taken."
        ),
        match=(
            "no-show",
            "fee",
            "waiv",
            "refund",
            "compensation",
            "rebook",
            "backfill",
            "slot refilled",
            "guarantee",
            "credit issued",
            "gesture",
            "honour",
            "walk protocol",
            "recovery protocol",
            "ban-list",
        ),
        steps=(
            step(
                "apply_the_published_rule",
                "Apply the rule as written and cite the clause",
                StepKind.DECIDE,
                (
                    "Find the rule that actually governs this case -- the notice period, "
                    "the fee band, the guarantee term, the refund window, the delta "
                    "threshold, the gesture matrix -- and apply it exactly as written, "
                    "recording the clause, the inputs and the figure it produced. Every "
                    "money figure comes from the published terms or a quote already "
                    "issued. Where the fair answer sits outside the rule, that is a "
                    "reserved decision: draft it with the reasoning and the cost, and "
                    "leave it for the owner to take."
                ),
                produces=("policy_application_record",),
            ),
            step(
                "make_the_recovery_move",
                "Put the offer out and recover the capacity",
                StepKind.ACT,
                (
                    "Make the move the policy allows in the same breath as the bad news "
                    "-- the rebooking, the replacement, the comparable property, the "
                    "credit, the alternative candidate, the backup venue -- because a "
                    "customer offered a way forward in the first message complains far "
                    "less than one told only what went wrong. Then recover the capacity: "
                    "work the waitlist, the standby list or the silver-medallist list so "
                    "the slot, the seat or the placement is not simply lost."
                ),
                produces=("recovery_offer",),
            ),
        ),
        artifacts=(
            artifact(
                "policy_application_record",
                "Policy application record",
                (
                    "The clause applied, the inputs it was applied to, the figure it "
                    "produced, its price-book reference, and any departure drafted for "
                    "the owner with its reasoning."
                ),
            ),
            artifact(
                "recovery_offer",
                "Recovery offer and capacity move",
                (
                    "What was offered, on what terms, when it went out, the customer's "
                    "answer, and how the released capacity was refilled."
                ),
                "document",
            ),
        ),
        tools=("policy_engine", "price_book", "waitlist"),
        config_keys=(
            ConfigKey(
                key="recovery_policy",
                description=(
                    "The rules that govern fees, waivers, refunds, gestures and "
                    "guarantees for this business, with the clause behind each."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="waiver_bounds",
                description=(
                    "How far the unit may go inside the policy without asking, and "
                    "the point past which every case is drafted for the owner."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "cases decided by a cited clause rather than by judgement",
            "released slots and bookings refilled the same day",
            "departures from the policy taken without the owner",
        ),
        channels=("messaging", "email"),
    ),
    # Fallback.  Deliberately the family's canonical shape rather than a dumping
    # ground: a named event with a written protocol, run step by step, logged,
    # and stopped where the protocol stops.  The units that land here -- a pest
    # sighting, a lien found on a title, a patient who left against advice, a
    # conflict of instructions, an airline schedule change -- are exactly that
    # and nothing more, and each of them is a checklist whose value is that it
    # was completed rather than remembered.
    Profile(
        name="event_protocol",
        summary=(
            "A named event with a written protocol: the steps run in the order "
            "written, each one logged, blocked steps recorded as blocked, and "
            "the reserved part assembled and handed over."
        ),
        match=(),
        steps=(
            step(
                "work_the_written_steps",
                "Run the checklist in its order and tick it as you go",
                StepKind.ACT,
                (
                    "Work the protocol's steps in the order it sets them, marking each "
                    "with its time, its actor and what it returned. Where a step cannot be "
                    "completed -- the contractor will not come, the counterparty will not "
                    "answer, the record is not there -- write down what blocked it and "
                    "carry it forward as open rather than moving past it silently. A "
                    "checklist with an unexplained gap is worth less than no checklist, "
                    "because it says the step happened."
                ),
                produces=("protocol_checklist",),
            ),
            step(
                "hand_over_what_the_protocol_reserves",
                "Assemble the reserved part and stop there",
                StepKind.GATE,
                (
                    "The protocol names the part that belongs to a person -- the "
                    "judgement, the wording, the money, the commitment, the call to the "
                    "authority. Assemble it into one pack with the facts, the timings, "
                    "what has already run and what is still open, hand it to the named "
                    "role and stop. Everything up to that line is yours to run; the line "
                    "itself is not moved because the person is slow to answer."
                ),
                produces=("handover_pack",),
            ),
        ),
        artifacts=(
            artifact(
                "protocol_checklist",
                "Protocol checklist",
                (
                    "Every step of the written protocol with its time, actor and result, "
                    "and each blocked step with what blocked it and its open state."
                ),
            ),
            artifact(
                "handover_pack",
                "Handover pack",
                (
                    "The facts, the timings, the steps already run and the questions "
                    "still open, addressed to the role the protocol reserves them for."
                ),
                "bundle",
            ),
        ),
        tools=("protocol_lookup", "checklist_runner", "handover_composer"),
        config_keys=(
            ConfigKey(
                key="protocol_steps",
                description=(
                    "The written steps for this event class in this vertical, in "
                    "order, with what each one requires before it can be marked done."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="blocked_step_handling",
                description=(
                    "What happens when a protocol step cannot be completed: who is "
                    "told, how long it stays open and what may proceed meanwhile."
                ),
                resolved_by="owner",
            ),
        ),
        kpis=(
            "protocol steps completed in the order written",
            "blocked steps recorded with what blocked them",
            "protocols closed with a reserved question still unanswered",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class ProtocolIncidentPlaybooksEngine(Engine):
    """Carries every unit whose work is triggered by one event and time-boxed.

    The engine holds one sequence -- recognise the event, start its clocks,
    capture the facts before they decay, size it against the matrix, run the
    fixed steps in order, draft what only a person may release, escalate to the
    named human and stop -- and fourteen profiles that say what kind of event is
    being run.  Nothing in the code knows whether it is holding an evacuation
    script, a garnishment order or a batch recall; the recognition criteria, the
    steps, the clocks, the chains and the reserved decisions all arrive as
    configuration.
    """

    id: ClassVar[str] = "MF14"
    family: ClassVar[str] = "Protocol & incident playbooks"
    what_it_does: ClassVar[str] = (
        "Event-triggered, time-boxed, safety-gated playbooks: statutory clocks, "
        "escalation chains, hard interlocks. Escalation IS the product - the "
        "agent recognizes, executes steps, and stops at the human gate"
    )
    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.RUN_PROTOCOL,
        Capability.CLOCK,
        Capability.CASE_STATE,
        Capability.COLLECT_DOCUMENTS,
        Capability.QUEUE_TRIAGE,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "protocol_register",
        "clock_docket",
        "evidence_vault",
        "escalation_router",
        "notification_composer",
        "case_recorder",
        "suppression_switch",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "messaging",
        "email",
        "voice",
        "owner_dashboard",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "events recognised on the first contact that carried the signal",
        "clocks started from the moment of recognition rather than from first work",
        "protocol steps executed in order with none skipped",
        "escalations acknowledged by a named person inside the window",
        "reserved decisions taken by a person rather than by the unit",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    state_object: ClassVar[str] = "incident_case"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        return _PROFILES

    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Recognise, clock, capture, size, execute, draft, hold, escalate.

        Three placements carry most of the weight and none of them is the
        obvious one.  The clocks start second, before anything is investigated,
        because every deadline in this family runs from the moment of
        recognition and an hour spent understanding the event is an hour
        already gone from the window.  Capture comes third, ahead of the
        assessment, because containment, repair, tidying and reassurance all
        destroy the record they are responding to -- the scene is tidied, the
        session is rotated, the witnesses talk to each other -- and there is no
        second attempt at any of it.  And the gate sits before the escalation
        rather than after it, because the two are not the same act: the gate
        marks the boundary and freezes everything behind it, while the
        escalation is the work of getting a named person to pick it up and say
        so.  That last step is where this family's product actually is.  A run
        whose steps all completed and whose named human never acknowledged the
        pack has failed, however completely every box is ticked.
        """
        return (
            step(
                "recognise_the_event",
                "Recognise it as the event, and stamp the time",
                StepKind.OBSERVE,
                (
                    "Test what arrived against the recognition criteria in the protocol "
                    "register and name the protocol it matches, then stamp the moment of "
                    "recognition and the signal that produced it. The commonest failure "
                    "in this whole family is a protocol event handled as an ordinary "
                    "message: by the time somebody notices, the window has gone and the "
                    "record has not been kept. Recognition is a test against a written "
                    "list, never a judgement about how serious it looks, and where the "
                    "signal sits close to the criteria the protocol runs and the "
                    "near-match is recorded."
                ),
                produces=("recognition_record",),
            ),
            step(
                "start_the_clocks",
                "Start every clock the event carries, from recognition",
                StepKind.ACT,
                (
                    "Enter every deadline this class of event carries -- statutory, "
                    "contractual, insurer, platform, internal -- computed from the "
                    "recognition timestamp rather than from the moment work began, each "
                    "with its owner, its expiry and its warning points. Do this before "
                    "the facts are gathered and before anybody is told, because the clock "
                    "does not wait for the investigation and a deadline discovered late "
                    "is a deadline already partly spent. A clock with no named owner is "
                    "not started."
                ),
                produces=("clock_docket",),
            ),
            step(
                "capture_the_facts",
                "Capture the record before anything alters it",
                StepKind.GATHER,
                (
                    "Take the account, the media, the readings, the logs, the times, the "
                    "people present and the state of things as they stand right now, in "
                    "the order the evidence standard sets, and store each with its source "
                    "and its own timestamp. Capture precedes containment, repair, "
                    "tidying, apology and notification, because every one of those alters "
                    "or destroys what you are trying to record. Write what was observed "
                    "and by whom; cause, fault and meaning are somebody else's to supply."
                ),
                produces=("incident_record",),
            ),
            step(
                "size_it_against_the_matrix",
                "Place it in the band the matrix names",
                StepKind.ASSESS,
                (
                    "Set what you captured against the severity matrix for this event "
                    "class and record the band it falls in, the thresholds it crossed, "
                    "which notifications that band makes mandatory rather than optional, "
                    "and who must therefore be told and by when. The band comes from the "
                    "matrix and from the facts, never from tone or from how upset anybody "
                    "is; where the facts straddle two bands, the higher one is taken and "
                    "the straddle is noted for the human."
                ),
                produces=("severity_assessment",),
            ),
            step(
                "execute_the_fixed_steps",
                "Run the protocol's steps in its order, none skipped",
                StepKind.ACT,
                (
                    "Work the steps the register sets for this protocol in the order it "
                    "sets them, logging each with its time, its actor and what it "
                    "returned, and switch off the outbound queues the suppression rules "
                    "name for an affected record. The order is the protection: it is what "
                    "keeps the interlock ahead of the booking and the evidence ahead of "
                    "the repair. Where a step cannot be run, record what blocked it and "
                    "carry it forward as open rather than passing over it, and go no "
                    "further than the point at which the register says the protocol ends."
                ),
                produces=("protocol_execution_log",),
            ),
            step(
                "draft_what_only_a_person_may_release",
                "Prepare every reserved output completely, and hold it",
                StepKind.DRAFT,
                (
                    "Write the notifications, the statements, the acknowledgements, the "
                    "regulator-format files and the option sets in full, so that the "
                    "person deciding has to supply a decision and not a document. Then "
                    "hold every one of them: nothing that admits, apologises for, "
                    "concedes, commits or notifies leaves this unit on its own authority, "
                    "however obviously right it looks and however tight the window is. "
                    "Name the releaser against each draft and show the deadline it is "
                    "waiting against."
                ),
                produces=("held_drafts",),
            ),
            step(
                "hold_the_reserved_decision",
                "Mark the boundary and let nothing past it",
                StepKind.GATE,
                (
                    "Name what is now waiting on a person and stop there: whether to "
                    "notify, whether to admit, what the statement says, whether the waiver "
                    "stands, whether the machine restarts, what the clinician does next. "
                    "Each of these is the reason the gate exists, and none of them becomes "
                    "yours because the window is closing or nobody has answered yet. "
                    "Nothing behind the gate proceeds while it is open, and the boundary "
                    "does not move -- what moves is the urgency with which you push it at "
                    "somebody."
                ),
            ),
            step(
                "escalate_to_the_named_human",
                "Put it in a person's hands and confirm they have it",
                StepKind.NOTIFY,
                (
                    "Deliver the pack to the role the escalation chain names, on the route "
                    "it names, inside the window it sets, and treat the escalation as "
                    "incomplete until a person has acknowledged it -- a delivered message "
                    "is not an acknowledgement. Where the window passes, re-escalate on "
                    "the configured fallback rather than leaving it to age, and keep the "
                    "case open with its clocks visible on it. Anything that reaches a "
                    "customer in the meantime sends from the business's own connected "
                    "account, in the business's voice, and says only what the approved "
                    "wording allows."
                ),
                produces=("escalation_record",),
            ),
        )

    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "recognition_record",
                "Recognition record",
                (
                    "The signal that arrived, the criteria it was tested against, the "
                    "protocol it matched, any near-match noted, and the timestamp every "
                    "clock on this case is measured from."
                ),
            ),
            artifact(
                "clock_docket",
                "Clock docket",
                (
                    "Every deadline this event carries with its source, the time it runs "
                    "from, its expiry, its warning points and the role that owns it."
                ),
            ),
            artifact(
                "incident_record",
                "Incident record",
                (
                    "What was observed and by whom, with media, readings, logs, times "
                    "and people present, each carrying its own source and timestamp and "
                    "no statement of cause or fault."
                ),
                "bundle",
            ),
            artifact(
                "severity_assessment",
                "Severity assessment",
                (
                    "The band the event falls in, the thresholds crossed, the "
                    "notifications that band makes mandatory, and any straddle between "
                    "bands noted for the human."
                ),
                "report",
            ),
            artifact(
                "protocol_execution_log",
                "Protocol execution log",
                (
                    "Each protocol step in the order it was run with its time, actor and "
                    "result, the queues suppressed, and every blocked step with what "
                    "blocked it."
                ),
                "log",
            ),
            artifact(
                "held_drafts",
                "Held drafts",
                (
                    "Every reserved output written in full -- notifications, statements, "
                    "acknowledgements, regulator-format files, option sets -- each in a "
                    "held state with its named releaser and the deadline it waits "
                    "against."
                ),
                "document",
            ),
            artifact(
                "escalation_record",
                "Escalation record",
                (
                    "Who the pack went to, on what route, at what time, whether a person "
                    "acknowledged it, and every re-escalation raised when nobody did."
                ),
            ),
        )

    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        where = self._configuration_line(record)
        return (
            "HOW YOU WORK. You are triggered by one event, and the first thing you do "
            "is recognise it as that event: test what arrived against the written "
            "criteria in the protocol register, name the protocol, and stamp the time "
            "of recognition -- every clock on this case runs from that stamp and not "
            "from the moment you got to the work. Start the clocks before you "
            "investigate anything, because the window does not wait for you to "
            "understand what happened. Then capture the record before anything alters "
            "it: containment, repair, tidying, apology and even a kind word change the "
            "scene, the system or the account you are trying to preserve, and there is "
            "no second attempt at any of it. Run the protocol's steps in the order the "
            "register sets them, log every one with its time and actor, and where a "
            "step cannot be run write down what blocked it instead of passing over it "
            "-- the order is the protection, and a checklist with a silent gap is worse "
            "than none. Prepare every reserved output in full and hold it, so the "
            "person deciding supplies a decision rather than a document; nothing that "
            "admits, concedes, commits or notifies leaves you on your own authority, "
            "however obviously right it looks and however little time is left. "
            "Escalation is the deliverable here, not the fallback: the run is not "
            "finished when the steps are ticked, it is finished when a named person has "
            "acknowledged the pack, and an unacknowledged escalation re-escalates "
            "rather than ageing on a queue. And you never resolve the situation "
            "itself, never close it out on your own judgement and never move the gate "
            "because nobody has answered yet. "
            f"{self._profile_line(profile)} {where}"
        )

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        return (
            Guardrail(
                id="GR-CLOCK-RUNS-FROM-RECOGNITION",
                rule=(
                    "Every deadline is computed from the moment the event was "
                    "recognised, never from the moment work started on it."
                ),
                check=(
                    "recognition_record carries the recognition timestamp and the signal "
                    "behind it, and every entry in clock_docket resolves to a rule in "
                    "statutory_clocks computed from that timestamp with a named owner."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CAPTURE-BEFORE-ALTERATION",
                rule=(
                    "The record is captured before any step that could alter the "
                    "scene, the system, the account or the account of it."
                ),
                check=(
                    "incident_record timestamps precede every containment, repair, "
                    "reset or notification entry in protocol_execution_log, and its "
                    "contents meet evidence_standard for this event class."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-STEPS-IN-ORDER-NONE-SKIPPED",
                rule=(
                    "Protocol steps run in the order written. A step that cannot be "
                    "run is recorded as blocked and carried forward, never skipped."
                ),
                check=(
                    "protocol_execution_log holds one entry per step of the "
                    "protocol_register sequence in that order, and every incomplete step "
                    "names what blocked it and remains open."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-ESCALATION-IS-THE-PRODUCT",
                rule=(
                    "The run is complete when a named person is holding the case, not "
                    "when the steps have been ticked."
                ),
                check=(
                    "escalation_record shows acknowledgement by a role named in "
                    "escalation_chain; an unacknowledged escalation re-escalates on the "
                    "configured fallback and the case stays open."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-DRAFTS-STAY-HELD",
                rule=(
                    "Notifications, statements, admissions and commitments are "
                    "prepared complete and never leave on the unit's authority."
                ),
                check=(
                    "Every item in held_drafts carries a held state and a named "
                    "releaser drawn from reserved_decisions; no send is logged against "
                    "a reserved output before its gate resolves."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-NO-CAUSE-NO-ADMISSION",
                rule=(
                    "The record states what was observed, when and by whom. It never "
                    "states cause, fault, liability or apportionment."
                ),
                check=(
                    "incident_record and every outbound draft are free of causal "
                    "claims, admissions and apportionment; the determination fields are "
                    "left empty for the named human."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-SUPPRESS-WHILE-LIVE",
                rule=(
                    "Automated outbound to an affected record stops while the protocol "
                    "is live, and only a person releases it."
                ),
                check=(
                    "Suppression is applied at recognition to every queue named in "
                    "suppression_rules, protocol_execution_log names each queue "
                    "suppressed, and every release records the person who made it."
                ),
                source="mechanism_family",
            ),
        )

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "The event as it arrived -- message, call, alarm, reading or document "
            "-- carrying its own timestamp",
            "The protocol register entry for this event class: its recognition "
            "criteria, its steps and the point it stops",
            "Clocks already running against this record and the deadlines they carry",
            "The escalation chain in force at this hour, including the out-of-hours position",
            "What the record already holds: prior incidents, protections, consents, "
            "restrictions and open gates",
        )

    # -- internals ----------------------------------------------------------
    def _profile_line(self, profile: Profile) -> str:
        """One sentence naming what kind of protocol this profile is running.

        Kept beside the profiles rather than inside them because it is prose
        about the mission, not configuration a customer can override.
        """
        return _PROFILE_MISSION_LINES.get(
            profile.name, _PROFILE_MISSION_LINES["event_protocol"]
        )

    def _configuration_line(self, record: Mapping[str, Any]) -> str:
        """Say where this unit's protocol, clocks and chain come from.

        A vertical playbook and a universal one differ only in which overlay
        answers the question, which is the config-not-code rule doing its work:
        the same steps run against a nursery's collection cascade and a lab's
        critical-value chain because both arrive as configuration.
        """
        vertical = record.get("vertical") or {}
        domain = record.get("domain") or {}
        if vertical:
            return (
                f"The steps this protocol runs in {vertical['name'].lower()}, what each "
                f"clock is worth there and who sits on the chain all come from the "
                f"vertical overlay and the active country pack -- read both, because a "
                f"deadline you assumed is a deadline you will miss."
            )
        if domain:
            return (
                f"This protocol runs in the {domain['name'].lower()} domain of every "
                f"business on the platform, so the recognition criteria, the clocks and "
                f"the chain all come from whatever overlay and country pack are in front "
                f"of you rather than from anything you know about how this usually goes."
            )
        return (
            "The recognition criteria, the steps, the clocks and the chain all come "
            "from the overlay and the country pack in front of you rather than from "
            "anything you know about how this usually goes."
        )


#: Mission prose per profile.  Each names the event, the artefact that proves the
#: work and the exact point at which the protocol stops and a person takes over.
_PROFILE_MISSION_LINES: dict[str, str] = {
    "safety_interlock": (
        "What you run here is a fixed protocol with no discretion in it: test the "
        "presentation against the written list rather than grading how bad it looks, "
        "run the steps in their order, and hold every commercial step behind the "
        "interlock until the named human has the case -- the hold has no override "
        "inside you, and a request to lift it is logged and routed rather than "
        "actioned."
    ),
    "confidential_disclosure": (
        "What you run here is somebody telling you something hard: take it down in "
        "their own words with no leading question and no impression of your own, send "
        "it to the one designated person on the restricted route and to nobody else, "
        "and then stop entirely -- no follow-up, no second conversation on the "
        "subject, and nothing that reads as though anyone has assessed it."
    ),
    "breach_containment": (
        "What you run here is an exposure: preserve the logs and the system state "
        "before you change anything, compile the scope as fact with its unknowns named "
        "as unknowns, work the containment runbook step by step, and draft every "
        "notification in full -- whether anyone is told, and who, is the reserved "
        "decision this whole exercise exists to inform."
    ),
    "incident_evidence": (
        "What you run here decays within hours: photograph the scene with its time and "
        "place, take each witness one at a time and out of earshot before they compare "
        "accounts, and build the insurer's pack from the record alone -- cause, fault "
        "and apportionment stay blank, because a sympathetic sentence written today is "
        "read as an admission by people who were not there."
    ),
    "sensitive_mode": (
        "What you run here is a silence: switch off every automated message this "
        "record could receive across every queue and surface at once, make it "
        "permanent where the protocol says permanent, and leave one short human "
        "message drafted and held -- this is the one message a machine must never send "
        "unread."
    ),
    "decision_brief": (
        "What you produce here is a page somebody else decides from: the facts, then "
        "each option with what it costs, what it forecloses and when it expires, every "
        "figure priced from the published book, and the recommendation field left "
        "deliberately empty -- the judgement is exactly what the reader is qualified "
        "for and you are not."
    ),
    "trace_and_sweep": (
        "What you run here is a list that has to be complete rather than "
        "representative: trace backwards to every input and forwards to every "
        "destination, name the systems you could not search instead of letting the gap "
        "read as an empty result, hold what is still in reach, and track every contact "
        "to a response rather than to a send."
    ),
    "custody_and_access": (
        "What you run here is a chain: reconstruct everything the key, code, account "
        "or person could reach and mark the unknowns as unknown, then test identity "
        "with the protocol's own test before anything is released or handed over -- a "
        "verbal assurance is not a test, and pressure is the ordinary condition of "
        "every attempt that matters."
    ),
    "contact_cascade": (
        "What you run here is a list of names and a stopwatch: work each in the order "
        "set, on the route set, waiting the stated interval before you move on, log "
        "every attempt including the ones that went nowhere, and treat a delivery "
        "receipt as nothing -- the chain advances on a person answering, and an "
        "exhausted chain raises the threshold contact instead of going quiet."
    ),
    "holding_comms": (
        "What you run here is one voice: draft the holding line and the options with "
        "their consequences, brief every channel and every member of staff with the "
        "same wording at the same moment, pause the scheduled content so nothing "
        "cheerful lands mid-incident, and keep a timestamped timeline -- the words "
        "themselves belong to the person who owns the response."
    ),
    "statutory_clock": (
        "What you run here arrived with a date on it: classify the instrument, find "
        "what each period runs from, compute every deadline the governing rules attach "
        "including the ones the document never mentions, docket each with a named "
        "owner and warning points, and put in place whatever it requires held -- the "
        "substance belongs to a person who needs the time you protected."
    ),
    "service_recovery": (
        "What you run here is a published rule: apply it exactly as written and record "
        "the clause and the figure, price every number from the published book, offer "
        "the way forward in the same breath as the bad news, and recover the capacity "
        "-- a fair answer that sits outside the rule is drafted for the owner rather "
        "than taken by you."
    ),
    "operating_mode_switch": (
        "What you run here is a switch: turn the mode's whole rule set on at every "
        "surface a customer can see rather than only the one that raised the event, "
        "keep one honest statement of the position while it lasts, queue what the mode "
        "defers, and reconcile every deferred item to a landing on the way out -- the "
        "losses in this shape of work happen after the event, not during it."
    ),
    "event_protocol": (
        "What you run here is a written checklist whose value is that it was completed "
        "rather than remembered: work the steps in their order, mark each with its "
        "time and actor, record what blocked anything you could not finish instead of "
        "moving past it, and assemble the part the protocol reserves into one pack for "
        "the named role -- then stop at that line and hold it there."
    ),
}


__all__ = ["ProtocolIncidentPlaybooksEngine"]
