"""MF7 -- watcher / surveillance.

Most of what a business needs to know is never delivered to it.  The competitor
two streets away changes his prices, a regulator changes a rule mid-caseload, a
supplier's terms move, a member quietly stops turning up, a mandate drifts off
its band, a nightly backup stops restoring.  Nothing arrives in an inbox; the
world simply becomes different, and the owner finds out weeks later from a
customer, an invoice or an auditor.  This family is the standing watch on those
sources.  Its product is never the reading -- it is the *change*, with the
evidence that shows it, in front of the person who can still do something about
it.

A watcher is defined by the state it keeps between runs.  Without a stored prior
there is no such thing as change: every reading looks new, everything is either
noise or an alarm, and the recipient learns within a fortnight to stop opening
the digest.  So the plan here is a loop rather than a pipeline -- read the
source, capture what it said at the moment it said it, set that against the
baseline the configuration names, decide against a threshold whether the
difference is material, write the finding, and write the new reading back as the
baseline the next cycle compares against.  Persistence is part of materiality: a
small movement in the same direction for five cycles is the finding, and a spike
that reverted is a log entry.

Two failure modes kill a watch and neither announces itself.  The first is the
blind spot -- a source that stopped answering looks exactly like a source where
nothing happened, so silence is never read as calm and every cycle reports which
sources answered, which did not and what that leaves unwatched.  The second is
evidence that decays.  A competitor's page, a channel rate, a social post, a
portal slot and a supplier's tariff can each change or vanish within the hour,
and the requote, the dispute, the invoice or the statutory clock that follows
rests entirely on what was captured at the time.  Capture therefore precedes
comparison, always.

The third standing rule is where this family stops rather than a caveat on it.
These units watch people as well as numbers -- attendance, vulnerability
indicators, till variances, departures, claims histories -- and the workbook says
the same thing over and over in its own words: observation only, the
determination stays human, the agent adjusts tone only.  So a unit here reports
what moved, when, against what and with what evidence.  Why it moved, what it
means about a person's conduct, competence or intent, and what should be done
about it belong to the human the finding is handed to.  Sources, cadences,
baselines, thresholds and routing all resolve from the vertical overlay and the
active country pack, which is how one engine carries a literature watch, a
rate-parity audit and a scrap-rate trigger without knowing which it is holding.
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

#: Read by every unit of the family.  Between them these six keys are the whole
#: watch: what is looked at, how often, what each reading is measured against,
#: what size of movement is worth a person's attention, who hears about it and
#: how long the proof is kept.  Change them and the same code watches a journal
#: feed, a channel rate table or a scrap counter.
_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="watch_sources",
        description=(
            "Every source this unit reads: what it is, how it is reached, the "
            "credential or grant it is read under, and the field that carries "
            "each reading's own timestamp rather than the time you saw it."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="watch_cadence",
        description=(
            "How often each source is read, how stale a reading may be before it "
            "is refused, and what the unit does when a source does not answer."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="baseline_definition",
        description=(
            "What each watched value is compared against -- the previous reading, "
            "a contracted level, a rule in force, a peer band -- and how far back "
            "the comparison reaches."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="materiality_thresholds",
        description=(
            "The movement at which a difference becomes a finding, per watch, and "
            "the persistence rule that makes a run of small movements material."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="alert_routing",
        description=(
            "Who receives each watch and at what volume: which findings will not "
            "wait for the digest, and the out-of-hours contact for those."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="evidence_retention",
        description=(
            "What must be captured with every observation and how long the "
            "capture is kept, so a finding can still be evidenced when a dispute "
            "or a statutory clock reaches it."
        ),
        required=True,
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

#: The eleven watch shapes actually present in the catalogue, most specific
#: first.  Tokens are read against worker, system agent, trigger, function and
#: expected output, and they are chosen as nouns of the subject matter --
#: "parity", "vexatious", "subrogation", "scrap" -- rather than the verbs every
#: unit in the family shares ("watched", "monitored", "flagged", "alerts").
#: Order carries real weight in four places.  The person-risk tokens must claim
#: welfare, vulnerability and pharmacovigilance signals before any commercial
#: profile sees them.  The abuse tokens must claim "poaching" and "observation
#: only", and the corpus tokens must claim the literature watch, before the
#: market profile's "competitor" reaches either.  And the supply tokens must
#: claim the reorder agents before the threshold profile's "threshold" swallows
#: them.
_PROFILES: tuple[Profile, ...] = (
    Profile(
        name="person_risk_flag",
        summary=(
            "A signal about a person compiled into a dossier and handed to the "
            "licensed or trained human who owns the handling, with the clock "
            "started and no assessment attached."
        ),
        match=(
            "clinical",
            "welfare",
            "vulnerable",
            "adverse event",
            "pv intake",
            "readmission",
            "counselling",
            "trained human",
            "international office",
            "jeopardy",
            "investigator site",
        ),
        steps=(
            step(
                "assemble_the_handover_dossier",
                "Compile the dossier for the named human",
                StepKind.DRAFT,
                (
                    "Compile what the signal is, the observations behind it with their "
                    "dates, the history already on file and the protocol that governs "
                    "this class of signal, and address it to the role the routing table "
                    "names -- the clinician, the welfare lead, the trained handler, the "
                    "international office, the relationship owner. Start whatever clock "
                    "the protocol attaches at the moment of detection and record that "
                    "time, because the receiving human inherits the clock and not the "
                    "detection. The dossier says what was observed and stops: the "
                    "meaning of it, the intervention and the decision are theirs, and "
                    "the only thing you may adjust on your own authority is the manner "
                    "of your own handling."
                ),
                produces=("handover_dossier", "routing_receipt"),
            ),
            step(
                "hold_at_the_named_human",
                "Stop at the named human",
                StepKind.GATE,
                (
                    "Hand the dossier over and stop. The finding does not become an "
                    "intervention, a case decision or an opinion about the person on "
                    "your authority, and it is not closed because nobody answered: an "
                    "unacknowledged dossier escalates to the out-of-hours contact and "
                    "stays open until a person has it in their hands."
                ),
            ),
        ),
        artifacts=(
            artifact(
                "handover_dossier",
                "Handover dossier",
                (
                    "What was observed, the dates and sources behind it, the history "
                    "already on file, the protocol that applies and an empty field for "
                    "the receiving human's assessment."
                ),
                "bundle",
            ),
            artifact(
                "routing_receipt",
                "Routing receipt",
                (
                    "The role the dossier went to, the time it was sent, the clock it "
                    "started, the acknowledgement received and every escalation raised "
                    "when one did not come."
                ),
            ),
        ),
        tools=("case_notes_lookup", "role_directory", "secure_handover"),
        config_keys=(
            ConfigKey(
                key="signal_definitions",
                description=(
                    "What constitutes a flag of this class in this vertical, the "
                    "observations that raise it and the ones that do not."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="named_handlers",
                description=(
                    "Which named role receives each class of signal, with the "
                    "out-of-hours fallback and the acknowledgement window."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="protocol_clock",
                description=(
                    "The clock each class of signal starts on detection and the "
                    "deadline it carries in this market."
                ),
                required=True,
            ),
        ),
        kpis=(
            "dossiers reaching the named role inside the protocol clock",
            "flags acknowledged by a person rather than ageing on a queue",
            "assessments or interventions the unit attempted itself",
        ),
        channels=("named_role_inbox",),
    ),
    Profile(
        name="abuse_pattern_watch",
        summary=(
            "Repeated counterparty behaviour assembled into an evidence pack "
            "mapped to the test that governs it, with only the graduated measure "
            "the policy already prescribes applied."
        ),
        match=(
            "abuse",
            "serial",
            "vexatious",
            "theft",
            "bypass",
            "poach",
            "beyond licence",
            "beyond license",
            "enforcement",
            "graduated",
            "returner",
            "party-house",
            "no-show",
            "observation only",
            "cross-account",
            "cross-order",
            "takedown",
        ),
        steps=(
            step(
                "map_it_to_the_test",
                "Map the occurrences onto the test that governs them",
                StepKind.ASSESS,
                (
                    "Set the occurrences against the test that actually governs them -- "
                    "the policy clause, the contract term, the platform's dispute rules, "
                    "the statutory definition -- and record occurrence by occurrence "
                    "which limb of that test each one meets, together with the limbs "
                    "nothing meets. The pattern is a count and a mapping, never a "
                    "characterisation of the party behind it: you record that six orders "
                    "in ninety days were refunded against an account that has ordered "
                    "eight, and you do not say what that person was doing."
                ),
                produces=("pattern_evidence_pack",),
            ),
            step(
                "apply_only_the_prescribed_measure",
                "Apply the measure the policy already attaches, and stop",
                StepKind.ACT,
                (
                    "Apply exactly the graduated measure the policy attaches to this "
                    "count -- the deposit requirement, the written warning, the "
                    "restriction, the notice -- cite the clause that carries it, and go "
                    "no further. Preserve every occurrence, message and capture in the "
                    "state it was found, because the pack has to survive a challenge "
                    "months later. Everything past the prescribed measure -- barring a "
                    "customer, closing an account, ending a relationship, pursuing "
                    "somebody -- is prepared as an option with its consequence beside it "
                    "and left for the named human to pick."
                ),
                produces=("measure_record",),
            ),
        ),
        artifacts=(
            artifact(
                "pattern_evidence_pack",
                "Pattern evidence pack",
                (
                    "Every occurrence with its date, value and capture, the test each "
                    "one is mapped onto, the limbs unmet, the party's prior history and "
                    "an empty determination field."
                ),
                "bundle",
            ),
            artifact(
                "measure_record",
                "Applied measure record",
                (
                    "The graduated measure applied, the clause that prescribed it, when "
                    "it took effect, who was told and the further options prepared for "
                    "the human with their consequences."
                ),
            ),
        ),
        tools=("occurrence_index", "policy_lookup", "evidence_vault"),
        config_keys=(
            ConfigKey(
                key="pattern_definitions",
                description=(
                    "What count, over what window and against what denominator "
                    "constitutes a pattern in this vertical."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="graduated_measures",
                description=(
                    "Which measure attaches to which count, the clause that carries "
                    "each one and the point past which only a human may go."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="evidence_standard",
                description=(
                    "What a pack must contain before it may go to a human, a "
                    "platform or a tribunal in this market."
                ),
                required=True,
            ),
        ),
        kpis=(
            "packs accepted by the reviewing human without further evidence",
            "applied measures citing the clause that prescribed them",
            "patterns raised that the human found unsupported",
        ),
    ),
    Profile(
        name="corpus_surveillance",
        summary=(
            "A standing body of text -- literature, submissions, reviews, "
            "feedback -- read on its cycle and condensed to what is new, with "
            "every theme traceable to the items that produced it."
        ),
        match=(
            "literature",
            "research summ",
            "consultation",
            "submissions",
            "voice-of-customer",
            "dish-level",
            "could not answer",
            "keep asking",
            "coverage condensed",
        ),
        steps=(
            step(
                "sift_the_new_from_the_known",
                "Keep only what is new or has changed",
                StepKind.ASSESS,
                (
                    "Read the corpus against what has already been reported and keep "
                    "only what is new or what has moved: the new publication, the "
                    "emerging theme, the complaint that has become a pattern, the "
                    "question asked for the fifth time this month. Rank by how often a "
                    "thing recurs and by the weight the configuration gives its source, "
                    "because one loud item and a quiet theme running through two hundred "
                    "are different findings and must not read the same."
                ),
                produces=("theme_index",),
            ),
            step(
                "condense_with_the_citations_attached",
                "Condense it so every claim walks back to an item",
                StepKind.DRAFT,
                (
                    "Write the digest so every statement in it can be walked back to the "
                    "items that produced it, with the item reference, its date and its "
                    "source beside each theme, and a verbatim example wherever the "
                    "wording itself is the finding. Condense what the corpus says and "
                    "never extend it: a conclusion the source material does not carry is "
                    "yours rather than the corpus's, and it has no place in a "
                    "surveillance digest."
                ),
                produces=("source_digest",),
            ),
        ),
        artifacts=(
            artifact(
                "theme_index",
                "Theme index",
                (
                    "Each theme with its occurrence count, the window it emerged in, "
                    "the weight of the sources behind it and whether it has been "
                    "reported before."
                ),
            ),
            artifact(
                "source_digest",
                "Sourced digest",
                (
                    "The condensed read: each theme with item-level citations, dates, "
                    "sources and a verbatim example, and nothing asserted that the items "
                    "do not carry."
                ),
                "document",
            ),
        ),
        tools=("corpus_reader", "theme_clusterer", "citation_index"),
        config_keys=(
            ConfigKey(
                key="corpus_sources",
                description=(
                    "The feeds, journals, review surfaces, inboxes and transcripts "
                    "read, with the cadence and the coverage expected of each."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="theme_taxonomy",
                description=(
                    "The categories themes are grouped under in this vertical and "
                    "the weight each kind of source carries."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "digest themes carrying item-level citations",
            "corpus items read against items available in the window",
            "themes the recipient had already seen somewhere else",
        ),
    ),
    Profile(
        name="market_signal_watch",
        summary=(
            "Third-party prices, rates, offers and mentions captured at source "
            "and compared on a stated like-for-like basis, with the capture "
            "attached to every number."
        ),
        match=(
            "competitor",
            "market",
            "pric",
            "tariff",
            "parity",
            "lane",
            "commodity",
            "shelf",
            "quote comparer",
            "panel quotes",
            "social listening",
            "mention",
            "offer moves",
        ),
        steps=(
            step(
                "capture_the_source_as_it_stood",
                "Capture the third-party surface as it stood",
                StepKind.GATHER,
                (
                    "Take the reading from the source itself and keep the artefact that "
                    "proves it -- the page, the listing, the rate card, the shelf photo, "
                    "the post -- with its address, its capture time and the account or "
                    "grant it was read under. A surface you do not own can change or "
                    "disappear within the hour, and the requote, the channel dispute and "
                    "the invoice that may follow rest on the capture rather than on your "
                    "note of what you saw."
                ),
                produces=("market_capture",),
            ),
            step(
                "compare_like_for_like",
                "Normalise before you compare",
                StepKind.ASSESS,
                (
                    "State the basis the configuration sets -- same inclusions, same "
                    "term, same quantity, same channel, same tax treatment -- and bring "
                    "each side onto it, showing the adjustment rather than folding it "
                    "into the number. Where a side cannot be brought onto the basis, say "
                    "so and leave it uncompared. A headline figure set against a "
                    "different thing is worse than no comparison at all, because "
                    "somebody will make a commercial move against it."
                ),
                produces=("like_for_like_comparison",),
            ),
        ),
        artifacts=(
            artifact(
                "market_capture",
                "Source capture",
                (
                    "The third-party reading with the artefact that proves it: the "
                    "address, the capture time, the grant it was read under and the "
                    "stored snapshot of the surface as it stood."
                ),
                "bundle",
            ),
            artifact(
                "like_for_like_comparison",
                "Like-for-like comparison",
                (
                    "Each side brought onto the stated basis with every adjustment "
                    "shown, the resulting gap, the items that could not be compared and "
                    "the reason each was left out."
                ),
                "report",
            ),
        ),
        tools=("source_crawler", "listing_capture", "comparison_normaliser"),
        config_keys=(
            ConfigKey(
                key="watched_market_sources",
                description=(
                    "The competitors, channels, panels, indices and community "
                    "surfaces this unit watches, with the read cadence for each."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="comparison_basis",
                description=(
                    "The terms on which a like-for-like comparison is made in this "
                    "vertical: inclusions, units, term length and tax treatment."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="capture_policy",
                description=(
                    "What must be captured with each third-party reading and how "
                    "long the capture is retained for a dispute in this market."
                ),
                required=True,
            ),
        ),
        kpis=(
            "findings carrying a capture of the source they came from",
            "comparisons made on a stated like-for-like basis",
            "market moves the owner heard about somewhere else first",
        ),
        channels=("owner_dashboard",),
    ),
    Profile(
        name="supply_watch",
        summary=(
            "Stock, consumables and supplier positions watched as days of cover, "
            "so the reorder or the pre-qualified alternate is on the owner's desk "
            "before the shortage bites."
        ),
        match=(
            "reorder",
            "replenish",
            "stock",
            "consumable",
            "parts",
            "supplier",
            "supplies",
            "alternates",
        ),
        steps=(
            step(
                "compute_the_cover",
                "Express the position as time, not quantity",
                StepKind.ASSESS,
                (
                    "Set what is on hand against what is committed and what is being "
                    "consumed, and give the answer as time rather than as a count: days "
                    "of cover at the current run rate, and the date the position goes "
                    "short. Include what is already on order with its promised date, and "
                    "treat a promise from a source that has slipped before as a promise "
                    "that may slip again."
                ),
                produces=("cover_position",),
            ),
            step(
                "prepare_the_reorder_or_the_alternate",
                "Put the order or the alternate in front of the owner",
                StepKind.DRAFT,
                (
                    "Draft the order the threshold calls for against the agreed source, "
                    "quantity and terms; where the usual source is itself the thing at "
                    "risk, work the pre-qualified alternates in the order configuration "
                    "ranks them and set out what each would cost and when it would "
                    "arrive. The order is prepared and left for the owner to release -- "
                    "you do not commit the business's money -- and a threshold crossed "
                    "with nothing drafted in front of somebody is the same as no watch "
                    "at all."
                ),
                produces=("reorder_draft",),
            ),
        ),
        artifacts=(
            artifact(
                "cover_position",
                "Cover position",
                (
                    "Per item: quantity on hand, committed, on order with its promised "
                    "date, the observed run rate, days of cover and the date the "
                    "position goes short."
                ),
                "report",
            ),
            artifact(
                "reorder_draft",
                "Prepared order or alternate",
                (
                    "The drafted order with source, quantity, agreed terms and expected "
                    "arrival, or the ranked alternates with the cost and lead time of "
                    "each, waiting on the owner's release."
                ),
                "document",
            ),
        ),
        tools=("inventory_system", "supplier_directory", "purchase_drafter"),
        config_keys=(
            ConfigKey(
                key="stock_thresholds",
                description=(
                    "Reorder point, safety stock, order multiple and expected lead "
                    "time per item or consumable in this vertical."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="approved_suppliers",
                description=(
                    "Agreed sources and pre-qualified alternates in preference "
                    "order, with terms and the authority each substitution needs."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "thresholds crossed with a prepared order the same day",
            "stockouts and near-misses logged with their cause",
            "cover days held above the configured floor",
        ),
    ),
    Profile(
        name="threshold_breach_watch",
        summary=(
            "A commitment, budget or limit run forward against what has been "
            "consumed, so the breach is raised in the window where it can still "
            "be avoided."
        ),
        match=(
            "sla",
            "threshold",
            "budget",
            "overrun",
            "overtime",
            "limit approaching",
            "pre-breach",
            "estimate",
            "scope",
            "drift",
            "mandate",
            "at-risk ticket",
            "before the bill",
        ),
        steps=(
            step(
                "project_the_breach",
                "Run the consumption forward to the crossing point",
                StepKind.ASSESS,
                (
                    "Take what has been consumed -- the hours, the spend, the response "
                    "time, the drift off the band, the scope already delivered -- and "
                    "run it forward at the observed rate to the point the limit is "
                    "crossed, naming the limit, the clause or mandate it comes from, the "
                    "projected value and the date. A breach reported after it landed is "
                    "a record; the finding this profile exists for is the one that "
                    "arrives while the commitment can still be met."
                ),
                produces=("breach_projection",),
            ),
            step(
                "set_out_the_options",
                "Set out the moves that would avert it",
                StepKind.DRAFT,
                (
                    "List the moves that would avert the crossing, each with what it "
                    "costs and what it gives up: reallocate, reprioritise, reroute, vary "
                    "the scope in writing, extend the deadline, warn the client early. "
                    "Where the configuration says the counterparty must hear about it "
                    "before the number lands, draft that message now with the figures as "
                    "they stand, so nobody is surprised by a bill or a breach they could "
                    "have been told about while it was still small."
                ),
                produces=("mitigation_options",),
            ),
        ),
        artifacts=(
            artifact(
                "breach_projection",
                "Breach projection",
                (
                    "The limit and its source, what has been consumed, the observed "
                    "rate, the projected value and the date the limit is crossed if "
                    "nothing changes."
                ),
                "report",
            ),
            artifact(
                "mitigation_options",
                "Mitigation options",
                (
                    "Each move that would avert the breach with its cost and its "
                    "trade-off, and the early-warning message drafted for whoever the "
                    "configuration says must be told."
                ),
                "document",
            ),
        ),
        tools=("commitment_register", "consumption_ledger", "projection_model"),
        config_keys=(
            ConfigKey(
                key="commitment_limits",
                description=(
                    "The service level, budget, estimate, mandate or statutory limit "
                    "each watch is measured against, with the clause it comes from."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="warning_lead_time",
                description=(
                    "How far ahead of a projected crossing the warning goes out, and "
                    "who receives it inside and outside the business."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "breaches raised before the limit was crossed",
            "commitments met after a warning was raised",
            "limits crossed with no prior warning on record",
        ),
    ),
    Profile(
        name="obligation_watch",
        summary=(
            "Written requirements -- clauses, obligations, curricula, licence "
            "terms -- held against what is actually happening, so the gap between "
            "the two is named while it can still be closed."
        ),
        match=(
            "obligation",
            "clause",
            "requirement",
            "non-compliant",
            "non-compliance",
            "misclassification",
            "sweep",
            "matrix",
            "deviation",
            "licensing",
            "seasoning",
            "gap",
            "stale content",
            "in-flight case",
            "skills",
        ),
        steps=(
            step(
                "extract_the_requirements",
                "Turn the instrument into monitorable lines",
                StepKind.GATHER,
                (
                    "Pull the requirements out of the instrument that carries them -- "
                    "the contract, the side letter, the rule change, the syllabus, the "
                    "licence, the redline playbook -- one line per obligation, each with "
                    "its trigger, its date, its owner and the clause reference it came "
                    "from. The buried obligation nobody ever extracted is the classic "
                    "failure in this shape of work: extraction is what turns a document "
                    "into something a watch can act on."
                ),
                produces=("obligation_register",),
            ),
            step(
                "sweep_the_population_against_them",
                "Test every affected record, not a sample",
                StepKind.ASSESS,
                (
                    "Test every affected record against every extracted requirement -- "
                    "each in-flight case, each module, each matter, each learner, each "
                    "draft -- and record for each pair whether it is met, missed, at "
                    "risk or untestable, with the evidence behind the answer. Sweeping "
                    "the whole population is the point: a sample tells you a problem "
                    "exists, and this finding has to name exactly who is affected and "
                    "what each of them now needs."
                ),
                produces=("compliance_matrix",),
            ),
        ),
        artifacts=(
            artifact(
                "obligation_register",
                "Obligation register",
                (
                    "One line per extracted requirement with its trigger, date, owner, "
                    "clause reference, the instrument version it came from and its "
                    "current monitoring state."
                ),
            ),
            artifact(
                "compliance_matrix",
                "Requirement sweep matrix",
                (
                    "Every affected record against every requirement, marked met, "
                    "missed, at risk or untestable, with the evidence for each answer "
                    "and the action each affected party now needs."
                ),
                "report",
            ),
        ),
        tools=("document_extractor", "requirements_register", "population_sweeper"),
        config_keys=(
            ConfigKey(
                key="governing_instruments",
                description=(
                    "The contracts, rule sets, curricula and licence terms this "
                    "watch monitors, with their versions and effective dates."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="affected_population",
                description=(
                    "Which records are swept against a requirement in this vertical "
                    "and how that set is refreshed between sweeps."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "obligations extracted with a clause reference and a trigger",
            "affected records identified per rule change",
            "obligations found later that the register had missed",
        ),
    ),
    Profile(
        name="anomaly_baseline_watch",
        summary=(
            "A figure set against its own normal band, sized and dated, with the "
            "correlated variables handed to whoever owns the cause."
        ),
        match=(
            "anomal",
            "variance",
            "discrepancy",
            "spike",
            "baseline",
            "bill shock",
            "scrap",
            "overspend",
            "lift",
            "statistical",
            "correlated",
            "early-warning",
            "cluster",
            "warranty",
            "claim-pattern",
        ),
        steps=(
            step(
                "size_it_against_the_band",
                "Size the deviation and price its consequence",
                StepKind.ASSESS,
                (
                    "State the figure, the band it should sit in, how that band was "
                    "computed, and by how much and for how long it has been outside it. "
                    "Season, volume and mix move a normal band and must be taken out "
                    "before a deviation is claimed, or every busy week becomes an alert. "
                    "Then say what it costs, breaks or exposes if it continues at this "
                    "rate: a deviation with no consequence beside it gets ignored, and "
                    "deserves to be."
                ),
                produces=("deviation_report",),
            ),
            step(
                "attach_the_correlated_variables",
                "Attach what moved with it, labelled as correlation",
                StepKind.GATHER,
                (
                    "Attach what moved alongside it -- the shift, the line, the "
                    "operator, the batch, the supplier, the release, the tariff change "
                    "-- as correlations with their strength and their window, so the "
                    "engineer, analyst or accountant who owns the cause starts from data "
                    "rather than a blank page. Correlation is what you supply and cause "
                    "is what they determine, and the pack must never be written so the "
                    "two read as the same thing."
                ),
                produces=("correlation_pack",),
            ),
        ),
        artifacts=(
            artifact(
                "deviation_report",
                "Deviation report",
                (
                    "The metric, its normal band and how the band was computed, the "
                    "size and duration of the excursion, the seasonality removed and the "
                    "consequence if it continues."
                ),
                "report",
            ),
            artifact(
                "correlation_pack",
                "Correlated-variable pack",
                (
                    "Every variable that moved with the metric, its correlation "
                    "strength and window, and an explicit statement that these are "
                    "correlations rather than causes."
                ),
                "bundle",
            ),
        ),
        tools=("metric_store", "baseline_model", "correlation_finder"),
        config_keys=(
            ConfigKey(
                key="metric_baselines",
                description=(
                    "Per watched metric: the normal band, how it is computed and the "
                    "seasonality and mix effects taken out of it."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="deviation_thresholds",
                description=(
                    "The size and duration of excursion at which a metric becomes a "
                    "finding, and the band that goes out immediately."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "deviations carrying a quantified consequence",
            "deviations raised before the period closed",
            "alerts raised on movement that was inside the normal band",
        ),
    ),
    Profile(
        name="customer_signal_watch",
        summary=(
            "The customer book read for behaviour -- decay, absence, unclaimed "
            "work, expansion -- and turned into a named list with the reason and "
            "the next contact already drafted."
        ),
        match=(
            "churn",
            "decay",
            "attendance",
            "absence",
            "lapse",
            "donor",
            "at-risk member",
            "account health",
            "save play",
            "save sequence",
            "upsell",
            "expansion",
            "unscheduled",
            "unbooked",
            "never booked",
            "cross-practice",
            "cross-service",
            "subrogation",
            "opportunity",
        ),
        steps=(
            step(
                "score_the_book",
                "Score every record against its own pattern",
                StepKind.ASSESS,
                (
                    "Run every record in the book against the configured signals -- "
                    "sessions missed against its own rhythm, usage against its own "
                    "history, work recommended and never taken up, a change that opens a "
                    "second service, a recoverable cost sitting inside a settled claim "
                    "-- and score each with the signals that fired and the value at "
                    "stake. Score against the record's own pattern rather than a "
                    "population average: the member who always came twice a month and "
                    "now comes once has decayed, and the member who always came once has "
                    "not."
                ),
                produces=("scored_book",),
            ),
            step(
                "draft_the_next_contact",
                "Draft the specific next contact for each name",
                StepKind.DRAFT,
                (
                    "For each record over the threshold, draft the contact itself -- "
                    "what was noticed, what is being offered, what it costs from the "
                    "agreed price list and one clear way to take it up -- and hand the "
                    "named list to the person or the sequence that owns the outreach. It "
                    "goes out through the business's own connected accounts and in the "
                    "business's own voice, never yours. Where the signal touches "
                    "somebody's circumstances rather than their usage, the draft goes to "
                    "a named human before it goes anywhere at all."
                ),
                produces=("outreach_list",),
            ),
        ),
        artifacts=(
            artifact(
                "scored_book",
                "Scored book",
                (
                    "Every record with the signals that fired against its own history, "
                    "the score, the value at stake and the date the behaviour changed."
                ),
                "report",
            ),
            artifact(
                "outreach_list",
                "Named outreach list",
                (
                    "Each record over threshold with the reason it is listed, the "
                    "drafted contact, the offer and its price-book reference, and the "
                    "owner of the outreach."
                ),
                "document",
            ),
        ),
        tools=("customer_book", "signal_scorer", "outreach_drafter"),
        config_keys=(
            ConfigKey(
                key="behaviour_signals",
                description=(
                    "Which behaviours count as decay, absence, unclaimed work or "
                    "expansion in this vertical, and over what window."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="save_and_offer_policy",
                description=(
                    "What may be offered against each signal, what needs the owner's "
                    "decision first, and how often one record may be contacted."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="connected_accounts",
                description=(
                    "OAuth grants for the customer's own accounts. Every drafted "
                    "contact leaves from one of these; the platform never reaches a "
                    "customer from an account it owns."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "at-risk records contacted before they lapsed",
            "drafted contacts released without an edit",
            "value recovered from records the sweep re-opened",
        ),
        channels=("messaging", "email"),
    ),
    Profile(
        name="performance_digest",
        summary=(
            "Internal numbers turned into one periodic read: what moved, against "
            "what, and what is worth doing next -- written for somebody who does "
            "not read reports."
        ),
        match=(
            "digest",
            "benchmark",
            "narrator",
            "analytics",
            "insights",
            "forecaster",
            "utilization",
            "utilisation",
            "chief of staff",
            "conversion",
            "section planning",
            "reporter",
        ),
        steps=(
            step(
                "assemble_the_period",
                "Pull each figure from the system that owns it",
                StepKind.GATHER,
                (
                    "Take each figure from the system of record that owns it rather than "
                    "from another report, state the period, the comparison period and "
                    "the plan or peer set it is measured against, and reconcile each "
                    "total to its source before a word is written. Two different numbers "
                    "for the same thing destroy the whole document; where sources "
                    "disagree, say which one was used and that they disagreed."
                ),
                produces=("period_figures",),
            ),
            step(
                "write_it_in_plain_language",
                "Write the three things that actually moved",
                StepKind.DRAFT,
                (
                    "Write it so somebody who never opens a dashboard can act on it: the "
                    "three or four things that actually moved, each with its size, its "
                    "direction and the plain reason the data supports, then what is "
                    "worth doing next set out as options rather than instructions. Cut "
                    "everything that did not move, because a page of unchanged numbers "
                    "teaches the reader to stop opening it, and where a movement has no "
                    "explanation in the data, say so instead of supplying one."
                ),
                produces=("period_narrative",),
            ),
        ),
        artifacts=(
            artifact(
                "period_figures",
                "Period figures",
                (
                    "Each reported figure with its system of record, the period and "
                    "comparison period, the plan or peer set behind it and the "
                    "reconciliation that proves it."
                ),
            ),
            artifact(
                "period_narrative",
                "Plain-language narrative",
                (
                    "What moved, by how much, in which direction and why as far as the "
                    "data supports it, with the next moves offered as options and the "
                    "unexplained movements named as unexplained."
                ),
                "document",
            ),
        ),
        tools=("metrics_warehouse", "benchmark_service", "report_composer"),
        config_keys=(
            ConfigKey(
                key="reporting_period",
                description=(
                    "The cycle each report covers, the period it is compared "
                    "against and the hour it must be in the recipient's hands."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="report_metrics",
                description=(
                    "Which figures appear, the system of record for each and the "
                    "plan or peer set they are measured against in this vertical."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "reports delivered inside their window",
            "figures reconciling to their system of record",
            "movements reported with an explanation the data supports",
        ),
        channels=("owner_dashboard", "email"),
    ),
    # Fallback.  Deliberately the family's canonical shape rather than a dumping
    # ground: a source read on its cycle, diffed against the state it was last
    # known to hold, and re-read once before anything is raised.  The units that
    # land here -- a portal watched for slots, a bank feed watched for renewals,
    # a backup watched for a restore that still works, a drawing watched for a
    # superseded revision -- are exactly that and nothing more.
    Profile(
        name="source_change_alert",
        summary=(
            "A watched source read on its cycle and diffed against the state it "
            "was last known to hold, with the difference verified once before it "
            "is raised."
        ),
        match=(),
        steps=(
            step(
                "diff_against_the_last_known_state",
                "Diff the source against its last known state",
                StepKind.ASSESS,
                (
                    "Compare what the source holds now against the state recorded for it "
                    "at the last read -- field by field where it is structured, item by "
                    "item where it is not -- and classify every difference as new, "
                    "changed, removed or unchanged. Where the configuration expects a "
                    "source to move, a source that returned the same thing twice is a "
                    "finding of its own: an unchanged backup timestamp and a portal that "
                    "never opens a slot both get reported rather than skipped."
                ),
                produces=("state_diff",),
            ),
            step(
                "verify_before_you_raise_it",
                "Re-read once, and test end to end where it is a test",
                StepKind.ACT,
                (
                    "Re-read the source once before raising anything, because a "
                    "transient failure, a cached page or a partial response is the "
                    "commonest cause of a change that was not one. Where the watch is a "
                    "test rather than an observation, run it end to end -- restore the "
                    "file and open it, request the record and read it back, take the "
                    "slot and confirm it held -- and record what the test actually "
                    "returned rather than the fact that it ran."
                ),
                produces=("verification_result",),
            ),
        ),
        artifacts=(
            artifact(
                "state_diff",
                "State difference",
                (
                    "Every field or item compared with its previous and current value, "
                    "classified as new, changed, removed or unchanged, including the "
                    "unchanged values the configuration expected to move."
                ),
            ),
            artifact(
                "verification_result",
                "Verification result",
                (
                    "The re-read or end-to-end test with what it actually returned, the "
                    "time it ran, and whether the difference survived verification."
                ),
                "log",
            ),
        ),
        tools=("source_reader", "state_differ", "verification_runner"),
        config_keys=(
            ConfigKey(
                key="source_state_keys",
                description=(
                    "Which fields of each source define its state, which "
                    "differences are meaningful and which are expected churn."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="verification_procedure",
                description=(
                    "For watches that test rather than observe: the test that runs "
                    "end to end, what counts as a pass and how often it runs."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "raised changes that survived re-verification",
            "cycles in which every watched source was read",
            "changes found by somebody else that the watch reported as unchanged",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class WatcherSurveillanceEngine(Engine):
    """Carries every unit whose work is a standing watch on a source.

    The engine holds one loop -- read the watchlist, capture what each source
    said, compare it to the stored baseline, test the difference against a
    threshold, write the finding, write the reading back as the next baseline
    and tell whoever wanted to know -- and eleven profiles that say what kind of
    source is being watched.  Nothing in the code knows whether it is holding a
    channel rate table, a journal feed or a scrap counter; the sources, the
    cadences, the baselines, the thresholds and the routing all arrive as
    configuration.
    """

    id: ClassVar[str] = "MF7"
    family: ClassVar[str] = "Watcher / surveillance"
    what_it_does: ClassVar[str] = (
        "Monitors internal and external signals - rates, literature, "
        "competitors, parity, benchmarks"
    )
    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.WATCH_SIGNAL,
        Capability.RECONCILE,
        Capability.SCORE,
        Capability.CLOCK,
        Capability.COLLECT_DOCUMENTS,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "source_watchlist",
        "source_fetcher",
        "snapshot_capture",
        "baseline_store",
        "delta_calculator",
        "materiality_scorer",
        "alert_dispatcher",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "owner_dashboard",
        "email",
        "messaging",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "material changes surfaced before the owner heard them elsewhere",
        "watched sources read on their configured cadence",
        "findings carrying a captured source and its timestamp",
        "raised findings the recipient marked as noise",
        "changes found afterwards that the watch had missed",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    state_object: ClassVar[str] = "watch_state"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        return _PROFILES

    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Read, capture, compare, decide, write, re-baseline, tell.

        The order is the discipline, and two placements in it carry most of the
        weight.  Capture happens before comparison, because the surface being
        compared can change or vanish while the comparison runs and the dispute
        that follows rests on what was kept.  Re-baselining happens after the
        finding is written and before anybody is told, so a cycle that fails
        halfway cannot silently move the baseline past a change nobody ever
        saw.  Notification is last because a watcher's credibility is a single
        resource: it is spent by alerts on movement inside the normal band, and
        it is spent just as fast by a cycle that says nothing at all.
        """
        return (
            step(
                "poll_the_watchlist",
                "Read every source on the watchlist",
                StepKind.OBSERVE,
                (
                    "Read every source on the watchlist at its configured cadence, from "
                    "its last position, and record for each one whether it answered, "
                    "when it was read and what it returned -- including the sources that "
                    "returned nothing at all. A source that failed to answer is a blind "
                    "spot and is recorded as one: silence is never taken as evidence "
                    "that nothing happened."
                ),
                produces=("observation_log",),
            ),
            step(
                "capture_the_evidence",
                "Capture what you saw at the moment you saw it",
                StepKind.GATHER,
                (
                    "Capture each reading as it stood: the value, the page, the record, "
                    "the reading or the item, with its source, its identifier and the "
                    "timestamp the source itself carries rather than the time you got "
                    "to it. Take a snapshot wherever the source can change or vanish "
                    "under you. The capture is the evidence, and a change you cannot "
                    "show is a change nobody can act on."
                ),
                produces=("evidence_capture",),
            ),
            step(
                "compare_against_the_baseline",
                "Set the reading against its baseline",
                StepKind.ASSESS,
                (
                    "Set what you captured against the stored prior -- the last reading, "
                    "the agreed reference, the contracted level, the rule in force, the "
                    "peer band -- and state the direction, the size and the window of "
                    "every difference. Name the baseline and its date beside the number: "
                    "a delta whose reference nobody can see is an assertion rather than "
                    "a finding."
                ),
                produces=("change_ledger",),
            ),
            step(
                "test_for_materiality",
                "Decide what is worth somebody's attention",
                StepKind.DECIDE,
                (
                    "Test each difference against the materiality thresholds configured "
                    "for this watch and record the threshold that produced the answer in "
                    "both directions. Count persistence as well as size: a small "
                    "movement in the same direction across several cycles is material "
                    "even where no single cycle was, and a movement that fired once and "
                    "reverted is logged rather than raised. A difference that matches no "
                    "threshold goes out at the default band instead of being dropped."
                ),
                produces=("materiality_decision",),
            ),
            step(
                "write_the_finding",
                "Write the change for one read",
                StepKind.DRAFT,
                (
                    "Write each material change so it can be acted on in one read: what "
                    "was watched, what it was before, what it is now, when it moved, the "
                    "evidence behind it, and what it puts at risk or within reach if "
                    "nothing is done. Write what moved and stop there. Why it moved, "
                    "what it says about a competitor's intent or a person's conduct, and "
                    "what to do about it are the reader's to conclude; where the "
                    "configuration names response options, set them out as options with "
                    "their consequences and leave the choice open."
                ),
                produces=("watch_finding",),
            ),
            step(
                "update_the_watch_state",
                "Re-baseline and age what is still open",
                StepKind.ACT,
                (
                    "Write the new reading into the watch state as the baseline the next "
                    "cycle compares against, with the time it was taken and the source "
                    "it came from, and carry every unresolved finding forward so a change "
                    "already raised is not raised again as new. Age the open findings "
                    "rather than dropping them: one nobody has dealt with is repeated "
                    "with its age attached."
                ),
                produces=("watch_state",),
            ),
            step(
                "raise_it_with_the_recipient",
                "Tell whoever wanted to know, at the right volume",
                StepKind.NOTIFY,
                (
                    "Deliver at the volume the routing sets for this watch -- "
                    "immediately for what will not keep, in the cycle digest for "
                    "everything else -- to the named recipient, with the capture attached "
                    "rather than referenced. A cycle in which nothing moved still "
                    "reports: the digest names the sources read, the sources that failed "
                    "to answer and the fact that nothing crossed a threshold, because a "
                    "watcher that only speaks when something happens cannot be told "
                    "apart from one that has stopped running."
                ),
                produces=("watch_digest",),
            ),
        )

    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "observation_log",
                "Observation log",
                (
                    "Every source on the watchlist for this cycle: when it was read, "
                    "whether it answered, what it returned, and the coverage lost where "
                    "it did not."
                ),
                "log",
            ),
            artifact(
                "evidence_capture",
                "Evidence capture",
                (
                    "The reading as it stood, with its source, identifier, the "
                    "timestamp the source itself carried and a snapshot wherever the "
                    "surface can change or vanish."
                ),
                "bundle",
            ),
            artifact(
                "change_ledger",
                "Change ledger",
                (
                    "Each difference found this cycle with the baseline it is measured "
                    "against, that baseline's date and source, and the direction, size "
                    "and window of the move."
                ),
            ),
            artifact(
                "materiality_decision",
                "Materiality decision",
                (
                    "For every difference, raised or held: the threshold applied, the "
                    "persistence counted, the band produced and the reason it was or "
                    "was not put in front of a person."
                ),
            ),
            artifact(
                "watch_finding",
                "Watch finding",
                (
                    "The material change written for one read: what was watched, before "
                    "and after, when it moved, the evidence, what is now at risk or "
                    "within reach, and the options with their consequences."
                ),
                "document",
            ),
            artifact(
                "watch_state",
                "Watch state",
                (
                    "The state carried between cycles: the last reading for each "
                    "watched value with its time and source, and every open finding "
                    "with its age."
                ),
            ),
            artifact(
                "watch_digest",
                "Watch digest",
                (
                    "The cycle's report: what moved and what did not, the sources read, "
                    "the sources that failed to answer, and an explicit statement when "
                    "nothing crossed a threshold."
                ),
                "report",
            ),
        )

    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        vertical = record.get("vertical") or {}
        if vertical:
            where = (
                f"What is worth watching in {vertical['name'].lower()}, how often each "
                f"source is read and the size of move that counts as material there "
                f"come from the vertical overlay and the active country pack -- read "
                f"both rather than deciding for yourself what is normal here."
            )
        else:
            where = (
                "This watch runs across every vertical on the platform, so what counts "
                "as normal, what counts as a material move and who wants to hear about "
                "it all come from whatever overlay is in front of you."
            )
        return (
            "HOW YOU WORK. Nothing you watch is delivered to you: prices move, rules "
            "change, usage decays, a supplier goes quiet, a backup stops restoring, and "
            "none of it arrives in an inbox. You read the sources on their cycle, "
            "capture what each one said at the moment it said it, and set that against "
            "the baseline the configuration names -- the last reading, the contracted "
            "level, the rule in force, the peer band -- so what you produce is the "
            "change and never the reading. Keep the state between runs, because a "
            "watcher with no memory has no change to report: write each new reading "
            "back as the baseline the next cycle compares against, and carry an open "
            "finding forward with its age rather than raising it a second time as new. "
            "Test every difference against the configured threshold before you raise "
            "it, counting persistence as well as size -- a small move in the same "
            "direction over several cycles is the finding, and a spike that reverted is "
            "a log entry. Never read silence as calm: a source that failed to answer "
            "looks exactly like a source where nothing happened, so every cycle reports "
            "which sources were read, which were not and what that leaves unwatched. "
            "Attach the capture to every number you report, because the requote, the "
            "dispute, the invoice or the statutory clock that may follow rests on what "
            "you kept at the time rather than on your note of it. And stop where "
            "observation stops: you report what moved, when, against what and with what "
            "evidence, while why it moved, what it means about a person's conduct or "
            "intent and what should be done about it belong to the human you hand it "
            f"to. {self._profile_line(profile)} {where}"
        )

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        return (
            Guardrail(
                id="GR-BASELINE-IS-NAMED",
                rule=(
                    "Every change is stated against a named baseline with its date. "
                    "A number with no reference it moved from is not a finding."
                ),
                check=(
                    "change_ledger names the baseline, its source and the time it was "
                    "taken for every difference raised, and each baseline resolves to "
                    "baseline_definition."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-SILENCE-IS-NOT-CALM",
                rule=(
                    "A source that did not answer is reported as unwatched. The "
                    "absence of a reading is never reported as the absence of change."
                ),
                check=(
                    "observation_log carries a read result for every source in "
                    "watch_sources each cycle, and watch_digest names the sources that "
                    "failed to answer and the coverage that was lost."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CAPTURE-BEFORE-COMPARE",
                rule=(
                    "Evidence is captured at the moment of observation, before any "
                    "comparison, because the source can change or vanish afterwards."
                ),
                check=(
                    "Every finding links to an evidence_capture taken at or before the "
                    "reading's own timestamp and retained for the period "
                    "evidence_retention sets."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-OBSERVATION-NOT-CONCLUSION",
                rule=(
                    "The unit reports what moved and what the evidence shows. It "
                    "never states the cause, or what a movement means about a "
                    "person's conduct, competence or intent."
                ),
                check=(
                    "watch_finding contains no cause statement, characterisation or "
                    "accusation; correlated variables are labelled as correlations and "
                    "the determination field is left for the named human."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MATERIALITY-CITES-A-THRESHOLD",
                rule=(
                    "What is raised and what is held back is decided by a configured "
                    "threshold, not by how interesting the movement looks."
                ),
                check=(
                    "materiality_decision names the threshold and the persistence rule "
                    "applied in both directions; a difference matching no threshold "
                    "goes out at the default band rather than being dropped."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-STATE-CARRIES-FORWARD",
                rule=(
                    "The reading becomes the next cycle's baseline, and an open "
                    "finding ages rather than disappearing."
                ),
                check=(
                    "watch_state is written every cycle with the reading, its time and "
                    "its source; a finding already raised is repeated with its age and "
                    "never re-raised as new."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-QUIET-CYCLE-STILL-REPORTS",
                rule=(
                    "A cycle in which nothing moved still reports. A watcher that "
                    "speaks only when something happens cannot be told apart from one "
                    "that has stopped running."
                ),
                check=(
                    "watch_digest is produced on every configured cycle, naming the "
                    "sources read and stating explicitly when nothing crossed a "
                    "threshold."
                ),
                source="mechanism_family",
            ),
        )

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "The watchlist, with the last read position, time and result for each source",
            "Stored watch state: the last known reading for every watched value",
            "Baselines, materiality thresholds and persistence rules in force, with versions",
            "Findings already open, with their age and what has been done about them",
            "Routing for this watch: who hears what, at what volume, and out of hours",
        )

    # -- internals ----------------------------------------------------------
    def _profile_line(self, profile: Profile) -> str:
        """One sentence naming what kind of source this profile is watching.

        Kept beside the profiles rather than inside them because it is prose
        about the mission, not configuration a customer can override.
        """
        return _PROFILE_MISSION_LINES.get(
            profile.name, _PROFILE_MISSION_LINES["source_change_alert"]
        )


#: Mission prose per profile.  Each names the source, the artefact that proves
#: the work, and the exact point at which the watch stops and a person takes
#: over.
_PROFILE_MISSION_LINES: dict[str, str] = {
    "person_risk_flag": (
        "What you watch here is a signal about a person: compile the observations, "
        "the dates and the history into one dossier, start the clock the protocol "
        "attaches at the moment of detection, hand it to the named clinician, "
        "handler or office and stop -- the meaning of the signal and every decision "
        "that follows from it are theirs, and an unacknowledged dossier escalates "
        "rather than closing."
    ),
    "abuse_pattern_watch": (
        "What you watch here is repeated behaviour by a counterparty: count the "
        "occurrences, map each one onto the limb of the policy or statutory test it "
        "meets, preserve every capture in the state you found it, apply only the "
        "graduated measure the policy already prescribes, and leave barring, closing "
        "and pursuing to the human with the authority to decide it."
    ),
    "market_signal_watch": (
        "What you watch here belongs to somebody else: capture the page, the rate "
        "card or the shelf as it stood with its address and its time, bring both "
        "sides onto a stated like-for-like basis and show the adjustment, and leave "
        "anything that will not normalise uncompared rather than putting a "
        "misleading gap in front of somebody about to make a commercial move."
    ),
    "supply_watch": (
        "What you watch here is a position that runs out: express it as days of "
        "cover and the date it goes short rather than as a quantity, and put the "
        "drafted order or the ranked pre-qualified alternates in front of the owner "
        "at the threshold -- you prepare the commitment and the owner releases it."
    ),
    "threshold_breach_watch": (
        "What you watch here is a limit being approached: run the consumption "
        "forward at the observed rate to the hour or the day it would be crossed, "
        "name the limit and the clause it comes from, and get the warning and the "
        "options in front of the person who can still change the plan -- a breach "
        "reported afterwards is only a record."
    ),
    "corpus_surveillance": (
        "What you watch here is a body of text that keeps growing: keep only what is "
        "new or has changed, rank a recurring theme above a single loud item, and "
        "write every statement so it walks back to the items and dates that produced "
        "it -- condense what the corpus says and never extend it."
    ),
    "obligation_watch": (
        "What you watch here is written down somewhere and being quietly missed: "
        "extract each obligation as its own monitorable line with its trigger and "
        "clause reference, sweep the whole affected population rather than a sample, "
        "and name exactly who is affected and what each of them now needs."
    ),
    "anomaly_baseline_watch": (
        "What you watch here is a number that should sit in a band: take season, "
        "volume and mix out before you claim a deviation, size it and price what it "
        "costs or breaks if it continues, and attach the variables that moved with "
        "it as correlations -- the cause is determined by the engineer or the "
        "analyst, never asserted by you."
    ),
    "customer_signal_watch": (
        "What you watch here is the book itself: score every record against its own "
        "history rather than a population average, and turn the ones over threshold "
        "into a named list with the reason and the next contact already drafted, "
        "priced from the agreed list and ready to go out through the business's own "
        "connected accounts in the business's own voice."
    ),
    "performance_digest": (
        "What you watch here is the business's own numbers: pull each figure from the "
        "system that owns it and reconcile before you write, then say plainly what "
        "the three or four things that actually moved were, cut everything that did "
        "not move, and mark an unexplained movement as unexplained instead of "
        "inventing a reason for it."
    ),
    "source_change_alert": (
        "What you watch here is one source and the state it was last known to hold: "
        "diff it field by field, treat a value that should have moved and did not as "
        "a finding of its own, and re-read or re-run the test once before raising "
        "anything, because a cached page and a partial response are the commonest "
        "causes of a change that never happened."
    ),
}


__all__ = ["WatcherSurveillanceEngine"]
